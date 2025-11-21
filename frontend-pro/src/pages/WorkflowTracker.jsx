import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertCircle, 
  Play, 
  Pause,
  RefreshCw,
  FileText,
  TrendingUp,
  Activity
} from 'lucide-react'
import { format } from 'date-fns'

const WorkflowTracker = () => {
  const { agentId } = useParams()
  const [selectedStep, setSelectedStep] = useState(null)
  const [report, setReport] = useState(null)
  const [days, setDays] = useState(7)

  // Fetch workflow steps
  const { data: stepsData, isLoading, error, refetch } = useQuery({
    queryKey: ['workflowSteps', agentId],
    queryFn: async () => {
      try {
        const params = new URLSearchParams()
        if (agentId) params.append('agent_id', agentId)
        params.append('limit', '500')
        
        const response = await api.get(`/workflow/steps?${params.toString()}`)
        console.log('Workflow steps response:', response.data)
        return response.data || { steps: [], count: 0 }
      } catch (err) {
        console.error('Error fetching workflow steps:', err)
        return { steps: [], count: 0 }
      }
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  // Fetch workflow report
  const { data: reportData, error: reportError } = useQuery({
    queryKey: ['workflowReport', agentId, days],
    queryFn: async () => {
      try {
        const params = new URLSearchParams()
        if (agentId) params.append('agent_id', agentId)
        params.append('days', days.toString())
        
        const response = await api.get(`/workflow/report?${params.toString()}`)
        console.log('Workflow report response:', response.data)
        return response.data || { summary: { total_entries: 0, total_completed: 0, total_failed: 0, total_in_progress: 0, success_rate: 0 }, steps: {} }
      } catch (err) {
        console.error('Error fetching workflow report:', err)
        return { summary: { total_entries: 0, total_completed: 0, total_failed: 0, total_in_progress: 0, success_rate: 0 }, steps: {} }
      }
    },
  })

  // Group steps by category
  const groupedSteps = React.useMemo(() => {
    try {
      if (!stepsData?.steps || !Array.isArray(stepsData.steps)) {
        return {}
      }
      return stepsData.steps.reduce((acc, step) => {
        if (!step) return acc
        const category = getStepCategory(step.step || step.step_name)
        if (!acc[category]) {
          acc[category] = []
        }
        acc[category].push(step)
        return acc
      }, {})
    } catch (err) {
      console.error('Error grouping steps:', err)
      return {}
    }
  }, [stepsData])

  const getStepCategory = (stepName) => {
    if (!stepName || typeof stepName !== 'string') return 'Altele'
    const name = stepName.toLowerCase()
    if (name.startsWith('crawl') || name.startsWith('vectors')) return '1. Obiectiv'
    if (name.startsWith('fastapi') || name.startsWith('langchain') || name.startsWith('deepseek')) return '2. Arhitectură'
    if (name.includes('agent')) return '3. Tipuri de agenți'
    if (name.includes('collection') || name.includes('graph') || name.includes('queue')) return '4. Model de date'
    if (name.startsWith('create') || name.startsWith('serp') || name.startsWith('graph')) return '5. Fluxul principal'
    if (name.startsWith('orchestration')) return '6. Orchestrare'
    if (name.startsWith('api_')) return '7. API Endpoints'
    if (name.includes('rank') || name.includes('visibility') || name.includes('ice')) return '8. Scoruri & decizie'
    if (name.includes('copywriter') || name.includes('onpage') || name.includes('ads')) return '9. Action Engine'
    if (name.startsWith('job_') || name.startsWith('alert_') || name.startsWith('kpi_')) return '10. Monitorizare & alerte'
    if (name.startsWith('ui_')) return '11. UI Panouri'
    if (name.includes('rate') || name.includes('proxy') || name.includes('backup')) return '12. Securitate & fiabilitate'
    if (name.startsWith('ads_')) return '13. Google Ads'
    if (name.startsWith('roadmap_')) return '14. Roadmap execuție'
    if (name.startsWith('dod_')) return '15. Definition of Done'
    return 'Altele'
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />
      case 'in_progress':
        return <Play className="w-5 h-5 text-blue-400 animate-pulse" />
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />
      case 'retrying':
        return <RefreshCw className="w-5 h-5 text-yellow-400 animate-spin" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-900/30 border-green-500/50'
      case 'failed':
        return 'bg-red-900/30 border-red-500/50'
      case 'in_progress':
        return 'bg-blue-900/30 border-blue-500/50'
      case 'pending':
        return 'bg-gray-800 border-gray-600'
      case 'retrying':
        return 'bg-yellow-900/30 border-yellow-500/50'
      default:
        return 'bg-gray-800 border-gray-600'
    }
  }

  const formatDuration = (ms) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms.toFixed(0)}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }

  const getStepSummary = (stepName) => {
    if (!reportData?.steps || !stepName) return null
    return reportData.steps[stepName] || null
  }

  // Show error state
  if (error || reportError) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">Eroare la încărcarea datelor</h2>
          <p className="text-text-muted mb-4">{error?.message || reportError?.message || 'Eroare necunoscută'}</p>
          <Button onClick={() => { refetch(); window.location.reload(); }} icon={<RefreshCw className="w-4 h-4" />}>
            Reîncearcă
          </Button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  // Show empty state if no data
  if (!stepsData || !stepsData.steps || stepsData.steps.length === 0) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Workflow Tracker</h1>
            <p className="text-text-muted mt-1">
              Monitorizare completă pentru toți pașii din planul de implementare
            </p>
          </div>
          <Button onClick={() => refetch()} icon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>
        </div>

        <Card>
          <Card.Body className="py-12">
            <div className="text-center">
              <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-text-primary mb-2">
                Nu există date de tracking
              </h3>
              <p className="text-text-muted mb-4 max-w-md mx-auto">
                Workflow tracking-ul nu este activ încă. Pentru a vedea tracking-ul, trebuie să integrezi
                sistemul de tracking în workflow-urile existente.
              </p>
              <div className="mt-6 p-4 bg-gray-800 rounded-lg text-left max-w-2xl mx-auto">
                <p className="text-sm text-text-muted mb-2">
                  <strong className="text-text-primary">Cum să activezi tracking:</strong>
                </p>
                <ol className="text-sm text-text-muted space-y-1 list-decimal list-inside">
                  <li>Integrează tracking în workflow-urile existente (vezi WORKFLOW_TRACKING_INTEGRATION.md)</li>
                  <li>Creează un agent nou - tracking-ul va fi activat automat</li>
                  <li>Verifică logs pentru erori de tracking</li>
                </ol>
              </div>
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
          <h1 className="text-3xl font-bold text-text-primary">Workflow Tracker</h1>
          <p className="text-text-muted mt-1">
            Monitorizare completă pentru toți pașii din planul de implementare
            {agentId && ` - Agent: ${agentId}`}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
          >
            <option value={1}>Ultimele 24h</option>
            <option value={7}>Ultimele 7 zile</option>
            <option value={30}>Ultimele 30 zile</option>
            <option value={90}>Ultimele 90 zile</option>
          </select>
          <Button onClick={() => refetch()} icon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      {reportData?.summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Total Entries</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {reportData.summary.total_entries}
                  </div>
                </div>
                <Activity className="w-8 h-8 text-blue-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Completed</div>
                  <div className="text-2xl font-bold text-green-400 mt-1">
                    {reportData.summary.total_completed}
                  </div>
                </div>
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Failed</div>
                  <div className="text-2xl font-bold text-red-400 mt-1">
                    {reportData.summary.total_failed}
                  </div>
                </div>
                <XCircle className="w-8 h-8 text-red-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Success Rate</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {reportData.summary.success_rate.toFixed(1)}%
                  </div>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
            </Card.Body>
          </Card>
        </div>
      )}

      {/* Steps by Category */}
      <div className="space-y-6">
        {Object.entries(groupedSteps).map(([category, steps]) => {
          try {
            const categorySteps = (Array.isArray(steps) ? steps : []).sort((a, b) => {
              try {
                const dateA = a?.timestamp ? new Date(a.timestamp) : new Date(0)
                const dateB = b?.timestamp ? new Date(b.timestamp) : new Date(0)
                return dateB - dateA
              } catch {
                return 0
              }
            })
            
            // Get latest status for each unique step
            const uniqueSteps = {}
            categorySteps.forEach(step => {
              if (!step) return
              const stepKey = step.step || step.step_name || 'unknown'
              try {
                if (!uniqueSteps[stepKey] || 
                    (step.timestamp && uniqueSteps[stepKey].timestamp &&
                     new Date(step.timestamp) > new Date(uniqueSteps[stepKey].timestamp))) {
                  uniqueSteps[stepKey] = step
                }
              } catch (err) {
                console.error('Error processing step:', err, step)
              }
            })

            const stepsList = Object.values(uniqueSteps)

          return (
            <Card key={category}>
              <Card.Header>
                <Card.Title>{category}</Card.Title>
                <Card.Description>
                  {stepsList.length} step{stepsList.length !== 1 ? 's' : ''} în această categorie
                </Card.Description>
              </Card.Header>
              <Card.Body>
                <div className="space-y-2">
                  {stepsList.map((step) => {
                    const summary = getStepSummary(step.step || step.step_name)
                    
                    return (
                      <div
                        key={step._id}
                        className={`p-4 rounded-lg border ${getStatusColor(step.status)} cursor-pointer hover:opacity-80 transition-opacity`}
                        onClick={() => setSelectedStep(step)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-1">
                            {getStatusIcon(step.status)}
                            <div className="flex-1">
                              <div className="font-medium text-text-primary">
                                {(step.step_name || step.step || 'Unknown Step').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                              <div className="text-sm text-text-muted mt-1">
                                {step.agent_id && `Agent: ${step.agent_id.substring(0, 8)}...`}
                                {step.duration_ms && ` • Duration: ${formatDuration(step.duration_ms)}`}
                                {step.timestamp && ` • ${format(new Date(step.timestamp), 'MMM dd, HH:mm')}`}
                              </div>
                            </div>
                          </div>
                          {summary && (
                            <div className="text-right">
                              <div className="text-sm text-text-muted">
                                {summary.completed}/{summary.total} success
                              </div>
                              <div className="text-xs text-text-muted">
                                {summary.success_rate.toFixed(0)}% rate
                              </div>
                            </div>
                          )}
                        </div>
                        {step.error && (
                          <div className="mt-2 p-2 bg-red-900/20 rounded text-sm text-red-400">
                            ❌ {step.error}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </Card.Body>
            </Card>
          )
          } catch (err) {
            console.error('Error rendering category:', category, err)
            return null
          }
        })}
      </div>

      {/* Step Detail Modal */}
      {selectedStep && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <Card.Header>
              <div className="flex items-center justify-between">
                <Card.Title>
                  {(selectedStep.step_name || selectedStep.step || 'Unknown Step').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </Card.Title>
                <Button
                  variant="ghost"
                  onClick={() => setSelectedStep(null)}
                >
                  ✕
                </Button>
              </div>
            </Card.Header>
            <Card.Body className="space-y-4">
              <div>
                <div className="text-sm text-text-muted">Status</div>
                <div className="flex items-center gap-2 mt-1">
                  {getStatusIcon(selectedStep.status)}
                  <span className="text-text-primary capitalize">{selectedStep.status}</span>
                </div>
              </div>

              {selectedStep.agent_id && (
                <div>
                  <div className="text-sm text-text-muted">Agent ID</div>
                  <div className="text-text-primary font-mono text-sm mt-1">
                    {selectedStep.agent_id}
                  </div>
                </div>
              )}

              {selectedStep.timestamp && (
                <div>
                  <div className="text-sm text-text-muted">Timestamp</div>
                  <div className="text-text-primary mt-1">
                    {format(new Date(selectedStep.timestamp), 'PPpp')}
                  </div>
                </div>
              )}

              {selectedStep.duration_ms && (
                <div>
                  <div className="text-sm text-text-muted">Duration</div>
                  <div className="text-text-primary mt-1">
                    {formatDuration(selectedStep.duration_ms)}
                  </div>
                </div>
              )}

              {selectedStep.error && (
                <div>
                  <div className="text-sm text-text-muted">Error</div>
                  <div className="text-red-400 mt-1 p-3 bg-red-900/20 rounded">
                    {selectedStep.error}
                  </div>
                </div>
              )}

              {selectedStep.error_traceback && (
                <div>
                  <div className="text-sm text-text-muted">Traceback</div>
                  <pre className="text-xs text-red-400 mt-1 p-3 bg-gray-900 rounded overflow-x-auto">
                    {selectedStep.error_traceback}
                  </pre>
                </div>
              )}

              {selectedStep.details && Object.keys(selectedStep.details).length > 0 && (
                <div>
                  <div className="text-sm text-text-muted">Details</div>
                  <pre className="text-xs text-text-primary mt-1 p-3 bg-gray-900 rounded overflow-x-auto">
                    {JSON.stringify(selectedStep.details, null, 2)}
                  </pre>
                </div>
              )}

              {selectedStep.metadata && Object.keys(selectedStep.metadata).length > 0 && (
                <div>
                  <div className="text-sm text-text-muted">Metadata</div>
                  <pre className="text-xs text-text-primary mt-1 p-3 bg-gray-900 rounded overflow-x-auto">
                    {JSON.stringify(selectedStep.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </Card.Body>
          </Card>
        </div>
      )}
    </div>
  )
}

export default WorkflowTracker

