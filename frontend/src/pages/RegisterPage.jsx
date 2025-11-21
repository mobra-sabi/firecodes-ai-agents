import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Bot, Loader2 } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuthStore()
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    companyName: '',
    industry: '',
  })
  
  const [validationError, setValidationError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setValidationError('')
    
    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setValidationError('Passwords do not match')
      return
    }
    
    // Validate password length
    if (formData.password.length < 6) {
      setValidationError('Password must be at least 6 characters')
      return
    }
    
    const result = await register(
      formData.email,
      formData.password,
      formData.companyName,
      formData.industry
    )
    
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

  const displayError = validationError || error

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
            Start your competitive intelligence journey
          </p>
        </div>

        {/* Register Card */}
        <div className="card">
          <h2 className="text-2xl font-semibold mb-6 text-center">
            Create Account
          </h2>

          {displayError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {displayError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-dark-700 mb-1">
                Email *
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
              <label htmlFor="companyName" className="block text-sm font-medium text-dark-700 mb-1">
                Company Name *
              </label>
              <input
                id="companyName"
                name="companyName"
                type="text"
                required
                value={formData.companyName}
                onChange={handleChange}
                className="input"
                placeholder="Your Company"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="industry" className="block text-sm font-medium text-dark-700 mb-1">
                Industry *
              </label>
              <input
                id="industry"
                name="industry"
                type="text"
                required
                value={formData.industry}
                onChange={handleChange}
                className="input"
                placeholder="e.g., Construction, SaaS, E-commerce"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark-700 mb-1">
                Password *
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
              <p className="text-xs text-dark-500 mt-1">
                Minimum 6 characters
              </p>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-dark-700 mb-1">
                Confirm Password *
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                value={formData.confirmPassword}
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
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-dark-600">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

