#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from multi_agent.agent_orchestrator import AgentOrchestrator
from multi_agent.communication_protocol import AgentCommunicationProtocol, MessageType
from optimized.smart_site_manager import SmartSiteManager

class MultiAgentDashboard:
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.comm_protocol = AgentCommunicationProtocol()
        self.site_manager = SmartSiteManager()
        
    async def initialize_system(self):
        """Inițializează sistemul multi-agent"""
        print("🚀 Inițializez sistemul multi-agent...")
        await self.orchestrator.load_existing_agents()
        print("✅ Sistem inițializat!")
        
    async def auto_discover_ecosystem(self, seed_site_url):
        """Descoperă automat ecosistemul din jurul unui site"""
        
        print(f"🔍 Încep descoperirea ecosistemului pentru {seed_site_url}...")
        
        # 1. Procesează site-ul seed
        print("📝 Procesez site-ul seed...")
        success = self.site_manager.process_site_smart(seed_site_url)
        
        if not success:
            print(f"❌ Nu s-a putut procesa site-ul seed: {seed_site_url}")
            return None
            
        # 2. Creează primul agent
        print("🤖 Creez primul agent...")
        seed_agent = await self.orchestrator.create_agent_from_site(seed_site_url)
        
        # 3. Detectează industria și caută site-uri relevante
        industry = seed_agent['industry']
        print(f"🏭 Industrie detectată: {industry}")
        
        # 4. Simulează descoperirea de site-uri din aceeași industrie
        related_sites = await self.discover_related_sites(seed_site_url, industry)
        
        # 5. Creează agenți pentru site-urile descoperite
        ecosystem_agents = [seed_agent]
        
        for site_url in related_sites[:3]:  # Limitează la 3 pentru demonstrație
            try:
                print(f"🌐 Procesez site: {site_url}")
                
                # Pentru demonstrație, creez agenți fictivi
                agent = await self.create_demo_agent(site_url, industry)
                ecosystem_agents.append(agent)
                    
                # Simulează o pauză
                await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"⚠️ Eroare la procesarea {site_url}: {e}")
                
        print(f"✅ Ecosistem creat cu {len(ecosystem_agents)} agenți!")
        return ecosystem_agents
        
    async def create_demo_agent(self, site_url, industry):
        """Creează un agent demo pentru demonstrație"""
        
        # Simulează crearea unui agent fără să proceseze site-ul real
        import uuid
        from datetime import datetime
        
        agent_config = {
            'agent_id': str(uuid.uuid4()),
            'site_url': site_url,
            'industry': industry,
            'capabilities': ['general_conversation', 'industry_expertise'],
            'creation_time': datetime.now().isoformat(),
            'status': 'demo',
            'connections': [],
            'collaboration_history': []
        }
        
        # Adaugă în orchestrator
        self.orchestrator.active_agents[agent_config['agent_id']] = agent_config
        
        print(f"✅ Agent demo creat: {agent_config['agent_id']}")
        return agent_config
        
    async def discover_related_sites(self, seed_site_url, industry):
        """Simulează descoperirea de site-uri relevante"""
        
        # Site-uri demo pentru diferite industrii
        industry_sites = {
            'construction': [
                'https://demo-construction-company.ro',
                'https://demo-building-materials.ro',
                'https://demo-architecture-firm.ro'
            ],
            'medical': [
                'https://demo-medical-clinic.ro',
                'https://demo-pharmacy.ro',
                'https://demo-medical-equipment.ro'
            ],
            'legal': [
                'https://demo-law-firm.ro',
                'https://demo-legal-services.ro',
                'https://demo-notary-office.ro'
            ],
            'finance': [
                'https://demo-financial-services.ro',
                'https://demo-accounting-firm.ro',
                'https://demo-investment-company.ro'
            ],
            'general': [
                'https://demo-related-company1.ro',
                'https://demo-related-company2.ro',
                'https://demo-supplier.ro'
            ]
        }
        
        return industry_sites.get(industry, industry_sites['general'])
        
    async def test_agent_collaboration(self, question):
        """Testează colaborarea între agenți"""
        
        print(f"\n🤝 Testez colaborarea pentru întrebarea: '{question}'")
        
        if not self.orchestrator.active_agents:
            print("❌ Nu există agenți în sistem pentru colaborare")
            return None
            
        # Alege primul agent ca agent principal
        primary_agent_id = list(self.orchestrator.active_agents.keys())[0]
        
        # Testează colaborarea
        collaboration_result = await self.orchestrator.agent_collaboration_request(
            primary_agent_id, 
            question, 
            {'test_mode': True}
        )
        
        if collaboration_result:
            print("\n📋 Rezultat colaborare:")
            print(f"  🎯 Agent principal: {primary_agent_id}")
            print(f"  👥 Experți consultați: {len(collaboration_result['expert_agents'])}")
            print(f"  💬 Răspuns colaborativ:")
            print(f"    {collaboration_result['final_answer']}")
        else:
            print("❌ Nu s-a putut realiza colaborarea")
            
        return collaboration_result
        
    def display_ecosystem_status(self):
        """Afișează statusul ecosistemului de agenți"""
        
        stats = self.orchestrator.get_ecosystem_stats()
        
        print("\n📊 STATUS ECOSISTEM MULTI-AGENT")
        print("=" * 50)
        print(f"🤖 Total agenți: {stats['total_agents']}")
        print(f"🏭 Industrii: {', '.join(stats['industries'])}")
        print(f"🔗 Total conexiuni: {stats['total_connections']}")
        print(f"💬 Sesiuni colaborare: {stats['collaboration_sessions']}")
        
        if stats.get('active_agents_by_industry'):
            print("\n📈 Distribuție pe industrii:")
            for industry, count in stats['active_agents_by_industry'].items():
                print(f"  • {industry}: {count} agenți")
                
        # Afișează și statistici comunicare
        comm_stats = self.comm_protocol.get_communication_stats()
        print(f"\n📨 Mesaje total: {comm_stats['total_messages']}")
        print(f"🗣️ Conversații active: {comm_stats['active_conversations']}")
        
    async def run_dashboard(self):
        """Rulează dashboard-ul interactiv"""
        
        await self.initialize_system()
        
        while True:
            print("\n🎯 MULTI-AGENT AI DASHBOARD")
            print("=" * 40)
            print("1. Creează ecosistem din site seed")
            print("2. Testează colaborarea între agenți")
            print("3. Status ecosistem")
            print("4. Comunicare între agenți")
            print("5. Demo swarm intelligence")
            print("6. Ieși")
            
            choice = input("\nAlege opțiunea (1-6): ").strip()
            
            if choice == "1":
                site_url = input("🌐 Site seed pentru ecosistem: ").strip()
                if site_url:
                    ecosystem = await self.auto_discover_ecosystem(site_url)
                    if ecosystem:
                        print(f"🎉 Ecosistem creat cu {len(ecosystem)} agenți!")
                        
            elif choice == "2":
                question = input("❓ Întrebarea pentru colaborare: ").strip()
                if question:
                    await self.test_agent_collaboration(question)
                    
            elif choice == "3":
                self.display_ecosystem_status()
                
            elif choice == "4":
                await self.demo_agent_communication()
                
            elif choice == "5":
                await self.demo_swarm_intelligence()
                
            elif choice == "6":
                print("👋 La revedere!")
                break
            else:
                print("❌ Opțiune invalidă")
                
    async def demo_agent_communication(self):
        """Demo pentru comunicarea între agenți"""
        
        if len(self.orchestrator.active_agents) < 2:
            print("❌ Sunt necesari cel puțin 2 agenți pentru demo comunicare")
            return
            
        agents = list(self.orchestrator.active_agents.keys())
        sender = agents[0]
        recipient = agents[1]
        
        print(f"\n📨 Demo comunicare: {sender} → {recipient}")
        
        # Trimite mesaj demo
        message_id = await self.comm_protocol.send_agent_message(
            sender,
            recipient,
            MessageType.KNOWLEDGE_SHARE,
            "Împărtășesc cunoștințe despre industria noastră"
        )
        
        print(f"✅ Mesaj trimis cu ID: {message_id}")
        
        # Broadcast demo
        broadcast_id = await self.comm_protocol.broadcast_to_network(
            sender,
            MessageType.MARKET_UPDATE,
            "Update important despre piața din industria noastră"
        )
        
        print(f"📢 Broadcast trimis cu ID: {broadcast_id}")
        
    async def demo_swarm_intelligence(self):
        """Demo pentru swarm intelligence"""
        
        print("\n🐝 DEMO SWARM INTELLIGENCE")
        print("=" * 30)
        
        complex_question = "Cum pot optimiza costurile și calitatea pentru un proiect complex care implică multiple domenii de expertiză?"
        
        print(f"❓ Întrebare complexă: {complex_question}")
        print("\n🧠 Simulez swarm intelligence...")
        
        # Simulează procesul de swarm intelligence
        steps = [
            "🔍 Analizez complexitatea problemei...",
            "📊 Identific domeniile de expertiză necesare...",
            "👥 Aloc task-uri la agenții specializați...",
            "⚡ Execut procesarea paralelă...",
            "🔗 Integrez rezultatele...",
            "✅ Construiesc consensul final..."
        ]
        
        for step in steps:
            print(step)
            await asyncio.sleep(1)
            
        print(f"\n🎯 Swarm Intelligence Rezultat:")
        print("Prin colaborarea a multiple agenți specializați, soluția optimă include:")
        print("• Planificare în etape cu milestone-uri clare")
        print("• Alocarea resurselor bazată pe prioritizare")
        print("• Monitoring continuu și feedback loop")
        print("• Colaborare cross-functionala între domenii")
        print("• Optimizare iterativă bazată pe rezultate")

def main():
    dashboard = MultiAgentDashboard()
    
    try:
        asyncio.run(dashboard.run_dashboard())
    except KeyboardInterrupt:
        print("\n👋 Dashboard oprit de utilizator")
    except Exception as e:
        print(f"❌ Eroare în dashboard: {e}")

if __name__ == "__main__":
    main()
