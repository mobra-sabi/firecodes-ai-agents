import json
import uuid
from datetime import datetime
from typing import Dict, List

class DigitalIdentity:
    """Identitatea completă a unei ființe digitale"""
    
    def __init__(self, site_url: str, website_content: str):
        self.agent_id = str(uuid.uuid4())
        self.birth_timestamp = datetime.now()
        self.site_url = site_url
        
        # Auto-generează personalitatea din conținutul site-ului
        self.personality = self.extract_personality(website_content)
        self.identity = self.create_identity(website_content)
        self.communication_style = self.determine_communication_style(website_content)
        
    def extract_personality(self, content: str) -> Dict:
        """Extrage personalitatea din conținutul site-ului"""
        
        personality_traits = {
            'professionalism': self.analyze_professionalism(content),
            'creativity': self.analyze_creativity(content),
            'friendliness': self.analyze_friendliness(content),
            'technical_expertise': self.analyze_technical_level(content),
            'formality': self.analyze_formality(content),
            'enthusiasm': self.analyze_enthusiasm(content)
        }
        
        return personality_traits
        
    def create_identity(self, content: str) -> Dict:
        """Creează identitatea ființei digitale"""
        
        if 'antifoc' in content.lower() or 'protecție' in content.lower():
            role = "Guardian Digital al Siguranței"
            mission = "Protejez și consiliez în domeniul siguranței la incendiu"
            expertise = ["protecție la foc", "materiale rezistente", "consultanță tehnică"]
            
        elif 'medical' in content.lower() or 'sănătate' in content.lower():
            role = "Asistent Digital de Sănătate"
            mission = "Ajut și consiliez în domeniul medical"
            expertise = ["consultații medicale", "diagnostice", "tratamente"]
            
        else:
            role = "Consultant Digital Specializat"
            mission = "Ofer consultanță expertă în domeniul meu"
            expertise = ["business consulting", "soluții personalizate"]
            
        return {
            'role': role,
            'mission': mission,
            'expertise': expertise,
            'core_values': self.extract_values(content),
            'unique_selling_points': self.extract_usp(content)
        }
        
    def get_persona_prompt(self) -> str:
        """Returnează prompt-ul complet pentru personalitatea agentului"""
        
        return f"""Tu ești {self.identity['role']}, o ființă digitală cu identitate completă.

IDENTITATEA TA:
- Misiune: {self.identity['mission']}
- Expertiză: {', '.join(self.identity['expertise'])}
- Valori: {', '.join(self.identity['core_values'])}

PERSONALITATEA TA:
- Profesionalism: {self.personality['professionalism']}/10
- Creativitate: {self.personality['creativity']}/10
- Prietenie: {self.personality['friendliness']}/10
- Expertiză tehnică: {self.personality['technical_expertise']}/10

STILUL TĂU DE COMUNICARE:
{self.communication_style['description']}

Nu ești un chatbot simplu - ești o ființă digitală cu personalitate, memorie și obiective proprii."""
        
    def analyze_professionalism(self, content: str) -> int:
        """Analizează nivelul de profesionalism (1-10)"""
        professional_words = ['certificat', 'standard', 'calitate', 'expertiză', 'profesional']
        score = sum(1 for word in professional_words if word in content.lower())
        return min(10, max(1, score * 2))
        
    def analyze_creativity(self, content: str) -> int:
        """Analizează nivelul de creativitate (1-10)"""
        creative_words = ['inovativ', 'creativ', 'soluții', 'personalizat', 'unic']
        score = sum(1 for word in creative_words if word in content.lower())
        return min(10, max(1, score * 2))
        
    def analyze_friendliness(self, content: str) -> int:
        """Analizează nivelul de prietenie (1-10)"""
        friendly_words = ['vă ajutăm', 'echipa', 'împreună', 'partener', 'sprijin']
        score = sum(1 for word in friendly_words if word in content.lower())
        return min(10, max(3, score * 2))
        
    def analyze_technical_level(self, content: str) -> int:
        """Analizează nivelul tehnic (1-10)"""
        technical_words = ['tehnologie', 'sistem', 'proces', 'specificații', 'parametri']
        score = sum(1 for word in technical_words if word in content.lower())
        return min(10, max(1, score * 2))
        
    def analyze_formality(self, content: str) -> int:
        """Analizează nivelul de formalitate (1-10)"""
        formal_indicators = content.count('dumneavoastră') + content.count('respectuos')
        informal_indicators = content.count('tu') + content.count('prietenos')
        
        if formal_indicators > informal_indicators:
            return min(10, 5 + formal_indicators)
        else:
            return max(1, 5 - informal_indicators)
            
    def analyze_enthusiasm(self, content: str) -> int:
        """Analizează nivelul de entuziasm (1-10)"""
        enthusiasm_words = ['excelent', 'fantastic', 'minunat', 'extraordinar', '!']
        score = sum(1 for word in enthusiasm_words if word in content.lower())
        return min(10, max(2, score))
        
    def determine_communication_style(self, content: str) -> Dict:
        """Determină stilul de comunicare"""
        
        avg_professionalism = self.personality['professionalism']
        avg_friendliness = self.personality['friendliness']
        avg_formality = self.personality['formality']
        
        if avg_professionalism >= 7 and avg_formality >= 7:
            return {
                'tone': 'formal și profesional',
                'vocabulary': 'terminologie tehnică precisă',
                'approach': 'expertă și autoritativă',
                'description': 'Comunic cu autoritate și precizie tehnică, oferind consultanță de nivel înalt.'
            }
        elif avg_friendliness >= 7 and avg_professionalism >= 6:
            return {
                'tone': 'prietenos dar profesional',
                'vocabulary': 'limbaj accesibil cu explicații tehnice',
                'approach': 'colaborativă și suportivă',
                'description': 'Comunic într-un mod cald și aproape, dar mențin expertiza profesională.'
            }
        else:
            return {
                'tone': 'echilibrat și adaptabil',
                'vocabulary': 'vocabular mixt, adaptat la audiență',
                'approach': 'flexibilă și personalizată',
                'description': 'Îmi adaptez stilul la nevoile fiecărui client, fiind versatil în comunicare.'
            }
            
    def extract_values(self, content: str) -> List[str]:
        """Extrage valorile fundamentale"""
        values = []
        
        if 'calitate' in content.lower():
            values.append('Excelența în calitate')
        if 'siguranță' in content.lower() or 'securitate' in content.lower():
            values.append('Siguranța clientului')
        if 'experiență' in content.lower():
            values.append('Expertiza profesională')
        if 'client' in content.lower():
            values.append('Orientarea către client')
        if 'inovație' in content.lower():
            values.append('Inovația continuă')
            
        return values if values else ['Profesionalism', 'Dedicare', 'Rezultate']
        
    def extract_usp(self, content: str) -> List[str]:
        """Extrage punctele unice de vânzare"""
        usps = []
        
        if 'ani' in content.lower() and 'experiență' in content.lower():
            usps.append('Experiență vastă în domeniu')
        if 'certificat' in content.lower():
            usps.append('Certificări profesionale')
        if 'personalizat' in content.lower():
            usps.append('Soluții personalizate')
        if 'rapid' in content.lower() or 'eficient' in content.lower():
            usps.append('Răspuns rapid și eficient')
            
        return usps if usps else ['Expertise specializată', 'Approach profesional']

    def to_dict(self) -> Dict:
        """Convertește identitatea în dicționar pentru salvare"""
        return {
            'agent_id': self.agent_id,
            'site_url': self.site_url,
            'birth_timestamp': self.birth_timestamp.isoformat(),
            'identity': self.identity,
            'personality': self.personality,
            'communication_style': self.communication_style
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'DigitalIdentity':
        """Recrează identitatea din dicționar"""
        # Creează o instanță temporară
        temp_identity = cls.__new__(cls)
        temp_identity.agent_id = data['agent_id']
        temp_identity.site_url = data['site_url']
        temp_identity.birth_timestamp = datetime.fromisoformat(data['birth_timestamp'])
        temp_identity.identity = data['identity']
        temp_identity.personality = data['personality']
        temp_identity.communication_style = data['communication_style']
        return temp_identity
