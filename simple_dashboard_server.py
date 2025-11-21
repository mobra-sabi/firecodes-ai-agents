#!/usr/bin/env python3
"""
🚀 Simple Dashboard Server
Serves static files AND provides API data from MongoDB
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
from pymongo import MongoClient
from bson import ObjectId
import json
import os

# MongoDB connection
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/live-stats':
            self.send_api_response()
        else:
            # Serve static files
            super().do_GET()
    
    def send_api_response(self):
        try:
            # Count agents
            total_agents = db.site_agents.count_documents({})
            master_agents = db.site_agents.count_documents({"agent_type": "master"})
            slave_agents = db.site_agents.count_documents({"agent_type": "slave"})
            
            # Calculate total chunks
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}
            ]
            chunks_result = list(db.site_agents.aggregate(pipeline))
            total_chunks = chunks_result[0]["total"] if chunks_result else 0
            
            # Get master agents
            masters = list(db.site_agents.find(
                {"agent_type": "master"},
                {"domain": 1, "chunks_indexed": 1, "created_at": 1}
            ).limit(10))
            
            # For each master, count slaves
            for master in masters:
                master_id = str(master["_id"])
                master["_id"] = master_id
                slave_count = db.site_agents.count_documents({
                    "master_agent_id": ObjectId(master_id)
                })
                master["slave_count"] = slave_count
                master["created_at"] = master.get("created_at").isoformat() if master.get("created_at") else ""
            
            # Get recent slaves
            recent_slaves = list(db.site_agents.find(
                {"agent_type": "slave"},
                {"domain": 1, "chunks_indexed": 1, "created_at": 1, "master_agent_id": 1}
            ).sort("created_at", -1).limit(10))
            
            # Get master domain for each slave
            for slave in recent_slaves:
                slave["_id"] = str(slave["_id"])
                if "master_agent_id" in slave:
                    master = db.site_agents.find_one(
                        {"_id": slave["master_agent_id"]},
                        {"domain": 1}
                    )
                    slave["master_domain"] = master["domain"] if master else "Unknown"
                    slave["master_agent_id"] = str(slave["master_agent_id"])  # Convert to string
                slave["created_at"] = slave.get("created_at").isoformat() if slave.get("created_at") else ""
            
            response_data = {
                "total_agents": total_agents,
                "master_agents": master_agents,
                "slave_agents": slave_agents,
                "total_chunks": total_chunks,
                "masters": masters,
                "recent_slaves": recent_slaves
            }
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            # Send error response
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == '__main__':
    os.chdir('/srv/hf/ai_agents')
    port = 8888
    print(f"🚀 Starting Dashboard Server on port {port}...")
    print(f"📊 Serving static files from: {os.getcwd()}")
    print(f"🔗 API endpoint: http://localhost:{port}/api/live-stats")
    print(f"🌐 Dashboard: http://localhost:{port}/static/live_data_dashboard.html")
    
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    server.serve_forever()

