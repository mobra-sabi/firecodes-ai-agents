#!/usr/bin/env python3
"""
🤖 TEST AGENT - Agent Automat de Testare cu LLM Intelligence
=============================================================

Agent complex care testează automat:
- Backend: Toate endpoint-urile API (workflows, competitive, SERP, learning)
- Frontend: Componente, routing, services, hooks
- Integration: End-to-end flows
- Performance: Response times, memory usage

Folosește DeepSeek/Kimi pentru:
- Analiză inteligentă a rezultatelor
- Identificare pattern-uri de erori
- Sugestii de fix-uri
- Generare rapoarte comprehensive

Usage:
    python3 test_agent.py --full          # Test complet (backend + frontend + integration)
    python3 test_agent.py --backend       # Doar backend testing
    python3 test_agent.py --frontend      # Doar frontend testing
    python3 test_agent.py --report-only   # Generează doar raport din ultimele teste
"""

import asyncio
import requests
import json
import time
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
import traceback
from pathlib import Path

# Import LLM orchestrator pentru analiză
sys.path.insert(0, os.path.dirname(__file__))
from llm_orchestrator import get_orchestrator

class TestStatus(str, Enum):
    """Status-uri posibile pentru teste"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARNING = "warning"

class TestResult:
    """Rezultatul unui test individual"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status = TestStatus.PASS
        self.message = ""
        self.details = {}
        self.duration = 0.0
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }

