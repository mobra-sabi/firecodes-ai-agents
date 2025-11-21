#!/usr/bin/env python3
"""
📊 SERP TIMELINE TRACKER - V3.0 Full Implementation

Urmărește evoluția SERP în timp:
- Daily/weekly snapshots
- Ranking history per keyword
- Change detection (new entrants, rank drops/rises)
- Trend analysis (velocity, patterns)

Salvează în MongoDB time-series collections
"""

import os
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
import json
from pymongo import MongoClient
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import SERP search
try:
    from tools.unified_serp_search import brave_search
except:
    logger.warning("⚠️  unified_serp_search not available, using mock")
    def brave_search(query, count=10):
        return []


class SERPTimelineTracker:
    """
    Tracker pentru evoluția SERP în timp
    """
    
    def __init__(self):
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        # Ensure indexes for time-series
        self._ensure_indexes()
        
        logger.info("✅ SERP Timeline Tracker initialized")
    
    def track_keyword(self, keyword: str, agent_id: str = None, save: bool = True) -> Dict:
        """
        Urmărește un keyword și salvează snapshot SERP
        
        Args:
            keyword: Keyword de urmărit
            agent_id: Optional - ID agent pentru tracking
            save: Salvează în MongoDB (default True)
        
        Returns:
            Dict cu snapshot SERP
        """
        logger.info(f"📊 Tracking SERP for keyword: '{keyword}'")
        
        try:
            # Get SERP results
            serp_results = brave_search(keyword, count=20)
            
            # Extract rankings
            rankings = []
            for i, result in enumerate(serp_results, 1):
                domain = self._extract_domain(result.get("url", ""))
                
                rankings.append({
                    "position": i,
                    "domain": domain,
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")[:500]  # Limit snippet
                })
            
            # Create snapshot
            snapshot = {
                "keyword": keyword,
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc),
                "rankings": rankings,
                "top_10_domains": [r["domain"] for r in rankings[:10]],
                "total_results": len(rankings)
            }
            
            # Save snapshot
            if save:
                snapshot_id = self._save_snapshot(snapshot)
                snapshot["_id"] = snapshot_id
                
                # Update ranking history
                self._update_ranking_history(keyword, rankings, agent_id)
                
                # Detect changes
                changes = self._detect_changes(keyword, rankings, agent_id)
                if changes:
                    self._save_changes(keyword, changes, agent_id)
                    logger.info(f"   ⚠️  Detected {len(changes)} changes")
            
            logger.info(f"✅ SERP snapshot complete: {len(rankings)} results")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Error tracking keyword: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def track_keywords_batch(
        self,
        keywords: List[str],
        agent_id: str = None,
        delay: float = 1.0
    ) -> List[Dict]:
        """
        Urmărește multiple keywords în batch cu delay între requests
        
        Args:
            keywords: List de keywords
            agent_id: Optional - ID agent
            delay: Delay între requests (seconds)
        
        Returns:
            List de snapshots
        """
        logger.info(f"📦 Batch tracking {len(keywords)} keywords...")
        
        import time
        snapshots = []
        
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"  [{i}/{len(keywords)}] Tracking: {keyword}")
            
            snapshot = self.track_keyword(keyword, agent_id)
            snapshots.append(snapshot)
            
            # Delay între requests (rate limiting)
            if i < len(keywords):
                time.sleep(delay)
        
        logger.info(f"✅ Batch tracking complete: {len(snapshots)} snapshots")
        
        return snapshots
    
    def get_ranking_history(
        self,
        keyword: str,
        domain: str = None,
        days: int = 30,
        agent_id: str = None
    ) -> Dict:
        """
        Obține istoricul ranking-urilor pentru un keyword
        
        Args:
            keyword: Keyword
            domain: Optional - specific domain to track
            days: Număr zile în urmă
            agent_id: Optional - filter by agent
        
        Returns:
            Dict cu istoric
        """
        logger.info(f"📈 Getting ranking history for '{keyword}' (last {days} days)")
        
        try:
            # Query ranking_history
            query = {"keyword": keyword}
            if agent_id:
                query["agent_id"] = agent_id
            
            history_doc = self.db.ranking_history.find_one(query)
            
            if not history_doc:
                logger.warning(f"   No history found for '{keyword}'")
                return {"keyword": keyword, "history": []}
            
            # Filter by date range
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            history = history_doc.get("history", [])
            filtered_history = [
                h for h in history
                if datetime.fromisoformat(h.get("timestamp", "2020-01-01")) > cutoff_date
            ]
            
            # If domain specified, filter rankings
            if domain:
                for entry in filtered_history:
                    rankings = entry.get("rankings", [])
                    domain_ranking = next(
                        (r for r in rankings if r.get("domain") == domain),
                        None
                    )
                    entry["domain_position"] = domain_ranking.get("position") if domain_ranking else None
            
            logger.info(f"✅ History retrieved: {len(filtered_history)} data points")
            
            return {
                "keyword": keyword,
                "domain": domain,
                "days": days,
                "history": filtered_history,
                "data_points": len(filtered_history)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting history: {e}")
            return {"keyword": keyword, "history": []}
    
    def get_recent_changes(
        self,
        agent_id: str = None,
        days: int = 7,
        change_types: List[str] = None
    ) -> List[Dict]:
        """
        Obține schimbări recente în SERP
        
        Args:
            agent_id: Optional - filter by agent
            days: Număr zile în urmă
            change_types: Optional - filter by type (new_entrant, rank_drop, rank_rise)
        
        Returns:
            List de schimbări
        """
        logger.info(f"🔍 Getting recent changes (last {days} days)...")
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = {
                "timestamp": {"$gte": cutoff_date}
            }
            
            if agent_id:
                query["agent_id"] = agent_id
            
            if change_types:
                query["change_type"] = {"$in": change_types}
            
            changes = list(self.db.serp_changes_log.find(query).sort("timestamp", -1).limit(100))
            
            logger.info(f"✅ Found {len(changes)} recent changes")
            
            return changes
            
        except Exception as e:
            logger.error(f"❌ Error getting changes: {e}")
            return []
    
    def analyze_trends(
        self,
        keyword: str,
        domain: str = None,
        days: int = 30
    ) -> Dict:
        """
        Analizează trend-uri pentru un keyword
        
        Args:
            keyword: Keyword de analizat
            domain: Optional - specific domain
            days: Perioadă de analiză
        
        Returns:
            Dict cu analiză trend-uri
        """
        logger.info(f"📊 Analyzing trends for '{keyword}' (last {days} days)")
        
        try:
            # Get history
            history_data = self.get_ranking_history(keyword, domain, days)
            history = history_data.get("history", [])
            
            if len(history) < 2:
                logger.warning(f"   Insufficient data for trend analysis")
                return {
                    "keyword": keyword,
                    "trend": "insufficient_data",
                    "confidence": 0.0
                }
            
            # Calculate trends
            positions = []
            timestamps = []
            
            for entry in history:
                if domain:
                    pos = entry.get("domain_position")
                else:
                    # Average position across all tracked domains
                    rankings = entry.get("rankings", [])
                    if rankings:
                        pos = sum(r.get("position", 100) for r in rankings[:10]) / len(rankings[:10])
                    else:
                        pos = None
                
                if pos:
                    positions.append(pos)
                    timestamps.append(datetime.fromisoformat(entry.get("timestamp")))
            
            if len(positions) < 2:
                return {
                    "keyword": keyword,
                    "trend": "insufficient_data",
                    "confidence": 0.0
                }
            
            # Calculate velocity (change per day)
            time_span = (timestamps[-1] - timestamps[0]).days
            position_change = positions[-1] - positions[0]
            
            if time_span > 0:
                velocity = position_change / time_span
            else:
                velocity = 0.0
            
            # Determine trend
            if velocity < -0.5:  # Improving (lower position = better)
                trend = "rising"
                strength = min(abs(velocity), 5.0) / 5.0
            elif velocity > 0.5:  # Declining
                trend = "falling"
                strength = min(abs(velocity), 5.0) / 5.0
            else:
                trend = "stable"
                strength = 1.0 - min(abs(velocity), 0.5) / 0.5
            
            # Volatility
            if len(positions) >= 3:
                volatility = sum(abs(positions[i] - positions[i-1]) for i in range(1, len(positions))) / (len(positions) - 1)
            else:
                volatility = 0.0
            
            analysis = {
                "keyword": keyword,
                "domain": domain,
                "trend": trend,
                "velocity": velocity,  # positions/day
                "strength": strength,  # 0-1
                "volatility": volatility,
                "current_position": positions[-1] if positions else None,
                "position_30d_ago": positions[0] if positions else None,
                "data_points": len(positions),
                "time_span_days": time_span
            }
            
            logger.info(f"✅ Trend analysis complete: {trend} (velocity: {velocity:.2f})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing trends: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _extract_domain(self, url: str) -> str:
        """
        Extrage domain din URL
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except:
            return ""
    
    def _save_snapshot(self, snapshot: Dict) -> str:
        """
        Salvează snapshot în MongoDB
        """
        try:
            result = self.db.serp_snapshots.insert_one(snapshot)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return ""
    
    def _update_ranking_history(self, keyword: str, rankings: List[Dict], agent_id: str = None):
        """
        Update ranking history cu nou snapshot
        """
        try:
            history_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rankings": rankings[:20]  # Top 20
            }
            
            query = {"keyword": keyword}
            if agent_id:
                query["agent_id"] = agent_id
            
            self.db.ranking_history.update_one(
                query,
                {
                    "$push": {"history": history_entry},
                    "$set": {
                        "last_updated": datetime.now(timezone.utc),
                        "keyword": keyword,
                        "agent_id": agent_id
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to update history: {e}")
    
    def _detect_changes(self, keyword: str, current_rankings: List[Dict], agent_id: str = None) -> List[Dict]:
        """
        Detectează schimbări vs snapshot anterior
        """
        try:
            # Get last snapshot
            query = {"keyword": keyword}
            if agent_id:
                query["agent_id"] = agent_id
            
            last_snapshot = self.db.serp_snapshots.find_one(
                query,
                sort=[("timestamp", -1)],
                skip=1  # Skip current snapshot
            )
            
            if not last_snapshot:
                return []
            
            last_rankings = last_snapshot.get("rankings", [])
            
            # Build domain -> position maps
            current_map = {r["domain"]: r["position"] for r in current_rankings}
            last_map = {r["domain"]: r["position"] for r in last_rankings}
            
            changes = []
            
            # Check for new entrants (în top 10)
            for domain in current_map:
                if domain not in last_map and current_map[domain] <= 10:
                    changes.append({
                        "change_type": "new_entrant",
                        "domain": domain,
                        "position": current_map[domain]
                    })
            
            # Check for rank changes
            for domain in current_map:
                if domain in last_map:
                    position_change = last_map[domain] - current_map[domain]
                    
                    # Significant rise (improved by 3+ positions)
                    if position_change >= 3:
                        changes.append({
                            "change_type": "rank_rise",
                            "domain": domain,
                            "old_position": last_map[domain],
                            "new_position": current_map[domain],
                            "change": position_change
                        })
                    
                    # Significant drop (declined by 3+ positions)
                    elif position_change <= -3:
                        changes.append({
                            "change_type": "rank_drop",
                            "domain": domain,
                            "old_position": last_map[domain],
                            "new_position": current_map[domain],
                            "change": position_change
                        })
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return []
    
    def _save_changes(self, keyword: str, changes: List[Dict], agent_id: str = None):
        """
        Salvează schimbări detectate
        """
        try:
            for change in changes:
                self.db.serp_changes_log.insert_one({
                    "keyword": keyword,
                    "agent_id": agent_id,
                    "timestamp": datetime.now(timezone.utc),
                    "change_type": change.get("change_type"),
                    "domain": change.get("domain"),
                    "details": change
                })
        except Exception as e:
            logger.error(f"Failed to save changes: {e}")
    
    def _ensure_indexes(self):
        """
        Ensure MongoDB indexes pentru performance
        """
        try:
            # serp_snapshots indexes
            self.db.serp_snapshots.create_index([("keyword", 1), ("timestamp", -1)])
            self.db.serp_snapshots.create_index([("agent_id", 1), ("timestamp", -1)])
            
            # ranking_history indexes
            self.db.ranking_history.create_index([("keyword", 1)])
            self.db.ranking_history.create_index([("agent_id", 1)])
            
            # serp_changes_log indexes
            self.db.serp_changes_log.create_index([("keyword", 1), ("timestamp", -1)])
            self.db.serp_changes_log.create_index([("agent_id", 1), ("timestamp", -1)])
            self.db.serp_changes_log.create_index([("change_type", 1)])
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")


# Test
if __name__ == "__main__":
    tracker = SERPTimelineTracker()
    
    print("="*80)
    print("🧪 TESTING SERP TIMELINE TRACKER")
    print("="*80)
    
    # Test 1: Track single keyword
    print("\n📊 Test 1: Tracking keyword...")
    snapshot = tracker.track_keyword("protectie la foc", agent_id="test_agent")
    
    if snapshot:
        print(f"✅ Snapshot captured!")
        print(f"   Total results: {snapshot.get('total_results', 0)}")
        print(f"   Top 3 domains: {snapshot.get('top_10_domains', [])[:3]}")
    
    # Test 2: Analyze trends (will have limited data initially)
    print("\n📊 Test 2: Analyzing trends...")
    trends = tracker.analyze_trends("protectie la foc", days=7)
    
    if trends:
        print(f"✅ Trend analysis complete!")
        print(f"   Trend: {trends.get('trend', 'N/A')}")
        print(f"   Velocity: {trends.get('velocity', 0):.2f} positions/day")
        print(f"   Data points: {trends.get('data_points', 0)}")
    
    # Test 3: Get recent changes
    print("\n🔍 Test 3: Getting recent changes...")
    changes = tracker.get_recent_changes(days=7)
    
    print(f"✅ Found {len(changes)} recent changes")
    
    print("\n✨ SERP Timeline Tracker ready!")

