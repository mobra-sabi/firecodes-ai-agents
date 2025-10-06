from agents.site_agent import SiteAgent
import pickle
import os

class CachedSiteAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.cache_file = f"/tmp/agent_cache_{site_url.replace('://', '_').replace('/', '_')}.pkl"
        self.agent = None
        
    def load_or_create_agent(self):
        """Încarcă agent din cache sau creează unul nou"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.agent = pickle.load(f)
                print("⚡ Agent încărcat din cache")
            except:
                self.agent = SiteAgent(self.site_url)
                self._save_to_cache()
        else:
            self.agent = SiteAgent(self.site_url)
            self._save_to_cache()
        return self.agent
    
    def _save_to_cache(self):
        """Salvează agentul în cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.agent, f)
        except Exception as e:
            print(f"⚠️ Eroare la caching: {e}")
