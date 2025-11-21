"""
Mirror Agent Security & Whitelist System
Issue 8: Aplică whitelist strict pe domeniu în mirror
- Reguli guvernanță, PII scrubbing, cross-domain protection
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import requests
from pymongo import MongoClient
import openai
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecurityViolation:
    """Înregistrare pentru încălcări de securitate"""
    violation_id: str
    site_id: str
    violation_type: str  # "domain_violation", "pii_detected", "cross_domain", "unauthorized_access"
    details: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self):
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class DomainWhitelist:
    """Configurare whitelist pentru domenii"""
    site_id: str
    allowed_domains: List[str]
    blocked_domains: List[str]
    strict_mode: bool
    cross_domain_blocked: bool
    pii_scrubbing_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self):
        result = asdict(self)
        if isinstance(self.created_at, datetime):
            result['created_at'] = self.created_at.isoformat()
        if isinstance(self.updated_at, datetime):
            result['updated_at'] = self.updated_at.isoformat()
        return result

class PIIScrubber:
    """Sistem pentru eliminarea datelor personale"""
    
    def __init__(self):
        # Patterns pentru PII
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?40|0)[0-9]{9}|(\+?40|0)[0-9]{3}[-\s]?[0-9]{3}[-\s]?[0-9]{3}',
            'cnp': r'\b[1-9][0-9]{12}\b',  # CNP românesc
            'iban': r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b',
            'credit_card': r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
            'address': r'\b(str\.|strada|bulevardul|bd\.|aleea|nr\.|numărul)\s+[A-Za-z0-9\s,.-]+\b',
            'name': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'  # Nume complet
        }
        
        # Replacement patterns
        self.replacements = {
            'email': '[EMAIL_REDACTED]',
            'phone': '[PHONE_REDACTED]',
            'cnp': '[CNP_REDACTED]',
            'iban': '[IBAN_REDACTED]',
            'credit_card': '[CARD_REDACTED]',
            'address': '[ADDRESS_REDACTED]',
            'name': '[NAME_REDACTED]'
        }
    
    def scrub_text(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Elimină PII din text și returnează textul curat și detaliile"""
        scrubbed_text = text
        detected_pii = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                original = match.group()
                replacement = self.replacements[pii_type]
                
                # Înlocuiește în text
                scrubbed_text = scrubbed_text.replace(original, replacement)
                
                # Adaugă la lista de PII detectate
                detected_pii.append({
                    'type': pii_type,
                    'original': original,
                    'replacement': replacement,
                    'position': match.span()
                })
        
        return scrubbed_text, detected_pii
    
    def is_pii_present(self, text: str) -> bool:
        """Verifică dacă textul conține PII"""
        for pattern in self.pii_patterns.values():
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

