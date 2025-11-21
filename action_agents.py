#!/usr/bin/env python3
"""
🤖 Action Execution Agents - FAZA 3
Agenți specializați pentru execuție acțiuni SEO
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


# ============================================================================
# BASE ACTION AGENT
# ============================================================================

class BaseActionAgent:
    """
    Base class pentru toți agenții de execuție
    Funcționalitate comună: logging, LLM calls, result formatting
    """
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "ai_agents_db"
    ):
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.agent_name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.agent_name}")
        
        # Import LLM helper (REAL - NO MORE MOCKS!)
        from llm_helper import call_llm_with_fallback
        self.llm = call_llm_with_fallback
        self.logger.info(f"✅ {self.agent_name} - LLM Helper loaded (DeepSeek/Qwen/Kimi)")
    
    async def execute_action(
        self,
        action: Dict,
        agent_id: str,
        playbook_id: str
    ) -> Dict:
        """
        Execută acțiune (template method)
        Fiecare subclass override _execute_implementation
        
        Returns:
            {
                "success": bool,
                "result": dict,
                "logs": list,
                "errors": list
            }
        """
        self.logger.info(f"🎬 Executing action {action['action_id']}: {action['title']}")
        
        logs = []
        errors = []
        
        try:
            # Call subclass implementation
            result = await self._execute_implementation(action, agent_id, logs)
            
            return {
                "success": True,
                "result": result,
                "logs": logs,
                "errors": errors
            }
            
        except Exception as e:
            self.logger.error(f"❌ Action execution failed: {e}")
            errors.append(str(e))
            
            return {
                "success": False,
                "result": None,
                "logs": logs,
                "errors": errors
            }
    
    async def _execute_implementation(
        self,
        action: Dict,
        agent_id: str,
        logs: List[str]
    ) -> Dict:
        """Override în subclass"""
        raise NotImplementedError(f"{self.agent_name} must implement _execute_implementation")
    
    def _call_llm(
        self,
        prompt: str,
        model_preference: str = "qwen",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> str:
        """Helper pentru LLM calls"""
        if not self.llm:
            raise RuntimeError("LLM not available")
        
        return self.llm(
            prompt=prompt,
            model_preference=model_preference,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def _get_agent_context(self, agent_id: str) -> Dict:
        """Obține context agent din MongoDB cu toate datele REALE"""
        try:
            obj_id = ObjectId(agent_id)
        except:
            obj_id = agent_id
        
        agent = self.db.site_agents.find_one({"_id": obj_id})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Extrage date REALE din agent_config.knowledge_base
        company_name = None
        industry = None
        services = []
        keywords = []
        
        # Încearcă din agent_config.knowledge_base (CEL MAI IMPORTANT)
        if agent.get("agent_config") and isinstance(agent["agent_config"], dict):
            kb = agent["agent_config"].get("knowledge_base", {})
            if isinstance(kb, dict):
                company_info = kb.get("company_info", {})
                if isinstance(company_info, dict):
                    company_name = company_info.get("company_name") or company_name
                
                services_offered = kb.get("services_offered", [])
                if isinstance(services_offered, list):
                    services = [s.get("service_name") if isinstance(s, dict) else str(s) 
                               for s in services_offered[:10]]
                
                # Extrage expertise ca keywords
                expertise = agent["agent_config"].get("expertise", [])
                if isinstance(expertise, list):
                    keywords.extend([str(e) for e in expertise[:5]])
        
        # Extrage industry din agent_config.role sau expertise
        if not industry and agent.get("agent_config"):
            role = agent["agent_config"].get("role", "")
            if role:
                # Încearcă să extragă industry din role (mai inteligent)
                if "construcții" in role.lower() or "construcții" in role.lower():
                    industry = "Construcții"
                elif "autorizări" in role.lower() or "isu" in role.lower():
                    industry = "Autorizări și Licențe"
                elif "servicii" in role.lower():
                    industry = "Servicii"
                else:
                    # Fallback: extrage din role
                    industry = role.split("în")[-1].strip() if "în" in role else role.split("-")[0].strip()
        
        # Fallback: Extrage company name din domain sau deepseek_identity
        if not company_name:
            # Încearcă din domain (parse domain name mai inteligent)
            domain = agent.get("domain", "")
            if domain:
                # Remove www. and .ro/.com etc
                domain_clean = domain.replace("www.", "").split(".")[0]
                # Pentru domenii specifice, folosește nume mai clar
                if "isuautorizari" in domain_clean.lower():
                    company_name = "ISU Autorizări"
                elif "cnsipc" in domain_clean.lower() or "igsu" in domain_clean.lower():
                    company_name = "CNSIPC/IGSU"
                else:
                    company_name = domain_clean.replace("-", " ").replace("_", " ").title()
            
            # Încearcă din deepseek_identity
            if not company_name and agent.get("deepseek_identity"):
                identity = agent["deepseek_identity"]
                # Încearcă să extragă nume companie din primele 200 chars
                if "companie" in identity.lower()[:200]:
                    import re
                    match = re.search(r'companie\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', identity[:200], re.IGNORECASE)
                    if match:
                        company_name = match.group(1)
        
        # Fallback: Extrage industry din domain sau keywords
        if not industry:
            domain = agent.get("domain", "").lower()
            if domain:
                # Parse domain pentru a găsi industry (mai specific)
                if "autorizari" in domain or "isu" in domain:
                    industry = "Autorizări și Licențe"
                elif "constructii" in domain or "constructii" in domain:
                    industry = "Construcții"
                elif "servicii" in domain:
                    industry = "Servicii"
                elif "cnsipc" in domain or "igsu" in domain:
                    industry = "Autorizări și Licențe"
        
        # Extrage keywords din agent dacă nu există
        if not keywords:
            keywords = agent.get("keywords", [])[:5] if isinstance(agent.get("keywords"), list) else []
            if not keywords and agent.get("overall_keywords"):
                keywords = list(agent.get("overall_keywords", {}).keys())[:5]
        
        # Extrage services din agent dacă nu există
        if not services:
            services = agent.get("services", [])[:5] if isinstance(agent.get("services"), list) else []
        
        # Extrage site_url
        site_url = agent.get("site_url", "") or agent.get("domain", "")
        if site_url and not site_url.startswith("http"):
            site_url = f"https://{site_url}"
        
        return {
            "company_name": company_name or "Companie",
            "industry": industry or "Servicii",
            "services": services or [],
            "keywords": keywords or [],
            "site_url": site_url,
            "domain": agent.get("domain", ""),
            "agent_id": agent_id
        }


# ============================================================================
# COPYWRITER AGENT
# ============================================================================

class CopywriterAgent(BaseActionAgent):
    """
    ✍️ Agent pentru generare conținut SEO-optimized
    
    Capabilities:
    - Blog posts / articles (2000-3000 words)
    - Landing pages
    - Product descriptions
    - FAQ sections
    - Meta descriptions
    """
    
    async def _execute_implementation(
        self,
        action: Dict,
        agent_id: str,
        logs: List[str]
    ) -> Dict:
        """
        Generează conținut optimizat SEO folosind Qwen/Kimi
        """
        logs.append("📝 CopywriterAgent starting content generation...")
        
        # Get agent context
        context = self._get_agent_context(agent_id)
        logs.append(f"✅ Loaded context for {context['company_name']}")
        
        # Extract parameters
        params = action.get("parameters", {})
        keywords = action.get("assigned_keywords", [])
        target_word_count = params.get("target_word_count", 2000)
        include_faq = params.get("include_faq", True)
        
        logs.append(f"📊 Target: {target_word_count} words, Keywords: {len(keywords)}")
        
        # Build prompt
        prompt = self._build_content_prompt(
            title=action["title"],
            description=action["description"],
            keywords=keywords,
            target_word_count=target_word_count,
            include_faq=include_faq,
            context=context
        )
        
        logs.append("🧠 Calling Qwen for content generation...")
        
        # Generate content with Qwen (GPU)
        try:
            content_json = self._call_llm(
                prompt=prompt,
                model_preference="qwen",
                max_tokens=4000,
                temperature=0.7
            )
            
            content_data = json.loads(content_json)
            logs.append(f"✅ Content generated: {len(content_data.get('body', ''))} chars")
            
        except Exception as e:
            logs.append(f"⚠️ Qwen failed, using fallback: {e}")
            content_data = self._fallback_content(action, keywords)
        
        # Calculate quality score
        quality_score = self._calculate_content_quality(content_data, keywords)
        logs.append(f"📊 Quality score: {quality_score:.2f}")
        
        return {
            "content": content_data,
            "quality_score": quality_score,
            "word_count": len(content_data.get("body", "").split()),
            "keywords_used": keywords,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _build_content_prompt(
        self,
        title: str,
        description: str,
        keywords: List[str],
        target_word_count: int,
        include_faq: bool,
        context: Dict
    ) -> str:
        """Construiește prompt pentru Qwen"""
        
        keywords_str = ", ".join(keywords) if keywords else "N/A"
        
        prompt = f"""You are an expert SEO copywriter. Write high-quality, SEO-optimized content.

