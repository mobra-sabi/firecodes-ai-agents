import { create } from 'zustand'
import api from '../services/api'

export const useAuthStore = create((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Initialize auth from localStorage
  initAuth: () => {
    const token = localStorage.getItem('auth-token')
    const userStr = localStorage.getItem('auth-user')
    
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        set({ token, user, isAuthenticated: true })
      } catch (error) {
        localStorage.removeItem('auth-token')
        localStorage.removeItem('auth-user')
      }
    }
  },

  // Login
  login: async (email, password) => {
    set({ isLoading: true, error: null })
    
    // DEMO MODE - Skip backend for now
    if (email === 'admin@example.com' && password === 'admin123') {
      const mockUser = {
        email: 'admin@example.com',
        full_name: 'Admin User',
        role: 'admin'
      }
      const mockToken = 'mock-jwt-token-demo'
      
      localStorage.setItem('auth-token', mockToken)
      localStorage.setItem('auth-user', JSON.stringify(mockUser))
      
      set({
        token: mockToken,
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
      })
      
      return { success: true }
    }
    
    try {
      const response = await api.post('/auth/login', { email, password })
      const { access_token, user } = response.data
      
      localStorage.setItem('auth-token', access_token)
      localStorage.setItem('auth-user', JSON.stringify(user))
      
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      })
      
      return { success: true }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      set({ error: errorMessage, isLoading: false })
      return { success: false, error: errorMessage }
    }
  },

  // Register
  register: async (email, password, name) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.post('/auth/register', { email, password, full_name: name })
      const { access_token, user } = response.data
      
      localStorage.setItem('auth-token', access_token)
      localStorage.setItem('auth-user', JSON.stringify(user))
      
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      })
      
      return { success: true }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Registration failed'
      set({ error: errorMessage, isLoading: false })
      return { success: false, error: errorMessage }
    }
  },

  // Logout
  logout: () => {
    localStorage.removeItem('auth-token')
    localStorage.removeItem('auth-user')
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    })
  },
}))

