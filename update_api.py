import sys

new_code = '''@app.get("/api/crawler/stats")
async def get_crawler_stats():
    """Returnează statisticile live ale crawler-ului, inclusiv activitate recentă"""
    try:
        # Conectare la ro_index_db pe portul 27018
        from config.database_config import MONGODB_URI
        from pymongo import MongoClient, DESCENDING, ASCENDING
        client_crawler = MongoClient(MONGODB_URI)
        db_crawler = client_crawler["ro_index_db"]
        
        # Basic Counts
        stats = {
            "completed": db_crawler.crawl_queue.count_documents({"status": "completed"}),
            "pending": db_crawler.crawl_queue.count_documents({"status": "pending"}),
            "failed": db_crawler.crawl_queue.count_documents({"status": "failed"}),
            "scraped_sites": db_crawler.crawled_sites.count_documents({}),
            "workers_active": 8
        }

        # Start Time & Duration
        first_entry = db_crawler.crawl_queue.find_one({}, sort=[("added_at", ASCENDING)])
        stats["started_at"] = first_entry["added_at"].isoformat() if first_entry and "added_at" in first_entry else None
        
        # Data Volume (Approximate)
        stats["estimated_data_size_gb"] = round((stats["completed"] * 0.0001), 2)

        # Recent Scraped Sites (Ce a strans pana acum)
        recent_cursor = db_crawler.crawled_sites.find({}, {"domain": 1, "title": 1, "scraped_at": 1}).sort("scraped_at", DESCENDING).limit(7)
        stats["recent_sites"] = []
        for site in recent_cursor:
            stats["recent_sites"].append({
                "domain": site.get("domain"),
                "title": (site.get("title") or "No Title")[:50],
                "time": site.get("scraped_at").isoformat() if site.get("scraped_at") else None
            })

        # Next in Queue (Ce urmeaza)
        next_cursor = db_crawler.crawl_queue.find({"status": "pending"}, {"url": 1, "domain": 1}).limit(7)
        stats["next_queue"] = []
        for item in next_cursor:
            stats["next_queue"].append({
                "url": item.get("url"),
                "domain": item.get("domain")
            })

        client_crawler.close()
        return {"ok": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting crawler stats: {e}")
        return {"ok": False, "error": str(e)}
'''

with open("agent_api.py", "r") as f:
    content = f.read()

# Old code block to identify
old_code_start = '@app.get("/api/crawler/stats")'
old_code_end_marker = 'logger.error(f"Error getting crawler stats: {e}")'

if old_code_start in content:
    parts = content.split(old_code_start)
    pre_part = parts[0]
    post_part_initial = parts[1]
    
    # Find end of function
    if old_code_end_marker in post_part_initial:
        split_post = post_part_initial.split(old_code_end_marker, 1)
        post_part = split_post[1]
        
        # Check if there is a return line after logger error in old code (it wasn't in cat output but might be)
        # In the cat output it ended at logger.error line.
        # The replacement code includes the exception return.
        
        # Reconstruct
        new_content = pre_part + new_code + post_part
        
        with open("agent_api.py", "w") as f:
            f.write(new_content)
        print("API updated successfully")
    else:
        print("Could not find end of function block")
else:
    print("Could not find start of function block")
