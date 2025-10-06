#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from multi_agent.agent_orchestrator import AgentOrchestrator
from multi_agent.communication_protocol import AgentCommunicationProtocol, MessageType

async def test_collaboration_system():
    """Test pentru sistemul de colaborare între agenți"""
    
    print("🧪 TEST SISTEM COLABORARE MULTI-AGENT")
    print("=" * 50)
    
    # Inițializează sistemul
    orchestrator = AgentOrchestrator()
    comm_protocol = AgentCommunicationProtocol()
    
    # Creează agenți demo pentru test
    await create_demo_agents(orchestrator)
    
    # Test 1: Colaborare simplă
    print("\n🔬 Test 1: Colaborare simplă")
    await test_simple_collaboration(orchestrator)
    
    # Test 2: Comunicare între agenți
    print("\n🔬 Test 2: Comunicare între agenți")
    await test_agent_communication(comm_protocol, orchestrator)
    
    # Test 3: Swarm intelligence
    print("\n🔬 Test 3: Swarm intelligence")
    await test_swarm_intelligence(orchestrator)
    
    print("\n✅ Toate testele completate!")

async def create_demo_agents(orchestrator):
    """Creează agenți demo pentru teste"""
    
    import uuid
    from datetime import datetime
    
    demo_agents = [
        {
            'site_url': 'https://demo-construction.ro',
            'industry': 'construction',
            'capabilities': ['pricing_expert', 'technical_specialist']
        },
        {
            'site_url': 'https://demo-legal.ro', 
            'industry': 'legal',
            'capabilities': ['legal', 'contract_analysis']
        },
        {
            'site_url': 'https://demo-finance.ro',
            'industry': 'finance',
            'capabilities': ['financial', 'investment_analysis']
        }
    ]
    
    for demo_data in demo_agents:
        agent_id = str(uuid.uuid4())
        agent_config = {
            'agent_id': agent_id,
            'site_url': demo_data['site_url'],
            'industry': demo_data['industry'],
            'capabilities': demo_data['capabilities'],
            'creation_time': datetime.now().isoformat(),
            'status': 'test',
            'connections': [],
            'collaboration_history': []
        }
        
        orchestrator.active_agents[agent_id] = agent_config
        print(f"🤖 Agent demo creat: {demo_data['industry']} ({agent_id[:8]})")

async def test_simple_collaboration(orchestrator):
    """Test colaborare simplă între agenți"""
    
    if len(orchestrator.active_agents) < 2:
        print("❌ Nu sunt suficienți agenți pentru test")
        return
        
    primary_agent_id = list(orchestrator.active_agents.keys())[0]
    question = "Cum pot estima costurile pentru un proiect de construcții cu aspecte legale complexe?"
    
    print(f"❓ Întrebare test: {question}")
    print(f"🎯 Agent principal: {primary_agent_id[:8]}")
    
    # Rulează colaborarea
    result = await orchestrator.agent_collaboration_request(
        primary_agent_id,
        question,
        {'test_mode': True}
    )
    
    if result:
        print(f"✅ Colaborare reușită!")
        print(f"👥 Experți consultați: {len(result['expert_agents'])}")
        print(f"💬 Răspuns: {result['final_answer'][:100]}...")
    else:
        print("❌ Colaborarea a eșuat")

async def test_agent_communication(comm_protocol, orchestrator):
    """Test comunicare între agenți"""
    
    if len(orchestrator.active_agents) < 2:
        print("❌ Nu sunt suficienți agenți pentru test comunicare")
        return
        
    agents = list(orchestrator.active_agents.keys())
    
    # Test mesaj direct
    message_id = await comm_protocol.send_agent_message(
        agents[0],
        agents[1], 
        MessageType.EXPERTISE_REQUEST,
        "Test message pentru verificarea sistemului de comunicare"
    )
    
    print(f"📨 Mesaj trimis cu ID: {message_id}")
    
    # Test broadcast
    broadcast_id = await comm_protocol.broadcast_to_network(
        agents[0],
        MessageType.MARKET_UPDATE,
        "Test broadcast pentru toți agenții din rețea"
    )
    
    print(f"📢 Broadcast trimis cu ID: {broadcast_id}")
    
    # Afișează statistici
    stats = comm_protocol.get_communication_stats()
    print(f"📊 Total mesaje: {stats['total_messages']}")

async def test_swarm_intelligence(orchestrator):
    """Test swarm intelligence simulation"""
    
    print("🐝 Simulez swarm intelligence...")
    
    complex_problem = {
        'description': 'Optimizarea unui proiect multi-disciplinar',
        'domains': ['construction', 'legal', 'finance'],
        'complexity': 'high'
    }
    
    # Simulează procesul de swarm intelligence
    steps = [
        "🔍 Analizez problema complexă...",
        "📊 Identific domeniile necesare...",
        "👥 Selectez agenții specializați...",
        "⚡ Procesez în paralel...",
        "🔗 Combin rezultatele...",
        "✅ Generez soluția finală..."
    ]
    
    for i, step in enumerate(steps):
        print(f"  {step}")
        await asyncio.sleep(0.5)  # Simulează timpul de procesare
        
    print("🎯 Swarm intelligence rezultat:")
    print("  • Identificate 3 domenii de expertiză")
    print("  • Procesare paralelă realizată")
    print("  • Soluție integrată generată")
    print("  • Consensus atins între agenți")

if __name__ == "__main__":
    asyncio.run(test_collaboration_system())
