"""
Learning Scheduler - Background task to process actions for learning
"""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient

from learning_pipeline import get_learning_pipeline

logger = logging.getLogger(__name__)


class LearningScheduler:
    """
    Scheduler that periodically processes actions for learning
    """
    
    def __init__(self, mongo_client: MongoClient, qdrant_client=None, interval_minutes: int = 5):
        self.mongo = mongo_client
        self.qdrant = qdrant_client
        self.interval_minutes = interval_minutes
        self.scheduler = BackgroundScheduler()
        self.learning_pipeline = get_learning_pipeline(mongo_client, qdrant_client)
        
        logger.info(f"✅ Learning Scheduler initialized (interval: {interval_minutes} minutes)")
    
    def start(self):
        """Start the scheduler"""
        try:
            # Process actions every N minutes
            self.scheduler.add_job(
                self._process_actions,
                'interval',
                minutes=self.interval_minutes,
                id='process_actions_for_learning',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("✅ Learning Scheduler started")
        except Exception as e:
            logger.error(f"❌ Error starting scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("✅ Learning Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")
    
    def _process_actions(self):
        """Process actions for learning"""
        try:
            logger.info("🔄 Processing actions for learning...")
            processed = self.learning_pipeline.process_actions_batch(limit=100)
            logger.info(f"✅ Processed {processed} actions for learning")
        except Exception as e:
            logger.error(f"❌ Error processing actions: {e}")


# Global instance
_scheduler_instance = None

def get_learning_scheduler(mongo_client: MongoClient = None, qdrant_client=None) -> LearningScheduler:
    """Get or create learning scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None and mongo_client:
        _scheduler_instance = LearningScheduler(mongo_client, qdrant_client)
    return _scheduler_instance

