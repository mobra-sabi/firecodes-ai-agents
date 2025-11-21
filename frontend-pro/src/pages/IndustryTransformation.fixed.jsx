import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Play, RefreshCw, CheckCircle, XCircle, Clock, Loader2, MessageSquare, Send, Bot, User } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const IndustryTransformation = () => {
  const queryClient = useQueryClient()
  const [discoveryMethod, setDiscoveryMethod] = useState('deepseek')
  const [maxCompanies, setMaxCompanies] = useState(500)
  const [maxParallel, setMaxParallel] = useState(33)
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSessionId, setChatSessionId] = useState(null)
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [renderError, setRenderError] = useState(null)
  const chatEndRef = useRef(null)

  // TOATE HOOKS-URILE TREBUIE SĂ FIE AICI, ÎNAINTE DE ORICE RETURN CONDITIONAL

  // Fetch progress
  const { data: progress, isLoading: progressLoading, error: progressError } = useQuery({
    queryKey: ['industry-progress'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/progress')
        return response.data
      } catch (error) {
        console.error('Error fetching progress:', error)
        throw error
      }
    },
    refetchInterval: 5000,
    retry: 2,
    onError: (error) => {
      console.error('Progress query error:', error)
    }
  })

  // Fetch companies
  const { data: companiesData, error: companiesError } = useQuery({
    queryKey: ['construction-companies'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/companies?limit=100')
        return response.data
      } catch (error) {
        console.error('Error fetching companies:', error)
        return { companies: [], ok: false, error: error.message }
      }
    },
    refetchInterval: 10000,
    retry: 1,
  })

  // Fetch logs
  const { data: logsData, error: logsError } = useQuery({
    queryKey: ['industry-logs'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/logs?limit=200')
        return response.data
      } catch (error) {
        console.error('Error fetching logs:', error)
        return { logs: [], ok: false, error: error.message }
      }
    },
    refetchInterval: 3000,
    retry: 1,
  })

  // Fetch GPU recommendations
  const { data: gpuRecommendations, error: gpuError } = useQuery({
    queryKey: ['gpu-recommendations'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/gpu-recommendations')
        return response.data
      } catch (error) {
        console.error('Error fetching GPU recommendations:', error)
        return { ok: false, error: error.message }
      }
    },
    refetchInterval: 30000,
    retry: 1,
  })

  // Start transformation mutation
  const startTransformation = useMutation({
    mutationFn: async (data) => {
      try {
        const response = await api.post('/industry/construction/transform', data)
        return response.data
      } catch (error) {
        console.error('Transformation error:', error)
        const errorMessage = error?.response?.data?.detail || error?.message || 'Unknown error'
        throw new Error(errorMessage)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['industry-progress'])
      queryClient.invalidateQueries(['construction-companies'])
      queryClient.invalidateQueries(['industry-logs'])
    },
    onError: (error) => {
      console.error('Transformation failed:', error)
    }
  })

  // Chat mutation
  const sendChatMessage = useMutation({
    mutationFn: async (message) => {
      const response = await api.post('/industry/construction/chat', {
        message,
        session_id: chatSessionId,
      })
      return response.data
    },
    onSuccess: (data) => {
      if (!chatSessionId && data.session_id) {
        setChatSessionId(data.session_id)
      }
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          action_executed: data.action_executed,
          timestamp: data.timestamp,
        },
      ])
      setIsChatLoading(false)
      queryClient.invalidateQueries(['industry-progress'])
      queryClient.invalidateQueries(['construction-companies'])
      queryClient.invalidateQueries(['industry-logs'])
    },
    onError: () => {
      setIsChatLoading(false)
    },
  })

  // Error boundary pentru rendering errors
  useEffect(() => {
    const errorHandler = (event) => {
      console.error('Uncaught error:', event.error || event)
      setRenderError(event.error || new Error(String(event.reason || event)))
    }
    
    const rejectionHandler = (event) => {
      console.error('Unhandled rejection:', event.reason)
      setRenderError(event.reason || new Error('Unhandled promise rejection'))
    }
    
    window.addEventListener('error', errorHandler)
    window.addEventListener('unhandledrejection', rejectionHandler)
    
    return () => {
      window.removeEventListener('error', errorHandler)
      window.removeEventListener('unhandledrejection', rejectionHandler)
    }
  }, [])

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Handlers
  const handleStart = () => {
    startTransformation.mutate({
      discovery_method: discoveryMethod,
      max_companies: maxCompanies,
      max_parallel_agents: maxParallel,
    })
  }

  const handleChatSend = () => {
    if (!chatInput.trim() || isChatLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setIsChatLoading(true)

    setChatMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString(),
      },
    ])

    sendChatMessage.mutate(userMessage)
  }

  // Data extraction
  const stats = (progress && progress.statistics) ? progress.statistics : {
    total_companies_discovered: 0,
    companies_pending: 0,
    companies_created: 0,
    construction_agents_created: 0
  }
  const batches = (progress && progress.recent_batches) ? progress.recent_batches : []
  const companies = (companiesData && companiesData.companies) ? companiesData.companies : []

  // ACUM PUTEM FACE RETURN-URI CONDITIONALE
  
  // Error boundary pentru rendering
  if (renderError) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8 bg-primary-900">
        <div className="text-center max-w-2xl">
          <h2 className="text-2xl font-bold text-red-400 mb-4">⚠️ Eroare la încărcarea paginii</h2>
          <p className="text-text-primary mb-2">{renderError?.message || renderError?.toString() || 'Eroare necunoscută'}</p>
          <button
            onClick={() => {
              setRenderError(null)
              window.location.reload()
            }}
            className="px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-accent-blue-dark mt-4"
          >
            Reîncarcă pagina
          </button>
        </div>
      </div>
    )
  }

  // Early return pentru loading state
  if (progressLoading && !progress) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-muted">Se încarcă...</p>
        </div>
      </div>
    )
  }

  // Safety check: dacă nu există date, arată loading
  if (!progress && !progressLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-muted">Se încarcă datele...</p>
        </div>
      </div>
    )
  }

  // Main render
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary flex items-center gap-3">
            <Building2 className="w-8 h-8 text-accent-blue" />
            Industry Transformation - Construcții România
          </h1>
          <p className="text-text-muted mt-1">
            Transformă întreaga industrie de construcții din România în agenți AI compleți
          </p>
        </div>
        <Button
          icon={<RefreshCw className="w-4 h-4" />}
          onClick={() => {
            queryClient.invalidateQueries(['industry-progress'])
            queryClient.invalidateQueries(['construction-companies'])
          }}
        >
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <Card>
          <Card.Body>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">Companii Descoperite</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {stats.total_companies_discovered || 0}
                </p>
              </div>
              <Building2 className="w-8 h-8 text-accent-blue opacity-50" />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">În Așteptare</p>
                <p className="text-2xl font-bold text-accent-yellow mt-1">
                  {stats.companies_pending || 0}
                </p>
              </div>
              <Clock className="w-8 h-8 text-accent-yellow opacity-50" />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">Agenți Creați</p>
                <p className="text-2xl font-bold text-accent-green mt-1">
                  {stats.companies_created || 0}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-accent-green opacity-50" />
            </div>
          </Card.Body>
        </Card>

        <Card>
          <Card.Body>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">Total Agenți</p>
                <p className="text-2xl font-bold text-accent-blue mt-1">
                  {stats.construction_agents_created || 0}
                </p>
              </div>
              <Building2 className="w-8 h-8 text-accent-blue opacity-50" />
            </div>
          </Card.Body>
        </Card>
      </div>

      {/* Start Transformation */}
      <Card>
        <Card.Body>
          <h2 className="text-xl font-semibold text-text-primary mb-4">
            Pornește Transformarea Industriei
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Metodă de Descoperire
              </label>
              <select
                value={discoveryMethod}
                onChange={(e) => setDiscoveryMethod(e.target.value)}
                className="input-custom w-full"
              >
                <option value="deepseek">DeepSeek Discovery (Recomandat)</option>
                <option value="web_search">Web Search</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Max Companii
                </label>
                <input
                  type="number"
                  value={maxCompanies}
                  onChange={(e) => setMaxCompanies(parseInt(e.target.value))}
                  className="input-custom w-full"
                  min="10"
                  max="1000"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Paralel (Agenți simultan)
                </label>
                <input
                  type="number"
                  value={maxParallel}
                  onChange={(e) => setMaxParallel(parseInt(e.target.value))}
                  className="input-custom w-full"
                  min="1"
                  max="50"
                />
                {gpuRecommendations?.recommendations && (
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-text-muted">
                      <strong className="text-text-primary">Hardware:</strong> {gpuRecommendations.recommendations.hardware.gpu_count}x {gpuRecommendations.recommendations.hardware.gpu_model}
                    </p>
                    <div className="flex gap-2 text-xs">
                      <button
                        type="button"
                        onClick={() => setMaxParallel(gpuRecommendations.recommendations.conservative.parallel_agents)}
                        className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-text-muted hover:text-text-primary transition"
                      >
                        Conservator: {gpuRecommendations.recommendations.conservative.parallel_agents}
                      </button>
                      <button
                        type="button"
                        onClick={() => setMaxParallel(gpuRecommendations.recommendations.optimal.parallel_agents)}
                        className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white transition"
                      >
                        Optim: {gpuRecommendations.recommendations.optimal.parallel_agents}
                      </button>
                      <button
                        type="button"
                        onClick={() => setMaxParallel(gpuRecommendations.recommendations.aggressive.parallel_agents)}
                        className="px-2 py-1 bg-orange-600 hover:bg-orange-700 rounded text-white transition"
                      >
                        Agresiv: {gpuRecommendations.recommendations.aggressive.parallel_agents}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <Button
              icon={startTransformation.isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              onClick={handleStart}
              disabled={startTransformation.isLoading}
              className="w-full"
            >
              {startTransformation.isLoading ? 'Pornire...' : 'Pornește Transformarea'}
            </Button>

            {startTransformation.isError && (
              <div className="p-3 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg">
                <p className="text-sm text-red-400">
                  ❌ Eroare: {startTransformation.error?.message || 'Unknown error'}
                </p>
              </div>
            )}
          </div>
        </Card.Body>
      </Card>

      {/* Error Display */}
      {(progressError || logsError || companiesError || gpuError) && (
        <Card className="mt-6 border-red-500">
          <Card.Body>
            <div className="p-4 bg-red-500 bg-opacity-10 rounded-lg">
              <h3 className="text-red-400 font-semibold mb-2">⚠️ Eroare la încărcarea datelor</h3>
              <p className="text-red-300 text-sm">
                {progressError?.message || logsError?.message || companiesError?.message || gpuError?.message || 'Eroare necunoscută'}
              </p>
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

export default IndustryTransformation

