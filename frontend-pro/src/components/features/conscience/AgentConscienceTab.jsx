import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Brain, Activity, TrendingUp, AlertTriangle, BookOpen, Eye, RefreshCw, Loader2 } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const AgentConscienceTab = ({ agentId }) => {
  const [refreshing, setRefreshing] = useState(false)

  // Fetch conscience summary
  const { data: conscienceData, isLoading, refetch } = useQuery({
    queryKey: ['agent-conscience', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/conscience/summary`)
      return response.data
    },
    enabled: !!agentId,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch awareness feed
  const { data: awarenessData } = useQuery({
    queryKey: ['agent-awareness', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/conscience/awareness?hours=24`)
      return response.data
    },
    enabled: !!agentId,
  })

  // Fetch journal
  const { data: journalData } = useQuery({
    queryKey: ['agent-journal', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/conscience/journal?days=30`)
      return response.data
    },
    enabled: !!agentId,
  })

  const handleTriggerReflection = async () => {
    setRefreshing(true)
    try {
      await api.post(`/agents/${agentId}/conscience/reflect`)
      await refetch()
    } catch (error) {
      console.error('Error triggering reflection:', error)
    } finally {
      setRefreshing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent-blue" />
      </div>
    )
  }

  const summary = conscienceData?.summary || {}
  const state = summary.state || {}
  const health = summary.health || {}
  const reflection = summary.latest_reflection || {}
  const awareness = summary.awareness || {}
  const journalStats = summary.journal_stats || {}

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Brain className="w-6 h-6 text-accent-blue" />
            Agent Conscience
          </h2>
          <p className="text-text-muted mt-1">
            Self-awareness, state awareness, and temporal awareness
          </p>
        </div>
        <Button
          onClick={handleTriggerReflection}
          disabled={refreshing}
          icon={refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
        >
          Trigger Reflection
        </Button>
      </div>

      {/* Health Scores */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">SEO Health</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {health.seo_health?.toFixed(0) || 'N/A'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              (health.seo_health || 0) >= 70 ? 'bg-accent-green bg-opacity-20' :
              (health.seo_health || 0) >= 40 ? 'bg-accent-yellow bg-opacity-20' :
              'bg-accent-red bg-opacity-20'
            }`}>
              <TrendingUp className={`w-6 h-6 ${
                (health.seo_health || 0) >= 70 ? 'text-accent-green' :
                (health.seo_health || 0) >= 40 ? 'text-accent-yellow' :
                'text-accent-red'
              }`} />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Ads Health</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {health.ads_health?.toFixed(0) || 'N/A'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              (health.ads_health || 0) >= 50 ? 'bg-accent-green bg-opacity-20' : 'bg-accent-red bg-opacity-20'
            }`}>
              <Activity className={`w-6 h-6 ${
                (health.ads_health || 0) >= 50 ? 'text-accent-green' : 'text-accent-red'
              }`} />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Opportunity</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {health.opportunity_level?.toFixed(0) || 'N/A'}
              </p>
            </div>
            <div className="w-12 h-12 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-accent-blue" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Risk Level</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {health.risk_level?.toFixed(0) || 'N/A'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              (health.risk_level || 0) >= 50 ? 'bg-accent-red bg-opacity-20' : 'bg-accent-green bg-opacity-20'
            }`}>
              <AlertTriangle className={`w-6 h-6 ${
                (health.risk_level || 0) >= 50 ? 'text-accent-red' : 'text-accent-green'
              }`} />
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current State */}
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent-blue" />
            Current State
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-text-muted">Status</p>
              <p className="text-text-primary font-medium">{state.current_status || 'Unknown'}</p>
            </div>
            {state.last_update && (
              <div>
                <p className="text-sm text-text-muted">Last Update</p>
                <p className="text-text-primary font-medium">
                  {new Date(state.last_update).toLocaleString()}
                </p>
              </div>
            )}
            {state.detected_changes && state.detected_changes.length > 0 && (
              <div>
                <p className="text-sm text-text-muted">Recent Changes</p>
                <p className="text-text-primary font-medium">{state.detected_changes.length} changes detected</p>
              </div>
            )}
          </div>
        </Card>

        {/* Latest Reflection */}
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-accent-blue" />
            Latest Self-Reflection
          </h3>
          {reflection.reflection ? (
            <div className="space-y-3">
              <div className="bg-primary-800 p-4 rounded-lg">
                <p className="text-sm text-text-muted whitespace-pre-wrap">
                  {reflection.reflection.substring(0, 500)}
                  {reflection.reflection.length > 500 && '...'}
                </p>
              </div>
              {reflection.reflected_at && (
                <p className="text-xs text-text-muted">
                  {new Date(reflection.reflected_at).toLocaleString()}
                </p>
              )}
              {reflection.recommendations && reflection.recommendations.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-text-primary mb-2">Recommendations:</p>
                  <ul className="list-disc list-inside text-sm text-text-muted space-y-1">
                    {reflection.recommendations.slice(0, 3).map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-text-muted">No reflection available. Click "Trigger Reflection" to generate one.</p>
          )}
        </Card>

        {/* Awareness Feed */}
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Eye className="w-5 h-5 text-accent-blue" />
            Awareness Feed (24h)
          </h3>
          {awarenessData?.feed && awarenessData.feed.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {awarenessData.feed.slice(0, 10).map((entry, idx) => (
                <div key={idx} className="bg-primary-800 p-3 rounded-lg">
                  <div className="flex items-start justify-between mb-1">
                    <span className={`text-xs px-2 py-1 rounded ${
                      entry.importance === 'high' ? 'bg-accent-red bg-opacity-20 text-accent-red' :
                      entry.importance === 'medium' ? 'bg-accent-yellow bg-opacity-20 text-accent-yellow' :
                      'bg-primary-700 text-text-muted'
                    }`}>
                      {entry.category}
                    </span>
                    <span className="text-xs text-text-muted">
                      {new Date(entry.discovered_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm text-text-primary">{entry.discovery}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-text-muted">No discoveries in the last 24 hours</p>
          )}
        </Card>

        {/* Journal Stats */}
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-accent-blue" />
            Journal Statistics
          </h3>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-text-muted">Total Entries (30 days)</p>
              <p className="text-2xl font-bold text-text-primary">{journalStats.total_entries || 0}</p>
            </div>
            {journalStats.by_type && Object.keys(journalStats.by_type).length > 0 && (
              <div>
                <p className="text-sm text-text-muted mb-2">By Type</p>
                <div className="space-y-1">
                  {Object.entries(journalStats.by_type).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-sm">
                      <span className="text-text-muted">{type}</span>
                      <span className="text-text-primary font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Awareness Summary */}
      {awarenessData?.summary && (
        <Card>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Awareness Summary (7 days)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-text-muted">Total Discoveries</p>
              <p className="text-2xl font-bold text-text-primary">{awarenessData.summary.total_discoveries || 0}</p>
            </div>
            {awarenessData.summary.by_importance && (
              <>
                <div>
                  <p className="text-sm text-text-muted">High Importance</p>
                  <p className="text-2xl font-bold text-accent-red">{awarenessData.summary.by_importance.high || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Medium Importance</p>
                  <p className="text-2xl font-bold text-accent-yellow">{awarenessData.summary.by_importance.medium || 0}</p>
                </div>
              </>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

export default AgentConscienceTab

