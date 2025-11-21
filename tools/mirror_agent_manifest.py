#!/usr/bin/env python3
"""
Mirror Agent Manifest - Template pentru governance și reguli
Issue 1: Definește manifestul template pentru agentul Mirror (Q/A)
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import re

logger = logging.getLogger(__name__)

class MirrorAgentPurpose(Enum):
    """Scopul agentului Mirror"""
    FACTUAL_QA = "factual_qa"
    SITE_SPECIFIC = "site_specific"
    LEARNING_ENHANCEMENT = "learning_enhancement"
    FAQ_GENERATION = "faq_generation"

class FallbackStrategy(Enum):
    """Strategiile de fallback"""
    DONT_KNOW = "dont_know"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    SEARCH_WEB = "search_web"
    USE_GENERAL_KNOWLEDGE = "use_general_knowledge"

@dataclass
class CitationRequirement:
    """Cerințe pentru citări"""
    min_sources: int = 2
    max_sources: int = 5
    require_url: bool = True
    require_timestamp: bool = True
    quality_threshold: float = 0.8

@dataclass
class DomainWhitelist:
    """Whitelist de domenii permise"""
    allowed_domains: List[str]
    allow_subdomains: bool = True
    strict_mode: bool = True
    
    def is_allowed(self, url: str) -> bool:
        """Verifică dacă URL-ul este permis"""
        if not url:
            return False
            
        # Normalizează URL-ul
        url_clean = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
        
        for domain in self.allowed_domains:
            domain_clean = domain.lower().replace("www.", "")
            
            if self.allow_subdomains:
                if url_clean.endswith(domain_clean) or url_clean == domain_clean:
                    return True
            else:
                if url_clean == domain_clean:
                    return True
        
        return False

@dataclass
class Guardrails:
    """Guardrails pentru securitate și conformitate"""
    pii_scrubbing: bool = True
    content_filtering: bool = True
    response_length_limit: int = 2000
    max_iterations: int = 3
    confidence_threshold: float = 0.7
    
    # Patterns pentru PII scrubbing
    pii_patterns: Dict[str, str] = None
    
    def __post_init__(self):
        if self.pii_patterns is None:
            self.pii_patterns = {
                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "phone": r'\b\d{3}-\d{3}-\d{4}\b|\b\d{10}\b',
                "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
                "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
            }

@dataclass
class FallbackSteps:
    """Pași pentru fallback 'Nu știu'"""
    steps: List[str]
    escalation_threshold: float = 0.5
    human_escalation: bool = True
    
    def get_fallback_response(self, confidence: float) -> str:
        """Generează răspunsul de fallback bazat pe confidence"""
        if confidence < self.escalation_threshold:
            return self.steps[0] if self.steps else "Nu pot răspunde la această întrebare cu încredere suficientă."
        else:
            return self.steps[1] if len(self.steps) > 1 else self.steps[0]

@dataclass
class MirrorAgentManifest:
    """Manifest complet pentru agentul Mirror"""
    
    # Identificare
    manifest_id: str
    site_id: str
    domain: str
    version: str
    created_at: datetime
    
    # Scop și rol
    purpose: MirrorAgentPurpose
    description: str
    
    # Cerințe pentru citări
    citation_requirements: CitationRequirement
    
    # Whitelist de domenii
    domain_whitelist: DomainWhitelist
    
    # Guardrails și securitate
    guardrails: Guardrails
    
    # Strategii de fallback
    fallback_strategy: FallbackStrategy
    fallback_steps: FallbackSteps
    
    # Configurații tehnice
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    similarity_threshold: float = 0.83
    max_context_length: int = 4000
    
    # Metadate
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertește manifestul în dicționar pentru serializare"""
        data = asdict(self)
        # Convertește enum-urile în string-uri
        data['purpose'] = self.purpose.value
        data['fallback_strategy'] = self.fallback_strategy.value
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MirrorAgentManifest':
        """Creează manifest din dicționar"""
        # Ignoră _id din MongoDB
        data = {k: v for k, v in data.items() if k != '_id'}
        
        # Convertește string-urile în enum-uri
        data['purpose'] = MirrorAgentPurpose(data['purpose'])
        data['fallback_strategy'] = FallbackStrategy(data['fallback_strategy'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Creează obiectele nested
        data['citation_requirements'] = CitationRequirement(**data['citation_requirements'])
        data['domain_whitelist'] = DomainWhitelist(**data['domain_whitelist'])
        data['guardrails'] = Guardrails(**data['guardrails'])
        data['fallback_steps'] = FallbackSteps(**data['fallback_steps'])
        
        return cls(**data)
    
    def validate(self) -> Dict[str, Any]:
        """Validează manifestul și returnează rezultatul"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validări obligatorii
        if not self.site_id:
            validation_result["errors"].append("site_id is required")
            validation_result["valid"] = False
        
        if not self.domain:
            validation_result["errors"].append("domain is required")
            validation_result["valid"] = False
        
        if not self.domain_whitelist.allowed_domains:
            validation_result["errors"].append("domain_whitelist must have at least one domain")
            validation_result["valid"] = False
        
        # Validări de calitate
        if self.similarity_threshold < 0.5 or self.similarity_threshold > 1.0:
            validation_result["warnings"].append("similarity_threshold should be between 0.5 and 1.0")
        
        if self.citation_requirements.min_sources < 1:
            validation_result["warnings"].append("min_sources should be at least 1")
        
        return validation_result

class MirrorManifestManager:
    """Manager pentru manifestele agentului Mirror"""
    
    def __init__(self):
        self.manifests: Dict[str, MirrorAgentManifest] = {}
    
    def create_default_manifest(self, site_id: str, domain: str) -> MirrorAgentManifest:
        """Creează un manifest default pentru un site"""
        try:
            manifest_id = f"mirror_manifest_{site_id}_{uuid.uuid4().hex[:8]}"
            
            # Configurații default
            manifest = MirrorAgentManifest(
                manifest_id=manifest_id,
                site_id=site_id,
                domain=domain,
                version="1.0",
                created_at=datetime.now(timezone.utc),
                purpose=MirrorAgentPurpose.FACTUAL_QA,
                description=f"Mirror Q/A agent for {domain} - Factual question answering based on site content",
                
                citation_requirements=CitationRequirement(
                    min_sources=2,
                    max_sources=5,
                    require_url=True,
                    require_timestamp=True,
                    quality_threshold=0.8
                ),
                
                domain_whitelist=DomainWhitelist(
                    allowed_domains=[domain],
                    allow_subdomains=True,
                    strict_mode=True
                ),
                
                guardrails=Guardrails(
                    pii_scrubbing=True,
                    content_filtering=True,
                    response_length_limit=2000,
                    max_iterations=3,
                    confidence_threshold=0.7
                ),
                
                fallback_strategy=FallbackStrategy.DONT_KNOW,
                fallback_steps=FallbackSteps(
                    steps=[
                        "Nu pot răspunde la această întrebare cu încredere suficientă bazată pe conținutul site-ului.",
                        "Întrebarea depășește domeniul de expertiză al acestui agent.",
                        "Vă rog să reformulați întrebarea sau să contactați suportul tehnic."
                    ],
                    escalation_threshold=0.5,
                    human_escalation=True
                ),
                
                tags=["mirror", "qa", "factual", domain],
                metadata={
                    "auto_generated": True,
                    "template_version": "1.0",
                    "governance_level": "strict"
                }
            )
            
            # Validează manifestul
            validation = manifest.validate()
            if not validation["valid"]:
                raise ValueError(f"Manifest validation failed: {validation['errors']}")
            
            # Salvează manifestul
            self.manifests[manifest_id] = manifest
            
            logger.info(f"✅ Created default manifest for {domain}: {manifest_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"❌ Error creating default manifest: {e}")
            raise
    
    def get_manifest(self, manifest_id: str) -> Optional[MirrorAgentManifest]:
        """Obține un manifest după ID"""
        return self.manifests.get(manifest_id)
    
    def get_manifest_by_site(self, site_id: str) -> Optional[MirrorAgentManifest]:
        """Obține manifestul pentru un site"""
        for manifest in self.manifests.values():
            if manifest.site_id == site_id:
                return manifest
        return None
    
    def update_manifest(self, manifest_id: str, updates: Dict[str, Any]) -> bool:
        """Actualizează un manifest"""
        try:
            if manifest_id not in self.manifests:
                return False
            
            manifest = self.manifests[manifest_id]
            
            # Actualizează câmpurile permise
            allowed_fields = ['description', 'similarity_threshold', 'max_context_length', 'tags', 'metadata']
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(manifest, field, value)
            
            # Validează manifestul actualizat
            validation = manifest.validate()
            if not validation["valid"]:
                logger.warning(f"Manifest validation warnings: {validation['warnings']}")
            
            logger.info(f"✅ Updated manifest {manifest_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating manifest: {e}")
            return False
    
    def delete_manifest(self, manifest_id: str) -> bool:
        """Șterge un manifest"""
        try:
            if manifest_id in self.manifests:
                del self.manifests[manifest_id]
                logger.info(f"✅ Deleted manifest {manifest_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting manifest: {e}")
            return False
    
    def list_manifests(self) -> List[Dict[str, Any]]:
        """Listează toate manifestele"""
        return [manifest.to_dict() for manifest in self.manifests.values()]
    
    def save_manifest_to_db(self, manifest: MirrorAgentManifest) -> bool:
        """Salvează manifestul în MongoDB"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:9308')
            db = client['ai_agents_db']
            
            # Salvează manifestul
            manifest_data = manifest.to_dict()
            result = db.mirror_manifests.insert_one(manifest_data)
            
            logger.info(f"💾 Saved manifest to database: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving manifest to database: {e}")
            return False
    
    def load_manifests_from_db(self) -> int:
        """Încarcă manifestele din MongoDB"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:9308')
            db = client['ai_agents_db']
            
            manifests_data = list(db.mirror_manifests.find({}))
            loaded_count = 0
            
            for manifest_data in manifests_data:
                try:
                    manifest = MirrorAgentManifest.from_dict(manifest_data)
                    self.manifests[manifest.manifest_id] = manifest
                    loaded_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Error loading manifest {manifest_data.get('manifest_id', 'unknown')}: {e}")
            
            logger.info(f"📂 Loaded {loaded_count} manifests from database")
            return loaded_count
            
        except Exception as e:
            logger.error(f"❌ Error loading manifests from database: {e}")
            return 0

# Funcții de utilitate pentru API
def create_mirror_manifest_for_site(site_id: str, domain: str) -> Dict[str, Any]:
    """Creează un manifest pentru un site"""
    try:
        manager = MirrorManifestManager()
        manifest = manager.create_default_manifest(site_id, domain)
        
        # Salvează în baza de date
        manager.save_manifest_to_db(manifest)
        
        return {
            "ok": True,
            "message": f"Mirror manifest created for {domain}",
            "manifest_id": manifest.manifest_id,
            "site_id": manifest.site_id,
            "domain": manifest.domain,
            "version": manifest.version,
            "purpose": manifest.purpose.value,
            "validation": manifest.validate()
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating mirror manifest: {e}")
        return {
            "ok": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test
    def test_mirror_manifest():
        manager = MirrorManifestManager()
        
        # Test cu matari-antifoc.ro
        site_id = "matari_antifoc_ro_1761560625"
        domain = "matari-antifoc.ro"
        
        manifest = manager.create_default_manifest(site_id, domain)
        
        print("🧪 Mirror Manifest Test:")
        print("=" * 50)
        print(f"Manifest ID: {manifest.manifest_id}")
        print(f"Site ID: {manifest.site_id}")
        print(f"Domain: {manifest.domain}")
        print(f"Purpose: {manifest.purpose.value}")
        print(f"Citation Requirements: {manifest.citation_requirements.min_sources} sources")
        print(f"Domain Whitelist: {manifest.domain_whitelist.allowed_domains}")
        print(f"Guardrails: PII scrubbing = {manifest.guardrails.pii_scrubbing}")
        print(f"Fallback Strategy: {manifest.fallback_strategy.value}")
        
        # Test validare
        validation = manifest.validate()
        print(f"Validation: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
    
    test_mirror_manifest()
