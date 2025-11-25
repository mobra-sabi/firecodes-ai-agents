import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, MessageSquare, FileText, RefreshCw, Loader2 } from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { useState } from 'react'
import CompetitiveAnalysisTab from '@/components/features/competitive/CompetitiveAnalysisTab'
import CompetitorsTab from '@/components/features/competitive/CompetitorsTab'
import SerpRankingsTab from '@/components/features/competitive/SerpRankingsTab'
import StrategyTab from '@/components/features/competitive/StrategyTab'
import CompetitiveStrategyTab from '@/components/features/competitive/CompetitiveStrategyTab'
import AgentChat from './AgentChat'
import SubdomainEditor from '@/components/SubdomainEditor'
import AgentConscienceTab from '@/components/features/conscience/AgentConscienceTab'
import AIConsultingTab from '@/components/features/consulting/AIConsultingTab'
import { Plus, Brain } from 'lucide-react'

const AgentDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState('')
  const [analysisProgress, setAnalysisProgress] = useState(0)

  // Fetch agent details
  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: async () => {
      const response = await api.get(`/agents/${id}`)
      return response.data
    },
    enabled: !!id,
  })

  // Fetch competitors (slaves)
  const { data: competitors } = useQuery({
    queryKey: ['competitors', id],
    queryFn: async () => {
      const response = await api.get(`/agents?master_id=${id}&type=slave`)
      return response.data
    },
    enabled: !!id,
  })

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'keywords', label: 'Keywords' },
    { id: 'competitive-analysis', label: 'Competitive Analysis' },
    { id: 'competitors', label: 'Competitors' },
    { id: 'serp', label: 'SERP Rankings' },
    { id: 'strategy', label: 'Strategy' },
    { id: 'consulting', label: '🧠 AI Consulting', highlight: true },
    { id: 'conscience', label: 'Conscience' },
    { id: 'chat', label: 'Chat' },
    { id: 'reports', label: 'Reports' },
  ]

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-primary-700 rounded w-1/4 mb-8"></div>
        <div className="h-96 bg-primary-700 rounded-lg"></div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Agent not found</p>
        <Link to="/agents">
          <Button className="mt-4">Back to Agents</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <Link to="/agents">
          <Button variant="ghost" icon={<ArrowLeft className="w-4 h-4" />} className="mb-4">
            Back to Agents
          </Button>
        </Link>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">{agent.domain}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                agent.status === 'active'
                  ? 'bg-accent-green bg-opacity-10 text-accent-green'
                  : 'bg-accent-yellow bg-opacity-10 text-accent-yellow'
              }`}>
                {agent.status}
              </span>
              {agent.industry && (
                <span className="text-text-muted">• {agent.industry}</span>
              )}
              {agent.created_at && (
                <span className="text-text-muted">
                  • Created {new Date(agent.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button 
              className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white"
              icon={<Brain className="w-4 h-4" />}
              onClick={() => navigate(`/agents/${id}/consulting`)}
            >
              AI Consulting
            </Button>
            <Button 
              variant="secondary" 
              icon={<MessageSquare className="w-4 h-4" />}
              onClick={() => navigate(`/agents/${id}/chat`)}
            >
              Chat
            </Button>
            <Button variant="secondary" icon={<FileText className="w-4 h-4" />}>
              Report
            </Button>
            <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-primary-600">
        <div className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? tab.highlight 
                    ? 'border-purple-500 text-purple-400 bg-purple-500/10'
                    : 'border-accent-blue text-accent-blue'
                  : tab.highlight
                    ? 'border-transparent text-purple-400 hover:text-purple-300 hover:bg-purple-500/5'
                    : 'border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'Chunks', value: agent.chunks_indexed || 0 },
              { label: 'Keywords', value: agent.keyword_count || 0 },
              { label: 'Competitors', value: agent.slave_count || 0 },
              { label: 'Avg Rank', value: '-' },
              { label: 'Coverage', value: '-' },
              { label: 'Top Position', value: '-' },
            ].map((kpi) => (
              <Card key={kpi.label}>
                <Card.Body className="p-4">
                  <p className="text-text-muted text-sm">{kpi.label}</p>
                  <p className="text-2xl font-bold text-text-primary mt-1">{kpi.value}</p>
                </Card.Body>
              </Card>
            ))}
          </div>

          {/* Subdomains */}
          {agent.subdomains && agent.subdomains.length > 0 && (
            <Card>
              <Card.Header>
                <Card.Title>Subdomains</Card.Title>
              </Card.Header>
              <Card.Body>
                <div className="space-y-3">
                  {agent.subdomains.map((subdomain, index) => (
                    <div key={index} className="flex items-start gap-3">
                      <span className="text-accent-blue">•</span>
                      <div>
                        <p className="text-text-primary font-medium">{subdomain.name}</p>
                        <p className="text-text-muted text-sm">{subdomain.description}</p>
                        {subdomain.keywords && (
                          <p className="text-text-muted text-xs mt-1">
                            {subdomain.keywords.length} keywords
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'keywords' && (
        <div className="space-y-6">
          {/* Buton Analiză DeepSeek */}
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-text-primary">DeepSeek Analysis</h3>
                  <p className="text-sm text-text-muted mt-1">
                    Analizează site-ul și generează subdomenii + keywords
                  </p>
                  {isAnalyzing && analysisStatus && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-text-primary">{analysisStatus}</span>
                        <span className="text-text-muted">{analysisProgress}%</span>
                      </div>
                      <div className="w-full bg-primary-700 rounded-full h-2">
                        <div
                          className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${analysisProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
                <Button
                  onClick={async () => {
                    setIsAnalyzing(true)
                    setAnalysisStatus('Pornire analiză...')
                    setAnalysisProgress(10)
                    
                    try {
                      // Folosește direct POST (WebSocket nu funcționează prin Cloudflare Tunnel)
                      setAnalysisStatus('Analizare cu DeepSeek...')
                      setAnalysisProgress(30)
                      
                      const response = await api.post(`/agents/${id}/analyze`)
                      
                      if (response.data.ok) {
                        setAnalysisStatus('✅ Analiză completă!')
                        setAnalysisProgress(100)
                        setIsAnalyzing(false)
                        
                        // Reîncarcă datele agentului după 1 secundă
                        setTimeout(() => {
                          window.location.reload()
                        }, 1000)
                      } else {
                        throw new Error(response.data.error || 'Analysis failed')
                      }
                    } catch (error) {
                      console.error('Analysis error:', error)
                      setIsAnalyzing(false)
                      setAnalysisStatus('')
                      setAnalysisProgress(0)
                      alert('Error: ' + (error.response?.data?.detail || error.message || 'Unknown error'))
                    }
                  }}
                  disabled={isAnalyzing}
                  className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    'Run DeepSeek Analysis'
                  )}
                </Button>
              </div>
            </Card.Body>
          </Card>

          {/* Subdomenii */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-text-primary">
                Subdomains {agent.subdomains && agent.subdomains.length > 0 && `(${agent.subdomains.length})`}
              </h3>
              <Button
                variant="secondary"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={async () => {
                  const name = prompt('Subdomain name:')
                  if (name) {
                    try {
                      await api.post(`/agents/${id}/subdomains`, {
                        name: name,
                        description: '',
                        keywords: [],
                        suggested_keywords: []
                      })
                      window.location.reload()
                    } catch (error) {
                      alert('Error: ' + (error.response?.data?.detail || error.message))
                    }
                  }
                }}
              >
                Add Subdomain
              </Button>
            </div>
            
            {agent.subdomains && agent.subdomains.length > 0 ? (
              agent.subdomains.map((subdomain, index) => (
                <SubdomainEditor
                  key={index}
                  subdomain={subdomain}
                  index={index}
                  agentId={id}
                  onUpdate={() => window.location.reload()}
                  onDelete={() => window.location.reload()}
                />
              ))
            ) : (
              <Card>
                <Card.Body className="py-8 text-center">
                  <p className="text-text-muted">No subdomains found. Run DeepSeek Analysis to generate subdomains.</p>
                </Card.Body>
              </Card>
            )}
          </div>

          {/* Keywords Generale */}
          <Card>
            <Card.Header>
              <Card.Title>Overall Keywords ({agent.overall_keywords?.length || agent.keyword_count || 0})</Card.Title>
            </Card.Header>
            <Card.Body>
              {agent.overall_keywords && agent.overall_keywords.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {agent.overall_keywords.map((keyword, index) => (
                    <span key={index} className="px-2 py-1 bg-primary-700 rounded text-sm text-text-primary">
                      {keyword}
                    </span>
                  ))}
                </div>
              ) : agent.keywords && agent.keywords.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {agent.keywords.map((keyword, index) => (
                    <span key={index} className="px-2 py-1 bg-primary-700 rounded text-sm text-text-primary">
                      {keyword}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-text-muted text-center py-8">No keywords found. Run DeepSeek Analysis to generate keywords.</p>
              )}
            </Card.Body>
          </Card>
        </div>
      )}

      {activeTab === 'competitive-analysis' && (
        <CompetitiveStrategyTab agentId={id} />
      )}

      {activeTab === 'competitors' && (
        <CompetitorsTab agentId={id} />
      )}

      {activeTab === 'serp' && (
        <SerpRankingsTab agentId={id} />
      )}

      {activeTab === 'strategy' && (
        <StrategyTab agentId={id} />
      )}

      {activeTab === 'consulting' && (
        <AIConsultingTab agentId={id} />
      )}

      {activeTab === 'conscience' && (
        <AgentConscienceTab agentId={id} />
      )}

      {activeTab === 'chat' && (
        <div className="mt-4">
          <AgentChat />
        </div>
      )}

      {activeTab === 'reports' && (
        <Card>
          <Card.Header>
            <Card.Title>SEO Reports</Card.Title>
          </Card.Header>
          <Card.Body>
            <p className="text-text-muted text-center py-8">No reports generated yet</p>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

export default AgentDetail

