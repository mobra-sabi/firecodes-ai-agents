import { useState, useEffect } from 'react'
import { Search, TrendingUp, Globe, Star, ChevronDown, ChevronUp } from 'lucide-react'
import { getCompetitors, startSerpDiscovery } from '../../../services/workflows'
import Button from '../../ui/Button'
import Card from '../../ui/Card'

/**
 * Tab pentru Competitors - afișează lista de competitori discovered
 */
const CompetitorsTab = ({ agentId }) => {
  const [competitors, setCompetitors] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [expandedCompetitor, setExpandedCompetitor] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchCompetitors = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getCompetitors(agentId, 100) // Get up to 100 competitors
      setCompetitors(data.competitors || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (agentId) {
      fetchCompetitors()
    }
  }, [agentId])

  const handleRunDiscovery = async () => {
    try {
      setRunning(true)
      await startSerpDiscovery(agentId, 20) // Search 20 keywords
      // Refresh after 30 seconds to get results
      setTimeout(fetchCompetitors, 30000)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const filteredCompetitors = competitors.filter(comp =>
    comp.domain?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  if (competitors.length === 0) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">
            No Competitors Discovered Yet
          </h3>
          <p className="text-text-muted mb-6">
            Run SERP discovery to find competitors on Google
          </p>
          <Button
            onClick={handleRunDiscovery}
            loading={running}
            icon={<Search className="w-4 h-4" />}
          >
            Discover Competitors
          </Button>
        </Card.Body>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Discovered Competitors</h2>
          <p className="text-text-muted mt-1">
            {competitors.length} competitors found from SERP analysis
          </p>
        </div>
        <Button
          onClick={handleRunDiscovery}
          loading={running}
          icon={<Search className="w-4 h-4" />}
          variant="secondary"
        >
          Run Discovery
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search competitors by domain..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-text-primary placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-primary-400">{competitors.length}</div>
            <div className="text-xs text-text-muted mt-1">Total</div>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {competitors.filter(c => c.relevance_score > 70).length}
            </div>
            <div className="text-xs text-text-muted mt-1">High Relevance</div>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">
              {competitors.filter(c => c.appearances > 10).length}
            </div>
            <div className="text-xs text-text-muted mt-1">Frequent</div>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">
              {Math.round(competitors.reduce((sum, c) => sum + (c.relevance_score || 0), 0) / competitors.length)}%
            </div>
            <div className="text-xs text-text-muted mt-1">Avg Relevance</div>
          </Card.Body>
        </Card>
      </div>

      {/* Competitors List */}
      <div className="space-y-3">
        {filteredCompetitors.map((competitor, idx) => (
          <Card key={idx}>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4 flex-1">
                  {/* Rank */}
                  <div className="flex items-center justify-center w-10 h-10 bg-primary-700 rounded-full">
                    <span className="text-lg font-bold text-primary-300">#{idx + 1}</span>
                  </div>

                  {/* Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <Globe className="w-4 h-4 text-gray-400" />
                      <a
                        href={competitor.url || `https://${competitor.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-lg font-semibold text-text-primary hover:text-primary-400 transition-colors"
                      >
                        {competitor.domain}
                      </a>
                    </div>
                    <div className="flex items-center space-x-4 mt-1 text-sm text-text-muted">
                      <span>Appearances: {competitor.appearances || 0}</span>
                      <span>•</span>
                      <span>Relevance: {Math.round(competitor.relevance_score || 0)}%</span>
                    </div>
                  </div>

                  {/* Score Badge */}
                  <div className="flex items-center space-x-2">
                    <div
                      className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        (competitor.relevance_score || 0) > 70
                          ? 'bg-green-900/30 text-green-400 border border-green-700'
                          : (competitor.relevance_score || 0) > 40
                          ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-700'
                          : 'bg-gray-800 text-gray-400 border border-gray-700'
                      }`}
                    >
                      Score: {Math.round(competitor.relevance_score || 0)}
                    </div>
                    <button
                      onClick={() => setExpandedCompetitor(expandedCompetitor === idx ? null : idx)}
                      className="text-gray-400 hover:text-gray-200 transition-colors"
                    >
                      {expandedCompetitor === idx ? (
                        <ChevronUp className="w-5 h-5" />
                      ) : (
                        <ChevronDown className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedCompetitor === idx && (
                <div className="mt-4 pt-4 border-t border-gray-700 space-y-3">
                  {/* DeepSeek Validation */}
                  {competitor.deepseek_validated && (
                    <div>
                      <h5 className="text-sm font-semibold text-text-primary mb-2">
                        DeepSeek Validation
                      </h5>
                      <div className={`p-3 rounded-lg ${
                        competitor.deepseek_is_relevant
                          ? 'bg-green-900/20 border border-green-700'
                          : 'bg-red-900/20 border border-red-700'
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-semibold ${
                            competitor.deepseek_is_relevant ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {competitor.deepseek_is_relevant ? '✅ RELEVANT' : '❌ IRELEVANT'}
                          </span>
                          <span className="text-xs text-text-muted">
                            Confidence: {Math.round((competitor.deepseek_confidence || 0) * 100)}%
                          </span>
                        </div>
                        {competitor.deepseek_reason && (
                          <p className="text-xs text-text-muted mt-1">
                            {competitor.deepseek_reason}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Rankings by Keyword */}
                  {competitor.rankings_by_keyword && Object.keys(competitor.rankings_by_keyword).length > 0 && (
                    <div>
                      <h5 className="text-sm font-semibold text-text-primary mb-2">
                        Google Rankings (poziții reale)
                      </h5>
                      <div className="space-y-1">
                        {Object.entries(competitor.rankings_by_keyword).slice(0, 10).map(([keyword, rank]) => (
                          <div key={keyword} className="flex items-center justify-between text-xs">
                            <span className="text-text-muted truncate flex-1">{keyword}</span>
                            <span className={`ml-2 px-2 py-1 rounded ${
                              rank <= 3 ? 'bg-green-900/30 text-green-400' :
                              rank <= 10 ? 'bg-yellow-900/30 text-yellow-400' :
                              'bg-gray-800 text-gray-400'
                            }`}>
                              Rank {rank}
                            </span>
                          </div>
                        ))}
                        {Object.keys(competitor.rankings_by_keyword).length > 10 && (
                          <span className="text-xs text-text-muted">
                            +{Object.keys(competitor.rankings_by_keyword).length - 10} more keywords
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Keywords Matched */}
                  {competitor.keywords_matched && competitor.keywords_matched.length > 0 && (
                    <div>
                      <h5 className="text-sm font-semibold text-text-primary mb-2">
                        Keywords Matched ({competitor.keywords_matched.length})
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {competitor.keywords_matched.slice(0, 10).map((keyword, kidx) => (
                          <span
                            key={kidx}
                            className="px-2 py-1 bg-gray-800 text-gray-300 rounded text-xs"
                          >
                            {keyword}
                          </span>
                        ))}
                        {competitor.keywords_matched.length > 10 && (
                          <span className="px-2 py-1 text-gray-400 text-xs">
                            +{competitor.keywords_matched.length - 10} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* URL */}
                  {competitor.url && (
                    <div>
                      <h5 className="text-sm font-semibold text-text-primary mb-1">URL</h5>
                      <a
                        href={competitor.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-400 hover:text-blue-300 break-all"
                      >
                        {competitor.url}
                      </a>
                    </div>
                  )}

                  {/* Discovered Date */}
                  {competitor.discovered_at && (
                    <div>
                      <h5 className="text-sm font-semibold text-text-primary mb-1">Discovered</h5>
                      <p className="text-sm text-text-muted">
                        {new Date(competitor.discovered_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </Card.Body>
          </Card>
        ))}
      </div>

      {filteredCompetitors.length === 0 && searchTerm && (
        <div className="text-center py-8 text-text-muted">
          No competitors found matching "{searchTerm}"
        </div>
      )}
    </div>
  )
}

export default CompetitorsTab

