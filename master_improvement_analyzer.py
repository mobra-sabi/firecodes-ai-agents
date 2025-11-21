#!/usr/bin/env python3
"""
📊 MASTER IMPROVEMENT ANALYZER
==============================

Analizează slave agents și generează plan de îmbunătățire pentru master:
1. Compară servicii master vs slaves
2. Identifică gap-uri în keywords
3. Analizează conținut și strategie
4. Generează action plan complet
"""

import json
from typing import Dict, List, Any
from pymongo import MongoClient
from qdrant_client import QdrantClient
from bson import ObjectId
from llm_orchestrator import get_orchestrator

class MasterImprovementAnalyzer:
    """Analizează competiția și generează plan de îmbunătățire"""
    
    def __init__(self):
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.ai_agents_db
        self.qdrant = QdrantClient("localhost", port=6333)
        self.llm = get_orchestrator()
    
    def analyze_and_improve(self, master_agent_id: str):
        """Analiză completă și generare plan îmbunătățire"""
        
        print("=" * 80)
        print("📊 MASTER IMPROVEMENT ANALYSIS")
        print("=" * 80)
        
        # 1. Get master agent
        master = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        if not master:
            raise ValueError(f"Master agent {master_agent_id} not found")
        
        master_domain = master.get('domain', 'unknown')
        print(f"\n🎯 Master: {master_domain}")
        
        # 2. Get slave agents
        relationships = list(self.db.agent_relationships.find({
            "master_id": ObjectId(master_agent_id),
            "relationship_type": "competitor"
        }))
        
        print(f"   Slave agents: {len(relationships)}")
        
        if len(relationships) == 0:
            print("❌ Nu există slave agents pentru comparație!")
            return None
        
        # 3. Colectează date despre slaves
        slaves_data = self._collect_slaves_data(relationships)
        
        # 4. Compară master cu slaves
        comparison = self._compare_master_vs_slaves(master, slaves_data)
        
        # 5. Generează improvement plan cu DeepSeek
        improvement_plan = self._generate_improvement_plan(
            master_domain,
            comparison
        )
        
        # 6. Salvează în MongoDB
        self._save_improvement_plan(master_agent_id, improvement_plan, comparison)
        
        # 7. Raport
        self._print_report(master_domain, comparison, improvement_plan)
        
        return improvement_plan
    
    def _collect_slaves_data(self, relationships: List[Dict]) -> List[Dict]:
        """Colectează date despre toți slave agents"""
        
        slaves_data = []
        
        for rel in relationships:
            slave = self.db.site_agents.find_one({"_id": rel['slave_id']})
            
            if not slave:
                continue
            
            # Extrage informații relevante
            slave_info = {
                "domain": slave.get('domain', 'unknown'),
                "url": slave.get('site_url', ''),
                "chunks": slave.get('chunks_indexed', 0),
                "services": self._extract_services(slave),
                "keywords": rel.get('competitor_data', {}).get('keywords_matched', []),
                "relevance_score": rel.get('competitor_data', {}).get('relevance_score', 0),
                "metadata": slave.get('learning_metadata', {})
            }
            
            slaves_data.append(slave_info)
        
        print(f"\n📊 Date colectate pentru {len(slaves_data)} slaves")
        
        return slaves_data
    
    def _extract_services(self, agent: Dict) -> List[str]:
        """Extrage servicii din agent config"""
        agent_config = agent.get('agent_config', {})
        services = agent_config.get('services', [])
        
        if isinstance(services, list):
            return [s.get('name', s) if isinstance(s, dict) else str(s) for s in services]
        
        return []
    
    def _compare_master_vs_slaves(
        self,
        master: Dict,
        slaves_data: List[Dict]
    ) -> Dict:
        """Compară master cu slaves"""
        
        print(f"\n{'='*80}")
        print(f"🔍 COMPARAȚIE MASTER VS SLAVES")
        print(f"{'='*80}")
        
        # Master data
        master_chunks = master.get('chunks_indexed', 0)
        master_services = self._extract_services(master)
        master_domain = master.get('domain', 'unknown')
        
        # Slaves aggregate data
        total_slave_chunks = sum(s['chunks'] for s in slaves_data)
        avg_slave_chunks = total_slave_chunks / len(slaves_data) if slaves_data else 0
        
        # Colectează toate serviciile și keywords de la slaves
        all_slave_services = set()
        all_slave_keywords = set()
        
        for slave in slaves_data:
            all_slave_services.update(slave['services'])
            all_slave_keywords.update(slave['keywords'])
        
        # Gap analysis
        services_gap = list(all_slave_services - set(master_services))
        
        # Slaves cu mai multe chunks decât master
        stronger_competitors = [
            s for s in slaves_data
            if s['chunks'] > master_chunks
        ]
        
        comparison = {
            "master": {
                "domain": master_domain,
                "chunks": master_chunks,
                "services": master_services,
                "services_count": len(master_services)
            },
            "slaves": {
                "count": len(slaves_data),
                "total_chunks": total_slave_chunks,
                "avg_chunks": avg_slave_chunks,
                "all_services": list(all_slave_services),
                "all_keywords": list(all_slave_keywords),
                "stronger_competitors": len(stronger_competitors)
            },
            "gaps": {
                "services_missing": services_gap,
                "chunks_below_avg": master_chunks < avg_slave_chunks,
                "competitors_ahead": len(stronger_competitors)
            },
            "opportunities": {
                "new_keywords": list(all_slave_keywords),
                "service_expansion": services_gap[:10],
                "content_volume": "increase" if master_chunks < avg_slave_chunks else "maintain"
            }
        }
        
        print(f"\n📊 Master: {master_chunks} chunks, {len(master_services)} services")
        print(f"📊 Slaves: avg {avg_slave_chunks:.0f} chunks, {len(all_slave_services)} unique services")
        print(f"⚠️ Gap: {len(services_gap)} servicii lipsesc, {len(stronger_competitors)} competitori mai puternici")
        
        return comparison
    
    def _generate_improvement_plan(
        self,
        master_domain: str,
        comparison: Dict
    ) -> Dict:
        """Generează plan de îmbunătățire cu DeepSeek"""
        
        print(f"\n{'='*80}")
        print(f"🧠 GENERARE IMPROVEMENT PLAN (DeepSeek)")
        print(f"{'='*80}")
        
        # Construiește prompt pentru DeepSeek
        prompt = f"""Analizează competiția și generează plan de îmbunătățire pentru {master_domain}.

MASTER (actual):
- Chunks: {comparison['master']['chunks']}
- Servicii: {comparison['master']['services_count']}
- Lista servicii: {', '.join(comparison['master']['services'][:10])}

COMPETITORI ({comparison['slaves']['count']} slaves):
- Chunks medii: {comparison['slaves']['avg_chunks']:.0f}
- Servicii unice: {len(comparison['slaves']['all_services'])}
- Competitori mai puternici: {comparison['gaps']['competitors_ahead']}

GAP-URI IDENTIFICATE:
- Servicii lipsă: {', '.join(comparison['gaps']['services_missing'][:5])}
- Keywords competitori: {', '.join(comparison['opportunities']['new_keywords'][:10])}
- Volum content: {"sub medie" if comparison['gaps']['chunks_below_avg'] else "peste medie"}

Generează plan ACȚIONABIL în format JSON:
{{
  "priority_actions": [
    {{
      "action": "Descriere acțiune",
      "reason": "De ce e important",
      "impact": "high/medium/low",
      "effort": "low/medium/high",
      "expected_result": "Rezultat așteptat"
    }}
  ],
  "service_improvements": [
    {{
      "service": "Nume serviciu",
      "action": "Ce să adaugi/îmbunătățești",
      "competitors_doing_it": ["domain1", "domain2"]
    }}
  ],
  "keyword_strategy": [
    {{
      "keyword": "keyword",
      "priority": "high/medium/low",
      "usage": "Cum să-l folosești"
    }}
  ],
  "content_strategy": {{
    "current_volume": {comparison['master']['chunks']},
    "target_volume": "number",
    "focus_areas": ["area1", "area2"]
  }}
}}
"""
        
        print(f"🎭 Trimit către DeepSeek...")
        
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=3000
        )
        
        if not response.get("success"):
            print(f"❌ DeepSeek failed: {response.get('error', 'Unknown')}")
            return None
        
        print(f"✅ Plan generat!")
        print(f"   Provider: {response['provider']}")
        print(f"   Tokens: {response.get('tokens', 0)}")
        
        # Parse JSON
        import re
        content = response['content']
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            plan = json.loads(content)
            return plan
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
            # Returnează plan minimal
            return {
                "priority_actions": [],
                "service_improvements": [],
                "keyword_strategy": [],
                "content_strategy": {},
                "raw_response": content
            }
    
    def _save_improvement_plan(
        self,
        master_agent_id: str,
        improvement_plan: Dict,
        comparison: Dict
    ):
        """Salvează planul în MongoDB"""
        
        self.db.improvement_plans.replace_one(
            {"master_agent_id": master_agent_id},
            {
                "master_agent_id": master_agent_id,
                "improvement_plan": improvement_plan,
                "comparison_data": comparison,
                "created_at": datetime.now(),
                "status": "pending",
                "actions_completed": []
            },
            upsert=True
        )
        
        print(f"\n💾 Plan salvat în MongoDB!")
    
    def _print_report(
        self,
        master_domain: str,
        comparison: Dict,
        improvement_plan: Dict
    ):
        """Afișează raport final"""
        
        print(f"\n{'='*80}")
        print(f"📊 RAPORT FINAL - {master_domain.upper()}")
        print(f"{'='*80}")
        
        print(f"\n🎯 SITUAȚIE ACTUALĂ:")
        print(f"   Master chunks: {comparison['master']['chunks']}")
        print(f"   Competitori mediu: {comparison['slaves']['avg_chunks']:.0f} chunks")
        print(f"   Gap: {comparison['slaves']['avg_chunks'] - comparison['master']['chunks']:.0f} chunks")
        
        print(f"\n⚠️ GAP-URI:")
        print(f"   Servicii lipsă: {len(comparison['gaps']['services_missing'])}")
        if comparison['gaps']['services_missing'][:5]:
            for svc in comparison['gaps']['services_missing'][:5]:
                print(f"      • {svc}")
        
        print(f"\n🎯 TOP 5 ACȚIUNI PRIORITARE:")
        for idx, action in enumerate(improvement_plan.get('priority_actions', [])[:5], 1):
            print(f"\n   {idx}. {action.get('action', 'N/A')}")
            print(f"      Impact: {action.get('impact', 'N/A')}")
            print(f"      Effort: {action.get('effort', 'N/A')}")
            print(f"      Rezultat: {action.get('expected_result', 'N/A')[:80]}")
        
        print(f"\n🔑 TOP 10 KEYWORDS DE INTEGRAT:")
        for idx, kw_strategy in enumerate(improvement_plan.get('keyword_strategy', [])[:10], 1):
            print(f"   {idx:2d}. {kw_strategy.get('keyword', 'N/A')} ({kw_strategy.get('priority', 'N/A')})")
        
        print(f"\n{'='*80}")


def main():
    """Run script"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python master_improvement_analyzer.py <master_agent_id>")
        sys.exit(1)
    
    master_id = sys.argv[1]
    
    analyzer = MasterImprovementAnalyzer()
    plan = analyzer.analyze_and_improve(master_id)
    
    if plan:
        print(f"\n✅ IMPROVEMENT PLAN GENERATED!")
    else:
        print(f"\n❌ FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime
    main()

