import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { BarChart3, TrendingUp, Target, Search, AlertCircle } from 'lucide-react'

const Intelligence = () => {
  const [overview, setOverview] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [competitors, setCompetitors] = useState([])
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [overviewRes, keywordsRes, competitorsRes, trendsRes] = await Promise.all([
        fetch('/api/intelligence/overview').then(r => r.json()),
        fetch('/api/intelligence/keywords').then(r => r.json()),
        fetch('/api/intelligence/competitors').then(r => r.json()),
        fetch('/api/intelligence/trends').then(r => r.json())
      ])

      setOverview(overviewRes)
      setKeywords(keywordsRes.keywords || [])
      setCompetitors(competitorsRes.competitors || [])
      setTrends(trendsRes)
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch intelligence data:', err)
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
        <h1 className="text-3xl font-bold text-text-primary">Competitive Intelligence</h1>
        <p className="text-text-muted mt-1">Industry insights and competitive analysis</p>
      </div>

      {/* Overview Stats */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Master Agents</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {overview.total_masters}
                  </div>
                </div>
                <Target className="w-8 h-8 text-primary-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Keywords Tracked</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {overview.total_keywords}
                  </div>
                </div>
                <Search className="w-8 h-8 text-blue-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">Competitors</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {overview.total_competitors}
                  </div>
                </div>
                <BarChart3 className="w-8 h-8 text-green-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-text-muted">SERP Results</div>
                  <div className="text-2xl font-bold text-text-primary mt-1">
                    {overview.total_serp_results}
                  </div>
                </div>
                <TrendingUp className="w-8 h-8 text-yellow-400" />
              </div>
            </Card.Body>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-4 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'overview'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('keywords')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'keywords'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          Keyword Rankings
        </button>
        <button
          onClick={() => setActiveTab('competitors')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'competitors'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          Competitive Positioning
        </button>
        <button
          onClick={() => setActiveTab('trends')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'trends'
              ? 'text-primary-400 border-b-2 border-primary-400'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          Trends & Insights
        </button>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && overview && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Keywords */}
            <Card>
              <Card.Header>
                <Card.Title>Top Keywords</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="space-y-3">
                  {overview.top_keywords.slice(0, 10).map((kw, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-800 rounded">
                      <div className="flex-1">
                        <div className="font-medium text-text-primary">{kw.keyword}</div>
                        <div className="text-sm text-text-muted">
                          {kw.agents_count} agents • {kw.frequency} appearances
                        </div>
                      </div>
                      <div className="text-primary-400 font-semibold">
                        #{idx + 1}
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>

            {/* Top Competitors */}
            <Card>
              <Card.Header>
                <Card.Title>Top Competitors</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="space-y-3">
                  {overview.top_competitors.slice(0, 10).map((comp, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-800 rounded">
                      <div className="flex-1">
                        <div className="font-medium text-text-primary">{comp.domain}</div>
                        <div className="text-sm text-text-muted">
                          Score: {comp.avg_score} • {comp.frequency} appearances
                        </div>
                      </div>
                      <div className="text-green-400 font-semibold">
                        #{idx + 1}
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          </div>
        )}

        {activeTab === 'keywords' && (
          <Card>
            <Card.Header>
              <Card.Title>Keyword Rankings</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-800 border-b border-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                        Keyword
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                        Master Domain
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                        Position
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                        Results
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                        Top Competitors
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {keywords.slice(0, 50).map((kw, idx) => (
                      <tr key={idx} className="hover:bg-gray-800">
                        <td className="px-4 py-3 text-text-primary font-medium">
                          {kw.keyword}
                        </td>
                        <td className="px-4 py-3 text-text-muted text-sm">
                          {kw.master_domain}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {kw.position ? (
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${
                              kw.position <= 3
                                ? 'bg-green-900/30 text-green-400'
                                : kw.position <= 10
                                ? 'bg-yellow-900/30 text-yellow-400'
                                : 'bg-red-900/30 text-red-400'
                            }`}>
                              #{kw.position}
                            </span>
                          ) : (
                            <span className="text-text-muted text-xs">N/A</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center text-text-muted text-sm">
                          {kw.total_results}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {kw.top_competitors.slice(0, 3).map((comp, cIdx) => (
                              <span
                                key={cIdx}
                                className="px-2 py-1 bg-gray-700 rounded text-xs text-text-muted"
                                title={`Position: ${comp.position}`}
                              >
                                {comp.domain}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        )}

        {activeTab === 'competitors' && (
          <Card>
            <Card.Header>
              <Card.Title>Competitive Positioning</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-800 border-b border-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                        Domain
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                        Appearances
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                        Avg Score
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                        Keywords
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                        Competing Masters
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {competitors.slice(0, 50).map((comp, idx) => (
                      <tr key={idx} className="hover:bg-gray-800">
                        <td className="px-4 py-3 text-text-primary font-medium">
                          {comp.domain}
                        </td>
                        <td className="px-4 py-3 text-center text-text-primary">
                          {comp.appearances}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="px-2 py-1 bg-blue-900/30 text-blue-400 rounded text-xs font-semibold">
                            {comp.avg_score}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center text-text-muted text-sm">
                          {comp.total_keywords}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {comp.masters_competing.slice(0, 3).map((master, mIdx) => (
                              <span
                                key={mIdx}
                                className="px-2 py-1 bg-gray-700 rounded text-xs text-text-muted"
                                title={`Score: ${master.score}`}
                              >
                                {master.domain}
                              </span>
                            ))}
                            {comp.masters_competing.length > 3 && (
                              <span className="px-2 py-1 bg-gray-700 rounded text-xs text-text-muted">
                                +{comp.masters_competing.length - 3}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        )}

        {activeTab === 'trends' && trends && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Trends Timeline */}
            <Card>
              <Card.Header>
                <Card.Title>Ranking Trends</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="space-y-4">
                  {trends.trends.slice(0, 10).map((trend, idx) => (
                    <div key={idx} className="p-4 bg-gray-800 rounded">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-text-primary">
                          {trend.master_domain}
                        </div>
                        <div className="text-sm text-text-muted">
                          {new Date(trend.date).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 mt-2">
                        <div>
                          <div className="text-xs text-text-muted">Results</div>
                          <div className="text-sm font-semibold text-text-primary">
                            {trend.results_count}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-text-muted">Avg Position</div>
                          <div className="text-sm font-semibold text-text-primary">
                            {trend.avg_position ? `#${trend.avg_position}` : 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-text-muted">Keywords</div>
                          <div className="text-sm font-semibold text-text-primary">
                            {trend.keywords_tracked}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>

            {/* Insights */}
            <Card>
              <Card.Header>
                <Card.Title>Insights</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="space-y-4">
                  {/* Top Performers */}
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center">
                      <TrendingUp className="w-5 h-5 text-green-400 mr-2" />
                      Top Performers
                    </h3>
                    <div className="space-y-2">
                      {trends.insights.top_performers.slice(0, 5).map((perf, idx) => (
                        <div key={idx} className="p-3 bg-gray-800 rounded">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium text-text-primary text-sm">
                                {perf.keyword}
                              </div>
                              <div className="text-xs text-text-muted">
                                {perf.domain}
                              </div>
                            </div>
                            <span className="px-2 py-1 bg-green-900/30 text-green-400 rounded text-xs font-semibold">
                              #{perf.position}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

export default Intelligence
