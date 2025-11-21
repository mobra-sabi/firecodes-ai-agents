#!/bin/bash
##################################################
# 📊 MONITORIZARE LIVE PROCESARE AGENȚI
##################################################

clear

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  📊 MONITORIZARE LIVE PROCESARE AGENȚI                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    # Clear previous output (keep header)
    tput cup 4 0
    tput ed
    
    # Timestamp
    echo "⏰ Actualizat: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Status MongoDB
    python3 << 'PYEOF'
from pymongo import MongoClient
import sys

try:
    mongo = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
    db = mongo.ai_agents_db
    
    total = db.site_agents.count_documents({})
    with_data = db.site_agents.count_documents({'chunks_indexed': {'$gt': 0}})
    without_data = total - with_data
    
    percent = (with_data / total * 100) if total > 0 else 0
    
    print(f"📊 STATUS MONGODB:")
    print(f"   Total agenți: {total}")
    print(f"   ✅ Cu date complete: {with_data} ({percent:.1f}%)")
    print(f"   ⏳ În așteptare: {without_data}")
    print("")
    
    # Progress bar
    bar_length = 50
    filled = int(bar_length * percent / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"   [{bar}] {percent:.1f}%")
    print("")
    
except Exception as e:
    print(f"❌ Eroare MongoDB: {e}")
    sys.exit(1)
PYEOF
    
    # GPU Usage
    echo "🎮 GPU USAGE:"
    nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits | \
    awk -F', ' 'NR>=6 && NR<=10 {printf "   GPU %s: %3s%% | RAM: %s/%s MB\n", $1, $3, $4, $5}'
    echo ""
    
    # Procese active
    echo "🔄 PROCESE ACTIVE:"
    PARALLEL_PROC=$(ps aux | grep "parallel_agent_processor" | grep -v grep | wc -l)
    VLLM_PROC=$(ps aux | grep "vllm.*9301" | grep -v grep | wc -l)
    
    if [ $PARALLEL_PROC -gt 0 ]; then
        echo "   ✅ Parallel processor: RUNNING ($PARALLEL_PROC procese)"
    else
        echo "   ⏸️  Parallel processor: STOPPED"
    fi
    
    if [ $VLLM_PROC -gt 0 ]; then
        echo "   ✅ vLLM (port 9301): RUNNING"
    else
        echo "   ❌ vLLM (port 9301): STOPPED"
    fi
    echo ""
    
    # Ultimele 5 linii din log
    if [ -f /tmp/parallel_processing.log ]; then
        echo "📜 ULTIMELE EVENIMENTE:"
        tail -10 /tmp/parallel_processing.log | grep -E "GPU|SUCCES|EROARE|Agent:" | tail -5 | sed 's/^/   /'
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 Apasă Ctrl+C pentru a opri monitorizarea"
    echo ""
    
    sleep 5
done

