/**
 * Organization Graph API
 */
const API_BASE = '/api'

export const getGraph = async (agentId) => {
  const response = await fetch(`${API_BASE}/graph/${agentId}`)
  if (!response.ok) throw new Error('Failed to fetch graph')
  return response.json()
}

export const updateGraph = async (agentId) => {
  const response = await fetch(`${API_BASE}/graph/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId })
  })
  if (!response.ok) throw new Error('Failed to update graph')
  return response.json()
}

export const getSimilarSlaves = async (agentId, limit = 10) => {
  const response = await fetch(`${API_BASE}/graph/${agentId}/similar?limit=${limit}`)
  if (!response.ok) throw new Error('Failed to fetch similar slaves')
  return response.json()
}

