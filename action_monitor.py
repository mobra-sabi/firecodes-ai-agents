"""
Action Monitor - Middleware to track all API routes and actions
"""
import time
import logging
import json
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from deepseek_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


class ActionMonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that monitors all API requests and logs them to MongoDB
    """
    
    def __init__(self, app: ASGIApp, orchestrator=None):
        super().__init__(app)
        self.orchestrator = orchestrator
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Try to get orchestrator from app state if not provided
        if not self.orchestrator:
            app = getattr(request, 'app', None)
            if app and hasattr(app, 'state'):
                self.orchestrator = getattr(app.state, 'orchestrator', None)
        # Skip monitoring for certain paths
        skip_paths = ['/health', '/docs', '/openapi.json', '/favicon.ico', '/ws/']
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        
        # Get user/agent info from request
        user_id = None
        agent_id = None
        
        # Try to get from headers or query params
        if "x-user-id" in request.headers:
            user_id = request.headers["x-user-id"]
        if "x-agent-id" in request.headers:
            agent_id = request.headers["x-agent-id"]
        
        # Try to get from query params
        if not agent_id and "agent_id" in request.query_params:
            agent_id = request.query_params["agent_id"]
        
        # Get request body (if any)
        request_data = {}
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        request_data = json.loads(body.decode())
                    except:
                        request_data = {"raw": body.decode()[:500]}  # Limit size
        except:
            pass
        
        # Execute request
        response = None
        status_code = 500
        response_data = {}
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Try to get response body
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parse response if JSON
                try:
                    response_data = json.loads(response_body.decode())
                except:
                    response_data = {"size": len(response_body)}
                
                # Recreate response with body
                from starlette.responses import Response as StarletteResponse
                response = StarletteResponse(
                    content=response_body,
                    status_code=status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            except:
                pass
                
        except Exception as e:
            logger.error(f"❌ Error in request: {e}")
            status_code = 500
            response_data = {"error": str(e)}
            raise
        
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine action type from route
            action_type = self._determine_action_type(request.url.path, request.method)
            
            # Log action
            if self.orchestrator:
                try:
                    self.orchestrator.log_action(
                        action_type=action_type,
                        route=request.url.path,
                        method=request.method,
                        user_id=user_id,
                        agent_id=agent_id,
                        request_data=request_data,
                        response_data=response_data,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        metadata={
                            "query_params": dict(request.query_params),
                            "headers": dict(request.headers),
                            "client_host": request.client.host if request.client else None
                        }
                    )
                except Exception as e:
                    logger.error(f"❌ Error logging action: {e}")
        
        return response
    
    def _determine_action_type(self, route: str, method: str) -> str:
        """Determine action type from route and method"""
        route_lower = route.lower()
        
        # Agent actions
        if "/agents" in route_lower:
            if method == "POST":
                return "agent_creation"
            elif method == "GET":
                return "agent_query"
            elif method == "PUT" or method == "PATCH":
                return "agent_update"
            elif method == "DELETE":
                return "agent_deletion"
        
        # SERP actions
        if "/serp" in route_lower or "serp" in route_lower:
            return "serp_search"
        
        # Competitive analysis
        if "/competitive" in route_lower or "/competitors" in route_lower:
            return "competitive_analysis"
        
        # Keywords
        if "/keywords" in route_lower:
            return "keyword_analysis"
        
        # Actions queue
        if "/actions" in route_lower:
            return "action_queue_operation"
        
        # Alerts
        if "/alerts" in route_lower:
            return "alert_operation"
        
        # Graph
        if "/graph" in route_lower:
            return "graph_operation"
        
        # Google Ads
        if "/ads" in route_lower:
            return "google_ads_operation"
        
        # Learning
        if "/learning" in route_lower:
            return "learning_operation"
        
        # Intelligence
        if "/intelligence" in route_lower:
            return "intelligence_query"
        
        # Reports
        if "/reports" in route_lower:
            return "report_generation"
        
        # Auth
        if "/auth" in route_lower or "/login" in route_lower or "/register" in route_lower:
            return "authentication"
        
        # Default
        return f"api_{method.lower()}"

