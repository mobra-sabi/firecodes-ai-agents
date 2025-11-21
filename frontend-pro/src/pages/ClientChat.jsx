import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Send, ArrowLeft, Bot, User } from 'lucide-react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8090'

export default function ClientChat() {
  const { agentId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [agent, setAgent] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetchAgent()
    loadChatHistory()
  }, [agentId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchAgent = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/agents/${agentId}`)
      setAgent(response.data)
    } catch (error) {
      console.error('Error fetching agent:', error)
    }
  }

  const loadChatHistory = async () => {
    try {
      // Încarcă istoricul chat pentru agent
      const response = await axios.get(`${API_BASE}/api/agents/${agentId}/chat/history`)
      if (response.data && response.data.length > 0) {
        setMessages(response.data)
      } else {
        // Mesaj de bun venit
        setMessages([{
          role: 'assistant',
          content: `Bună! Sunt agentul tău AI pentru ${agent?.domain || 'site-ul tău'}. Cum te pot ajuta astăzi?`,
          timestamp: new Date().toISOString()
        }])
      }
    } catch (error) {
      // Dacă nu există istoric, adaugă mesaj de bun venit
      setMessages([{
        role: 'assistant',
        content: `Bună! Sunt agentul tău AI. Cum te pot ajuta astăzi cu SEO și recomandări?`,
        timestamp: new Date().toISOString()
      }])
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post(`${API_BASE}/api/agents/${agentId}/chat`, {
        message: input,
        session_id: `client_${agentId}_${Date.now()}`
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response || response.data.message || 'Nu am putut genera un răspuns.',
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content: 'Ne pare rău, a apărut o eroare. Te rugăm să încerci din nou.',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
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
            <div className="p-2 bg-blue-100 rounded-lg">
              <Bot className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                Chat cu {agent?.domain || 'Agentul'}
              </h1>
              <p className="text-sm text-gray-600">Agent AI pentru SEO</p>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto max-w-4xl w-full mx-auto px-4 py-6 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-900 border border-gray-200'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
            {msg.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-gray-600" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-blue-600" />
            </div>
            <div className="bg-white rounded-2xl px-4 py-3 border border-gray-200">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <form onSubmit={sendMessage} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Scrie un mesaj..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

