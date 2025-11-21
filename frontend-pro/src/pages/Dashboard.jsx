import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bot, Users, Hash, TrendingUp, Plus } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const Dashboard = () => {
  // Fetch dashboard stats
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const response = await api.get('/stats')
      console.log('Dashboard stats response:', response.data)
      return response.data
    },
    retry: 2,
    refetchOnWindowFocus: true,
  })

  // Debug logging
  console.log('Dashboard - stats:', stats, 'isLoading:', isLoading, 'error:', error)

  const kpiCards = [
    {
      title: 'Master Agents',
      value: stats?.master_agents ?? 0,
      icon: Bot,
      color: 'blue',
      link: '/agents?type=master',
    },
    {
      title: 'Slave Agents',
      value: stats?.slave_agents ?? 0,
      icon: Users,
      color: 'purple',
      link: '/agents?type=slave',
    },
    {
      title: 'Total Keywords',
      value: stats?.total_keywords ?? 0,
      icon: Hash,
      color: 'green',
      link: '/intelligence',
    },
    {
      title: 'Total Agents',
      value: stats?.total_agents ?? 0,
      icon: TrendingUp,
      color: 'yellow',
      link: '/agents',
    },
  ]

  const colorClasses = {
    blue: 'from-accent-blue to-blue-600',
    purple: 'from-accent-purple to-purple-600',
    green: 'from-accent-green to-green-600',
    yellow: 'from-accent-yellow to-yellow-600',
  }

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-primary-700 rounded w-1/4 mb-8"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-primary-700 rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-text-muted mt-1">Welcome back! Here's your overview.</p>
        </div>
        <Card>
          <Card.Body className="p-6">
            <div className="text-center">
              <p className="text-red-400 mb-2">Error loading dashboard stats</p>
              <p className="text-text-muted text-sm">{error.message}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          </Card.Body>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-text-muted mt-1">Welcome back! Here's your overview.</p>
        </div>
        <Link to="/agents/new">
          <Button icon={<Plus className="w-5 h-5" />}>
            New Master Agent
          </Button>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((card) => (
          <Link key={card.title} to={card.link}>
            <Card hover className="h-full">
              <Card.Body className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-muted text-sm font-medium">{card.title}</p>
                    <p className="text-3xl font-bold text-text-primary mt-2">
                      {(card.value ?? 0).toLocaleString()}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg bg-gradient-to-br ${colorClasses[card.color]}`}>
                    <card.icon className="w-6 h-6 text-white" />
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <Card.Header>
          <Card.Title>Quick Actions</Card.Title>
        </Card.Header>
        <Card.Body>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link to="/agents/new">
              <div className="p-4 border-2 border-dashed border-primary-600 rounded-lg hover:border-accent-blue transition-colors">
                <Plus className="w-8 h-8 text-accent-blue mx-auto mb-2" />
                <p className="text-center font-medium text-text-primary">Create New Agent</p>
                <p className="text-center text-sm text-text-muted mt-1">Start competitive analysis</p>
              </div>
            </Link>
            <Link to="/intelligence">
              <div className="p-4 border-2 border-dashed border-primary-600 rounded-lg hover:border-accent-blue transition-colors">
                <TrendingUp className="w-8 h-8 text-accent-blue mx-auto mb-2" />
                <p className="text-center font-medium text-text-primary">View Intelligence</p>
                <p className="text-center text-sm text-text-muted mt-1">Competitive insights</p>
              </div>
            </Link>
            <Link to="/reports">
              <div className="p-4 border-2 border-dashed border-primary-600 rounded-lg hover:border-accent-blue transition-colors">
                <Bot className="w-8 h-8 text-accent-blue mx-auto mb-2" />
                <p className="text-center font-medium text-text-primary">SEO Reports</p>
                <p className="text-center text-sm text-text-muted mt-1">Strategic analysis</p>
              </div>
            </Link>
          </div>
        </Card.Body>
      </Card>

      {/* Activity Feed (placeholder) */}
      <Card>
        <Card.Header>
          <Card.Title>Recent Activity</Card.Title>
        </Card.Header>
        <Card.Body>
          <div className="space-y-4">
            <p className="text-text-muted text-center py-8">
              No recent activity. Create your first agent to get started!
            </p>
          </div>
        </Card.Body>
      </Card>
    </div>
  )
}

export default Dashboard

