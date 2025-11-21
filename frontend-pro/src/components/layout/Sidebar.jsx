import { NavLink } from 'react-router-dom'
import { Home, Bot, BarChart3, FileText, Settings, LogOut, Activity, Server, Brain, Zap, Bell, Network, DollarSign, ListChecks, Building2, Sparkles } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { cn } from '@/utils/cn'

const Sidebar = () => {
  const { user, logout } = useAuthStore()

  const navItems = [
    { to: '/', icon: Home, label: 'Dashboard' },
    { to: '/agents', icon: Bot, label: 'Master Agents' },
    { to: '/task-ai', icon: Sparkles, label: 'Task AI Agent' },
    { to: '/workflows', icon: Activity, label: 'Workflows' },
    { to: '/workflow-tracker', icon: ListChecks, label: 'Workflow Tracker' },
    { to: '/actions', icon: Zap, label: 'Actions Queue' },
    { to: '/alerts', icon: Bell, label: 'Alerts Center' },
    { to: '/graph', icon: Network, label: 'Org Graph' },
    { to: '/ads', icon: DollarSign, label: 'Google Ads' },
    { to: '/control-center', icon: Server, label: 'Control Center' },
    { to: '/learning', icon: Brain, label: 'Learning Center' },
    { to: '/intelligence', icon: BarChart3, label: 'Intelligence' },
    { to: '/reports', icon: FileText, label: 'Reports' },
    { to: '/industry', icon: Building2, label: 'Industry Transform' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="w-64 min-h-screen bg-primary-800 border-r border-primary-600 flex flex-col">
      {/* Logo/Brand */}
      <div className="px-6 py-6 border-b border-primary-600">
        <h1 className="text-2xl font-bold text-gradient">AI Agents</h1>
        <p className="text-sm text-text-muted mt-1">Competitive Intelligence</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-accent-blue text-white shadow-glow-blue'
                  : 'text-text-secondary hover:text-text-primary hover:bg-primary-700'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Profile */}
      <div className="px-4 py-4 border-t border-primary-600">
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-primary-700">
          <div className="w-10 h-10 rounded-full bg-accent-blue flex items-center justify-center text-white font-semibold">
            {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">
              {user?.full_name || 'User'}
            </p>
            <p className="text-xs text-text-muted truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full mt-2 flex items-center gap-2 px-4 py-2 rounded-lg text-text-secondary hover:text-accent-red hover:bg-primary-700 transition-all duration-200"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </div>
  )
}

export default Sidebar

