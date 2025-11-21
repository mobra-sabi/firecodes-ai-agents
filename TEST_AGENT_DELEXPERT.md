❌ Qwen2.5-72B local error: Qwen local not available on ports 9400 or 9201
⚠️ Qwen local failed, trying Llama 3.1 70B...
❌ Qwen2.5-72B local error: Qwen local not available on ports 9400 or 9201
⚠️ Qwen local failed, trying Llama 3.1 70B...
[94m[20:10:53] INFO: ================================================================================[0m
[94m[20:10:53] INFO: 🤖 TEST AGENT - Starting Comprehensive Testing[0m
[94m[20:10:53] INFO: ================================================================================[0m
[94m[20:10:53] INFO: [0m
[94m[20:10:53] INFO: 📡 BACKEND TESTS[0m
[94m[20:10:53] INFO: --------------------------------------------------------------------------------[0m
[92m[20:10:53] SUCCESS: ✅ Backend Health Check[0m
[92m[20:10:53] SUCCESS: ✅ GET /api/workflows/active[0m
[92m[20:10:53] SUCCESS: ✅ GET /api/workflows/recent[0m
[92m[20:10:53] SUCCESS: ✅ POST /api/workflows/start-agent-creation[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/workflows/status/{id}[0m
[92m[20:10:55] SUCCESS: ✅ POST /api/workflows/{id}/stop[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/agents/{id}/competitive-analysis[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/agents/{id}/competitors[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/agents/{id}/strategy[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/agents/{id}/serp-rankings[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/agents/{id}/serp/history[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/learning/stats[0m
[92m[20:10:55] SUCCESS: ✅ GET /api/learning/training-status[0m
[94m[20:10:55] INFO: [0m
[94m[20:10:55] INFO: 🎨 FRONTEND TESTS[0m
[94m[20:10:55] INFO: --------------------------------------------------------------------------------[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/services/workflows.js[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/hooks/useWebSocket.js[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/hooks/useWorkflowStatus.js[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/pages/WorkflowMonitor.jsx[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/App.jsx[0m
[92m[20:10:55] SUCCESS: ✅ Frontend File: src/components/layout/Sidebar.jsx[0m
[93m[20:10:59] WARNING: ⚠️  Frontend Code Quality Analysis (LLM): Code quality: good, 3 potential issues[0m
[94m[20:10:59] INFO: [0m
[94m[20:10:59] INFO: ================================================================================[0m
[94m[20:10:59] INFO: 📊 TEST SUMMARY[0m
[94m[20:10:59] INFO: ================================================================================[0m
[94m[20:10:59] INFO: Total Tests: 20[0m
[92m[20:10:59] SUCCESS: ✅ Passed: 19[0m
[94m[20:10:59] INFO: ❌ Failed: 0[0m
[93m[20:10:59] WARNING: ⚠️  Warnings: 1[0m
[94m[20:10:59] INFO: ⏭️  Skipped: 0[0m
[94m[20:10:59] INFO: ⏱️  Duration: 6.07s[0m
[92m[20:10:59] SUCCESS: 📈 Pass Rate: 95.0%[0m
[94m[20:10:59] INFO: ================================================================================[0m
[94m[20:10:59] INFO: [0m
[94m[20:10:59] INFO: 📝 Generating detailed report with LLM analysis...[0m
[92m[20:11:02] SUCCESS: ✅ Report saved to: /srv/hf/ai_agents/TEST_AGENT_REPORT.md[0m
[94m[20:11:02] INFO: [0m
[94m[20:11:02] INFO: 🎯 QUICK INSIGHTS:[0m
[92m[20:11:02] SUCCESS: ✅ All tests passed! System is healthy.[0m
[93m[20:11:02] WARNING: ⚠️  1 warnings - non-critical issues found[0m
