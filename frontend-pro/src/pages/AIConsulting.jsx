import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { 
  ArrowLeft, 
  Brain, 
  Building2, 
  Users, 
  Target, 
  TrendingUp,
  Sparkles,
  MessageSquare,
  FileText,
  Globe,
  Zap
} from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import AIConsultingTab from '@/components/features/consulting/AIConsultingTab'

const AIConsulting = () => {
  const { agentId } = useParams()
  
  // Fetch agent details
  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}`)
      return response.data
    },
    enabled: !!agentId
  })

  // Fetch competitive map stats
  const { data: competitiveMap } = useQuery({
    queryKey: ['competitive-map', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/competitive-map`)
      return response.data
    },
    enabled: !!agentId
  })

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-primary-700 rounded w-1/4"></div>
        <div className="h-64 bg-primary-700 rounded-lg"></div>
      </div>
    )
  }

  const stats = [
    { 
      label: 'Competitori Analizați', 
      value: competitiveMap?.competitive_map?.length || 0,
      icon: Users,
      color: 'text-blue-400'
    },
    { 
      label: 'Keywords Monitorizate', 
      value: competitiveMap?.keywords_processed || 0,
      icon: Target,
      color: 'text-green-400'
    },
    { 
      label: 'Agenți Creați', 
      value: competitiveMap?.slave_agents_created || 0,
      icon: Brain,
      color: 'text-purple-400'
    },
    { 
      label: 'Site-uri Recomandate', 
      value: competitiveMap?.recommended_sites_count || 0,
      icon: Globe,
      color: 'text-yellow-400'
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/agents/${agentId}`}>
            <Button variant="ghost" icon={<ArrowLeft className="w-4 h-4" />} className="mb-2">
              Înapoi la Agent
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-blue-500 rounded-xl">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">
                Consultant AI pentru {agent?.domain}
              </h1>
              <p className="text-text-muted">
                Analiză competitivă și recomandări strategice powered by DeepSeek
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <Card key={index} className="bg-primary-800/50">
            <Card.Body className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 bg-primary-700 rounded-lg ${stat.color}`}>
                  <stat.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-text-primary">{stat.value}</p>
                  <p className="text-xs text-text-muted">{stat.label}</p>
                </div>
              </div>
            </Card.Body>
          </Card>
        ))}
      </div>

      {/* Main Consulting Component */}
      <AIConsultingTab agentId={agentId} />
    </div>
  )
}

export default AIConsulting

