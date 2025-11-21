import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import { Users, Bot, TrendingUp, FileText, Plus, Activity } from 'lucide-react'

export default function DashboardPage() {
  // Fetch dashboard stats
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await api.get('/stats')
      return response.data
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const statCards = [
    {
      title: 'Master Agents',
      value: stats?.master_agents || 0,
      icon: Bot,
      color: 'bg-blue-500',
      link: '/agents',
    },
    {
      title: 'Slave Agents',
      value: stats?.slave_agents || 0,
      icon: Users,
      color: 'bg-purple-500',
    },
    {
      title: 'Total Keywords',
      value: stats?.total_keywords || 0,
      icon: TrendingUp,
      color: 'bg-green-500',
    },
    {
      title: 'CI Reports',
      value: stats?.reports || 0,
      icon: FileText,
      color: 'bg-orange-500',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900">Dashboard</h1>
          <p className="text-dark-600 mt-1">
            Welcome back! Here's what's happening with your AI agents.
          </p>
        </div>
        <Link to="/agents" className="btn btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Master Agent
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.title} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-dark-600 font-medium">{stat.title}</p>
                  <p className="text-3xl font-bold text-dark-900 mt-2">
                    {isLoading ? '...' : stat.value.toLocaleString()}
                  </p>
                </div>
                <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
              {stat.link && (
                <Link
                  to={stat.link}
                  className="text-sm text-primary-600 hover:text-primary-700 font-medium mt-4 inline-block"
                >
                  View all →
                </Link>
              )}
            </div>
          )
        })}
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-dark-900">Recent Workflows</h2>
          <Activity className="w-5 h-5 text-dark-400" />
        </div>
        
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-dark-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : stats?.recent_workflows?.length > 0 ? (
          <div className="space-y-4">
            {stats.recent_workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="flex items-center justify-between p-4 bg-dark-50 rounded-lg hover:bg-dark-100 transition-colors"
              >
                <div>
                  <h3 className="font-medium text-dark-900">{workflow.domain}</h3>
                  <p className="text-sm text-dark-600 mt-1">
                    {workflow.status === 'completed' && `✅ Completed`}
                    {workflow.status === 'running' && `⏳ In Progress (${workflow.progress}%)`}
                    {workflow.status === 'failed' && `❌ Failed`}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-dark-600">
                    {workflow.slaves_created || 0} slaves
                  </p>
                  <p className="text-xs text-dark-500 mt-1">
                    {new Date(workflow.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 text-dark-300 mx-auto mb-3" />
            <p className="text-dark-600">No workflows yet</p>
            <Link to="/agents" className="text-primary-600 hover:text-primary-700 font-medium text-sm mt-2 inline-block">
              Create your first master agent
            </Link>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <h3 className="font-semibold text-dark-900 mb-2">📚 Documentation</h3>
          <p className="text-sm text-dark-600 mb-4">
            Learn how to create and manage AI agents
          </p>
          <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Read docs →
          </a>
        </div>

        <div className="card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <h3 className="font-semibold text-dark-900 mb-2">🎯 Best Practices</h3>
          <p className="text-sm text-dark-600 mb-4">
            Tips for effective competitive intelligence
          </p>
          <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Learn more →
          </a>
        </div>

        <div className="card bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <h3 className="font-semibold text-dark-900 mb-2">💬 Get Support</h3>
          <p className="text-sm text-dark-600 mb-4">
            Need help? Our team is here for you
          </p>
          <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Contact us →
          </a>
        </div>
      </div>
    </div>
  )
}

