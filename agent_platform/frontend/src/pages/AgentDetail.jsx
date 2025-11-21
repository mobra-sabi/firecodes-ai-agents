import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Loader2, CheckCircle, Clock, Play, FileText, Activity } from 'lucide-react'
import api from '../lib/api'

export default function AgentDetail() {
  const { id } = useParams()
  
  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: async () => {
      const { data } = await api.get(`/agents/${id}`)
      return data
    },
  })
  
  const { data: slaves } = useQuery({
    queryKey: ['agent-slaves', id],
    queryFn: async () => {
      const { data } = await api.get(`/agents/${id}/slaves`)
      return data
    },
    enabled: !!agent && agent.agent_type === 'master',
  })
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }
  
  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Agent not found</p>
        <Link to="/agents" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
          Back to Agents
        </Link>
      </div>
    )
  }
  
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back Button */}
      <Link
        to="/agents"
        className="inline-flex items-center space-x-2 text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back to Agents</span>
      </Link>
      
      {/* Agent Header */}
      <div className="card">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">{agent.domain}</h1>
            <p className="text-slate-600">{agent.site_url || 'No URL'}</p>
          </div>
          <div className="flex items-center space-x-3">
            {agent.status === 'validated' ? (
              <CheckCircle className="w-6 h-6 text-green-600" />
            ) : (
              <Clock className="w-6 h-6 text-yellow-600" />
            )}
            <span className={`px-4 py-2 rounded-full text-sm font-medium ${
              agent.status === 'validated'
                ? 'bg-green-100 text-green-700'
                : agent.status === 'ready'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-yellow-100 text-yellow-700'
            }`}>
              {agent.status}
            </span>
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 mb-6 pb-6 border-b border-slate-200">
          <Link
            to={`/agents/${id}/workflow`}
            className="btn-primary flex items-center space-x-2 text-sm"
          >
            <Activity className="w-4 h-4" />
            <span>Monitor Workflow</span>
          </Link>
          {agent.agent_type === 'master' && agent.status === 'validated' && (
            <>
              <button
                onClick={async () => {
                  try {
                    await api.post('/workflow/start', { agent_id: id })
                    alert('Workflow started! Check monitor for progress.')
                  } catch (err) {
                    alert('Failed to start workflow: ' + (err.response?.data?.error || err.message))
                  }
                }}
                className="btn-secondary flex items-center space-x-2 text-sm"
              >
                <Play className="w-4 h-4" />
                <span>Start Workflow</span>
              </button>
              <button
                onClick={async () => {
                  try {
                    await api.post(`/api/reports/generate/${id}`)
                    alert('Report generated! Check Reports page.')
                    window.location.href = '/reports'
                  } catch (err) {
                    alert('Failed to generate report: ' + (err.response?.data?.error || err.message))
                  }
                }}
                className="btn-secondary flex items-center space-x-2 text-sm"
              >
                <FileText className="w-4 h-4" />
                <span>Generate Report</span>
              </button>
            </>
          )}
        </div>
        
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-50 p-4 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Type</p>
            <p className="text-lg font-bold text-slate-900 capitalize">{agent.agent_type || 'N/A'}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Chunks</p>
            <p className="text-lg font-bold text-slate-900">{agent.chunks_indexed || 0}</p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg">
            <p className="text-sm text-slate-600 mb-1">Keywords</p>
            <p className="text-lg font-bold text-slate-900">{agent.keyword_count || 0}</p>
          </div>
          {agent.agent_type === 'master' && (
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-sm text-slate-600 mb-1">Slaves</p>
              <p className="text-lg font-bold text-slate-900">{agent.slave_count || 0}</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Slaves (if master) */}
      {agent.agent_type === 'master' && slaves && slaves.length > 0 && (
        <div className="card">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Slave Agents</h2>
          <div className="space-y-3">
            {slaves.map((slave) => (
              <Link
                key={slave._id}
                to={`/agents/${slave._id}`}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div>
                  <p className="font-semibold text-slate-900">{slave.domain}</p>
                  <p className="text-sm text-slate-600">{slave.chunks_indexed || 0} chunks</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  slave.status === 'validated'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {slave.status}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

