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
from digital_beings.communication.real_qwen_communication import RealQwenCommunication
from database.mongodb_handler import MongoDBHandler

class RealDigitalBeingsManager:
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.real_communication = RealQwenCommunication()
        self.beings_collection = "real_digital_beings_registry"
        self.init_beings_registry()
        self.display_gpu_status()
        
    def init_beings_registry(self):
        try:
            collection = self.mongodb.db[self.beings_collection]
            collection.create_index("agent_id", unique=True)
            print("✅ Registru ființe digitale REALE inițializat")
        except Exception as e:
            print(f"⚠️ Eroare inițializare registru: {e}")
            
    def display_gpu_status(self):
        active_clusters = self.real_communication.active_clusters
        total_clusters = len(self.real_communication.qwen_clusters)
        print(f"\n🖥️ STATUS GPU CLUSTERS:")
        print(f"   Active: {len(active_clusters)}/{total_clusters}")
        if active_clusters:
            print(f"   Clustere funcționale: {', '.join(active_clusters)}")
        
        if len(active_clusters) == 0:
            print("⚠️ NU EXISTĂ CLUSTERE GPU ACTIVE!")
            print("💡 Pentru conversații REALE:")
            print("   Terminal 1: CUDA_VISIBLE_DEVICES=\"0\" vllm serve Qwen/Qwen2.5-7B-Instruct --port 9301 --gpu-memory-utilization 0.6")
            print("   Terminal 2: CUDA_VISIBLE_DEVICES=\"1\" vllm serve Qwen/Qwen2.5-7B-Instruct --port 9302 --gpu-memory-utilization 0.6")
        
    async def create_real_digital_being_from_site(self, site_url: str) -> str:
        print(f"🧬 Creez ființă digitală REALĂ pentru {site_url}...")
        
        site_content = self.mongodb.get_site_content(site_url)
        if not site_content:
            print(f"❌ Nu găsesc conținut pentru {site_url}")
            return None
            
        content = site_content.get('content', '')
        identity = DigitalIdentity(site_url, content)
        print(f"✅ Identitate REALĂ: {identity.identity['role']}")
        
        memory = EpisodeMemory(identity.agent_id)
        birth_episode = memory.create_episode(
            'birth',
            f"Am fost creat ca {identity.identity['role']} pentru {site_url}.",
            importance=10,
            metadata={'site_url': site_url, 'role': identity.identity['role']}
        )
        print(f"📝 Episod naștere REAL creat: {birth_episode}")
        
        skills = DigitalBeingSkills(identity.agent_id, identity.identity)
        print(f"⚡ Skills REALE cu expertiză în: {identity.identity['expertise']}")
        
        being_registry_entry = {
            'agent_id': identity.agent_id,
            'site_url': site_url,
            'identity_role': identity.identity['role'],
            'identity_mission': identity.identity['mission'],
            'expertise': identity.identity['expertise'],
            'personality': identity.personality,
            'creation_time': identity.birth_timestamp.isoformat(),
            'status': 'active',
            'being_type': 'real_gpu_powered'
        }
        
        try:
            collection = self.mongodb.db[self.beings_collection]
            collection.insert_one(being_registry_entry)
            print(f"📋 Ființă REALĂ înregistrată")
        except Exception as e:
            print(f"⚠️ Eroare înregistrare: {e}")
        
        print(f"🎉 Ființă digitală REALĂ creată: {identity.agent_id}")
        return identity.agent_id
        
    def list_real_beings(self) -> List[Dict]:
        try:
            collection = self.mongodb.db[self.beings_collection]
            beings = list(collection.find({'status': 'active', 'being_type': 'real_gpu_powered'}))
            print(f"👥 Găsite {len(beings)} ființe REALE active")
            return beings
        except Exception as e:
            print(f"❌ Eroare listare ființe REALE: {e}")
            return []
            
    def get_real_being_data(self, agent_id: str) -> Dict:
        try:
            collection = self.mongodb.db[self.beings_collection]
            being_data = collection.find_one({'agent_id': agent_id})
            if being_data:
                print(f"📋 Date REALE găsite pentru {agent_id[:12]}...")
                return being_data
            else:
                print(f"❌ Nu găsesc ființa REALĂ {agent_id}")
                return None
        except Exception as e:
            print(f"❌ Eroare obținere date: {e}")
            return None
            
    async def create_real_gpu_conversation(self, being1_id: str, being2_id: str, topic: str) -> Dict:
        if not self.real_communication.active_clusters:
            return {
                'error': 'Nu există clustere GPU active pentru conversație REALĂ',
                'commands': [
                    'CUDA_VISIBLE_DEVICES="0" vllm serve Qwen/Qwen2.5-7B-Instruct --port 9301 --gpu-memory-utilization 0.6',
                    'CUDA_VISIBLE_DEVICES="1" vllm serve Qwen/Qwen2.5-7B-Instruct --port 9302 --gpu-memory-utilization 0.6'
                ]
            }
            
        being1_data = self.get_real_being_data(being1_id)
        being2_data = self.get_real_being_data(being2_id)
        
        if not being1_data or not being2_data:
            return {'error': 'Nu s-au găsit datele ființelor REALE'}
            
        print(f"🧠 Creez conversație REALĂ cu GPU:")
        print(f"   {being1_data['identity_role']} ↔ {being2_data['identity_role']}")
        print(f"   Subiect: {topic}")
        
        conversation = await self.real_communication.create_real_conversation(
            being1_data, being2_data, topic, message_count=6
        )
        
        if conversation.get('success'):
            memory1 = EpisodeMemory(being1_id)
            memory2 = EpisodeMemory(being2_id)
            
            memory1.create_episode(
                'real_gpu_conversation',
                f"Conversație REALĂ cu GPU cu {being2_data['identity_role']} despre {topic}",
                importance=8,
                metadata={'other_being': being2_id, 'topic': topic}
            )
            
            memory2.create_episode(
                'real_gpu_conversation',
                f"Conversație REALĂ cu GPU cu {being1_data['identity_role']} despre {topic}",
                importance=8,
                metadata={'other_being': being1_id, 'topic': topic}
            )
            
            print("✅ Conversație REALĂ completă + memorii salvate!")
            
        return conversation

