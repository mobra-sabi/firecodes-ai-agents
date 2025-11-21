# 🚀 AI Agent Platform - Frontend

Modern React frontend for the AI Agent Platform with competitive intelligence capabilities.

## 🛠️ Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool & dev server
- **React Router v6** - Routing
- **TanStack Query** - Data fetching & caching
- **Zustand** - State management
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Axios** - HTTP client

## 📦 Installation

### Prerequisites

- Node.js 18+ or npm/yarn/pnpm

### Setup

```bash
# Navigate to frontend directory
cd /srv/hf/ai_agents/frontend

# Install dependencies
npm install
# or
yarn install
```

## 🚀 Development

```bash
# Start dev server (with hot reload)
npm run dev

# Server will start on http://0.0.0.0:3000
```

The dev server includes:
- ⚡ Hot Module Replacement (HMR)
- 🔄 API proxy to backend (localhost:5000)
- 📱 Mobile-responsive preview

## 🏗️ Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── App.jsx                 # Main app with routing
│   ├── main.jsx                # Entry point
│   ├── index.css               # Global styles + Tailwind
│   ├── layouts/
│   │   └── DashboardLayout.jsx # Main layout with header/nav
│   ├── pages/
│   │   ├── LoginPage.jsx       # Authentication
│   │   ├── RegisterPage.jsx
│   │   ├── DashboardPage.jsx   # Main dashboard
│   │   ├── MasterAgentsPage.jsx
│   │   ├── AgentDetailPage.jsx
│   │   └── WorkflowProgressPage.jsx
│   ├── stores/
│   │   └── authStore.js        # Auth state management
│   └── lib/
│       ├── api.js              # Axios instance
│       └── cn.js               # Utility functions
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## 🎨 Design System

### Colors

- **Primary**: Blue shades (`primary-*`)
- **Dark**: Gray shades (`dark-*`)
- **Status**: Green (success), Yellow (warning), Red (error)

### Components

All components use Tailwind CSS utility classes with custom component classes:

- `.btn` - Base button styles
- `.btn-primary`, `.btn-secondary`, `.btn-outline` - Button variants
- `.card` - Card container
- `.input` - Form input
- `.badge` - Status badges

### Typography

- **Font**: Inter (sans-serif)
- **Mono**: JetBrains Mono

## 🔐 Authentication

The app uses JWT-based authentication:

1. User registers/logs in via `/auth/register` or `/auth/login`
2. JWT token stored in localStorage (via Zustand persist)
3. Token automatically included in all API requests
4. Protected routes redirect to login if not authenticated

## 🔌 API Integration

### Base Configuration

```javascript
// API base URL is proxied by Vite
const API_BASE = '/api'  // → http://localhost:5000/api

// All requests automatically include Authorization header
api.defaults.headers.common['Authorization'] = `Bearer ${token}`
```

### Key Endpoints

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user
- `GET /agents` - List agents (filtered by user)
- `POST /workflow/start` - Start new workflow
- `GET /stats` - Dashboard statistics

## 📱 Responsive Design

The app is fully responsive:
- **Mobile**: < 768px (stacked layout)
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 🎯 Key Features

### 1. Dashboard
- Real-time statistics
- Recent workflow activity
- Quick actions

### 2. Master Agents
- List all master agents
- Search & filter
- Create new agents
- View agent details

### 3. Agent Details
- Master-slave organogram
- Competitive intelligence
- Keyword tracking
- Slave agent list

### 4. Live Workflow
- Real-time progress tracking
- Phase-by-phase updates
- GPU & resource monitoring

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:5000
```

### Proxy Configuration

In `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    },
  },
}
```

## 🚀 Deployment

### Build & Deploy

```bash
# Build
npm run build

# Output: dist/ folder

# Deploy to static hosting (Vercel, Netlify, etc.)
# or serve with nginx/apache
```

### Cloudflare Tunnel (Development)

```bash
# In another terminal
cloudflared tunnel --url http://localhost:3000
```

## 🐛 Troubleshooting

### API Connection Issues

1. Check backend is running on port 5000
2. Verify proxy configuration in `vite.config.js`
3. Check browser console for CORS errors

### Authentication Issues

1. Clear localStorage: `localStorage.clear()`
2. Check JWT token expiration
3. Verify backend auth endpoints are working

### Build Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📚 Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [TanStack Query](https://tanstack.com/query/)
- [Zustand](https://zustand-demo.pmnd.rs/)

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test locally
4. Submit for review

## 📄 License

Proprietary - All rights reserved

