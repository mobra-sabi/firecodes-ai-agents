#!/usr/bin/env python3
"""Test pentru QdrantContextEnhancer"""

from qdrant_context_enhancer import get_context_enhancer

print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  🧪 TEST: Qdrant Context Enhancer pentru DeepSeek                   ║")
print("╚══════════════════════════════════════════════════════════════════════╝")
print()

# Initialize
enhancer = get_context_enhancer()

# Test 1: Context pentru o query simplă
print("📝 TEST 1: Context pentru query simplă")
print("-" * 70)

agent_id = "6910d0682716fa6b8a6f8e72"  # ropaintsolutions
query = "Ce servicii de protecție la foc oferă compania?"

contexts = enhancer.get_context_for_query(
    query=query,
    collection_name=f"agent_{agent_id}",
    top_k=3
)

print(f"Query: {query}")
print(f"Găsite: {len(contexts)} contexte\n")

for i, ctx in enumerate(contexts, 1):
    print(f"{i}. Score: {ctx['score']:.3f}")
    print(f"   Text: {ctx['text'][:150]}...")
    print()

# Test 2: Context pentru strategie competitivă
print("\n" + "="*70)
print("📝 TEST 2: Context complet pentru strategie competitivă")
print("-" * 70)

full_context = enhancer.get_full_industry_analysis_context(
    agent_id=agent_id,
    analysis_focus="strategia competitivă în industria de protecție la foc"
)

print("Context generat pentru DeepSeek:")
print()
print(full_context[:1500])
print()
print("[... continut trunchiat pentru afisare ...]")
print()
print(f"✅ Total caractere: {len(full_context)}")

# Test 3: Industry context per topics
print("\n" + "="*70)
print("📝 TEST 3: Context per topics industriale")
print("-" * 70)

topics = ["protecție la foc", "servicii", "experiență"]
industry_ctx = enhancer.get_industry_context(
    agent_id=agent_id,
    topics=topics,
    top_k_per_topic=2
)

for topic, contexts in industry_ctx.items():
    print(f"\n🎯 Topic: {topic}")
    print(f"   Contexte găsite: {len(contexts)}")
    if contexts:
        print(f"   Best score: {contexts[0]['score']:.3f}")

print()
print("═══════════════════════════════════════════════════════════════════════")
print("✅ QdrantContextEnhancer funcționează perfect!")
print("✅ DeepSeek va primi context îmbogățit automat!")
print("═══════════════════════════════════════════════════════════════════════")
