#!/usr/bin/env python3
"""
Qwen Rankings Learning Pipeline
Transformă tot flow-ul (rankings + strategii + competitori) în training data pentru Qwen
Qwen devine expert în domeniul specific al fiecărui agent
"""

import logging
import json
from datetime import datetime
from typing import Dict, List
from pymongo import MongoClient
from bson import ObjectId
import os

logger = logging.getLogger(__name__)

class QwenRankingsLearningPipeline:
    """
    Pipeline de învățare pentru Qwen din rankings + strategii
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['ai_agents_db']
        self.jsonl_dir = "/srv/hf/ai_agents/qwen_training_data"
        os.makedirs(self.jsonl_dir, exist_ok=True)
    
    def generate_ranking_conversation(self, ranking: Dict, agent: Dict) -> Dict:
        """
        Conversație despre rankings pentru training
        """
        keyword = ranking['keyword']
        position = ranking.get('master_position')
        serp_results = ranking.get('serp_results', [])
        
        # Top 3 competitori
        top_3 = [r for r in serp_results[:3] if r['domain'] != agent.get('domain')]
        
        user_query = f"""
Analizeaz\u0103 poziția site-ului {agent.get('domain')} pentru keyword-ul "{keyword}".
Compania: {agent.get('name', 'N/A')}
Industrie: {agent.get('industry', 'N/A')}

Poziția curentă: {position if position else 'Nu este în top 20'}

Top 3 competitori:
{json.dumps([{'position': c['position'], 'domain': c['domain'], 'title': c['title']} for c in top_3], indent=2)}

Ce strategie recomanzi?
"""
        
        # Generate assistant response
        if not position:
            response = f"""
📊 **Analiză Ranking pentru "{keyword}"**

**Poziția actuală:** Nu este în top 20 Google

**Situația:**
- Site-ul {agent.get('domain')} nu apare în primele 20 de rezultate pentru "{keyword}"
- Competitorii dominanți: {', '.join([c['domain'] for c in top_3])}

**Recomandări prioritare:**

1. **Google Ads Campaign (URGENT)**
   - Lansează campanie cu bid între $4.00 - $6.00
   - Target: Poziția 1-3 în ads
   - Budget recomandat: $500-800/lună

