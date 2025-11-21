/**
 * Google Ads API
 */
const API_BASE = '/api'

export const getAdsOAuthUrl = async (agentId) => {
  const response = await fetch(`${API_BASE}/ads/oauth/url?agent_id=${agentId}`)
  if (!response.ok) throw new Error('Failed to get OAuth URL')
  return response.json()
}

export const setCustomerId = async (agentId, customerId) => {
  const response = await fetch(`${API_BASE}/ads/accounts/${agentId}/customer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId })
  })
  if (!response.ok) throw new Error('Failed to set customer ID')
  return response.json()
}

export const createCampaign = async (campaignData) => {
  const response = await fetch(`${API_BASE}/ads/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(campaignData)
  })
  if (!response.ok) throw new Error('Failed to create campaign')
  return response.json()
}

export const createAdGroup = async (adGroupData) => {
  const response = await fetch(`${API_BASE}/ads/ad-groups`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(adGroupData)
  })
  if (!response.ok) throw new Error('Failed to create ad group')
  return response.json()
}

export const addKeywords = async (keywordsData) => {
  const response = await fetch(`${API_BASE}/ads/keywords`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(keywordsData)
  })
  if (!response.ok) throw new Error('Failed to add keywords')
  return response.json()
}

export const createRSAAd = async (adData) => {
  const response = await fetch(`${API_BASE}/ads/rsa-ads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(adData)
  })
  if (!response.ok) throw new Error('Failed to create RSA ad')
  return response.json()
}

export const syncFromSEO = async (agentId, keywords = null, intentFilter = 'transactional') => {
  const response = await fetch(`${API_BASE}/ads/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId, keywords, intent_filter: intentFilter })
  })
  if (!response.ok) throw new Error('Failed to sync from SEO')
  return response.json()
}

export const getCampaigns = async (agentId = null) => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  
  const response = await fetch(`${API_BASE}/ads/campaigns?${params}`)
  if (!response.ok) throw new Error('Failed to fetch campaigns')
  return response.json()
}

