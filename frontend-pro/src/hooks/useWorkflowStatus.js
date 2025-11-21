import { useState, useEffect, useCallback } from 'react'
import { getWorkflowStatus } from '../services/workflows'
import useWebSocket from './useWebSocket'

/**
 * Custom hook pentru monitoring workflow status cu WebSocket real-time updates
 * 
 * @param {string} workflowId - ID-ul workflow-ului de monitorizat
 * @param {object} options - Options { pollInterval, useWebSocketUpdates }
 * @returns {object} - { workflow, loading, error, refresh }
 */
export const useWorkflowStatus = (workflowId, options = {}) => {
  const {
    pollInterval = 0, // 0 = disabled, use WebSocket instead
    useWebSocketUpdates = true
  } = options

  const [workflow, setWorkflow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // WebSocket URL pentru acest workflow
  const wsUrl = workflowId && useWebSocketUpdates
    ? `ws://localhost:8000/api/workflows/ws/${workflowId}`
    : null

  // WebSocket connection
  const { lastMessage, isConnected } = useWebSocket(wsUrl, {
    enabled: !!wsUrl,
    onMessage: (data) => {
      // Update workflow cu data din WebSocket
      if (data.type === 'workflow_update' || data.type === 'workflow_status') {
        setWorkflow(data.data)
        setLoading(false)
      }
    },
    onError: (error) => {
      console.error('WebSocket error in useWorkflowStatus:', error)
    }
  })

  // Fetch initial workflow status
  const fetchWorkflow = useCallback(async () => {
    if (!workflowId) return

    try {
      setLoading(true)
      setError(null)
      const data = await getWorkflowStatus(workflowId)
      setWorkflow(data)
    } catch (err) {
      console.error('Error fetching workflow:', err)
      setError(err.message || 'Failed to fetch workflow')
    } finally {
      setLoading(false)
    }
  }, [workflowId])

  // Initial fetch
  useEffect(() => {
    fetchWorkflow()
  }, [fetchWorkflow])

  // Polling (dacă nu folosim WebSocket sau ca backup)
  useEffect(() => {
    if (!workflowId || !pollInterval || useWebSocketUpdates) return

    const interval = setInterval(() => {
      fetchWorkflow()
    }, pollInterval)

    return () => clearInterval(interval)
  }, [workflowId, pollInterval, useWebSocketUpdates, fetchWorkflow])

  return {
    workflow,
    loading,
    error,
    refresh: fetchWorkflow,
    isWebSocketConnected: isConnected
  }
}

export default useWorkflowStatus