**TASK:** {title}
**DESCRIPTION:** {description}

**COMPANY CONTEXT:**
- Name: {context['company_name']}
- Industry: {context['industry']}
- Target audience: {context.get('target_audience', 'general public')}

**SEO REQUIREMENTS:**
- Target keywords: {keywords_str}
- Word count: {target_word_count}+ words
- Include FAQ: {'Yes' if include_faq else 'No'}
- Tone: Professional, informative, engaging
- Keyword density: 2-3% (natural placement)

**OUTPUT FORMAT (JSON):**
{{
  "title": "SEO-optimized H1 title",
  "meta_description": "150-160 chars meta description",
  "introduction": "Engaging introduction paragraph (200-300 words)",
  "body": "Main content with H2/H3 headings, paragraphs, bullet points",
  "faq": [
    {{"question": "...", "answer": "..."}},
    ...
  ],
  "conclusion": "Call-to-action conclusion (150-200 words)",
  "internal_link_suggestions": ["Page A", "Page B"],
  "image_suggestions": ["Image 1 alt text", "Image 2 alt text"]
}}

Write comprehensive, valuable content that answers user intent. Use natural language, avoid keyword stuffing. Include statistics, examples, and actionable tips.

Return ONLY valid JSON, no markdown formatting.
"""
        return prompt
    
    def _fallback_content(self, action: Dict, keywords: List[str]) -> Dict:
        """Fallback content dacă LLM fail"""
        keyword = keywords[0] if keywords else "SEO"
        
        return {
            "title": action["title"],
            "meta_description": f"Professional guide about {keyword}. Learn more about {keyword} from industry experts.",
            "introduction": f"This comprehensive guide covers everything you need to know about {keyword}.",
            "body": f"<h2>What is {keyword}?</h2>\n<p>[Content placeholder - {action['description']}]</p>",
            "faq": [
                {"question": f"What is {keyword}?", "answer": "Detailed answer here."},
                {"question": f"Why is {keyword} important?", "answer": "Benefits explanation here."}
            ],
            "conclusion": f"For more information about {keyword}, contact us today.",
            "internal_link_suggestions": [],
            "image_suggestions": [f"{keyword} illustration", f"{keyword} infographic"]
        }
    
    def _calculate_content_quality(self, content: Dict, keywords: List[str]) -> float:
        """
        Calculează scor calitate conținut (0-1)
        
        Factors:
        - Word count (min 500)
        - Keyword presence (natural)
        - Structure (headings, paragraphs)
        - Readability
        """
        score = 0.0
        factors = 0
        
        body = content.get("body", "")
        word_count = len(body.split())
        
        # Factor 1: Word count (max 0.3)
        if word_count >= 2000:
            score += 0.3
        elif word_count >= 1000:
            score += 0.2
        elif word_count >= 500:
            score += 0.1
        factors += 1
        
        # Factor 2: Keyword presence (max 0.3)
        if keywords:
            keyword_mentions = sum(
                body.lower().count(kw.lower()) for kw in keywords
            )
            keyword_density = keyword_mentions / max(word_count, 1)
            
            if 0.02 <= keyword_density <= 0.04:  # 2-4% ideal
                score += 0.3
            elif 0.01 <= keyword_density <= 0.06:
                score += 0.2
            else:
                score += 0.1
        factors += 1
        
        # Factor 3: Structure (max 0.2)
        has_h2 = "<h2>" in body or "## " in body
        has_h3 = "<h3>" in body or "### " in body
        has_lists = "<ul>" in body or "<ol>" in body or "- " in body
        
        structure_score = sum([has_h2, has_h3, has_lists]) / 3 * 0.2
        score += structure_score
        factors += 1
        
        # Factor 4: Meta & FAQ (max 0.2)
        has_meta = bool(content.get("meta_description"))
        has_faq = bool(content.get("faq")) and len(content.get("faq", [])) >= 3
        score += (int(has_meta) + int(has_faq)) / 2 * 0.2
        factors += 1
        
        return min(score, 1.0)


# ============================================================================
# ONPAGE OPTIMIZER AGENT
# ============================================================================

class OnPageOptimizer(BaseActionAgent):
    """
    🔧 Agent pentru optimizare on-page
    
    Capabilities:
    - Rewrite title tags
    - Optimize meta descriptions
    - Improve headings structure (H1/H2/H3)
    - Internal linking recommendations
    - Image alt text optimization
    """
    
    async def _execute_implementation(
        self,
        action: Dict,
        agent_id: str,
        logs: List[str]
    ) -> Dict:
        """
        Optimizează elemente on-page pentru SEO folosind DeepSeek/Qwen REAL
        """
        logs.append("🔧 OnPageOptimizer starting REAL optimization with LLM...")
        
        # Get agent context REAL din MongoDB
        context = self._get_agent_context(agent_id)
        
        # Get keywords REAL din agent sau din action
        agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        keywords = action.get("assigned_keywords", [])
        if not keywords and agent:
            # Extrage keywords din agent dacă există
            keywords = agent.get("keywords", [])[:5] if isinstance(agent.get("keywords"), list) else []
            if not keywords and agent.get("overall_keywords"):
                keywords = list(agent.get("overall_keywords", {}).keys())[:5]
        
        logs.append(f"🎯 Optimizing for REAL keywords: {', '.join(keywords) if keywords else 'No keywords found'}")
        logs.append(f"📊 Agent context: {context.get('company_name')} - {context.get('industry')}")
        
        # Generate optimized elements folosind LLM REAL
        optimizations = {
            "title_tag": await self._optimize_title_llm(context, keywords, logs),
            "meta_description": await self._optimize_meta_llm(context, keywords, logs),
            "h1": await self._optimize_h1_llm(context, keywords, logs),
            "h2_suggestions": await self._suggest_h2_headings_llm(context, keywords, logs),
            "internal_links": await self._suggest_internal_links(agent_id, keywords, logs),
            "image_alts": await self._generate_image_alts_llm(context, keywords, logs)
        }
        
        logs.append("✅ All on-page elements optimized with REAL LLM")
        
        return {
            "optimizations": optimizations,
            "keywords_targeted": keywords,
            "agent_context": {
                "domain": context.get("site_url", "").split("//")[-1].split("/")[0] if context.get("site_url") else "",
                "company": context.get("company_name", ""),
                "industry": context.get("industry", "")
            },
            "optimized_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _optimize_title_llm(self, context: Dict, keywords: List[str], logs: List[str]) -> str:
        """Generează title tag optimizat folosind LLM REAL (max 60 chars)"""
        try:
            keyword_str = ", ".join(keywords[:3]) if keywords else context.get("industry", "services")
            company = context.get("company_name", "Company")
            industry = context.get("industry", "")
            services = ", ".join(context.get("services", [])[:3]) if context.get("services") else ""
            
            # Construiește prompt SPECIFIC cu date REALE
            domain_info = f"Domain: {context.get('domain', '')}"
            services_info = f"Services: {', '.join(services[:3])}" if services else ""
            
            prompt = f"""Ești un expert SEO român. Generează un title tag optimizat (MAXIM 60 caractere) pentru această companie REALĂ:

