#!/usr/bin/env python3
"""
Test rapid: Creează agent cu Qdrant funcțional
"""

import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from tools.construction_agent_creator import ConstructionAgentCreator

# Testează cu TUV Rheinland
print("🚀 Testez creare agent cu Qdrant pornit...")
print("=" * 70)

creator = ConstructionAgentCreator()
result = creator.create_agent("https://academia-ro.tuv.com/")

print("\n" + "=" * 70)
print(f"✅ REZULTAT: {result}")

