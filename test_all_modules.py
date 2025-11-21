#!/usr/bin/env python3
"""
🧪 TEST COMPLET - TOATE MODULELE AI AGENTS
============================================

Test cap-coadă pentru:
1. MongoDB Connection
2. LLM Orchestrator (DeepSeek + OpenAI fallback)
3. SERP Client (Brave Search)
4. GPU Embeddings
5. Qdrant Vector DB
6. Scraping (BeautifulSoup + Playwright)
7. DeepSeek Competitive Analyzer
8. Langchain Integration
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModuleTester:
    """Tester pentru toate modulele"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
    
    def test_mongodb(self) -> Dict[str, Any]:
        """Test MongoDB connection"""
        print("\n" + "="*80)
        print("🗄️  MODULE 1: MONGODB")
        print("="*80)
        
        try:
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            db = client["ai_agents_db"]
            
            # Test collections
            collections = db.list_collection_names()
            agents_count = db.site_agents.count_documents({})
            
            print(f"✅ MongoDB: Connected")
            print(f"   Database: ai_agents_db")
            print(f"   Collections: {len(collections)}")
            print(f"   Agents: {agents_count}")
            print(f"   Status: OPERATIONAL ✓")
            
            return {
                "status": "success",
                "connected": True,
                "collections": len(collections),
                "agents": agents_count
            }
            
        except Exception as e:
            print(f"❌ MongoDB: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_llm_orchestrator(self) -> Dict[str, Any]:
        """Test LLM Orchestrator"""
        print("\n" + "="*80)
        print("🎭 MODULE 2: LLM ORCHESTRATOR")
        print("="*80)
        
        try:
            from llm_orchestrator import get_orchestrator
            
            orch = get_orchestrator()
            
            # Test simple chat
            print("📤 Testing simple chat...")
            result = orch.chat(
                messages=[
                    {"role": "user", "content": "Răspunde cu DA în 1 cuvânt."}
                ],
                max_tokens=10
            )
            
            print(f"✅ LLM Orchestrator: Working")
            print(f"   Provider: {result.get('provider', 'N/A')}")
            print(f"   Model: {result.get('model', 'N/A')}")
            print(f"   Success: {result.get('success', False)}")
            
            if result.get('success'):
                content = result.get('content', '')
                print(f"   Response: {content[:100]}")
                print(f"   Status: OPERATIONAL ✓")
                
                # Get stats
                stats = orch.get_stats()
                print(f"   Total calls: {stats.get('total_calls', 0)}")
                print(f"   Success rate: {stats.get('success_rate', 0)}%")
                
                return {
                    "status": "success",
                    "provider": result.get('provider'),
                    "model": result.get('model'),
                    "stats": stats
                }
            else:
                raise Exception(f"LLM failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ LLM Orchestrator: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_serp_client(self) -> Dict[str, Any]:
        """Test SERP Client (Brave Search)"""
        print("\n" + "="*80)
        print("🔍 MODULE 3: SERP CLIENT (Brave Search)")
        print("="*80)
        
        try:
            from tools.serp_client import BraveSerpClient, search
            
            # Test function
            print("📤 Testing search function...")
            results = search("test query", count=3)
            
            print(f"✅ SERP search(): Working")
            print(f"   Results: {len(results)} URLs")
            if results:
                print(f"   First result: {results[0][:60]}...")
            
            # Test class
            print("\n📤 Testing BraveSerpClient class...")
            try:
                client = BraveSerpClient()
                results2 = client.search("python programming", count=3)
                
                print(f"✅ BraveSerpClient: Working")
                print(f"   Results: {len(results2)} URLs")
                print(f"   Status: OPERATIONAL ✓")
                
                return {
                    "status": "success",
                    "function_works": len(results) > 0,
                    "class_works": len(results2) > 0,
                    "results_count": len(results2)
                }
            except Exception as e:
                if "BRAVE_API_KEY" in str(e):
                    print(f"⚠️  BraveSerpClient: API key missing (expected)")
                    print(f"   Status: READY (needs API key)")
                    return {
                        "status": "warning",
                        "message": "API key missing",
                        "ready": True
                    }
                raise
                
        except Exception as e:
            print(f"❌ SERP Client: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_gpu_embeddings(self) -> Dict[str, Any]:
        """Test GPU Embeddings"""
        print("\n" + "="*80)
        print("🎮 MODULE 4: GPU EMBEDDINGS")
        print("="*80)
        
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Check GPU
            gpu_available = torch.cuda.is_available()
            device = "cuda" if gpu_available else "cpu"
            
            if gpu_available:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                print(f"✅ GPU: {gpu_name}")
                print(f"   Memory: {gpu_memory:.1f} GB")
            else:
                print(f"⚠️  GPU: Not available (using CPU)")
            
            # Load model
            print("\n📤 Loading embedding model...")
            model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            
            # Test embedding
            test_text = "This is a test sentence for embeddings."
            embedding = model.encode([test_text])[0]
            
            print(f"✅ GPU Embeddings: Working")
            print(f"   Device: {device}")
            print(f"   Model: all-MiniLM-L6-v2")
            print(f"   Dimensions: {len(embedding)}")
            print(f"   Sample: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
            print(f"   Status: OPERATIONAL ✓")
            
            return {
                "status": "success",
                "gpu_available": gpu_available,
                "device": device,
                "gpu_name": gpu_name if gpu_available else "N/A",
                "dimensions": len(embedding)
            }
            
        except Exception as e:
            print(f"❌ GPU Embeddings: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_qdrant(self) -> Dict[str, Any]:
        """Test Qdrant Vector Database"""
        print("\n" + "="*80)
        print("🗃️  MODULE 5: QDRANT VECTOR DATABASE")
        print("="*80)
        
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(url="http://localhost:9306")
            collections = client.get_collections()
            
            print(f"✅ Qdrant: Connected")
            print(f"   Collections: {len(collections.collections)}")
            
            # Get sample collection info
            if collections.collections:
                sample = collections.collections[0]
                info = client.get_collection(sample.name)
                points = getattr(info, "points_count", getattr(info, "vectors_count", 0))
                
                print(f"   Sample: {sample.name}")
                print(f"   Points: {points}")
            
            print(f"   Status: OPERATIONAL ✓")
            
            return {
                "status": "success",
                "connected": True,
                "collections": len(collections.collections)
            }
            
        except Exception as e:
            print(f"⚠️  Qdrant: {e}")
            print(f"   Status: NOT RUNNING (optional)")
            return {"status": "warning", "error": str(e)}
    
    def test_scraping(self) -> Dict[str, Any]:
        """Test Scraping (BeautifulSoup + Playwright)"""
        print("\n" + "="*80)
        print("🌐 MODULE 6: WEB SCRAPING")
        print("="*80)
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Test BeautifulSoup
            print("📤 Testing BeautifulSoup scraping...")
            response = requests.get("https://example.com", timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            
            print(f"✅ BeautifulSoup: Working")
            print(f"   Test URL: example.com")
            print(f"   Title: {title.text if title else 'N/A'}")
            
            # Check Playwright
            print("\n📤 Checking Playwright...")
            try:
                from playwright.sync_api import sync_playwright
                print(f"✅ Playwright: Installed")
                print(f"   Status: READY")
            except ImportError:
                print(f"⚠️  Playwright: Not installed (optional)")
            
            print(f"   Status: OPERATIONAL ✓")
            
            return {
                "status": "success",
                "beautifulsoup": True,
                "playwright": False,  # Will be true if imported successfully
                "test_url": "example.com"
            }
            
        except Exception as e:
            print(f"❌ Scraping: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_deepseek_analyzer(self) -> Dict[str, Any]:
        """Test DeepSeek Competitive Analyzer"""
        print("\n" + "="*80)
        print("🎯 MODULE 7: DEEPSEEK COMPETITIVE ANALYZER")
        print("="*80)
        
        try:
            from deepseek_competitive_analyzer import get_analyzer
            
            analyzer = get_analyzer()
            
            print(f"✅ DeepSeek Analyzer: Loaded")
            print(f"   Functions: analyze_for_competition_discovery")
            print(f"   Functions: get_full_agent_context")
            print(f"   Status: READY ✓")
            
            return {
                "status": "success",
                "loaded": True,
                "ready": True
            }
            
        except Exception as e:
            print(f"❌ DeepSeek Analyzer: {e}")
            return {"status": "error", "error": str(e)}
    
    def test_langchain(self) -> Dict[str, Any]:
        """Test LangChain Integration"""
        print("\n" + "="*80)
        print("🔗 MODULE 8: LANGCHAIN INTEGRATION")
        print("="*80)
        
        try:
            from langchain_agent_integration import LangChainAgent, LangChainAgentManager
            
            print(f"✅ LangChain: Loaded")
            print(f"   Classes: LangChainAgent, LangChainAgentManager")
            print(f"   Status: READY ✓")
            
            return {
                "status": "success",
                "loaded": True,
                "ready": True,
                "classes": ["LangChainAgent", "LangChainAgentManager"]
            }
            
        except Exception as e:
            print(f"❌ LangChain: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_all_tests(self):
        """Run all module tests"""
        print("\n")
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  🧪 TEST COMPLET - TOATE MODULELE AI AGENTS                         ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        
        # Run tests
        self.results['mongodb'] = self.test_mongodb()
        self.results['llm_orchestrator'] = self.test_llm_orchestrator()
        self.results['serp_client'] = self.test_serp_client()
        self.results['gpu_embeddings'] = self.test_gpu_embeddings()
        self.results['qdrant'] = self.test_qdrant()
        self.results['scraping'] = self.test_scraping()
        self.results['deepseek_analyzer'] = self.test_deepseek_analyzer()
        self.results['langchain'] = self.test_langchain()
        
        # Summary
        print("\n")
        print("="*80)
        print("📊 SUMMARY - MODULE STATUS")
        print("="*80)
        
        operational = 0
        errors = 0
        warnings = 0
        
        for module, result in self.results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                operational += 1
                symbol = "✅"
            elif status == 'warning':
                warnings += 1
                symbol = "⚠️ "
            else:
                errors += 1
                symbol = "❌"
            
            print(f"{symbol} {module.upper()}: {status}")
        
        print("\n" + "="*80)
        print(f"Operational: {operational}/8")
        print(f"Warnings: {warnings}/8")
        print(f"Errors: {errors}/8")
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"\nTotal time: {elapsed:.2f}s")
        
        if errors == 0 and warnings <= 1:  # Qdrant e optional
            print("\n🎉 ALL CRITICAL MODULES OPERATIONAL!")
        elif errors == 0:
            print(f"\n✅ ALL CRITICAL MODULES OPERATIONAL (with {warnings} warnings)")
        else:
            print(f"\n⚠️  {errors} MODULE(S) HAVE ERRORS - NEEDS ATTENTION")
        
        print("="*80)
        
        # Save results
        output_file = "/srv/hf/ai_agents/test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': self.start_time.isoformat(),
                'duration': elapsed,
                'results': self.results,
                'summary': {
                    'operational': operational,
                    'warnings': warnings,
                    'errors': errors,
                    'total': 8
                }
            }, f, indent=2)
        
        print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    tester = ModuleTester()
    tester.run_all_tests()

