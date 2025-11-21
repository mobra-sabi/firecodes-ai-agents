import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  ArrowLeft, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  Trophy,
  Target,
  Activity,
  Calendar
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import {
  getRankingsStatistics,
  saveRankingsSnapshot,
  getRankingsTrend,
  getCompetitorLeaderboard,
  getRankingsHistory,
  getTrendBadge,
  formatPosition,
  getPositionColor
} from '../services/rankings'

const SERPDashboard = () => {
  const { agentId } = useParams()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [statistics, setStatistics] = useState(null)
  const [trend, setTrend] = useState(null)
  const [leaderboard, setLeaderboard] = useState([])
  const [history, setHistory] = useState([])
  const [selectedTab, setSelectedTab] = useState('overview')
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAllData()
  }, [agentId])

  const fetchAllData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [stats, trendData, competitorData, historyData] = await Promise.all([
        getRankingsStatistics(agentId),
        getRankingsTrend(agentId, 30).catch(() => null),
        getCompetitorLeaderboard(agentId).catch(() => ({ leaderboard: [] })),
        getRankingsHistory(agentId, 30).catch(() => ({ snapshots: [] }))
      ])

      setStatistics(stats)
      setTrend(trendData)
      setLeaderboard(competitorData.leaderboard || [])
      setHistory(historyData.snapshots || [])
    } catch (err) {
      console.error('Error fetching SERP data:', err)
      setError(err.message || 'Failed to load SERP dashboard')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      await saveRankingsSnapshot(agentId)
      setTimeout(() => fetchAllData(), 2000)
    } catch (err) {
      setError('Failed to refresh: ' + err.message)
    } finally {
      setRefreshing(false)
    }
  }

  const renderOverviewTab = () => {
    if (!statistics) return null

    const { 
      total_keywords, 
      total_serp_results, 
      unique_competitors,
      master_positions,
      average_position,
      deduplication_rate,
      competitor_leaderboard
    } = statistics

    return (
      <div className="space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-text-muted text-sm">Total Keywords</p>
                <Target className="w-5 h-5 text-accent-blue" />
              </div>
              <p className="text-4xl font-bold text-text-primary">{total_keywords || 0}</p>
            </div>
          </Card>

          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-text-muted text-sm">In Top 3</p>
                <Trophy className="w-5 h-5 text-accent-green" />
              </div>
              <p className="text-4xl font-bold text-accent-green">
                {master_positions?.top_3 || 0}
              </p>
              <p className="text-xs text-text-muted mt-1">
                {total_keywords > 0 
                  ? `${Math.round((master_positions?.top_3 || 0) / total_keywords * 100)}%` 
                  : '0%'}
              </p>
            </div>
          </Card>

          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-text-muted text-sm">Avg Position</p>
                <Activity className="w-5 h-5 text-accent-yellow" />
              </div>
              <p className="text-4xl font-bold text-text-primary">
                #{average_position?.toFixed(1) || 'N/A'}
              </p>
            </div>
          </Card>

          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-text-muted text-sm">Competitors</p>
                <AlertTriangle className="w-5 h-5 text-accent-red" />
              </div>
              <p className="text-4xl font-bold text-text-primary">{unique_competitors || 0}</p>
            </div>
          </Card>
        </div>

        {/* Trend Indicator */}
        {trend && (
          <Card>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                30-Day Trend Analysis
              </h3>
              <div className="flex items-center space-x-4">
                <div className={`px-4 py-2 rounded-lg ${getTrendBadge(trend.trend).color}`}>
                  <span className={`font-semibold ${getTrendBadge(trend.trend).textColor}`}>
                    {getTrendBadge(trend.trend).label}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="text-text-muted text-sm">Average Position Change</p>
                  <p className={`text-2xl font-bold ${
                    trend.average_position_change > 0 ? 'text-accent-green' : 
                    trend.average_position_change < 0 ? 'text-accent-red' : 'text-text-primary'
                  }`}>
                    {trend.average_position_change > 0 ? '+' : ''}
                    {trend.average_position_change?.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-text-muted text-sm">Top 10 Gained</p>
                  <p className="text-2xl font-bold text-accent-green">
                    +{trend.keywords_gained_top_10 || 0}
                  </p>
                </div>
                <div>
                  <p className="text-text-muted text-sm">Top 10 Lost</p>
                  <p className="text-2xl font-bold text-accent-red">
                    -{trend.keywords_lost_top_10 || 0}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Position Breakdown */}
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">
              Position Distribution
            </h3>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-4 bg-accent-green bg-opacity-10 rounded-lg border border-accent-green">
                <p className="text-3xl font-bold text-accent-green mb-1">
                  {master_positions?.top_3 || 0}
                </p>
                <p className="text-sm text-text-muted">Top 3</p>
              </div>
              <div className="text-center p-4 bg-accent-yellow bg-opacity-10 rounded-lg border border-accent-yellow">
                <p className="text-3xl font-bold text-accent-yellow mb-1">
                  {master_positions?.top_10 || 0}
                </p>
                <p className="text-sm text-text-muted">Top 10</p>
              </div>
              <div className="text-center p-4 bg-accent-red bg-opacity-10 rounded-lg border border-accent-red">
                <p className="text-3xl font-bold text-accent-red mb-1">
                  {master_positions?.top_20 || 0}
                </p>
                <p className="text-sm text-text-muted">Top 20</p>
              </div>
              <div className="text-center p-4 bg-gray-600 bg-opacity-10 rounded-lg border border-gray-600">
                <p className="text-3xl font-bold text-gray-600 mb-1">
                  {master_positions?.not_in_top_20 || 0}
                </p>
                <p className="text-sm text-text-muted">Not Ranked</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const renderKeywordsTab = () => {
    if (!statistics?.keywords_detail) return null

    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Keywords Performance ({statistics.keywords_detail.length})
          </h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {statistics.keywords_detail.map((kw, idx) => (
              <div 
                key={idx}
                className="flex items-center justify-between p-3 bg-dark-lighter rounded-lg hover:bg-dark-hover transition"
              >
                <div className="flex-1">
                  <p className="text-text-primary font-medium">{kw.keyword}</p>
                  <p className="text-xs text-text-muted">
                    {kw.serp_results_count} SERP results • {kw.unique_competitors_count} competitors
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <span className={`px-3 py-1 rounded-full text-white text-sm font-semibold ${
                    getPositionColor(kw.best_position)
                  }`}>
                    {formatPosition(kw.best_position)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  const renderCompetitorsTab = () => {
    if (leaderboard.length === 0) {
      return (
        <Card>
          <div className="p-6 text-center text-text-muted">
            No competitors data available yet
          </div>
        </Card>
      )
    }

    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Competitor Leaderboard ({leaderboard.length})
          </h3>
          <div className="space-y-3">
            {leaderboard.slice(0, 20).map((comp, idx) => (
              <div 
                key={idx}
                className="flex items-center justify-between p-4 bg-dark-lighter rounded-lg hover:bg-dark-hover transition"
              >
                <div className="flex items-center space-x-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
                    idx === 0 ? 'bg-accent-yellow' :
                    idx === 1 ? 'bg-gray-400' :
                    idx === 2 ? 'bg-orange-600' :
                    'bg-dark-hover'
                  }`}>
                    {idx + 1}
                  </div>
                  <div>
                    <p className="text-text-primary font-semibold">{comp.domain}</p>
                    <p className="text-xs text-text-muted">
                      {comp.appearances_top_10} appearances in Top 10
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-accent-blue">
                    #{comp.average_position.toFixed(1)}
                  </p>
                  <p className="text-xs text-text-muted">Avg Position</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  const renderHistoryTab = () => {
    if (history.length === 0) {
      return (
        <Card>
          <div className="p-6 text-center text-text-muted">
            <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No historical snapshots yet</p>
            <p className="text-sm mt-2">Click "Save Snapshot" to start tracking</p>
          </div>
        </Card>
      )
    }

    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Historical Snapshots ({history.length})
          </h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {history.map((snapshot, idx) => (
              <div 
                key={snapshot._id}
                className="flex items-center justify-between p-3 bg-dark-lighter rounded-lg"
              >
                <div>
                  <p className="text-text-primary font-medium">
                    {new Date(snapshot.timestamp).toLocaleString()}
                  </p>
                  <p className="text-xs text-text-muted">
                    {snapshot.total_keywords} keywords • {snapshot.unique_competitors} competitors
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-accent-green">
                    {snapshot.master_positions?.top_3 || 0} <span className="text-sm text-text-muted">top 3</span>
                  </p>
                  <p className="text-sm text-text-muted">
                    Avg: #{snapshot.average_position?.toFixed(1) || 'N/A'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-muted">Loading SERP Dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Card>
          <div className="p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-accent-red mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">Error</h2>
            <p className="text-text-muted">{error}</p>
            <Button onClick={fetchAllData} className="mt-4">
              Retry
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Link to={`/agent/${agentId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <h1 className="text-2xl font-bold text-text-primary">
            SERP Dashboard
          </h1>
        </div>
        <Button 
          onClick={handleRefresh} 
          disabled={refreshing}
          className="bg-accent-blue hover:bg-accent-blue-dark"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Saving...' : 'Save Snapshot'}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 mb-6 border-b border-dark-lighter">
        {['overview', 'keywords', 'competitors', 'history'].map(tab => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`px-4 py-2 font-medium transition ${
              selectedTab === tab
                ? 'text-accent-blue border-b-2 border-accent-blue'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
        {selectedTab === 'overview' && renderOverviewTab()}
        {selectedTab === 'keywords' && renderKeywordsTab()}
        {selectedTab === 'competitors' && renderCompetitorsTab()}
        {selectedTab === 'history' && renderHistoryTab()}
      </div>
    </div>
  )
}

export default SERPDashboard