class MirrorSecurityManager:
    """Manager pentru securitatea Mirror Agents"""
    
    def __init__(self, api_base_url: str = "http://localhost:8083"):
        self.api_base_url = api_base_url
        self.db = MongoClient("mongodb://localhost:27017").mirror_security
        self.pii_scrubber = PIIScrubber()
        self.openai_client = openai.OpenAI()
        
        # Cache pentru performanță
        self.whitelist_cache = {}
        self.security_rules_cache = {}
    
    async def validate_domain_access(self, site_id: str, request_domain: str, 
                                   user_ip: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Validează accesul la domeniu conform whitelist-ului"""
        logger.info(f"🔒 Validating domain access for {site_id}: {request_domain}")
        
        # Obține whitelist-ul pentru site
        whitelist = await self._get_whitelist(site_id)
        
        if not whitelist:
            # Creează whitelist implicit
            whitelist = await self._create_default_whitelist(site_id)
        
        # Verifică dacă domeniul este permis
        is_allowed = self._is_domain_allowed(request_domain, whitelist)
        
        if not is_allowed:
            # Log violation
            violation = SecurityViolation(
                violation_id=f"violation_{int(datetime.now().timestamp())}",
                site_id=site_id,
                violation_type="domain_violation",
                details=f"Unauthorized domain access attempt: {request_domain}",
                severity="high",
                timestamp=datetime.now(timezone.utc),
                user_ip=user_ip,
                user_agent=user_agent
            )
            
            await self._log_violation(violation)
            
            return {
                "ok": False,
                "allowed": False,
                "violation": violation.to_dict(),
                "message": f"Domain {request_domain} is not whitelisted for site {site_id}"
            }
        
        return {
            "ok": True,
            "allowed": True,
            "whitelist": whitelist.to_dict(),
            "message": f"Domain {request_domain} is authorized for site {site_id}"
        }
    
    async def scrub_pii_content(self, content: str, site_id: str) -> Dict[str, Any]:
        """Elimină PII din conținut"""
        logger.info(f"🧹 Scrubbing PII for {site_id}")
        
        # Verifică dacă PII scrubbing este activat
        whitelist = await self._get_whitelist(site_id)
        
        if not whitelist or not whitelist.pii_scrubbing_enabled:
            return {
                "ok": True,
                "scrubbed": False,
                "content": content,
                "message": "PII scrubbing is disabled for this site"
            }
        
        # Scrub PII
        scrubbed_content, detected_pii = self.pii_scrubber.scrub_text(content)
        
        # Log dacă s-a detectat PII
        if detected_pii:
            violation = SecurityViolation(
                violation_id=f"pii_{int(datetime.now().timestamp())}",
                site_id=site_id,
                violation_type="pii_detected",
                details=f"PII detected and scrubbed: {len(detected_pii)} items",
                severity="medium",
                timestamp=datetime.now(timezone.utc)
            )
            
            await self._log_violation(violation)
        
        return {
            "ok": True,
            "scrubbed": len(detected_pii) > 0,
            "content": scrubbed_content,
            "detected_pii": detected_pii,
            "violation_logged": len(detected_pii) > 0,
            "message": f"PII scrubbing completed: {len(detected_pii)} items processed"
        }
    
    async def validate_cross_domain_query(self, site_id: str, query: str, 
                                        target_domain: str = None) -> Dict[str, Any]:
        """Validează căutările cross-domain"""
        logger.info(f"🌐 Validating cross-domain query for {site_id}")
        
        whitelist = await self._get_whitelist(site_id)
        
        if not whitelist or not whitelist.cross_domain_blocked:
            return {
                "ok": True,
                "cross_domain_allowed": True,
                "message": "Cross-domain queries are allowed for this site"
            }
        
        # Verifică dacă query-ul conține referințe la alte domenii
        domain_references = self._extract_domain_references(query)
        
        if domain_references:
            # Verifică dacă domeniile sunt în whitelist
            unauthorized_domains = []
            for domain in domain_references:
                if not self._is_domain_allowed(domain, whitelist):
                    unauthorized_domains.append(domain)
            
            if unauthorized_domains:
                violation = SecurityViolation(
                    violation_id=f"cross_domain_{int(datetime.now().timestamp())}",
                    site_id=site_id,
                    violation_type="cross_domain",
                    details=f"Cross-domain query blocked: {unauthorized_domains}",
                    severity="medium",
                    timestamp=datetime.now(timezone.utc)
                )
                
                await self._log_violation(violation)
                
                return {
                    "ok": False,
                    "cross_domain_allowed": False,
                    "unauthorized_domains": unauthorized_domains,
                    "violation": violation.to_dict(),
                    "message": f"Cross-domain queries blocked: {unauthorized_domains}"
                }
        
        return {
            "ok": True,
            "cross_domain_allowed": True,
            "message": "Cross-domain query validation passed"
        }
    
    async def _get_whitelist(self, site_id: str) -> Optional[DomainWhitelist]:
        """Obține whitelist-ul pentru un site"""
        try:
            # Verifică cache-ul
            if site_id in self.whitelist_cache:
                return self.whitelist_cache[site_id]
            
            # Caută în baza de date
            whitelist_data = self.db.domain_whitelists.find_one({"site_id": site_id})
            
            if whitelist_data:
                whitelist = DomainWhitelist(
                    site_id=whitelist_data["site_id"],
                    allowed_domains=whitelist_data["allowed_domains"],
                    blocked_domains=whitelist_data["blocked_domains"],
                    strict_mode=whitelist_data["strict_mode"],
                    cross_domain_blocked=whitelist_data["cross_domain_blocked"],
                    pii_scrubbing_enabled=whitelist_data["pii_scrubbing_enabled"],
                    created_at=whitelist_data["created_at"],
                    updated_at=whitelist_data["updated_at"]
                )
                
                # Adaugă în cache
                self.whitelist_cache[site_id] = whitelist
                return whitelist
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting whitelist: {e}")
            return None
    
    async def _create_default_whitelist(self, site_id: str) -> DomainWhitelist:
        """Creează whitelist implicit pentru un site"""
        logger.info(f"🔧 Creating default whitelist for {site_id}")
        
        # Extrage domeniul din site_id
        domain = site_id.replace("_", ".").split("_")[0] if "_" in site_id else site_id
        
        whitelist = DomainWhitelist(
            site_id=site_id,
            allowed_domains=[domain, f"www.{domain}"],
            blocked_domains=[],
            strict_mode=True,
            cross_domain_blocked=True,
            pii_scrubbing_enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Salvează în baza de date
        self.db.domain_whitelists.insert_one(whitelist.to_dict())
        
        # Adaugă în cache
        self.whitelist_cache[site_id] = whitelist
        
        return whitelist
    
    def _is_domain_allowed(self, domain: str, whitelist: DomainWhitelist) -> bool:
        """Verifică dacă un domeniu este permis"""
        # Normalizează domeniul
        normalized_domain = domain.lower().strip()
        
        # Verifică dacă este în lista de blocare
        for blocked in whitelist.blocked_domains:
            if normalized_domain == blocked.lower() or normalized_domain.endswith(f".{blocked.lower()}"):
                return False
        
        # Verifică dacă este în lista de permisiuni
        for allowed in whitelist.allowed_domains:
            if normalized_domain == allowed.lower() or normalized_domain.endswith(f".{allowed.lower()}"):
                return True
        
        # În mod strict, dacă nu este explicit permis, este blocat
        return not whitelist.strict_mode
    
    def _extract_domain_references(self, text: str) -> List[str]:
        """Extrage referințele la domenii din text"""
        # Pattern pentru domenii
        domain_pattern = r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:[a-zA-Z]{2,}))\b'
        
        matches = re.findall(domain_pattern, text, re.IGNORECASE)
        return list(set(matches))  # Elimină duplicatele
    
    async def _log_violation(self, violation: SecurityViolation):
        """Loghează o încălcare de securitate"""
        try:
            self.db.security_violations.insert_one(violation.to_dict())
            logger.warning(f"🚨 Security violation logged: {violation.violation_type} for {violation.site_id}")
        except Exception as e:
            logger.error(f"Error logging violation: {e}")
    
    async def update_whitelist(self, site_id: str, whitelist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizează whitelist-ul pentru un site"""
        try:
            logger.info(f"🔧 Updating whitelist for {site_id}")
            
            # Validează datele
            allowed_domains = whitelist_data.get("allowed_domains", [])
            blocked_domains = whitelist_data.get("blocked_domains", [])
            strict_mode = whitelist_data.get("strict_mode", True)
            cross_domain_blocked = whitelist_data.get("cross_domain_blocked", True)
            pii_scrubbing_enabled = whitelist_data.get("pii_scrubbing_enabled", True)
            
            # Actualizează în baza de date
            result = self.db.domain_whitelists.update_one(
                {"site_id": site_id},
                {"$set": {
                    "allowed_domains": allowed_domains,
                    "blocked_domains": blocked_domains,
                    "strict_mode": strict_mode,
                    "cross_domain_blocked": cross_domain_blocked,
                    "pii_scrubbing_enabled": pii_scrubbing_enabled,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            
            # Actualizează cache-ul
            if site_id in self.whitelist_cache:
                del self.whitelist_cache[site_id]
            
            logger.info(f"✅ Whitelist updated for {site_id}")
            
            return {
                "ok": True,
                "site_id": site_id,
                "updated": result.modified_count > 0,
                "created": result.upserted_id is not None,
                "whitelist": whitelist_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating whitelist: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_security_dashboard(self, site_id: str) -> Dict[str, Any]:
        """Returnează dashboard-ul de securitate pentru un site"""
        try:
            # Obține whitelist-ul
            whitelist = await self._get_whitelist(site_id)
            
            # Obține încălcările recente
            recent_violations = list(self.db.security_violations.find(
                {"site_id": site_id}
            ).sort("timestamp", -1).limit(10))
            
            # Calculează statistici
            total_violations = self.db.security_violations.count_documents({"site_id": site_id})
            violations_24h = self.db.security_violations.count_documents({
                "site_id": site_id,
                "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            # Calculează distribuția pe tipuri
            violation_types = {}
            for violation in recent_violations:
                vtype = violation["violation_type"]
                violation_types[vtype] = violation_types.get(vtype, 0) + 1
            
            # Convertim timestamp-urile și ObjectId-urile pentru recent_violations
            for violation in recent_violations:
                violation['_id'] = str(violation['_id'])
                if 'timestamp' in violation and isinstance(violation['timestamp'], datetime):
                    violation['timestamp'] = violation['timestamp'].isoformat()
            
            # Convertim whitelist-ul
            whitelist_dict = None
            if whitelist:
                whitelist_dict = whitelist.to_dict()
            
            return {
                "ok": True,
                "site_id": site_id,
                "whitelist": whitelist_dict,
                "security_stats": {
                    "total_violations": total_violations,
                    "violations_24h": violations_24h,
                    "violation_types": violation_types
                },
                "recent_violations": recent_violations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting security dashboard: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Funcții helper pentru API
async def validate_mirror_security(site_id: str, request_domain: str, 
                                user_ip: str = None, user_agent: str = None) -> Dict[str, Any]:
    """Validează securitatea pentru un Mirror Agent"""
    security_manager = MirrorSecurityManager()
    return await security_manager.validate_domain_access(site_id, request_domain, user_ip, user_agent)

async def scrub_mirror_content(content: str, site_id: str) -> Dict[str, Any]:
    """Elimină PII din conținutul Mirror Agent"""
    security_manager = MirrorSecurityManager()
    return await security_manager.scrub_pii_content(content, site_id)

async def validate_cross_domain_mirror(site_id: str, query: str, target_domain: str = None) -> Dict[str, Any]:
    """Validează căutările cross-domain pentru Mirror Agent"""
    security_manager = MirrorSecurityManager()
    return await security_manager.validate_cross_domain_query(site_id, query, target_domain)

def get_security_stats() -> Dict[str, Any]:
    """Returnează statistici globale de securitate"""
    db = MongoClient("mongodb://localhost:27017").mirror_security
    
    # Calculează statistici globale
    total_sites = len(db.domain_whitelists.distinct("site_id"))
    total_violations = db.security_violations.count_documents({})
    
    # Calculează încălcările recente (ultimele 24h)
    recent_violations = db.security_violations.count_documents({
        "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
    })
    
    # Calculează distribuția pe severitate
    severity_distribution = {}
    for severity in ["low", "medium", "high", "critical"]:
        count = db.security_violations.count_documents({"severity": severity})
        severity_distribution[severity] = count
    
    return {
        "total_sites": total_sites,
        "total_violations": total_violations,
        "recent_violations_24h": recent_violations,
        "severity_distribution": severity_distribution,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
