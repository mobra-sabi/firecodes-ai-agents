# 🏢 MULTI-TENANT COMPETITIVE INTELLIGENCE PLATFORM
## Architecture & Implementation Plan

---

## 📊 **OVERVIEW**

Platform SaaS pentru Competitive Intelligence cu:
- **Multi-user support** - fiecare companie își vede doar datele sale
- **Shared infrastructure** - owner vede tot pentru analytics
- **Modern UI/UX** - Figma design system
- **Scalable architecture** - MongoDB + FastAPI + React/Vue

---

## 🏗️ **DATABASE SCHEMA**

### **1. Users Collection**
```javascript
{
  _id: ObjectId("user_id_123"),
  email: "ceo@company.com",
  password_hash: "$2b$12$...",
  full_name: "Ion Popescu",
  company_name: "Acme Construction SRL",
  company_website: "acme.ro",
  
  // Subscription
  subscription: {
    tier: "pro",  // free, starter, pro, enterprise
    started_at: ISODate("2025-01-01"),
    expires_at: ISODate("2026-01-01"),
    features: {
      max_master_agents: 5,
      max_slaves_per_master: 500,
      max_keywords: 200,
      ai_reports: true,
      api_access: true
    }
  },
  
  // Settings
  settings: {
    industry: "construction",
    language: "ro",
    timezone: "Europe/Bucharest",
    notifications: {
      email: true,
      new_competitors: true,
      weekly_reports: true
    }
  },
  
  // API
  api_key: "sk_live_abc123...",
  
  // Metadata
  created_at: ISODate(),
  last_login: ISODate(),
  status: "active"  // active, suspended, deleted
}
```

### **2. Site Agents (Modified)**
```javascript
{
  _id: ObjectId("agent_id_456"),
  user_id: ObjectId("user_id_123"), // ← USER ISOLATION
  
  domain: "example.com",
  site_url: "https://example.com",
  agent_type: "master",  // master, slave
  
  // Existing fields...
  chunks_indexed: 1084,
  has_embeddings: true,
  
  // NEW: Visibility
  visibility: "private",  // private, shared (pentru colaborare)
  
  created_at: ISODate(),
  updated_at: ISODate()
}
```

### **3. Master-Slave Relationships (Modified)**
```javascript
{
  _id: ObjectId(),
  user_id: ObjectId("user_id_123"), // ← USER ISOLATION
  
  master_id: ObjectId("master_agent_id"),
  slave_id: ObjectId("slave_agent_id"),
  
  // Existing fields...
  discovered_via: "renovare apartament",
  serp_position: 3,
  
  created_at: ISODate()
}
```

### **4. Usage Statistics (NEW)**
```javascript
{
  _id: ObjectId(),
  user_id: ObjectId("user_id_123"),
  
  period: "2025-11",  // YYYY-MM
  
  usage: {
    master_agents_created: 3,
    slave_agents_created: 127,
    keywords_searched: 45,
    google_api_calls: 450,
    deepseek_api_calls: 1200,
    ci_reports_generated: 3
  },
  
  limits: {
    master_agents_limit: 5,
    slaves_limit: 500,
    keywords_limit: 200
  },
  
  created_at: ISODate()
}
```

---

## 🔐 **AUTHENTICATION & AUTHORIZATION**

### **Backend: FastAPI + JWT**

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = verify_token(token)
    
    # Get user from DB
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Protected endpoint example
@app.get("/api/my-agents")
async def get_my_agents(current_user = Depends(get_current_user)):
    # Query only current user's agents
    agents = list(db.site_agents.find({
        "user_id": current_user["_id"]
    }))
    
    return {"agents": agents}
```

### **Frontend: Session Management**

```javascript
// Authentication state
const authStore = {
  user: null,
  token: null,
  
  async login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, password})
    });
    
    const data = await response.json();
    
    this.user = data.user;
    this.token = data.access_token;
    localStorage.setItem('auth_token', data.access_token);
    
    return data;
  },
  
  async fetchWithAuth(url, options = {}) {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.token}`
    };
    
    return fetch(url, {...options, headers});
  }
};
```

---

## 🎨 **UI/UX DESIGN - FIGMA WORKFLOW**

### **1. Design System în Figma**

```
Components:
├── Colors
│   ├── Primary: #2563eb
│   ├── Success: #10b981
│   ├── Warning: #f59e0b
│   └── Danger: #ef4444
│
├── Typography
│   ├── Headings (H1-H6)
│   ├── Body (Regular, Medium, Bold)
│   └── Code (Monospace)
│
├── Spacing
│   └── 4px, 8px, 16px, 24px, 32px, 48px
│
└── Components
    ├── Buttons (Primary, Secondary, Ghost)
    ├── Cards (Agent Card, Report Card)
    ├── Forms (Input, Select, Textarea)
    ├── Navigation (Sidebar, Header)
    ├── Tables (Agents Table, Competitors Table)
    └── Modals (Workflow Start, Settings)
```

### **2. Screens to Design**

#### **Public Pages:**
- Landing Page
- Pricing Page
- Login / Register
- Forgot Password

#### **Dashboard (Authenticated):**
- Overview Dashboard
- Master Agents List
- Agent Detail (with Slaves)
- Competitor Discovery
- CI Reports
- Settings / Profile
- Billing & Subscription

### **3. Figma → Code Workflow**

**OPTION A: Manual (BEST for production)**
```
1. Design în Figma
2. Export assets (icons, images)
3. Extract design tokens (colors, spacing)
4. Implement manual cu Tailwind CSS
5. Use Headless UI pentru components
```

