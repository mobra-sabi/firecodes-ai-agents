#!/usr/bin/env python3
"""
Agent Health Checker - Verifică statusul unui agent specific
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
import requests
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

class AgentHealthChecker:
    """Verifică statusul unui agent specific"""
    
    def __init__(self):
        self.qdrant_url = "http://localhost:9306"
        self.qwen_url = "http://localhost:11434"
        self.mongodb_uri = "mongodb://localhost:27017"
        
    async def check_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Verifică statusul complet al unui agent"""
        try:
            # Conectare la MongoDB
            mongo_client = MongoClient(self.mongodb_uri)
            db = mongo_client.ai_agents
            
            # Verifică dacă agentul există
            agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {
                    "agent_id": agent_id,
                    "status": "error",
                    "message": "Agent not found",
                    "checks": {}
                }
            
            # Verificări paralele
            checks = await asyncio.gather(
                self._check_agent_data(agent_id, db),
                self._check_qdrant_collections(agent_id),
                self._check_qwen_connection(),
                self._check_site_data(agent_id, db),
                return_exceptions=True
            )
            
            # Procesează rezultatele
            agent_data_check, qdrant_check, qwen_check, site_data_check = checks
            
            # Calculează statusul general
            all_checks = {
                "agent_data": agent_data_check if not isinstance(agent_data_check, Exception) else {"status": "error", "message": str(agent_data_check)},
                "qdrant_collections": qdrant_check if not isinstance(qdrant_check, Exception) else {"status": "error", "message": str(qdrant_check)},
                "qwen_connection": qwen_check if not isinstance(qwen_check, Exception) else {"status": "error", "message": str(qwen_check)},
                "site_data": site_data_check if not isinstance(site_data_check, Exception) else {"status": "error", "message": str(site_data_check)}
            }
            
            # Status general
            error_count = sum(1 for check in all_checks.values() if check.get("status") == "error")
            warning_count = sum(1 for check in all_checks.values() if check.get("status") == "warning")
            
            if error_count == 0 and warning_count == 0:
                overall_status = "healthy"
            elif error_count == 0:
                overall_status = "warning"
            else:
                overall_status = "error"
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.get("name", "Unknown"),
                "domain": agent.get("domain", "Unknown"),
                "status": overall_status,
                "checks": all_checks,
                "summary": {
                    "total_checks": len(all_checks),
                    "healthy": len([c for c in all_checks.values() if c.get("status") == "healthy"]),
                    "warnings": warning_count,
                    "errors": error_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            return {
                "agent_id": agent_id,
                "status": "error",
                "message": str(e),
                "checks": {}
            }
    
    async def _check_agent_data(self, agent_id: str, db) -> Dict[str, Any]:
        """Verifică datele agentului în MongoDB"""
        try:
            agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"status": "error", "message": "Agent not found in database"}
            
            # Verifică câmpurile esențiale
            required_fields = ["name", "domain"]
            missing_fields = [field for field in required_fields if not agent.get(field)]
            
            if missing_fields:
                return {
                    "status": "warning",
                    "message": f"Missing fields: {', '.join(missing_fields)}",
                    "data": {
                        "name": agent.get("name"),
                        "domain": agent.get("domain"),
                        "created_at": agent.get("created_at")
                    }
                }
            
            return {
                "status": "healthy",
                "message": "Agent data is complete",
                "data": {
                    "name": agent.get("name"),
                    "domain": agent.get("domain"),
                    "created_at": agent.get("created_at")
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _check_qdrant_collections(self, agent_id: str) -> Dict[str, Any]:
        """Verifică colecțiile Qdrant pentru agent"""
        try:
            collections_to_check = [
                f"agent_{agent_id}_pages",
                f"agent_{agent_id}_faq",
                f"agent_{agent_id}_content"
            ]
            
            existing_collections = []
            missing_collections = []
            
            for collection_name in collections_to_check:
                try:
                    response = requests.get(f"{self.qdrant_url}/collections/{collection_name}", timeout=5)
                    if response.status_code == 200:
                        existing_collections.append(collection_name)
                        
                        # Verifică numărul de puncte
                        points_response = requests.post(
                            f"{self.qdrant_url}/collections/{collection_name}/points/count",
                            json={},
                            timeout=5
                        )
                        if points_response.status_code == 200:
                            points_count = points_response.json().get("result", {}).get("count", 0)
                        else:
                            points_count = "unknown"
                    else:
                        missing_collections.append(collection_name)
                except Exception as e:
                    missing_collections.append(collection_name)
            
            if missing_collections:
                return {
                    "status": "warning" if existing_collections else "error",
                    "message": f"Missing collections: {', '.join(missing_collections)}",
                    "data": {
                        "existing": existing_collections,
                        "missing": missing_collections
                    }
                }
            
            return {
                "status": "healthy",
                "message": "All Qdrant collections exist",
                "data": {
                    "collections": existing_collections
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _check_qwen_connection(self) -> Dict[str, Any]:
        """Verifică conexiunea la Qwen"""
        try:
            response = requests.get(f"{self.qwen_url}/v1/models", timeout=10)
            if response.status_code == 200:
                models = response.json().get("data", [])
                qwen_models = [m for m in models if "qwen" in m.get("id", "").lower()]
                
                if qwen_models:
                    return {
                        "status": "healthy",
                        "message": "Qwen connection successful",
                        "data": {
                            "available_models": [m["id"] for m in qwen_models]
                        }
                    }
                else:
                    return {
                        "status": "warning",
                        "message": "Qwen connected but no Qwen models found",
                        "data": {
                            "available_models": [m["id"] for m in models]
                        }
                    }
            else:
                return {"status": "error", "message": f"Qwen connection failed: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _check_site_data(self, agent_id: str, db) -> Dict[str, Any]:
        """Verifică datele site-ului în baza de date"""
        try:
            agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"status": "error", "message": "Agent not found"}
            
            domain = agent.get("domain")
            if not domain:
                return {"status": "error", "message": "No domain specified"}
            
            site_data = db.site_data.find_one({"domain": domain})
            if not site_data:
                return {
                    "status": "warning",
                    "message": "No site data found - will be auto-extracted",
                    "data": {"domain": domain}
                }
            
            # Verifică câmpurile esențiale (adaptate la structura reală)
            essential_fields = ["contact_info"]
            optional_fields = ["services_products", "services_offered"]
            
            # Verifică business_type separat (poate fi "general" sau specific)
            business_type = site_data.get("business_type", "unknown")
            
            missing_essential = [field for field in essential_fields if not site_data.get(field)]
            missing_optional = [field for field in optional_fields if not site_data.get(field)]
            
            # Verifică dacă există servicii în oricare din câmpuri
            has_services = any([
                site_data.get("services_products"),
                site_data.get("services_offered"),
                site_data.get("technical_specifications")
            ])
            
            if missing_essential:
                return {
                    "status": "error",
                    "message": f"Site data missing essential fields: {', '.join(missing_essential)}",
                    "data": {
                        "domain": domain,
                        "has_contact": bool(site_data.get("contact_info")),
                        "has_services": has_services,
                        "business_type": site_data.get("business_type", "unknown")
                    }
                }
            
            if missing_optional and not has_services:
                return {
                    "status": "warning",
                    "message": f"Site data incomplete: missing optional fields {', '.join(missing_optional)}",
                    "data": {
                        "domain": domain,
                        "has_contact": bool(site_data.get("contact_info")),
                        "has_services": has_services,
                        "business_type": business_type,
                        "available_fields": list(site_data.keys())
                    }
                }
            
            return {
                "status": "healthy",
                "message": "Site data is complete",
                "data": {
                    "domain": domain,
                    "business_type": business_type,
                    "services_count": len(site_data.get("services_products", [])),
                    "has_contact": bool(site_data.get("contact_info")),
                    "is_general_system": business_type == "general"
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Funcție helper pentru a rula verificarea
async def check_agent_health(agent_id: str) -> Dict[str, Any]:
    """Verifică statusul unui agent"""
    checker = AgentHealthChecker()
    return await checker.check_agent_health(agent_id)

if __name__ == "__main__":
    import asyncio
    import json
    
    async def test_checker():
        agent_id = "68e629bb5a7057c4b1b2f4da"
        result = await check_agent_health(agent_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_checker())
