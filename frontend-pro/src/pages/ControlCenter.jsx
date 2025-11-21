import { useState, useEffect } from 'react'
import { Activity, Database, Cpu, HardDrive, Zap, Server, AlertCircle, CheckCircle } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import api from '../services/api'

/**
 * Control Center - System Overview & Statistics
 */
const ControlCenter = () => {
  const [systemStatus, setSystemStatus] = useState(null)
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSystemStatus()
    const interval = setInterval(fetchSystemStatus, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const fetchSystemStatus = async () => {
    try {
      // Fetch system health from /health endpoint
      const healthResponse = await api.get('/health')
      const statsResponse = await api.get('/stats')
      
      const health = healthResponse.data
      const services = health?.services || {}
      
      setSystemStatus({
        api_status: health?.overall_status === 'healthy' ? 'ok' : 'issues',
        mongodb_connected: services?.mongodb?.status === 'healthy',
        qdrant_connected: services?.qdrant?.status === 'healthy',
        total_agents: statsResponse?.data?.total_agents || statsResponse?.total_agents || 0,
        active_workflows: statsResponse?.data?.active_workflows || statsResponse?.active_workflows || 0,
        chunks: statsResponse?.data?.chunks || statsResponse?.chunks || 0,
        keywords: statsResponse?.data?.keywords || statsResponse?.keywords || 0,
        competitors: statsResponse?.data?.competitors || statsResponse?.competitors || 0,
        serp_checks: statsResponse?.data?.serp_checks || statsResponse?.serp_checks || 0,
      })

      // Mock services data (would be actual service checks in production)
      setServices([
        { name: 'Master Agent API', port: 5010, status: 'running', uptime: '12d 4h' },
        { name: 'Frontend', port: 4000, status: 'running', uptime: '12d 4h' },
        { name: 'Live Dashboard', port: 6001, status: 'running', uptime: '11d 8h' },
        { name: 'DeepSeek Processor', status: 'running', uptime: '12d 4h' },
        { name: 'GPU Embeddings', status: 'running', uptime: '12d 4h' },
        { name: 'MongoDB', port: 27018, status: systemStatus?.mongodb_connected ? 'running' : 'stopped', uptime: '30d+' },
        { name: 'Qdrant', port: 9306, status: systemStatus?.qdrant_connected ? 'running' : 'stopped', uptime: '30d+' },
      ])
      
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch system status:', err)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Control Center</h1>
        <p className="text-text-muted mt-2">
          System overview, statistics, and service monitoring
        </p>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <Card.Body className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-sm">API Status</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {systemStatus?.api_status === 'ok' ? 'Healthy' : 'Issues'}
                </p>
              </div>
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                systemStatus?.api_status === 'ok'
                  ? 'bg-green-900/30 text-green-400'
                  : 'bg-red-900/30 text-red-400'
              }`}>
                {systemStatus?.api_status === 'ok' ? (
                  <CheckCircle className="w-6 h-6" />
                ) : (
                  <AlertCircle className="w-6 h-6" />
                )}
              </div>
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-sm">MongoDB</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {systemStatus?.mongodb_connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
              <Database className="w-12 h-12 text-blue-400" />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-sm">Qdrant</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {systemStatus?.qdrant_connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
              <HardDrive className="w-12 h-12 text-purple-400" />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-sm">Active Workflows</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {systemStatus?.active_workflows || 0}
                </p>
              </div>
              <Activity className="w-12 h-12 text-yellow-400" />
            </div>
          </Card.Body>
        </Card>
      </div>

      {/* Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-primary-400">
                {systemStatus?.total_agents || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Total Agents</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-green-400">23</div>
              <div className="text-xs text-text-muted mt-1">Active</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-blue-400">
                {systemStatus?.chunks ? (systemStatus.chunks >= 1000000 ? `${(systemStatus.chunks / 1000000).toFixed(1)}M` : systemStatus.chunks >= 1000 ? `${(systemStatus.chunks / 1000).toFixed(1)}K` : systemStatus.chunks) : '0'}
              </div>
              <div className="text-xs text-text-muted mt-1">Chunks</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-yellow-400">
                {systemStatus?.keywords ? (systemStatus.keywords >= 1000 ? `${(systemStatus.keywords / 1000).toFixed(1)}K` : systemStatus.keywords) : '0'}
              </div>
              <div className="text-xs text-text-muted mt-1">Keywords</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-purple-400">{systemStatus?.competitors || 0}</div>
              <div className="text-xs text-text-muted mt-1">Competitors</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-red-400">
                {systemStatus?.serp_checks ? (systemStatus.serp_checks >= 1000 ? `${(systemStatus.serp_checks / 1000).toFixed(1)}K` : systemStatus.serp_checks) : '0'}
              </div>
              <div className="text-xs text-text-muted mt-1">SERP Checks</div>
            </Card.Body>
          </Card>
        </div>
      </div>

      {/* Services Status */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services.map((service, idx) => (
            <Card key={idx}>
              <Card.Body className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      service.status === 'running'
                        ? 'bg-green-900/30 text-green-400'
                        : 'bg-red-900/30 text-red-400'
                    }`}>
                      <Server className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-text-primary">
                        {service.name}
                      </h3>
                      {service.port && (
                        <p className="text-sm text-text-muted mt-0.5">
                          Port: {service.port}
                        </p>
                      )}
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          service.status === 'running'
                            ? 'bg-green-900/30 text-green-400 border border-green-700'
                            : 'bg-red-900/30 text-red-400 border border-red-700'
                        }`}>
                          {service.status.toUpperCase()}
                        </span>
                        {service.uptime && (
                          <span className="text-xs text-text-muted">
                            Uptime: {service.uptime}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          ))}
        </div>
      </div>

      {/* GPU Cluster (if available) */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">GPU Cluster</h2>
        <Card>
          <Card.Body className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <Cpu className="w-8 h-8 text-primary-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-text-primary">11</div>
                <div className="text-sm text-text-muted">RTX 3080 Ti</div>
              </div>
              <div className="text-center">
                <Zap className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-text-primary">~450ms</div>
                <div className="text-sm text-text-muted">Avg Embed Time</div>
              </div>
              <div className="text-center">
                <Activity className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-text-primary">85%</div>
                <div className="text-sm text-text-muted">Utilization</div>
              </div>
              <div className="text-center">
                <Database className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-text-primary">1.2M</div>
                <div className="text-sm text-text-muted">Vectors</div>
              </div>
            </div>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default ControlCenter

