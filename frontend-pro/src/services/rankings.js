// Rankings Monitor Service - REAL API Calls pentru FAZA 2
import api from './api'

/**
 * Obține statistici REALE despre rankings din MongoDB
 */
export const getRankingsStatistics = async (agentId) => {
  const response = await api.get(`/api/agents/${agentId}/rankings-statistics`)
  return response.data
}

/**
 * Salvează snapshot REAL în MongoDB rankings_history
 */
export const saveRankingsSnapshot = async (agentId) => {
  const response = await api.post(`/api/agents/${agentId}/rankings-snapshot`)
  return response.data
}

/**
 * Obține trend REAL pentru ultimele N zile
 */
export const getRankingsTrend = async (agentId, days = 30) => {
  const response = await api.get(`/api/agents/${agentId}/rankings-trend`, {
    params: { days }
  })
  return response.data
}

/**
 * Obține leaderboard REAL al competitorilor
 */
export const getCompetitorLeaderboard = async (agentId) => {
  const response = await api.get(`/api/agents/${agentId}/competitor-leaderboard`)
  return response.data
}

/**
 * Obține istoric REAL snapshots din MongoDB
 */
export const getRankingsHistory = async (agentId, limit = 30) => {
  const response = await api.get(`/api/agents/${agentId}/rankings-history`, {
    params: { limit }
  })
  return response.data
}

/**
 * Calculează scor vizibilitate per competitor (client-side helper)
 */
export const calculateVisibilityScore = (rankings) => {
  if (!rankings || rankings.length === 0) return 0
  
  let totalScore = 0
  rankings.forEach(rank => {
    const position = rank.position
    if (position <= 3) totalScore += 10
    else if (position <= 10) totalScore += 5
    else if (position <= 20) totalScore += 2
  })
  
  return totalScore
}

/**
 * Determină trend badge (improving/stable/declining)
 */
export const getTrendBadge = (trend) => {
  if (trend === 'improving') {
    return { label: '📈 Improving', color: 'bg-accent-green', textColor: 'text-white' }
  } else if (trend === 'declining') {
    return { label: '📉 Declining', color: 'bg-accent-red', textColor: 'text-white' }
  } else {
    return { label: '➡️ Stable', color: 'bg-accent-yellow', textColor: 'text-dark-bg' }
  }
}

/**
 * Formatează poziție pentru display
 */
export const formatPosition = (position) => {
  if (!position) return 'Not in Top 20'
  return `#${position}`
}

/**
 * Obține culoare pe baza poziției
 */
export const getPositionColor = (position) => {
  if (!position) return 'bg-gray-600'
  if (position <= 3) return 'bg-accent-green'
  if (position <= 10) return 'bg-accent-yellow'
  return 'bg-accent-red'
}

