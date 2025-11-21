#!/usr/bin/env python3
"""
🎭 Master Agent - Agent Maestru Verbal
Serviciu FastAPI complet pentru controlul sistemului AI
"""

import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yaml

# Adaugă directorul curent la path
sys.path.insert(0, os.path.dirname(__file__))

from router import router

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "agent_actions.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agent_config.yaml")
config = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

# Create FastAPI app
app = FastAPI(
    title="Master Agent API",
    description="Agent Maestru Verbal pentru controlul sistemului AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router, prefix="/api", tags=["master-agent"])


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(content={
        "service": "Master Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "execute": "/api/execute",
            "state": "/api/state",
            "profile": "/api/profile/{user_id}",
            "learn": "/api/learn",
            "websocket": "/api/ws/{user_id}"
        }
    })


@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    
    port = config.get("agent", {}).get("port", 5010)
    host = config.get("agent", {}).get("host", "0.0.0.0")
    
    logger.info(f"🚀 Starting Master Agent on {host}:{port}")
    
    uvicorn.run(
        "agent_main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


