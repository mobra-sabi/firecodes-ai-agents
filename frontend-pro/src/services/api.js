import axios from 'axios'

// Create axios instance with base configuration
// Detectează dacă suntem pe Cloudflare Tunnel și folosește URL-ul direct al backend-ului
const isCloudflare = window.location.hostname.includes('trycloudflare.com')
const baseURL = isCloudflare 
  ? 'https://opens-explained-neck-writings.trycloudflare.com/api'  // Backend tunnel
  : '/api'  // Local proxy

const api = axios.create({
  baseURL,
  timeout: 120000, // 2 minute - suficient pentru analize DeepSeek (poate dura 30-60 secunde)
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth-token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // DEMO MODE - Return mock data for specific endpoints
    const url = error.config?.url
    
    // Removed mock data for /stats - use real backend data
    
    // Removed mock for /agents - use real backend
    
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-token')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export default api

