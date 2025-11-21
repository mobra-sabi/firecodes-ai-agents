"""
Actions Module - Conectează outputurile LangChain la acțiuni reale

Acest modul primește ActionPlan-uri din Decision Chain și le execută automat
prin conectori externi (Google Ads, WordPress, SEO APIs, etc.)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .action_executor import ActionExecutor, execute_action_plan, get_action_status
from .google_ads_connector import GoogleAdsConnector
from .wordpress_connector import WordPressConnector
from .seo_api_connector import SEOAPIConnector

__all__ = [
    "ActionExecutor",
    "GoogleAdsConnector",
    "WordPressConnector",
    "SEOAPIConnector",
    "execute_action_plan",
    "get_action_status"
]

