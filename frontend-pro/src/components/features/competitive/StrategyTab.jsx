import { useState, useEffect } from 'react'
import { Target, TrendingUp, Shield, Zap, AlertTriangle, CheckCircle } from 'lucide-react'
import { getCompetitiveStrategy } from '../../../services/workflows'
import Button from '../../ui/Button'
import Card from '../../ui/Card'

/**
 * Tab pentru Competitive Strategy - afișează strategiile per service
 */
const StrategyTab = ({ agentId }) => {
  const [strategy, setStrategy] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedService, setExpandedService] = useState(null)

  const fetchStrategy = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getCompetitiveStrategy(agentId)
      setStrategy(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (agentId) {
      fetchStrategy()
    }
  }, [agentId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  if (!strategy?.exists) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <Target className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">
            No Strategy Generated Yet
          </h3>
          <p className="text-text-muted mb-6">
            Run competitive analysis to generate strategic recommendations
          </p>
        </Card.Body>
      </Card>
    )
  }

  const strategies = strategy.strategy?.services || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary">Competitive Strategy</h2>
        <p className="text-text-muted mt-1">
          Strategic analysis and recommendations per service
        </p>
      </div>

      {/* Overall Summary */}
      {strategy.strategy?.overall_summary && (
        <Card>
          <Card.Body className="p-6">
            <div className="flex items-start space-x-3">
              <Target className="w-6 h-6 text-primary-400 mt-1 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-2">
                  Overall Strategy
                </h3>
                <p className="text-text-muted leading-relaxed">
                  {strategy.strategy.overall_summary}
                </p>
              </div>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-primary-400">{strategies.length}</div>
            <div className="text-xs text-text-muted mt-1">Services</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {strategies.reduce((sum, s) => sum + (s.advantages?.length || 0), 0)}
            </div>
            <div className="text-xs text-text-muted mt-1">Advantages</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">
              {strategies.reduce((sum, s) => sum + (s.opportunities?.length || 0), 0)}
            </div>
            <div className="text-xs text-text-muted mt-1">Opportunities</div>
          </Card.Body>
        </Card>
        
        <Card>
          <Card.Body className="p-4 text-center">
            <div className="text-2xl font-bold text-red-400">
              {strategies.reduce((sum, s) => sum + (s.weaknesses?.length || 0), 0)}
            </div>
            <div className="text-xs text-text-muted mt-1">Weaknesses</div>
          </Card.Body>
        </Card>
      </div>

      {/* Services Strategies */}
      <div className="space-y-4">
        {strategies.map((service, idx) => (
          <Card key={idx}>
            <Card.Body className="p-6">
              {/* Service Header */}
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedService(expandedService === idx ? null : idx)}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-700 rounded-full flex items-center justify-center">
                    <Target className="w-5 h-5 text-primary-300" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary">
                      {service.service_name || `Service ${idx + 1}`}
                    </h3>
                    {service.description && (
                      <p className="text-sm text-text-muted mt-0.5">
                        {service.description}
                      </p>
                    )}
                  </div>
                </div>
                <button className="text-gray-400 hover:text-gray-200 transition-colors">
                  <svg
                    className={`w-5 h-5 transform transition-transform ${
                      expandedService === idx ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>

              {/* Expanded Content */}
              {expandedService === idx && (
                <div className="mt-6 space-y-6">
                  {/* Research Strategy */}
                  {service.research_strategy && (
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <Zap className="w-5 h-5 text-blue-400" />
                        <h4 className="text-md font-semibold text-text-primary">
                          Research Strategy
                        </h4>
                      </div>
                      <p className="text-text-muted pl-7 leading-relaxed">
                        {service.research_strategy}
                      </p>
                    </div>
                  )}

                  {/* Competitive Advantages */}
                  {service.advantages && service.advantages.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <Shield className="w-5 h-5 text-green-400" />
                        <h4 className="text-md font-semibold text-text-primary">
                          Competitive Advantages ({service.advantages.length})
                        </h4>
                      </div>
                      <ul className="space-y-2 pl-7">
                        {service.advantages.map((advantage, aidx) => (
                          <li key={aidx} className="flex items-start space-x-2">
                            <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                            <span className="text-text-muted">{advantage}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Opportunities */}
                  {service.opportunities && service.opportunities.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <TrendingUp className="w-5 h-5 text-yellow-400" />
                        <h4 className="text-md font-semibold text-text-primary">
                          Opportunities ({service.opportunities.length})
                        </h4>
                      </div>
                      <ul className="space-y-2 pl-7">
                        {service.opportunities.map((opportunity, oidx) => (
                          <li key={oidx} className="flex items-start space-x-2">
                            <Zap className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                            <span className="text-text-muted">{opportunity}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Weaknesses */}
                  {service.weaknesses && service.weaknesses.length > 0 && (
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                        <h4 className="text-md font-semibold text-text-primary">
                          Potential Weaknesses ({service.weaknesses.length})
                        </h4>
                      </div>
                      <ul className="space-y-2 pl-7">
                        {service.weaknesses.map((weakness, widx) => (
                          <li key={widx} className="flex items-start space-x-2">
                            <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                            <span className="text-text-muted">{weakness}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Keywords */}
                  {service.keywords && service.keywords.length > 0 && (
                    <div>
                      <h4 className="text-md font-semibold text-text-primary mb-2">
                        Target Keywords ({service.keywords.length})
                      </h4>
                      <div className="flex flex-wrap gap-2 pl-7">
                        {service.keywords.map((keyword, kidx) => (
                          <span
                            key={kidx}
                            className="px-3 py-1 bg-gray-800 text-gray-300 rounded-full text-sm"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card.Body>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default StrategyTab

