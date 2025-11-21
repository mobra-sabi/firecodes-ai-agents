import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Activity, Cpu, Database, Network, Zap, TrendingUp, Users, FileText, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'

const LiveMonitor = () => {
  const { agentId, workflowId } = useParams()
  const [progress, setProgress] = useState(null)
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState({})
  const [keywords, setKeywords] = useState([])
  const [competitors, setCompetitors] = useState([])
  const [serpResults, setSerpResults] = useState([])
  const [playbook, setPlaybook] = useState(null)
  const [slavesProgress, setSlavesProgress] = useState(null)
  const [resolvedAgentId, setResolvedAgentId] = useState(agentId)
  
  // Dacă avem workflowId în loc de agentId, încearcă să găsească agentul
  useEffect(() => {
    if (agentId && agentId !== 'workflow') return // Avem deja agentId valid
    
    // Verifică sessionStorage pentru workflow_id pending
    const pendingWorkflowId = workflowId || sessionStorage.getItem('pending_workflow_id')
    const pendingSiteUrl = sessionStorage.getItem('pending_site_url')
    
    if (pendingWorkflowId && pendingSiteUrl) {
      // Încearcă să găsească agentul periodic
      const findAgent = async () => {
        try {
          const findResponse = await api.get('/agents/by-site-url', {
            params: { site_url: pendingSiteUrl }
          })
          
          if (findResponse.data && findResponse.data.ok && findResponse.data.agent_id) {
            // Agentul găsit - actualizează URL-ul fără refresh
            setResolvedAgentId(findResponse.data.agent_id)
            sessionStorage.removeItem('pending_workflow_id')
            sessionStorage.removeItem('pending_site_url')
            // Actualizează URL-ul fără refresh
            window.history.replaceState(null, '', `/agents/${findResponse.data.agent_id}/live`)
          }
        } catch (err) {
          // Continuă să încerce
        }
      }
      
      // Încearcă imediat
      findAgent()
      
      // Apoi la fiecare 3 secunde
      const interval = setInterval(findAgent, 3000)
      return () => clearInterval(interval)
    }
  }, [agentId, workflowId])
  
  // Fetch all data
  useEffect(() => {
    const currentAgentId = resolvedAgentId || agentId
    if (!currentAgentId || currentAgentId === 'workflow') return

    const fetchData = async () => {
      try {
        // Progress
        const progressRes = await api.get(`/agents/${currentAgentId}/progress`)
        setProgress(progressRes.data)

        // Stats from MongoDB
        const statsRes = await api.get(`/agents/${currentAgentId}/stats`)
        setStats(statsRes.data || {})

        // Keywords
        try {
          const keywordsRes = await api.get(`/agents/${currentAgentId}/keywords`)
          setKeywords(keywordsRes.data?.keywords || [])
        } catch (e) {}

        // Competitors (slaves)
        try {
          const competitorsRes = await api.get(`/agents?master_id=${currentAgentId}`)
          setCompetitors(competitorsRes.data || [])
        } catch (e) {}

        // SERP Results
        try {
          const serpRes = await api.get(`/agents/${currentAgentId}/serp-rankings`)
          setSerpResults(serpRes.data?.results || [])
        } catch (e) {}

        // Playbook
        try {
          const playbookRes = await api.get(`/agents/${currentAgentId}/playbook`)
          setPlaybook(playbookRes.data)
        } catch (e) {}

        // Slaves Progress
        try {
          const slavesProgressRes = await api.get(`/agents/${currentAgentId}/slaves/progress`)
          setSlavesProgress(slavesProgressRes.data)
        } catch (e) {}

      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 3000) // Update every 3 seconds

    return () => clearInterval(interval)
  }, [resolvedAgentId, agentId])

  // Simulate logs from progress steps
  useEffect(() => {
    if (!progress) return

    const newLogs = progress.steps.map(step => ({
      timestamp: new Date().toISOString(),
      level: step.status === 'completed' ? 'success' : step.status === 'in_progress' ? 'info' : 'pending',
      message: `${step.name}: ${step.details || step.status}`,
      step: step.id
    }))

    setLogs(newLogs)
  }, [progress])

  const currentAgentId = resolvedAgentId || agentId
  
  if (!currentAgentId || currentAgentId === 'workflow') {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400"></div>
        <p className="text-text-muted">Waiting for agent to be created...</p>
        <p className="text-xs text-text-muted">This may take a few seconds</p>
      </div>
    )
  }

  if (!progress) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-pulse">Loading...</div>
      </div>
    )
  }

  const StepCard = ({ step, icon: Icon, children }) => {
    const getStatusColor = (status) => {
      switch (status) {
        case 'completed': return 'text-accent-green'
        case 'in_progress': return 'text-blue-400'
        case 'failed': return 'text-accent-red'
        default: return 'text-text-muted'
      }
    }

    const getStatusIcon = (status) => {
      switch (status) {
        case 'completed': return <CheckCircle className="w-5 h-5" />
        case 'in_progress': return <Activity className="w-5 h-5 animate-pulse" />
        case 'failed': return <AlertCircle className="w-5 h-5" />
        default: return <Clock className="w-5 h-5" />
      }
    }

    return (
      <Card className="border-l-4" style={{
        borderLeftColor: step.status === 'completed' ? '#10b981' : 
                         step.status === 'in_progress' ? '#3b82f6' : '#6b7280'
      }}>
        <Card.Body className="p-4">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg bg-primary-700 ${getStatusColor(step.status)}`}>
              {Icon && <Icon className="w-5 h-5" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-text-primary">{step.name}</h3>
                <div className={`flex items-center gap-2 ${getStatusColor(step.status)}`}>
                  {getStatusIcon(step.status)}
                  <span className="text-sm font-medium">{step.progress}%</span>
                </div>
              </div>
              {step.details && (
                <p className="text-sm text-text-muted mb-2">{step.details}</p>
              )}
              {children}
            </div>
          </div>
        </Card.Body>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Live Monitor</h1>
          <p className="text-text-muted mt-1">Real-time agent creation process - {progress.domain || 'Loading...'}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-400">{progress.overall_progress}%</div>
            <div className="text-xs text-text-muted">Overall Progress</div>
          </div>
        </div>
      </div>

      {/* Overall Progress Bar */}
      <Card>
        <Card.Body className="p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-text-primary">
              {progress.completed_steps} / {progress.total_steps} Steps Completed
            </span>
            <span className="text-sm text-blue-400">{progress.overall_progress}%</span>
          </div>
          <div className="w-full bg-primary-700 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-500 to-accent-blue h-full transition-all duration-500"
              style={{ width: `${progress.overall_progress}%` }}
            />
          </div>
        </Card.Body>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <Card.Body className="p-4">
            <div className="flex items-center gap-3">
              <Database className="w-8 h-8 text-blue-400" />
              <div>
                <div className="text-2xl font-bold text-text-primary">{stats.chunks_indexed || 0}</div>
                <div className="text-xs text-text-muted">Chunks Indexed</div>
              </div>
            </div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-accent-green" />
              <div>
                <div className="text-2xl font-bold text-text-primary">{keywords.length}</div>
                <div className="text-xs text-text-muted">Keywords Generated</div>
              </div>
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body className="p-4">
            <div className="flex items-center gap-3">
              <Users className="w-8 h-8 text-accent-yellow" />
              <div>
                <div className="text-2xl font-bold text-text-primary">{competitors.length}</div>
                <div className="text-xs text-text-muted">Competitors Found</div>
              </div>
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body className="p-4">
            <div className="flex items-center gap-3">
              <Network className="w-8 h-8 text-accent-blue" />
              <div>
                <div className="text-2xl font-bold text-text-primary">{serpResults.length}</div>
                <div className="text-xs text-text-muted">SERP Results</div>
              </div>
            </div>
          </Card.Body>
        </Card>
      </div>

      {/* Process Steps */}
      <div className="space-y-4">
        {progress.steps.map((step, index) => {
          const icons = [Cpu, Database, Zap, FileText, Network, Users, TrendingUp, CheckCircle]
          const Icon = icons[index] || Activity

          return (
            <StepCard key={step.id} step={step} icon={Icon}>
              {/* Show relevant data for each step */}
              {step.id === 1 && stats.chunks_indexed > 0 && (
                <div className="mt-2 p-3 bg-primary-700 rounded">
                  <div className="text-xs text-text-muted mb-1">Live Data:</div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>Chunks: <span className="text-accent-green font-mono">{stats.chunks_indexed}</span></div>
                    <div>Status: <span className="text-accent-green">✓ Indexed</span></div>
                  </div>
                </div>
              )}

              {step.id === 4 && keywords.length > 0 && (
                <div className="mt-2 p-3 bg-primary-700 rounded">
                  <div className="text-xs text-text-muted mb-1">Generated Keywords:</div>
                  <div className="flex flex-wrap gap-1">
                    {keywords.slice(0, 10).map((kw, i) => (
                      <span key={i} className="px-2 py-1 bg-blue-500 bg-opacity-20 text-blue-400 rounded text-xs">
                        {typeof kw === 'string' ? kw : kw.keyword || kw.text}
                      </span>
                    ))}
                    {keywords.length > 10 && (
                      <span className="px-2 py-1 text-text-muted text-xs">+{keywords.length - 10} more</span>
                    )}
                  </div>
                </div>
              )}

              {step.id === 6 && competitors.length > 0 && (
                <div className="mt-2 p-3 bg-primary-700 rounded">
                  <div className="text-xs text-text-muted mb-1">Slave Agents Created:</div>
                  <div className="space-y-1">
                    {competitors.slice(0, 5).map((comp, i) => (
                      <div key={i} className="text-sm flex items-center gap-2">
                        <CheckCircle className="w-3 h-3 text-accent-green" />
                        <span className="text-text-primary">{comp.domain}</span>
                        {comp.chunks_indexed > 0 && (
                          <span className="text-text-muted text-xs">({comp.chunks_indexed} chunks)</span>
                        )}
                      </div>
                    ))}
                    {competitors.length > 5 && (
                      <div className="text-xs text-text-muted">+{competitors.length - 5} more competitors</div>
                    )}
                  </div>
                </div>
              )}

              {step.id === 5 && serpResults.length > 0 && (
                <div className="mt-2 p-3 bg-primary-700 rounded">
                  <div className="text-xs text-text-muted mb-1">SERP Rankings:</div>
                  <div className="space-y-1">
                    {serpResults.slice(0, 5).map((result, i) => (
                      <div key={i} className="text-sm flex items-center gap-2">
                        <span className="text-accent-blue font-mono">#{result.rank || result.position}</span>
                        <span className="text-text-primary truncate">{result.domain || result.url}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {step.id === 8 && playbook && (
                <div className="mt-2 p-3 bg-primary-700 rounded">
                  <div className="text-xs text-text-muted mb-1">Playbook Generated:</div>
                  <div className="text-sm text-text-primary">
                    {playbook.actions?.length || 0} actions planned
                  </div>
                </div>
              )}
            </StepCard>
          )
        })}
      </div>

      {/* Slave Agents Creation Progress */}
      {slavesProgress && slavesProgress.target > 0 && (
        <Card>
          <Card.Header>
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Users className="w-5 h-5 text-accent-yellow animate-pulse" />
              Slave Agents Creation - LIVE
            </h3>
          </Card.Header>
          <Card.Body className="p-6">
            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-text-muted">
                  Creating {slavesProgress.target} slave agents in background
                </span>
                <span className="text-2xl font-bold text-accent-yellow">
                  {slavesProgress.progress_percent}%
                </span>
              </div>
              <div className="w-full bg-primary-700 rounded-full h-3 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-accent-yellow to-accent-green transition-all duration-500 ease-out"
                  style={{ width: `${slavesProgress.progress_percent}%` }}
                />
              </div>
              <div className="flex justify-between items-center mt-2 text-xs text-text-muted">
                <span>Started: {slavesProgress.started_at ? new Date(slavesProgress.started_at).toLocaleString() : 'N/A'}</span>
                <span className={`font-semibold ${slavesProgress.status === 'completed' ? 'text-accent-green' : 'text-blue-400'}`}>
                  Status: {slavesProgress.status.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <div className="p-3 bg-primary-700 rounded text-center">
                <div className="text-2xl font-bold text-text-primary">{slavesProgress.completed}</div>
                <div className="text-xs text-text-muted">Processed</div>
              </div>
              <div className="p-3 bg-primary-700 rounded text-center">
                <div className="text-2xl font-bold text-accent-green">{slavesProgress.created}</div>
                <div className="text-xs text-text-muted">Created New</div>
              </div>
              <div className="p-3 bg-primary-700 rounded text-center">
                <div className="text-2xl font-bold text-accent-blue">{slavesProgress.skipped}</div>
                <div className="text-xs text-text-muted">Skipped</div>
              </div>
              <div className="p-3 bg-primary-700 rounded text-center">
                <div className="text-2xl font-bold text-red-400">{slavesProgress.failed}</div>
                <div className="text-xs text-text-muted">Failed</div>
              </div>
              <div className="p-3 bg-primary-700 rounded text-center">
                <div className="text-2xl font-bold text-text-primary">{slavesProgress.slaves?.total_chunks || 0}</div>
                <div className="text-xs text-text-muted">Total Chunks</div>
              </div>
            </div>

            {/* Recent Slaves */}
            {slavesProgress.recent_slaves && slavesProgress.recent_slaves.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-text-muted mb-3">Recently Created Slaves (Last 10):</h4>
                <div className="space-y-2">
                  {slavesProgress.recent_slaves.slice().reverse().map((slave, index) => (
                    <div
                      key={slave.id}
                      className="flex items-center justify-between p-3 bg-primary-700 rounded hover:bg-primary-600 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {slave.status === 'completed' ? (
                          <CheckCircle className="w-4 h-4 text-accent-green" />
                        ) : (
                          <Clock className="w-4 h-4 text-blue-400 animate-pulse" />
                        )}
                        <div>
                          <div className="text-sm font-medium text-text-primary">{slave.domain}</div>
                          <div className="text-xs text-text-muted">
                            {slave.created_at ? new Date(slave.created_at).toLocaleTimeString() : 'Processing...'}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          slave.status === 'completed' 
                            ? 'bg-accent-green bg-opacity-10 text-accent-green' 
                            : 'bg-blue-500 bg-opacity-10 text-blue-400'
                        }`}>
                          {slave.status}
                        </span>
                        <span className="text-sm font-mono text-text-primary">
                          {slave.chunks} chunks
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card.Body>
        </Card>
      )}

      {/* Live Logs */}
      <Card>
        <Card.Header>
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400 animate-pulse" />
            Live Process Logs
          </h3>
        </Card.Header>
        <Card.Body className="p-0">
          <div className="max-h-96 overflow-y-auto">
            {logs.map((log, index) => (
              <div
                key={index}
                className={`p-3 border-b border-primary-700 font-mono text-xs ${
                  log.level === 'success' ? 'text-accent-green' :
                  log.level === 'info' ? 'text-blue-400' :
                  'text-text-muted'
                }`}
              >
                <span className="text-text-muted">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
                <span className={log.level === 'success' ? 'text-accent-green' : 'text-blue-400'}>
                  {log.level.toUpperCase()}
                </span>{' '}
                {log.message}
              </div>
            ))}
          </div>
        </Card.Body>
      </Card>
    </div>
  )
}

export default LiveMonitor

