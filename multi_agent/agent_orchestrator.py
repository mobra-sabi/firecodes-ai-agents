import asyncio
import json
from datetime import datetime
from typing import Dict, List
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.mongodb_handler import MongoDBHandler

class AgentOrchestrator:
    """Orchestrator pentru comunicarea între agenți AI"""
    
    def __init__(self):
        self.active_agents = {}
        self.agent_network = {}
        self.communication_logs = []
        self.mongodb = MongoDBHandler()
        
    def agent_ecosystem_features(self):
        return {
            'agent_discovery': {
                'auto_industry_detection': 'Detectează industria din conținutul site-ului',
                'related_agents_finder': 'Găsește agenți din aceeași industrie',
                'collaboration_suggestions': 'Sugerează colaborări între agenți',
                'expertise_mapping': 'Mapează expertiza fiecărui agent'
            },
            
            'inter_agent_communication': {
                'direct_messaging': 'Agenții pot comunica direct între ei',
                'broadcast_messages': 'Mesaje broadcast către toți agenții din industrie',
                'collaborative_responses': 'Răspunsuri colaborative la întrebări complexe',
                'knowledge_sharing': 'Împărtășire automată de cunoștințe'
            },
            
            'collective_intelligence': {
                'group_problem_solving': 'Rezolvarea problemelor în grup',
                'consensus_building': 'Construirea consensului între agenți',
                'distributed_learning': 'Învățare distribuită pe tot ecosistemul',
                'cross_pollination': 'Transfer de cunoștințe între industrii'
            },
            
            'advanced_capabilities': {
                'supply_chain_mapping': 'Maparea completă a lanțului de aprovizionare',
                'market_ecosystem_analysis': 'Analiză completă ecosistem piață',
                'competitive_intelligence_network': 'Rețea de intelligence competitiv',
                'collaborative_forecasting': 'Prognoze colaborative de piață'
            }
        }
        
    async def create_agent_from_site(self, site_url, industry_context=None):
        """Creează agent nou din site și îl integrează în ecosistem"""
        
        # 1. Detectează industria automată
        detected_industry = await self.detect_industry(site_url)
        
        # 2. Creează agentul
        agent_id = str(uuid.uuid4())
        agent_config = {
            'agent_id': agent_id,
            'site_url': site_url,
            'industry': detected_industry,
            'capabilities': await self.analyze_agent_capabilities(site_url),
            'creation_time': datetime.now().isoformat(),
            'status': 'active',
            'connections': [],
            'collaboration_history': []
        }
        
        # 3. Înregistrează în ecosistem
        self.active_agents[agent_id] = agent_config
        
        # 4. Salvează în MongoDB
        try:
            collection = self.mongodb.db['agent_ecosystem']
            collection.insert_one(agent_config)
        except Exception as e:
            print(f"Eroare salvare agent: {e}")
        
        # 5. Găsește agenți înrudiți
        related_agents = await self.find_related_agents(detected_industry)
        
        # 6. Stabilește conexiuni
        await self.establish_agent_connections(agent_id, related_agents)
        
        # 7. Anunță ecosistemul de noul agent
        await self.broadcast_new_agent_announcement(agent_config)
        
        print(f"✅ Agent creat: {agent_id} pentru {site_url} (industria: {detected_industry})")
        return agent_config
        
    async def detect_industry(self, site_url):
        """Detectează industria din conținutul site-ului"""
        
        industry_keywords = {
            'medical': ['medical', 'clinică', 'spital', 'sănătate', 'doctor', 'tratament', 'pacient'],
            'legal': ['avocat', 'juridic', 'legal', 'drept', 'tribunal', 'contract', 'consultanță'],
            'construction': ['construcții', 'edificii', 'arhitectură', 'inginerie', 'proiect', 'vopsitorii'],
            'finance': ['bancă', 'financiar', 'credit', 'investiții', 'asigurări', 'contabilitate'],
            'retail': ['magazin', 'vânzări', 'produse', 'comerț', 'retail', 'online'],
            'manufacturing': ['fabrică', 'producție', 'industrial', 'manufactura', 'tehnologie'],
            'education': ['educație', 'școală', 'universitate', 'curs', 'învățare', 'formare'],
            'hospitality': ['hotel', 'restaurant', 'turism', 'cazare', 'ospitalitate', 'servicii'],
            'agriculture': ['agricultură', 'fermă', 'cultivare', 'produse agricole', 'siloz'],
            'automotive': ['auto', 'mașini', 'vehicule', 'transport', 'automotive']
        }
        
        # Analizează conținutul pentru detectarea industriei
        site_content = self.mongodb.get_site_content(site_url)
        
        if not site_content:
            return 'unknown'
            
        content_text = (site_content.get('content', '') + ' ' + 
                       site_content.get('title', '') + ' ' + 
                       site_content.get('description', '')).lower()
        
        industry_scores = {}
        for industry, keywords in industry_keywords.items():
            score = sum(content_text.count(keyword) for keyword in keywords)
            industry_scores[industry] = score
            
        # Returnează industria cu cel mai mare scor
        if industry_scores:
            detected_industry = max(industry_scores, key=industry_scores.get)
            return detected_industry if industry_scores[detected_industry] > 0 else 'general'
        
        return 'general'
        
    async def analyze_agent_capabilities(self, site_url):
        """Analizează capabilitățile unui agent bazat pe conținutul site-ului"""
        
        site_content = self.mongodb.get_site_content(site_url)
        if not site_content:
            return ['general_conversation']
            
        content = site_content.get('content', '').lower()
        
        capabilities = []
        
        # Detectează capabilități bazate pe conținut
        capability_keywords = {
            'pricing_expert': ['preț', 'tarif', 'cost', 'ofertă', 'buget'],
            'technical_specialist': ['tehnic', 'specializat', 'metodă', 'procedură', 'tehnologie'],
            'sales_expert': ['vânzări', 'comercial', 'client', 'customer', 'marketing'],
            'project_manager': ['proiect', 'management', 'coordonare', 'planificare'],
            'quality_assurance': ['calitate', 'certificare', 'standard', 'control'],
            'customer_service': ['suport', 'asistență', 'help', 'contact', 'întrebări']
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in content for keyword in keywords):
                capabilities.append(capability)
                
        return capabilities if capabilities else ['general_conversation']
        
    async def find_related_agents(self, industry):
        """Găsește agenți din aceeași industrie sau înrudite"""
        
        related_agents = []
        
        # Agenți din aceeași industrie
        for agent_id, agent_config in self.active_agents.items():
            if agent_config['industry'] == industry:
                related_agents.append(agent_id)
                
        # Industrii înrudite
        industry_relationships = {
            'medical': ['legal', 'finance'],
            'legal': ['medical', 'finance', 'construction'],
            'construction': ['legal', 'finance', 'manufacturing'],
            'finance': ['medical', 'legal', 'retail', 'manufacturing'],
            'retail': ['finance', 'manufacturing'],
            'manufacturing': ['construction', 'finance', 'retail'],
            'agriculture': ['manufacturing', 'retail', 'finance']
        }
        
        related_industries = industry_relationships.get(industry, [])
        
        for agent_id, agent_config in self.active_agents.items():
            if agent_config['industry'] in related_industries:
                related_agents.append(agent_id)
                
        return list(set(related_agents))
        
    async def establish_agent_connections(self, agent_id, related_agents):
        """Stabilește conexiuni între agenți"""
        
        if agent_id in self.active_agents:
            self.active_agents[agent_id]['connections'] = related_agents
            
            # Actualizează și conexiunile inverse
            for related_agent_id in related_agents:
                if related_agent_id in self.active_agents:
                    if agent_id not in self.active_agents[related_agent_id]['connections']:
                        self.active_agents[related_agent_id]['connections'].append(agent_id)
                        
    async def broadcast_new_agent_announcement(self, agent_config):
        """Anunță ecosistemul despre un nou agent"""
        
        announcement = {
            'type': 'new_agent_announcement',
            'agent_id': agent_config['agent_id'],
            'industry': agent_config['industry'],
            'capabilities': agent_config['capabilities'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Salvează anunțul
        self.communication_logs.append(announcement)
        
        print(f"📢 Anunț ecosistem: Nou agent {agent_config['industry']} cu capabilități: {', '.join(agent_config['capabilities'])}")
        
    async def agent_collaboration_request(self, requesting_agent_id, question, context):
        """Agent cere colaborare de la alți agenți pentru răspuns complex"""
        
        requesting_agent = self.active_agents.get(requesting_agent_id)
        if not requesting_agent:
            return None
            
        # Analizează ce tip de expertiză este necesară
        required_expertise = await self.analyze_required_expertise(question, context)
        
        # Găsește agenții cu expertiza necesară
        expert_agents = await self.find_expert_agents(required_expertise)
        
        collaboration_session = {
            'session_id': str(uuid.uuid4()),
            'requesting_agent': requesting_agent_id,
            'question': question,
            'required_expertise': required_expertise,
            'expert_agents': expert_agents,
            'responses': [],
            'start_time': datetime.now().isoformat()
        }
        
        print(f"🤝 Sesiune colaborare: {requesting_agent_id} cere expertiză: {', '.join(required_expertise)}")
        
        # Simulează răspunsurile de la experți (în implementarea reală ar fi API calls)
        for expert_agent_id in expert_agents[:3]:  # Limitează la 3 experți
            expert_response = await self.simulate_expert_response(
                expert_agent_id, 
                question, 
                required_expertise
            )
            collaboration_session['responses'].append(expert_response)
            
        # Combină răspunsurile
        collaborative_answer = await self.synthesize_collaborative_response(
            question, 
            collaboration_session['responses']
        )
        
        collaboration_session['final_answer'] = collaborative_answer
        collaboration_session['end_time'] = datetime.now().isoformat()
        
        return collaboration_session
        
    async def analyze_required_expertise(self, question, context):
        """Analizează ce expertiză este necesară pentru întrebare"""
        
        expertise_keywords = {
            'pricing_expert': ['preț', 'cost', 'tarif', 'cât costă', 'ofertă', 'buget'],
            'technical_specialist': ['cum se face', 'tehnic', 'specificații', 'metode', 'proceduri'],
            'legal': ['contract', 'juridic', 'legal', 'lege', 'tribunal'],
            'medical': ['medical', 'sănătate', 'tratament', 'diagnostic'],
            'financial': ['financiar', 'credit', 'investiție', 'cost'],
            'quality_assurance': ['calitate', 'standarde', 'certificări', 'garanție'],
            'project_manager': ['când', 'planificare', 'etape', 'timeline', 'management']
        }
        
        question_lower = question.lower()
        required_expertise = []
        
        for expertise, keywords in expertise_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                required_expertise.append(expertise)
                
        return required_expertise if required_expertise else ['general_conversation']
        
    async def find_expert_agents(self, required_expertise):
        """Găsește agenții cu expertiza necesară"""
        
        expert_agents = []
        
        for agent_id, agent_config in self.active_agents.items():
            agent_capabilities = agent_config.get('capabilities', [])
            
            # Verifică dacă agentul are vreo expertiză necesară
            if any(expertise in agent_capabilities for expertise in required_expertise):
                expert_agents.append(agent_id)
                
        return expert_agents
        
    async def simulate_expert_response(self, expert_agent_id, question, required_expertise):
        """Simulează răspunsul unui expert (în realitate ar fi API call)"""
        
        expert_agent = self.active_agents.get(expert_agent_id)
        if not expert_agent:
            return None
            
        # Simulare răspuns bazat pe industrie și capabilități
        industry = expert_agent['industry']
        capabilities = expert_agent['capabilities']
        
        simulated_response = {
            'expert_agent_id': expert_agent_id,
            'industry': industry,
            'capabilities': capabilities,
            'response': f"Ca expert în {industry} cu specializare în {', '.join(capabilities)}, pot contribui cu informații specifice pentru această întrebare.",
            'confidence': 0.8,
            'timestamp': datetime.now().isoformat()
        }
        
        return simulated_response
        
    async def synthesize_collaborative_response(self, question, expert_responses):
        """Combină răspunsurile experților într-un răspuns comprehensiv"""
        
        if not expert_responses:
            return "Nu am putut găsi experți disponibili pentru această întrebare."
            
        # Construiește răspunsul colaborativ
        collaborative_answer = f"Bazat pe consultarea cu {len(expert_responses)} experți din ecosistem:\n\n"
        
        for i, response in enumerate(expert_responses, 1):
            collaborative_answer += f"{i}. Expert {response['industry']}: {response['response']}\n\n"
            
        collaborative_answer += "Această informație rezultă din colaborarea între agenții specializați din rețeaua noastră."
        
        return collaborative_answer
        
    def get_ecosystem_stats(self):
        """Returnează statistici despre ecosistemul de agenți"""
        
        if not self.active_agents:
            return {
                'total_agents': 0,
                'industries': [],
                'total_connections': 0,
                'collaboration_sessions': 0
            }
            
        industries = list(set(agent['industry'] for agent in self.active_agents.values()))
        total_connections = sum(len(agent.get('connections', [])) for agent in self.active_agents.values())
        
        return {
            'total_agents': len(self.active_agents),
            'industries': industries,
            'total_connections': total_connections,
            'collaboration_sessions': len(self.communication_logs),
            'active_agents_by_industry': {
                industry: len([a for a in self.active_agents.values() if a['industry'] == industry])
                for industry in industries
            }
        }
        
    async def load_existing_agents(self):
        """Încarcă agenții existenți din baza de date"""
        
        try:
            collection = self.mongodb.db['agent_ecosystem']
            existing_agents = list(collection.find({}))
            
            for agent_data in existing_agents:
                agent_id = agent_data['agent_id']
                self.active_agents[agent_id] = agent_data
                
            print(f"✅ Încărcați {len(existing_agents)} agenți din baza de date")
            
        except Exception as e:
            print(f"⚠️ Eroare la încărcarea agenților: {e}")