**OPTION B: Figma Plugin**
```
1. Design în Figma
2. Use "Anima" or "Locofy" plugin
3. Export React/Vue components
4. Cleanup & optimize code
5. Integrate în app
```

---

## 🚀 **TECH STACK RECOMMENDATION**

### **Backend:**
```
✅ FastAPI (Python) - API server
✅ JWT - Authentication
✅ MongoDB - Database
✅ Redis - Session cache
✅ Celery - Background tasks (long workflows)
```

### **Frontend:**
```
✅ React + TypeScript - UI framework
✅ Tailwind CSS - Styling
✅ Shadcn/ui - Component library
✅ TanStack Query - Data fetching
✅ Zustand - State management
✅ React Router - Navigation
```

### **Infrastructure:**
```
✅ Docker - Containerization
✅ Nginx - Reverse proxy
✅ Cloudflare - CDN + Security
✅ MongoDB Atlas - Database hosting (optional)
```

---

## 📅 **IMPLEMENTATION PHASES**

### **PHASE 1: Core Multi-Tenant (2-3 weeks)**
- [ ] User authentication system
- [ ] MongoDB schema migration
- [ ] User isolation in API
- [ ] Basic dashboard
- [ ] User registration/login

### **PHASE 2: Design System (1-2 weeks)**
- [ ] Figma design system
- [ ] Component library
- [ ] Responsive layouts
- [ ] Dark mode support
- [ ] Brand identity

### **PHASE 3: Dashboard Features (3-4 weeks)**
- [ ] Master agents management
- [ ] Workflow launcher
- [ ] Live progress tracking
- [ ] CI reports viewer
- [ ] Competitor analysis

### **PHASE 4: Advanced Features (2-3 weeks)**
- [ ] Subscription tiers
- [ ] Billing integration (Stripe)
- [ ] Usage analytics
- [ ] API access
- [ ] Team collaboration

### **PHASE 5: Polish & Launch (1-2 weeks)**
- [ ] Testing
- [ ] Documentation
- [ ] Marketing site
- [ ] Beta users
- [ ] Launch! 🚀

---

## 💰 **MONETIZATION MODELS**

### **Subscription Tiers:**

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Master Agents | 1 | 3 | 10 | Unlimited |
| Slaves per Master | 50 | 150 | 500 | Unlimited |
| Keywords | 20 | 60 | 200 | Unlimited |
| CI Reports | ❌ | Basic | Advanced | Custom |
| API Access | ❌ | ❌ | ✅ | ✅ |
| White Label | ❌ | ❌ | ❌ | ✅ |
| **Price/month** | **$0** | **$49** | **$199** | **$999+** |

---

## 🔧 **OWNER ADMIN PANEL**

### **Super Admin Features:**
```
Dashboard:
├── Total Users: 1,247
├── Active Subscriptions: 892
├── MRR: $87,341
├── Churn Rate: 2.3%
│
Users Management:
├── View all users
├── Search & filter
├── Edit subscriptions
├── View usage stats
├── Suspend/delete accounts
│
Analytics:
├── Revenue charts
├── User growth
├── Feature usage
├── API usage
├── System health
│
System:
├── Database stats
├── API performance
├── Background jobs
└── Error logs
```

---

## 🎯 **NEXT STEPS**

### **Immediate (This Week):**
1. ✅ Finish current workflow (279 slaves)
2. Create Figma account & design system
3. Design 3 core screens (Login, Dashboard, Agent Detail)
4. Implement user authentication backend

### **Short Term (This Month):**
1. Complete UI design în Figma
2. Implement multi-tenant backend
3. Build React dashboard
4. Beta testing cu 5-10 users

### **Long Term (3 Months):**
1. Launch public beta
2. Stripe integration
3. Marketing & growth
4. Scale infrastructure

---

## 📞 **RESOURCES & TOOLS**

### **Design:**
- **Figma:** https://figma.com (Free pentru design)
- **Tailwind UI:** https://tailwindui.com ($299 one-time)
- **Shadcn/ui:** https://ui.shadcn.com (Free, open source)
- **Heroicons:** https://heroicons.com (Free icons)

### **Authentication:**
- **Auth0:** https://auth0.com (Managed auth)
- **Supabase Auth:** https://supabase.com (Open source)
- **Custom JWT:** DIY (Full control)

### **Billing:**
- **Stripe:** https://stripe.com (Best for SaaS)
- **Paddle:** https://paddle.com (Alternative)

### **Hosting:**
- **DigitalOcean:** $5-20/month (Start small)
- **Hetzner:** $4-10/month (Cheap, powerful)
- **AWS/GCP:** Pay as you go (Enterprise)

---

## 💡 **PRO TIPS**

1. **Start cu MVP minimal:**
   - 1 user type (no teams)
   - 1 subscription tier
   - Core features only
   - Launch fast, iterate

2. **Use existing solutions:**
   - Tailwind + Shadcn (no need to design everything)
   - Supabase or Auth0 (no need to build auth)
   - Stripe (no need to build billing)

3. **Focus pe value:**
   - Features care diferențiază
   - UX extraordinar
   - Speed & reliability
   - Customer support

4. **Analytics from day 1:**
   - Track everything
   - User behavior
   - Feature usage
   - Conversion funnels

---

## 🎊 **CONCLUSION**

**Da, Figma + Multi-tenant = Perfect match!**

Arhitectura e standard SaaS, scalabilă și profesională.
Start cu Figma design, apoi implement gradual.

**Next:** Design 3 screens în Figma și implementăm autentificarea? 🚀

