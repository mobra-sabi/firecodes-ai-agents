#!/usr/bin/env python3
"""
📊 MongoDB Schemas pentru SERP Monitoring
Production-ready collections cu indexuri optimizate
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class SERPMongoDBSchemas:
    """
    Manager pentru MongoDB collections SERP
    
    Collections:
    1. serp_runs - Log pentru fiecare rulare SERP
    2. serp_results - Rezultate SERP (o intrare / keyword / data / poziție)
    3. competitors - Competitori unificați pe domeniu
    4. ranks_history - Istoric poziții (master + competitori)
    5. serp_alerts - Alerte automate (rank drops, new competitors, etc.)
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "ai_agents_db"):
        """
        Initialize MongoDB schemas manager
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.logger = logging.getLogger(f"{__name__}.SERPMongoDBSchemas")
    
    def create_all_indexes(self):
        """Creează toate indexurile pentru collections SERP"""
        self.logger.info("Creating MongoDB indexes for SERP collections...")
        
        self.create_serp_runs_indexes()
        self.create_serp_results_indexes()
        self.create_competitors_indexes()
        self.create_ranks_history_indexes()
        self.create_serp_alerts_indexes()
        
        self.logger.info("✅ All SERP indexes created successfully")
    
    def create_serp_runs_indexes(self):
        """Indexuri pentru collection: serp_runs"""
        collection = self.db.serp_runs
        
        # Index principal: agent_id + started_at (pentru queries frecvente)
        collection.create_index([
            ("agent_id", ASCENDING),
            ("started_at", DESCENDING)
        ], name="idx_agent_date")
        
        # Index pentru status (pentru monitoring)
        collection.create_index([("status", ASCENDING)], name="idx_status")
        
        # Index pentru finished_at (pentru queries temporale)
        collection.create_index([("finished_at", DESCENDING)], name="idx_finished")
        
        self.logger.info("✅ serp_runs indexes created")
    
    def create_serp_results_indexes(self):
        """Indexuri pentru collection: serp_results"""
        collection = self.db.serp_results
        
        # Index compus: agent_id + keyword + date (query foarte frecvent)
        collection.create_index([
            ("agent_id", ASCENDING),
            ("keyword", ASCENDING),
            ("date", DESCENDING)
        ], name="idx_agent_keyword_date")
        
        # Index pentru run_id (pentru agregări per run)
        collection.create_index([("run_id", ASCENDING)], name="idx_run_id")
        
        # Index pentru domain (pentru queries per competitor)
        collection.create_index([
            ("domain", ASCENDING),
            ("date", DESCENDING)
        ], name="idx_domain_date")
        
        # Index pentru rank (pentru top N queries)
        collection.create_index([
            ("agent_id", ASCENDING),
            ("rank", ASCENDING)
        ], name="idx_agent_rank")
        
        # Unique index pentru deduplicare
        collection.create_index([
            ("agent_id", ASCENDING),
            ("keyword", ASCENDING),
            ("domain", ASCENDING),
            ("date", ASCENDING)
        ], unique=True, name="idx_unique_result")
        
        self.logger.info("✅ serp_results indexes created")
    
    def create_competitors_indexes(self):
        """Indexuri pentru collection: competitors"""
        collection = self.db.competitors
        
        # Index principal: domain (folosit ca _id, dar și pentru queries)
        collection.create_index([("domain", ASCENDING)], unique=True, name="idx_domain")
        
        # Index pentru agent_slave_id (pentru linking master-slave)
        collection.create_index([("agent_slave_id", ASCENDING)], name="idx_slave_id")
        
        # Index pentru threat score (pentru top N queries)
        collection.create_index([("scores.threat", DESCENDING)], name="idx_threat_score")
        
        # Index pentru keywords_seen (pentru overlap analysis)
        collection.create_index([("keywords_seen", ASCENDING)], name="idx_keywords_seen")
        
        self.logger.info("✅ competitors indexes created")
    
    def create_ranks_history_indexes(self):
        """Indexuri pentru collection: ranks_history"""
        collection = self.db.ranks_history
        
        # Index compus: domain + keyword (query principal)
        collection.create_index([
            ("domain", ASCENDING),
            ("keyword", ASCENDING)
        ], unique=True, name="idx_domain_keyword")
        
        # Index pentru series.date (pentru queries temporale)
        collection.create_index([("series.date", DESCENDING)], name="idx_series_date")
        
        # Index pentru current_rank (pentru monitoring)
        collection.create_index([
            ("domain", ASCENDING),
            ("current_rank", ASCENDING)
        ], name="idx_domain_current_rank")
        
        self.logger.info("✅ ranks_history indexes created")
    
    def create_serp_alerts_indexes(self):
        """Indexuri pentru collection: serp_alerts"""
        collection = self.db.serp_alerts
        
        # Index principal: agent_id + date + severity
        collection.create_index([
            ("agent_id", ASCENDING),
            ("date", DESCENDING),
            ("severity", ASCENDING)
        ], name="idx_agent_date_severity")
        
        # Index pentru acknowledged (pentru dashboard)
        collection.create_index([
            ("agent_id", ASCENDING),
            ("acknowledged", ASCENDING)
        ], name="idx_agent_acknowledged")
        
        # Index pentru alert_type
        collection.create_index([("alert_type", ASCENDING)], name="idx_alert_type")
        
        # Index pentru run_id
        collection.create_index([("run_id", ASCENDING)], name="idx_run_id")
        
        self.logger.info("✅ serp_alerts indexes created")
    
    def insert_serp_run(
        self,
        agent_id: str,
        keywords: list,
        market: str = "ro",
        provider: str = "brave"
    ) -> str:
        """
        Creează un nou SERP run
        
        Args:
            agent_id: ID agent master
            keywords: Lista keywords de căutat
            market: Piață (ro, us, uk, etc.)
            provider: Provider SERP (brave, serpapi, custom)
        
        Returns:
            run_id generat
        """
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}"
        
        doc = {
            "_id": run_id,
            "agent_id": agent_id,
            "keywords": keywords,
            "market": market,
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "provider": provider,
            "status": "running",
            "stats": {
                "queries": 0,
                "pages_fetched": 0,
                "errors": 0,
                "total_results": 0,
                "unique_domains": 0
            }
        }
        
        self.db.serp_runs.insert_one(doc)
        self.logger.info(f"✅ Created SERP run: {run_id} for agent {agent_id}")
        
        return run_id
    
    def update_serp_run_status(
        self,
        run_id: str,
        status: str,
        stats: dict = None
    ):
        """
        Update status pentru SERP run
        
        Args:
            run_id: ID run
            status: Status nou (running, succeeded, failed, partial)
            stats: Stats updatate (opțional)
        """
        update_doc = {
            "status": status,
            "finished_at": datetime.now(timezone.utc)
        }
        
        if stats:
            update_doc["stats"] = stats
        
        self.db.serp_runs.update_one(
            {"_id": run_id},
            {"$set": update_doc}
        )
        
        self.logger.info(f"✅ Updated SERP run {run_id}: status={status}")
    
    def insert_serp_result(
        self,
        run_id: str,
        agent_id: str,
        keyword: str,
        rank: int,
        url: str,
        domain: str,
        title: str = "",
        snippet: str = "",
        result_type: str = "organic",
        page: int = 1
    ):
        """
        Inserează un rezultat SERP
        
        Args:
            run_id: ID run
            agent_id: ID agent
            keyword: Keyword căutat
            rank: Poziție în SERP
            url: URL rezultat
            domain: Domeniu canonicalizat
            title: Titlu rezultat
            snippet: Snippet rezultat
            result_type: Tip rezultat (organic, ad, featured_snippet, map)
            page: Pagina SERP
        """
        date = datetime.now(timezone.utc).date()
        # Use run_id + rank for unique _id (permite multiple runs per zi)
        result_id = f"serp:{run_id}:{keyword}:{rank}"
        
        doc = {
            "_id": result_id,
            "agent_id": agent_id,
            "keyword": keyword,
            "date": date.isoformat(),
            "rank": rank,
            "url": url,
            "domain": domain,
            "title": title,
            "snippet": snippet,
            "type": result_type,
            "page": page,
            "run_id": run_id,
            "crawled_at": datetime.now(timezone.utc)
        }
        
        # Upsert (evită duplicate errors)
        self.db.serp_results.update_one(
            {"_id": result_id},
            {"$set": doc},
            upsert=True
        )
    
    def upsert_competitor(
        self,
        domain: str,
        keywords_seen: list,
        scores: dict,
        agent_slave_id: str = None
    ):
        """
        Creează sau update competitor
        
        Args:
            domain: Domeniu competitor
            keywords_seen: Lista keywords unde apare
            scores: Dict cu visibility, authority, threat
            agent_slave_id: ID slave agent (opțional)
        """
        now = datetime.now(timezone.utc).date()
        
        # Update sau insert
        existing = self.db.competitors.find_one({"_id": domain})
        
        if existing:
            # Update
            self.db.competitors.update_one(
                {"_id": domain},
                {
                    "$set": {
                        "last_seen": now.isoformat(),
                        "scores": scores,
                        "agent_slave_id": agent_slave_id
                    },
                    "$addToSet": {
                        "keywords_seen": {"$each": keywords_seen}
                    },
                    "$inc": {
                        "appearances_count": 1
                    }
                }
            )
        else:
            # Insert
            doc = {
                "_id": domain,
                "domain": domain,
                "first_seen": now.isoformat(),
                "last_seen": now.isoformat(),
                "keywords_seen": keywords_seen,
                "appearances_count": 1,
                "agent_slave_id": agent_slave_id,
                "scores": scores,
                "notes": ""
            }
            self.db.competitors.insert_one(doc)
    
    def update_rank_history(
        self,
        domain: str,
        keyword: str,
        rank: int,
        run_id: str
    ):
        """
        Update rank history pentru un domeniu + keyword
        
        Args:
            domain: Domeniu (master sau competitor)
            keyword: Keyword
            rank: Poziție curentă
            run_id: ID run
        """
        date = datetime.now(timezone.utc).date().isoformat()
        history_id = f"rank:{domain}:{keyword}"
        
        # Update history
        self.db.ranks_history.update_one(
            {"_id": history_id},
            {
                "$set": {
                    "domain": domain,
                    "keyword": keyword,
                    "current_rank": rank,
                    "last_updated": datetime.now(timezone.utc)
                },
                "$push": {
                    "series": {
                        "date": date,
                        "rank": rank,
                        "run_id": run_id
                    }
                },
                "$min": {"best_rank_ever": rank},
                "$max": {"worst_rank_ever": rank}
            },
            upsert=True
        )
    
    def create_alert(
        self,
        agent_id: str,
        run_id: str,
        alert_type: str,
        severity: str,
        keyword: str,
        details: dict,
        actions_suggested: list = None
    ) -> str:
        """
        Creează o alertă SERP
        
        Args:
            agent_id: ID agent
            run_id: ID run
            alert_type: Tip alertă (rank_drop, rank_gain, new_competitor, etc.)
            severity: Severitate (critical, warning, info)
            keyword: Keyword afectat
            details: Detalii alertă (dict cu previous_rank, current_rank, etc.)
            actions_suggested: Lista acțiuni sugerate
        
        Returns:
            alert_id generat
        """
        doc = {
            "agent_id": agent_id,
            "run_id": run_id,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "keyword": keyword,
            "details": details,
            "actions_suggested": actions_suggested or [],
            "action_taken": None,
            "notified_at": datetime.now(timezone.utc),
            "acknowledged": False
        }
        
        result = self.db.serp_alerts.insert_one(doc)
        return str(result.inserted_id)


# Test & Setup
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("="*80)
    print("📊 MongoDB SERP Schemas - Setup & Test")
    print("="*80)
    print()
    
    # Initialize
    schemas = SERPMongoDBSchemas()
    
    # Create all indexes
    print("Creating indexes...")
    schemas.create_all_indexes()
    print()
    
    # Test: Create a SERP run
    print("Test: Create SERP run")
    run_id = schemas.insert_serp_run(
        agent_id="protectiilafoc.ro",
        keywords=["vopsea intumescenta", "protectie pasiva la foc"],
        market="ro",
        provider="brave"
    )
    print(f"   Created run_id: {run_id}")
    print()
    
    # Test: Insert SERP results
    print("Test: Insert SERP results")
    schemas.insert_serp_result(
        run_id=run_id,
        agent_id="protectiilafoc.ro",
        keyword="vopsea intumescenta",
        rank=1,
        url="https://www.promat.com/ro-ro/vopsea",
        domain="promat.com",
        title="Vopsea intumescenta - Promat",
        snippet="Oferim vopsea intumescenta...",
        result_type="organic"
    )
    print("   ✅ Inserted 1 SERP result")
    print()
    
    # Test: Upsert competitor
    print("Test: Upsert competitor")
    schemas.upsert_competitor(
        domain="promat.com",
        keywords_seen=["vopsea intumescenta"],
        scores={
            "visibility": 0.85,
            "authority": 0.62,
            "threat": 78.5
        }
    )
    print("   ✅ Upserted competitor: promat.com")
    print()
    
    # Test: Update rank history
    print("Test: Update rank history")
    schemas.update_rank_history(
        domain="protectiilafoc.ro",
        keyword="vopsea intumescenta",
        rank=3,
        run_id=run_id
    )
    print("   ✅ Updated rank history: protectiilafoc.ro - rank 3")
    print()
    
    # Test: Create alert
    print("Test: Create alert")
    alert_id = schemas.create_alert(
        agent_id="protectiilafoc.ro",
        run_id=run_id,
        alert_type="rank_drop",
        severity="warning",
        keyword="vopsea intumescenta",
        details={
            "previous_rank": 2,
            "current_rank": 3,
            "delta": -1
        },
        actions_suggested=["Re-optimize page", "Check technical SEO"]
    )
    print(f"   ✅ Created alert: {alert_id}")
    print()
    
    # Update run status
    print("Test: Update run status")
    schemas.update_serp_run_status(
        run_id=run_id,
        status="succeeded",
        stats={
            "queries": 2,
            "pages_fetched": 2,
            "errors": 0,
            "total_results": 20,
            "unique_domains": 15
        }
    )
    print("   ✅ Updated run status: succeeded")
    print()
    
    print("="*80)
    print("✅ Setup & Test Complete!")
    print("="*80)
    print()
    print("Collections created:")
    print("   • serp_runs")
    print("   • serp_results")
    print("   • competitors")
    print("   • ranks_history")
    print("   • serp_alerts")
    print()
    print("All indexes created successfully!")