async def main():
    manager = RealDigitalBeingsManager()
    
    print("🚀 REAL DIGITAL BEINGS ECOSYSTEM cu GPU QWEN")
    print("=" * 60)
    
    if not manager.real_communication.active_clusters:
        print("\n❌ NU EXISTĂ CLUSTERE GPU ACTIVE!")
        print("💡 Pornește clusterele cu comenzile de mai sus")
        print("⚠️ Continuă cu crearea ființelor...")
    
    real_beings = manager.list_real_beings()
    
    if len(real_beings) >= 2:
        print(f"\n👥 FIINȚE REALE EXISTENTE ({len(real_beings)}):")
        for being in real_beings:
            print(f"  • {being['identity_role']} - {being['site_url']}")
            
        if manager.real_communication.active_clusters:
            print(f"\n🧠 CREEZ CONVERSAȚIE REALĂ cu GPU...")
            
            conversation = await manager.create_real_gpu_conversation(
                real_beings[0]['agent_id'],
                real_beings[1]['agent_id'],
                "strategii de protecție la incendiu și inovații"
            )
            
            if conversation.get('success'):
                print(f"\n🎉 CONVERSAȚIE REALĂ REUȘITĂ!")
                print(f"🧠 Clustere GPU: {', '.join(conversation.get('clusters_used', []))}")
                print(f"👥 Participanți: {', '.join(conversation['participants'])}")
                print(f"💬 Mesaje AI: {conversation['message_count']}")
                
                print(f"\n📝 CONVERSAȚIA REALĂ:")
                for i, msg in enumerate(conversation['conversation_log'], 1):
                    print(f"  {i}. {msg}")
                    
            else:
                print(f"❌ Conversația a eșuat: {conversation.get('error', 'N/A')}")
                if 'commands' in conversation:
                    print("\n💡 Comenzi GPU:")
                    for cmd in conversation['commands']:
                        print(f"   {cmd}")
    else:
        print("🧬 Creez primele două ființe REALE...")
        
        first_being_id = await manager.create_real_digital_being_from_site('https://tehnica-antifoc.ro/')
        
        if first_being_id:
            print(f"✅ Prima ființă REALĂ: {first_being_id[:12]}...")
            
            second_being_id = await manager.create_real_digital_being_from_site('https://tehnica-antifoc.ro/')
            
            if second_being_id:
                print(f"✅ A doua ființă REALĂ: {second_being_id[:12]}...")
                
                if manager.real_communication.active_clusters:
                    print(f"\n🧠 PRIMA CONVERSAȚIE REALĂ cu GPU...")
                    
                    conversation = await manager.create_real_gpu_conversation(
                        first_being_id,
                        second_being_id,
                        "viitorul protecției la incendiu"
                    )
                    
                    if conversation.get('success'):
                        print(f"\n🎉 PRIMA CONVERSAȚIE REALĂ REUȘITĂ!")
                        print(f"💬 Mesaje AI: {conversation['message_count']}")
                        
                        print(f"\n📝 CONVERSAȚIA:")
                        for i, msg in enumerate(conversation['conversation_log'], 1):
                            print(f"  {i}. {msg}")

if __name__ == "__main__":
    asyncio.run(main())
