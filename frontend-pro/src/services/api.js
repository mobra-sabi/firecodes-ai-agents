import axios from 'axios'

// Create axios instance with base configuration
const isDev = import.meta.env.DEV
const baseURL = isDev ? '/api' : import.meta.env.VITE_API_URL || 'http://localhost:5001'

const api = axios.create({
  baseURL,
  timeout: 30000, // 30s - suficient pentru chat DeepSeek (poate dura 10-15 secunde)
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

