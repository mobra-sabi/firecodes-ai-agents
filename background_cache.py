#!/usr/bin/env python3
import time
import threading
from agents.cached_agent import CachedSiteAgent

class BackgroundCacheService:
    def __init__(self):
        self.active_agents = {}
        self.running = False
        
    def start_service(self):
        """Pornește serviciul de caching în background"""
        self.running = True
        cache_thread = threading.Thread(target=self._cache_maintenance)
        cache_thread.daemon = True
        cache_thread.start()
        print("⚙️ Serviciu de caching în background pornit")
        
    def _cache_maintenance(self):
        """Menține agenții activi în memorie"""
        while self.running:
            # Menține agenții recenți în cache
            time.sleep(300)  # Verifică la fiecare 5 minute
            
    def get_agent(self, site_url):
        """Obține agent cu caching optimizat"""
        if site_url not in self.active_agents:
            agent_loader = CachedSiteAgent(site_url)
            self.active_agents[site_url] = agent_loader.load_or_create_agent()
        return self.active_agents[site_url]
