#!/usr/bin/env python3
"""
🔍 DEEPSEEK + SERP DISCOVERY COMPLET
====================================

Workflow:
1. DeepSeek → sparge site în subdomenii + keywords
2. Pentru fiecare keyword → SERP search (Brave/Google)
3. Colectează 10-15 site-uri per keyword
4. Salvează în MongoDB pentru procesare ulterioară
"""

import json
import time
from typing import Dict, List, Any
from pymongo import MongoClient
from qdrant_client import QdrantClient
from bson import ObjectId
from datetime import datetime
from llm_orchestrator import get_orchestrator
from tools.serp_client import _brave_search

class DeepSeekSerpDiscovery:
    """DeepSeek Analysis + SERP Discovery pe fiecare keyword"""
    
    def __init__(self):
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.ai_agents_db
        self.qdrant = QdrantClient("localhost", port=6333)
        self.llm = get_orchestrator()
    
    def analyze_and_discover(self, agent_id: str, max_results_per_keyword: int = 15):
        """
        Proces complet:
        1. Get agent context
        2. DeepSeek analysis → subdomenii + keywords
        3. SERP search pentru fiecare keyword
        4. Salvează rezultate în MongoDB
        """
        
        print("=" * 80)
        print(f"🚀 DEEPSEEK + SERP DISCOVERY COMPLET")
        print("=" * 80)
        
        # 1. Get agent
        agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        domain = agent.get('domain', 'unknown')
        print(f"\n🎯 Agent: {domain}")
        
        # 2. Get context from Qdrant
        collection_name = agent.get('vector_collection', '')
        context_text = ""
        
        if collection_name:
            try:
                results = self.qdrant.scroll(collection_name=collection_name, limit=10)
                for chunk in results[0]:
                    context_text += chunk.payload.get('chunk_text', '') + "\n\n"
                print(f"📄 Context: {len(context_text)} chars")
            except Exception as e:
                print(f"⚠️ Qdrant error: {e}")
                context_text = f"Domain: {domain}\nURL: {agent.get('site_url', '')}"
        
        # 3. DeepSeek Analysis
        print(f"\n{'='*80}")
        print(f"🧠 STEP 1: DEEPSEEK ANALYSIS")
        print(f"{'='*80}")
        
        analysis_result = self._deepseek_analysis(domain, context_text)
        
        if not analysis_result:
            print("❌ DeepSeek analysis failed!")
            return None
        
        subdomains = analysis_result.get('subdomains', [])
        keywords = analysis_result.get('keywords', [])
        
        print(f"✅ Subdomenii: {len(subdomains)}")
        print(f"✅ Keywords: {len(keywords)}")
        
        # Salvează analysis
        self.db.competitive_analysis.replace_one(
            {"agent_id": agent_id},
            {
                "agent_id": agent_id,
                "domain": domain,
                "subdomains": subdomains,
                "keywords": keywords,
                "timestamp": datetime.now().isoformat(),
                "provider": "deepseek"
            },
            upsert=True
        )
        
        # 4. SERP Discovery per keyword
        print(f"\n{'='*80}")
        print(f"🔍 STEP 2: SERP DISCOVERY PER KEYWORD")
        print(f"{'='*80}")
        
        serp_results = self._serp_discovery_all_keywords(
            keywords[:20],  # Limit la 20 keywords pentru a nu exploda
            max_results_per_keyword
        )
        
        # 5. Salvează SERP results
        self._save_serp_results(agent_id, domain, keywords, serp_results)
        
        # 6. Raport final
        print(f"\n{'='*80}")
        print(f"📊 RAPORT FINAL")
        print(f"{'='*80}")
        
        total_urls = sum(len(urls) for urls in serp_results.values())
        unique_domains = self._extract_unique_domains(serp_results)
        
        print(f"✅ Keywords procesate: {len(serp_results)}")
        print(f"✅ Total URL-uri găsite: {total_urls}")
        print(f"✅ Domenii unice: {len(unique_domains)}")
        
        print(f"\n🔝 TOP 10 DOMENII GĂSITE:")
        for idx, (domain, count) in enumerate(list(unique_domains.items())[:10], 1):
            print(f"   {idx:2d}. {domain}: {count} apariții")
        
        return {
            "agent_id": agent_id,
            "domain": domain,
            "subdomains": subdomains,
            "keywords_processed": len(serp_results),
            "total_urls": total_urls,
            "unique_domains": len(unique_domains),
            "serp_results": serp_results
        }
    
    def _deepseek_analysis(self, domain: str, context: str) -> Dict:
        """DeepSeek analysis pentru subdomenii + keywords"""
        
        prompt = f"""Analizează următorul context despre compania {domain}:

{context[:3000]}

Identifică:
1. 5-7 subdomenii principale de activitate (segmente de business)
2. Pentru fiecare subdomeniu, generează 3-5 keywords strategice
3. Generează și 10-15 keywords generale pentru industrie

Răspunde DOAR în format JSON:
{{
  "subdomains": [
    {{
      "name": "Nume subdomeniu",
      "description": "Descriere scurtă",
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ],
  "keywords": ["keyword general 1", "keyword general 2", ...]
}}
"""
        
        print(f"🎭 Trimit către DeepSeek...")
        
        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        if not response.get("success"):
            print(f"❌ DeepSeek failed: {response.get('error', 'Unknown')}")
            return None
        
        print(f"✅ DeepSeek răspuns primit!")
        print(f"   Provider: {response['provider']}")
        print(f"   Tokens: {response.get('tokens', 0)}")
        
        # Parse JSON
        import re
        content = response['content']
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        try:
            data = json.loads(content)
            return data
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
            return None
    
    def _serp_discovery_all_keywords(
        self,
        keywords: List[str],
        max_results_per_keyword: int
    ) -> Dict[str, List[str]]:
        """SERP search pentru toate keywords"""
        
        results = {}
        
        for idx, keyword in enumerate(keywords, 1):
            print(f"\n🔎 [{idx}/{len(keywords)}] Searching: '{keyword}'")
            
            try:
                urls = _brave_search(keyword, count=max_results_per_keyword)
                results[keyword] = urls
                
                print(f"   ✅ Găsite: {len(urls)} URL-uri")
                
                # Rate limiting
                if idx < len(keywords):
                    time.sleep(1)  # 1 sec între requests
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                results[keyword] = []
        
        return results
    
    def _extract_unique_domains(self, serp_results: Dict[str, List[str]]) -> Dict[str, int]:
        """Extrage domenii unice și contorizează apariții"""
        from urllib.parse import urlparse
        
        domain_counts = {}
        
        for keyword, urls in serp_results.items():
            for url in urls:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    # Remove www
                    domain = domain.replace('www.', '')
                    
                    if domain:
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                except:
                    continue
        
        # Sort by count
        return dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _save_serp_results(
        self,
        agent_id: str,
        domain: str,
        keywords: List[str],
        serp_results: Dict[str, List[str]]
    ):
        """Salvează rezultatele SERP în MongoDB"""
        
        # Extract unique domains cu metadata
        unique_domains = self._extract_unique_domains(serp_results)
        
        # Creează lista de competitori potențiali
        potential_competitors = []
        
        for comp_domain, count in unique_domains.items():
            # Skip propriul domeniu
            if comp_domain in domain or domain in comp_domain:
                continue
            
            # Găsește primul URL pentru acest domeniu
            first_url = None
            keywords_found = []
            
            for keyword, urls in serp_results.items():
                for url in urls:
                    if comp_domain in url.lower():
                        if not first_url:
                            first_url = url
                        if keyword not in keywords_found:
                            keywords_found.append(keyword)
            
            potential_competitors.append({
                "domain": comp_domain,
                "url": first_url or f"https://{comp_domain}",
                "appearances": count,
                "relevance_score": min(count / len(keywords) * 100, 100),  # 0-100
                "keywords_matched": keywords_found,
                "status": "discovered",
                "discovered_at": datetime.now()
            })
        
        # Salvează în MongoDB
        self.db.serp_discovery_results.replace_one(
            {"agent_id": agent_id},
            {
                "agent_id": agent_id,
                "domain": domain,
                "keywords_searched": keywords,
                "total_keywords": len(serp_results),
                "total_urls_found": sum(len(urls) for urls in serp_results.values()),
                "potential_competitors": potential_competitors[:50],  # Top 50
                "serp_raw_results": serp_results,  # Full data
                "created_at": datetime.now(),
                "status": "completed"
            },
            upsert=True
        )
        
        print(f"\n✅ Salvat {len(potential_competitors)} competitori potențiali în MongoDB!")


def main():
    """Test/Run script"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python deepseek_serp_discovery.py <agent_id> [max_results_per_keyword]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    
    discovery = DeepSeekSerpDiscovery()
    result = discovery.analyze_and_discover(agent_id, max_results)
    
    if result:
        print(f"\n✅ SUCCESS!")
    else:
        print(f"\n❌ FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()

