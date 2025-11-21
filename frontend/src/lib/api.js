import axios from 'axios'

// Create axios instance with base configuration
// Use dashboard_api.py (port 5000) - REAL API with real data
const isDev = import.meta.env.DEV
const baseURL = isDev ? '/api' : 'https://sum-removed-enzyme-butler.trycloudflare.com'

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Token is already set in auth store
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export default api

