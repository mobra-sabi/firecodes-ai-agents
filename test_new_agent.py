#!/usr/bin/env python3
"""
Test Agent - Comprehensive Testing pentru un Agent NOU
Testează TOATE endpoint-urile cu agent-ul creat recent
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
API_BASE = "http://localhost:5010"
AGENT_ID = "691a19dd2772e8833c819084"  # Industrial Cruman agent

class AgentTester:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def log(self, message: str, level: str = 'info'):
        """Log cu culori"""
        colors = {
            'success': '\033[92m',
            'error': '\033[91m',
            'warning': '\033[93m',
            'info': '\033[94m',
            'reset': '\033[0m'
        }
        color = colors.get(level, colors['info'])
        print(f"{color}{message}{colors['reset']}")
        
    def test_endpoint(self, method: str, endpoint: str, name: str, 
                     data: Dict = None, expected_keys: List[str] = None) -> bool:
        """Test generic pentru un endpoint"""
        try:
            url = f"{API_BASE}{endpoint}"
            self.log(f"\n🔍 Testing: {name}", 'info')
            self.log(f"   {method} {endpoint}", 'info')
            
            start = time.time()
            
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            duration = time.time() - start
            
            if response.status_code == 200:
                result = response.json()
                
                # Verify expected keys
                if expected_keys:
                    missing = [k for k in expected_keys if k not in result]
                    if missing:
                        self.log(f"   ⚠️  Missing keys: {missing}", 'warning')
                        self.results['warnings'].append({
                            'name': name,
                            'issue': f"Missing keys: {missing}"
                        })
                
                self.log(f"   ✅ PASSED ({duration:.2f}s)", 'success')
                self.log(f"   Response preview: {json.dumps(result, indent=2)[:200]}...", 'info')
                
                self.results['passed'].append({
                    'name': name,
                    'endpoint': endpoint,
                    'duration': duration,
                    'response': result
                })
                return True
            else:
                self.log(f"   ❌ FAILED - Status {response.status_code}", 'error')
                self.log(f"   Response: {response.text[:200]}", 'error')
                
                self.results['failed'].append({
                    'name': name,
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'error': response.text[:200]
                })
                return False
                
        except Exception as e:
            self.log(f"   ❌ EXCEPTION: {str(e)}", 'error')
            self.results['failed'].append({
                'name': name,
                'endpoint': endpoint,
                'error': str(e)
            })
            return False
            
    def run_all_tests(self):
        """Rulează TOATE testele pentru agent"""
        self.log("\n" + "="*80, 'info')
        self.log("🤖 TEST AGENT - Testare Completă Agent NOU", 'info')
        self.log("="*80, 'info')
        self.log(f"\n📝 Agent ID: {self.agent_id}", 'info')
        self.log(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'info')
        
        # 1. BASIC AGENT ENDPOINTS
        self.log("\n\n" + "="*80, 'info')
        self.log("📋 SECTION 1: BASIC AGENT ENDPOINTS", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}',
            'Get Agent Details',
            expected_keys=['_id', 'domain', 'name', 'status']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/content',
            'Get Agent Content',
            expected_keys=['content']
        )
        
        # 2. COMPETITIVE INTELLIGENCE ENDPOINTS
        self.log("\n\n" + "="*80, 'info')
        self.log("🎯 SECTION 2: COMPETITIVE INTELLIGENCE", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/competitive-analysis',
            'Get Competitive Analysis',
            expected_keys=['exists', 'analysis']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/competitors',
            'Get Competitors List',
            expected_keys=['competitors', 'total']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/strategy',
            'Get Competitive Strategy',
            expected_keys=['exists', 'strategy']
        )
        
        # 3. SERP MONITORING ENDPOINTS
        self.log("\n\n" + "="*80, 'info')
        self.log("📈 SECTION 3: SERP MONITORING", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/serp-rankings',
            'Get SERP Rankings',
            expected_keys=['rankings']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/serp/history?keyword=mentenanta',
            'Get SERP History',
            expected_keys=['history', 'keyword']
        )
        
        # 4. WORKFLOW ENDPOINTS (pentru acest agent)
        self.log("\n\n" + "="*80, 'info')
        self.log("⚡ SECTION 4: WORKFLOW MANAGEMENT", 'info')
        self.log("="*80, 'info')
        
        # Start competitive analysis workflow
        self.test_endpoint(
            'POST',
            '/api/workflows/start-competitive-analysis',
            'Start Competitive Analysis Workflow',
            data={'agent_id': self.agent_id},
            expected_keys=['workflow_id', 'status']
        )
        
        # Get active workflows
        self.test_endpoint(
            'GET',
            '/api/workflows/active',
            'Get Active Workflows',
            expected_keys=['workflows']
        )
        
        # Start SERP discovery
        self.test_endpoint(
            'POST',
            '/api/workflows/start-serp-discovery',
            'Start SERP Discovery Workflow',
            data={'agent_id': self.agent_id, 'num_keywords': 5},
            expected_keys=['workflow_id', 'status']
        )
        
        # 5. LEARNING ENDPOINTS (general)
        self.log("\n\n" + "="*80, 'info')
        self.log("🧠 SECTION 5: LEARNING CENTER", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            '/api/learning/stats',
            'Get Learning Statistics',
            expected_keys=['total_interactions']
        )
        
        self.test_endpoint(
            'GET',
            '/api/learning/training-status',
            'Get Training Status',
            expected_keys=['is_training']
        )
        
        # 6. GOOGLE RANKINGS & SLAVES
        self.log("\n\n" + "="*80, 'info')
        self.log("🗺️ SECTION 6: GOOGLE RANKINGS & SLAVE AGENTS", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/google-rankings-map',
            'Get Google Rankings Map',
            expected_keys=['exists', 'rankings']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/google-ads-strategy',
            'Get Google Ads Strategy',
            expected_keys=['exists']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/slave-agents',
            'Get Slave Agents',
            expected_keys=['total_slaves', 'slaves']
        )
        
        self.test_endpoint(
            'GET',
            f'/api/agents/{self.agent_id}/rankings-summary',
            'Get Rankings Summary',
            expected_keys=['has_data', 'total_keywords']
        )
        
        self.test_endpoint(
            'POST',
            '/api/workflows/start-serp-discovery-with-slaves',
            'Start SERP Discovery with Slaves',
            data={'agent_id': self.agent_id, 'num_keywords': 3},
            expected_keys=['workflow_id', 'status']
        )
        
        # 7. SYSTEM HEALTH
        self.log("\n\n" + "="*80, 'info')
        self.log("🏥 SECTION 7: SYSTEM HEALTH", 'info')
        self.log("="*80, 'info')
        
        self.test_endpoint(
            'GET',
            '/health',
            'System Health Check',
            expected_keys=['status']
        )
        
        self.test_endpoint(
            'GET',
            '/api/agents/stats',
            'Get Agents Statistics',
            expected_keys=['total']
        )
        
        # RESULTS SUMMARY
        self.print_summary()
        
    def print_summary(self):
        """Afișează summary final"""
        self.log("\n\n" + "="*80, 'info')
        self.log("📊 TEST SUMMARY", 'info')
        self.log("="*80, 'info')
        
        total = len(self.results['passed']) + len(self.results['failed'])
        passed = len(self.results['passed'])
        failed = len(self.results['failed'])
        warnings = len(self.results['warnings'])
        
        self.log(f"\nTotal Tests: {total}", 'info')
        self.log(f"✅ Passed: {passed}", 'success')
        self.log(f"❌ Failed: {failed}", 'error' if failed > 0 else 'info')
        self.log(f"⚠️  Warnings: {warnings}", 'warning' if warnings > 0 else 'info')
        
        if total > 0:
            pass_rate = (passed / total) * 100
            self.log(f"\n📈 Pass Rate: {pass_rate:.1f}%", 'success' if pass_rate >= 80 else 'warning')
        
        # Failed tests details
        if failed > 0:
            self.log("\n❌ FAILED TESTS:", 'error')
            for i, test in enumerate(self.results['failed'], 1):
                self.log(f"\n   {i}. {test['name']}", 'error')
                self.log(f"      Endpoint: {test['endpoint']}", 'error')
                self.log(f"      Error: {test.get('error', 'Unknown')[:100]}", 'error')
        
        # Warnings details
        if warnings > 0:
            self.log("\n⚠️  WARNINGS:", 'warning')
            for i, warning in enumerate(self.results['warnings'], 1):
                self.log(f"\n   {i}. {warning['name']}", 'warning')
                self.log(f"      Issue: {warning['issue']}", 'warning')
        
        self.log("\n" + "="*80, 'info')
        self.log(f"🕐 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'info')
        self.log("="*80 + "\n", 'info')
        
        # Save detailed report
        report_path = f'/srv/hf/ai_agents/TEST_AGENT_{self.agent_id}_REPORT.json'
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        self.log(f"📄 Detailed report saved: {report_path}", 'info')

if __name__ == "__main__":
    tester = AgentTester(AGENT_ID)
    tester.run_all_tests()