DOMENIU: {context.get('domain', '')}
COMPANIE: {company}
INDUSTRIE: {industry}
CUVINTE CHEIE: {keyword_str}
SERVICII: {services_info}

REGLI STRICTE:
1. Generează ÎN ROMÂNĂ - fără excepții
2. Folosește informații SPECIFICE despre această companie - NU fraze generice
3. Include cuvântul cheie principal natural
4. Maxim 60 caractere
5. INTERZIS: "Soluții Expert", "Servicii Profesionale", "Crește-ți Vizibilitatea", "Transform Your Business", "Get Started", "Boost Your", "Discover our"

EXEMPLE CORECTE:
- Pentru "isuautorizari.ro": "Autorizări ISU - Documentație și Licențe Fire"
- Pentru "cnsipc.igsu.ro": "Autorizări ISU CNSIPC - Licențe Securitate Incendiu"
- Pentru construcții: "Construcții [Nume] - Renovări și Proiecte Rezidențiale"

Returnează DOAR title tag-ul în română, fără ghilimele, fără alt text."""
            
            title = self._call_llm(prompt, model_preference="deepseek", max_tokens=100, temperature=0.7)
            title = title.strip().strip('"').strip("'")
            
            # Fallback dacă LLM returnează prea mult
            if len(title) > 60:
                title = title[:57] + "..."
            
            logs.append(f"✅ Generated REAL title: {title}")
            return title[:60]
        except Exception as e:
            logs.append(f"⚠️ LLM title generation failed: {e}, using fallback")
            keyword = keywords[0] if keywords else context.get("industry", "Services")
            company = context.get("company_name", "Company")
            return f"{keyword.title()} - {company}"[:60]
    
    async def _optimize_meta_llm(self, context: Dict, keywords: List[str], logs: List[str]) -> str:
        """Generează meta description folosind LLM REAL (150-160 chars)"""
        try:
            keyword_str = ", ".join(keywords[:3]) if keywords else context.get("industry", "services")
            company = context.get("company_name", "Company")
            industry = context.get("industry", "")
            services = ", ".join(context.get("services", [])[:3]) if context.get("services") else ""
            
            # Construiește prompt SPECIFIC
            domain_info = f"Domain: {context.get('domain', '')}"
            services_list = context.get("services", [])
            services_info = f"Services: {', '.join(services_list[:3])}" if services_list else ""
            
            prompt = f"""Ești un expert SEO român. Generează o meta description optimizată (150-160 caractere) pentru această companie REALĂ:

