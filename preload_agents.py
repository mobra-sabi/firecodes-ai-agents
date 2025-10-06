#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.cached_agent import CachedSiteAgent

# Lista site-uri critice pentru pre-încărcare
CRITICAL_SITES = [
    "https://tehnica-antifoc.ro/",
    "https://www.cosmotechnical.ro/"
]

def preload_critical_agents():
    """Pre-încarcă agenții pentru site-uri critice"""
    print("🚀 Pre-încărcare agenți critici...")
    
    for site_url in CRITICAL_SITES:
        print(f"⚡ Pre-încărcare: {site_url}")
        agent_loader = CachedSiteAgent(site_url)
        agent = agent_loader.load_or_create_agent()
        print(f"✅ Agent pregătit: {site_url}")
    
    print("🎉 Toți agenții critici sunt pregătiți!")

if __name__ == "__main__":
    preload_critical_agents()
