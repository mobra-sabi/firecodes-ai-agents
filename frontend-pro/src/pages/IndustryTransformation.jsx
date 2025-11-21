import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Play, RefreshCw, CheckCircle, Clock, Loader2, MessageSquare, Send, Bot, User } from 'lucide-react'
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
  const [error, setError] = useState(null)
  const chatEndRef = useRef(null)

  // Fetch progress with error handling
  const { data: progress, isLoading: progressLoading } = useQuery({
    queryKey: ['industry-progress'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/progress')
        return response.data
      } catch (error) {
        console.error('Error fetching progress:', error)
        return { statistics: { total_companies_discovered: 0, companies_pending: 0, companies_created: 0, construction_agents_created: 0 } }
      }
    },
    refetchInterval: 5000,
    retry: 1,
    onError: (err) => {
      console.error('Progress query error:', err)
      setError(err.message)
    }
  })

  // Fetch companies with error handling
  const { data: companiesData } = useQuery({
    queryKey: ['construction-companies'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/companies?limit=100')
        return response.data
      } catch (error) {
        console.error('Error fetching companies:', error)
        return { companies: [], ok: false }
      }
    },
    refetchInterval: 10000,
    retry: 1,
  })

  // Fetch logs with error handling
  const { data: logsData } = useQuery({
    queryKey: ['industry-logs'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/logs?limit=200')
        return response.data
      } catch (error) {
        console.error('Error fetching logs:', error)
        return { logs: [], ok: false }
      }
    },
    refetchInterval: 2000, // Refresh la fiecare 2 secunde pentru logs live
    retry: 1,
  })

  // Fetch GPU recommendations with error handling
  const { data: gpuRecommendations } = useQuery({
    queryKey: ['gpu-recommendations'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/gpu-recommendations')
        return response.data
      } catch (error) {
        console.error('Error fetching GPU recommendations:', error)
        return { ok: false }
      }
    },
    refetchInterval: 30000,
    retry: 1,
  })

  // Fetch DeepSeek strategy
  const { data: strategyData, isLoading: strategyLoading, refetch: refetchStrategy } = useQuery({
    queryKey: ['deepseek-strategy'],
    queryFn: async () => {
      try {
        // Timeout mai mare pentru generarea strategiei (60 secunde)
        const response = await api.get('/industry/construction/strategy', {
          timeout: 60000 // 60 secunde
        })
        return response.data
      } catch (error) {
        console.error('Error fetching strategy:', error)
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          return { ok: false, strategy: 'Timeout: Generarea strategiei durează prea mult. Încearcă din nou.' }
        }
        return { ok: false, strategy: 'Eroare la generarea strategiei: ' + (error.message || 'Unknown error') }
      }
    },
    refetchInterval: false, // Nu auto-refresh (doar manual)
    retry: 1,
    staleTime: 300000, // Strategia e valabilă 5 minute
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
      setError(error.message)
    }
  })

  // Chat mutation
  const sendChatMessage = useMutation({
    mutationFn: async (message) => {
      try {
        const response = await api.post('/industry/construction/chat', {
          message,
          session_id: chatSessionId,
        })
        return response.data
      } catch (error) {
        console.error('Chat error:', error)
        throw error
      }
    },
    onSuccess: (data) => {
      if (!chatSessionId && data.session_id) {
        setChatSessionId(data.session_id)
      }
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || 'Răspuns primit',
          action_executed: data.action_executed,
          timestamp: data.timestamp,
        },
      ])
      setIsChatLoading(false)
      queryClient.invalidateQueries(['industry-progress'])
      queryClient.invalidateQueries(['construction-companies'])
      queryClient.invalidateQueries(['industry-logs'])
    },
    onError: (error) => {
      setIsChatLoading(false)
      setError(error.message || 'Eroare la trimiterea mesajului')
    },
  })

  // Auto-scroll chat
  useEffect(() => {
    try {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    } catch (e) {
      console.error('Scroll error:', e)
    }
  }, [chatMessages])

  // Global error handler
  useEffect(() => {
    const handleError = (event) => {
      console.error('Global error:', event.error)
      setError(event.error?.message || 'Eroare necunoscută')
    }
    const handleRejection = (event) => {
      console.error('Unhandled rejection:', event.reason)
      setError(event.reason?.message || 'Eroare de promisiune')
    }
    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleRejection)
    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleRejection)
    }
  }, [])

  // Handlers
  const handleStart = () => {
    try {
      setError(null)
      startTransformation.mutate({
        discovery_method: discoveryMethod,
        max_companies: maxCompanies,
        max_parallel_agents: maxParallel,
      })
    } catch (e) {
      console.error('Start error:', e)
      setError(e.message)
    }
  }

  const handleChatSend = () => {
    if (!chatInput.trim() || isChatLoading) return
    try {
      const userMessage = chatInput.trim()
      setChatInput('')
      setIsChatLoading(true)
      setError(null)

      setChatMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content: userMessage,
          timestamp: new Date().toISOString(),
        },
      ])

      sendChatMessage.mutate(userMessage)
    } catch (e) {
      console.error('Chat send error:', e)
      setIsChatLoading(false)
      setError(e.message)
    }
  }

  // Data extraction with safe defaults
  const stats = (progress && progress.statistics) ? progress.statistics : {
    total_companies_discovered: 0,
    companies_pending: 0,
    companies_created: 0,
    construction_agents_created: 0
  }
  // Sort logs by timestamp (newest first) and ensure we have logs
  const logs = (logsData && logsData.logs) ? [...logsData.logs].sort((a, b) => {
    const timeA = new Date(a.timestamp || 0).getTime()
    const timeB = new Date(b.timestamp || 0).getTime()
    return timeB - timeA // Newest first
  }) : []

  // Error display
  if (error && !progressLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen p-8 bg-primary-900">
        <div className="text-center max-w-2xl">
          <h2 className="text-2xl font-bold text-red-400 mb-4">⚠️ Eroare</h2>
          <p className="text-text-primary mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null)
              window.location.reload()
            }}
            className="px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-accent-blue-dark"
          >
            Reîncarcă pagina
          </button>
        </div>
      </div>
    )
  }

  // Loading state
  if (progressLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-primary">Se încarcă datele...</p>
        </div>
      </div>
    )
  }

  // Main render with try-catch wrapper
  try {
    return (
      <div className="p-6 space-y-6">
        {error && (
          <div className="p-4 bg-red-900/50 border border-red-700 rounded-lg">
            <p className="text-sm text-red-400">⚠️ {error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-xs text-red-300 hover:text-red-200"
            >
              Închide
            </button>
          </div>
        )}

        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Building2 className="w-6 h-6" />
            Transformare Industrie Construcții
          </h1>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <Card.Body>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-muted">Companii Descoperite</p>
                  <p className="text-2xl font-bold text-text-primary">{stats.total_companies_discovered || 0}</p>
                </div>
                <Building2 className="w-8 h-8 text-accent-blue" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-muted">În Așteptare</p>
                  <p className="text-2xl font-bold text-yellow-400">{stats.companies_pending || 0}</p>
                </div>
                <Clock className="w-8 h-8 text-yellow-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-muted">Agenți Creați</p>
                  <p className="text-2xl font-bold text-green-400">{stats.companies_created || 0}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-muted">Agenți Construcții</p>
                  <p className="text-2xl font-bold text-purple-400">{stats.construction_agents_created || 0}</p>
                </div>
                <Building2 className="w-8 h-8 text-purple-400" />
              </div>
            </Card.Body>
          </Card>
        </div>

        {/* Configuration */}
        <Card>
          <Card.Body>
            <h3 className="text-lg font-semibold text-text-primary mb-4">Configurare Transformare</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Metodă Descoperire
                </label>
                <select
                  value={discoveryMethod}
                  onChange={(e) => setDiscoveryMethod(e.target.value)}
                  className="w-full px-3 py-2 bg-primary-800 border border-primary-700 rounded-lg text-text-primary"
                >
                  <option value="deepseek">DeepSeek</option>
                  <option value="web_search">Web Search</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Max Companii
                </label>
                <input
                  type="number"
                  value={maxCompanies}
                  onChange={(e) => setMaxCompanies(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-primary-800 border border-primary-700 rounded-lg text-text-primary"
                  min="1"
                  max="1000"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Paralel Max
                </label>
                <input
                  type="number"
                  value={maxParallel}
                  onChange={(e) => setMaxParallel(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-primary-800 border border-primary-700 rounded-lg text-text-primary"
                  min="1"
                  max="100"
                />
              </div>
            </div>

            {gpuRecommendations?.recommendations?.conservative?.parallel_agents && (
              <div className="mt-4 p-3 bg-primary-800 rounded-lg">
                <p className="text-xs text-text-muted mb-2">
                  <strong className="text-text-primary">Hardware:</strong> {gpuRecommendations.recommendations.hardware?.gpu_count || 0}x {gpuRecommendations.recommendations.hardware?.gpu_model || 'N/A'} ({gpuRecommendations.recommendations.hardware?.total_vram_gb || 0} GB VRAM)
                </p>
                <div className="flex gap-2">
                  {gpuRecommendations.recommendations.conservative?.parallel_agents && (
                    <button
                      type="button"
                      onClick={() => setMaxParallel(gpuRecommendations.recommendations.conservative.parallel_agents)}
                      className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-text-muted hover:text-text-primary transition text-xs"
                    >
                      Conservator: {gpuRecommendations.recommendations.conservative.parallel_agents}
                    </button>
                  )}
                  {gpuRecommendations.recommendations.optimal?.parallel_agents && (
                    <button
                      type="button"
                      onClick={() => setMaxParallel(gpuRecommendations.recommendations.optimal.parallel_agents)}
                      className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white transition text-xs"
                    >
                      Optim: {gpuRecommendations.recommendations.optimal.parallel_agents}
                    </button>
                  )}
                  {gpuRecommendations.recommendations.aggressive?.parallel_agents && (
                    <button
                      type="button"
                      onClick={() => setMaxParallel(gpuRecommendations.recommendations.aggressive.parallel_agents)}
                      className="px-2 py-1 bg-orange-600 hover:bg-orange-700 rounded text-white transition text-xs"
                    >
                      Agresiv: {gpuRecommendations.recommendations.aggressive.parallel_agents}
                    </button>
                  )}
                </div>
              </div>
            )}

            <div className="mt-4">
              <Button
                onClick={handleStart}
                disabled={startTransformation.isPending}
                className="w-full md:w-auto"
              >
                {startTransformation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Se procesează...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start Transformation
                  </>
                )}
              </Button>
            </div>

            {startTransformation.isError && (
              <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg">
                <p className="text-sm text-red-400">
                  ❌ Eroare: {startTransformation.error?.message || 'Unknown error'}
                </p>
              </div>
            )}

            {startTransformation.isSuccess && (
              <div className="mt-4 p-3 bg-green-900/50 border border-green-700 rounded-lg">
                <p className="text-sm text-green-400">
                  ✅ Transformare inițiată cu succes!
                </p>
              </div>
            )}
          </Card.Body>
        </Card>

        {/* DeepSeek Strategy */}
        <Card>
          <Card.Body>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <Bot className="w-5 h-5" />
                Strategia DeepSeek
              </h3>
              <Button
                onClick={() => refetchStrategy()}
                disabled={strategyLoading}
                size="sm"
                variant="secondary"
              >
                {strategyLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
              </Button>
            </div>
            <div className="bg-primary-900 rounded-lg p-4 max-h-96 overflow-y-auto">
              {strategyLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-accent-blue" />
                  <p className="ml-3 text-text-muted">Se generează strategia...</p>
                </div>
              ) : strategyData?.strategy ? (
                <div className="prose prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap text-sm text-text-primary font-sans">
                    {strategyData.strategy}
                  </pre>
                </div>
              ) : (
                <p className="text-text-muted">Nu există strategie generată. Apasă refresh pentru a genera una.</p>
              )}
            </div>
          </Card.Body>
        </Card>

        {/* Live Logs */}
        <Card>
          <Card.Body>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <RefreshCw className="w-5 h-5" />
              Logs Live
            </h3>
            <div className="bg-primary-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-text-muted">Nu există loguri încă. Logs-urile vor apărea aici când transformarea pornește...</p>
              ) : (
                logs.map((log, idx) => {
                  const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('ro-RO') : new Date().toLocaleTimeString('ro-RO')
                  const message = log.message || JSON.stringify(log)
                  const isError = message.toLowerCase().includes('error') || message.toLowerCase().includes('eroare') || log.stage === 'error'
                  const isSuccess = message.includes('✅') || message.includes('complet') || log.stage === 'complete'
                  const isWarning = message.includes('⚠️') || log.stage === 'warning'
                  
                  return (
                    <div key={log._id || idx} className="mb-2 border-b border-primary-800 pb-1">
                      <span className="text-text-muted text-[10px]">[{timestamp}]</span>
                      <span className="text-text-muted text-[10px] ml-2">[{log.stage || 'info'}]</span>
                      <span className={`ml-2 ${
                        isError ? 'text-red-400' :
                        isWarning ? 'text-yellow-400' :
                        isSuccess ? 'text-green-400' :
                        'text-text-primary'
                      }`}>
                        {message}
                      </span>
                    </div>
                  )
                })
              )}
            </div>
          </Card.Body>
        </Card>

        {/* DeepSeek Chat */}
        <Card>
          <Card.Body>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              DeepSeek Chat
            </h3>
            <div className="bg-primary-900 rounded-lg p-4 h-96 flex flex-col">
              <div className="flex-1 overflow-y-auto mb-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <p className="text-text-muted text-sm">Începe o conversație cu DeepSeek...</p>
                ) : (
                  chatMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 ${
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center flex-shrink-0">
                          <Bot className="w-5 h-5 text-white" />
                        </div>
                      )}
                      <div
                        className={`max-w-[70%] rounded-lg p-3 ${
                          msg.role === 'user'
                            ? 'bg-accent-blue text-white'
                            : 'bg-primary-800 text-text-primary'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        {msg.action_executed && (
                          <p className="text-xs mt-2 text-green-400">
                            ✅ Acțiune executată: {msg.action_executed}
                          </p>
                        )}
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-primary-700 flex items-center justify-center flex-shrink-0">
                          <User className="w-5 h-5 text-text-primary" />
                        </div>
                      )}
                    </div>
                  ))
                )}
                {isChatLoading && (
                  <div className="flex gap-3 justify-start">
                    <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-primary-800 rounded-lg p-3">
                      <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleChatSend()}
                  placeholder="Scrie un mesaj..."
                  className="flex-1 px-4 py-2 bg-primary-800 border border-primary-700 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
                  disabled={isChatLoading}
                />
                <Button
                  onClick={handleChatSend}
                  disabled={!chatInput.trim() || isChatLoading}
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card.Body>
        </Card>
      </div>
    )
  } catch (renderError) {
    console.error('Render error:', renderError)
    return (
      <div className="flex items-center justify-center min-h-screen p-8 bg-primary-900">
        <div className="text-center max-w-2xl">
          <h2 className="text-2xl font-bold text-red-400 mb-4">⚠️ Eroare la randare</h2>
          <p className="text-text-primary mb-2">{renderError.message}</p>
          <pre className="text-xs text-text-muted bg-primary-800 p-4 rounded mb-4 overflow-auto max-h-64">
            {renderError.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-accent-blue-dark"
          >
            Reîncarcă pagina
          </button>
        </div>
      </div>
    )
  }
}

export default IndustryTransformation