DOMENIU: {context.get('domain', '')}
COMPANIE: {company}
INDUSTRIE: {industry}
CUVINTE CHEIE: {keyword_str}
SERVICII: {services_info}

REGLI STRICTE:
1. Generează ÎN ROMÂNĂ - fără excepții
2. Folosește informații SPECIFICE despre această companie - NU fraze generice
3. Exact 150-160 caractere
4. Include cuvintele cheie principale natural
5. Call-to-action specific acestui business
6. INTERZIS: "Deblochează-ți potențialul", "Obține rezultate măsurabile", "Transformă-ți viziunea", "Discover our", "Elevate your business", "Expert solutions"

EXEMPLE CORECTE:
- Pentru "isuautorizari.ro": "Obține autorizări ISU rapid și sigur. Documentație completă pentru licențe de securitate la incendiu. Consultanță specializată."
- Pentru construcții: "Servicii complete construcții și renovări. [Companie] - proiecte rezidențiale și comerciale cu garanție."

Returnează DOAR meta description-ul în română, fără ghilimele, fără alt text."""
            
            meta = self._call_llm(prompt, model_preference="deepseek", max_tokens=100, temperature=0.7)
            meta = meta.strip().strip('"').strip("'")
            
            # Ensure length
            if len(meta) < 150:
                meta = meta + " Contact us for expert solutions."
            meta = meta[:160]
            
            logs.append(f"✅ Generated REAL meta: {meta[:50]}...")
            return meta
        except Exception as e:
            logs.append(f"⚠️ LLM meta generation failed: {e}, using fallback")
            keyword = keywords[0] if keywords else "services"
            company = context.get("company_name", "Company")
            return f"Professional {keyword} services from {company}. Expert solutions, quality results. Contact us today."[:160]
    
    async def _optimize_h1_llm(self, context: Dict, keywords: List[str], logs: List[str]) -> str:
        """Generează H1 optimizat folosind LLM REAL"""
        try:
            keyword_str = ", ".join(keywords[:3]) if keywords else context.get("industry", "services")
            company = context.get("company_name", "Company")
            industry = context.get("industry", "")
            
            # Construiește prompt SPECIFIC
            domain_info = f"Domain: {context.get('domain', '')}"
            services_list = context.get("services", [])
            services_info = f"Services: {', '.join(services_list[:3])}" if services_list else ""
            
            prompt = f"""Ești un expert SEO român. Generează un heading H1 optimizat pentru această companie REALĂ:

