#!/bin/bash
##################################################
# 🚀 AI AGENT PLATFORM - MVP AUTO-INSTALLER
# Installs and configures the complete multi-tenant MVP
##################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  🚀 AI AGENT PLATFORM - MVP INSTALLER                         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Main installation
print_header

# Step 1: Check Node.js
print_step "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js not found! Please install Node.js 18+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    print_error "Node.js version too old (need 16+, have $NODE_VERSION)"
    exit 1
fi

print_success "Node.js $(node -v) found"

# Step 2: Check Python
print_step "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 not found!"
    exit 1
fi

print_success "Python3 $(python3 --version) found"

# Step 3: Check MongoDB
print_step "Checking MongoDB connection..."
if ! python3 -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000).admin.command('ping')" 2>/dev/null; then
    print_error "Cannot connect to MongoDB on localhost:27017"
    echo "   Please ensure MongoDB is running"
    exit 1
fi

print_success "MongoDB connection OK"

# Step 4: Install Python dependencies
print_step "Installing Python dependencies..."
pip install -q pyjwt bcrypt python-multipart 2>/dev/null || {
    print_error "Failed to install Python packages"
    exit 1
}
print_success "Python packages installed"

# Step 5: Install Frontend dependencies
print_step "Installing Frontend dependencies..."
cd /srv/hf/ai_agents/frontend

if [ ! -f "package.json" ]; then
    print_error "package.json not found! Are you in the right directory?"
    exit 1
fi

npm install --silent --no-progress 2>&1 | grep -v "npm WARN" || true
print_success "Frontend dependencies installed"

# Step 6: Create admin user
print_step "Creating admin user..."

python3 << 'PYEOF'
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timezone

try:
    mongo = MongoClient('mongodb://localhost:27017/')
    db = mongo.ai_agents_db
    
    # Check if admin already exists
    existing = db.users.find_one({"email": "admin@example.com"})
    if existing:
        print("   Admin user already exists, skipping...")
    else:
        password = "admin123"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin = {
            "email": "admin@example.com",
            "password_hash": hashed,
            "company_name": "Admin",
            "industry": "All Industries",
            "role": "admin",
            "created_at": datetime.now(timezone.utc),
            "subscription": {
                "plan": "enterprise",
                "agents_limit": 99999,
                "expires_at": None
            }
        }
        
        db.users.insert_one(admin)
        print("   Created admin user")
except Exception as e:
    print(f"   Error: {e}")
    exit(1)
PYEOF

print_success "Admin user ready"

# Step 7: Run migration (add user_id to existing agents)
print_step "Running database migration..."

python3 << 'PYEOF'
from pymongo import MongoClient
from bson import ObjectId

try:
    mongo = MongoClient('mongodb://localhost:27017/')
    db = mongo.ai_agents_db
    
    # Get admin user
    admin = db.users.find_one({"role": "admin"})
    if admin:
        admin_id = admin["_id"]
        
        # Update agents
        result1 = db.site_agents.update_many(
            {"user_id": {"$exists": False}},
            {"$set": {"user_id": admin_id}}
        )
        
        # Update reports
        result2 = db.competitor_discovery_reports.update_many(
            {"user_id": {"$exists": False}},
            {"$set": {"user_id": admin_id}}
        )
        
        print(f"   Updated {result1.modified_count} agents, {result2.modified_count} reports")
    else:
        print("   No admin user found, skipping migration")
except Exception as e:
    print(f"   Warning: {e}")
PYEOF

print_success "Migration complete"

# Step 8: Create startup scripts
print_step "Creating startup scripts..."

cd /srv/hf/ai_agents

# Auth API startup script
cat > start_auth_api.sh << 'EOF'
#!/bin/bash
cd /srv/hf/ai_agents
echo "🔐 Starting Auth API on port 5001..."
python3 auth_api.py
EOF

chmod +x start_auth_api.sh

# Frontend startup script
cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd /srv/hf/ai_agents/frontend
echo "⚛️  Starting Frontend on port 3000..."
npm run dev
EOF

chmod +x start_frontend.sh

# Combined startup script
cat > start_mvp.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting AI Agent Platform MVP..."
echo ""

# Start Auth API in background
cd /srv/hf/ai_agents
python3 auth_api.py > /tmp/auth_api.log 2>&1 &
AUTH_PID=$!
echo "✅ Auth API started (PID: $AUTH_PID, Log: /tmp/auth_api.log)"

# Wait for auth API to start
sleep 2

# Start Frontend
cd /srv/hf/ai_agents/frontend
echo "✅ Starting Frontend..."
echo ""
npm run dev

# Cleanup on exit
trap "kill $AUTH_PID" EXIT
EOF

chmod +x start_mvp.sh

print_success "Startup scripts created"

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ INSTALLATION COMPLETE!                                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📋 Quick Start:${NC}"
echo ""
echo -e "  ${YELLOW}1. Start the platform:${NC}"
echo -e "     cd /srv/hf/ai_agents"
echo -e "     ./start_mvp.sh"
echo ""
echo -e "  ${YELLOW}2. Open browser:${NC}"
echo -e "     http://localhost:3000"
echo ""
echo -e "  ${YELLOW}3. Login with:${NC}"
echo -e "     Email:    admin@example.com"
echo -e "     Password: admin123"
echo ""

echo -e "${BLUE}📁 Documentation:${NC}"
echo ""
echo "  • Quick Start:   /srv/hf/ai_agents/MULTI_TENANT_MVP_README.md"
echo "  • Frontend:      /srv/hf/ai_agents/frontend/README.md"
echo "  • Design System: /srv/hf/ai_agents/FIGMA_DESIGN_TEMPLATES.md"
echo "  • Summary:       /srv/hf/ai_agents/MVP_CREATION_SUMMARY.md"
echo ""

echo -e "${BLUE}🛠️  Individual Scripts:${NC}"
echo ""
echo "  • ./start_auth_api.sh  - Start auth API only"
echo "  • ./start_frontend.sh  - Start frontend only"
echo "  • ./start_mvp.sh       - Start everything (recommended)"
echo ""

echo -e "${GREEN}🎉 Ready to launch! Run: ./start_mvp.sh${NC}"
echo ""

