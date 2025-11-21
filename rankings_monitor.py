"""
Rankings Monitor - Monitorizare constantă poziții Google
"""
import os
from datetime import datetime, timezone
from typing import Dict, List
from pymongo import MongoClient
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RankingsMonitor:
    """Monitorizare continuă poziții Google pentru master agents"""
    
    def __init__(self):
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["ai_agents_db"]  # FIX: Use ai_agents_db (REAL data!)
        self.site_agents = self.db["site_agents"]
        self.rankings_history = self.db["rankings_history"]
        self.serp_results = self.db["serp_results"]
    
    def calculate_agent_statistics(self, agent_id: str) -> Dict:
        """
        Calculează statistici complete pentru un agent
        
        Returns:
            {
                "total_keywords": 25,
                "total_serp_results": 500,
                "unique_competitors": 22,
                "master_positions": {
                    "top_3": 5,
                    "top_10": 12,
                    "top_20": 18,
                    "not_in_top_20": 7
                },
                "average_position": 8.4,
                "keywords_detail": [...]
            }
        """
        try:
            agent_id_obj = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
            
            # 1. Găsește toate keywords pentru acest agent
            agent = self.site_agents.find_one({"_id": agent_id_obj})
            if not agent:
                return {"error": "Agent not found"}
            
            master_domain = agent.get("domain", "").replace("https://", "").replace("http://", "").rstrip("/")
            
            # 2. Găsește toate rezultatele SERP
            serp_results = list(self.serp_results.find({"master_agent_id": str(agent_id)}))
            
            if not serp_results:
                return {
                    "total_keywords": 0,
                    "total_serp_results": 0,
                    "unique_competitors": 0,
                    "master_positions": {"top_3": 0, "top_10": 0, "top_20": 0, "not_in_top_20": 0},
                    "average_position": None,
                    "keywords_detail": []
                }
            
            # 3. Calculează statistici
            total_keywords = len(serp_results)
            total_serp_results = sum(len(sr.get("results", [])) for sr in serp_results)
            
            # 4. Găsește competitori unici
            all_domains = set()
            for sr in serp_results:
                for result in sr.get("results", []):
                    domain = result.get("url", "").replace("https://", "").replace("http://", "").split("/")[0]
                    if domain and domain != master_domain:
                        all_domains.add(domain)
            
            unique_competitors = len(all_domains)
            
            # 5. Poziții master agent
            positions = {
                "top_3": 0,
                "top_10": 0,
                "top_20": 0,
                "not_in_top_20": 0
            }
            
            all_positions = []
            keywords_detail = []
            
            for sr in serp_results:
                keyword = sr.get("keyword", "")
                results = sr.get("results", [])
                
                # Găsește poziția master-ului
                master_position = None
                for i, result in enumerate(results, 1):
                    domain = result.get("url", "").replace("https://", "").replace("http://", "").split("/")[0]
                    if master_domain in domain or domain in master_domain:
                        master_position = i
                        all_positions.append(i)
                        break
                
                # Clasifică poziția
                if master_position:
                    if master_position <= 3:
                        positions["top_3"] += 1
                    if master_position <= 10:
                        positions["top_10"] += 1
                    if master_position <= 20:
                        positions["top_20"] += 1
                else:
                    positions["not_in_top_20"] += 1
                
                # Adaugă la detalii
                keywords_detail.append({
                    "keyword": keyword,
                    "position": master_position,
                    "total_results": len(results),
                    "subdomain": sr.get("subdomain", "N/A"),
                    "timestamp": sr.get("timestamp", datetime.now(timezone.utc))
                })
            
            # 6. Calculează poziție medie (doar pentru keywords unde suntem în top 20)
            average_position = sum(all_positions) / len(all_positions) if all_positions else None
            
            return {
                "total_keywords": total_keywords,
                "total_serp_results": total_serp_results,
                "unique_competitors": unique_competitors,
                "deduplication_rate": round((1 - unique_competitors / max(total_serp_results, 1)) * 100, 1),
                "master_positions": positions,
                "average_position": round(average_position, 1) if average_position else None,
                "keywords_detail": keywords_detail,
                "calculation": {
                    "formula": f"{total_keywords} keywords × 20 results = {total_keywords * 20} potential",
                    "after_dedup": f"{total_keywords * 20} potential → {unique_competitors} unique agents",
                    "reduction": f"{round((1 - unique_competitors / max(total_keywords * 20, 1)) * 100, 1)}%"
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {"error": str(e)}
    
    def save_snapshot(self, agent_id: str) -> str:
        """
        Salvează un snapshot al poziției curente în istoric
        pentru tracking de-a lungul timpului
        """
        try:
            stats = self.calculate_agent_statistics(agent_id)
            
            if "error" in stats:
                return None
            
            snapshot = {
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc),
                "statistics": stats,
                "type": "scheduled_snapshot"
            }
            
            result = self.rankings_history.insert_one(snapshot)
            logger.info(f"✅ Snapshot saved for agent {agent_id}: {result.inserted_id}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            return None
    
    def get_rankings_trend(self, agent_id: str, days: int = 30) -> Dict:
        """
        Obține trendul de poziții pentru ultimele N zile
        
        Returns:
            {
                "snapshots": [...],
                "trend": "improving" | "stable" | "declining",
                "average_position_change": +2.3,
                "keywords_gained_top_10": 5,
                "keywords_lost_top_10": 2
            }
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            snapshots = list(
                self.rankings_history.find({
                    "agent_id": agent_id,
                    "timestamp": {"$gte": cutoff_date}
                }).sort("timestamp", 1)
            )
            
            if len(snapshots) < 2:
                return {
                    "snapshots": snapshots,
                    "trend": "insufficient_data",
                    "message": "Need at least 2 snapshots to calculate trend"
                }
            
            # Calculează trend
            first = snapshots[0]["statistics"]
            last = snapshots[-1]["statistics"]
            
            first_avg = first.get("average_position")
            last_avg = last.get("average_position")
            
            if first_avg and last_avg:
                avg_change = first_avg - last_avg  # Pozitiv = îmbunătățire (poziție mai mică)
                
                if avg_change > 1:
                    trend = "improving"
                elif avg_change < -1:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "unknown"
                avg_change = None
            
            # Câte keywords au intrat/ieșit din top 10
            first_top10 = first.get("master_positions", {}).get("top_10", 0)
            last_top10 = last.get("master_positions", {}).get("top_10", 0)
            
            keywords_gained = max(0, last_top10 - first_top10)
            keywords_lost = max(0, first_top10 - last_top10)
            
            return {
                "snapshots": snapshots,
                "trend": trend,
                "average_position_change": round(avg_change, 1) if avg_change else None,
                "keywords_gained_top_10": keywords_gained,
                "keywords_lost_top_10": keywords_lost,
                "first_snapshot": snapshots[0]["timestamp"],
                "last_snapshot": snapshots[-1]["timestamp"],
                "total_snapshots": len(snapshots)
            }
            
        except Exception as e:
            logger.error(f"Error getting trend: {e}")
            return {"error": str(e)}
    
    def get_competitor_leaderboard(self, agent_id: str) -> List[Dict]:
        """
        Obține un leaderboard cu toți competitorii și câte ori apar în top 10
        """
        try:
            serp_results = list(self.serp_results.find({"master_agent_id": str(agent_id)}))
            
            competitor_stats = {}
            
            for sr in serp_results:
                for i, result in enumerate(sr.get("results", [])[:10], 1):  # Doar top 10
                    domain = result.get("url", "").replace("https://", "").replace("http://", "").split("/")[0]
                    
                    if domain not in competitor_stats:
                        competitor_stats[domain] = {
                            "domain": domain,
                            "appearances_top_10": 0,
                            "total_appearances": 0,
                            "average_position": [],
                            "keywords": []
                        }
                    
                    competitor_stats[domain]["appearances_top_10"] += 1
                    competitor_stats[domain]["total_appearances"] += 1
                    competitor_stats[domain]["average_position"].append(i)
                    competitor_stats[domain]["keywords"].append(sr.get("keyword"))
            
            # Calculează average position
            for domain, stats in competitor_stats.items():
                stats["average_position"] = round(
                    sum(stats["average_position"]) / len(stats["average_position"]), 1
                )
            
            # Sortează după appearances_top_10
            leaderboard = sorted(
                competitor_stats.values(),
                key=lambda x: x["appearances_top_10"],
                reverse=True
            )
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []


def monitor_all_agents():
    """Monitorizează toți agenții activi și salvează snapshots"""
    monitor = RankingsMonitor()
    
    # Găsește toți master agents cu serp_results
    agents = monitor.site_agents.find({"status": "active"})
    
    for agent in agents:
        agent_id = str(agent["_id"])
        logger.info(f"📊 Monitoring agent: {agent.get('domain')} ({agent_id})")
        
        # Salvează snapshot
        snapshot_id = monitor.save_snapshot(agent_id)
        
        if snapshot_id:
            # Afișează statistici
            stats = monitor.calculate_agent_statistics(agent_id)
            logger.info(f"   Keywords: {stats['total_keywords']}")
            logger.info(f"   Unique Competitors: {stats['unique_competitors']}")
            logger.info(f"   Top 10 positions: {stats['master_positions']['top_10']}")
            logger.info(f"   Average position: {stats.get('average_position', 'N/A')}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        agent_id = sys.argv[1]
        
        monitor = RankingsMonitor()
        
        print("\n" + "="*80)
        print(f"📊 RANKINGS STATISTICS - Agent {agent_id}")
        print("="*80 + "\n")
        
        stats = monitor.calculate_agent_statistics(agent_id)
        
        if "error" in stats:
            print(f"❌ Error: {stats['error']}")
        else:
            print(f"📈 CALCUL MATEMATIC:")
            print(f"   {stats['calculation']['formula']}")
            print(f"   {stats['calculation']['after_dedup']}")
            print(f"   Reducere: {stats['calculation']['reduction']}")
            print()
            print(f"📊 STATISTICI:")
            print(f"   Total Keywords: {stats['total_keywords']}")
            print(f"   Total SERP Results: {stats['total_serp_results']}")
            print(f"   Unique Competitors: {stats['unique_competitors']}")
            print(f"   Deduplication Rate: {stats['deduplication_rate']}%")
            print()
            print(f"🎯 POZIȚII MASTER AGENT:")
            print(f"   Top 3: {stats['master_positions']['top_3']} keywords")
            print(f"   Top 10: {stats['master_positions']['top_10']} keywords")
            print(f"   Top 20: {stats['master_positions']['top_20']} keywords")
            print(f"   Not in Top 20: {stats['master_positions']['not_in_top_20']} keywords")
            print()
            if stats.get('average_position'):
                print(f"   📊 Average Position: #{stats['average_position']}")
            print()
            
            # Leaderboard
            print("🏆 COMPETITOR LEADERBOARD:")
            leaderboard = monitor.get_competitor_leaderboard(agent_id)
            for i, comp in enumerate(leaderboard[:10], 1):
                print(f"   {i}. {comp['domain']}")
                print(f"      Appearances in Top 10: {comp['appearances_top_10']}")
                print(f"      Average Position: #{comp['average_position']}")
            
            print("\n" + "="*80)
    else:
        print("📊 Monitoring all active agents...")
        monitor_all_agents()