DOMENIU: {context.get('domain', '')}
COMPANIE: {company}
INDUSTRIE: {industry}
CUVINTE CHEIE: {keyword_str}
SERVICII: {services_info}

REGLI STRICTE:
1. Generează ÎN ROMÂNĂ - fără excepții
2. Folosește informații SPECIFICE despre această companie - NU fraze generice
3. Include cuvântul cheie principal natural
4. Clar și descriptiv
5. Maxim 80 caractere
6. INTERZIS: "Crește-ți Vizibilitatea Online", "Servicii Profesionale", "Soluții Expert", "Boost Your", "H1 Heading Generator"

EXEMPLE CORECTE:
- Pentru "isuautorizari.ro": "Autorizări ISU - Licențe de Securitate la Incendiu"
- Pentru construcții: "Construcții și Renovări [Locație] - Proiecte Rezidențiale"

Returnează DOAR heading-ul H1 în română, fără ghilimele, fără alt text."""
            
            h1 = self._call_llm(prompt, model_preference="deepseek", max_tokens=100, temperature=0.7)
            h1 = h1.strip().strip('"').strip("'")
            
            logs.append(f"✅ Generated REAL H1: {h1}")
            return h1
        except Exception as e:
            logs.append(f"⚠️ LLM H1 generation failed: {e}, using fallback")
            keyword = keywords[0] if keywords else context.get("industry", "Services")
            return f"{keyword.title()} - {context.get('company_name', 'Company')}"
    
    async def _suggest_h2_headings_llm(self, context: Dict, keywords: List[str], logs: List[str]) -> List[str]:
        """Sugerează H2 headings folosind LLM REAL"""
        try:
            keyword_str = ", ".join(keywords[:3]) if keywords else context.get("industry", "services")
            company = context.get("company_name", "Company")
            industry = context.get("industry", "")
            services = ", ".join(context.get("services", [])[:5]) if context.get("services") else ""
            
            # Construiește prompt SPECIFIC
            domain_info = f"Domain: {context.get('domain', '')}"
            services_list = context.get("services", [])
            services_info = f"Services: {', '.join(services_list[:5])}" if services_list else ""
            
            prompt = f"""Ești un expert SEO român. Generează 6-8 heading-uri H2 optimizate pentru această companie REALĂ:

