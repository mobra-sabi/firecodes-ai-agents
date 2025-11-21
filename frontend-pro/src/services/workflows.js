import api from './api'

/**
 * Workflows Service - API calls for workflow management
 */

// Start workflows
export const startAgentCreation = async (url) => {
  const response = await api.post('/workflows/start-agent-creation', { url })
  return response.data
}

export const startCompetitiveAnalysis = async (agentId) => {
  const response = await api.post('/workflows/start-competitive-analysis', { agent_id: agentId })
  return response.data
}

export const startSerpDiscovery = async (agentId, maxKeywords = 20) => {
  const response = await api.post('/workflows/start-serp-discovery', {
    agent_id: agentId,
    max_keywords: maxKeywords
  })
  return response.data
}

export const startTraining = async (modelName = 'qwen2.5', epochs = 3) => {
  const response = await api.post('/workflows/start-training', {
    model_name: modelName,
    epochs
  })
  return response.data
}

export const startSerpDiscoveryWithSlaves = async (agentId, numKeywords = null) => {
  const response = await api.post('/workflows/start-serp-discovery-with-slaves', {
    agent_id: agentId,
    num_keywords: numKeywords
  })
  return response.data
}

// Get workflow status
export const getWorkflowStatus = async (workflowId) => {
  const response = await api.get(`/workflows/status/${workflowId}`)
  return response.data
}

// List workflows
export const listActiveWorkflows = async () => {
  const response = await api.get('/workflows/active')
  return response.data
}

export const listRecentWorkflows = async (limit = 50) => {
  const response = await api.get(`/workflows/recent?limit=${limit}`)
  return response.data
}

// Control workflows
export const pauseWorkflow = async (workflowId) => {
  const response = await api.post(`/workflows/${workflowId}/pause`)
  return response.data
}

export const stopWorkflow = async (workflowId) => {
  const response = await api.post(`/workflows/${workflowId}/stop`)
  return response.data
}

// Competitive Intelligence
export const getCompetitiveAnalysis = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/competitive-analysis`)
  return response.data
}

export const getCompetitors = async (agentId, limit = 50) => {
  const response = await api.get(`/agents/${agentId}/competitors?limit=${limit}`)
  return response.data
}

export const getCompetitiveStrategy = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/strategy`)
  return response.data
}

// SERP Monitoring
export const getSerpRankings = async (agentId, limit = 10) => {
  const response = await api.get(`/agents/${agentId}/serp-rankings?limit=${limit}`)
  return response.data
}

export const refreshSerpRankings = async (agentId) => {
  const response = await api.post(`/agents/${agentId}/serp/refresh`)
  return response.data
}

export const getSerpHistory = async (agentId, days = 30) => {
  const response = await api.get(`/agents/${agentId}/serp/history?days=${days}`)
  return response.data
}

// Learning Center
export const getLearningStats = async () => {
  const response = await api.get('/learning/stats')
  return response.data
}

export const processLearningData = async () => {
  const response = await api.post('/learning/process-data')
  return response.data
}

export const buildJsonl = async () => {
  const response = await api.post('/learning/build-jsonl')
  return response.data
}

export const getTrainingStatus = async () => {
  const response = await api.get('/learning/training-status')
  return response.data
}

// Google Rankings & Ads Strategy
export const getGoogleRankingsMap = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/google-rankings-map`)
  return response.data
}

export const getGoogleAdsStrategy = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/google-ads-strategy`)
  return response.data
}

export const getSlaveAgents = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/slave-agents`)
  return response.data
}

export const getRankingsSummary = async (agentId) => {
  const response = await api.get(`/agents/${agentId}/rankings-summary`)
  return response.data
}
