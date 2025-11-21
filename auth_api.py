#!/usr/bin/env python3
"""
🔐 AUTHENTICATION API - Multi-Tenant Support
Handles user registration, login, JWT tokens, and tenant isolation
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from typing import Optional, Dict, Any
import os

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# MongoDB
mongo = MongoClient('mongodb://localhost:27018/')
db = mongo.ai_agents_db

# FastAPI app
app = FastAPI(title="AI Agent Platform Auth API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Pydantic Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    industry: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    email: str
    company_name: str
    industry: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Utility Functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    # DEMO MODE: Accept demo-token-bypass
    if token == "demo-token-bypass":
        demo_user = db.users.find_one({"email": "demo@example.com"})
        if demo_user:
            return demo_user
        # Return mock user if not in DB
        return {
            "_id": ObjectId("000000000000000000000000"),
            "email": "demo@example.com",
            "full_name": "Demo User",
            "role": "admin"
        }
    
    payload = decode_token(token)
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# API Endpoints
@app.post("/auth/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = db.users.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_data = {
        "email": data.email,
        "password_hash": hash_password(data.password),
        "company_name": data.company_name,
        "industry": data.industry,
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "subscription": {
            "plan": "free",
            "agents_limit": 10,
            "expires_at": None
        }
    }
    
    result = db.users.insert_one(user_data)
    user_id = str(result.inserted_id)
    
    # Create JWT token
    token = create_access_token({
        "user_id": user_id,
        "email": data.email,
        "role": "user"
    })
    
    # Return response
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": data.email,
            "company_name": data.company_name,
            "industry": data.industry,
            "role": "user"
        }
    }


@app.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Login a user"""
    
    # Find user
    user = db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create JWT token
    token = create_access_token({
        "user_id": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "user")
    })
    
    # Return response
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "company_name": user.get("company_name", ""),
            "industry": user.get("industry", ""),
            "role": user.get("role", "user")
        }
    }


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "email": current_user["email"],
        "company_name": current_user.get("company_name", ""),
        "industry": current_user.get("industry", ""),
        "role": current_user.get("role", "user")
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    # For admin, show all agents. For regular users, show only their agents
    user_id = str(current_user["_id"])
    is_admin = current_user.get("role") == "admin"
    
    # Count agents
    if is_admin:
        master_agents = db.site_agents.count_documents({"agent_type": "master"})
        slave_agents = db.site_agents.count_documents({"agent_type": "slave"})
        total_agents = db.site_agents.count_documents({})
    else:
        master_agents = db.site_agents.count_documents({"agent_type": "master", "user_id": user_id})
        slave_agents = db.site_agents.count_documents({"agent_type": "slave", "user_id": user_id})
        total_agents = db.site_agents.count_documents({"user_id": user_id})
    
    # Count keywords (approximate)
    total_keywords = db.site_agents.aggregate([
        {"$match": {"user_id": user_id} if not is_admin else {}},
        {"$group": {"_id": None, "total": {"$sum": {"$size": {"$ifNull": ["$keywords", []]}}}}}
    ])
    keywords_count = next(total_keywords, {}).get("total", 0)
    
    # Count CI reports
    reports_count = db.competitive_reports.count_documents({"user_id": user_id} if not is_admin else {})
    
    return {
        "master_agents": master_agents,
        "slave_agents": slave_agents,
        "total_agents": total_agents,
        "total_keywords": keywords_count,
        "reports": reports_count
    }


@app.get("/agents")
async def get_agents(
    current_user: dict = Depends(get_current_user),
    type: Optional[str] = None
):
    """Get list of agents"""
    user_id = str(current_user["_id"])
    is_admin = current_user.get("role") == "admin"
    
    # Query filter
    query = {} if is_admin else {"user_id": user_id}
    
    # Add type filter if specified
    if type:
        query["agent_type"] = type
    
    # Get agents
    agents = list(db.site_agents.find(query).sort("created_at", -1).limit(100))
    
    # Convert ObjectId to string and calculate statistics
    result = []
    for agent in agents:
        agent_id = agent["_id"]
        
        # Calculate slave count for master agents
        slave_count = 0
        if agent.get("agent_type") == "master":
            slave_count = db.site_agents.count_documents({
                "master_agent_id": agent_id,
                "agent_type": "slave"
            })
        
        # Calculate keyword count
        keywords = agent.get("keywords", [])
        keyword_count = len(keywords) if isinstance(keywords, list) else 0
        
        # Build agent data
        agent_data = {
            "_id": str(agent_id),
            "domain": agent.get("domain", ""),
            "site_url": agent.get("site_url", ""),
            "agent_type": agent.get("agent_type", "master"),
            "industry": agent.get("industry", ""),
            "status": agent.get("status", "active"),
            "created_at": agent.get("created_at", datetime.now(timezone.utc).isoformat()),
            "chunks_indexed": agent.get("chunks_indexed", 0),
            "keywords": keywords,
            "keyword_count": keyword_count,
            "slave_count": slave_count,
        }
        
        if "master_agent_id" in agent and agent["master_agent_id"]:
            agent_data["master_agent_id"] = str(agent["master_agent_id"])
        
        result.append(agent_data)
    
    return result


class CreateAgentRequest(BaseModel):
    site_url: str
    industry: str


@app.post("/agents")
async def create_agent(
    data: CreateAgentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new master agent and start CEO workflow"""
    import sys
    sys.path.insert(0, '/srv/hf/ai_agents')
    
    try:
        # Import CEO workflow
        from ceo_master_workflow import CEOMasterWorkflow
        
        # Create workflow instance
        workflow = CEOMasterWorkflow()
        
        # Start workflow in background
        import asyncio
        from threading import Thread
        
        def run_workflow():
            """Run workflow in separate thread"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    workflow.execute_full_workflow(
                        site_url=data.site_url,
                        results_per_keyword=15,
                        parallel_gpu_agents=5
                    )
                )
                
                # Update agent with user_id
                if result.get("master_agent_id"):
                    db.site_agents.update_one(
                        {"_id": ObjectId(result["master_agent_id"])},
                        {"$set": {"user_id": str(current_user["_id"])}}
                    )
                    
            except Exception as e:
                print(f"Workflow error: {e}")
            finally:
                loop.close()
        
        # Start workflow thread
        thread = Thread(target=run_workflow, daemon=True)
        thread.start()
        
        return {
            "message": "Agent creation started",
            "site_url": data.site_url,
            "industry": data.industry,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("🔐 Starting Auth API on port 5001...")
    print("📝 Endpoints:")
    print("   POST /auth/register")
    print("   POST /auth/login")
    print("   GET  /auth/me")
    uvicorn.run(app, host="0.0.0.0", port=5001)

