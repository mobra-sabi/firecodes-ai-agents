import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Lightbulb, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8090'

export default function ClientRecommendations() {
  const { agentId } = useParams()
  const navigate = useNavigate()
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [agent, setAgent] = useState(null)

  useEffect(() => {
    fetchData()
  }, [agentId])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [agentRes, reflectionRes] = await Promise.all([
        axios.get(`${API_BASE}/api/agents/${agentId}`),
        axios.get(`${API_BASE}/api/agents/${agentId}/conscience/reflect`).catch(() => null)
      ])

      setAgent(agentRes.data)

      // Extrage recomandări din reflection sau generează din datele agentului
      if (reflectionRes?.data?.recommendations) {
        setRecommendations(reflectionRes.data.recommendations)
      } else {
        // Generează recomandări simple din datele disponibile
        const recs = []
        if (agentRes.data.keywords && agentRes.data.keywords.length < 10) {
          recs.push({
            type: 'info',
            title: 'Adaugă mai multe cuvinte cheie',
            description: 'Agentul tău are doar câteva cuvinte cheie. Adaugă mai multe pentru o analiză mai completă.',
            priority: 'medium'
          })
        }
        if (agentRes.data.competitors && agentRes.data.competitors.length < 5) {
          recs.push({
            type: 'warning',
            title: 'Identifică mai mulți competitori',
            description: 'Analiza competitorilor este limitată. Identifică mai mulți competitori pentru o analiză mai precisă.',
            priority: 'high'
          })
        }
        setRecommendations(recs)
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error)
    } finally {
      setLoading(false)
    }
  }

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />
      case 'info':
      default:
        return <Lightbulb className="w-5 h-5 text-blue-600" />
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'border-red-200 bg-red-50'
      case 'medium':
        return 'border-yellow-200 bg-yellow-50'
      case 'low':
        return 'border-blue-200 bg-blue-50'
      default:
        return 'border-gray-200 bg-white'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate(`/client/${agentId}`)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Lightbulb className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Recomandări</h1>
              <p className="text-sm text-gray-600">{agent?.domain}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {recommendations.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-8 text-center border border-gray-200">
            <Lightbulb className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Nu există recomandări disponibile momentan.</p>
            <p className="text-sm text-gray-500 mt-2">
              Agentul tău analizează în continuare site-ul și va genera recomandări în curând.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {recommendations.map((rec, idx) => (
              <div
                key={idx}
                className={`bg-white rounded-xl shadow-sm p-6 border-2 ${getPriorityColor(rec.priority)}`}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 mt-1">
                    {getIcon(rec.type)}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {rec.title}
                    </h3>
                    <p className="text-gray-700 mb-3">
                      {rec.description}
                    </p>
                    {rec.actions && rec.actions.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-sm font-medium text-gray-700">Acțiuni recomandate:</p>
                        <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                          {rec.actions.map((action, actionIdx) => (
                            <li key={actionIdx}>{action}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

