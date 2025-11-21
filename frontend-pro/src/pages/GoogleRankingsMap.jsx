import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import {
  getGoogleRankingsMap,
  getGoogleAdsStrategy,
  getSlaveAgents,
  startSerpDiscoveryWithSlaves
} from '../services/workflows'

const GoogleRankingsMap = () => {
  const { agentId } = useParams()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [rankingsData, setRankingsData] = useState(null)
  const [adsStrategy, setAdsStrategy] = useState(null)
  const [slaveAgents, setSlaveAgents] = useState([])
  const [selectedTab, setSelectedTab] = useState('grid')
  const [selectedKeyword, setSelectedKeyword] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAllData()
  }, [agentId])

  const fetchAllData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [rankings, strategy, slaves] = await Promise.all([
        getGoogleRankingsMap(agentId),
        getGoogleAdsStrategy(agentId).catch(() => null),
        getSlaveAgents(agentId).catch(() => [])
      ])

      setRankingsData(rankings)
      setAdsStrategy(strategy)
      setSlaveAgents(slaves)
    } catch (err) {
      console.error('Error fetching data:', err)
      setError(err.message || 'Failed to load rankings data')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      await startSerpDiscoveryWithSlaves(agentId)
      setTimeout(() => fetchAllData(), 3000)
    } catch (err) {
      setError('Failed to start refresh: ' + err.message)
    } finally {
      setRefreshing(false)
    }
  }

  const getPositionColor = (position) => {
    if (!position) return 'bg-gray-600'
    if (position <= 3) return 'bg-accent-green'
    if (position <= 10) return 'bg-accent-yellow'
    return 'bg-accent-red'
  }

  const getPositionBadge = (position) => {
    if (!position) return 'Not in Top 20'
    return `#${position}`
  }

  const getPriorityLabel = (position) => {
    if (!position) return { label: 'CRITICAL', color: 'bg-accent-red' }
    if (position <= 3) return { label: 'LOW', color: 'bg-accent-green' }
    if (position <= 10) return { label: 'MEDIUM', color: 'bg-accent-yellow' }
    return { label: 'HIGH', color: 'bg-accent-red' }
  }

  const renderSummary = () => {
    if (!rankingsData?.summary) return null

    const { summary } = rankingsData

    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <div className="p-6">
            <p className="text-text-muted text-sm mb-2">Total Keywords</p>
            <p className="text-4xl font-bold text-text-primary">{summary.total_keywords || 0}</p>
          </div>
        </Card>
        <Card>
          <div className="p-6">
            <p className="text-text-muted text-sm mb-2">In Top 3</p>
            <p className="text-4xl font-bold text-accent-green">{summary.top_3_count || 0}</p>
          </div>
        </Card>
        <Card>
          <div className="p-6">
            <p className="text-text-muted text-sm mb-2">In Top 10</p>
            <p className="text-4xl font-bold text-accent-yellow">{summary.top_10_count || 0}</p>
          </div>
        </Card>
        <Card>
          <div className="p-6">
            <p className="text-text-muted text-sm mb-2">Not in Top 20</p>
            <p className="text-4xl font-bold text-accent-red">{summary.not_in_top_20_count || 0}</p>
          </div>
        </Card>
      </div>
    )
  }

  const renderRankingsGrid = () => {
    if (!rankingsData || !rankingsData.keywords_data) {
      return (
        <Card>
          <div className="p-6 text-center">
            <p className="text-text-muted">No rankings data available. Click refresh to generate.</p>
          </div>
        </Card>
      )
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rankingsData.keywords_data.map((kwData, index) => {
          const position = kwData.master_position
          const priority = getPriorityLabel(position)
          const color = getPositionColor(position)

          return (
            <Card
              key={index}
              className="cursor-pointer hover:shadow-lg transition-shadow border-l-4"
              style={{ borderLeftColor: color.replace('bg-', '#') }}
              onClick={() => setSelectedKeyword(kwData)}
            >
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-text-primary">{kwData.keyword}</h3>
                  {position <= 3 ? (
                    <TrendingUp className="text-accent-green" size={20} />
                  ) : (
                    <TrendingDown className="text-accent-red" size={20} />
                  )}
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-3xl font-bold ${color.replace('bg-', 'text-')}`}>
                    {getPositionBadge(position)}
                  </span>
                </div>

                <div className="flex gap-2 mb-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${priority.color} bg-opacity-20`}>
                    {priority.label}
                  </span>
                  <span className="px-2 py-1 rounded text-xs font-medium bg-primary-700 text-text-muted">
                    {kwData.total_results || 20} results
                  </span>
                </div>

                <p className="text-text-muted text-sm mb-2">Top 3 Competitors:</p>
                {kwData.top_3_competitors?.slice(0, 3).map((comp, i) => (
                  <p
                    key={i}
                    className="text-xs text-text-muted truncate"
                  >
                    #{comp.position}: {comp.domain}
                  </p>
                ))}

                {kwData.gap_to_top_10 > 0 && (
                  <div className="mt-3 p-2 bg-blue-500 bg-opacity-10 rounded text-xs text-blue-400">
                    {kwData.gap_to_top_10} positions to top 10
                  </div>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    )
  }

  const renderKeywordDetail = () => {
    if (!selectedKeyword) {
      return (
        <Card>
          <div className="p-6 text-center">
            <p className="text-text-muted">Click on a keyword to see detailed rankings</p>
          </div>
        </Card>
      )
    }

    return (
      <Card>
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-text-primary">
              "{selectedKeyword.keyword}" - Detailed Rankings
            </h2>
            <Button variant="secondary" onClick={() => setSelectedKeyword(null)}>
              Back to Grid
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-primary-700">
                  <th className="px-4 py-3 text-left text-text-muted">Position</th>
                  <th className="px-4 py-3 text-left text-text-muted">Domain</th>
                  <th className="px-4 py-3 text-left text-text-muted">Title</th>
                  <th className="px-4 py-3 text-left text-text-muted">Actions</th>
                </tr>
              </thead>
              <tbody>
                {selectedKeyword.serp_results?.map((result, index) => (
                  <tr
                    key={index}
                    className={`border-b border-primary-700 ${
                      result.is_master ? 'bg-accent-green bg-opacity-10' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getPositionColor(result.position)} text-white`}>
                        #{result.position}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      {result.domain}
                      {result.is_master && (
                        <span className="ml-2 px-2 py-1 bg-accent-green bg-opacity-20 text-accent-green text-xs rounded">
                          YOU
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-muted max-w-md truncate">
                      {result.title}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => window.open(result.url, '_blank')}
                        className="text-accent-blue hover:text-accent-purple"
                      >
                        <ExternalLink size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    )
  }

  const renderStrategyPanel = () => {
    if (!adsStrategy) {
      return (
        <Card>
          <div className="p-6 text-center">
            <p className="text-text-muted">
              No Google Ads strategy generated yet. Refresh rankings to generate strategy.
            </p>
          </div>
        </Card>
      )
    }

    return (
      <div className="space-y-6">
        <Card>
          <div className="p-6">
            <h2 className="text-2xl font-bold text-text-primary mb-4">Google Ads Strategy</h2>
            <p className="text-text-muted mb-6">{adsStrategy.executive_summary}</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-primary-700 rounded">
                <p className="text-text-muted text-sm mb-1">Total Budget</p>
                <p className="text-2xl font-bold text-text-primary">
                  {adsStrategy.budget_total || '$3000-5000/mo'}
                </p>
              </div>
              <div className="p-4 bg-primary-700 rounded">
                <p className="text-text-muted text-sm mb-1">Priority Keywords</p>
                <p className="text-2xl font-bold text-text-primary">
                  {adsStrategy.priority_actions?.length || 0}
                </p>
              </div>
              <div className="p-4 bg-primary-700 rounded">
                <p className="text-text-muted text-sm mb-1">Expected ROI</p>
                <p className="text-2xl font-bold text-text-primary">
                  {adsStrategy.expected_roi || '250-300%'}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <h3 className="text-xl font-bold text-text-primary mb-4">Priority Actions</h3>
            <div className="space-y-4">
              {adsStrategy.priority_actions?.map((action, index) => (
                <div key={index} className="p-4 bg-primary-700 rounded">
                  <h4 className="font-semibold text-text-primary mb-2">
                    {action.keyword || action.title}
                  </h4>
                  <p className="text-text-muted text-sm mb-2">
                    {action.recommendation || action.description}
                  </p>
                  {action.bid_range && (
                    <span className="px-2 py-1 bg-accent-blue bg-opacity-20 text-accent-blue text-xs rounded">
                      Bid: {action.bid_range}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-purple"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <Link to={`/agents/${agentId}`}>
          <Button variant="ghost" icon={<ArrowLeft className="w-4 h-4" />} className="mb-4">
            Back to Agent
          </Button>
        </Link>

        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-text-primary">Google Rankings Map</h1>
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            icon={<RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />}
          >
            {refreshing ? 'Refreshing...' : 'Refresh Rankings'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-accent-red bg-opacity-10 border border-accent-red rounded text-accent-red">
          {error}
        </div>
      )}

      {renderSummary()}

      <div className="flex border-b border-primary-700 mb-6">
        {['grid', 'detail', 'strategy', 'slaves'].map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`px-4 py-2 font-medium transition-colors ${
              selectedTab === tab
                ? 'text-accent-purple border-b-2 border-accent-purple'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {selectedTab === 'grid' && renderRankingsGrid()}
      {selectedTab === 'detail' && renderKeywordDetail()}
      {selectedTab === 'strategy' && renderStrategyPanel()}
      {selectedTab === 'slaves' && (
        <Card>
          <div className="p-6">
            <h3 className="text-xl font-bold text-text-primary mb-4">
              Competitor Agents (Slaves)
            </h3>
            <p className="text-text-muted mb-4">
              Total: {slaveAgents.length} competitor agents created
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {slaveAgents.map((slave, index) => (
                <div key={index} className="p-4 bg-primary-700 rounded">
                  <h4 className="font-semibold text-text-primary mb-1">{slave.domain}</h4>
                  <p className="text-text-muted text-xs">
                    Created: {new Date(slave.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

export default GoogleRankingsMap
