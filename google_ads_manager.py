"""
Google Ads Manager
Manages Google Ads API integration for campaign creation, ad groups, keywords, and RSA ads
"""
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# Google Ads API imports
try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    GOOGLE_ADS_AVAILABLE = True
    GoogleAdsClientType = GoogleAdsClient
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    GoogleAdsClientType = None
    logger.warning("⚠️ Google Ads API library not installed. Install with: pip install google-ads")


class GoogleAdsManager:
    """Manages Google Ads API operations"""
    
    def __init__(self, mongo_client: MongoClient = None):
        if mongo_client is None:
            mongo_client = MongoClient("mongodb://localhost:27017/")
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.ads_collection = self.db["google_ads_accounts"]
        self.campaigns_collection = self.db["google_ads_campaigns"]
        
        # OAuth 2.0 configuration (from Google Cloud Console credentials)
        # Load from environment variables for security
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.project_id = os.getenv("GOOGLE_ADS_PROJECT_ID", "")
        self.redirect_uri = os.getenv("GOOGLE_ADS_REDIRECT_URI", "http://localhost/api/ads/oauth/callback")
        self.scopes = [
            "https://www.googleapis.com/auth/adwords"
        ]
        
        # OAuth 2.0 endpoints
        self.auth_uri = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri = "https://oauth2.googleapis.com/token"
        
        # Google Ads API configuration
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.api_version = "v16"
        
        if not GOOGLE_ADS_AVAILABLE:
            logger.warning("⚠️ Google Ads API not available. Install google-ads package.")
    
    def get_oauth_url(self, agent_id: str, state: Optional[str] = None) -> str:
        """
        Generate OAuth 2.0 authorization URL
        
        Args:
            agent_id: Agent ID to associate with the account
            state: Optional state parameter for OAuth flow
        
        Returns:
            Authorization URL
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed. Install with: pip install google-ads")
        
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": self.client_id,
                    "project_id": self.project_id,
                    "auth_uri": self.auth_uri,
                    "token_uri": self.token_uri,
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": self.client_secret,
                    "redirect_uris": ["http://localhost"]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state or agent_id,
            prompt='consent'
        )
        
        return authorization_url
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict:
        """
        Handle OAuth callback and store credentials
        
        Args:
            code: Authorization code from OAuth callback
            state: State parameter (should contain agent_id)
        
        Returns:
            Account information
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed. Install with: pip install google-ads")
        
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": self.client_id,
                    "project_id": self.project_id,
                    "auth_uri": self.auth_uri,
                    "token_uri": self.token_uri,
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": self.client_secret,
                    "redirect_uris": ["http://localhost"]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        # Exchange code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get customer ID (need to make initial API call)
        # For now, store credentials and let user provide customer_id
        account_data = {
            "agent_id": state,  # state should be agent_id
            "credentials": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            },
            "connected_at": datetime.now(timezone.utc),
            "status": "connected"
        }
        
        self.ads_collection.update_one(
            {"agent_id": state},
            {"$set": account_data},
            upsert=True
        )
        
        logger.info(f"✅ Google Ads account connected for agent {state}")
        return account_data
    
    def get_client(self, agent_id: str):
        """
        Get Google Ads client for an agent
        
        Args:
            agent_id: Agent ID
        
        Returns:
            GoogleAdsClient instance or None
        """
        if not GOOGLE_ADS_AVAILABLE or GoogleAdsClientType is None:
            return None
        
        account = self.ads_collection.find_one({"agent_id": agent_id})
        if not account or account.get("status") != "connected":
            logger.warning(f"⚠️ No connected Google Ads account for agent {agent_id}")
            return None
        
        credentials_data = account.get("credentials", {})
        customer_id = account.get("customer_id")
        
        if not customer_id:
            logger.warning(f"⚠️ No customer_id configured for agent {agent_id}")
            return None
        
        # Create credentials object
        credentials = Credentials(
            token=credentials_data.get("token"),
            refresh_token=credentials_data.get("refresh_token"),
            token_uri=credentials_data.get("token_uri"),
            client_id=credentials_data.get("client_id"),
            client_secret=credentials_data.get("client_secret"),
            scopes=credentials_data.get("scopes")
        )
        
        # Refresh token if needed
        if credentials.expired:
            credentials.refresh(Request())
            # Update stored credentials
            self.ads_collection.update_one(
                {"agent_id": agent_id},
                {"$set": {"credentials.token": credentials.token}}
            )
        
        # Create Google Ads client
        try:
            client = GoogleAdsClient.load_from_dict({
                "developer_token": self.developer_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": credentials.refresh_token,
                "use_proto_plus": True
            })
            return client
        except Exception as e:
            logger.error(f"❌ Error creating Google Ads client: {e}")
            return None
    
    def create_campaign(
        self,
        agent_id: str,
        campaign_name: str,
        budget_amount_micros: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bidding_strategy: str = "MAXIMIZE_CONVERSIONS"
    ) -> Dict:
        """
        Create a new Google Ads campaign
        
        Args:
            agent_id: Agent ID
            campaign_name: Campaign name
            budget_amount_micros: Budget in micros (1,000,000 micros = 1 currency unit)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            bidding_strategy: Bidding strategy type
        
        Returns:
            Campaign information
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed")
        
        client = self.get_client(agent_id)
        if not client:
            raise Exception("Google Ads client not available")
        
        account = self.ads_collection.find_one({"agent_id": agent_id})
        customer_id = account.get("customer_id")
        
        try:
            # Create campaign budget
            budget_service = client.get_service("CampaignBudgetService")
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            budget.name = f"{campaign_name} Budget"
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            budget.amount_micros = budget_amount_micros
            
            budget_response = budget_service.mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[budget_operation]
            )
            budget_resource_name = budget_response.results[0].resource_name
            
            # Create campaign
            campaign_service = client.get_service("CampaignService")
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = campaign_name
            campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
            campaign.status = client.enums.CampaignStatusEnum.PAUSED  # Start paused
            campaign.campaign_budget = budget_resource_name
            campaign.start_date = start_date or datetime.now().strftime("%Y-%m-%d")
            if end_date:
                campaign.end_date = end_date
            
            # Set bidding strategy
            if bidding_strategy == "MAXIMIZE_CONVERSIONS":
                campaign.maximize_conversions.target_cpa_micros = None
            elif bidding_strategy == "TARGET_CPA":
                # Would need target_cpa_micros parameter
                campaign.target_cpa.target_cpa_micros = None
            
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation]
            )
            campaign_resource_name = campaign_response.results[0].resource_name
            
            # Store in MongoDB
            campaign_data = {
                "agent_id": agent_id,
                "campaign_id": campaign_resource_name.split("/")[-1],
                "campaign_name": campaign_name,
                "budget_amount_micros": budget_amount_micros,
                "bidding_strategy": bidding_strategy,
                "status": "paused",
                "created_at": datetime.now(timezone.utc),
                "resource_name": campaign_resource_name
            }
            
            self.campaigns_collection.insert_one(campaign_data)
            
            logger.info(f"✅ Campaign created: {campaign_name} for agent {agent_id}")
            return campaign_data
        
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex}")
            raise Exception(f"Google Ads API error: {ex}")
    
    def create_ad_group(
        self,
        agent_id: str,
        campaign_id: str,
        ad_group_name: str,
        cpc_bid_micros: Optional[int] = None
    ) -> Dict:
        """
        Create an ad group within a campaign
        
        Args:
            agent_id: Agent ID
            campaign_id: Campaign ID
            ad_group_name: Ad group name
            cpc_bid_micros: CPC bid in micros (optional)
        
        Returns:
            Ad group information
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed")
        
        client = self.get_client(agent_id)
        if not client:
            raise Exception("Google Ads client not available")
        
        account = self.ads_collection.find_one({"agent_id": agent_id})
        customer_id = account.get("customer_id")
        
        campaign = self.campaigns_collection.find_one({
            "agent_id": agent_id,
            "campaign_id": campaign_id
        })
        if not campaign:
            raise Exception(f"Campaign {campaign_id} not found")
        
        try:
            ad_group_service = client.get_service("AdGroupService")
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create
            ad_group.name = ad_group_name
            ad_group.campaign = campaign.get("resource_name")
            ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
            
            if cpc_bid_micros:
                ad_group.cpc_bid_micros = cpc_bid_micros
            
            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[ad_group_operation]
            )
            ad_group_resource_name = ad_group_response.results[0].resource_name
            
            # Store in MongoDB
            ad_group_data = {
                "agent_id": agent_id,
                "campaign_id": campaign_id,
                "ad_group_id": ad_group_resource_name.split("/")[-1],
                "ad_group_name": ad_group_name,
                "cpc_bid_micros": cpc_bid_micros,
                "status": "enabled",
                "created_at": datetime.now(timezone.utc),
                "resource_name": ad_group_resource_name
            }
            
            self.db.google_ads_ad_groups.insert_one(ad_group_data)
            
            logger.info(f"✅ Ad group created: {ad_group_name} for campaign {campaign_id}")
            return ad_group_data
        
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex}")
            raise Exception(f"Google Ads API error: {ex}")
    
    def add_keywords(
        self,
        agent_id: str,
        ad_group_id: str,
        keywords: List[Dict],
        match_type: str = "BROAD"
    ) -> Dict:
        """
        Add keywords to an ad group
        
        Args:
            agent_id: Agent ID
            ad_group_id: Ad group ID
            keywords: List of keyword dicts with 'text' and optional 'cpc_bid_micros'
            match_type: Match type (BROAD, PHRASE, EXACT)
        
        Returns:
            Operation result
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed")
        
        client = self.get_client(agent_id)
        if not client:
            raise Exception("Google Ads client not available")
        
        account = self.ads_collection.find_one({"agent_id": agent_id})
        customer_id = account.get("customer_id")
        
        ad_group = self.db.google_ads_ad_groups.find_one({
            "agent_id": agent_id,
            "ad_group_id": ad_group_id
        })
        if not ad_group:
            raise Exception(f"Ad group {ad_group_id} not found")
        
        try:
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            operations = []
            
            match_type_enum = {
                "BROAD": client.enums.KeywordMatchTypeEnum.BROAD,
                "PHRASE": client.enums.KeywordMatchTypeEnum.PHRASE,
                "EXACT": client.enums.KeywordMatchTypeEnum.EXACT
            }.get(match_type, client.enums.KeywordMatchTypeEnum.BROAD)
            
            for keyword_data in keywords:
                operation = client.get_type("AdGroupCriterionOperation")
                criterion = operation.create
                criterion.ad_group = ad_group.get("resource_name")
                criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                
                keyword = criterion.keyword
                keyword.text = keyword_data.get("text")
                keyword.match_type = match_type_enum
                
                if keyword_data.get("cpc_bid_micros"):
                    criterion.cpc_bid_micros = keyword_data.get("cpc_bid_micros")
                
                operations.append(operation)
            
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=operations
            )
            
            logger.info(f"✅ Added {len(keywords)} keywords to ad group {ad_group_id}")
            return {
                "added": len(response.results),
                "ad_group_id": ad_group_id
            }
        
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex}")
            raise Exception(f"Google Ads API error: {ex}")
    
    def create_rsa_ad(
        self,
        agent_id: str,
        ad_group_id: str,
        headlines: List[str],
        descriptions: List[str],
        final_url: str,
        path1: Optional[str] = None,
        path2: Optional[str] = None
    ) -> Dict:
        """
        Create a Responsive Search Ad (RSA)
        
        Args:
            agent_id: Agent ID
            ad_group_id: Ad group ID
            headlines: List of headline texts (3-15 headlines)
            descriptions: List of description texts (2-4 descriptions)
            final_url: Final URL
            path1: Optional path 1
            path2: Optional path 2
        
        Returns:
            Ad information
        """
        if not GOOGLE_ADS_AVAILABLE:
            raise Exception("Google Ads API library not installed")
        
        client = self.get_client(agent_id)
        if not client:
            raise Exception("Google Ads client not available")
        
        account = self.ads_collection.find_one({"agent_id": agent_id})
        customer_id = account.get("customer_id")
        
        ad_group = self.db.google_ads_ad_groups.find_one({
            "agent_id": agent_id,
            "ad_group_id": ad_group_id
        })
        if not ad_group:
            raise Exception(f"Ad group {ad_group_id} not found")
        
        try:
            ad_group_ad_service = client.get_service("AdGroupAdService")
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create
            ad_group_ad.ad_group = ad_group.get("resource_name")
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
            
            # Create responsive search ad
            ad = ad_group_ad.ad
            ad.type_ = client.enums.AdTypeEnum.RESPONSIVE_SEARCH_AD
            ad.final_urls.append(final_url)
            
            if path1:
                ad.final_url_suffix = f"{path1}/{path2}" if path2 else path1
            
            # Add headlines
            for headline_text in headlines[:15]:  # Max 15 headlines
                headline = ad.responsive_search_ad.headlines.add()
                headline.text = headline_text
                headline.pinned_field = None  # Let Google optimize
            
            # Add descriptions
            for desc_text in descriptions[:4]:  # Max 4 descriptions
                description = ad.responsive_search_ad.descriptions.add()
                description.text = desc_text
                description.pinned_field = None
            
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[ad_group_ad_operation]
            )
            
            ad_resource_name = response.results[0].resource_name
            
            # Store in MongoDB
            ad_data = {
                "agent_id": agent_id,
                "ad_group_id": ad_group_id,
                "ad_id": ad_resource_name.split("/")[-1],
                "ad_type": "RESPONSIVE_SEARCH_AD",
                "headlines": headlines,
                "descriptions": descriptions,
                "final_url": final_url,
                "status": "enabled",
                "created_at": datetime.now(timezone.utc),
                "resource_name": ad_resource_name
            }
            
            self.db.google_ads_ads.insert_one(ad_data)
            
            logger.info(f"✅ RSA ad created for ad group {ad_group_id}")
            return ad_data
        
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex}")
            raise Exception(f"Google Ads API error: {ex}")
    
    def sync_from_seo_insights(
        self,
        agent_id: str,
        keywords: List[Dict],
        intent_filter: str = "transactional"
    ) -> Dict:
        """
        Create Google Ads campaigns from SEO insights
        
        Args:
            agent_id: Agent ID
            keywords: List of keyword dicts with 'keyword', 'opportunity_score', 'intent'
            intent_filter: Filter keywords by intent (transactional, commercial, informational)
        
        Returns:
            Sync result
        """
        # Filter keywords by intent and opportunity
        filtered_keywords = [
            kw for kw in keywords
            if kw.get("intent") == intent_filter and kw.get("opportunity_score", 0) > 0.5
        ]
        
        if not filtered_keywords:
            return {"status": "no_keywords", "message": "No keywords matching criteria"}
        
        # Group keywords by theme (simplified - could use clustering)
        # For now, create one campaign with one ad group
        campaign_name = f"SEO Insights - {intent_filter.title()} - {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            # Create campaign
            campaign = self.create_campaign(
                agent_id=agent_id,
                campaign_name=campaign_name,
                budget_amount_micros=10000000,  # 10 currency units
                bidding_strategy="MAXIMIZE_CONVERSIONS"
            )
            
            # Create ad group
            ad_group = self.create_ad_group(
                agent_id=agent_id,
                campaign_id=campaign["campaign_id"],
                ad_group_name=f"{campaign_name} - Ad Group 1"
            )
            
            # Add keywords
            keyword_list = [
                {"text": kw["keyword"], "cpc_bid_micros": None}
                for kw in filtered_keywords[:20]  # Limit to 20 keywords
            ]
            
            self.add_keywords(
                agent_id=agent_id,
                ad_group_id=ad_group["ad_group_id"],
                keywords=keyword_list,
                match_type="BROAD"
            )
            
            # Create RSA ad (simplified - would use DeepSeek to generate headlines/descriptions)
            agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            domain = agent.get("domain", "") if agent else ""
            
            headlines = [
                f"Best {domain} Services",
                f"Professional {domain} Solutions",
                f"Quality {domain} Services"
            ]
            descriptions = [
                f"Discover premium {domain} services",
                f"Expert solutions for your {domain} needs"
            ]
            
            self.create_rsa_ad(
                agent_id=agent_id,
                ad_group_id=ad_group["ad_group_id"],
                headlines=headlines,
                descriptions=descriptions,
                final_url=f"https://{domain}"
            )
            
            return {
                "status": "success",
                "campaign_id": campaign["campaign_id"],
                "ad_group_id": ad_group["ad_group_id"],
                "keywords_added": len(keyword_list)
            }
        
        except Exception as e:
            logger.error(f"❌ Error syncing from SEO insights: {e}")
            return {"status": "error", "message": str(e)}

