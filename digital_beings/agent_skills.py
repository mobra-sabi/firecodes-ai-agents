import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.mongodb_handler import MongoDBHandler

class DigitalBeingSkills:
    """Arsenal REAL de skill-uri pentru ființe digitale"""
    
    def __init__(self, agent_id: str, agent_identity: Dict):
        self.agent_id = agent_id
        self.identity = agent_identity
        self.mongodb = MongoDBHandler()
        self.collection_name = f"skills_{agent_id}"
        
        # Inițializează skill-urile în MongoDB
        self.skill_levels = self.initialize_skill_levels()
        self.save_skills_to_db()
        
    def initialize_skill_levels(self) -> Dict:
        """Inițializează skill-urile bazate pe identitate REALĂ"""
        
        base_skills = {
            'web_research': 5,
            'data_analysis': 5,
            'content_creation': 5,
            'client_communication': 5,
            'trend_analysis': 3,
            'automation': 4,
            'strategic_thinking': 4
        }
        
        # Ajustează skill-urile bazate pe identitatea REALĂ
        expertise = self.identity.get('expertise', [])
        
        if any('protecție la foc' in exp.lower() for exp in expertise):
            base_skills.update({
                'technical_expertise': 9,
                'safety_analysis': 9,
                'compliance_checking': 8,
                'risk_assessment': 8
            })
        elif any('medical' in exp.lower() for exp in expertise):
            base_skills.update({
                'medical_knowledge': 9,
                'patient_communication': 8,
                'health_analysis': 8,
                'empathy': 9
            })
            
        return base_skills
        
    def save_skills_to_db(self):
        """Salvează skill-urile în MongoDB"""
        
        try:
            collection = self.mongodb.db[self.collection_name]
            
            skill_document = {
                'agent_id': self.agent_id,
                'skills': self.skill_levels,
                'last_updated': datetime.now().isoformat(),
                'usage_log': []
            }
            
            # Upsert (update sau insert)
            collection.replace_one(
                {'agent_id': self.agent_id}, 
                skill_document, 
                upsert=True
            )
            
            print(f"💾 Skills salvate pentru agent {self.agent_id}")
            
        except Exception as e:
            print(f"❌ Eroare salvare skills: {e}")
            
    def use_skill(self, skill_name: str, context: str = "") -> Dict:
        """Folosește un skill și înregistrează utilizarea REALĂ"""
        
        if skill_name not in self.skill_levels:
            return {'error': f'Skill {skill_name} nu există'}
            
        skill_level = self.skill_levels[skill_name]
        
        # Simulează rezultatul bazat pe nivelul skill-ului
        success_rate = skill_level / 10
        performance_score = min(10, skill_level + (success_rate * 2))
        
        usage_entry = {
            'skill': skill_name,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'performance_score': performance_score,
            'skill_level_at_use': skill_level
        }
        
        # Salvează utilizarea în MongoDB
        try:
            collection = self.mongodb.db[self.collection_name]
            collection.update_one(
                {'agent_id': self.agent_id},
                {'$push': {'usage_log': usage_entry}}
            )
        except Exception as e:
            print(f"⚠️ Eroare log skill usage: {e}")
            
        print(f"⚡ Folosit skill '{skill_name}' (nivel {skill_level}) - performanță: {performance_score:.1f}")
        
        return {
            'skill': skill_name,
            'performance_score': performance_score,
            'skill_level': skill_level,
            'success': performance_score >= 6,
            'context': context
        }
        
    def improve_skill(self, skill_name: str, feedback_score: int):
        """Îmbunătățește un skill bazat pe feedback REAL"""
        
        if skill_name not in self.skill_levels:
            print(f"❌ Skill {skill_name} nu există")
            return
            
        old_level = self.skill_levels[skill_name]
        
        # Calculează îmbunătățirea
        if feedback_score >= 8:
            improvement = 0.2
        elif feedback_score >= 6:
            improvement = 0.1
        elif feedback_score <= 3:
            improvement = -0.1
        else:
            improvement = 0
            
        new_level = max(1, min(10, old_level + improvement))
        self.skill_levels[skill_name] = new_level
        
        # Salvează în MongoDB
        self.save_skills_to_db()
        
        print(f"📈 Skill '{skill_name}': {old_level:.1f} → {new_level:.1f} (feedback: {feedback_score})")
        
        return {
            'skill': skill_name,
            'old_level': old_level,
            'new_level': new_level,
            'improvement': improvement,
            'feedback_score': feedback_score
        }
        
    def get_skill_report(self) -> Dict:
        """Generează raport REAL despre skill-urile agentului"""
        
        try:
            collection = self.mongodb.db[self.collection_name]
            skill_data = collection.find_one({'agent_id': self.agent_id})
            
            if not skill_data:
                return {'error': 'Nu există date despre skills'}
                
            usage_log = skill_data.get('usage_log', [])
            
            # Calculează statistici reale
            skill_usage_count = {}
            for log_entry in usage_log:
                skill = log_entry['skill']
                skill_usage_count[skill] = skill_usage_count.get(skill, 0) + 1
                
            most_used = sorted(skill_usage_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'agent_id': self.agent_id,
                'current_skills': self.skill_levels,
                'top_skills': sorted(self.skill_levels.items(), key=lambda x: x[1], reverse=True)[:5],
                'most_used_skills': most_used,
                'expertise_areas': [skill for skill, level in self.skill_levels.items() if level >= 8],
                'improvement_areas': [skill for skill, level in self.skill_levels.items() if level < 5],
                'total_skill_usage': len(usage_log),
                'last_updated': skill_data.get('last_updated', 'unknown')
            }
            
        except Exception as e:
            return {'error': f'Eroare generare raport: {e}'}