2. **SEO Improvements**
   - Creează conținut optimizat pentru "{keyword}"
   - Analizează ce face bine {top_3[0]['domain']} (poziția #1)
   - Backlink building către pagina relevantă

3. **Content Gap Analysis**
   - Studiază conținutul competitorilor din top 3
   - Identifică ce informații lipsesc pe site-ul tău
   - Creează conținut mai complet și mai bun

**Prioritate:** MAXIMĂ - lipsă completă de vizibilitate pentru acest keyword important.
"""
        elif position <= 3:
            response = f"""
📊 **Analiză Ranking pentru "{keyword}"**

**Poziția actuală:** #{position} (TOP 3! 🎯)

**Situația:**
- Excelent! Site-ul este în top 3 pentru "{keyword}"
- Vizibilitate organică foarte bună

**Recomandări de optimizare:**

1. **Menține Poziția**
   - Actualizează periodic conținutul
   - Monitorizează competitorii săptămânal
   - Păstrează backlink-urile actuale

2. **Google Ads (Opțional)**
   - Dacă vrei dominare totală, lansează ads cu bid redus ($2-3)
   - Poți captura și pozițiile ads + organice
   - ROI excelent datorită poziției organice deja bune

3. **Optimizare Cost**
   - Dacă ai ads active, reduce bid-ul cu 10-15%
   - Poziția organică este suficient de bună
   - Focus pe alte keywords unde lipsești

**Prioritate:** LOW - Poziția este excelentă, doar menținere și optimizare.
"""
        elif position <= 10:
            response = f"""
📊 **Analiză Ranking pentru "{keyword}"**

**Poziția actuală:** #{position} (Top 10 ✅)

**Situația:**
- Bine! Ești în top 10 pentru "{keyword}"
- Oportunitate de a ajunge în top 3 cu efort moderat

**Recomandări:**

1. **Push to Top 3 cu Ads**
   - Lansează Google Ads cu bid $3.50 - $5.00
   - Target: Poziția 1-3 în ads section
   - Combinație ads + organic (#10) = vizibilitate crescută

2. **SEO Enhancement**
   - Optimizează pagina existentă
   - Mai multe backlink-uri de calitate
   - Îmbunătățește experiența utilizatorului (UX)

3. **Competitive Analysis**
   - Studiază ce fac diferit site-urile din poziția #1-3
   - Implementează best practices identificate

**Prioritate:** MEDIUM - Investiție moderată poate aduce rezultate mari.
"""
        else:
            # 11-20
            response = f"""
📊 **Analiză Ranking pentru "{keyword}"**

**Poziția actuală:** #{position} (În top 20, dar nu în top 10)

**Situația:**
- Apari în top 20, dar vizibilitatea este limitată
- Gap de {10 - position} poziții până în top 10
- Oportunitate MARE pentru îmbunătățire

**Recomandări:**

1. **Google Ads (HIGH PRIORITY)**
   - Lansează campanie cu bid $3.50 - $5.00
   - Focus pe poziția 3-5 în ads
   - Budget: $400-600/lună

2. **SEO Intensiv**
   - Conținut nou, mai complet despre "{keyword}"
   - Target: 2000-3000 cuvinte, foarte detaliat
   - Schema markup pentru rich snippets
   - 5-10 backlink-uri noi în următoarele 2 luni

3. **Quick Wins**
   - Optimizează title și meta description
   - Îmbunătățește viteza paginii
   - Mobile optimization

**Prioritate:** HIGH - Cu investiție moderată, poți intra în top 10 în 2-3 luni.
**ROI estimat:** 250-300% în 6 luni
"""
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": user_query
                },
                {
                    "role": "assistant",
                    "content": response
                }
            ]
        }
    
    def generate_strategy_conversation(self, strategy: Dict, agent: Dict) -> Dict:
        """
        Conversație despre strategii Google Ads
        """
        user_query = f"""
Generează strategia Google Ads pentru {agent.get('domain')}.

Compania: {agent.get('name')}
Industrie: {agent.get('industry')}

Context:
{json.dumps(strategy.get('analysis_data', {}), indent=2, default=str)[:500]}...

Care este strategia completă?
"""
        
        response = f"""
📊 **Strategia Google Ads Completă pentru {agent.get('domain')}**

{strategy.get('executive_summary', 'N/A')}

**Budget Total Recomandat:** {strategy.get('budget_total', '$3000-5000/lună')}

**Keywords Prioritare:**
{json.dumps(strategy.get('priority_actions', [])[:5], indent=2)}

**Plan de Acțiune:**
{json.dumps(strategy.get('action_plan', []), indent=2, default=str)}

**KPI-uri Target:**
{json.dumps(strategy.get('kpis', {}), indent=2)}

**Insights Competitive:**
{json.dumps(strategy.get('competitor_insights', {}), indent=2)}

**Timeline:** {strategy.get('timeline', '3-6 luni pentru rezultate semnificative')}
"""
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": user_query
                },
                {
                    "role": "assistant",
                    "content": response
                }
            ]
        }
    
    def generate_competitor_conversation(self, slave: Dict, master: Dict, keyword: str) -> Dict:
        """
        Conversație despre un competitor (slave agent)
        """
        user_query = f"""
Analizează competitorul {slave.get('domain')} pentru keyword-ul "{keyword}".

**Master Agent:** {master.get('domain')}
**Competitor:** {slave.get('domain')}

Content preview competitor:
{slave.get('scraped_content', '')[:500]}...

Ce putem învăța de la acest competitor?
"""
        
        response = f"""
🔍 **Analiza Competitorului: {slave.get('domain')}**

**Context:**
- Competitor pentru keyword: "{keyword}"
- Master agent: {master.get('domain')}

**Ce face bine acest competitor:**

1. **Conținut:**
   - Are conținut relevant pentru "{keyword}"
   - Probabil optimizat SEO
   - Structurat pentru user intent

2. **Ce putem învăța:**
   - Structura conținutului lor
   - Keywords secundare folosite
   - Tipul de informații oferite

3. **Cum să competem:**
   - Creează conținut mai complet
   - Adaugă elemente lipsă
   - Optimizează mai bine pentru long-tail keywords

4. **Strategie Google Ads:**
   - Dacă ei nu au ads, poți domina cu ads
   - Dacă au ads, analizează copy-ul lor și creează unul mai bun
   - Bid strategic pentru a apărea deasupra lor

**Recomandare:** Studiază în detaliu pagina lor și identifică gap-uri pe care le poți exploata.
"""
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": user_query
                },
                {
                    "role": "assistant",
                    "content": response
                }
            ]
        }
    
    def generate_training_data(self, agent_id: str) -> str:
        """
        Generează JSONL pentru training Qwen cu tot flow-ul
        
        Returns:
            Path to JSONL file
        """
        logger.info(f"📚 Generating training data for agent {agent_id}...")
        
        agent = self.db.site_agents.find_one({'_id': ObjectId(agent_id)})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        conversations = []
        
        # 1. Rankings conversations
        rankings = list(self.db.google_rankings.find({'agent_id': agent_id}))
        logger.info(f"   Processing {len(rankings)} rankings...")
        
        for ranking in rankings:
            conv = self.generate_ranking_conversation(ranking, agent)
            conversations.append(conv)
        
        # 2. Strategy conversations
        strategies = list(self.db.agent_strategies.find({'agent_id': agent_id}))
        logger.info(f"   Processing {len(strategies)} strategies...")
        
        for strategy in strategies:
            conv = self.generate_strategy_conversation(strategy, agent)
            conversations.append(conv)
        
        # 3. Competitor conversations
        slaves = list(self.db.site_agents.find({'master_ids': agent_id, 'type': 'slave'}))
        logger.info(f"   Processing {len(slaves)} competitors...")
        
        for slave in slaves[:20]:  # Limit to 20 top competitors
            # Find keyword where this slave appears
            ranking_with_slave = self.db.google_rankings.find_one({
                'agent_id': agent_id,
                'slave_ids': str(slave['_id'])
            })
            
            if ranking_with_slave:
                keyword = ranking_with_slave['keyword']
                conv = self.generate_competitor_conversation(slave, agent, keyword)
                conversations.append(conv)
        
        # Write JSONL
        jsonl_path = f"{self.jsonl_dir}/agent_{agent_id}_rankings_learning.jsonl"
        
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for conv in conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ Generated {len(conversations)} training conversations")
        logger.info(f"📄 JSONL saved to: {jsonl_path}")
        
        # Store metadata
        self.db.qwen_training_data.insert_one({
            'agent_id': agent_id,
            'agent_domain': agent.get('domain'),
            'jsonl_path': jsonl_path,
            'total_conversations': len(conversations),
            'rankings_count': len(rankings),
            'strategies_count': len(strategies),
            'competitors_count': len(slaves),
            'generated_at': datetime.now()
        })
        
        return jsonl_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    pipeline = QwenRankingsLearningPipeline()
    
    agent_id = "691a19dd2772e8833c819084"
    
    print(f"\n🧪 Testing Qwen Learning Pipeline...")
    print(f"Agent ID: {agent_id}")
    
    try:
        jsonl_path = pipeline.generate_training_data(agent_id)
        print(f"\n✅ Training data generated!")
        print(f"📄 File: {jsonl_path}")
        
        # Show first conversation
        with open(jsonl_path, 'r') as f:
            first = json.loads(f.readline())
            print(f"\n📖 Sample conversation:")
            print(json.dumps(first, indent=2, ensure_ascii=False)[:500] + "...")
    except Exception as e:
        print(f"\n❌ Error: {e}")

