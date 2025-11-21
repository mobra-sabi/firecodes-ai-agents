import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Send, Loader2, ArrowLeft, MessageSquare, Bot, User } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const AgentChat = () => {
  const { agentId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  // Fetch agent details
  const { data: agent } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}`)
      return response.data
    },
    enabled: !!agentId,
  })

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
      const response = await api.get(`/agents/${agentId}/chat/sessions/${sessionId}`)
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
      // Folosește endpoint-ul nou cu DeepSeek
      // Timeout mai mare pentru chat (30 secunde)
      const response = await api.post(`/agents/${agentId}/chat`, {
        message: userMessage,
        session_id: sessionId,
      }, {
        timeout: 30000 // 30 seconds
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
          context_used: response.data.context_used,
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

  return (
    <div className="flex flex-col h-screen bg-primary-900">
      {/* Header */}
      <div className="bg-primary-800 border-b border-primary-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              icon={<ArrowLeft className="w-4 h-4" />}
              onClick={() => navigate('/agents')}
            >
              Back
            </Button>
            <div>
              <h1 className="text-xl font-semibold text-text-primary">
                {agent?.domain || 'Loading...'}
              </h1>
              <p className="text-sm text-text-muted">
                Chat with {agent?.domain || 'agent'} - Powered by DeepSeek
              </p>
            </div>
          </div>
          {agent && (
            <div className="flex items-center gap-4 text-sm text-text-muted">
              <span>{agent.chunks_indexed || 0} chunks</span>
              <span>•</span>
              <span>{agent.keyword_count || 0} keywords</span>
              <span>•</span>
              <span>{agent.slave_count || 0} competitors</span>
            </div>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageSquare className="w-16 h-16 text-text-muted mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Start a conversation
            </h2>
            <p className="text-text-muted max-w-md">
              Chat with {agent?.domain || 'this agent'} to get insights about your business,
              competitive positioning, and SEO strategy. DeepSeek will analyze all your data
              including keywords, rankings, competitors, and CI reports.
            </p>
            <div className="mt-6 p-4 bg-primary-800 rounded-lg text-left max-w-md">
              <p className="text-sm text-text-muted mb-2">
                <strong className="text-text-primary">What you can ask:</strong>
              </p>
              <ul className="text-sm text-text-muted space-y-1 list-disc list-inside">
                <li>What are my top keywords and rankings?</li>
                <li>How do I compare with competitors?</li>
                <li>What SEO improvements should I make?</li>
                <li>What business insights can you provide?</li>
              </ul>
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
                  <Bot className="w-5 h-5 text-accent-blue" />
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
                {message.context_used && message.role === 'assistant' && (
                  <div className="mt-2 pt-2 border-t border-primary-700 text-xs text-text-muted">
                    <span>
                      Used {message.context_used.keywords_count || 0} keywords,{' '}
                      {message.context_used.competitors_count || 0} competitors,{' '}
                      {message.context_used.serp_results_count || 0} SERP results
                    </span>
                  </div>
                )}
                <p className="text-xs opacity-70 mt-1">
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
              <Bot className="w-5 h-5 text-accent-blue" />
            </div>
            <div className="bg-primary-800 rounded-lg px-4 py-3">
              <Loader2 className="w-5 h-5 animate-spin text-accent-blue" />
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
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
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
          💡 DeepSeek analyzes your complete business data: keywords, rankings, competitors, and CI reports
        </p>
      </div>
    </div>
  )
}

export default AgentChat

