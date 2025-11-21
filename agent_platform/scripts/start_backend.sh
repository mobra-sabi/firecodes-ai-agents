#!/bin/bash
# Start Backend API

cd "$(dirname "$0")/../backend"
echo "🚀 Starting Backend API..."
python3 dashboard_api.py

