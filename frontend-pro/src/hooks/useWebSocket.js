import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * Custom hook pentru WebSocket connection cu auto-reconnect
 * 
 * @param {string} url - WebSocket URL (ex: ws://localhost:8000/api/workflows/ws/123)
 * @param {object} options - Options { enabled, onMessage, onError, reconnectInterval }
 * @returns {object} - { isConnected, lastMessage, sendMessage, disconnect }
 */
export const useWebSocket = (url, options = {}) => {
  const {
    enabled = true,
    onMessage = null,
    onError = null,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const shouldReconnectRef = useRef(true)

  const connect = useCallback(() => {
    if (!enabled || !url) return

    try {
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close()
      }

      // Create WebSocket connection
      const ws = new WebSocket(url)
      
      ws.onopen = () => {
        console.log('✅ WebSocket connected:', url)
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
          if (onMessage) {
            onMessage(data)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        if (onError) {
          onError(error)
        }
      }

      ws.onclose = () => {
        console.log('📡 WebSocket disconnected')
        setIsConnected(false)
        
        // Auto-reconnect if enabled and not manually closed
        if (shouldReconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          console.log(`🔄 Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('❌ Max reconnect attempts reached')
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Error creating WebSocket:', error)
    }
  }, [url, enabled, onMessage, onError, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
      return true
    }
    console.warn('WebSocket not connected, cannot send message')
    return false
  }, [])

  useEffect(() => {
    if (enabled && url) {
      shouldReconnectRef.current = true
      connect()
    }

    return () => {
      disconnect()
    }
  }, [url, enabled, connect, disconnect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect
  }
}

export default useWebSocket

