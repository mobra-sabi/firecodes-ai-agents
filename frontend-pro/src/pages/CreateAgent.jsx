import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const CreateAgent = () => {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    site_url: '',
    industry: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await api.post('/agents', formData)
      if (response.data && response.data.ok) {
        const agentId = response.data.agent_id
        const workflowId = response.data.workflow_id
        const siteUrl = formData.site_url
        
        // Funcție pentru a găsi agentul și a redirecționa direct la Live Monitor
        const findAndRedirectToLiveMonitor = async (retries = 8, delay = 1500) => {
          for (let i = 0; i < retries; i++) {
            try {
              // Încearcă să găsească agentul după site_url
              const findResponse = await api.get('/agents/by-site-url', {
                params: { site_url: siteUrl }
              })
              
              if (findResponse.data && findResponse.data.ok && findResponse.data.agent_id) {
                // Agentul găsit - redirecționează DIRECT la Live Monitor (NU la lista de agenți)
                navigate(`/agents/${findResponse.data.agent_id}/live`)
                return true
              }
            } catch (err) {
              // Continuă să încerce
              console.log(`Attempt ${i + 1}/${retries} - Agent not found yet, retrying...`)
            }
            
            // Așteaptă înainte de următoarea încercare
            if (i < retries - 1) {
              await new Promise(resolve => setTimeout(resolve, delay))
            }
          }
          
          // Dacă nu s-a găsit după toate încercările, încă redirecționează la Live Monitor
          // LiveMonitor va încerca să găsească agentul periodic folosind workflow_id
          // Salvăm workflow_id în sessionStorage pentru LiveMonitor
          sessionStorage.setItem('pending_workflow_id', workflowId)
          sessionStorage.setItem('pending_site_url', siteUrl)
          navigate(`/agents/workflow/${workflowId}/live`)
          return false
        }
        
        if (agentId) {
          // Agentul există deja - redirecționează DIRECT la Live Monitor
          navigate(`/agents/${agentId}/live`)
        } else {
          // Agentul nu există încă - încearcă să-l găsească și redirecționează la Live Monitor
          await findAndRedirectToLiveMonitor()
        }
      } else {
        alert('Failed to create agent: ' + (response.data?.error || 'Unknown error'))
      }
    } catch (error) {
      alert('Failed to create agent: ' + (error.response?.data?.detail || error.message))
    } finally {
      setIsLoading(false)
    }
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <Link to="/agents">
          <Button variant="ghost" icon={<ArrowLeft className="w-4 h-4" />} className="mb-4">
            Back to Agents
          </Button>
        </Link>
        
        <h1 className="text-3xl font-bold text-text-primary">Create Master Agent</h1>
        <p className="text-text-muted mt-2">
          Create a new AI agent for competitive intelligence
        </p>
      </div>

      {/* Form */}
      <Card>
        <Card.Body className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="site_url" className="block text-sm font-medium text-text-primary mb-2">
                Site URL *
              </label>
              <input
                id="site_url"
                name="site_url"
                type="url"
                required
                value={formData.site_url}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="https://example.com"
              />
              <p className="text-xs text-text-muted mt-1">
                Enter the full URL of the site you want to analyze
              </p>
            </div>

            <div>
              <label htmlFor="industry" className="block text-sm font-medium text-text-primary mb-2">
                Industry *
              </label>
              <input
                id="industry"
                name="industry"
                type="text"
                required
                value={formData.industry}
                onChange={handleChange}
                className="input-custom w-full"
                placeholder="e.g., Construction, Real Estate, Marketing"
              />
              <p className="text-xs text-text-muted mt-1">
                Specify the industry for better analysis
              </p>
            </div>

            <div className="bg-primary-800 border border-primary-600 rounded-lg p-4">
              <h3 className="font-medium text-text-primary mb-2">What happens next?</h3>
              <ul className="space-y-2 text-sm text-text-muted">
                <li>• Site will be scraped and analyzed with AI</li>
                <li>• Keywords will be generated (10-15 per subdomain)</li>
                <li>• Competitors will be discovered via Google search</li>
                <li>• Slave agents will be created for competitors</li>
                <li>• SEO report will be generated</li>
                <li>• Estimated time: 20-45 minutes</li>
              </ul>
            </div>

            <div className="flex gap-4">
              <Button type="submit" className="flex-1" loading={isLoading}>
                Create Agent
              </Button>
              <Link to="/agents" className="flex-1">
                <Button type="button" variant="secondary" className="w-full">
                  Cancel
                </Button>
              </Link>
            </div>
          </form>
        </Card.Body>
      </Card>
    </div>
  )
}

export default CreateAgent

