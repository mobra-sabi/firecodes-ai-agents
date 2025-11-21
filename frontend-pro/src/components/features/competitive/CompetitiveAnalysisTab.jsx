import { useState, useEffect } from 'react'
import { RefreshCw, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react'
import { getCompetitiveAnalysis, startCompetitiveAnalysis } from '../../../services/workflows'
import Button from '../../ui/Button'
import Card from '../../ui/Card'

/**
 * Tab pentru Competitive Analysis - afișează subdomenii și keywords
 */
const CompetitiveAnalysisTab = ({ agentId }) => {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const fetchAnalysis = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getCompetitiveAnalysis(agentId)
      setAnalysis(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (agentId) {
      fetchAnalysis()
    }
  }, [agentId])

  const handleRunAnalysis = async () => {
    try {
      setRunning(true)
      await startCompetitiveAnalysis(agentId)
      // Refresh after 5 seconds to get results
      setTimeout(fetchAnalysis, 5000)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400">{error}</p>
          <Button onClick={fetchAnalysis} className="mt-4">
            Retry
          </Button>
        </Card.Body>
      </Card>
    )
  }

  if (!analysis?.exists) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <TrendingUp className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">
            No Competitive Analysis Yet
          </h3>
          <p className="text-text-muted mb-6">
            Run competitive analysis to identify subdomains and keywords
          </p>
          <Button
            onClick={handleRunAnalysis}
            loading={running}
            icon={<TrendingUp className="w-4 h-4" />}
          >
            Run Analysis
          </Button>
        </Card.Body>
      </Card>
    )
  }

  const analysisData = analysis.analysis || {}
  const subdomains = analysisData.subdomains || []
  const keywords = analysisData.keywords || []

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Competitive Analysis</h2>
          <p className="text-text-muted mt-1">
            Subdomains and keywords identified for competitive intelligence
          </p>
        </div>
        <Button
          onClick={handleRunAnalysis}
          loading={running}
          icon={<RefreshCw className="w-4 h-4" />}
          variant="secondary"
        >
          Refresh
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <Card.Body className="p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary-400">{subdomains.length}</div>
              <div className="text-sm text-text-muted mt-1">Subdomains</div>
            </div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-400">
                {subdomains.reduce((sum, s) => sum + (s.keywords?.length || 0), 0)}
              </div>
              <div className="text-sm text-text-muted mt-1">Keywords (Subdomain)</div>
            </div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-400">{keywords.length}</div>
              <div className="text-sm text-text-muted mt-1">General Keywords</div>
            </div>
          </Card.Body>
        </Card>
      </div>

      {/* Subdomains */}
      {subdomains.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-text-primary mb-4">
            📦 Subdomains ({subdomains.length})
          </h3>
          <div className="space-y-4">
            {subdomains.map((subdomain, idx) => (
              <Card key={idx}>
                <Card.Body className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-text-primary">
                        {subdomain.name || `Subdomain ${idx + 1}`}
                      </h4>
                      {subdomain.description && (
                        <p className="text-sm text-text-muted mt-1">
                          {subdomain.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center space-x-2 text-sm">
                      <span className="px-3 py-1 bg-primary-700 text-primary-300 rounded-full">
                        {subdomain.keywords?.length || 0} keywords
                      </span>
                    </div>
                  </div>

                  {/* Keywords for this subdomain */}
                  {subdomain.keywords && subdomain.keywords.length > 0 && (
                    <div className="mt-4">
                      <div className="flex flex-wrap gap-2">
                        {subdomain.keywords.map((keyword, kidx) => (
                          <span
                            key={kidx}
                            className="px-3 py-1 bg-gray-800 text-gray-300 rounded-full text-sm"
                          >
                            🔑 {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </Card.Body>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* General Keywords */}
      {keywords.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold text-text-primary mb-4">
            🌐 General Keywords ({keywords.length})
          </h3>
          <Card>
            <Card.Body className="p-6">
              <div className="flex flex-wrap gap-2">
                {keywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 bg-blue-900/30 text-blue-300 border border-blue-700 rounded-full text-sm"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </Card.Body>
          </Card>
        </div>
      )}
    </div>
  )
}

export default CompetitiveAnalysisTab

