import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import { Plus, Search, Bot, Users, Hash, Calendar, ExternalLink, Loader2 } from 'lucide-react'

export default function MasterAgentsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch master agents
  const { data: agents, isLoading } = useQuery({
    queryKey: ['master-agents'],
    queryFn: async () => {
      const response = await api.get('/agents?type=master')
      return response.data
    },
    refetchInterval: 30000,
  })

  const filteredAgents = agents?.filter((agent) =>
    agent.domain?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-dark-900">Master Agents</h1>
          <p className="text-dark-600 mt-1">
            Manage your AI agents and their competitive intelligence
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Master Agent
        </button>
      </div>

      {/* Search Bar */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-dark-400" />
          <input
            type="text"
            placeholder="Search agents by domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Agents Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card h-64 bg-dark-100 animate-pulse" />
          ))}
        </div>
      ) : filteredAgents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <AgentCard key={agent._id} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <Bot className="w-16 h-16 text-dark-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-dark-900 mb-2">
            {searchQuery ? 'No agents found' : 'No master agents yet'}
          </h3>
          <p className="text-dark-600 mb-6">
            {searchQuery
              ? 'Try a different search query'
              : 'Create your first master agent to start competitive intelligence'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create Master Agent
            </button>
          )}
        </div>
      )}

      {/* Create Agent Modal */}
      {showCreateModal && (
        <CreateAgentModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}

function AgentCard({ agent }) {
  const statusConfig = {
    active: { badge: 'badge-success', text: '✅ Active' },
    processing: { badge: 'badge-warning', text: '⏳ Processing' },
    failed: { badge: 'badge-error', text: '❌ Failed' },
  }

  const status = statusConfig[agent.status] || statusConfig.active

  return (
    <Link
      to={`/agents/${agent._id}`}
      className="card hover:shadow-lg transition-all group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-dark-900 group-hover:text-primary-600 transition-colors flex items-center gap-2">
            {agent.domain}
            <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>
          <p className="text-sm text-dark-600 mt-1">{agent.industry || 'Industry'}</p>
        </div>
        <span className={`badge ${status.badge}`}>{status.text}</span>
      </div>

      <div className="space-y-3 mb-4">
        <div className="flex items-center gap-2 text-sm text-dark-600">
          <Users className="w-4 h-4" />
          <span>{agent.slave_count || 0} slave agents</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-dark-600">
          <Hash className="w-4 h-4" />
          <span>{agent.keyword_count || 0} keywords tracked</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-dark-600">
          <Bot className="w-4 h-4" />
          <span>{agent.chunks_indexed || 0} chunks indexed</span>
        </div>
      </div>

      <div className="pt-4 border-t border-dark-200 flex items-center justify-between">
        <div className="flex items-center gap-1 text-xs text-dark-500">
          <Calendar className="w-3 h-3" />
          {agent.created_at
            ? new Date(agent.created_at).toLocaleDateString()
            : 'Recently'}
        </div>
        <span className="text-sm text-primary-600 group-hover:text-primary-700 font-medium">
          View details →
        </span>
      </div>
    </Link>
  )
}

function CreateAgentModal({ onClose }) {
  const [url, setUrl] = useState('')
  const [industry, setIndustry] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsCreating(true)
    
    try {
      await api.post('/agents', {
        site_url: url,
        industry: industry,
      })
      
      // Show success message
      alert('Agent creation started! The workflow will run in background. Refresh the page in a few minutes to see the new agent.')
      
      // Close modal and refresh page
      onClose()
      setTimeout(() => window.location.reload(), 2000)
    } catch (error) {
      alert('Failed to create agent: ' + (error.response?.data?.detail || error.message))
      setIsCreating(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50" onClick={onClose} />
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="card max-w-md w-full">
          <h2 className="text-2xl font-bold text-dark-900 mb-4">Create Master Agent</h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-700 mb-1">
                Website URL *
              </label>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="input"
                placeholder="https://example.com"
                disabled={isCreating}
              />
              <p className="text-xs text-dark-500 mt-1">
                The website to create a master agent for
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-700 mb-1">
                Industry *
              </label>
              <input
                type="text"
                required
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="input"
                placeholder="e.g., Construction, SaaS, E-commerce"
                disabled={isCreating}
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="btn btn-secondary flex-1"
                disabled={isCreating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary flex-1 flex items-center justify-center gap-2"
                disabled={isCreating}
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Agent'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}

