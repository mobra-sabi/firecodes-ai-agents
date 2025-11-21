import { Link, useLocation } from 'react-router-dom'
import { Brain, LayoutDashboard, Users, FileText } from 'lucide-react'

export default function Layout({ children }) {
  const location = useLocation()
  
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/agents', icon: Users, label: 'Agents' },
    { path: '/reports', icon: FileText, label: 'Reports' },
  ]
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-lg border-b border-slate-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between h-auto sm:h-16 py-3 sm:py-0 gap-3 sm:gap-0">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg">
                <Brain className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  AI Agent Platform
                </h1>
                <p className="text-xs text-slate-500 hidden sm:block">Competitive Intelligence</p>
              </div>
            </div>
            
            <nav className="flex flex-wrap gap-1 sm:gap-0 sm:flex-nowrap w-full sm:w-auto">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg transition-all duration-200 text-sm sm:text-base ${
                      isActive
                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                )
              })}
            </nav>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}

