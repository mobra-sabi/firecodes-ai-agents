import { useState, useEffect } from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Minus, BarChart2 } from 'lucide-react'
import { getSerpRankings, refreshSerpRankings, getSerpHistory } from '../../../services/workflows'
import Button from '../../ui/Button'
import Card from '../../ui/Card'

/**
 * Tab pentru SERP Rankings - afișează pozițiile în Google pentru keywords
 */
const SerpRankingsTab = ({ agentId }) => {
  const [rankings, setRankings] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [selectedKeyword, setSelectedKeyword] = useState(null)

  const fetchRankings = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getSerpRankings(agentId)
      // Transformă datele pentru a se potrivi cu formatul așteptat
      const formattedRankings = (data.rankings || []).map(r => ({
        keyword: r.keyword || r.query || '',
        current_position: r.rank || r.position || 0,
        previous_position: r.previous_rank || null,
        url: r.url || '',
        domain: r.domain || '',
        title: r.title || '',
        snippet: r.snippet || '',
        is_master: r.is_master || false
      }))
      setRankings(formattedRankings)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async (keyword) => {
    try {
      const data = await getSerpHistory(agentId, keyword, 30) // Last 30 days
      setHistory(data.history || [])
      setSelectedKeyword(keyword)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  useEffect(() => {
    if (agentId) {
      fetchRankings()
    }
  }, [agentId])

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      await refreshSerpRankings(agentId)
      setTimeout(fetchRankings, 5000)
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  const getRankTrend = (ranking) => {
    if (!ranking.previous_position) return 'new'
    const change = ranking.previous_position - ranking.current_position
    if (change > 0) return 'up'
    if (change < 0) return 'down'
    return 'stable'
  }

  const getTrendIcon = (trend) => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4 text-green-400" />
    if (trend === 'down') return <TrendingDown className="w-4 h-4 text-red-400" />
    if (trend === 'new') return <BarChart2 className="w-4 h-4 text-blue-400" />
    return <Minus className="w-4 h-4 text-gray-400" />
  }

  const getTrendBadge = (trend, change) => {
    if (trend === 'up') {
      return (
        <span className="px-2 py-1 bg-green-900/30 text-green-400 border border-green-700 rounded text-xs font-semibold">
          +{Math.abs(change)}
        </span>
      )
    }
    if (trend === 'down') {
      return (
        <span className="px-2 py-1 bg-red-900/30 text-red-400 border border-red-700 rounded text-xs font-semibold">
          {change}
        </span>
      )
    }
    if (trend === 'new') {
      return (
        <span className="px-2 py-1 bg-blue-900/30 text-blue-400 border border-blue-700 rounded text-xs">
          NEW
        </span>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  if (rankings.length === 0) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <BarChart2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">
            No SERP Rankings Yet
          </h3>
          <p className="text-text-muted mb-6">
            Refresh rankings to see your position on Google
          </p>
          <Button
            onClick={handleRefresh}
            loading={refreshing}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Check Rankings
          </Button>
        </Card.Body>
      </Card>
    )
  }

  // Stats
  const topRankings = rankings.filter(r => r.current_position <= 10).length
  const avgPosition = Math.round(
    rankings.reduce((sum, r) => sum + r.current_position, 0) / rankings.length
  )
  const improving = rankings.filter(r => getRankTrend(r) === 'up').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">SERP Rankings</h2>
          <p className="text-text-muted mt-1">
            Google search positions for {rankings.length} keywords
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          loading={refreshing}
          icon={<RefreshCw className="w-4 h-4" />}
          variant="secondary"
        >
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-primary-400">{rankings.length}</div>
            <div className="text-xs text-text-muted mt-1">Tracked Keywords</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-green-400">{topRankings}</div>
            <div className="text-xs text-text-muted mt-1">Top 10</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">{avgPosition}</div>
            <div className="text-xs text-text-muted mt-1">Avg Position</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">{improving}</div>
            <div className="text-xs text-text-muted mt-1">Improving</div>
          </Card.Body>
        </Card>
      </div>

      {/* Rankings Table */}
      <Card>
        <Card.Body className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800 border-b border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Keyword
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Position
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Change
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Trend
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Last Check
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {rankings.map((ranking, idx) => {
                  const trend = getRankTrend(ranking)
                  const change = ranking.previous_position 
                    ? ranking.previous_position - ranking.current_position
                    : 0
                  
                  return (
                    <tr
                      key={idx}
                      className="hover:bg-gray-800/50 transition-colors cursor-pointer"
                      onClick={() => fetchHistory(ranking.keyword)}
                    >
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-text-primary">
                          {ranking.keyword}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold ${
                            ranking.current_position <= 3
                              ? 'bg-green-900/30 text-green-400 border border-green-700'
                              : ranking.current_position <= 10
                              ? 'bg-blue-900/30 text-blue-400 border border-blue-700'
                              : 'bg-gray-800 text-gray-400 border border-gray-700'
                          }`}
                        >
                          #{ranking.current_position}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {getTrendBadge(trend, change)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center">
                          {getTrendIcon(trend)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right text-sm text-text-muted">
                        {ranking.checked_at
                          ? new Date(ranking.checked_at).toLocaleDateString()
                          : 'N/A'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card.Body>
      </Card>

      {/* History Chart (Simple visualization) */}
      {selectedKeyword && history.length > 0 && (
        <Card>
          <Card.Body className="p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">
              History for "{selectedKeyword}"
            </h3>
            <div className="space-y-2">
              {history.slice(0, 10).map((entry, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <span className="text-text-muted">
                    {new Date(entry.date).toLocaleDateString()}
                  </span>
                  <span className="text-text-primary font-semibold">
                    Position #{entry.position}
                  </span>
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

export default SerpRankingsTab

