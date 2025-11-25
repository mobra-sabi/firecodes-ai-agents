import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Brain, 
  MessageSquare, 
  FileText, 
  Users, 
  Target, 
  TrendingUp,
  Building2,
  Globe,
  Loader2,
  ChevronDown,
  ChevronRight,
  Send,
  Sparkles,
  Download,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

const AIConsultingTab = ({ agentId }) => {
  const queryClient = useQueryClient()
  const [activeSection, setActiveSection] = useState('overview')
  const [expandedCategories, setExpandedCategories] = useState({})
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [selectedReportType, setSelectedReportType] = useState('full')

  // Fetch discovery questions
  const { data: discoveryQuestions } = useQuery({
    queryKey: ['consulting-questions', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/consulting/discovery-questions`)
      return response.data.questions
    }
  })

  // Fetch previous reports
  const { data: previousReports, isLoading: loadingReports } = useQuery({
    queryKey: ['consulting-reports', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/consulting/reports?limit=10`)
      return response.data.reports
    }
  })

  // Generate report mutation
  const generateReportMutation = useMutation({
    mutationFn: async (reportType) => {
      const response = await api.post(`/agents/${agentId}/consulting/generate-report?report_type=${reportType}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['consulting-reports', agentId])
    }
  })

  // Ask question mutation
  const askQuestionMutation = useMutation({
    mutationFn: async ({ question, context }) => {
      const response = await api.post(`/agents/${agentId}/consulting/ask`, { question, context })
      return response.data
    }
  })

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return

    const userMessage = chatMessage
    setChatMessage('')
    setChatHistory(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      const result = await askQuestionMutation.mutateAsync({
        question: userMessage,
        context: chatHistory.map(m => `${m.role}: ${m.content}`).join('\n')
      })
      setChatHistory(prev => [...prev, { role: 'assistant', content: result.answer }])
    } catch (error) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: 'Eroare la procesarea întrebării. Încearcă din nou.' 
      }])
    }
  }

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }))
  }

  const reportTypes = [
    { id: 'full', label: 'Raport Complet', icon: FileText, description: 'Analiză completă cu toate secțiunile', time: '~2 min' },
    { id: 'quick', label: 'Raport Rapid', icon: Sparkles, description: 'Top competitori + acțiuni imediate', time: '~30 sec' },
    { id: 'seo', label: 'Audit SEO', icon: Target, description: 'Gap analysis și strategie conținut', time: '~1 min' },
    { id: 'expansion', label: 'Expansiune', icon: TrendingUp, description: 'Subdomenii și servicii noi', time: '~1 min' },
  ]

  const categoryLabels = {
    team_capacity: { label: 'Echipă și Capacitate', icon: Users },
    services_differentiation: { label: 'Servicii și Diferențiere', icon: Target },
    clients_market: { label: 'Clienți și Piață', icon: Globe },
    objectives_resources: { label: 'Obiective și Resurse', icon: TrendingUp }
  }

  return (
    <div className="space-y-6">
      {/* Navigation Tabs */}
      <div className="flex gap-2 p-1 bg-primary-800 rounded-lg">
        {[
          { id: 'overview', label: 'Prezentare', icon: Brain },
          { id: 'discovery', label: 'Descoperire Business', icon: MessageSquare },
          { id: 'reports', label: 'Rapoarte AI', icon: FileText },
          { id: 'chat', label: 'Consultant AI', icon: Sparkles },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
              activeSection === tab.id
                ? 'bg-accent-blue text-white'
                : 'text-text-muted hover:text-text-primary hover:bg-primary-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Section */}
      {activeSection === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-gradient-to-br from-purple-900/50 to-primary-800 border-purple-500/30">
            <Card.Body className="p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <Brain className="w-8 h-8 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">Consultant AI DeepSeek</h3>
                  <p className="text-purple-200 mt-2">
                    Analizez concurența, identific oportunități și ofer recomandări personalizate pentru creșterea afacerii tale.
                  </p>
                  <div className="flex gap-2 mt-4">
                    <span className="px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-300">
                      25 competitori analizați
                    </span>
                    <span className="px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-300">
                      69 keywords
                    </span>
                    <span className="px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-300">
                      11.857 chunks
                    </span>
                  </div>
                </div>
              </div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Ce pot face pentru tine?</h3>
              <ul className="space-y-3">
                {[
                  'Analiză competitivă detaliată cu rankuri SERP',
                  'Recomandări SEO și content marketing',
                  'Sugestii de subdomenii și servicii noi',
                  'Template-uri oferte pentru parteneriate B2B',
                  'Plan de acțiune pe 90 de zile',
                  'Răspunsuri la întrebări specifice business'
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-text-secondary">
                    <CheckCircle2 className="w-4 h-4 text-accent-green" />
                    {item}
                  </li>
                ))}
              </ul>
            </Card.Body>
          </Card>

          {/* Quick Actions */}
          <Card className="md:col-span-2">
            <Card.Header>
              <Card.Title>Acțiuni Rapide</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {reportTypes.map(type => (
                  <button
                    key={type.id}
                    onClick={() => {
                      setSelectedReportType(type.id)
                      setActiveSection('reports')
                    }}
                    className="p-4 bg-primary-700 hover:bg-primary-600 rounded-xl transition-all text-left group"
                  >
                    <type.icon className="w-6 h-6 text-accent-blue mb-2 group-hover:scale-110 transition-transform" />
                    <h4 className="font-medium text-text-primary">{type.label}</h4>
                    <p className="text-xs text-text-muted mt-1">{type.description}</p>
                    <span className="text-xs text-accent-blue mt-2 inline-block">{type.time}</span>
                  </button>
                ))}
              </div>
            </Card.Body>
          </Card>
        </div>
      )}

      {/* Discovery Questions Section */}
      {activeSection === 'discovery' && (
        <div className="space-y-4">
          <Card className="bg-gradient-to-r from-blue-900/30 to-primary-800 border-blue-500/30">
            <Card.Body className="p-6">
              <div className="flex items-center gap-3">
                <MessageSquare className="w-6 h-6 text-blue-400" />
                <div>
                  <h3 className="text-lg font-semibold text-white">Întrebări de Descoperire Business</h3>
                  <p className="text-blue-200 text-sm">
                    Răspunde la aceste întrebări pentru a primi recomandări personalizate
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>

          {discoveryQuestions && Object.entries(discoveryQuestions).map(([category, questions]) => {
            const categoryInfo = categoryLabels[category] || { label: category, icon: Target }
            const CategoryIcon = categoryInfo.icon
            const isExpanded = expandedCategories[category]

            return (
              <Card key={category}>
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full p-4 flex items-center justify-between hover:bg-primary-700/50 transition-colors rounded-t-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-accent-blue/10 rounded-lg">
                      <CategoryIcon className="w-5 h-5 text-accent-blue" />
                    </div>
                    <div className="text-left">
                      <h4 className="font-medium text-text-primary">{categoryInfo.label}</h4>
                      <p className="text-xs text-text-muted">{questions.length} întrebări</p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-text-muted" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-text-muted" />
                  )}
                </button>
                
                {isExpanded && (
                  <Card.Body className="pt-0">
                    <div className="space-y-3 pl-12">
                      {questions.map((question, index) => (
                        <div key={index} className="p-3 bg-primary-700/50 rounded-lg">
                          <p className="text-text-primary text-sm">
                            <span className="text-accent-blue font-medium mr-2">{index + 1}.</span>
                            {question}
                          </p>
                        </div>
                      ))}
                    </div>
                  </Card.Body>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* Reports Section */}
      {activeSection === 'reports' && (
        <div className="space-y-6">
          {/* Generate New Report */}
          <Card>
            <Card.Header>
              <Card.Title className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-accent-yellow" />
                Generează Raport Nou
              </Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {reportTypes.map(type => (
                  <button
                    key={type.id}
                    onClick={() => setSelectedReportType(type.id)}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      selectedReportType === type.id
                        ? 'border-accent-blue bg-accent-blue/10'
                        : 'border-primary-600 hover:border-primary-500'
                    }`}
                  >
                    <type.icon className={`w-5 h-5 mb-2 ${
                      selectedReportType === type.id ? 'text-accent-blue' : 'text-text-muted'
                    }`} />
                    <h4 className="font-medium text-text-primary text-sm">{type.label}</h4>
                    <p className="text-xs text-text-muted mt-1">{type.time}</p>
                  </button>
                ))}
              </div>

              <Button
                onClick={() => generateReportMutation.mutate(selectedReportType)}
                disabled={generateReportMutation.isPending}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              >
                {generateReportMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generez raportul... (poate dura până la 2 minute)
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generează {reportTypes.find(t => t.id === selectedReportType)?.label}
                  </>
                )}
              </Button>

              {/* Generated Report Display */}
              {generateReportMutation.data && (
                <div className="mt-6 p-4 bg-primary-700 rounded-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium text-text-primary">Raport Generat</h4>
                    <Button variant="ghost" size="sm" icon={<Download className="w-4 h-4" />}>
                      Export
                    </Button>
                  </div>
                  <div className="prose prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap text-sm text-text-secondary bg-primary-800 p-4 rounded-lg overflow-auto max-h-96">
                      {generateReportMutation.data.report}
                    </pre>
                  </div>
                </div>
              )}
            </Card.Body>
          </Card>

          {/* Previous Reports */}
          <Card>
            <Card.Header>
              <Card.Title>Rapoarte Anterioare</Card.Title>
            </Card.Header>
            <Card.Body>
              {loadingReports ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-accent-blue" />
                </div>
              ) : previousReports && previousReports.length > 0 ? (
                <div className="space-y-3">
                  {previousReports.map((report, index) => (
                    <div
                      key={report._id || index}
                      className="flex items-center justify-between p-4 bg-primary-700 rounded-lg hover:bg-primary-600 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-accent-blue" />
                        <div>
                          <p className="font-medium text-text-primary">
                            {reportTypes.find(t => t.id === report.report_type)?.label || report.report_type}
                          </p>
                          <p className="text-xs text-text-muted">
                            {new Date(report.generated_at).toLocaleString('ro-RO')}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-text-muted">
                        <span>{report.metadata?.tokens_output || 0} tokens</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-text-muted py-8">
                  Nu ai generat încă niciun raport. Începe prin a genera primul raport!
                </p>
              )}
            </Card.Body>
          </Card>
        </div>
      )}

      {/* AI Chat Section */}
      {activeSection === 'chat' && (
        <Card className="h-[600px] flex flex-col">
          <Card.Header className="border-b border-primary-600">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <Card.Title>Consultant AI</Card.Title>
                <p className="text-xs text-text-muted">Powered by DeepSeek</p>
              </div>
            </div>
          </Card.Header>
          
          <Card.Body className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="p-4 bg-primary-700 rounded-full mb-4">
                  <Sparkles className="w-8 h-8 text-accent-yellow" />
                </div>
                <h3 className="text-lg font-medium text-text-primary mb-2">
                  Bună! Sunt consultantul tău AI.
                </h3>
                <p className="text-text-muted max-w-md mb-6">
                  Întreabă-mă orice despre afacerea ta, competiție, strategie SEO sau cum să-ți crești vizibilitatea online.
                </p>
                <div className="grid grid-cols-2 gap-2 max-w-lg">
                  {[
                    'Cum pot atrage mai mulți clienți?',
                    'Ce servicii noi ar trebui să adaug?',
                    'Cum mă diferențiez de competiție?',
                    'Ce keywords să prioritizez?'
                  ].map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setChatMessage(suggestion)}
                      className="p-3 text-left text-sm bg-primary-700 hover:bg-primary-600 rounded-lg text-text-secondary transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              chatHistory.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-4 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-accent-blue text-white rounded-br-md'
                        : 'bg-primary-700 text-text-primary rounded-bl-md'
                    }`}
                  >
                    {message.role === 'assistant' && (
                      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-primary-600">
                        <Brain className="w-4 h-4 text-purple-400" />
                        <span className="text-xs text-purple-400 font-medium">Consultant AI</span>
                      </div>
                    )}
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))
            )}
            
            {askQuestionMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-primary-700 p-4 rounded-2xl rounded-bl-md">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    <span className="text-sm text-text-muted">Analizez întrebarea...</span>
                  </div>
                </div>
              </div>
            )}
          </Card.Body>

          <div className="p-4 border-t border-primary-600">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Întreabă-mă orice despre afacerea ta..."
                className="flex-1 px-4 py-3 bg-primary-700 border border-primary-600 rounded-xl text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-blue"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!chatMessage.trim() || askQuestionMutation.isPending}
                className="px-6 bg-gradient-to-r from-purple-600 to-blue-600"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

export default AIConsultingTab

