"""
Utilități comune pentru ecosistemul de ființe digitale
"""

import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_being_id() -> str:
    """Generează ID unic pentru o ființă digitală"""
    return f"being_{str(uuid.uuid4())[:8]}"

def generate_conversation_id() -> str:
    """Generează ID unic pentru o conversație"""
    return f"conv_{str(uuid.uuid4())[:8]}"

def calculate_compatibility(being1: Dict, being2: Dict) -> float:
    """Calculează compatibilitatea între două ființe"""
    
    # Compatibilitate bazată pe personalitate
    personality1 = being1.get('personality', {})
    personality2 = being2.get('personality', {})
    
    personality_diff = 0
    for trait in ['professionalism', 'creativity', 'friendliness', 'formality']:
        diff = abs(personality1.get(trait, 5) - personality2.get(trait, 5))
        personality_diff += diff
        
    personality_compatibility = max(0, 1 - (personality_diff / 40))  # Normalize to 0-1
    
    # Compatibilitate bazată pe skill-uri
    skills1 = set(being1.get('skills', {}).keys())
    skills2 = set(being2.get('skills', {}).keys())
    
    if skills1 and skills2:
        skill_overlap = len(skills1.intersection(skills2)) / len(skills1.union(skills2))
    else:
        skill_overlap = 0
        
    # Compatibilitate bazată pe industrie
    industry1 = being1.get('identity', {}).get('industry', '')
    industry2 = being2.get('identity', {}).get('industry', '')
    industry_compatibility = 1.0 if industry1 == industry2 else 0.3
    
    # Weighted average
    total_compatibility = (
        personality_compatibility * 0.4 +
        skill_overlap * 0.3 +
        industry_compatibility * 0.3
    )
    
    return round(total_compatibility, 2)

def format_timestamp(timestamp: str = None) -> str:
    """Formatează timestamp pentru afișare"""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def hash_content(content: str) -> str:
    """Creează hash pentru conținut"""
    return hashlib.md5(content.encode()).hexdigest()[:8]

def calculate_time_decay(timestamp: str, decay_factor: float = 0.1) -> float:
    """Calculează decay-ul temporal pentru importanța memoriilor"""
    
    try:
        event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_diff = datetime.now() - event_time
        days_old = time_diff.days
        
        # Exponential decay
        decay = max(0.1, 1.0 * (1 - decay_factor) ** days_old)
        return decay
    except:
        return 1.0

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extrage cuvinte cheie din text"""
    
    # Simple keyword extraction (în producție ar folosi NLP mai avansat)
    words = text.lower().split()
    
    # Filtrează cuvintele comune
    stop_words = {'și', 'în', 'de', 'la', 'cu', 'pe', 'pentru', 'din', 'că', 'se', 'este', 'sunt', 'a', 'an', 'the', 'is', 'are', 'and', 'or', 'but'}
    
    keywords = [word for word in words if len(word) > 3 and word not in stop_words]
    
    # Returnează cele mai frecvente
    keyword_freq = {}
    for word in keywords:
        keyword_freq[word] = keyword_freq.get(word, 0) + 1
        
    sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, freq in sorted_keywords[:max_keywords]]

def similarity_score(text1: str, text2: str) -> float:
    """Calculează similaritatea între două texte"""
    
    keywords1 = set(extract_keywords(text1))
    keywords2 = set(extract_keywords(text2))
    
    if not keywords1 or not keywords2:
        return 0.0
        
    intersection = keywords1.intersection(keywords2)
    union = keywords1.union(keywords2)
    
    return len(intersection) / len(union) if union else 0.0

def validate_being_data(being_data: Dict) -> bool:
    """Validează datele unei ființe digitale"""
    
    required_fields = ['agent_id', 'identity', 'personality', 'skills']
    
    for field in required_fields:
        if field not in being_data:
            logger.error(f"Missing required field: {field}")
            return False
            
    # Validează personality scores
    personality = being_data.get('personality', {})
    for trait, score in personality.items():
        if not isinstance(score, (int, float)) or not (0 <= score <= 10):
            logger.error(f"Invalid personality score for {trait}: {score}")
            return False
            
    return True

def export_being_summary(being: Dict) -> Dict:
    """Exportă sumar al unei ființe pentru vizualizare"""
    
    return {
        'id': being.get('agent_id', 'unknown'),
        'name': being.get('identity', {}).get('role', 'Unknown Being'),
        'industry': being.get('identity', {}).get('industry', 'general'),
        'personality_summary': {
            'dominant_traits': get_dominant_traits(being.get('personality', {})),
            'communication_style': being.get('communication_style', 'balanced')
        },
        'skill_summary': {
            'top_skills': get_top_skills(being.get('skills', {})),
            'expertise_level': calculate_expertise_level(being.get('skills', {}))
        },
        'activity_summary': {
            'total_interactions': len(being.get('interaction_history', [])),
            'memory_episodes': len(being.get('memory', {}).get('episodes', [])),
            'last_activity': being.get('last_activity', 'never')
        }
    }

def get_dominant_traits(personality: Dict) -> List[str]:
    """Identifică trăsăturile dominante ale personalității"""
    
    sorted_traits = sorted(personality.items(), key=lambda x: x[1], reverse=True)
    return [trait for trait, score in sorted_traits[:3] if score >= 6]

def get_top_skills(skills: Dict) -> List[str]:
    """Identifică skill-urile de top"""
    
    sorted_skills = sorted(skills.items(), key=lambda x: x[1], reverse=True)
    return [skill for skill, level in sorted_skills[:5] if level >= 7]

def calculate_expertise_level(skills: Dict) -> str:
    """Calculează nivelul general de expertiză"""
    
    if not skills:
        return 'beginner'
        
    avg_skill = sum(skills.values()) / len(skills)
    
    if avg_skill >= 8:
        return 'expert'
    elif avg_skill >= 6:
        return 'advanced'
    elif avg_skill >= 4:
        return 'intermediate'
    else:
        return 'beginner'

class BeingLogger:
    """Logger specializat pentru ființe digitale"""
    
    def __init__(self, being_id: str):
        self.being_id = being_id
        self.logger = logging.getLogger(f"being_{being_id}")
        
    def log_action(self, action: str, details: str = "", importance: int = 5):
        """Log o acțiune a ființei"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'being_id': self.being_id,
            'action': action,
            'details': details,
            'importance': importance
        }
        
        if importance >= 8:
            self.logger.warning(f"High importance: {action} - {details}")
        else:
            self.logger.info(f"{action} - {details}")
            
        return log_entry
        
    def log_interaction(self, other_being_id: str, interaction_type: str, result: str):
        """Log o interacțiune între ființe"""
        
        self.log_action(
            f"interaction_{interaction_type}",
            f"With {other_being_id}: {result}",
            importance=6
        )
        
    def log_learning(self, skill: str, old_level: float, new_level: float):
        """Log învățarea unui skill"""
        
        improvement = new_level - old_level
        self.log_action(
            "skill_learning",
            f"{skill}: {old_level:.2f} → {new_level:.2f} (+{improvement:.2f})",
            importance=7 if improvement > 0.5 else 5
        )

# Constante pentru ecosistem
ECOSYSTEM_CONSTANTS = {
    'MAX_MEMORY_SIZE': 10000,
    'SKILL_IMPROVEMENT_RATE': 0.1,
    'MEMORY_DECAY_RATE': 0.05,
    'INTERACTION_COOLDOWN': 60,  # secunde
    'MAX_CONNECTIONS': 10,
    'MIN_COMPATIBILITY': 0.3
}
