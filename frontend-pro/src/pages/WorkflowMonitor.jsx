import { useState, useEffect } from 'react'
import { RefreshCw, Play, Pause, Square, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { listActiveWorkflows, listRecentWorkflows, pauseWorkflow, stopWorkflow } from '../services/workflows'
import { useWorkflowStatus } from '../hooks/useWorkflowStatus'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'

const WorkflowMonitor = () => {
  const [activeWorkflows, setActiveWorkflows] = useState([])
  const [recentWorkflows, setRecentWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTab, setSelectedTab] = useState('active') // 'active' or 'history'

  // Fetch workflows
  const fetchWorkflows = async () => {
    try {
      setLoading(true)
      const [active, recent] = await Promise.all([
        listActiveWorkflows(),
        listRecentWorkflows(20)
      ])
      // ✅ Validate API responses
      setActiveWorkflows(Array.isArray(active?.workflows) ? active.workflows : [])
      setRecentWorkflows(Array.isArray(recent?.workflows) ? recent.workflows : [])
    } catch (error) {
      console.error('Error fetching workflows:', error)
      // ✅ Better error handling - set empty arrays on error
      setActiveWorkflows([])
      setRecentWorkflows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkflows()
    
    // ✅ Polling pentru active workflows (la fiecare 5 secunde) cu cleanup proper
    const interval = setInterval(fetchWorkflows, 5000)
    
    // ✅ Cleanup: stop polling când componenta se unmount
    return () => {
      clearInterval(interval)
    }
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">🔄 Workflow Monitor</h1>
          <p className="text-text-muted mt-2">
            Real-time tracking for all background processes
          </p>
        </div>
        
        <Button
          icon={<RefreshCw className="w-4 h-4" />}
          onClick={fetchWorkflows}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-gray-700">
        <button
          onClick={() => setSelectedTab('active')}
          className={`px-6 py-3 font-medium transition-colors ${
            selectedTab === 'active'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          🔄 Active ({activeWorkflows.length})
        </button>
        <button
          onClick={() => setSelectedTab('history')}
          className={`px-6 py-3 font-medium transition-colors ${
            selectedTab === 'history'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          📜 History ({recentWorkflows.length})
        </button>
      </div>

      {/* Active Workflows */}
      {selectedTab === 'active' && (
        <div className="space-y-4">
          {activeWorkflows.length === 0 ? (
            <Card>
              <Card.Body className="text-center py-12">
                <div className="text-gray-400 text-lg">
                  No active workflows
                </div>
                <p className="text-gray-500 mt-2">
                  Start a new workflow from the Agents page
                </p>
              </Card.Body>
            </Card>
          ) : (
            activeWorkflows.map((workflow) => (
              <WorkflowCard key={workflow.workflow_id} workflow={workflow} onUpdate={fetchWorkflows} />
            ))
          )}
        </div>
      )}

      {/* History */}
      {selectedTab === 'history' && (
        <div className="space-y-4">
          {recentWorkflows.length === 0 ? (
            <Card>
              <Card.Body className="text-center py-12">
                <div className="text-gray-400 text-lg">
                  No workflow history
                </div>
              </Card.Body>
            </Card>
          ) : (
            recentWorkflows.map((workflow) => (
              <WorkflowHistoryCard key={workflow.workflow_id} workflow={workflow} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

// Component pentru fiecare workflow activ cu live tracking
const WorkflowCard = ({ workflow: initialWorkflow, onUpdate }) => {
  const { workflow, isWebSocketConnected } = useWorkflowStatus(initialWorkflow.workflow_id, {
    useWebSocketUpdates: true
  })

  const currentWorkflow = workflow || initialWorkflow
  const [showLogs, setShowLogs] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  const handlePause = async () => {
    try {
      setActionLoading(true)
      await pauseWorkflow(currentWorkflow.workflow_id)
      onUpdate()
    } catch (error) {
      console.error('Error pausing workflow:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const handleStop = async () => {
    if (confirm('Are you sure you want to stop this workflow?')) {
      try {
        setActionLoading(true)
        await stopWorkflow(currentWorkflow.workflow_id)
        onUpdate()
      } catch (error) {
        console.error('Error stopping workflow:', error)
      } finally {
        setActionLoading(false)
      }
    }
  }

  // Support both number and object format for progress
  const progress = typeof currentWorkflow.progress === 'object' 
    ? (currentWorkflow.progress?.percent || 0)
    : (currentWorkflow.progress || 0)
  
  const statusColor = {
    pending: 'text-yellow-400',
    running: 'text-blue-400',
    in_progress: 'text-blue-400',
    completed: 'text-green-400',
    failed: 'text-red-400',
    cancelled: 'text-gray-400'
  }[currentWorkflow.status] || 'text-gray-400'

  const workflowIcon = {
    agent_creation: '🤖',
    competitive_analysis: '🎯',
    serp_discovery: '🔍',
    training: '🎓',
    rag_update: '🔄',
    slave_creation: '👥'
  }[currentWorkflow.type] || '⚙️'

  return (
    <Card>
      <Card.Body className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">{workflowIcon}</span>
            <div>
              <h3 className="text-xl font-semibold text-text-primary">
                {currentWorkflow.type?.replace('_', ' ').toUpperCase()}
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                ID: {currentWorkflow.workflow_id?.substring(0, 12)}...
                {isWebSocketConnected && (
                  <span className="ml-2 text-green-400">● Live</span>
                )}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`text-sm font-medium ${statusColor}`}>
              {currentWorkflow.status?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">
              {currentWorkflow.current_step || 
               (currentWorkflow.type === 'slave_creation' 
                 ? `Creating slave agents: ${currentWorkflow.progress?.completed || 0}/${currentWorkflow.progress?.total || 0}`
                 : 'Initializing...')}
            </span>
            <span className="text-primary-400 font-semibold">{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-primary-500 to-primary-400 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {/* Additional details for slave creation */}
          {currentWorkflow.type === 'slave_creation' && currentWorkflow.details && (
            <div className="mt-2 text-xs text-gray-400 flex gap-4">
              <span>✅ Created: {currentWorkflow.details.created || 0}</span>
              <span>⏭️ Skipped: {currentWorkflow.details.skipped || 0}</span>
              <span>❌ Failed: {currentWorkflow.details.failed || 0}</span>
              <span>🎯 Master: {currentWorkflow.details.master_domain || 'N/A'}</span>
            </div>
          )}
        </div>

        {/* Params */}
        {currentWorkflow.params && (
          <div className="mb-4 p-3 bg-gray-800 rounded-lg">
            <div className="text-xs text-gray-400 space-y-1">
              {Object.entries(currentWorkflow.params).map(([key, value]) => (
                <div key={key}>
                  <span className="font-medium">{key}:</span>{' '}
                  <span className="text-gray-300">{typeof value === 'string' ? value : JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Logs Toggle */}
        {currentWorkflow.logs && currentWorkflow.logs.length > 0 && (
          <div className="mb-4">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
            >
              {showLogs ? '▼' : '▶'} {showLogs ? 'Hide' : 'Show'} Logs ({currentWorkflow.logs.length})
            </button>
            
            {showLogs && (
              <div className="mt-2 p-3 bg-gray-900 rounded-lg max-h-60 overflow-y-auto font-mono text-xs space-y-1">
                {currentWorkflow.logs.slice(-10).map((log, idx) => (
                  <div key={idx} className={`${log.level === 'ERROR' ? 'text-red-400' : 'text-gray-300'}`}>
                    <span className="text-gray-500">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
                    <span className={log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARNING' ? 'text-yellow-400' : 'text-gray-300'}>
                      {log.level}:
                    </span>{' '}
                    {log.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {currentWorkflow.status === 'running' && (
          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="secondary"
              icon={<Pause className="w-4 h-4" />}
              onClick={handlePause}
              loading={actionLoading}
            >
              Pause
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<Square className="w-4 h-4" />}
              onClick={handleStop}
              loading={actionLoading}
            >
              Stop
            </Button>
          </div>
        )}

        {/* Metadata */}
        <div className="mt-4 pt-4 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>Started: {currentWorkflow.started_at ? new Date(currentWorkflow.started_at).toLocaleString() : 'N/A'}</span>
            </div>
          </div>
          
          {currentWorkflow.result && (
            <div className="text-green-400 font-medium">
              ✓ Result available
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  )
}

// Component pentru workflow history (completed/failed)
const WorkflowHistoryCard = ({ workflow }) => {
  const [showDetails, setShowDetails] = useState(false)
  
  const statusIcon = {
    completed: <CheckCircle className="w-5 h-5 text-green-400" />,
    failed: <XCircle className="w-5 h-5 text-red-400" />,
    cancelled: <AlertCircle className="w-5 h-5 text-gray-400" />
  }[workflow.status] || <Clock className="w-5 h-5 text-gray-400" />

  const workflowIcon = {
    agent_creation: '🤖',
    competitive_analysis: '🎯',
    serp_discovery: '🔍',
    training: '🎓',
    rag_update: '🔄'
  }[workflow.type] || '⚙️'

  const duration = workflow.completed_at && workflow.started_at
    ? ((new Date(workflow.completed_at) - new Date(workflow.started_at)) / 1000).toFixed(1) + 's'
    : 'N/A'

  return (
    <Card>
      <Card.Body className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1">
            <span className="text-2xl">{workflowIcon}</span>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h4 className="font-medium text-text-primary">
                  {workflow.type?.replace('_', ' ').toUpperCase()}
                </h4>
                {statusIcon}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {new Date(workflow.created_at).toLocaleString()} · Duration: {duration}
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-sm text-primary-400 hover:text-primary-300"
          >
            {showDetails ? 'Hide' : 'Show'} Details
          </button>
        </div>

        {showDetails && (
          <div className="mt-4 pt-4 border-t border-gray-700 space-y-2">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Workflow ID:</span>
                <p className="text-gray-200 font-mono text-xs mt-1">{workflow.workflow_id}</p>
              </div>
              <div>
                <span className="text-gray-400">Progress:</span>
                <p className="text-gray-200 mt-1">{workflow.progress?.toFixed(1)}%</p>
              </div>
            </div>

            {workflow.error && (
              <div className="p-3 bg-red-900/20 border border-red-500 rounded-lg">
                <p className="text-sm text-red-400 font-medium">Error:</p>
                <p className="text-xs text-red-300 mt-1 font-mono">{workflow.error}</p>
              </div>
            )}

            {workflow.result && (
              <div className="p-3 bg-green-900/20 border border-green-500 rounded-lg">
                <p className="text-sm text-green-400 font-medium">Result:</p>
                <pre className="text-xs text-green-300 mt-1 overflow-x-auto">
                  {JSON.stringify(workflow.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Card.Body>
    </Card>
  )
}

export default WorkflowMonitor

