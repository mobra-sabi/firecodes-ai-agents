import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Bot, LayoutDashboard, Users, Activity, LogOut, User, ChevronDown } from 'lucide-react'
import { useState } from 'react'

export default function DashboardLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/agents', label: 'Master Agents', icon: Users },
  ]

  const isActivePath = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <div className="min-h-screen bg-dark-50">
      {/* Header */}
      <header className="bg-white border-b border-dark-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-dark-900">AI Agent Platform</h1>
                <p className="text-xs text-dark-500">Competitive Intelligence</p>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = isActivePath(item.path)
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700 font-medium'
                        : 'text-dark-600 hover:bg-dark-100'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                )
              })}
            </nav>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-dark-100 transition-colors"
              >
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-primary-700" />
                </div>
                <div className="hidden sm:block text-left">
                  <p className="text-sm font-medium text-dark-900">{user?.email || 'User'}</p>
                  <p className="text-xs text-dark-500">{user?.company_name || 'Company'}</p>
                </div>
                <ChevronDown className={`w-4 h-4 text-dark-500 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
              </button>

              {showUserMenu && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-dark-200 py-1 z-50">
                    <div className="px-4 py-3 border-b border-dark-200">
                      <p className="text-sm font-medium text-dark-900">{user?.email}</p>
                      <p className="text-xs text-dark-500 mt-0.5">{user?.company_name}</p>
                      <p className="text-xs text-dark-400 mt-1">
                        Industry: {user?.industry || 'Not set'}
                      </p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-200 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-dark-600">
              © 2025 AI Agent Platform. All rights reserved.
            </p>
            <div className="flex items-center gap-4 text-sm text-dark-600">
              <a href="#" className="hover:text-primary-600 transition-colors">Documentation</a>
              <a href="#" className="hover:text-primary-600 transition-colors">Support</a>
              <a href="#" className="hover:text-primary-600 transition-colors">API</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

