import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const LoginPage = () => {
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
            <h1 className="text-3xl font-bold text-gradient mb-2">AI Agents Platform</h1>
            <p className="text-text-muted">Competitive Intelligence System</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-accent-red bg-opacity-10 border border-accent-red text-accent-red px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

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

            <Button type="submit" className="w-full" loading={isLoading}>
              Sign In
            </Button>

            <p className="text-center text-text-muted text-sm">
              Don't have an account?{' '}
              <Link to="/register" className="text-accent-blue hover:text-accent-blue-dark font-medium">
                Sign up
              </Link>
            </p>
          </form>
        </Card.Body>
      </Card>
    </div>
  )
}

export default LoginPage

