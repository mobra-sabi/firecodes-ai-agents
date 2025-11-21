import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MessageSquare, TrendingUp, BarChart3, Lightbulb, ArrowRight, Sparkles } from 'lucide-react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8090'

export default function ClientDashboard() {
  const { agentId } = useParams()
  const navigate = useNavigate()
  const [agent, setAgent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    seoHealth: 0,
    keywords: 0,
    competitors: 0,
    topPosition: null
  })

  useEffect(() => {
    if (agentId) {
      fetchAgentData()
    } else {
      // Dacă nu există agentId, găsește primul agent al utilizatorului
      fetchUserAgents()
    }
  }, [agentId])

  const fetchUserAgents = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/agents`)
      if (response.data && response.data.length > 0) {
        navigate(`/client/${response.data[0]._id}`)
      }
    } catch (error) {
      console.error('Error fetching agents:', error)
    }
  }

  const fetchAgentData = async () => {
    try {
      setLoading(true)
      const [agentRes, healthRes] = await Promise.all([
        axios.get(`${API_BASE}/api/agents/${agentId}`),
        axios.get(`${API_BASE}/api/agents/${agentId}/conscience/health`).catch(() => null)
      ])

      setAgent(agentRes.data)
      
      if (healthRes?.data) {
        setStats({
          seoHealth: Math.round(healthRes.data.seo_health || 0),
          keywords: agentRes.data.keywords?.length || 0,
          competitors: agentRes.data.competitors?.length || 0,
          topPosition: agentRes.data.top_position || null
        })
      } else {
        setStats({
          seoHealth: 0,
          keywords: agentRes.data.keywords?.length || 0,
          competitors: agentRes.data.competitors?.length || 0,
          topPosition: null
        })
      }
    } catch (error) {
      console.error('Error fetching agent data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-gray-600">Nu s-a găsit niciun agent.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{agent.domain}</h1>
              <p className="text-gray-600 mt-1">Dashboard-ul tău SEO</p>
            </div>
            <button
              onClick={() => navigate(`/client/${agentId}/chat`)}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <MessageSquare className="w-5 h-5" />
              Chat cu Agentul
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Sănătate SEO</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.seoHealth}/100</p>
              </div>
              <div className={`p-3 rounded-full ${stats.seoHealth >= 70 ? 'bg-green-100' : stats.seoHealth >= 40 ? 'bg-yellow-100' : 'bg-red-100'}`}>
                <TrendingUp className={`w-6 h-6 ${stats.seoHealth >= 70 ? 'text-green-600' : stats.seoHealth >= 40 ? 'text-yellow-600' : 'text-red-600'}`} />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Cuvinte Cheie</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.keywords}</p>
              </div>
              <div className="p-3 rounded-full bg-blue-100">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Competitori</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stats.competitors}</p>
              </div>
              <div className="p-3 rounded-full bg-purple-100">
                <Sparkles className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Poziție Top</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {stats.topPosition ? `#${stats.topPosition}` : 'N/A'}
                </p>
              </div>
              <div className="p-3 rounded-full bg-indigo-100">
                <TrendingUp className="w-6 h-6 text-indigo-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chat Card */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <MessageSquare className="w-6 h-6 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">Chat cu Agentul</h2>
            </div>
            <p className="text-gray-600 mb-4">
              Discută cu agentul tău AI despre SEO, recomandări și strategii pentru site-ul tău.
            </p>
            <button
              onClick={() => navigate(`/client/${agentId}/chat`)}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
            >
              Deschide Chat <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Recommendations Card */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Lightbulb className="w-6 h-6 text-yellow-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">Recomandări</h2>
            </div>
            <p className="text-gray-600 mb-4">
              Vezi recomandările personalizate ale agentului pentru îmbunătățirea SEO.
            </p>
            <button
              onClick={() => navigate(`/client/${agentId}/recommendations`)}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
            >
              Vezi Recomandări <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

