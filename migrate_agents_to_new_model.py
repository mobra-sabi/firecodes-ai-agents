#!/usr/bin/env python3
"""
Script de migrare agenți existenți la noul model pe 4 straturi
Transformă agenții din structura veche la noul format conform checklist-ului
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentMigrator:
    """Migrator pentru agenții existenți la noul model"""
    
    def __init__(self):
        # Conectare la MongoDB
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:9308/')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.ai_agents_db
        
        # Încarcă manifest-ul nou
        self.new_manifest = self._load_new_manifest()
        
    def _load_new_manifest(self) -> Dict:
        """Încarcă manifest-ul nou din YAML"""
        try:
            with open('/srv/hf/ai_agents/agent_manifest.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Eroare la încărcarea manifest-ului: {e}")
            return {}
    
    def analyze_existing_agents(self) -> List[Dict]:
        """Analizează agenții existenți"""
        logger.info("🔍 Analizez agenții existenți...")
        
        agents = list(self.db.agents.find())
        logger.info(f"Găsiți {len(agents)} agenți existenți")
        
        analysis = []
        for agent in agents:
            agent_analysis = {
                'id': str(agent['_id']),
                'name': agent.get('name', 'N/A'),
                'domain': agent.get('domain', 'N/A'),
                'site_url': agent.get('site_url', 'N/A'),
                'status': agent.get('status', 'N/A'),
                'created_at': agent.get('createdAt', 'N/A'),
                'updated_at': agent.get('updatedAt', 'N/A'),
                'needs_migration': True,
                'migration_priority': 'high' if agent.get('status') == 'ready' else 'medium'
            }
            
            # Verifică dacă are conținut indexat
            content_count = self.db.site_content.count_documents({'agent_id': agent['_id']})
            agent_analysis['content_pages'] = content_count
            
            # Verifică conversații
            conv_count = self.db.conversations.count_documents({'agent_id': agent['_id']})
            agent_analysis['conversations'] = conv_count
            
            analysis.append(agent_analysis)
        
        return analysis
    
    def create_new_agent_structure(self, old_agent: Dict) -> Dict:
        """Creează structura nouă pentru un agent"""
        logger.info(f"🔄 Creez structura nouă pentru agent {old_agent.get('name')}")
        
        # Extrage informații din agentul vechi
        domain = old_agent.get('domain', 'unknown')
        site_url = old_agent.get('site_url', '')
        name = old_agent.get('name', f'Agent {domain}')
        
        # Creează structura nouă conform manifest-ului
        new_agent = {
            # Identitate & Scop
            'identity': {
                'name': name,
                'role': 'Reprezentant oficial al site-ului web',
                'domain': domain,
                'purpose': f'Transformă site-ul {site_url} într-un agent AI competent',
                'capabilities': [
                    'Răspunde la întrebări despre servicii și produse',
                    'Oferă consultanță și recomandări',
                    'Caută informații în conținutul site-ului',
                    'Comunică ca reprezentant oficial',
                    'Escalează la om când este necesar'
                ],
                'limitations': [
                    'Nu poate accesa informații din afara site-ului',
                    'Nu poate face tranzacții financiare',
                    'Nu poate accesa conturi personale',
                    'Nu poate modifica conținutul site-ului'
                ]
            },
            
            # Contract de Capabilități
            'contract': {
                'knows': [
                    'Toate serviciile și produsele site-ului',
                    'Informații despre companie și echipă',
                    'Politici și proceduri',
                    'FAQ și ghiduri'
                ],
                'doesnt_know': [
                    'Informații personale ale clienților',
                    'Detalii financiare confidențiale',
                    'Informații din afara site-ului',
                    'Starea în timp real a stocurilor'
                ],
                'escalation_triggers': [
                    'Întrebări despre prețuri specifice',
                    'Probleme tehnice complexe',
                    'Cereri de modificări pe site',
                    'Informații confidențiale'
                ]
            },
            
            # Percepție (Ingest & Înțelegere)
            'perception': {
                'crawler': {
                    'max_pages': 20,
                    'timeout': 30,
                    'rate_limit': 1,
                    'user_agent': 'Mozilla/5.0 (compatible; SiteAI/1.0)'
                },
                'content_processing': {
                    'chunk_size': 1000,
                    'chunk_overlap': 200,
                    'min_chunk_size': 100,
                    'max_chunk_size': 2000
                },
                'normalization': {
                    'remove_scripts': True,
                    'remove_styles': True,
                    'remove_navigation': True,
                    'clean_whitespace': True,
                    'extract_metadata': True
                },
                'site_url': site_url,
                'last_crawl': old_agent.get('updatedAt', datetime.now(timezone.utc))
            },
            
            # Memorie
            'memory': {
                'working_memory': {
                    'max_conversation_turns': 10,
                    'context_window': 4000
                },
                'long_term_memory': {
                    'vector_db': 'qdrant',
                    'collection_name': f'agent_{str(old_agent["_id"])}_content',
                    'embedding_model': 'BAAI/bge-large-en-v1.5'
                },
                'retention_policy': {
                    'conversation_ttl': '7 days',
                    'content_ttl': '30 days',
                    'max_storage_size': '1GB'
                }
            },
            
            # Raționare (LLM)
            'reasoning': {
                'llm': {
                    'model': 'qwen2.5:7b',
                    'temperature': 0.7,
                    'max_tokens': 1000,
                    'timeout': 60
                },
                'planning': {
                    'max_steps': 3,
                    'reflection_enabled': True,
                    'source_citation': True
                },
                'verification': {
                    'confidence_threshold': 0.7,
                    'auto_verify': True,
                    'fallback_response': 'Nu știu răspunsul exact. Vă pot conecta cu echipa noastră de specialiști.'
                }
            },
            
            # Acțiune (Tools)
            'tools': {
                'search_index': {
                    'description': 'Caută informații în conținutul site-ului',
                    'max_results': 5,
                    'similarity_threshold': 0.7
                },
                'fetch_url': {
                    'description': 'Descarcă conținut de pe o pagină specifică',
                    'allowed_domains': [site_url],
                    'max_size': '1MB'
                },
                'calculate': {
                    'description': 'Efectuează calcule simple',
                    'sandbox': True,
                    'timeout': 10
                }
            },
            
            # Interfețe
            'interfaces': {
                'api': {
                    'endpoints': ['/ask', '/search', '/status'],
                    'methods': ['POST', 'GET']
                },
                'ui': {
                    'type': 'chat_interface',
                    'features': [
                        'conversație în timp real',
                        'căutare în conținut',
                        'istoric conversații',
                        'feedback utilizator'
                    ]
                },
                'webhooks': {
                    'events': [
                        'conversation_started',
                        'escalation_triggered',
                        'error_occurred'
                    ]
                }
            },
            
            # Securitate & Conformitate
            'security': {
                'rate_limiting': {
                    'requests_per_minute': 60,
                    'burst_limit': 10
                },
                'authentication': {
                    'api_key_required': False,
                    'session_based': True
                },
                'privacy': {
                    'pii_detection': True,
                    'pii_scrubbing': True,
                    'audit_logging': True
                },
                'compliance': {
                    'gdpr_compliant': True,
                    'data_retention': '30 days',
                    'right_to_deletion': True
                }
            },
            
            # Evaluare & Monitorizare
            'monitoring': {
                'metrics': [
                    'response_time',
                    'accuracy_rate',
                    'escalation_rate',
                    'user_satisfaction'
                ],
                'alerts': [
                    'high_error_rate',
                    'slow_response',
                    'escalation_spike'
                ],
                'evaluation': {
                    'test_questions': 50,
                    'evaluation_frequency': 'weekly',
                    'a_b_testing': True
                }
            },
            
            # Configurații specifice
            'config': {
                'language': 'romanian',
                'timezone': 'Europe/Bucharest',
                'currency': 'RON',
                'date_format': 'DD/MM/YYYY',
                'fallback_responses': {
                    'no_answer': 'Îmi pare rău, nu am găsit informația în conținutul site-ului nostru. Vă pot conecta cu echipa noastră de specialiști.',
                    'error': 'A apărut o problemă tehnică. Te rog încearcă din nou sau contactează-ne direct.',
                    'escalation': 'Pentru această întrebare, vă recomand să contactați echipa noastră de specialiști.'
                }
            },
            
            # Metadata migrare
            'migration': {
                'migrated_from': str(old_agent['_id']),
                'migration_date': datetime.now(timezone.utc),
                'migration_version': '1.0',
                'original_structure': {
                    'name': old_agent.get('name'),
                    'domain': old_agent.get('domain'),
                    'site_url': old_agent.get('site_url'),
                    'status': old_agent.get('status'),
                    'created_at': old_agent.get('createdAt'),
                    'updated_at': old_agent.get('updatedAt')
                }
            },
            
            # Câmpuri pentru compatibilitate
            '_id': old_agent['_id'],
            'name': name,
            'domain': domain,
            'site_url': site_url,
            'status': 'migrated',
            'createdAt': old_agent.get('createdAt', datetime.now(timezone.utc)),
            'updatedAt': datetime.now(timezone.utc),
            'version': '2.0',
            'architecture': '4-layer'
        }
        
        return new_agent
    
    def migrate_agent(self, old_agent: Dict, dry_run: bool = True) -> Dict:
        """Migrează un agent la noul model"""
        agent_id = str(old_agent['_id'])
        agent_name = old_agent.get('name', 'Unknown')
        
        logger.info(f"🔄 Migrez agent {agent_name} (ID: {agent_id})")
        
        # Creează structura nouă
        new_agent = self.create_new_agent_structure(old_agent)
        
        if dry_run:
            logger.info(f"✅ [DRY RUN] Agent {agent_name} ar fi migrat cu succes")
            return new_agent
        
        try:
            # Actualizează agentul în baza de date
            result = self.db.agents.update_one(
                {'_id': old_agent['_id']},
                {'$set': new_agent}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Agent {agent_name} migrat cu succes")
                
                # Creează entry în log-ul de migrare
                migration_log = {
                    'agent_id': old_agent['_id'],
                    'agent_name': agent_name,
                    'migration_date': datetime.now(timezone.utc),
                    'migration_version': '1.0',
                    'status': 'success',
                    'changes': {
                        'architecture': '4-layer',
                        'version': '2.0',
                        'status': 'migrated'
                    }
                }
                
                self.db.migration_logs.insert_one(migration_log)
                
                return new_agent
            else:
                logger.error(f"❌ Eroare la migrarea agentului {agent_name}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Eroare la migrarea agentului {agent_name}: {e}")
            return {}
    
    def migrate_all_agents(self, dry_run: bool = True) -> Dict:
        """Migrează toți agenții la noul model"""
        logger.info("🚀 Încep migrarea tuturor agenților...")
        
        # Analizează agenții existenți
        analysis = self.analyze_existing_agents()
        
        results = {
            'total_agents': len(analysis),
            'migrated': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for agent_analysis in analysis:
            agent_id = agent_analysis['id']
            agent_name = agent_analysis['name']
            
            # Ia agentul complet din DB
            old_agent = self.db.agents.find_one({'_id': ObjectId(agent_id)})
            if not old_agent:
                logger.warning(f"⚠️ Agent {agent_name} nu a fost găsit în DB")
                results['skipped'] += 1
                continue
            
            # Migrează agentul
            new_agent = self.migrate_agent(old_agent, dry_run)
            
            if new_agent:
                results['migrated'] += 1
                results['details'].append({
                    'id': agent_id,
                    'name': agent_name,
                    'status': 'success',
                    'architecture': '4-layer',
                    'version': '2.0'
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'id': agent_id,
                    'name': agent_name,
                    'status': 'failed'
                })
        
        return results
    
    def validate_migration(self) -> Dict:
        """Validează că migrarea a fost realizată corect"""
        logger.info("🔍 Validez migrarea...")
        
        validation = {
            'total_agents': 0,
            'migrated_agents': 0,
            'validation_errors': [],
            'details': []
        }
        
        agents = list(self.db.agents.find())
        validation['total_agents'] = len(agents)
        
        for agent in agents:
            agent_id = str(agent['_id'])
            agent_name = agent.get('name', 'Unknown')
            
            # Verifică dacă are structura nouă
            has_identity = 'identity' in agent
            has_contract = 'contract' in agent
            has_perception = 'perception' in agent
            has_memory = 'memory' in agent
            has_reasoning = 'reasoning' in agent
            has_tools = 'tools' in agent
            has_interfaces = 'interfaces' in agent
            has_security = 'security' in agent
            has_monitoring = 'monitoring' in agent
            has_config = 'config' in agent
            has_migration = 'migration' in agent
            
            is_migrated = all([
                has_identity, has_contract, has_perception, has_memory,
                has_reasoning, has_tools, has_interfaces, has_security,
                has_monitoring, has_config, has_migration
            ])
            
            if is_migrated:
                validation['migrated_agents'] += 1
                validation['details'].append({
                    'id': agent_id,
                    'name': agent_name,
                    'status': 'migrated',
                    'architecture': agent.get('architecture', 'unknown'),
                    'version': agent.get('version', 'unknown')
                })
            else:
                missing_fields = []
                if not has_identity: missing_fields.append('identity')
                if not has_contract: missing_fields.append('contract')
                if not has_perception: missing_fields.append('perception')
                if not has_memory: missing_fields.append('memory')
                if not has_reasoning: missing_fields.append('reasoning')
                if not has_tools: missing_fields.append('tools')
                if not has_interfaces: missing_fields.append('interfaces')
                if not has_security: missing_fields.append('security')
                if not has_monitoring: missing_fields.append('monitoring')
                if not has_config: missing_fields.append('config')
                if not has_migration: missing_fields.append('migration')
                
                validation['validation_errors'].append({
                    'id': agent_id,
                    'name': agent_name,
                    'missing_fields': missing_fields
                })
        
        return validation
    
    def generate_migration_report(self, results: Dict) -> str:
        """Generează raport de migrare"""
        report = f"""
