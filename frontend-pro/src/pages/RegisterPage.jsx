import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const RegisterPage = () => {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuthStore()
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match')
      return
    }
    
    const result = await register(formData.email, formData.password, formData.name)
    if (result.success) {
      navigate('/')
    }
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-primary-900 px-4">
      <Card className="w-full max-w-md">
        <Card.Body className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gradient mb-2">Create Account</h1>
            <p className="text-text-muted">Get started with AI Agents</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-accent-red bg-opacity-10 border border-accent-red text-accent-red px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-text-primary mb-2">
                Full Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                value={formData.name}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="John Doe"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-primary mb-2">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text-primary mb-2">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="••••••••"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-primary mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="••••••••"
              />
            </div>

            <Button type="submit" className="w-full" loading={isLoading}>
              Create Account
            </Button>

            <p className="text-center text-text-muted text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-accent-blue hover:text-accent-blue-dark font-medium">
                Sign in
              </Link>
            </p>
          </form>
        </Card.Body>
      </Card>
    </div>
  )
}

export default RegisterPage

