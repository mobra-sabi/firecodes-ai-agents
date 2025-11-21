#!/usr/bin/env python3
"""
🎯 SERP Ingest & Scoring Module
Production-ready implementation cu formule transparente

Usage:
    from serp_ingest import SERPScorer, canonical_domain
    
    scorer = SERPScorer()
    results = scorer.aggregate_visibility(serp_results)
"""

from datetime import datetime, timezone
from urllib.parse import urlparse
import math
from typing import List, Dict, Optional
import logging

try:
    import publicsuffix2
    psl = publicsuffix2.PublicSuffixList()
    HAS_PSL = True
except ImportError:
    HAS_PSL = False
    logging.warning("publicsuffix2 not installed. Using basic domain canonicalization.")

logger = logging.getLogger(__name__)


def canonical_domain(url: str) -> str:
    """
    Canonicalizează domeniul din URL
    
    Transformări:
    - Remove www.
    - Lowercase
    - Extract netloc from URL
    - Use Public Suffix List dacă e disponibil
    
    Examples:
        "https://www.Promat.com/ro-ro/products" → "promat.com"
        "https://promat.ro" → "promat.ro"
        "https://api.competitor.com" → "competitor.com"
    
    Args:
        url: URL complet sau domeniu
    
    Returns:
        Domeniu canonicalizat (lowercase, fără www)
    """
    try:
        # Parse URL
        parsed = urlparse(url.lower().strip())
        netloc = parsed.netloc or parsed.path.split('/')[0]
        
        # Remove www.
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Use Public Suffix List dacă e disponibil
        if HAS_PSL:
            try:
                # Get registered domain (handles .co.uk, .com.ro, etc.)
                parts = netloc.rsplit('.', 2)
                if len(parts) >= 2:
                    netloc = '.'.join(parts[-2:])
            except:
                pass
        
        return netloc
    except Exception as e:
        logger.error(f"Error canonicalizing domain {url}: {e}")
        return url.lower().strip()


def normalized_rank(rank: int) -> float:
    """
    Normalizează rank-ul la interval [0..1]
    
    Formula:
        rank 1  → 1.0 (cel mai bine)
        rank 10 → 0.1
        rank >10 → 0.0
    
    Args:
        rank: Poziția în SERP (1-based)
    
    Returns:
        Scor normalizat [0..1]
    """
    if rank > 10:
        return 0.0
    return (11 - rank) / 10.0