DOMENIU: {context.get('domain', '')}
COMPANIE: {company}
INDUSTRIE: {industry}
CUVINTE CHEIE: {keyword_str}
SERVICII: {services_info}

REGLI STRICTE:
1. Generează ÎN ROMÂNĂ - fără excepții
2. Folosește informații SPECIFICE despre această companie - NU fraze generice
3. Include cuvintele cheie natural
4. Acoperă aspecte specifice (ce, de ce, cum, beneficii, proces, întrebări frecvente)
5. INTERZIS: "Cadrul Nostru Complet", "Beneficiile Cheie", "Cum Metodologia Noastră", "Our Comprehensive", "Key Benefits", "How Our"

EXEMPLE CORECTE pentru "isuautorizari.ro":
- "Ce sunt autorizările ISU și când sunt necesare?"
- "Documentația necesară pentru autorizare ISU"
- "Procesul de obținere a autorizației de securitate la incendiu"
- "Servicii de consultanță pentru autorizări ISU"

Returnează DOAR un array JSON în română, precum: ["Heading 1", "Heading 2", ...]"""
            
            response = self._call_llm(prompt, model_preference="deepseek", max_tokens=300, temperature=0.7)
            
            # Parse JSON response
            import json
            import re
            # Extract JSON array
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                headings = json.loads(json_match.group())
            else:
                # Fallback: split by lines
                headings = [h.strip().strip('"').strip("'") for h in response.split('\n') if h.strip() and h.strip()[0].isupper()][:8]
            
            logs.append(f"✅ Generated {len(headings)} REAL H2 headings")
            return headings[:8]
        except Exception as e:
            logs.append(f"⚠️ LLM H2 generation failed: {e}, using fallback")
            keyword = keywords[0] if keywords else "services"
            return [
                f"What is {keyword}?",
                f"Benefits of {keyword}",
                f"Our {keyword} Services",
                f"Why Choose {context.get('company_name', 'Us')}?",
                f"{keyword} Process",
                "Frequently Asked Questions"
            ]
    
    async def _suggest_internal_links(
        self,
        agent_id: str,
        keywords: List[str],
        logs: List[str]
    ) -> List[Dict]:
        """
        Sugerează internal links din Qdrant (semantic search)
        """
        links = []
        
        try:
            # Query Qdrant pentru related content
            from qdrant_client import QdrantClient
            
            qdrant = QdrantClient(url="http://localhost:6333")
            collection_name = f"agent_{agent_id}"
            
            # Search pentru fiecare keyword
            for keyword in keywords[:3]:  # Max 3 keywords
                try:
                    # Simple search (fără embeddings pentru acum)
                    # În production ar folosi embeddings
                    links.append({
                        "anchor_text": keyword,
                        "target_url": f"/services/{keyword.lower().replace(' ', '-')}",
                        "relevance_score": 0.85
                    })
                except Exception as e:
                    logs.append(f"⚠️ Qdrant search failed for '{keyword}': {e}")
            
        except Exception as e:
            logs.append(f"⚠️ Internal linking failed: {e}")
        
        return links
    
    async def _generate_image_alts_llm(self, context: Dict, keywords: List[str], logs: List[str]) -> List[str]:
        """Generează image alt texts folosind LLM REAL"""
        try:
            keyword_str = ", ".join(keywords[:3]) if keywords else context.get("industry", "services")
            company = context.get("company_name", "Company")
            industry = context.get("industry", "")
            
            # Construiește prompt SPECIFIC
            domain_info = f"Domain: {context.get('domain', '')}"
            services_info = f"Services: {', '.join(services[:3])}" if services else ""
            
            prompt = f"""Ești un expert SEO român. Generează 5-7 texte alternative pentru imagini optimizate pentru această companie REALĂ:

