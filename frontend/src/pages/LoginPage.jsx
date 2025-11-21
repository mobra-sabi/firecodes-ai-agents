import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Bot, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, isLoading, error } = useAuthStore()
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    const result = await login(formData.email, formData.password)
    if (result.success) {
      navigate('/dashboard')
    }
  }

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4">
            <Bot className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-dark-900 mb-2">
            AI Agent Platform
          </h1>
          <p className="text-dark-600">
            Competitive Intelligence with AI
          </p>
        </div>

        {/* Login Card */}
        <div className="card">
          <h2 className="text-2xl font-semibold mb-6 text-center">
            Welcome Back
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-dark-700 mb-1">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="input"
                placeholder="you@company.com"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark-700 mb-1">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="input"
                placeholder="••••••••"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-dark-600">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign up
            </Link>
          </div>
        </div>

        {/* Demo Credentials (for development) */}
        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
          <p className="font-medium text-yellow-800 mb-1">🔑 Demo Credentials:</p>
          <p className="text-yellow-700">
            Email: <code className="bg-yellow-100 px-1 rounded">demo@example.com</code><br />
            Password: <code className="bg-yellow-100 px-1 rounded">demo123</code>
          </p>
        </div>
      </div>
    </div>
  )
}

