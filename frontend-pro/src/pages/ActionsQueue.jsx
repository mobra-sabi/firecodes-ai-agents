import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getActionsQueue, addAction, getActionsStats, updateActionStatus } from '@/api/actions'
import { useWebSocket } from '@/hooks/useWebSocket'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Dialog from '@/components/ui/Dialog'
import { Play, Pause, CheckCircle, XCircle, Clock, AlertCircle, Zap, Target, TrendingUp, Eye } from 'lucide-react'
import { format } from 'date-fns'

const ActionsQueue = () => {
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [selectedAction, setSelectedAction] = useState(null)
  const [newAction, setNewAction] = useState({
    agent_id: '',
    action_type: 'content_create',
    action_data: {},
    priority: 50
  })
  
  const queryClient = useQueryClient()
  
  // Fetch agents for dropdown
  const { data: agentsData } = useQuery({
    queryKey: ['agents', 'all'],
    queryFn: async () => {
      const response = await api.get('/agents?limit=100')
      return response.data || []
    }
  })
  
  const { data: actionsData, isLoading } = useQuery({
    queryKey: ['actionsQueue', selectedAgent],
    queryFn: () => getActionsQueue(selectedAgent),
    refetchInterval: 5000
  })
  
  // WebSocket for live updates
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = window.location.host
  const { isConnected: wsConnected, lastMessage: wsMessage } = useWebSocket(
    `${wsProtocol}//${wsHost}/ws/actions`,
    {
      enabled: true,
      onMessage: (data) => {
        if (data.type === 'action_update') {
          queryClient.invalidateQueries(['actionsQueue'])
          queryClient.invalidateQueries(['actionsStats'])
        }
      }
    }
  )
  
  const { data: stats } = useQuery({
    queryKey: ['actionsStats', selectedAgent],
    queryFn: () => getActionsStats(selectedAgent),
    refetchInterval: 5000
  })
  
  const addActionMutation = useMutation({
    mutationFn: addAction,
    onSuccess: () => {
      queryClient.invalidateQueries(['actionsQueue'])
      queryClient.invalidateQueries(['actionsStats'])
      setShowAddDialog(false)
      setNewAction({ agent_id: '', action_type: 'content_create', action_data: {}, priority: 50 })
    }
  })
  
  const updateStatusMutation = useMutation({
    mutationFn: ({ actionId, status }) => updateActionStatus(actionId, status),
    onSuccess: () => {
      queryClient.invalidateQueries(['actionsQueue'])
      queryClient.invalidateQueries(['actionsStats'])
    }
  })
  
  const handleAddAction = () => {
    addActionMutation.mutate(newAction)
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-400" />
      case 'running': return <Play className="w-4 h-4 text-blue-400" />
      case 'queued': return <Clock className="w-4 h-4 text-yellow-400" />
      default: return <AlertCircle className="w-4 h-4 text-gray-400" />
    }
  }
  
  const getActionTypeLabel = (type) => {
    const labels = {
      content_create: 'Create Content',
      onpage_optimize: 'Optimize On-Page',
      interlink_suggest: 'Suggest Interlinks',
      schema_generate: 'Generate Schema',
      ads_create: 'Create Ads',
      ads_update: 'Update Ads',
      experiment_run: 'Run Experiment',
      rollback: 'Rollback'
    }
    return labels[type] || type
  }
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Actions Queue</h1>
          <p className="text-text-muted mt-1">Manage and monitor SEO/PPC actions</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-sm text-text-muted">{wsConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>
      
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Total</h3>
                <Target className="w-5 h-5 text-primary-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{stats.total || 0}</p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Pending</h3>
                <Clock className="w-5 h-5 text-yellow-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{stats.pending || 0}</p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Running</h3>
                <Play className="w-5 h-5 text-blue-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{stats.running || 0}</p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Completed</h3>
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{stats.completed || 0}</p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Failed</h3>
                <XCircle className="w-5 h-5 text-red-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{stats.failed || 0}</p>
            </Card.Body>
          </Card>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex justify-between items-center">
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Filter by Agent ID..."
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
            value={selectedAgent || ''}
            onChange={(e) => setSelectedAgent(e.target.value || null)}
          />
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Zap className="w-4 h-4 mr-2" />
          Add Action
        </Button>
      </div>
      
      {/* Actions List */}
      <Card>
        <Card.Header>
          <Card.Title>Actions Queue</Card.Title>
        </Card.Header>
        <Card.Body className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
            </div>
          ) : !actionsData || (Array.isArray(actionsData) && actionsData.length === 0) || (actionsData?.actions && actionsData.actions.length === 0) ? (
            <p className="text-text-muted text-center py-12">No actions in queue</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Action</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Type</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Priority</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Created</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-gray-900 divide-y divide-gray-800">
                  {(Array.isArray(actionsData) ? actionsData : actionsData?.actions || []).map((action) => (
                    <tr key={action._id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-text-primary">
                        {action._id?.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                        {getActionTypeLabel(action.action_type)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-900 text-primary-300">
                          {action.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        <div className="flex items-center justify-center space-x-2">
                          {getStatusIcon(action.status)}
                          <span className="capitalize">{action.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                        {action.created_at ? format(new Date(action.created_at), 'yyyy-MM-dd HH:mm') : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        {action.status === 'pending' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => updateStatusMutation.mutate({ actionId: action._id, status: 'running' })}
                          >
                            <Play className="w-3 h-3 mr-1" />
                            Start
                          </Button>
                        )}
                        {action.status === 'running' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => updateStatusMutation.mutate({ actionId: action._id, status: 'completed' })}
                          >
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Complete
                          </Button>
                        )}
                        {action.status === 'completed' && action.result && (
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() => setSelectedAction(action)}
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View Results
                          </Button>
                        )}
                        {action.status === 'completed' && !action.result && (
                          <span className="text-text-muted text-xs">No results</span>
                        )}
                        {action.status === 'failed' && action.error && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setSelectedAction(action)}
                          >
                            <AlertCircle className="w-3 h-3 mr-1" />
                            View Error
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* Action Results Dialog */}
      <Dialog open={!!selectedAction} onOpenChange={(open) => !open && setSelectedAction(null)}>
        <Dialog.Content className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
          <Dialog.Header>
            <Dialog.Title>
              {selectedAction?.status === 'completed' ? 'Action Results' : 'Action Error'}
            </Dialog.Title>
            <Dialog.Description>
              {selectedAction?.action_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} - {selectedAction?._id?.substring(0, 8)}...
            </Dialog.Description>
          </Dialog.Header>
          
          {selectedAction?.status === 'completed' && selectedAction?.result && (
            <div className="space-y-6 mt-4">
              {selectedAction.action_type === 'onpage_optimize' && selectedAction.result.optimizations && (
                <>
                  <div className="bg-gray-800 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center">
                      <Target className="w-5 h-5 mr-2 text-primary-400" />
                      On-Page Optimizations
                    </h3>
                    
                    {selectedAction.result.optimizations.title_tag && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-text-muted mb-1">Title Tag</label>
                        <div className="bg-gray-900 rounded p-3 text-text-primary border border-gray-700">
                          {selectedAction.result.optimizations.title_tag}
                        </div>
                      </div>
                    )}
                    
                    {selectedAction.result.optimizations.meta_description && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-text-muted mb-1">Meta Description</label>
                        <div className="bg-gray-900 rounded p-3 text-text-primary border border-gray-700">
                          {selectedAction.result.optimizations.meta_description}
                        </div>
                      </div>
                    )}
                    
                    {selectedAction.result.optimizations.h1 && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-text-muted mb-1">H1 Heading</label>
                        <div className="bg-gray-900 rounded p-3 text-text-primary border border-gray-700">
                          {selectedAction.result.optimizations.h1}
                        </div>
                      </div>
                    )}
                    
                    {selectedAction.result.optimizations.h2_suggestions && selectedAction.result.optimizations.h2_suggestions.length > 0 && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-text-muted mb-2">H2 Heading Suggestions</label>
                        <ul className="space-y-2">
                          {selectedAction.result.optimizations.h2_suggestions.map((h2, idx) => (
                            <li key={idx} className="bg-gray-900 rounded p-2 text-text-primary border border-gray-700">
                              {h2}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {selectedAction.result.optimizations.image_alts && selectedAction.result.optimizations.image_alts.length > 0 && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-text-muted mb-2">Image Alt Text Suggestions</label>
                        <ul className="space-y-2">
                          {selectedAction.result.optimizations.image_alts.map((alt, idx) => (
                            <li key={idx} className="bg-gray-900 rounded p-2 text-text-primary border border-gray-700 text-sm">
                              {alt}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {selectedAction.result.optimizations.internal_links && selectedAction.result.optimizations.internal_links.length > 0 && (
                      <div>
                        <label className="block text-sm font-medium text-text-muted mb-2">Internal Link Suggestions</label>
                        <ul className="space-y-2">
                          {selectedAction.result.optimizations.internal_links.map((link, idx) => (
                            <li key={idx} className="bg-gray-900 rounded p-2 text-text-primary border border-gray-700">
                              {link}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  
                  {selectedAction.result.agent_context && (
                    <div className="bg-gray-800 rounded-lg p-4">
                      <h3 className="text-lg font-semibold text-text-primary mb-3">Agent Context</h3>
                      <div className="space-y-2 text-sm">
                        {selectedAction.result.agent_context.domain && (
                          <div>
                            <span className="text-text-muted">Domain: </span>
                            <span className="text-text-primary">{selectedAction.result.agent_context.domain}</span>
                          </div>
                        )}
                        {selectedAction.result.agent_context.company && (
                          <div>
                            <span className="text-text-muted">Company: </span>
                            <span className="text-text-primary">{selectedAction.result.agent_context.company}</span>
                          </div>
                        )}
                        {selectedAction.result.agent_context.industry && (
                          <div>
                            <span className="text-text-muted">Industry: </span>
                            <span className="text-text-primary">{selectedAction.result.agent_context.industry}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {selectedAction.action_type === 'content_create' && selectedAction.result.content && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-text-primary mb-3">Generated Content</h3>
                  <div className="bg-gray-900 rounded p-4 text-text-primary border border-gray-700 whitespace-pre-wrap">
                    {selectedAction.result.content}
                  </div>
                </div>
              )}
              
              {selectedAction.result && !selectedAction.result.optimizations && !selectedAction.result.content && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-text-primary mb-3">Result Data</h3>
                  <pre className="bg-gray-900 rounded p-4 text-text-primary border border-gray-700 text-xs overflow-auto">
                    {JSON.stringify(selectedAction.result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
          
          {selectedAction?.status === 'failed' && selectedAction?.error && (
            <div className="mt-4 bg-red-900/20 border border-red-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-red-400 mb-2 flex items-center">
                <AlertCircle className="w-5 h-5 mr-2" />
                Error Details
              </h3>
              <p className="text-red-300">{selectedAction.error}</p>
            </div>
          )}
          
          <div className="flex justify-end mt-6">
            <Button variant="secondary" onClick={() => setSelectedAction(null)}>
              Close
            </Button>
          </div>
        </Dialog.Content>
      </Dialog>
      
      {/* Add Action Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <Dialog.Content className="sm:max-w-[600px]">
          <Dialog.Header>
            <Dialog.Title>Add New Action</Dialog.Title>
            <Dialog.Description>Add a new action to the queue</Dialog.Description>
          </Dialog.Header>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Agent</label>
              <select
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newAction.agent_id}
                onChange={(e) => setNewAction({ ...newAction, agent_id: e.target.value })}
              >
                <option value="">Select an agent...</option>
                {agentsData?.map((agent) => (
                  <option key={agent._id} value={agent._id}>
                    {agent.domain} ({agent._id.substring(0, 8)}...)
                  </option>
                ))}
              </select>
              {newAction.agent_id && (
                <p className="mt-1 text-xs text-text-muted">
                  Agent ID: {newAction.agent_id}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Action Type</label>
              <select
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newAction.action_type}
                onChange={(e) => setNewAction({ ...newAction, action_type: e.target.value })}
              >
                <option value="content_create">Create Content</option>
                <option value="onpage_optimize">Optimize On-Page</option>
                <option value="interlink_suggest">Suggest Interlinks</option>
                <option value="schema_generate">Generate Schema</option>
                <option value="ads_create">Create Ads</option>
                <option value="ads_update">Update Ads</option>
                <option value="experiment_run">Run Experiment</option>
                <option value="rollback">Rollback</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Priority (0-100)</label>
              <input
                type="number"
                min="0"
                max="100"
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newAction.priority}
                onChange={(e) => setNewAction({ ...newAction, priority: parseInt(e.target.value) })}
              />
            </div>
            <div className="flex justify-end space-x-4">
              <Button variant="secondary" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleAddAction} disabled={addActionMutation.isLoading}>
                {addActionMutation.isLoading ? 'Adding...' : 'Add Action'}
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog>
    </div>
  )
}

export default ActionsQueue

