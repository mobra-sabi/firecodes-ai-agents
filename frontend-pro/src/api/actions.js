/**
 * Actions Queue API
 */
const API_BASE = '/api'

export const getActionsQueue = async (agentId = null, status = null) => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  if (status) params.append('status', status)
  params.append('limit', '50')
  
  const response = await fetch(`${API_BASE}/actions/queue?${params}`)
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Failed to fetch actions queue: ${error}`)
  }
  const data = await response.json()
  // Return actions array directly if response has 'actions' field
  return data.actions || data || []
}

export const addAction = async (actionData) => {
  const response = await fetch(`${API_BASE}/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(actionData)
  })
  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Failed to add action: ${error}`)
  }
  return response.json()
}

export const getActionDetails = async (actionId) => {
  const response = await fetch(`${API_BASE}/actions/${actionId}`)
  if (!response.ok) throw new Error('Failed to fetch action details')
  return response.json()
}

export const updateActionStatus = async (actionId, status, result = null, error = null) => {
  const response = await fetch(`${API_BASE}/actions/${actionId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, result, error })
  })
  if (!response.ok) throw new Error('Failed to update action status')
  return response.json()
}

export const getActionsStats = async (agentId = null) => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  
  const response = await fetch(`${API_BASE}/actions/stats?${params}`)
  if (!response.ok) throw new Error('Failed to fetch actions stats')
  return response.json()
}

