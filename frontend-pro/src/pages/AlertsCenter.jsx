import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, checkAlerts, acknowledgeAlert, resolveAlert } from '@/api/alerts'
import { useWebSocket } from '@/hooks/useWebSocket'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { AlertCircle, CheckCircle, XCircle, Bell, RefreshCw, Filter } from 'lucide-react'
import { format } from 'date-fns'

const AlertsCenter = () => {
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [filterType, setFilterType] = useState('all')
  
  const queryClient = useQueryClient()
  
  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts', selectedAgent, filterSeverity, filterType],
    queryFn: () => getAlerts(selectedAgent, filterType !== 'all' ? filterType : null, filterSeverity !== 'all' ? filterSeverity : null),
    refetchInterval: 10000
  })
  
  // WebSocket for live alerts
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = window.location.host
  const { isConnected: wsConnected, lastMessage: wsMessage } = useWebSocket(
    `${wsProtocol}//${wsHost}/ws/alerts`,
    {
      enabled: true,
      onMessage: (data) => {
        if (data.type === 'alert') {
          queryClient.invalidateQueries(['alerts'])
        }
      }
    }
  )
  
  const acknowledgeMutation = useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts'])
    }
  })
  
  const resolveMutation = useMutation({
    mutationFn: ({ alertId, resolution }) => resolveAlert(alertId, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts'])
    }
  })
  
  const checkAlertsMutation = useMutation({
    mutationFn: checkAlerts,
    onSuccess: () => {
      queryClient.invalidateQueries(['alerts'])
    }
  })
  
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-900'
      case 'high': return 'text-orange-400 bg-orange-900'
      case 'medium': return 'text-yellow-400 bg-yellow-900'
      case 'low': return 'text-blue-400 bg-blue-900'
      default: return 'text-gray-400 bg-gray-800'
    }
  }
  
  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical': return <XCircle className="w-5 h-5 text-red-400" />
      case 'high': return <AlertCircle className="w-5 h-5 text-orange-400" />
      default: return <Bell className="w-5 h-5 text-yellow-400" />
    }
  }
  
  const getAlertTypeLabel = (type) => {
    const labels = {
      rank_drop: 'Rank Drop',
      competitor_new: 'New Competitor',
      ctr_low: 'Low CTR',
      visibility_drop: 'Visibility Drop',
      keyword_lost: 'Keyword Lost',
      action_failed: 'Action Failed',
      system_error: 'System Error'
    }
    return labels[type] || type
  }
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Alerts Center</h1>
          <p className="text-text-muted mt-1">Monitor and manage system alerts</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-sm text-text-muted">{wsConnected ? 'Live' : 'Disconnected'}</span>
        </div>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Filter by Agent ID..."
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
            value={selectedAgent || ''}
            onChange={(e) => setSelectedAgent(e.target.value || null)}
          />
          <Button
            variant="secondary"
            onClick={() => selectedAgent && checkAlertsMutation.mutate(selectedAgent)}
            disabled={!selectedAgent || checkAlertsMutation.isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${checkAlertsMutation.isLoading ? 'animate-spin' : ''}`} />
            Check Alerts
          </Button>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex space-x-4">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-text-muted" />
          <select
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <select
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="all">All Types</option>
          <option value="rank_drop">Rank Drop</option>
          <option value="competitor_new">New Competitor</option>
          <option value="ctr_low">Low CTR</option>
          <option value="visibility_drop">Visibility Drop</option>
          <option value="keyword_lost">Keyword Lost</option>
          <option value="action_failed">Action Failed</option>
          <option value="system_error">System Error</option>
        </select>
      </div>
      
      {/* Stats */}
      {alertsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Total Alerts</h3>
                <Bell className="w-5 h-5 text-primary-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">{alertsData.count || 0}</p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Critical</h3>
                <XCircle className="w-5 h-5 text-red-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">
                {alertsData.alerts?.filter(a => a.severity === 'critical').length || 0}
              </p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">High</h3>
                <AlertCircle className="w-5 h-5 text-orange-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">
                {alertsData.alerts?.filter(a => a.severity === 'high').length || 0}
              </p>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted">Active</h3>
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <p className="text-3xl font-bold text-text-primary mt-2">
                {alertsData.alerts?.filter(a => a.status === 'active').length || 0}
              </p>
            </Card.Body>
          </Card>
        </div>
      )}
      
      {/* Alerts List */}
      <Card>
        <Card.Header>
          <Card.Title>Active Alerts</Card.Title>
        </Card.Header>
        <Card.Body className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
            </div>
          ) : alertsData?.alerts?.length === 0 ? (
            <p className="text-text-muted text-center py-12">No active alerts</p>
          ) : (
            <div className="divide-y divide-gray-800">
              {alertsData?.alerts?.map((alert) => (
                <div key={alert._id} className="p-6 hover:bg-gray-800 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className={`p-2 rounded-full ${getSeverityColor(alert.severity)}`}>
                        {getSeverityIcon(alert.severity)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-text-primary">
                            {getAlertTypeLabel(alert.alert_type)}
                          </h3>
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(alert.severity)}`}>
                            {alert.severity}
                          </span>
                        </div>
                        <p className="text-text-muted mb-2">{alert.message}</p>
                        <div className="flex items-center space-x-4 text-sm text-text-muted">
                          <span>Agent: {alert.agent_id?.substring(0, 8)}...</span>
                          <span>•</span>
                          <span>{alert.created_at ? format(new Date(alert.created_at), 'yyyy-MM-dd HH:mm') : 'N/A'}</span>
                        </div>
                        {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                          <div className="mt-3 p-3 bg-gray-800 rounded-md">
                            <pre className="text-xs text-text-muted overflow-x-auto">
                              {JSON.stringify(alert.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {alert.status === 'active' && (
                        <>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => acknowledgeMutation.mutate(alert._id)}
                            disabled={acknowledgeMutation.isLoading}
                          >
                            Acknowledge
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => resolveMutation.mutate({ alertId: alert._id, resolution: 'Resolved manually' })}
                            disabled={resolveMutation.isLoading}
                          >
                            Resolve
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}

export default AlertsCenter

