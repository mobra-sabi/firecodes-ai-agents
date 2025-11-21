#!/usr/bin/env python3
"""
🎯 GPU Optimizer - Sistem inteligent de distribuție agenți pe GPU-uri

Optimizează procesarea agenților pentru hardware disponibil:
- 11x RTX 3080 Ti (12 GB VRAM fiecare)
- Distribuție inteligentă a sarcinii
- Load balancing automat
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPUOptimizer:
    """
    Optimizează procesarea agenților pe GPU-uri disponibile
    """
    
    def __init__(self, gpu_count: int = 11, gpu_memory_gb: int = 12):
        """
        Args:
            gpu_count: Numărul de GPU-uri disponibile
            gpu_memory_gb: Memoria VRAM per GPU (GB)
        """
        self.gpu_count = gpu_count
        self.gpu_memory_gb = gpu_memory_gb
        self.total_vram = gpu_count * gpu_memory_gb
        
        # Estimări de consum per agent
        self.ram_per_agent = 2.5  # GB RAM pentru scraping + chunking
        self.vram_per_agent_embedding = 1.5  # GB VRAM pentru embeddings
        
        # Calcul capacitate
        self.agents_per_gpu_conservative = 2  # Conservator
        self.agents_per_gpu_optimal = 3  # Optim
        self.agents_per_gpu_aggressive = 4  # Agresiv
        
        logger.info(f"✅ GPU Optimizer initialized:")
        logger.info(f"   GPU-uri: {gpu_count}x RTX 3080 Ti ({gpu_memory_gb} GB fiecare)")
        logger.info(f"   VRAM total: {self.total_vram} GB")
        logger.info(f"   Capacitate conservatoare: {gpu_count * self.agents_per_gpu_conservative} agenți paralel")
        logger.info(f"   Capacitate optimă: {gpu_count * self.agents_per_gpu_optimal} agenți paralel")
        logger.info(f"   Capacitate agresivă: {gpu_count * self.agents_per_gpu_aggressive} agenți paralel")
    
    def get_optimal_parallel_count(self, mode: str = "optimal") -> int:
        """
        Returnează numărul optim de agenți paralel
        
        Args:
            mode: "conservative", "optimal", sau "aggressive"
        
        Returns:
            Numărul de agenți paralel recomandați
        """
        if mode == "conservative":
            return self.gpu_count * self.agents_per_gpu_conservative
        elif mode == "aggressive":
            return self.gpu_count * self.agents_per_gpu_aggressive
        else:  # optimal
            return self.gpu_count * self.agents_per_gpu_optimal
    
    def calculate_processing_time(self, total_agents: int, parallel_count: int) -> Dict:
        """
        Calculează timpul estimat de procesare
        
        Args:
            total_agents: Numărul total de agenți de procesat
            parallel_count: Numărul de agenți paralel
        
        Returns:
            Dict cu estimări de timp
        """
        # Timp mediu per agent (minute)
        avg_time_per_agent = 8  # ~8 minute per agent (scraping + chunking + embeddings + keywords + SERP)
        
        batches = (total_agents + parallel_count - 1) // parallel_count  # Ceiling division
        total_time_minutes = batches * avg_time_per_agent
        
        return {
            "total_agents": total_agents,
            "parallel_count": parallel_count,
            "batches": batches,
            "time_per_batch_minutes": avg_time_per_agent,
            "total_time_minutes": total_time_minutes,
            "total_time_hours": round(total_time_minutes / 60, 2),
            "estimated_completion": datetime.now(timezone.utc).replace(
                microsecond=0
            ).isoformat()  # Placeholder, va fi actualizat
        }
    
    def get_recommendations(self) -> Dict:
        """
        Returnează recomandări pentru procesare
        
        Returns:
            Dict cu recomandări
        """
        conservative = self.get_optimal_parallel_count("conservative")
        optimal = self.get_optimal_parallel_count("optimal")
        aggressive = self.get_optimal_parallel_count("aggressive")
        
        return {
            "hardware": {
                "gpu_count": self.gpu_count,
                "gpu_model": "RTX 3080 Ti",
                "vram_per_gpu_gb": self.gpu_memory_gb,
                "total_vram_gb": self.total_vram
            },
            "recommendations": {
                "conservative": {
                    "parallel_agents": conservative,
                    "description": "Sigur și stabil, recomandat pentru procesare continuă",
                    "use_case": "Procesare pe termen lung, fără risc de suprasolicitare"
                },
                "optimal": {
                    "parallel_agents": optimal,
                    "description": "Echilibrat între performanță și stabilitate",
                    "use_case": "Procesare standard, recomandat pentru majoritatea cazurilor"
                },
                "aggressive": {
                    "parallel_agents": aggressive,
                    "description": "Performanță maximă, poate suprasolicita sistemul",
                    "use_case": "Procesare rapidă, pentru batch-uri mari cu monitorizare"
                }
            },
            "processing_phases": {
                "phase_1_scraping": {
                    "resource": "CPU + RAM",
                    "consumption_per_agent": f"{self.ram_per_agent} GB RAM",
                    "parallel_capacity": "Limită de CPU cores"
                },
                "phase_2_embeddings": {
                    "resource": "GPU VRAM",
                    "consumption_per_agent": f"{self.vram_per_agent_embedding} GB VRAM",
                    "parallel_capacity": f"~{self.gpu_memory_gb // self.vram_per_agent_embedding} agenți per GPU"
                },
                "phase_3_keywords_serp": {
                    "resource": "API calls (DeepSeek + Brave)",
                    "consumption_per_agent": "Rate limits API",
                    "parallel_capacity": "Limită de rate limits"
                }
            }
        }


# Singleton instance
_gpu_optimizer = None

def get_gpu_optimizer(gpu_count: int = 11, gpu_memory_gb: int = 12) -> GPUOptimizer:
    """Returnează instanța singleton a GPU Optimizer"""
    global _gpu_optimizer
    if _gpu_optimizer is None:
        _gpu_optimizer = GPUOptimizer(gpu_count, gpu_memory_gb)
    return _gpu_optimizer

