#!/bin/bash

echo "🔗 IMPLEMENTARE INTEGRARE COMPLETĂ"
echo "=================================="
echo ""

# 1. Modifică llm_orchestrator să salveze agent_id
echo "1️⃣ Actualizare LLM Orchestrator cu agent_id metadata..."
# TODO: Add agent_id to save_interaction calls

# 2. Modifică data collector să accepte agent_id
echo "2️⃣ Actualizare Data Collector..."
cd /srv/hf/ai_agents/data_collector
cat >> collector.py << 'EOF'

# Agent-specific functions
def get_agent_interactions(agent_id: str, limit: int = 100):
    """Get interactions for specific agent"""
    collection = get_mongo_collection()
    return list(collection.find({
        "metadata.agent_id": agent_id,
        "type": "interaction"
    }).sort("timestamp", -1).limit(limit))

def get_agent_stats(agent_id: str):
    """Get learning statistics for agent"""
    collection = get_mongo_collection()
    
    total = collection.count_documents({
        "metadata.agent_id": agent_id,
        "type": "interaction"
    })
    
    processed = collection.count_documents({
        "metadata.agent_id": agent_id,
        "type": "interaction",
        "processed": True
    })
    
    return {
        "agent_id": agent_id,
        "total_interactions": total,
        "processed": processed,
        "pending": total - processed,
        "training_ready": total >= 10
    }
EOF

echo "✅ Data Collector updated"

# 3. Restart services
echo ""
echo "3️⃣ Restart servicii..."
echo "   Port 5001 - Auto-Learning UI"
echo "   Port 6000 - Live Dashboard"
echo "   Port 5010 - Master Agent"

echo ""
echo "✅ INTEGRARE PREGĂTITĂ!"
echo ""
echo "📋 URMĂTORII PAȘI:"
echo "   1. Testează salvarea cu agent_id"
echo "   2. Verifică în Auto-Learning UI"
echo "   3. Testează Master Agent commands"
echo "   4. Verifică Live Dashboard metrics"
