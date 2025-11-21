import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Users, Hash, Bot, TrendingUp, ExternalLink, Loader2 } from 'lucide-react'

export default function AgentDetailPage() {
  const { agentId } = useParams()

  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}`)
      return response.data
    },
  })

  const { data: slaves } = useQuery({
    queryKey: ['agent-slaves', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/slaves`)
      return response.data
    },
    enabled: !!agent,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="card text-center py-16">
        <h3 className="text-lg font-semibold text-dark-900">Agent not found</h3>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-dark-900">{agent.domain}</h1>
              <a
                href={`https://${agent.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700"
              >
                <ExternalLink className="w-5 h-5" />
              </a>
            </div>
            <p className="text-dark-600">{agent.industry || 'Industry not specified'}</p>
          </div>
          <span className="badge badge-success">✅ Active</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div>
            <p className="text-sm text-dark-600 mb-1">Chunks Indexed</p>
            <p className="text-2xl font-bold text-dark-900">{agent.chunks_indexed || 0}</p>
          </div>
          <div>
            <p className="text-sm text-dark-600 mb-1">Slave Agents</p>
            <p className="text-2xl font-bold text-dark-900">{slaves?.length || 0}</p>
          </div>
          <div>
            <p className="text-sm text-dark-600 mb-1">Keywords</p>
            <p className="text-2xl font-bold text-dark-900">{agent.keyword_count || 0}</p>
          </div>
          <div>
            <p className="text-sm text-dark-600 mb-1">Created</p>
            <p className="text-sm font-medium text-dark-900">
              {agent.created_at ? new Date(agent.created_at).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <h2 className="text-xl font-semibold text-dark-900 mb-4">Slave Agents</h2>
        
        {slaves && slaves.length > 0 ? (
          <div className="space-y-3">
            {slaves.map((slave) => (
              <div
                key={slave._id}
                className="flex items-center justify-between p-4 bg-dark-50 rounded-lg hover:bg-dark-100 transition-colors"
              >
                <div>
                  <h3 className="font-medium text-dark-900">{slave.domain}</h3>
                  <p className="text-sm text-dark-600 mt-1">
                    {slave.chunks_indexed || 0} chunks • 
                    Discovered via: <span className="font-mono text-xs">{slave.discovered_via_keyword || 'N/A'}</span>
                  </p>
                </div>
                <div className="text-right">
                  <span className="badge badge-success">Active</span>
                  <p className="text-xs text-dark-500 mt-1">
                    SERP #{slave.serp_position || 'N/A'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-dark-300 mx-auto mb-3" />
            <p className="text-dark-600">No slave agents yet</p>
            <p className="text-sm text-dark-500 mt-1">
              Slave agents will appear here after competitive analysis
            </p>
          </div>
        )}
      </div>

      {/* Competitive Intelligence */}
      <div className="card">
        <h2 className="text-xl font-semibold text-dark-900 mb-4">Competitive Intelligence</h2>
        <div className="bg-dark-50 rounded-lg p-6 text-center">
          <TrendingUp className="w-12 h-12 text-dark-300 mx-auto mb-3" />
          <p className="text-dark-600">CI Report will appear here</p>
          <p className="text-sm text-dark-500 mt-1">
            Complete workflow to generate competitive intelligence report
          </p>
        </div>
      </div>
    </div>
  )
}