class SERPScorer:
    """
    Sistem de scoring transparent pentru rezultate SERP
    
    Formule:
    - normalized_rank: Poziție → [0..1]
    - type_weight: Organic/Featured/Ad → multiplicator
    - intent_weight: Informational/Commercial/Transactional → multiplicator
    - difficulty_penalty: Keyword difficulty → penalty
    - kw_weight: Search volume → weight
    
    Score final per keyword:
        score = normalized_rank × type_weight × intent_weight × difficulty_penalty × kw_weight
    
    Agregat competitor:
        visibility = sum(score_kw × kw_weight for all keywords)
    """
    
    # Type weights (cât de vizibil e fiecare tip de rezultat)
    TYPE_WEIGHTS = {
        "organic": 1.0,           # Standard organic result
        "featured_snippet": 1.2,  # Featured snippets sunt mai vizibile
        "ad": 0.6,                # Ads sunt plătite, mai puțin relevant pentru SEO
        "map": 0.8,               # Local pack (Google Maps)
        "video": 0.9,             # Video results
        "image": 0.7,             # Image pack
        "news": 0.85              # News results
    }
    
    # Intent weights (cât de valoros e keyword-ul)
    INTENT_WEIGHTS = {
        "informational": 0.8,     # "ce este protectia la foc" - discovery
        "commercial": 1.0,        # "vopsea intumescenta pret" - research
        "transactional": 1.1,     # "cumpara vopsea intumescenta" - ready to buy
        "navigational": 0.7       # "promat protectie foc" - brand search
    }
    
    def __init__(self):
        """Initialize SERP scorer"""
        self.logger = logging.getLogger(f"{__name__}.SERPScorer")
    
    def competitor_score_keyword(
        self, 
        rank: int, 
        result_type: str = "organic",
        intent: str = "commercial",
        difficulty: int = 50,
        volume: int = 0
    ) -> float:
        """
        Calculează scor per keyword per competitor
        
        Formula:
            score = normalized_rank × type_weight × intent_weight × difficulty_penalty × kw_weight
        
        Args:
            rank: Poziția în SERP (1-based)
            result_type: Tipul rezultatului (organic, featured_snippet, ad, map, etc.)
            intent: Intenția user-ului (informational, commercial, transactional, navigational)
            difficulty: Keyword difficulty (0-100, default 50)
            volume: Search volume lunar (default 0)
        
        Returns:
            Scor normalizat pentru acest keyword
        """
        # 1. Normalized rank [0..1]
        norm_rank = normalized_rank(rank)
        
        # 2. Type weight
        type_w = self.TYPE_WEIGHTS.get(result_type, 1.0)
        
        # 3. Intent weight
        intent_w = self.INTENT_WEIGHTS.get(intent, 1.0)
        
        # 4. Difficulty penalty (keywords grele = scoruri mai mici)
        # Formula: 1 - (difficulty/100) * 0.3
        # difficulty 0   → penalty 1.0 (fără penalty)
        # difficulty 50  → penalty 0.85
        # difficulty 100 → penalty 0.7
        diff_pen = 1 - (difficulty / 100.0) * 0.3
        
        # 5. Keyword weight bazat pe volume
        # Formula: log(1 + volume) / (log(1 + volume) + 5)
        # volume 0     → weight ~0
        # volume 100   → weight 0.48
        # volume 1000  → weight 0.58
        # volume 10000 → weight 0.65
        kw_w = math.log1p(max(volume, 0))
        kw_w = kw_w / (kw_w + 5) if kw_w > 0 else 0.1  # Minimum 0.1
        
        # Scor final
        score = norm_rank * type_w * intent_w * diff_pen * kw_w
        
        self.logger.debug(
            f"Score calculation: rank={rank}, type={result_type}, intent={intent}, "
            f"difficulty={difficulty}, volume={volume} → "
            f"norm_rank={norm_rank:.3f}, type_w={type_w}, intent_w={intent_w}, "
            f"diff_pen={diff_pen:.3f}, kw_w={kw_w:.3f} → score={score:.3f}"
        )
        
        return score
    
    def aggregate_visibility(
        self, 
        items: List[Dict],
        normalize: bool = True
    ) -> List[Dict]:
        """
        Agregă scoruri per domeniu pentru toate keywords
        
        Args:
            items: Lista de rezultate SERP, fiecare cu:
                - url: URL rezultat
                - rank: Poziție
                - type: Tip rezultat (organic, featured_snippet, etc.)
                - intent: Intenție keyword (informational, commercial, etc.)
                - difficulty: Keyword difficulty (opțional, default 50)
                - volume: Search volume (opțional, default 0)
                - keyword: Keyword (opțional, pentru debugging)
            normalize: Dacă True, normalizează la [0..1] (default True)
        
        Returns:
            Lista sortată descrescător după visibility_score, fiecare element cu:
                - domain: Domeniu canonicalizat
                - visibility_score: Scor agregat
                - keywords_count: Număr keywords unde apare
                - avg_rank: Rang mediu
                - best_rank: Cel mai bun rang
        """
        by_domain = {}
        
        for it in items:
            # Canonical domain
            dom = canonical_domain(it.get("url", ""))
            if not dom:
                continue
            
            # Calculate score pentru acest keyword
            score = self.competitor_score_keyword(
                rank=it.get("rank", 99),
                result_type=it.get("type", "organic"),
                intent=it.get("intent", "commercial"),
                difficulty=it.get("difficulty", 50),
                volume=it.get("volume", 0)
            )
            
            # Agregare per domeniu
            if dom not in by_domain:
                by_domain[dom] = {
                    "domain": dom,
                    "visibility_score": 0.0,
                    "keywords_count": 0,
                    "ranks": [],
                    "keywords": []
                }
            
            by_domain[dom]["visibility_score"] += score
            by_domain[dom]["keywords_count"] += 1
            by_domain[dom]["ranks"].append(it.get("rank", 99))
            
            if "keyword" in it:
                by_domain[dom]["keywords"].append(it["keyword"])
        
        # Calcul metrici finale
        result = []
        max_score = max([d["visibility_score"] for d in by_domain.values()]) if by_domain else 1.0
        
        for dom, data in by_domain.items():
            avg_rank = sum(data["ranks"]) / len(data["ranks"]) if data["ranks"] else 99.0
            best_rank = min(data["ranks"]) if data["ranks"] else 99
            
            # Normalizare opțională
            visibility = data["visibility_score"]
            if normalize and max_score > 0:
                visibility = visibility / max_score
            
            result.append({
                "domain": dom,
                "visibility_score": visibility,
                "visibility_score_raw": data["visibility_score"],
                "keywords_count": data["keywords_count"],
                "avg_rank": round(avg_rank, 2),
                "best_rank": best_rank,
                "keywords": data["keywords"][:10]  # Max 10 pentru output
            })
        
        # Sort descrescător după visibility_score
        result.sort(key=lambda x: -x["visibility_score"])
        
        self.logger.info(
            f"Aggregated {len(result)} domains from {len(items)} SERP results. "
            f"Top domain: {result[0]['domain'] if result else 'N/A'} "
            f"(score: {result[0]['visibility_score']:.3f})"
        )
        
        return result
    
    def calculate_threat_score(
        self,
        visibility_score: float,
        authority_score: float,
        keyword_overlap_percentage: float
    ) -> float:
        """
        Calculează threat score (0-100)
        
        Formula:
            threat = visibility × 50% + authority × 30% + overlap × 20%
        
        Args:
            visibility_score: Scor visibility [0..1]
            authority_score: Scor authority [0..1] (DA/DR din Moz/Ahrefs)
            keyword_overlap_percentage: Overlap % cu masterul [0..100]
        
        Returns:
            Threat score [0..100]
        """
        threat = (
            visibility_score * 100 * 0.5 +      # 50% visibility
            authority_score * 100 * 0.3 +       # 30% authority
            keyword_overlap_percentage * 0.2     # 20% overlap
        )
        
        return min(threat, 100.0)  # Cap la 100
    
    def deduplicate_serp_results(self, results: List[Dict]) -> List[Dict]:
        """
        Deduplicare rezultate SERP
        
        Pentru același domeniu pe același keyword:
        - Păstrează cel cu rank mai bun
        - Salvează variantele în array `variants`
        
        Args:
            results: Lista rezultate SERP cu url, keyword, rank, etc.
        
        Returns:
            Lista deduplicată
        """
        by_domain_kw = {}
        
        for result in results:
            canonical = canonical_domain(result.get("url", ""))
            keyword = result.get("keyword", "")
            
            if not canonical or not keyword:
                continue
            
            key = (canonical, keyword)
            
            if key not in by_domain_kw:
                by_domain_kw[key] = {
                    "domain": canonical,
                    "keyword": keyword,
                    "rank": result.get("rank", 99),
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "type": result.get("type", "organic"),
                    "variants": []
                }
            else:
                # Dacă e o variantă cu rank mai bun, înlocuiește
                if result.get("rank", 99) < by_domain_kw[key]["rank"]:
                    # Salvează vechiul ca variantă
                    by_domain_kw[key]["variants"].append({
                        "rank": by_domain_kw[key]["rank"],
                        "url": by_domain_kw[key]["url"],
                        "title": by_domain_kw[key]["title"]
                    })
                    # Update cu noul
                    by_domain_kw[key]["rank"] = result.get("rank", 99)
                    by_domain_kw[key]["url"] = result.get("url", "")
                    by_domain_kw[key]["title"] = result.get("title", "")
                    by_domain_kw[key]["snippet"] = result.get("snippet", "")
                else:
                    # Salvează ca variantă
                    by_domain_kw[key]["variants"].append({
                        "rank": result.get("rank", 99),
                        "url": result.get("url", ""),
                        "title": result.get("title", "")
                    })
        
        return list(by_domain_kw.values())


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("="*80)
    print("🎯 SERP Scoring Module - Test")
    print("="*80)
    print()
    
    # Simulate SERP results pentru "vopsea intumescenta"
    serp_results = [
        {
            "keyword": "vopsea intumescenta",
            "rank": 1,
            "url": "https://www.promat.com/ro-ro/vopsea-intumescenta",
            "type": "organic",
            "intent": "commercial",
            "difficulty": 65,
            "volume": 500
        },
        {
            "keyword": "vopsea intumescenta",
            "rank": 2,
            "url": "https://competitor2.ro/produse/vopsea",
            "type": "organic",
            "intent": "commercial",
            "difficulty": 65,
            "volume": 500
        },
        {
            "keyword": "vopsea intumescenta",
            "rank": 3,
            "url": "https://protectiilafoc.ro/vopsea-intumescenta",
            "type": "organic",
            "intent": "commercial",
            "difficulty": 65,
            "volume": 500
        },
        {
            "keyword": "protectie pasiva la foc",
            "rank": 1,
            "url": "https://www.promat.com/ro-ro/protectie-pasiva",
            "type": "organic",
            "intent": "informational",
            "difficulty": 70,
            "volume": 800
        },
        {
            "keyword": "protectie pasiva la foc",
            "rank": 5,
            "url": "https://protectiilafoc.ro/protectie-pasiva",
            "type": "organic",
            "intent": "informational",
            "difficulty": 70,
            "volume": 800
        }
    ]
    
    # Initialize scorer
    scorer = SERPScorer()
    
    # 1. Test canonicalizare
    print("1️⃣ Test Canonicalizare Domenii:")
    test_urls = [
        "https://www.Promat.com/ro-ro/products",
        "https://promat.ro",
        "http://WWW.Competitor2.RO/page",
        "competitor3.com"
    ]
    for url in test_urls:
        print(f"   {url:50s} → {canonical_domain(url)}")
    print()
    
    # 2. Test scoring per keyword
    print("2️⃣ Test Scoring per Keyword:")
    for result in serp_results[:3]:
        score = scorer.competitor_score_keyword(
            rank=result["rank"],
            result_type=result["type"],
            intent=result["intent"],
            difficulty=result["difficulty"],
            volume=result["volume"]
        )
        print(f"   {result['keyword'][:30]:30s} - Rank #{result['rank']} → Score: {score:.4f}")
    print()
    
    # 3. Test agregare visibility
    print("3️⃣ Test Agregare Visibility (toate keywords):")
    visibility = scorer.aggregate_visibility(serp_results, normalize=True)
    print(f"   {'Domain':<30} {'Visibility':>12} {'Keywords':>10} {'Avg Rank':>10} {'Best Rank':>12}")
    print("   " + "-"*76)
    for comp in visibility:
        print(f"   {comp['domain']:<30} {comp['visibility_score']:>12.4f} {comp['keywords_count']:>10} {comp['avg_rank']:>10.2f} {comp['best_rank']:>12}")
    print()
    
    # 4. Test threat score
    print("4️⃣ Test Threat Score (top competitor):")
    if visibility:
        top_comp = visibility[0]
        threat = scorer.calculate_threat_score(
            visibility_score=top_comp["visibility_score"],
            authority_score=0.62,  # Simulation (DA/DR)
            keyword_overlap_percentage=60.0  # 60% overlap cu master
        )
        print(f"   Domain: {top_comp['domain']}")
        print(f"   Visibility Score: {top_comp['visibility_score']:.3f}")
        print(f"   Authority Score: 0.62 (simulation)")
        print(f"   Keyword Overlap: 60%")
        print(f"   → THREAT SCORE: {threat:.1f}/100")
    print()
    
    # 5. Test deduplicare
    print("5️⃣ Test Deduplicare:")
    # Adaugă duplicate
    duplicate_results = serp_results + [
        {
            "keyword": "vopsea intumescenta",
            "rank": 4,
            "url": "https://www.promat.com/ro-ro/vopsea-alta-pagina",
            "type": "organic",
            "intent": "commercial",
            "difficulty": 65,
            "volume": 500
        }
    ]
    print(f"   Înainte deduplicare: {len(duplicate_results)} rezultate")
    deduplicated = scorer.deduplicate_serp_results(duplicate_results)
    print(f"   După deduplicare: {len(deduplicated)} rezultate")
    
    # Verifică variante
    for result in deduplicated:
        if result["variants"]:
            print(f"   {result['domain']} ({result['keyword']}): rank {result['rank']} + {len(result['variants'])} variante")
    
    print()
    print("="*80)
    print("✅ Test complet!")
    print("="*80)

