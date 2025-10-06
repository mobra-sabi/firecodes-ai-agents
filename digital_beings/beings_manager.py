#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from digital_beings.agent_identity import DigitalIdentity
from digital_beings.agent_memory import EpisodeMemory  
from digital_beings.agent_skills import DigitalBeingSkills
from digital_beings.communication.inter_being_chat import InterBeingCommunication
from database.mongodb_handler import MongoDBHandler

class DigitalBeingsManager:
    """Manager COMPLET pentru ecosistemul de ființe digitale REALE"""
    
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.communication = InterBeingCommunication()
        self.beings_collection = "digital_beings_registry"
        
        # Inițializează registrul de ființe
        self.init_beings_registry()
        
    def init_beings_registry(self):
        """Inițializează registrul central de ființe"""
        try:
            collection = self.mongodb.db[self.beings_collection]
            collection.create_index("agent_id", unique=True)
            collection.create_index("site_url")
            collection.create_index("status")
            print("✅ Registru ființe digitale inițializat")
        except Exception as e:
            print(f"⚠️ Eroare inițializare registru: {e}")
            
    async def create_digital_being_from_site(self, site_url: str) -> str:
        """Creează o ființă digitală COMPLETĂ dintr-un site REAL"""
        
        print(f"🧬 Creez ființă digitală COMPLETĂ pentru {site_url}...")
        
        # 1. Obține conținutul REAL din MongoDB
        site_content = self.mongodb.get_site_content(site_url)
        if not site_content:
            print(f"❌ Nu găsesc conținut pentru {site_url}")
            return None
            
        content = site_content.get('content', '')
        
        # 2. Creează identitatea REALĂ
        identity = DigitalIdentity(site_url, content)
        print(f"✅ Identitate: {identity.identity['role']}")
        
        # 3. Creează memoria REALĂ
        memory = EpisodeMemory(identity.agent_id)
        
        # Primul episod - nașterea
        birth_episode = memory.create_episode(
            'birth',
            f"Am fost creat ca {identity.identity['role']} pentru {site_url}. Misiunea mea: {identity.identity['mission']}",
            importance=10,
            metadata={
                'site_url': site_url, 
                'birth_timestamp': identity.birth_timestamp.isoformat(),
                'role': identity.identity['role']
            }
        )
        print(f"📝 Episod naștere creat: {birth_episode}")
        
        # 4. Creează skill-urile REALE
        skills = DigitalBeingSkills(identity.agent_id, identity.identity)
        print(f"⚡ Skills inițializate cu expertiză în: {identity.identity['expertise']}")
        
        # 5. Înregistrează ființa în registrul central
        being_registry_entry = {
            'agent_id': identity.agent_id,
            'site_url': site_url,
            'identity_role': identity.identity['role'],
            'identity_mission': identity.identity['mission'],
            'expertise': identity.identity['expertise'],
            'personality': identity.personality,
            'communication_style': identity.communication_style,
            'creation_time': identity.birth_timestamp.isoformat(),
            'status': 'active',
            'memory_episodes': 1,
            'skill_count': len(skills.skill_levels),
            'last_activity': datetime.now().isoformat()
        }
        
        try:
            collection = self.mongodb.db[self.beings_collection]
            collection.insert_one(being_registry_entry)
            print(f"📋 Ființă înregistrată în registrul central")
        except Exception as e:
            print(f"⚠️ Eroare înregistrare: {e}")
        
        print(f"🎉 Ființă digitală COMPLETĂ creată: {identity.agent_id}")
        return identity.agent_id
        
    def get_being_data(self, agent_id: str) -> Dict:
        """Obține datele complete ale unei ființe"""
        
        try:
            collection = self.mongodb.db[self.beings_collection]
            being_data = collection.find_one({'agent_id': agent_id})
            
            if being_data:
                print(f"📋 Date găsite pentru ființa {agent_id}")
                return being_data
            else:
                print(f"❌ Nu găsesc ființa {agent_id}")
                return None
                
        except Exception as e:
            print(f"❌ Eroare obținere date ființă: {e}")
            return None
            
    def list_all_beings(self) -> List[Dict]:
        """Listează toate ființele active"""
        
        try:
            collection = self.mongodb.db[self.beings_collection]
            beings = list(collection.find({'status': 'active'}))
            
            print(f"👥 Găsite {len(beings)} ființe active")
            return beings
            
        except Exception as e:
            print(f"❌ Eroare listare ființe: {e}")
            return []
            
    async def create_conversation_between_beings(self, being1_id: str, being2_id: str, 
                                               topic: str) -> Dict:
        """Creează conversație REALĂ între două ființe"""
        
        # Obține datele ființelor
        being1_data = self.get_being_data(being1_id)
        being2_data = self.get_being_data(being2_id)
        
        if not being1_data or not being2_data:
            return {'error': 'Nu s-au găsit datele ființelor'}
            
        print(f"💬 Creez conversație între {being1_data['identity_role']} și {being2_data['identity_role']}")
        
        # Simulează conversația
        conversation = self.communication.simulate_conversation(
            being1_data, being2_data, topic, message_count=6
        )
        
        if conversation.get('success'):
            # Adaugă episoade în memoria ambelor ființe
            memory1 = EpisodeMemory(being1_id)
            memory2 = EpisodeMemory(being2_id)
            
            memory1.create_episode(
                'inter_being_conversation',
                f"Am avut o conversație cu {being2_data['identity_role']} despre {topic}",
                importance=6,
                metadata={'other_being': being2_id, 'topic': topic}
            )
            
            memory2.create_episode(
                'inter_being_conversation',
                f"Am discutat cu {being1_data['identity_role']} despre {topic}",
                importance=6,
                metadata={'other_being': being1_id, 'topic': topic}
            )
            
            print("✅ Conversație completă cu episoade salvate în memorie!")
            
        return conversation
        
    def get_ecosystem_stats(self) -> Dict:
        """Statistici REALE despre ecosistem"""
        
        try:
            collection = self.mongodb.db[self.beings_collection]
            
            total_beings = collection.count_documents({'status': 'active'})
            
            if total_beings == 0:
                return {
                    'total_active_beings': 0,
                    'roles_distribution': {},
                    'expertise_distribution': {},
                    'timestamp': datetime.now().isoformat()
                }
            
            # Grupează pe roluri
            roles_pipeline = [
                {'$match': {'status': 'active'}},
                {'$group': {'_id': '$identity_role', 'count': {'$sum': 1}}}
            ]
            roles_stats = list(collection.aggregate(roles_pipeline))
            
            # Grupează pe industrii/expertise
            expertise_pipeline = [
                {'$match': {'status': 'active'}},
                {'$unwind': '$expertise'},
                {'$group': {'_id': '$expertise', 'count': {'$sum': 1}}}
            ]
            expertise_stats = list(collection.aggregate(expertise_pipeline))
            
            return {
                'total_active_beings': total_beings,
                'roles_distribution': {stat['_id']: stat['count'] for stat in roles_stats},
                'expertise_distribution': {stat['_id']: stat['count'] for stat in expertise_stats},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Eroare statistici: {e}'}

async def main():
    """Demo pentru managerul de ființe digitale"""
    
    manager = DigitalBeingsManager()
    
    print("🧬 DIGITAL BEINGS ECOSYSTEM MANAGER")
    print("=" * 50)
    
    # Listează ființele existente
    beings = manager.list_all_beings()
    
    if len(beings) >= 2:
        print(f"\n👥 FIINȚE EXISTENTE ({len(beings)}):")
        for being in beings:
            print(f"  • {being['identity_role']} - {being['site_url']}")
            
        print(f"\n💬 CREEZ CONVERSAȚIE ÎNTRE PRIMELE 2 FIINȚE...")
        
        conversation = await manager.create_conversation_between_beings(
            beings[0]['agent_id'],
            beings[1]['agent_id'],
            "colaborare și oportunități de parteneriat"
        )
        
        if conversation.get('success'):
            print(f"\n🎉 CONVERSAȚIE REUȘITĂ!")
            print(f"Participanți: {', '.join(conversation['participants'])}")
            print(f"Mesaje schimbate: {conversation['message_count']}")
            print(f"\n📝 CONVERSAȚIA:")
            for msg in conversation['conversation_log']:
                print(f"  {msg}")
        else:
            print(f"❌ Conversația a eșuat: {conversation.get('error', 'Unknown error')}")
            
    elif len(beings) == 1:
        print(f"\n👥 O FIINȚĂ EXISTENTĂ:")
        print(f"  • {beings[0]['identity_role']} - {beings[0]['site_url']}")
        
        print("\n💡 Creez a doua ființă pentru conversație...")
        new_being_id = await manager.create_digital_being_from_site('https://tehnica-antifoc.ro/')
        
        if new_being_id:
            print(f"✅ A doua ființă creată: {new_being_id}")
            
            # Reîmprospătează lista
            beings = manager.list_all_beings()
            
            if len(beings) >= 2:
                print(f"\n💬 CREEZ CONVERSAȚIE ÎNTRE CELE 2 FIINȚE...")
                
                conversation = await manager.create_conversation_between_beings(
                    beings[0]['agent_id'],
                    beings[1]['agent_id'],
                    "colaborare și oportunități de parteneriat"
                )
                
                if conversation.get('success'):
                    print(f"\n🎉 CONVERSAȚIE REUȘITĂ!")
                    print(f"Participanți: {', '.join(conversation['participants'])}")
                    print(f"Mesaje schimbate: {conversation['message_count']}")
                    print(f"\n📝 CONVERSAȚIA:")
                    for msg in conversation['conversation_log']:
                        print(f"  {msg}")
    else:
        print("❌ Nu există ființe în ecosistem")
        print("💡 Creez prima ființă din site-ul tău...")
        
        # Creează prima ființă
        first_being_id = await manager.create_digital_being_from_site('https://tehnica-antifoc.ro/')
        
        if first_being_id:
            print(f"✅ Prima ființă creată: {first_being_id}")
            
            print("💡 Creez a doua ființă pentru conversație...")
            second_being_id = await manager.create_digital_being_from_site('https://tehnica-antifoc.ro/')
            
            if second_being_id:
                print(f"✅ A doua ființă creată: {second_being_id}")
                
                print(f"\n💬 CREEZ CONVERSAȚIE ÎNTRE CELE 2 FIINȚE NOI...")
                
                conversation = await manager.create_conversation_between_beings(
                    first_being_id,
                    second_being_id,
                    "colaborare și oportunități de parteneriat"
                )
                
                if conversation.get('success'):
                    print(f"\n🎉 CONVERSAȚIE REUȘITĂ!")
                    print(f"Participanți: {', '.join(conversation['participants'])}")
                    print(f"Mesaje schimbate: {conversation['message_count']}")
                    print(f"\n📝 CONVERSAȚIA:")
                    for msg in conversation['conversation_log']:
                        print(f"  {msg}")
    
    # Afișează statistici finale
    stats = manager.get_ecosystem_stats()
    print(f"\n📊 STATISTICI ECOSISTEM:")
    print(f"Total ființe active: {stats.get('total_active_beings', 0)}")
    
    if stats.get('roles_distribution'):
        print(f"Distribuție roluri: {stats['roles_distribution']}")
    
    if stats.get('expertise_distribution'):
        print(f"Distribuție expertiză: {stats['expertise_distribution']}")

if __name__ == "__main__":
    asyncio.run(main())