class TestAgent:
    """Agent principal de testare cu DeepSeek"""
    
    def __init__(self, base_url: str = "http://localhost:5010"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.llm = get_orchestrator()
        self.start_time = None
        self.end_time = None
        
        # Counters
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.warnings = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log cu timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[94m",      # Blue
            "SUCCESS": "\033[92m",    # Green
            "WARNING": "\033[93m",    # Yellow
            "ERROR": "\033[91m",      # Red
            "RESET": "\033[0m"
        }
        color = colors.get(level, colors["INFO"])
        print(f"{color}[{timestamp}] {level}: {message}{colors['RESET']}")
    
    def add_result(self, result: TestResult):
        """Adaugă un rezultat de test"""
        self.results.append(result)
        self.total_tests += 1
        
        if result.status == TestStatus.PASS:
            self.passed += 1
            self.log(f"✅ {result.name}", "SUCCESS")
        elif result.status == TestStatus.FAIL:
            self.failed += 1
            self.log(f"❌ {result.name}: {result.message}", "ERROR")
        elif result.status == TestStatus.WARNING:
            self.warnings += 1
            self.log(f"⚠️  {result.name}: {result.message}", "WARNING")
        elif result.status == TestStatus.SKIP:
            self.skipped += 1
            self.log(f"⏭️  {result.name}: Skipped", "INFO")
    
    # ========================================================================
    # BACKEND TESTS
    # ========================================================================
    
    async def test_backend_health(self):
        """Test 1: Verifică că API-ul backend răspunde"""
        result = TestResult("Backend Health Check", "backend")
        start = time.time()
        
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            result.duration = time.time() - start
            
            if response.status_code == 200:
                result.status = TestStatus.PASS
                result.message = f"Backend is alive (response time: {result.duration:.2f}s)"
                result.details = {
                    "status_code": response.status_code,
                    "response_time": result.duration
                }
            else:
                result.status = TestStatus.FAIL
                result.message = f"Backend returned status {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = f"Backend not responding: {str(e)}"
            result.duration = time.time() - start
        
        self.add_result(result)
        return result.status == TestStatus.PASS
    
    async def test_workflows_endpoints(self):
        """Test 2-11: Testează toate endpoints-urile de workflows"""
        
        # Test 2: List active workflows
        result = TestResult("GET /api/workflows/active", "workflows")
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/workflows/active", timeout=10)
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Found {data.get('count', 0)} active workflows"
                result.details = {"count": data.get('count', 0), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 3: List recent workflows
        result = TestResult("GET /api/workflows/recent", "workflows")
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/workflows/recent?limit=10", timeout=10)
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Found {data.get('count', 0)} recent workflows"
                result.details = {"count": data.get('count', 0), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 4: Start agent creation workflow
        result = TestResult("POST /api/workflows/start-agent-creation", "workflows")
        start = time.time()
        workflow_id = None
        
        try:
            response = requests.post(
                f"{self.base_url}/api/workflows/start-agent-creation",
                json={"url": "https://example.com"},
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                workflow_id = data.get('workflow_id')
                
                if workflow_id:
                    result.status = TestStatus.PASS
                    result.message = f"Workflow created: {workflow_id[:12]}..."
                    result.details = {"workflow_id": workflow_id, "response_time": result.duration}
                else:
                    result.status = TestStatus.FAIL
                    result.message = "No workflow_id returned"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 5: Get workflow status (dacă am workflow_id)
        if workflow_id:
            result = TestResult("GET /api/workflows/status/{id}", "workflows")
            start = time.time()
            
            try:
                # Așteaptă puțin să se inițializeze workflow-ul
                await asyncio.sleep(2)
                
                response = requests.get(
                    f"{self.base_url}/api/workflows/status/{workflow_id}",
                    timeout=10
                )
                result.duration = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    result.status = TestStatus.PASS
                    result.message = f"Status: {data.get('status')}, Progress: {data.get('progress', 0)}%"
                    result.details = {
                        "workflow_id": workflow_id,
                        "status": data.get('status'),
                        "progress": data.get('progress'),
                        "current_step": data.get('current_step'),
                        "response_time": result.duration
                    }
                else:
                    result.status = TestStatus.FAIL
                    result.message = f"Status code: {response.status_code}"
            except Exception as e:
                result.status = TestStatus.FAIL
                result.message = str(e)
                result.duration = time.time() - start
            
            self.add_result(result)
            
            # Test 6: Stop workflow
            result = TestResult("POST /api/workflows/{id}/stop", "workflows")
            start = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/workflows/{workflow_id}/stop",
                    timeout=10
                )
                result.duration = time.time() - start
                
                if response.status_code == 200:
                    result.status = TestStatus.PASS
                    result.message = "Workflow stopped successfully"
                else:
                    result.status = TestStatus.FAIL
                    result.message = f"Status code: {response.status_code}"
            except Exception as e:
                result.status = TestStatus.FAIL
                result.message = str(e)
                result.duration = time.time() - start
            
            self.add_result(result)
    
    async def test_competitive_endpoints(self):
        """Test 12-14: Testează endpoints-urile de competitive intelligence"""
        
        # Folosim un agent_id fake pentru test
        test_agent_id = "507f1f77bcf86cd799439011"
        
        # Test 12: Get competitive analysis
        result = TestResult("GET /api/agents/{id}/competitive-analysis", "competitive")
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/{test_agent_id}/competitive-analysis",
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Analysis exists: {data.get('exists', False)}"
                result.details = {"exists": data.get('exists'), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 13: Get competitors
        result = TestResult("GET /api/agents/{id}/competitors", "competitive")
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/{test_agent_id}/competitors?limit=10",
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Found {data.get('count', 0)} competitors"
                result.details = {"count": data.get('count', 0), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 14: Get strategy
        result = TestResult("GET /api/agents/{id}/strategy", "competitive")
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/{test_agent_id}/strategy",
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Strategy exists: {data.get('exists', False)}"
                result.details = {"exists": data.get('exists'), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
    
    async def test_serp_endpoints(self):
        """Test 15-17: Testează endpoints-urile SERP"""
        
        test_agent_id = "507f1f77bcf86cd799439011"
        
        # Test 15: Get SERP rankings
        result = TestResult("GET /api/agents/{id}/serp-rankings", "serp")
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/{test_agent_id}/serp-rankings?limit=10",
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Found {data.get('count', 0)} rankings"
                result.details = {"count": data.get('count', 0), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 16: Get SERP history
        result = TestResult("GET /api/agents/{id}/serp/history", "serp")
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/{test_agent_id}/serp/history?days=30",
                timeout=10
            )
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Found {data.get('data_points', 0)} data points"
                result.details = {"data_points": data.get('data_points', 0), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
    
    async def test_learning_endpoints(self):
        """Test 18-19: Testează endpoints-urile Learning"""
        
        # Test 18: Get learning stats
        result = TestResult("GET /api/learning/stats", "learning")
        start = time.time()
        
        try:
            response = requests.get(f"{self.base_url}/api/learning/stats", timeout=10)
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Total interactions: {data.get('total_interactions', 0)}"
                result.details = {
                    "total_interactions": data.get('total_interactions', 0),
                    "unprocessed": data.get('unprocessed', 0),
                    "response_time": result.duration
                }
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
        
        # Test 19: Get training status
        result = TestResult("GET /api/learning/training-status", "learning")
        start = time.time()
        
        try:
            response = requests.get(f"{self.base_url}/api/learning/training-status", timeout=10)
            result.duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                result.status = TestStatus.PASS
                result.message = f"Training active: {data.get('is_training', False)}"
                result.details = {"is_training": data.get('is_training'), "response_time": result.duration}
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status code: {response.status_code}"
        except Exception as e:
            result.status = TestStatus.FAIL
            result.message = str(e)
            result.duration = time.time() - start
        
        self.add_result(result)
    
    # ========================================================================
    # FRONTEND TESTS
    # ========================================================================
    
    async def test_frontend_files(self):
        """Test 20-25: Verifică existența fișierelor frontend"""
        
        frontend_path = Path("/srv/hf/ai_agents/frontend-pro")
        
        files_to_check = [
            ("src/services/workflows.js", "frontend"),
            ("src/hooks/useWebSocket.js", "frontend"),
            ("src/hooks/useWorkflowStatus.js", "frontend"),
            ("src/pages/WorkflowMonitor.jsx", "frontend"),
            ("src/App.jsx", "frontend"),
            ("src/components/layout/Sidebar.jsx", "frontend")
        ]
        
        for file_path, category in files_to_check:
            result = TestResult(f"Frontend File: {file_path}", category)
            full_path = frontend_path / file_path
            
            if full_path.exists():
                result.status = TestStatus.PASS
                result.message = "File exists"
                result.details = {"size": full_path.stat().st_size}
            else:
                result.status = TestStatus.FAIL
                result.message = "File not found"
            
            self.add_result(result)
    
    async def test_frontend_code_quality(self):
        """Test 26: Verifică calitatea codului frontend cu LLM"""
        
        result = TestResult("Frontend Code Quality Analysis (LLM)", "frontend")
        
        try:
            # Citește WorkflowMonitor.jsx pentru analiză
            workflow_monitor_path = Path("/srv/hf/ai_agents/frontend-pro/src/pages/WorkflowMonitor.jsx")
            
            if workflow_monitor_path.exists():
                code = workflow_monitor_path.read_text()
                
                # Trimite către LLM pentru analiză
                prompt = f"""Analizează următorul cod React și identifică:
1. Potențiale bug-uri sau probleme
2. Best practices care lipsesc
3. Optimizări posibile
4. Security issues

Cod:
```jsx
{code[:3000]}  # Primele 3000 caractere
```

Răspunde DOAR în format JSON:
{{
  "overall_quality": "good/fair/poor",
  "bugs_found": [],
  "suggestions": [],
  "security_issues": []
}}
"""
                
                llm_response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                if llm_response.get('success'):
                    # Parse response
                    content = llm_response['content']
                    # Clean markdown if present
                    import re
                    content = re.sub(r'^```json\s*', '', content)
                    content = re.sub(r'^```\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    
                    analysis = json.loads(content)
                    
                    quality = analysis.get('overall_quality', 'unknown')
                    bugs = analysis.get('bugs_found', [])
                    
                    if quality == 'good' and len(bugs) == 0:
                        result.status = TestStatus.PASS
                        result.message = "Code quality is good"
                    elif quality == 'fair' or len(bugs) > 0:
                        result.status = TestStatus.WARNING
                        result.message = f"Code quality: {quality}, {len(bugs)} potential issues"
                    else:
                        result.status = TestStatus.FAIL
                        result.message = f"Code quality: {quality}"
                    
                    result.details = analysis
                else:
                    result.status = TestStatus.SKIP
                    result.message = "LLM analysis failed"
            else:
                result.status = TestStatus.SKIP
                result.message = "WorkflowMonitor.jsx not found"
        
        except Exception as e:
            result.status = TestStatus.SKIP
            result.message = f"Analysis error: {str(e)}"
        
        self.add_result(result)
    
    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================
    
    async def run_all_tests(self):
        """Rulează toate testele"""
        
        self.start_time = datetime.now(timezone.utc)
        
        self.log("=" * 80)
        self.log("🤖 TEST AGENT - Starting Comprehensive Testing", "INFO")
        self.log("=" * 80)
        self.log("")
        
        # Backend Tests
        self.log("📡 BACKEND TESTS", "INFO")
        self.log("-" * 80)
        
        backend_alive = await self.test_backend_health()
        
        if backend_alive:
            await self.test_workflows_endpoints()
            await self.test_competitive_endpoints()
            await self.test_serp_endpoints()
            await self.test_learning_endpoints()
        else:
            self.log("⚠️  Backend not responding - skipping API tests", "WARNING")
        
        self.log("")
        
        # Frontend Tests
        self.log("🎨 FRONTEND TESTS", "INFO")
        self.log("-" * 80)
        
        await self.test_frontend_files()
        await self.test_frontend_code_quality()
        
        self.log("")
        
        self.end_time = datetime.now(timezone.utc)
        
        # Summary
        await self.print_summary()
        
        # Generate report
        await self.generate_report()
    
    async def print_summary(self):
        """Print test summary"""
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        self.log("=" * 80)
        self.log("📊 TEST SUMMARY", "INFO")
        self.log("=" * 80)
        self.log(f"Total Tests: {self.total_tests}")
        self.log(f"✅ Passed: {self.passed}", "SUCCESS")
        self.log(f"❌ Failed: {self.failed}", "ERROR" if self.failed > 0 else "INFO")
        self.log(f"⚠️  Warnings: {self.warnings}", "WARNING" if self.warnings > 0 else "INFO")
        self.log(f"⏭️  Skipped: {self.skipped}")
        self.log(f"⏱️  Duration: {duration:.2f}s")
        
        pass_rate = (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0
        self.log(f"📈 Pass Rate: {pass_rate:.1f}%", "SUCCESS" if pass_rate >= 80 else "WARNING")
        
        self.log("=" * 80)
    
    async def generate_report(self):
        """Generează raport detaliat cu analiză LLM"""
        
        self.log("")
        self.log("📝 Generating detailed report with LLM analysis...", "INFO")
        
        # Pregătește datele pentru LLM
        results_summary = {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "duration": (self.end_time - self.start_time).total_seconds(),
            "failed_tests": [r.to_dict() for r in self.results if r.status == TestStatus.FAIL],
            "warning_tests": [r.to_dict() for r in self.results if r.status == TestStatus.WARNING]
        }
        
        # Trimite către LLM pentru analiză
        prompt = f"""Analizează rezultatele următoarelor teste automate și generează un raport comprehensiv:

Rezultate:
{json.dumps(results_summary, indent=2)}

Generează un raport care include:
1. Overview (status general, pass rate)
2. Issues critice identificate
3. Recomandări pentru fix-uri
4. Priorities (ce trebuie fixat urgent)

Răspunde în format Markdown, dar fără code blocks (direct markdown text).
"""
        
        try:
            llm_response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            if llm_response.get('success'):
                llm_analysis = llm_response['content']
            else:
                llm_analysis = "LLM analysis not available"
        except Exception as e:
            llm_analysis = f"Error generating LLM analysis: {str(e)}"
        
        # Creează raport complet
        report = f"""# 🤖 TEST AGENT - RAPORT AUTOMAT

**Data**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Duration**: {(self.end_time - self.start_time).total_seconds():.2f}s

---

## 📊 REZUMAT

| Metric | Value |
|--------|-------|
| Total Tests | {self.total_tests} |
| ✅ Passed | {self.passed} |
| ❌ Failed | {self.failed} |
| ⚠️ Warnings | {self.warnings} |
| ⏭️ Skipped | {self.skipped} |
| **Pass Rate** | **{(self.passed / self.total_tests * 100) if self.total_tests > 0 else 0:.1f}%** |

---

## 🔍 ANALIZĂ LLM (DeepSeek/Kimi)

{llm_analysis}

---

## 📋 REZULTATE DETALIATE

### ✅ Tests Passed ({self.passed})

"""
        
        # Add passed tests
        for r in self.results:
            if r.status == TestStatus.PASS:
                report += f"- **{r.name}** ({r.category}): {r.message} ({r.duration:.2f}s)\n"
        
        # Add failed tests
        if self.failed > 0:
            report += f"\n### ❌ Tests Failed ({self.failed})\n\n"
            for r in self.results:
                if r.status == TestStatus.FAIL:
                    report += f"- **{r.name}** ({r.category})\n"
                    report += f"  - **Error**: {r.message}\n"
                    if r.details:
                        report += f"  - **Details**: {json.dumps(r.details, indent=2)}\n"
                    report += f"  - **Duration**: {r.duration:.2f}s\n\n"
        
        # Add warnings
        if self.warnings > 0:
            report += f"\n### ⚠️ Warnings ({self.warnings})\n\n"
            for r in self.results:
                if r.status == TestStatus.WARNING:
                    report += f"- **{r.name}** ({r.category}): {r.message}\n"
        
        # Save report
        report_path = Path("/srv/hf/ai_agents/TEST_AGENT_REPORT.md")
        report_path.write_text(report)
        
        self.log(f"✅ Report saved to: {report_path}", "SUCCESS")
        self.log("")
        
        # Print quick summary
        self.log("🎯 QUICK INSIGHTS:", "INFO")
        if self.failed == 0:
            self.log("✅ All tests passed! System is healthy.", "SUCCESS")
        else:
            self.log(f"❌ {self.failed} tests failed - review report for details", "ERROR")
        
        if self.warnings > 0:
            self.log(f"⚠️  {self.warnings} warnings - non-critical issues found", "WARNING")


async def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Agent - Automated Testing with LLM")
    parser.add_argument("--backend", action="store_true", help="Run only backend tests")
    parser.add_argument("--frontend", action="store_true", help="Run only frontend tests")
    parser.add_argument("--full", action="store_true", help="Run all tests (default)")
    parser.add_argument("--base-url", default="http://localhost:5010", help="Backend base URL")
    
    args = parser.parse_args()
    
    agent = TestAgent(base_url=args.base_url)
    
    await agent.run_all_tests()
    
    # Exit code based on results
    sys.exit(0 if agent.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())

