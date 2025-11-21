import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { TrendingUp, Users, Key, FileText, Loader2, Plus, RefreshCw, Activity, Brain, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import StatCard from '../components/StatCard'
import RecentAgents from '../components/RecentAgents'
import CreateAgentModal from '../components/CreateAgentModal'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export default function Dashboard() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const queryClient = useQueryClient()
  
  const { data: stats, isLoading, refetch: refetchStats } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const { data } = await api.get('/stats')
      return data
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })
  
  const { data: agents, refetch: refetchAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await api.get('/agents')
      return data || []
    },
    refetchInterval: 10000,
  })
  
  const handleRefresh = () => {
    refetchStats()
    refetchAgents()
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }
  
  const statCards = [
    {
      title: 'Master Agents',
      value: stats?.master_agents || 0,
      icon: Users,
      color: 'from-blue-500 to-blue-600',
      change: stats?.master_agents > 0 ? `+${stats.master_agents}` : '0',
    },
    {
      title: 'Slave Agents',
      value: stats?.slave_agents || 0,
      icon: TrendingUp,
      color: 'from-purple-500 to-purple-600',
      change: stats?.slave_agents > 0 ? `+${stats.slave_agents}` : '0',
    },
    {
      title: 'Total Keywords',
      value: stats?.total_keywords || 0,
      icon: Key,
      color: 'from-green-500 to-green-600',
      change: stats?.total_keywords > 0 ? `${stats.total_keywords}` : '0',
    },
    {
      title: 'Total Chunks',
      value: stats?.total_chunks || 0,
      icon: Brain,
      color: 'from-orange-500 to-orange-600',
      change: stats?.total_chunks > 0 ? `${stats.total_chunks}` : '0',
    },
  ]
  
  const recentAgents = agents?.slice(0, 6) || []
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header with Gradient Background */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl p-8 text-white">
        <div className="relative z-10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3">
                AI Agent Platform
              </h1>
              <p className="text-blue-100 text-lg">
                Orchestrated by <span className="font-semibold">DeepSeek</span> & <span className="font-semibold">Kimi</span>
              </p>
              <p className="text-blue-200 text-sm mt-2">
                Competitive Intelligence & SEO Analysis
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleRefresh}
                className="bg-white/20 hover:bg-white/30 backdrop-blur-sm px-4 py-2 rounded-lg flex items-center space-x-2 transition-all"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Refresh</span>
              </button>
              <button
                onClick={() => setIsModalOpen(true)}
                className="bg-white text-blue-600 hover:bg-blue-50 px-6 py-2 rounded-lg font-semibold flex items-center space-x-2 transition-all shadow-lg"
              >
                <Plus className="w-5 h-5" />
                <span>New Agent</span>
              </button>
            </div>
          </div>
        </div>
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-400/20 rounded-full blur-2xl"></div>
      </div>
      
      {/* Stats Grid - Enhanced */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 hover:shadow-xl transition-all duration-300 hover:scale-105">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.color} shadow-lg`}>
                  <stat.icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-sm font-semibold text-green-600 bg-green-50 px-3 py-1 rounded-full">
                  {stat.change}
                </span>
              </div>
              <div>
                <p className="text-3xl font-bold text-slate-900 mb-1">{stat.value.toLocaleString()}</p>
                <p className="text-sm text-slate-600 font-medium">{stat.title}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      
      {/* Recent Agents - Enhanced */}
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-1">Recent Agents</h2>
            <p className="text-slate-600">Latest AI agents created</p>
          </div>
          <Link
            to="/agents"
            className="text-blue-600 hover:text-blue-700 font-semibold flex items-center space-x-2"
          >
            <span>View All</span>
            <TrendingUp className="w-4 h-4" />
          </Link>
        </div>
        
        {recentAgents.length === 0 ? (
          <div className="text-center py-12">
            <div className="bg-slate-50 rounded-xl p-8">
              <Brain className="w-16 h-16 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-600 mb-4">No agents yet. Create your first agent to get started!</p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-primary"
              >
                Create First Agent
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentAgents.map((agent, index) => (
              <motion.div
                key={agent._id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Link to={`/agents/${agent._id}`}>
                  <div className="bg-gradient-to-br from-slate-50 to-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer">
                    <div className="flex items-start justify-between mb-3">
                      <div className={`p-2 rounded-lg ${
                        agent.agent_type === 'master'
                          ? 'bg-gradient-to-br from-blue-500 to-blue-600'
                          : 'bg-gradient-to-br from-purple-500 to-purple-600'
                      }`}>
                        <span className="text-white font-bold text-sm">
                          {agent.agent_type === 'master' ? 'M' : 'S'}
                        </span>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        agent.status === 'validated'
                          ? 'bg-green-100 text-green-700'
                          : agent.status === 'ready'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {agent.status || 'created'}
                      </span>
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2 truncate">
                      {agent.domain || 'Unknown'}
                    </h3>
                    <div className="flex items-center justify-between text-xs text-slate-600">
                      <span>{agent.chunks_indexed || 0} chunks</span>
                      <span>{agent.keyword_count || 0} keywords</span>
                      {agent.agent_type === 'master' && (
                        <span>{agent.slave_count || 0} slaves</span>
                      )}
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
      
      {/* Quick Actions - Enhanced */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <Link to="/agents" className="group">
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-200 hover:border-blue-400 transition-all cursor-pointer hover:scale-105">
            <div className="flex items-center space-x-4">
              <div className="bg-blue-500 p-4 rounded-xl group-hover:scale-110 transition-transform">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg">View All Agents</h3>
                <p className="text-sm text-slate-600">Manage {stats?.total_agents || 0} agents</p>
              </div>
            </div>
          </div>
        </Link>
        
        <Link to="/reports" className="group">
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-200 hover:border-green-400 transition-all cursor-pointer hover:scale-105">
            <div className="flex items-center space-x-4">
              <div className="bg-green-500 p-4 rounded-xl group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg">View Reports</h3>
                <p className="text-sm text-slate-600">Download CEO reports</p>
              </div>
            </div>
          </div>
        </Link>
        
        <div 
          onClick={() => setIsModalOpen(true)}
          className="group cursor-pointer"
        >
          <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-200 hover:border-purple-400 transition-all hover:scale-105">
            <div className="flex items-center space-x-4">
              <div className="bg-purple-500 p-4 rounded-xl group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg">Create Agent</h3>
                <p className="text-sm text-slate-600">Start new workflow</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Orchestrator Info */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-xl p-6 text-white">
        <div className="flex items-center space-x-4">
          <div className="bg-blue-500/20 p-3 rounded-lg">
            <Brain className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="font-bold text-lg mb-1">AI Orchestration</h3>
            <p className="text-slate-300 text-sm">
              Powered by <span className="font-semibold text-blue-400">DeepSeek</span> for competitive analysis & 
              <span className="font-semibold text-purple-400"> Kimi</span> for agent orchestration
            </p>
          </div>
        </div>
      </div>
      
      {/* Create Agent Modal */}
      <CreateAgentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  )
}
