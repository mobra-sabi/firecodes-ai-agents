#!/usr/bin/env python3
"""
Health Checker - Verifică starea tuturor serviciilor
Implementează verificări pentru Qdrant, Qwen, OpenAI, Brave API
"""

import asyncio
import aiohttp
import requests
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Status de sănătate pentru un serviciu"""
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time: float
    error: Optional[str] = None
    details: Dict[str, Any] = None

class HealthChecker:
    """Verificător de sănătate pentru toate serviciile"""
    
    def __init__(self):
        self.services = {
            "qdrant": {
                "url": "http://localhost:9306/collections",
                "timeout": 5
            },
            "qwen": {
                "url": "http://localhost:11434/v1/models",
                "timeout": 10
            },
            "openai": {
                "url": "https://api.openai.com/v1/models",
                "timeout": 10,
                "headers": {
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
                }
            },
            "brave": {
                "url": "https://api.search.brave.com/res/v1/web/search",
                "timeout": 10,
                "params": {"q": "test", "count": 1},
                "headers": {
                    "X-Subscription-Token": os.getenv('BRAVE_API_KEY')
                }
            },
            "mongodb": {
                "url": "mongodb://localhost:27017",
                "timeout": 5
            }
        }
    
    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """Verifică toate serviciile în paralel"""
        tasks = []
        for service_name in self.services:
            tasks.append(self._check_service(service_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_status = {}
        for i, service_name in enumerate(self.services):
            result = results[i]
            if isinstance(result, Exception):
                health_status[service_name] = HealthStatus(
                    service=service_name,
                    status="unhealthy",
                    response_time=0.0,
                    error=str(result)
                )
            else:
                health_status[service_name] = result
        
        return health_status
    
    async def _check_service(self, service_name: str) -> HealthStatus:
        """Verifică un serviciu specific"""
        config = self.services[service_name]
        start_time = datetime.now()
        
        try:
            if service_name == "mongodb":
                return await self._check_mongodb(config)
            else:
                return await self._check_http_service(service_name, config)
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthStatus(
                service=service_name,
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    async def _check_http_service(self, service_name: str, config: Dict) -> HealthStatus:
        """Verifică un serviciu HTTP"""
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["url"],
                    headers=config.get("headers", {}),
                    params=config.get("params", {}),
                    timeout=aiohttp.ClientTimeout(total=config["timeout"])
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        return HealthStatus(
                            service=service_name,
                            status="healthy",
                            response_time=response_time,
                            details={"status_code": response.status}
                        )
                    else:
                        return HealthStatus(
                            service=service_name,
                            status="degraded",
                            response_time=response_time,
                            error=f"HTTP {response.status}",
                            details={"status_code": response.status}
                        )
                        
        except asyncio.TimeoutError:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthStatus(
                service=service_name,
                status="unhealthy",
                response_time=response_time,
                error="Timeout"
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthStatus(
                service=service_name,
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    async def _check_mongodb(self, config: Dict) -> HealthStatus:
        """Verifică MongoDB"""
        start_time = datetime.now()
        
        try:
            from pymongo import MongoClient
            client = MongoClient(config["url"], serverSelectionTimeoutMS=config["timeout"] * 1000)
            client.admin.command('ping')
            client.close()
            
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthStatus(
                service="mongodb",
                status="healthy",
                response_time=response_time,
                details={"connection": "successful"}
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthStatus(
                service="mongodb",
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    def get_health_summary(self, health_status: Dict[str, HealthStatus]) -> Dict[str, Any]:
        """Generează un rezumat al sănătății sistemului"""
        total_services = len(health_status)
        healthy_services = len([s for s in health_status.values() if s.status == "healthy"])
        degraded_services = len([s for s in health_status.values() if s.status == "degraded"])
        unhealthy_services = len([s for s in health_status.values() if s.status == "unhealthy"])
        
        overall_status = "healthy"
        if unhealthy_services > 0:
            overall_status = "unhealthy"
        elif degraded_services > 0:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unhealthy_services": unhealthy_services,
            "health_percentage": (healthy_services / total_services) * 100 if total_services > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                service: {
                    "status": status.status,
                    "response_time": status.response_time,
                    "error": status.error,
                    "details": status.details
                }
                for service, status in health_status.items()
            }
        }

# Funcție de utilitate pentru verificarea rapidă
async def quick_health_check() -> Dict[str, Any]:
    """Verificare rapidă a sănătății sistemului"""
    checker = HealthChecker()
    health_status = await checker.check_all_services()
    return checker.get_health_summary(health_status)

if __name__ == "__main__":
    async def main():
        checker = HealthChecker()
        health_status = await checker.check_all_services()
        summary = checker.get_health_summary(health_status)
        
        print("🔍 Health Check Results:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # Verifică dacă sistemul este sănătos
        if summary["overall_status"] == "healthy":
            print("✅ All services are healthy!")
        elif summary["overall_status"] == "degraded":
            print("⚠️ Some services are degraded")
        else:
            print("❌ Some services are unhealthy")
    
    asyncio.run(main())