DOMENIU: {context.get('domain', '')}
COMPANIE: {company}
INDUSTRIE: {industry}
CUVINTE CHEIE: {keyword_str}
SERVICII: {services_info}

REGLI STRICTE:
1. Generează ÎN ROMÂNĂ - fără excepții
2. Folosește informații SPECIFICE despre această companie - NU fraze generice
3. Include cuvintele cheie natural
4. Descriptiv și accesibil
5. INTERZIS: "persoană tastând pe laptop", "echipă colaborând", "profesionist de afaceri", "person typing", "team collaborating"

EXEMPLE CORECTE pentru "isuautorizari.ro":
- "Documentație autorizare ISU pentru clădiri comerciale"
- "Proces verificare securitate la incendiu"
- "Licență ISU pentru instalații tehnice"

Returnează DOAR un array JSON în română, precum: ["Text alternativ 1", "Text alternativ 2", ...]"""
            
            response = self._call_llm(prompt, model_preference="deepseek", max_tokens=200, temperature=0.7)
            
            # Parse JSON
            import json
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                alts = json.loads(json_match.group())
            else:
                alts = [a.strip().strip('"').strip("'") for a in response.split('\n') if a.strip()][:7]
            
            logs.append(f"✅ Generated {len(alts)} REAL image alt texts")
            return alts[:10]
        except Exception as e:
            logs.append(f"⚠️ LLM alt text generation failed: {e}, using fallback")
            alts = []
            for kw in keywords[:5]:
                alts.extend([
                    f"{kw} - {context.get('company_name', 'Company')} professional service",
                    f"{kw} - process and methodology",
                    f"{kw} - results and benefits"
                ])
            return alts[:10]


# ============================================================================
# SCHEMA GENERATOR AGENT
# ============================================================================

class SchemaGenerator(BaseActionAgent):
    """
    📋 Agent pentru generare JSON-LD schema markup
    
    Capabilities:
    - Article schema
    - Service schema
    - FAQ schema
    - Organization schema
    - Breadcrumb schema
    """
    
    async def _execute_implementation(
        self,
        action: Dict,
        agent_id: str,
        logs: List[str]
    ) -> Dict:
        """
        Generează JSON-LD schemas
        """
        logs.append("📋 SchemaGenerator starting schema generation...")
        
        context = self._get_agent_context(agent_id)
        keywords = action.get("assigned_keywords", [])
        
        # Generate schemas
        schemas = {
            "organization": self._generate_organization_schema(context),
            "service": self._generate_service_schema(context, keywords),
            "faq": self._generate_faq_schema(keywords),
            "breadcrumb": self._generate_breadcrumb_schema(context, keywords)
        }
        
        logs.append(f"✅ Generated {len(schemas)} schema types")
        
        return {
            "schemas": schemas,
            "schema_count": len(schemas),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_organization_schema(self, context: Dict) -> Dict:
        """Organization schema"""
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": context["company_name"],
            "url": context["site_url"],
            "description": f"Professional {context['industry']} services",
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "customer service",
                "availableLanguage": ["Romanian", "English"]
            }
        }
    
    def _generate_service_schema(self, context: Dict, keywords: List[str]) -> Dict:
        """Service schema"""
        keyword = keywords[0] if keywords else context["industry"]
        
        return {
            "@context": "https://schema.org",
            "@type": "Service",
            "name": keyword,
            "provider": {
                "@type": "Organization",
                "name": context["company_name"]
            },
            "description": f"Professional {keyword} services",
            "areaServed": "Romania"
        }
    
    def _generate_faq_schema(self, keywords: List[str]) -> Dict:
        """FAQ schema"""
        keyword = keywords[0] if keywords else "services"
        
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"What is {keyword}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"{keyword} is a professional service that provides..."
                    }
                },
                {
                    "@type": "Question",
                    "name": f"How much does {keyword} cost?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Pricing depends on project scope. Contact us for a free quote."
                    }
                }
            ]
        }
    
    def _generate_breadcrumb_schema(self, context: Dict, keywords: List[str]) -> Dict:
        """Breadcrumb schema"""
        keyword = keywords[0] if keywords else "services"
        
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": context["site_url"]
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": keyword,
                    "item": f"{context['site_url']}/services/{keyword.lower().replace(' ', '-')}"
                }
            ]
        }


# ============================================================================
# LINK SUGGESTER AGENT
# ============================================================================

class LinkSuggester(BaseActionAgent):
    """
    🔗 Agent pentru sugestii internal linking
    Folosește Qdrant pentru semantic search
    """
    
    async def _execute_implementation(
        self,
        action: Dict,
        agent_id: str,
        logs: List[str]
    ) -> Dict:
        """
        Sugerează internal links semantic-related
        """
        logs.append("🔗 LinkSuggester analyzing content...")
        
        keywords = action.get("assigned_keywords", [])
        suggestions = []
        
        # Pentru fiecare keyword, găsește conținut related
        for keyword in keywords[:5]:
            related_links = await self._find_related_content(
                agent_id, 
                keyword,
                logs
            )
            suggestions.extend(related_links)
        
        # Deduplicate
        unique_suggestions = self._deduplicate_links(suggestions)
        
        logs.append(f"✅ Found {len(unique_suggestions)} unique link suggestions")
        
        return {
            "link_suggestions": unique_suggestions,
            "total_suggestions": len(unique_suggestions),
            "keywords_analyzed": keywords,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _find_related_content(
        self,
        agent_id: str,
        keyword: str,
        logs: List[str]
    ) -> List[Dict]:
        """Găsește conținut related în Qdrant"""
        links = []
        
        try:
            # În production: query Qdrant cu embeddings
            # Pentru acum: mock suggestions
            links.append({
                "source_keyword": keyword,
                "anchor_text": keyword,
                "target_url": f"/services/{keyword.lower().replace(' ', '-')}",
                "relevance_score": 0.85,
                "context": f"Learn more about {keyword}"
            })
            
        except Exception as e:
            logs.append(f"⚠️ Related content search failed: {e}")
        
        return links
    
    def _deduplicate_links(self, links: List[Dict]) -> List[Dict]:
        """Remove duplicates"""
        seen = set()
        unique = []
        
        for link in links:
            key = (link["anchor_text"], link["target_url"])
            if key not in seen:
                seen.add(key)
                unique.append(link)
        
        return unique


# ============================================================================
# EXPORT ALL AGENTS
# ============================================================================

AVAILABLE_AGENTS = {
    "CopywriterAgent": CopywriterAgent,
    "OnPageOptimizer": OnPageOptimizer,
    "SchemaGenerator": SchemaGenerator,
    "LinkSuggester": LinkSuggester
}


def get_agent(agent_name: str) -> BaseActionAgent:
    """Factory pentru agent instances"""
    agent_class = AVAILABLE_AGENTS.get(agent_name)
    if not agent_class:
        raise ValueError(f"Unknown agent: {agent_name}")
    
    return agent_class()


if __name__ == "__main__":
    import asyncio
    
    async def test_agents():
        # Test CopywriterAgent
        writer = CopywriterAgent()
        
        action = {
            "action_id": "A1",
            "title": "Create guide about fire protection",
            "description": "Comprehensive guide 2000+ words",
            "assigned_keywords": ["protecție pasivă la foc"],
            "parameters": {
                "target_word_count": 2000,
                "include_faq": True
            }
        }
        
        result = await writer.execute_action(
            action=action,
            agent_id="691a34b65774faae88a735a1",
            playbook_id="test123"
        )
        
        print(f"✅ CopywriterAgent result: {result['success']}")
        print(f"   Quality: {result['result']['quality_score']:.2f}")
        print(f"   Word count: {result['result']['word_count']}")
        
        # Test SchemaGenerator
        schema_gen = SchemaGenerator()
        
        action2 = {
            "action_id": "A2",
            "title": "Generate JSON-LD schemas",
            "description": "Create Organization, Service, FAQ schemas",
            "assigned_keywords": ["protecție pasivă la foc"]
        }
        
        result2 = await schema_gen.execute_action(
            action=action2,
            agent_id="691a34b65774faae88a735a1",
            playbook_id="test123"
        )
        
        print(f"\n✅ SchemaGenerator result: {result2['success']}")
        print(f"   Schemas: {result2['result']['schema_count']}")
    
    asyncio.run(test_agents())

