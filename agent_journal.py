"""
Agent Journal - Jurnal intern pentru fiecare agent
Oferă memorie semantică și conștiință de TIMP
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


class AgentJournal:
    """Gestionează jurnalul intern pentru fiecare agent"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.journal_collection = self.db.agent_journal
    
    def add_entry(self, agent_id: str, entry: str, entry_type: str = "general", metadata: Optional[Dict] = None) -> bool:
        """
        Adaugă o intrare în jurnal
        
        Args:
            agent_id: ID-ul agentului
            entry: Textul intrării
            entry_type: Tipul (discovery, reflection, action, observation, etc.)
            metadata: Metadata suplimentară
        """
        try:
            journal_entry = {
                "agent_id": str(agent_id),
                "entry": entry,
                "entry_type": entry_type,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc),
                "day": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
            
            self.journal_collection.insert_one(journal_entry)
            
            logger.info(f"Journal entry added for agent {agent_id}: {entry[:50]}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding journal entry for agent {agent_id}: {e}")
            return False
    
    def add_daily_summary(self, agent_id: str, summary: str, highlights: List[str] = None) -> bool:
        """Adaugă un rezumat zilnic"""
        try:
            entry = f"REZUMAT ZILNIC - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{summary}"
            
            if highlights:
                entry += "\n\nPuncte importante:\n"
                for highlight in highlights:
                    entry += f"- {highlight}\n"
            
            return self.add_entry(agent_id, entry, entry_type="daily_summary")
            
        except Exception as e:
            logger.error(f"Error adding daily summary for agent {agent_id}: {e}")
            return False
    
    def get_entries(self, agent_id: str, days: int = 30, entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obține intrările din jurnal"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = {
                "agent_id": str(agent_id),
                "timestamp": {"$gte": cutoff_time}
            }
            
            if entry_type:
                query["entry_type"] = entry_type
            
            entries = list(self.journal_collection.find(query).sort("timestamp", -1).limit(500))
            
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting journal entries for agent {agent_id}: {e}")
            return []
    
    def get_daily_entries(self, agent_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obține intrările pentru o zi specifică"""
        try:
            if not date:
                date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            entries = list(self.journal_collection.find({
                "agent_id": str(agent_id),
                "day": date
            }).sort("timestamp", 1))
            
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting daily entries for agent {agent_id}: {e}")
            return []
    
    def get_timeline(self, agent_id: str, days: int = 90) -> Dict[str, List[Dict[str, Any]]]:
        """Obține timeline-ul organizat pe zile"""
        try:
            entries = self.get_entries(agent_id, days=days)
            
            timeline = {}
            for entry in entries:
                day = entry.get("day", entry.get("timestamp", datetime.now()).strftime("%Y-%m-%d"))
                if day not in timeline:
                    timeline[day] = []
                timeline[day].append(entry)
            
            # Sortează zilele
            sorted_timeline = dict(sorted(timeline.items(), reverse=True))
            
            return sorted_timeline
            
        except Exception as e:
            logger.error(f"Error getting timeline for agent {agent_id}: {e}")
            return {}
    
    def get_statistics(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Obține statistici despre jurnal"""
        try:
            entries = self.get_entries(agent_id, days=days)
            
            stats = {
                "total_entries": len(entries),
                "by_type": {},
                "by_day": {},
                "first_entry": None,
                "last_entry": None
            }
            
            for entry in entries:
                entry_type = entry.get("entry_type", "unknown")
                stats["by_type"][entry_type] = stats["by_type"].get(entry_type, 0) + 1
                
                day = entry.get("day", "unknown")
                stats["by_day"][day] = stats["by_day"].get(day, 0) + 1
            
            if entries:
                stats["first_entry"] = min(entries, key=lambda x: x.get("timestamp", datetime.max)).get("timestamp")
                stats["last_entry"] = max(entries, key=lambda x: x.get("timestamp", datetime.min)).get("timestamp")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting journal statistics for agent {agent_id}: {e}")
            return {}
    
    def generate_memory_summary(self, agent_id: str, days: int = 90) -> str:
        """Generează un rezumat al memoriei pentru agent"""
        try:
            entries = self.get_entries(agent_id, days=days)
            
            if not entries:
                return "Nu există intrări în jurnal pentru această perioadă."
            
            summary = f"REZUMAT MEMORIE - Ultimele {days} zile\n\n"
            summary += f"Total intrări: {len(entries)}\n\n"
            
            # Grupează pe tipuri
            by_type = {}
            for entry in entries:
                entry_type = entry.get("entry_type", "unknown")
                if entry_type not in by_type:
                    by_type[entry_type] = []
                by_type[entry_type].append(entry)
            
            for entry_type, type_entries in by_type.items():
                summary += f"{entry_type.upper()}: {len(type_entries)} intrări\n"
                # Primele 3 intrări de fiecare tip
                for entry in type_entries[:3]:
                    summary += f"  - {entry.get('entry', '')[:100]}...\n"
                summary += "\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating memory summary for agent {agent_id}: {e}")
            return "Eroare la generarea rezumatului memoriei."