# 📊 RAPORT MIGRARE AGENȚI LA NOUL MODEL

**Data migrării:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
**Versiune nouă:** 2.0 (4-layer architecture)

## 📈 REZULTATE MIGRARE

- **Total agenți:** {results['total_agents']}
- **Migrați cu succes:** {results['migrated']}
- **Eșuați:** {results['failed']}
- **Săriți:** {results['skipped']}

## 📋 DETALII MIGRARE

"""
        
        for detail in results['details']:
            status_emoji = "✅" if detail['status'] == 'success' else "❌"
            report += f"- {status_emoji} **{detail['name']}** (ID: {detail['id']})\n"
            if detail['status'] == 'success':
                report += f"  - Arhitectură: {detail.get('architecture', 'N/A')}\n"
                report += f"  - Versiune: {detail.get('version', 'N/A')}\n"
            report += "\n"
        
        return report

def main():
    """Funcția principală"""
    print("🚀 MIGRARE AGENȚI LA NOUL MODEL PE 4 STRATURI")
    print("=" * 60)
    
    migrator = AgentMigrator()
    
    # Analizează agenții existenți
    print("\n1️⃣ Analizez agenții existenți...")
    analysis = migrator.analyze_existing_agents()
    
    print(f"Găsiți {len(analysis)} agenți:")
    for agent in analysis[:5]:  # Primele 5
        print(f"  - {agent['name']} ({agent['domain']}) - {agent['status']}")
    
    # Întreabă utilizatorul
    print(f"\n2️⃣ Vrei să migrez toți cei {len(analysis)} agenți?")
    print("Opțiuni:")
    print("  1. Dry run (doar simulează migrarea)")
    print("  2. Migrare reală")
    print("  3. Validează migrarea existentă")
    print("  4. Ieșire")
    
    choice = input("\nAlege opțiunea (1-4): ").strip()
    
    if choice == '1':
        print("\n🔄 Execut dry run...")
        results = migrator.migrate_all_agents(dry_run=True)
        print(migrator.generate_migration_report(results))
        
    elif choice == '2':
        confirm = input(f"\n⚠️ Ești sigur că vrei să migrezi toți cei {len(analysis)} agenți? (da/nu): ").strip().lower()
        if confirm == 'da':
            print("\n🔄 Execut migrarea...")
            results = migrator.migrate_all_agents(dry_run=False)
            print(migrator.generate_migration_report(results))
            
            # Salvează raportul
            with open('/srv/hf/ai_agents/migration_report.md', 'w', encoding='utf-8') as f:
                f.write(migrator.generate_migration_report(results))
            print("\n📄 Raportul a fost salvat în migration_report.md")
        else:
            print("❌ Migrarea a fost anulată")
            
    elif choice == '3':
        print("\n🔍 Validez migrarea...")
        validation = migrator.validate_migration()
        print(f"Total agenți: {validation['total_agents']}")
        print(f"Migrați: {validation['migrated_agents']}")
        print(f"Erori: {len(validation['validation_errors'])}")
        
        if validation['validation_errors']:
            print("\n❌ Erori de validare:")
            for error in validation['validation_errors']:
                print(f"  - {error['name']}: lipsesc {', '.join(error['missing_fields'])}")
        
    elif choice == '4':
        print("👋 La revedere!")
        
    else:
        print("❌ Opțiune invalidă")
    
    migrator.client.close()

if __name__ == "__main__":
    main()


