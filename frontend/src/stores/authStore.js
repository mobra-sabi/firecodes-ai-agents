import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../lib/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: {
        email: 'demo@example.com',
        full_name: 'Demo User',
        role: 'admin'
      },
      token: 'demo-token-bypass',
      isAuthenticated: true, // Auto-authenticated for demo
      isLoading: false,
      error: null,

      // Login action - BYPASSED for demo
      login: async (email, password) => {
        set({ isLoading: true, error: null })
        
        // Bypass login - auto success
        const mockUser = {
          email: email || 'demo@example.com',
          full_name: 'Demo User',
          role: 'admin'
        }
        const mockToken = 'demo-token-bypass'
        
        set({
          user: mockUser,
          token: mockToken,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        })
        
        // Set token in API client
        api.defaults.headers.common['Authorization'] = `Bearer ${mockToken}`
        
        return { success: true }
      },

      // Register action
      register: async (email, password, companyName, industry) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post('/auth/register', {
            email,
            password,
            company_name: companyName,
            industry,
          })
          const { access_token, user } = response.data
          
          set({
            user,
            token: access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
          
          // Set token in API client
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
          
          return { success: true }
        } catch (error) {
          const errorMessage = error.response?.data?.detail || 'Registration failed'
          set({ isLoading: false, error: errorMessage })
          return { success: false, error: errorMessage }
        }
      },

      // Logout action
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
        
        // Remove token from API client
        delete api.defaults.headers.common['Authorization']
      },

      // Initialize auth from stored token
      initAuth: () => {
        const { token } = get()
        if (token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Initialize auth on app start
useAuthStore.getState().initAuth()

