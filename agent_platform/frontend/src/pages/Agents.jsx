import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Plus, Search, Loader2, Play, FileText, Trash2 } from 'lucide-react'
import api from '../lib/api'
import { useState } from 'react'
import CreateAgentModal from '../components/CreateAgentModal'

export default function Agents() {
  const [searchTerm, setSearchTerm] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [filterType, setFilterType] = useState('all') // all, master, slave
  
  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await api.get('/agents')
      return data
    },
    refetchInterval: 30000,
  })
  
  const filteredAgents = agents?.filter(agent => {
    const matchesSearch = agent.domain?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = filterType === 'all' || agent.agent_type === filterType
    return matchesSearch && matchesType
  }) || []
  
  const handleStartWorkflow = async (agentId) => {
    try {
      await api.post(`/workflow/start`, { agent_id: agentId })
      alert('Workflow started! Check progress in agent details.')
    } catch (err) {
      alert('Failed to start workflow: ' + (err.response?.data?.error || err.message))
    }
  }
  
  const handleGenerateReport = async (agentId) => {
    try {
      const { data } = await api.post(`/api/reports/generate/${agentId}`)
      alert('Report generated! Check Reports page.')
      window.location.href = '/reports'
    } catch (err) {
      alert('Failed to generate report: ' + (err.response?.data?.error || err.message))
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }
  
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            Agents
          </h1>
          <p className="text-sm sm:text-base text-slate-600">Manage and monitor your AI agents</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="btn-primary flex items-center space-x-2 w-full sm:w-auto justify-center sm:justify-start"
        >
          <Plus className="w-4 h-4 sm:w-5 sm:h-5" />
          <span className="text-sm sm:text-base">New Master Agent</span>
        </button>
      </div>
      
      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterType('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterType === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilterType('master')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterType === 'master'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            Master
          </button>
          <button
            onClick={() => setFilterType('slave')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterType === 'slave'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            Slave
          </button>
        </div>
      </div>
      
      {/* Agents Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {filteredAgents.map((agent, index) => (
          <motion.div
            key={agent._id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <div className="card group">
              <div className="flex items-start justify-between mb-4">
                <Link to={`/agents/${agent._id}`} className="flex-1">
                  <div className={`p-3 rounded-lg inline-block ${
                    agent.agent_type === 'master'
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600'
                      : 'bg-gradient-to-br from-purple-500 to-purple-600'
                  }`}>
                    <span className="text-white font-bold">
                      {agent.agent_type === 'master' ? 'M' : 'S'}
                    </span>
                  </div>
                </Link>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  agent.status === 'validated'
                    ? 'bg-green-100 text-green-700'
                    : agent.status === 'created'
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {agent.status || 'unknown'}
                </span>
              </div>
              
              <Link to={`/agents/${agent._id}`}>
                <h3 className="text-lg font-bold text-slate-900 mb-2 hover:text-blue-600 transition-colors">
                  {agent.domain || 'Unknown'}
                </h3>
              </Link>
              
              <div className="space-y-2 text-sm text-slate-600 mb-4">
                <div className="flex justify-between">
                  <span>Chunks:</span>
                  <span className="font-semibold">{agent.chunks_indexed || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Keywords:</span>
                  <span className="font-semibold">{agent.keyword_count || 0}</span>
                </div>
                {agent.agent_type === 'master' && (
                  <div className="flex justify-between">
                    <span>Slaves:</span>
                    <span className="font-semibold">{agent.slave_count || 0}</span>
                  </div>
                )}
              </div>
              
              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-200">
                <Link
                  to={`/agents/${agent._id}`}
                  className="flex-1 px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-xs sm:text-sm font-medium text-slate-700 transition-colors text-center"
                >
                  View
                </Link>
                {agent.agent_type === 'master' && agent.status === 'validated' && (
                  <>
                    <button
                      onClick={() => handleStartWorkflow(agent._id)}
                      className="flex-1 px-3 py-2 bg-blue-100 hover:bg-blue-200 rounded-lg text-xs sm:text-sm font-medium text-blue-700 transition-colors flex items-center justify-center space-x-1"
                      title="Start CEO Workflow"
                    >
                      <Play className="w-3 h-3" />
                      <span>Workflow</span>
                    </button>
                    <button
                      onClick={() => handleGenerateReport(agent._id)}
                      className="flex-1 px-3 py-2 bg-green-100 hover:bg-green-200 rounded-lg text-xs sm:text-sm font-medium text-green-700 transition-colors flex items-center justify-center space-x-1"
                      title="Generate Report"
                    >
                      <FileText className="w-3 h-3" />
                      <span>Report</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      
      {filteredAgents.length === 0 && (
        <div className="text-center py-12">
          <div className="bg-slate-50 rounded-xl p-8 max-w-md mx-auto">
            <p className="text-slate-600 mb-2">
              {searchTerm || filterType !== 'all'
                ? `No agents found matching "${searchTerm}" ${filterType !== 'all' ? `(${filterType})` : ''}`
                : 'No agents found. Create your first agent to get started!'}
            </p>
            {!searchTerm && filterType === 'all' && (
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-primary mt-4"
              >
                Create First Agent
              </button>
            )}
          </div>
        </div>
      )}
      
      {/* Create Agent Modal */}
      <CreateAgentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  )
}

