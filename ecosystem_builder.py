#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from multi_agent.agent_orchestrator import AgentOrchestrator
from optimized.smart_site_manager import SmartSiteManager

class EcosystemBuilder:
    """Constructor de ecosisteme industriale complete"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.site_manager = SmartSiteManager()
        
    async def build_industry_ecosystem(self, industry_name, seed_sites=None):
        """Construiește ecosistem complet pentru o industrie"""
        
        print(f"🏭 Construiesc ecosistem pentru industria: {industry_name}")
        
        ecosystem = {
            'industry': industry_name,
            'agents': [],
            'connections': [],
            'capabilities': set(),
            'creation_time': str(datetime.now())
        }
        
        # Site-uri seed pentru industrie
        if not seed_sites:
            seed_sites = await self.get_industry_seed_sites(industry_name)
            
        # Creează agenți pentru fiecare site
        for site_url in seed_sites[:10]:  # Limitează la 10
            try:
                # Procesează site-ul
                if self.site_manager.process_site_smart(site_url):
                    # Creează agent
                    agent = await self.orchestrator.create_agent_from_site(site_url)
                    ecosystem['agents'].append(agent)
                    ecosystem['capabilities'].update(agent['capabilities'])
                    
                    print(f"✅ Agent creat pentru {site_url}")
                    
            except Exception as e:
                print(f"⚠️ Eroare la {site_url}: {e}")
                
        # Stabilește conexiuni în ecosistem
        await self.establish_ecosystem_connections(ecosystem)
        
        print(f"🎉 Ecosistem {industry_name} creat cu {len(ecosystem['agents'])} agenți")
        return ecosystem
        
    async def get_industry_seed_sites(self, industry):
        """Returnează site-uri seed pentru o industrie"""
        
        industry_seeds = {
            'construction': [
                'https://alpinconstruct.com/',
                'https://firestopping.ro/'
            ],
            'medical': [
                'https://demo-clinic.ro',
                'https://demo-medical.ro'
            ],
            'legal': [
                'https://demo-law.ro',
                'https://demo-legal.ro'
            ]
        }
        
        return industry_seeds.get(industry, ['https://example.com'])
        
    async def establish_ecosystem_connections(self, ecosystem):
        """Stabilește conexiuni între agenții din ecosistem"""
        
        agents = ecosystem['agents']
        
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents[i+1:], i+1):
                # Calculează compatibilitatea
                compatibility = await self.calculate_agent_compatibility(agent1, agent2)
                
                if compatibility > 0.5:  # Threshold pentru conexiune
                    connection = {
                        'agent1': agent1['agent_id'],
                        'agent2': agent2['agent_id'],
                        'compatibility': compatibility,
                        'connection_type': 'industry_peer'
                    }
                    ecosystem['connections'].append(connection)
                    
        print(f"🔗 Stabilite {len(ecosystem['connections'])} conexiuni")
        
    async def calculate_agent_compatibility(self, agent1, agent2):
        """Calculează compatibilitatea între doi agenți"""
        
        # Compatibilitate bazată pe industrie
        industry_match = 1.0 if agent1['industry'] == agent2['industry'] else 0.3
        
        # Compatibilitate bazată pe capabilități
        capabilities1 = set(agent1.get('capabilities', []))
        capabilities2 = set(agent2.get('capabilities', []))
        
        if capabilities1 and capabilities2:
            capability_overlap = len(capabilities1.intersection(capabilities2)) / len(capabilities1.union(capabilities2))
        else:
            capability_overlap = 0
            
        # Scor final
        compatibility = (industry_match * 0.7) + (capability_overlap * 0.3)
        return compatibility

async def main():
    builder = EcosystemBuilder()
    
    print("🏗️ ECOSYSTEM BUILDER")
    print("=" * 30)
    
    industry = input("Industria pentru ecosistem: ").strip() or "construction"
    
    ecosystem = await builder.build_industry_ecosystem(industry)
    
    print(f"\n📊 Ecosistem {industry} Summary:")
    print(f"🤖 Agenți: {len(ecosystem['agents'])}")
    print(f"🔗 Conexiuni: {len(ecosystem['connections'])}")
    print(f"⚙️ Capabilități: {len(ecosystem['capabilities'])}")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())
