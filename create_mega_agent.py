#!/usr/bin/env python3
"""
🚀 MEGA AGENT CREATOR cu WebSocket Progress
==========================================

Creează agenți mari (5000+ pages) cu progress tracking live.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MegaAgentCreator:
    """Creator pentru agenți mari cu progress tracking"""
    
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.ai_agents_db
    
    async def send_progress(self, step: str, progress: float, message: str, details: Dict = None):
        """Trimite progress update via WebSocket"""
        data = {
            "step": step,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        # Print to console
        print(f"[{progress:5.1f}%] {step}: {message}")
        if details:
            for key, val in details.items():
                print(f"          {key}: {val}")
        
        # Send via WebSocket if available
        if self.websocket:
            try:
                await self.websocket.send_text(json.dumps(data))
            except:
                pass
    
    async def create_mega_agent(self, url: str, max_pages: int = 5000):
        """
        Creează agent mare cu progress tracking
        
        Steps:
        1. Initialization (0-5%)
        2. Scraping (5-50%)
        3. Processing (50-60%)
        4. GPU Embeddings (60-75%)
        5. Qdrant Upload (75-85%)
        6. DeepSeek Analysis (85-90%)
        7. MongoDB Save (90-95%)
        8. Competitive Intelligence (95-100%)
        """
        
        start_time = time.time()
        
        try:
            # STEP 1: Initialization (0-5%)
            await self.send_progress(
                "initialization",
                0,
                "🚀 Starting agent creation...",
                {"url": url, "max_pages": max_pages}
            )
            
            import subprocess
            
            # Extract domain
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            
            await self.send_progress(
                "initialization",
                2,
                f"📝 Domain extracted: {domain}"
            )
            
            # Check if agent exists
            existing = self.db.site_agents.find_one({"domain": domain})
            if existing:
                await self.send_progress(
                    "initialization",
                    5,
                    f"⚠️ Agent already exists: {domain}",
                    {"agent_id": str(existing['_id'])}
                )
                return str(existing['_id'])
            
            await self.send_progress(
                "initialization",
                5,
                "✅ Initialization complete"
            )
            
            # STEP 2-7: Agent Creation (5-90%)
            await self.send_progress(
                "agent_creation",
                5,
                "🤖 Starting agent creation process...",
                {"script": "construction_agent_creator.py"}
            )
            
            # Run agent creator with progress monitoring
            agent_id = await self._run_agent_creator(url, max_pages)
            
            if not agent_id:
                raise Exception("Agent creation failed!")
            
            await self.send_progress(
                "agent_creation",
                90,
                f"✅ Agent created: {agent_id}",
                {"agent_id": agent_id, "domain": domain}
            )
            
            # STEP 8: Competitive Intelligence (90-100%)
            await self.send_progress(
                "competitive_intelligence",
                90,
                "🧠 Starting competitive intelligence...",
                {"agent_id": agent_id}
            )
            
            # Run CI workflow
            await self._run_competitive_intelligence(agent_id)
            
            # Final stats
            elapsed = time.time() - start_time
            agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            
            await self.send_progress(
                "completed",
                100,
                "🎉 Agent creation completed!",
                {
                    "agent_id": agent_id,
                    "domain": domain,
                    "chunks": agent.get('chunks_indexed', 0) if agent else 0,
                    "elapsed_seconds": elapsed,
                    "elapsed_minutes": elapsed / 60
                }
            )
            
            return agent_id
            
        except Exception as e:
            await self.send_progress(
                "error",
                0,
                f"❌ Error: {str(e)}",
                {"error": str(e)}
            )
            raise
    
    async def _run_agent_creator(self, url: str, max_pages: int) -> Optional[str]:
        """Run construction_agent_creator.py with progress monitoring"""
        
        import subprocess
        import threading
        import queue
        
        # Create agent creation script
        env = {
            **os.environ,
            "MONGODB_URI": "mongodb://localhost:27017",
            "QDRANT_URL": "http://localhost:9306"
        }
        
        # Start process
        process = subprocess.Popen(
            [
                'python3',
                '/srv/hf/ai_agents/tools/construction_agent_creator.py',
                '--url', url,
                '--mode', 'create_agent'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Monitor output for progress
        async def monitor_output():
            progress_mapping = {
                "Scraping": (10, 50),   # 10-50%
                "Extracting": (50, 55),  # 50-55%
                "Chunking": (55, 60),    # 55-60%
                "Embedding": (60, 75),   # 60-75%
                "Qdrant": (75, 85),      # 75-85%
                "Analyzing": (85, 90),   # 85-90%
            }
            
            current_phase = None
            
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                
                # Detect phase changes
                for phase, (start_pct, end_pct) in progress_mapping.items():
                    if phase.lower() in line.lower():
                        current_phase = phase
                        await self.send_progress(
                            "agent_creation",
                            start_pct,
                            f"📊 {phase}...",
                            {"output": line[:100]}
                        )
                        break
                
                # Detect page counts
                if "pages" in line.lower() and current_phase == "Scraping":
                    import re
                    match = re.search(r'(\d+)\s*pages?', line, re.IGNORECASE)
                    if match:
                        pages = int(match.group(1))
                        progress = 10 + (pages / max_pages) * 40  # 10-50%
                        await self.send_progress(
                            "scraping",
                            min(progress, 50),
                            f"🌐 Scraped {pages} pages...",
                            {"pages": pages, "max_pages": max_pages}
                        )
                
                # Detect chunks
                if "chunks" in line.lower() or "embeddings" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s*(chunks?|embeddings?)', line, re.IGNORECASE)
                    if match:
                        chunks = int(match.group(1))
                        await self.send_progress(
                            "embeddings",
                            70,
                            f"🎮 Processing embeddings: {chunks} chunks",
                            {"chunks": chunks}
                        )
        
        # Run monitoring in background
        await monitor_output()
        
        # Wait for completion
        process.wait()
        
        if process.returncode == 0:
            # Find created agent
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            
            agent = self.db.site_agents.find_one(
                {"domain": domain},
                sort=[("created_at", -1)]
            )
            
            return str(agent['_id']) if agent else None
        else:
            stderr = process.stderr.read()
            raise Exception(f"Agent creation failed: {stderr[:200]}")
    
    async def _run_competitive_intelligence(self, agent_id: str):
        """Run competitive intelligence workflow"""
        
        # SERP Discovery (90-93%)
        await self.send_progress(
            "ci_serp",
            90,
            "🔍 Running SERP discovery..."
        )
        
        import subprocess
        try:
            subprocess.run(
                ['python3', '/srv/hf/ai_agents/deepseek_serp_discovery.py', agent_id, '15'],
                check=True,
                timeout=300,
                capture_output=True
            )
            await self.send_progress(
                "ci_serp",
                93,
                "✅ SERP discovery completed"
            )
        except Exception as e:
            await self.send_progress(
                "ci_serp",
                93,
                f"⚠️ SERP discovery failed: {str(e)[:50]}"
            )
        
        # Slave Agents (93-97%)
        await self.send_progress(
            "ci_slaves",
            93,
            "🤖 Creating slave agents..."
        )
        
        try:
            subprocess.run(
                ['python3', '/srv/hf/ai_agents/create_intelligent_slave_agents.py', agent_id, '10', '30.0'],
                check=True,
                timeout=600,
                capture_output=True
            )
            await self.send_progress(
                "ci_slaves",
                97,
                "✅ Slave agents created"
            )
        except Exception as e:
            await self.send_progress(
                "ci_slaves",
                97,
                f"⚠️ Slave creation failed: {str(e)[:50]}"
            )
        
        # Improvement Analysis (97-99%)
        await self.send_progress(
            "ci_analysis",
            97,
            "📊 Running improvement analysis..."
        )
        
        try:
            subprocess.run(
                ['python3', '/srv/hf/ai_agents/master_improvement_analyzer.py', agent_id],
                check=True,
                timeout=300,
                capture_output=True
            )
            await self.send_progress(
                "ci_analysis",
                99,
                "✅ Improvement analysis completed"
            )
        except Exception as e:
            await self.send_progress(
                "ci_analysis",
                99,
                f"⚠️ Analysis failed: {str(e)[:50]}"
            )
        
        # Actionable Plan (99-100%)
        await self.send_progress(
            "ci_actions",
            99,
            "⚡ Generating actionable plan..."
        )
        
        try:
            subprocess.run(
                ['python3', '/srv/hf/ai_agents/action_service.py', agent_id],
                check=True,
                timeout=300,
                capture_output=True
            )
            await self.send_progress(
                "ci_actions",
                100,
                "✅ Actionable plan generated"
            )
        except Exception as e:
            await self.send_progress(
                "ci_actions",
                100,
                f"⚠️ Action plan failed: {str(e)[:50]}"
            )


async def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python create_mega_agent.py <url> [max_pages]")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    creator = MegaAgentCreator()
    agent_id = await creator.create_mega_agent(url, max_pages)
    
    print(f"\n✅ Agent ID: {agent_id}")
    print(f"🔗 Dashboard: http://100.66.157.27:5000/static/competitive_intelligence_dashboard.html?agent={agent_id}")


if __name__ == "__main__":
    asyncio.run(main())

