/**
 * Alerts API
 */
const API_BASE = '/api'

export const getAlerts = async (agentId = null, alertType = null, severity = null, status = 'active') => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  if (alertType) params.append('alert_type', alertType)
  if (severity) params.append('severity', severity)
  params.append('status', status)
  
  const response = await fetch(`${API_BASE}/alerts?${params}`)
  if (!response.ok) throw new Error('Failed to fetch alerts')
  return response.json()
}

export const checkAlerts = async (agentId) => {
  const response = await fetch(`${API_BASE}/alerts/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId })
  })
  if (!response.ok) throw new Error('Failed to check alerts')
  return response.json()
}

export const acknowledgeAlert = async (alertId) => {
  const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: 'POST'
  })
  if (!response.ok) throw new Error('Failed to acknowledge alert')
  return response.json()
}

export const resolveAlert = async (alertId, resolution = null) => {
  const response = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolution })
  })
  if (!response.ok) throw new Error('Failed to resolve alert')
  return response.json()
}

