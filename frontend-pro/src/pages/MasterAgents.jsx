import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Search, Loader2, CheckCircle, Clock, AlertCircle, Activity, MessageSquare, Zap } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { useState, useEffect } from 'react'

const MasterAgents = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [agentProgress, setAgentProgress] = useState({})

  // Fetch agents - TOȚI agenții (nu doar complet procesați)
  const { data: agentsData, isLoading, refetch } = useQuery({
    queryKey: ['agents', 'master'],
    queryFn: async () => {
      // Folosește endpoint-ul pentru toți agenții master
      const response = await api.get('/agents?type=master')
      return response.data || []
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })
  
  const agents = agentsData || []

  // Fetch progress for agents that are in creation
  useEffect(() => {
    if (!agents) return

    const fetchProgress = async () => {
      const agentsInProgress = agents.filter(
        (agent) => agent.chunks_indexed > 0 && (!agent.slave_count || agent.slave_count === 0)
      )

      for (const agent of agentsInProgress) {
        try {
          const response = await api.get(`/agents/${agent._id}/progress`)
          setAgentProgress((prev) => ({ ...prev, [agent._id]: response.data }))
        } catch (error) {
          console.error(`Error fetching progress for ${agent._id}:`, error)
        }
      }
    }

    fetchProgress()
    const interval = setInterval(fetchProgress, 3000) // Update every 3 seconds

    return () => clearInterval(interval)
  }, [agents])

  const filteredAgents = agents?.filter((agent) =>
    agent.domain.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.industry?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-primary-700 rounded w-1/4 mb-8"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-64 bg-primary-700 rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Master Agents</h1>
          <p className="text-text-muted mt-1">
            {filteredAgents.length} agent{filteredAgents.length !== 1 ? 's' : ''} found
          </p>
        </div>
        <Link to="/agents/new">
          <Button icon={<Plus className="w-5 h-5" />}>
            New Master Agent
          </Button>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-muted" />
        <input
          type="text"
          placeholder="Search by domain or industry..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-custom w-full pl-12"
        />
      </div>

      {/* Agents Grid */}
      {filteredAgents.length === 0 ? (
        <Card>
          <Card.Body className="py-12">
            <div className="text-center">
              <p className="text-text-muted mb-4">No agents found. Create your first agent!</p>
              <Link to="/agents/new">
                <Button>Create Agent</Button>
              </Link>
            </div>
          </Card.Body>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => {
            const progress = agentProgress[agent._id]
            const isInProgress = progress && progress.overall_progress < 100

            return (
              <div key={agent._id} className="relative">
                <div className="absolute top-2 right-2 z-10 flex gap-2">
                  {isInProgress && (
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        navigate(`/agents/${agent._id}/live`)
                      }}
                      className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-xs font-medium flex items-center gap-1 transition-colors"
                    >
                      <Activity className="w-3 h-3" />
                      Live Monitor
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      navigate(`/agents/${agent._id}/chat`)
                    }}
                    className="px-3 py-1 bg-accent-blue hover:bg-accent-blue/80 text-white rounded-md text-xs font-medium flex items-center gap-1 transition-colors"
                  >
                    <MessageSquare className="w-3 h-3" />
                    Chat
                  </button>
                </div>
                <Link to={`/agents/${agent._id}`}>
                  <Card hover className="h-full">
                    <Card.Body className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-text-primary truncate">
                            {agent.domain}
                          </h3>
                          {agent.industry && (
                            <p className="text-sm text-text-muted mt-1">{agent.industry}</p>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            isInProgress
                              ? 'bg-blue-500 bg-opacity-10 text-blue-400 flex items-center gap-1'
                              : agent.status === 'active' || agent.status === 'validated'
                              ? 'bg-accent-green bg-opacity-10 text-accent-green'
                              : 'bg-accent-yellow bg-opacity-10 text-accent-yellow'
                          }`}>
                            {isInProgress && <Loader2 className="w-3 h-3 animate-spin" />}
                            {isInProgress ? 'Creating...' : agent.status}
                          </span>
                          {/* Status complet indicator */}
                          {!isInProgress && agent.chunks_indexed > 0 && (
                            <span className="px-2 py-1 rounded text-xs font-medium bg-purple-500 bg-opacity-10 text-purple-400 flex items-center gap-1" title="Procesat complet: MongoDB + Qdrant + LangChain">
                              <CheckCircle className="w-3 h-3" />
                              AI Ready
                            </span>
                          )}
                        </div>
                      </div>

                    {/* PROGRESS BAR - LIVE */}
                    {isInProgress && progress && (
                      <div className="mb-4">
                        <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                          <span>Creation Progress</span>
                          <span className="text-blue-400 font-medium">{progress.overall_progress}%</span>
                        </div>
                        <div className="w-full bg-primary-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-accent-blue h-full transition-all duration-500 ease-out"
                            style={{ width: `${progress.overall_progress}%` }}
                          />
                        </div>
                        
                        {/* Current Step */}
                        <div className="mt-2 text-xs text-text-muted">
                          {progress.steps.find(s => s.status === 'in_progress')?.name || 'Processing...'}
                        </div>
                      </div>
                    )}

                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-text-muted">Chunks</span>
                        <span className="text-text-primary font-medium">
                          {agent.chunks_indexed || 0}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-muted">Keywords</span>
                        <span className="text-text-primary font-medium">
                          {agent.keyword_count || 0}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-muted">Competitors</span>
                        <span className="text-text-primary font-medium">
                          {agent.slave_count || 0}
                        </span>
                      </div>
                      {/* Status complet indicator */}
                      {agent.chunks_indexed > 0 && (
                        <div className="flex justify-between text-sm pt-2 border-t border-primary-700">
                          <span className="text-text-muted">Status</span>
                          <span className="text-purple-400 font-medium flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            AI Ready
                          </span>
                        </div>
                      )}
                    </div>

                      {agent.createdAt && (
                        <p className="text-xs text-text-muted mt-4">
                          Created {new Date(agent.createdAt).toLocaleDateString()}
                        </p>
                      )}
                    </Card.Body>
                  </Card>
                </Link>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default MasterAgents

