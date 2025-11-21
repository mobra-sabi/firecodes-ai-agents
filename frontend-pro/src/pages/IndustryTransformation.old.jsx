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
  const [maxParallel, setMaxParallel] = useState(33) // Default optim pentru 11x RTX 3080 Ti
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSessionId, setChatSessionId] = useState(null)
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [renderError, setRenderError] = useState(null)
  const chatEndRef = useRef(null)
  
  // Error boundary pentru rendering
  if (renderError) {
    if (process.env.NODE_ENV === 'development') {
      console.error('🚨 Render error caught:', renderError)
    }
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
          <details className="mt-4 text-left">
            <summary className="cursor-pointer text-text-muted hover:text-text-primary">Detalii tehnice</summary>
            <pre className="mt-2 p-4 bg-primary-800 rounded text-xs overflow-auto text-text-primary">
              {renderError?.stack || JSON.stringify(renderError, Object.getOwnPropertyNames(renderError), 2)}
            </pre>
          </details>
        </div>
      </div>
    )
  }

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
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: 2,
    onError: (error) => {
      console.error('Progress query error:', error)
    }
  })

  // Fetch companies (cu error handling)
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
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: 1,
  })

  // Fetch logs (cu error handling)
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
    refetchInterval: 3000, // Refresh every 3 seconds for live updates
    retry: 1,
  })

  // Fetch GPU recommendations (cu error handling)
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
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  })

  // Start transformation mutation
  const startTransformation = useMutation({
    mutationFn: async (data) => {
      try {
        const response = await api.post('/industry/construction/transform', data)
        return response.data
      } catch (error) {
        // Log error details for debugging
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

  // Debug: Log errors și prinde erori de rendering
  useEffect(() => {
    if (progressError) {
      console.error('Progress error:', progressError)
    }
  }, [progressError])
  
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
  
  // Debug: Log când componenta se montează - ELIMINAT pentru stabilitate
  // useEffect(() => {
  //   if (process.env.NODE_ENV === 'development') {
  //     console.log('✅ IndustryTransformation component mounted')
  //   }
  //   return () => {
  //     if (process.env.NODE_ENV === 'development') {
  //       console.log('❌ IndustryTransformation component unmounted')
  //     }
  //   }
  // }, [])

  const handleStart = () => {
    startTransformation.mutate({
      discovery_method: discoveryMethod,
      max_companies: maxCompanies,
      max_parallel_agents: maxParallel,
    })
  }

  // Chat with DeepSeek
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
      // Add messages to chat
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

  const handleChatSend = () => {
    if (!chatInput.trim() || isChatLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setIsChatLoading(true)

    // Add user message
    setChatMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString(),
      },
    ])

    // Send to DeepSeek
    sendChatMessage.mutate(userMessage)
  }

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Safe data extraction cu fallback
  const stats = (progress && progress.statistics) ? progress.statistics : {
    total_companies_discovered: 0,
    companies_pending: 0,
    companies_created: 0,
    construction_agents_created: 0
  }
  const batches = (progress && progress.recent_batches) ? progress.recent_batches : []
  const companies = (companiesData && companiesData.companies) ? companiesData.companies : []

  // Debug logging (doar în development) - ELIMINAT pentru a evita probleme
  // useEffect(() => {
  //   if (process.env.NODE_ENV === 'development') {
  //     console.log('📊 Data state:', {
  //       progress: !!progress,
  //       progressLoading,
  //       progressError: !!progressError,
  //       companiesData: !!companiesData,
  //       logsData: !!logsData,
  //       stats,
  //       batchesCount: batches.length,
  //       companiesCount: companies.length
  //     })
  //   }
  // }, [progress, progressLoading, progressError, companiesData, logsData, stats, batches, companies])

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
  
  return (
    <div className="space-y-8">
      {/* DeepSeek Chat Panel */}
      <Card>
        <Card.Body>
          <h2 className="text-xl font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Bot className="w-5 h-5 text-accent-blue" />
            Chat cu DeepSeek - Strategie & Execuție
          </h2>
          <p className="text-sm text-text-muted mb-4">
            Discută cu DeepSeek despre strategia de descoperire și transformare. DeepSeek poate executa acțiuni direct prin aplicație.
          </p>

          {/* Chat Messages */}
          <div className="bg-primary-900 rounded-lg p-4 max-h-96 overflow-y-auto space-y-3 mb-4">
            {chatMessages.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Începe conversația cu DeepSeek...</p>
                <p className="text-xs mt-2">Exemplu: "Descoperă 100 de companii din construcții"</p>
              </div>
            ) : (
              chatMessages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-accent-blue" />
                    </div>
                  )}
                  <div
                    className={`max-w-3xl rounded-lg px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-accent-blue text-white'
                        : 'bg-primary-800 text-text-primary'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.action_executed && (
                      <div className="mt-2 pt-2 border-t border-primary-700">
                        <p className="text-xs text-accent-green mb-1">
                          ✅ Acțiune executată: {msg.action_executed.name}
                        </p>
                        {msg.action_executed.result?.success && (
                          <pre className="text-xs bg-primary-900 p-2 rounded overflow-x-auto">
                            {JSON.stringify(msg.action_executed.result.result, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                      <User className="w-4 h-4 text-accent-blue" />
                    </div>
                  )}
                </div>
              ))
            )}
            {isChatLoading && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-accent-blue" />
                </div>
                <div className="bg-primary-800 rounded-lg px-4 py-3">
                  <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleChatSend()
                }
              }}
              placeholder="Discută cu DeepSeek despre strategia de transformare..."
              className="flex-1 input-custom"
              disabled={isChatLoading}
            />
            <Button
              icon={isChatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              onClick={handleChatSend}
              disabled={!chatInput.trim() || isChatLoading}
            >
              Send
            </Button>
          </div>
        </Card.Body>
      </Card>

      {/* Header */}
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

      {/* Explicație ce se întâmplă cu site-urile */}
      <Card className="mb-6">
        <Card.Body>
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            🔄 Ce se întâmplă cu site-urile descoperite?
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-primary-800 rounded-lg border-l-4 border-blue-500">
              <div className="font-semibold text-text-primary mb-1">1️⃣ Descoperire</div>
              <div className="text-text-muted">
                DeepSeek găsește companii din construcții → salvate în DB cu status "pending"
              </div>
            </div>
            <div className="p-3 bg-primary-800 rounded-lg border-l-4 border-green-500">
              <div className="font-semibold text-text-primary mb-1">2️⃣ Procesare</div>
              <div className="text-text-muted">
                Pentru fiecare companie se creează un agent AI complet (scraping, chunking, embeddings, keywords, SERP)
              </div>
            </div>
            <div className="p-3 bg-primary-800 rounded-lg border-l-4 border-purple-500">
              <div className="font-semibold text-text-primary mb-1">3️⃣ Rezultat</div>
              <div className="text-text-muted">
                Agent master creat în MongoDB + Qdrant, cu keywords, competitori, și hărți SEO
              </div>
            </div>
            <div className="p-3 bg-primary-800 rounded-lg border-l-4 border-orange-500">
              <div className="font-semibold text-text-primary mb-1">4️⃣ Status</div>
              <div className="text-text-muted">
                "pending" → "agent_created" când procesarea este completă
              </div>
            </div>
          </div>
        </Card.Body>
      </Card>

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
                <p className="text-sm text-sm text-text-muted">Agenți Creați</p>
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
                      <strong className="text-text-primary">Hardware:</strong> {gpuRecommendations.recommendations.hardware.gpu_count}x {gpuRecommendations.recommendations.hardware.gpu_model} ({gpuRecommendations.recommendations.hardware.total_vram_gb} GB VRAM)
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
                    {gpuRecommendations.pending_companies > 0 && gpuRecommendations.time_estimates?.optimal && (
                      <p className="text-xs text-accent-blue mt-1">
                        ⏱️ Estimare: ~{gpuRecommendations.time_estimates.optimal.total_time_hours}h pentru {gpuRecommendations.pending_companies} companii
                      </p>
                    )}
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

            {startTransformation.isSuccess && (
              <div className="p-3 bg-accent-green bg-opacity-10 border border-accent-green rounded-lg">
                <p className="text-sm text-accent-green">
                  ✅ Transformarea a fost pornită în background!
                </p>
              </div>
            )}

            {startTransformation.isError && (
              <div className="p-3 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg">
                <p className="text-sm text-red-400">
                  ❌ Eroare: {startTransformation.error?.response?.data?.detail || startTransformation.error?.message || startTransformation.error?.toString() || 'Unknown error'}
                </p>
                {startTransformation.error && (
                  <details className="mt-2 text-xs text-red-300">
                    <summary className="cursor-pointer hover:text-red-200">Detalii eroare (click pentru a deschide)</summary>
                    <pre className="mt-2 p-2 bg-red-900 bg-opacity-50 rounded overflow-auto max-h-40 text-xs">
                      {JSON.stringify({
                        message: startTransformation.error?.message,
                        response: startTransformation.error?.response?.data,
                        status: startTransformation.error?.response?.status,
                        fullError: startTransformation.error?.toString()
                      }, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        </Card.Body>
      </Card>

      {/* Recent Batches */}
      {batches.length > 0 && (
        <Card>
          <Card.Body>
            <h2 className="text-xl font-semibold text-text-primary mb-4">
              Batch-uri Recente
            </h2>
            <div className="space-y-3">
              {batches.map((batch) => (
                <div
                  key={batch.batch_id}
                  className="p-4 bg-primary-800 rounded-lg border border-primary-700"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text-primary">
                        {batch.batch_id}
                      </span>
                      {batch.status === 'running' && (
                        <Loader2 className="w-4 h-4 animate-spin text-accent-blue" />
                      )}
                      {batch.status === 'completed' && (
                        <CheckCircle className="w-4 h-4 text-accent-green" />
                      )}
                    </div>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        batch.status === 'running'
                          ? 'bg-accent-blue bg-opacity-10 text-accent-blue'
                          : 'bg-accent-green bg-opacity-10 text-accent-green'
                      }`}
                    >
                      {batch.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-text-muted">Total:</span>
                      <span className="text-text-primary ml-2 font-medium">
                        {batch.total_companies || 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">Creați:</span>
                      <span className="text-accent-green ml-2 font-medium">
                        {batch.created || 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">Există:</span>
                      <span className="text-accent-yellow ml-2 font-medium">
                        {batch.already_exists || 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted">Eșuat:</span>
                      <span className="text-red-400 ml-2 font-medium">
                        {batch.failed || 0}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Live Logs - Always show */}
      <Card>
        <Card.Body>
          <h2 className="text-xl font-semibold text-text-primary mb-4">
            📋 Logs Live - Ce se descoperă acum
          </h2>
          {logsData?.logs && logsData.logs.length > 0 ? (
            <div className="bg-primary-900 rounded-lg p-4 max-h-96 overflow-y-auto space-y-2">
              {logsData.logs.slice().reverse().map((log, index) => (
                <div
                  key={index}
                  className="text-sm p-2 rounded border-l-2 border-primary-700 bg-primary-800"
                  style={{
                    borderLeftColor:
                      log.stage === 'deepseek_discovery'
                        ? '#3b82f6'
                        : log.stage === 'creation_start'
                        ? '#10b981'
                        : log.stage === 'complete'
                        ? '#10b981'
                        : '#6b7280'
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-text-primary">{log.message}</p>
                      {log.data && log.data.company && (
                        <p className="text-text-muted text-xs mt-1">
                          📋 {log.data.company} - {log.data.domain} ({log.data.activity})
                        </p>
                      )}
                      {log.data && log.data.saved_count && (
                        <p className="text-accent-blue text-xs mt-1">
                          Progres: {log.data.saved_count}/{log.data.total} companii
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-text-muted ml-4">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-primary-900 rounded-lg p-8 text-center">
              <p className="text-text-muted">
                Nu există logs încă. Pornește transformarea pentru a vedea progresul live.
              </p>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Companies List */}
      {companies.length > 0 && (
        <Card>
          <Card.Body>
            <h2 className="text-xl font-semibold text-text-primary mb-4">
              Companii Descoperite ({companies.length})
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-primary-700">
                    <th className="text-left py-2 px-4 text-sm font-medium text-text-muted">
                      Nume
                    </th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-text-muted">
                      Domeniu
                    </th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-text-muted">
                      Activitate
                    </th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-text-muted">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {companies.slice(0, 50).map((company) => (
                    <tr
                      key={company._id}
                      className="border-b border-primary-800 hover:bg-primary-800"
                    >
                      <td className="py-2 px-4 text-sm text-text-primary">
                        {company.nume_companie || 'N/A'}
                      </td>
                      <td className="py-2 px-4 text-sm text-text-primary">
                        {company.domeniu || 'N/A'}
                      </td>
                      <td className="py-2 px-4 text-sm text-text-muted">
                        {company.activitate || 'N/A'}
                      </td>
                      <td className="py-2 px-4">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            company.status === 'agent_created'
                              ? 'bg-accent-green bg-opacity-10 text-accent-green'
                              : company.status === 'pending'
                              ? 'bg-accent-yellow bg-opacity-10 text-accent-yellow'
                              : 'bg-primary-700 text-text-muted'
                          }`}
                        >
                          {company.status || 'pending'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card.Body>
        </Card>
      )}
      
      {/* Error Display */}
      {(progressError || logsError || companiesError || gpuError) && (
        <Card className="mt-6 border-red-500">
          <Card.Body>
            <div className="p-4 bg-red-500 bg-opacity-10 rounded-lg">
              <h3 className="text-red-400 font-semibold mb-2">⚠️ Eroare la încărcarea datelor</h3>
              <p className="text-red-300 text-sm">
                {progressError?.message || logsError?.message || companiesError?.message || gpuError?.message || 'Eroare necunoscută'}
              </p>
              <details className="mt-2 text-xs text-red-200">
                <summary className="cursor-pointer">Detalii tehnice</summary>
                <pre className="mt-2 p-2 bg-red-900 bg-opacity-50 rounded overflow-auto">
                  {JSON.stringify({ 
                    progressError: progressError?.message, 
                    logsError: logsError?.message,
                    companiesError: companiesError?.message,
                    gpuError: gpuError?.message
                  }, null, 2)}
                </pre>
              </details>
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

export default IndustryTransformation

