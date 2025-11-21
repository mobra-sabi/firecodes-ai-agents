#!/bin/bash
##################################################
# 🔄 LOOP AUTOMAT - PROCESEAZĂ TOȚI AGENȚII
# Rulează parallel_agent_processor.py până când 
# toți agenții au date complete
##################################################

LOG_FILE="/tmp/process_all_agents.log"
BATCH_LOG="/tmp/parallel_processing.log"

echo "╔════════════════════════════════════════════════════════════════╗" | tee $LOG_FILE
echo "║  🔄 PROCESARE AUTOMATĂ TOȚI AGENȚII - LOOP                    ║" | tee -a $LOG_FILE
echo "╚════════════════════════════════════════════════════════════════╝" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

cd /srv/hf/ai_agents

BATCH_NUM=1
MAX_BATCHES=20  # Max 20 batches (protecție împotriva loop infinit)

while [ $BATCH_NUM -le $MAX_BATCHES ]; do
    # Verifică câți agenți mai trebuie procesați
    AGENTS_LEFT=$(python3 -c "
from pymongo import MongoClient
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db
count = db.site_agents.count_documents({
    '\$or': [
        {'chunks_indexed': {'\$exists': False}},
        {'chunks_indexed': 0}
    ]
})
print(count)
" 2>/dev/null)
    
    if [ "$AGENTS_LEFT" -eq "0" ]; then
        echo "" | tee -a $LOG_FILE
        echo "✅ TOȚI AGENȚII AU FOST PROCESAȚI!" | tee -a $LOG_FILE
        break
    fi
    
    echo "" | tee -a $LOG_FILE
    echo "═══════════════════════════════════════════════════════════════" | tee -a $LOG_FILE
    echo "📦 BATCH #$BATCH_NUM - Agenți rămas: $AGENTS_LEFT" | tee -a $LOG_FILE
    echo "═══════════════════════════════════════════════════════════════" | tee -a $LOG_FILE
    echo "⏰ Start: $(date '+%H:%M:%S')" | tee -a $LOG_FILE
    
    # Rulează parallel processor
    python3 parallel_agent_processor.py > $BATCH_LOG 2>&1
    
    # Extrage rezultate
    SUCCESSES=$(grep -c "✅ SUCCES:" $BATCH_LOG 2>/dev/null || echo "0")
    FAILURES=$(grep -c "❌ EROARE:" $BATCH_LOG 2>/dev/null || echo "0")
    
    echo "   ✅ Succese: $SUCCESSES" | tee -a $LOG_FILE
    echo "   ❌ Eșuări: $FAILURES" | tee -a $LOG_FILE
    echo "⏰ End: $(date '+%H:%M:%S')" | tee -a $LOG_FILE
    
    if [ "$SUCCESSES" -eq "0" ] && [ "$FAILURES" -eq "0" ]; then
        echo "⚠️  Nu s-au procesat agenți în acest batch, opresc..." | tee -a $LOG_FILE
        break
    fi
    
    BATCH_NUM=$((BATCH_NUM + 1))
    
    # Pauză între batches
    if [ $BATCH_NUM -le $MAX_BATCHES ] && [ "$AGENTS_LEFT" -gt "0" ]; then
        echo "⏸️  Pauză 10s..." | tee -a $LOG_FILE
        sleep 10
    fi
done

# Raport final
echo "" | tee -a $LOG_FILE
echo "╔════════════════════════════════════════════════════════════════╗" | tee -a $LOG_FILE
echo "║  📊 RAPORT FINAL                                              ║" | tee -a $LOG_FILE
echo "╚════════════════════════════════════════════════════════════════╝" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

python3 -c "
from pymongo import MongoClient

mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

total = db.site_agents.count_documents({})
with_data = db.site_agents.count_documents({'chunks_indexed': {'\$gt': 0}})
without_data = total - with_data

print(f'📊 STATUS FINAL:')
print(f'   Total agenți: {total}')
print(f'   ✅ Cu date complete: {with_data} ({with_data/total*100:.1f}%)')
print(f'   ⏳ Fără date: {without_data}')
" | tee -a $LOG_FILE

echo "" | tee -a $LOG_FILE
echo "✅ FINALIZAT! Log complet: $LOG_FILE" | tee -a $LOG_FILE

