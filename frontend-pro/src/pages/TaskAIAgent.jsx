import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Loader2, ArrowLeft, MessageSquare, Bot, User, Zap, CheckCircle2, XCircle } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const TaskAIAgent = () => {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  // Load conversation history if session exists
  useEffect(() => {
    if (sessionId) {
      loadConversationHistory()
    }
  }, [sessionId])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversationHistory = async () => {
    if (!sessionId) return

    try {
      const response = await api.get(`/task-ai/sessions/${sessionId}`)
      if (response.data.ok && response.data.messages) {
        setMessages(response.data.messages)
      }
    } catch (error) {
      console.error('Error loading conversation history:', error)
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage = inputMessage.trim()
    setInputMessage('')
    
    // Add user message to UI immediately
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, newUserMessage])

    setIsLoading(true)

    try {
      // Timeout mai mare pentru task execution (60 secunde)
      const response = await api.post(`/task-ai/chat`, {
        message: userMessage,
        session_id: sessionId,
      }, {
        timeout: 60000 // 60 seconds
      })

      if (response.data.ok) {
        // Set session ID if this is the first message
        if (!sessionId && response.data.session_id) {
          setSessionId(response.data.session_id)
        }

        // Add assistant response
        const assistantMessage = {
          role: 'assistant',
          content: response.data.response,
          timestamp: response.data.timestamp,
          actions_executed: response.data.actions_executed || [],
        }
        setMessages((prev) => [...prev, assistantMessage])
      } else {
        throw new Error('Failed to get response')
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        error: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const renderActionResult = (action) => {
    if (!action.result) return null

    const result = action.result
    const isSuccess = result.ok

    return (
      <div className={`mt-2 p-3 rounded-lg border ${
        isSuccess ? 'bg-green-900/20 border-green-700' : 'bg-red-900/20 border-red-700'
      }`}>
        <div className="flex items-center gap-2 mb-2">
          {isSuccess ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          <span className={`text-sm font-semibold ${
            isSuccess ? 'text-green-400' : 'text-red-400'
          }`}>
            {action.type.toUpperCase()} Action {isSuccess ? 'Success' : 'Failed'}
          </span>
        </div>
        {result.output && (
          <pre className="text-xs text-text-muted bg-primary-900 p-2 rounded overflow-x-auto">
            {typeof result.output === 'string' ? result.output : JSON.stringify(result.output, null, 2)}
          </pre>
        )}
        {result.error && (
          <p className="text-xs text-red-400 mt-1">{result.error}</p>
        )}
        {result.response && (
          <pre className="text-xs text-text-muted bg-primary-900 p-2 rounded overflow-x-auto mt-2">
            {typeof result.response === 'string' ? result.response : JSON.stringify(result.response, null, 2)}
          </pre>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-primary-900">
      {/* Header */}
      <div className="bg-primary-800 border-b border-primary-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              icon={<ArrowLeft className="w-4 h-4" />}
              onClick={() => navigate('/')}
            >
              Back
            </Button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-accent-blue" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-text-primary">
                  Task AI Agent
                </h1>
                <p className="text-sm text-text-muted">
                  AI Assistant powered by DeepSeek - Execute tasks through chat
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-text-muted">
            <span>💡 Task Execution Enabled</span>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-20 h-20 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center mb-4">
              <Zap className="w-10 h-10 text-accent-blue" />
            </div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Task AI Agent - Asistent AI Consultativ
            </h2>
            <p className="text-text-muted max-w-2xl mb-6">
              Bună! Sunt un asistent AI prietenos care te poate ajuta să rezolvi task-uri prin conversație naturală.
              Înainte de a executa orice, te voi consulta și voi explica clar ce pot face.
            </p>
            
            {/* Ghid Complet de Capabilități */}
            <div className="mt-6 p-6 bg-primary-800 rounded-lg text-left max-w-3xl w-full">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-accent-blue" />
                Ce pot face pentru tine?
              </h3>
              
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div className="p-4 bg-primary-700 rounded-lg">
                  <h4 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="text-accent-blue">💻</span> Comenzi Shell
                  </h4>
                  <p className="text-sm text-text-muted mb-2">
                    Pot executa comenzi shell sigure pentru analiză și verificări.
                  </p>
                  <ul className="text-xs text-text-muted space-y-1 ml-4">
                    <li>• <code className="text-accent-blue">ls</code>, <code className="text-accent-blue">cat</code>, <code className="text-accent-blue">grep</code></li>
                    <li>• <code className="text-accent-blue">curl</code>, <code className="text-accent-blue">head</code>, <code className="text-accent-blue">tail</code></li>
                    <li>• <code className="text-accent-blue">find</code>, <code className="text-accent-blue">wc</code>, <code className="text-accent-blue">grep</code></li>
                  </ul>
                  <p className="text-xs text-red-400 mt-2">⚠️ Nu pot: rm -rf, format, shutdown</p>
                </div>

                <div className="p-4 bg-primary-700 rounded-lg">
                  <h4 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="text-accent-blue">🌐</span> Apeluri API
                  </h4>
                  <p className="text-sm text-text-muted mb-2">
                    Pot face request-uri HTTP către servicii locale.
                  </p>
                  <ul className="text-xs text-text-muted space-y-1 ml-4">
                    <li>• Verificare health endpoints</li>
                    <li>• Obținere date din backend</li>
                    <li>• Status servicii (MongoDB, Qdrant)</li>
                  </ul>
                  <p className="text-xs text-red-400 mt-2">⚠️ Doar localhost pentru securitate</p>
                </div>

                <div className="p-4 bg-primary-700 rounded-lg">
                  <h4 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="text-accent-blue">📄</span> Operații Fișiere
                  </h4>
                  <p className="text-sm text-text-muted mb-2">
                    Pot citi fișiere din directorul proiectului.
                  </p>
                  <ul className="text-xs text-text-muted space-y-1 ml-4">
                    <li>• Citire cod sursă</li>
                    <li>• Verificare configurații</li>
                    <li>• Analiză loguri</li>
                  </ul>
                  <p className="text-xs text-red-400 mt-2">⚠️ Doar citire, nu modificare</p>
                </div>

                <div className="p-4 bg-primary-700 rounded-lg">
                  <h4 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="text-accent-blue">🗄️</span> Interogări Database
                  </h4>
                  <p className="text-sm text-text-muted mb-2">
                    Pot interoga colecții MongoDB permise.
                  </p>
                  <ul className="text-xs text-text-muted space-y-1 ml-4">
                    <li>• Numărare agenți</li>
                    <li>• Listare date</li>
                    <li>• Căutări simple</li>
                  </ul>
                  <p className="text-xs text-red-400 mt-2">⚠️ Doar citire, nu modificare</p>
                </div>
              </div>

              <div className="mt-4 p-4 bg-accent-blue bg-opacity-10 border border-accent-blue border-opacity-30 rounded-lg">
                <h4 className="font-semibold text-accent-blue mb-2">🎯 Cum lucrez?</h4>
                <ul className="text-sm text-text-muted space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-accent-blue">1.</span>
                    <span><strong>Întreb</strong> înainte de a executa acțiuni complexe sau multiple</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-accent-blue">2.</span>
                    <span><strong>Explic</strong> clar ce voi face și de ce</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-accent-blue">3.</span>
                    <span><strong>Ofer</strong> alternative și sugestii, nu doar execuții automate</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-accent-blue">4.</span>
                    <span><strong>Confirm</strong> cu tine înainte de workflow-uri complexe</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Exemple de Utilizare */}
            <div className="mt-6 p-6 bg-primary-800 rounded-lg text-left max-w-3xl w-full">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Bot className="w-5 h-5 text-accent-blue" />
                Exemple de întrebări
              </h3>
              <div className="grid md:grid-cols-2 gap-3">
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Verifică statusul MongoDB"
                </div>
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Câți agenți avem în baza de date?"
                </div>
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Citește primele 50 de linii din agent_api.py"
                </div>
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Arată-mi răspunsul de la endpoint-ul /health"
                </div>
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Listează toate fișierele .py din directorul curent"
                </div>
                <div className="p-3 bg-primary-700 rounded text-sm text-text-muted">
                  "Analizează site-ul X și găsește concurenți"
                </div>
              </div>
              <p className="text-xs text-text-muted mt-4 text-center">
                💡 <strong>Tip:</strong> Fii specific în cererile tale. Eu voi întreba dacă am nevoie de clarificări!
              </p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-accent-blue" />
                </div>
              )}
              <div
                className={`max-w-2xl rounded-lg px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-accent-blue text-white'
                    : 'bg-primary-800 text-text-primary'
                } ${message.error ? 'border border-red-500' : ''}`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {/* Show executed actions */}
                {message.actions_executed && message.actions_executed.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-primary-700">
                    <p className="text-xs text-text-muted mb-2 font-semibold">
                      Actions Executed:
                    </p>
                    {message.actions_executed.map((action, actionIndex) => (
                      <div key={actionIndex} className="mb-2">
                        {renderActionResult(action)}
                      </div>
                    ))}
                  </div>
                )}
                
                <p className="text-xs opacity-70 mt-2">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
              {message.role === 'user' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
                  <User className="w-5 h-5 text-accent-blue" />
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-accent-blue bg-opacity-20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-accent-blue" />
            </div>
            <div className="bg-primary-800 rounded-lg px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />
              <span className="text-text-muted">Processing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-primary-800 border-t border-primary-700 px-6 py-4">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe the task you want me to execute... (Press Enter to send, Shift+Enter for new line)"
              className="w-full px-4 py-3 bg-primary-900 border border-primary-700 rounded-lg text-text-primary placeholder-text-muted resize-none focus:outline-none focus:ring-2 focus:ring-accent-blue"
              rows={3}
              disabled={isLoading}
            />
          </div>
          <Button
            icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
          >
            Send
          </Button>
        </div>
        <p className="text-xs text-text-muted mt-2">
          ⚡ Task AI Agent can execute shell commands, API calls, file operations, and database queries
        </p>
      </div>
    </div>
  )
}

export default TaskAIAgent

