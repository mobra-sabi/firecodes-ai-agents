import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Zap, Plus, X, Loader2, Network, TrendingUp, Target, Map, RefreshCw, Info } from 'lucide-react'
import api from '@/services/api'
import Button from '../../ui/Button'
import Card from '../../ui/Card'
import CompetitiveMap from './CompetitiveMap'

/**
 * Tab pentru Competitive Strategy:
 * - Import keywords din subdomains
 * - Gestionare keywords (add/remove)
 * - Executare strategie (SERP + Slave Agents)
 * - Hartă vizuală interactivă a concurenței
 */
const CompetitiveStrategyTab = ({ agentId }) => {
  const [selectedKeywords, setSelectedKeywords] = useState([])
  const [customKeyword, setCustomKeyword] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [strategyResult, setStrategyResult] = useState(null)
  const [executionProgress, setExecutionProgress] = useState(null)
  const [newSiteDomain, setNewSiteDomain] = useState('')
  const [isAnalyzingRelevance, setIsAnalyzingRelevance] = useState(false)
  const [relevanceProgress, setRelevanceProgress] = useState(null) // { analyzed, total, percentage }
  const [viewMode, setViewMode] = useState('list') // 'list' sau 'by-keyword'
  const [showMechanism, setShowMechanism] = useState(false)
  const [mechanismData, setMechanismData] = useState(null)
  const [relevanceThreshold, setRelevanceThreshold] = useState(70) // Threshold pentru relevanță (0-100)
  const [showFinalSelection, setShowFinalSelection] = useState(false) // Toggle pentru secțiunea finală
  const [showSelectedOnly, setShowSelectedOnly] = useState(false) // Toggle pentru a afișa doar site-urile selectate
  const [selectThreshold, setSelectThreshold] = useState(50) // Threshold pentru selectare automată (0-100)
  const [isCreatingAgents, setIsCreatingAgents] = useState(false) // Status pentru crearea agenților
  const [agentCreationProgress, setAgentCreationProgress] = useState(null) // Progres creare agenți

  // Fetch agent details pentru keywords
  const { data: agent } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}`)
      return response.data
    },
    enabled: !!agentId,
  })

  // Fetch competitive map
  const { data: competitiveMap, refetch: refetchMap } = useQuery({
    queryKey: ['competitive-map', agentId],
    queryFn: async () => {
      const response = await api.get(`/agents/${agentId}/competitive-map`)
      return response.data
    },
    enabled: !!agentId,
    refetchInterval: (isExecuting || isAnalyzingRelevance || isCreatingAgents) ? 1000 : 10000, // Refresh foarte des (1s) în timpul execuției/analizei/creării agenților
  })

  // Actualizează progresul relevanței când se schimbă competitiveMap
  useEffect(() => {
    if (competitiveMap?.relevance_analysis_progress) {
      setRelevanceProgress(competitiveMap.relevance_analysis_progress)
    }
    if (competitiveMap?.relevance_analysis_status === 'completed' || competitiveMap?.relevance_analysis_status === 'failed') {
      setIsAnalyzingRelevance(false)
      if (competitiveMap?.relevance_analysis_status === 'completed') {
        const recommended = competitiveMap.competitive_map?.filter(s => s.recommended).length || 0
        // Nu mai afișăm alert aici, doar actualizăm datele
      }
    } else if (competitiveMap?.relevance_analysis_status === 'running' || competitiveMap?.relevance_analysis_status === 'in_progress') {
      setIsAnalyzingRelevance(true)
    }
    
    // Actualizează progresul creării agenților
    if (competitiveMap?.agent_creation_progress) {
      setAgentCreationProgress(competitiveMap.agent_creation_progress)
    } else {
      setAgentCreationProgress(null)
    }
    
    const agentStatus = competitiveMap?.agent_creation_status || competitiveMap?.status || 'not_started'
    
    // Doar dacă statusul este explicit 'in_progress' sau 'running', procesul rulează
    if (agentStatus === 'in_progress' || agentStatus === 'running') {
      setIsCreatingAgents(true)
    } else {
      // Pentru 'completed', 'failed', 'stopped', 'not_started' sau undefined, procesul nu rulează
      setIsCreatingAgents(false)
      if (agentStatus === 'completed') {
        const createdCount = competitiveMap?.slave_agents_created || 0
        // Nu mai afișăm alert aici, doar actualizăm datele
      }
    }
  }, [competitiveMap])

  // Import keywords din subdomains
  useEffect(() => {
    if (agent && agent.subdomains) {
      const allKeywords = []
      agent.subdomains.forEach(subdomain => {
        if (subdomain.keywords && Array.isArray(subdomain.keywords)) {
          allKeywords.push(...subdomain.keywords)
        }
      })
      // Adaugă și overall_keywords
      if (agent.overall_keywords && Array.isArray(agent.overall_keywords)) {
        allKeywords.push(...agent.overall_keywords)
      }
      // Elimină duplicate
      const uniqueKeywords = [...new Set(allKeywords)]
      setSelectedKeywords(uniqueKeywords)
    }
  }, [agent])

  const addKeyword = (keyword) => {
    if (keyword.trim() && !selectedKeywords.includes(keyword.trim())) {
      setSelectedKeywords([...selectedKeywords, keyword.trim()])
      setCustomKeyword('')
    }
  }

  const removeKeyword = (keyword) => {
    setSelectedKeywords(selectedKeywords.filter(kw => kw !== keyword))
  }

  const executeStrategy = async () => {
    if (selectedKeywords.length === 0) {
      alert('Please select at least one keyword')
      return
    }

    setIsExecuting(true)
    setExecutionProgress({
      status: 'starting',
      message: 'Starting SERP search...',
      keywords_processed: 0,
      total_keywords: selectedKeywords.length
    })

    try {
      const response = await api.post(`/agents/${agentId}/execute-strategy`, {
        keywords: selectedKeywords,
        results_per_keyword: 20
      }, {
        timeout: 10000 // Timeout scurt - răspuns imediat
      })

      if (response.data.ok) {
        setExecutionProgress({
          status: 'running',
          message: 'Searching Google for sites... This will take a few minutes.',
          keywords_processed: 0,
          total_keywords: selectedKeywords.length,
          estimated_time_minutes: response.data.estimated_time_minutes
        })
        
        // Poll pentru progres - așteaptă să apară site-urile
        const progressInterval = setInterval(async () => {
          try {
            const mapResponse = await api.get(`/agents/${agentId}/competitive-map`)
            if (mapResponse.data && mapResponse.data.competitive_map) {
              const map = mapResponse.data.competitive_map
              if (map.length > 0) {
                // Site-uri găsite! Oprește polling și afișează rezultatele
                setExecutionProgress({
                  status: 'completed',
                  message: `✅ Search completed! Found ${map.length} sites. Review and select sites below.`,
                  keywords_processed: selectedKeywords.length,
                  total_keywords: selectedKeywords.length,
                  sites_found: mapResponse.data.sites_found || map.length,
                  slave_agents_created: 0  // Nu creăm agenți automat
                })
                setIsExecuting(false)
                clearInterval(progressInterval)
                refetchMap()
                
                // Scroll la secțiunea cu site-uri
                setTimeout(() => {
                  const sitesSection = document.getElementById('sites-found-section')
                  if (sitesSection) {
                    sitesSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }
                }, 500)
              } else {
                // Încă se caută, actualizează progresul
                setExecutionProgress(prev => ({
                  ...prev,
                  message: `Searching... (${selectedKeywords.length} keywords)`
                }))
              }
            }
          } catch (e) {
            // Continuă polling
          }
        }, 3000) // Poll la fiecare 3 secunde (mai des pentru feedback mai bun)

        // Timeout după 15 minute (doar căutare, mai rapid)
        setTimeout(() => {
          clearInterval(progressInterval)
          if (isExecuting) {
            setIsExecuting(false)
            setExecutionProgress(null)
            alert('Search is taking longer than expected. Check results manually or try again.')
            refetchMap()
          }
        }, 15 * 60 * 1000)
      } else {
        alert('Strategy failed: ' + (response.data.error || 'Unknown error'))
        setIsExecuting(false)
        setExecutionProgress(null)
      }
    } catch (error) {
      console.error('Strategy execution error:', error)
      alert('Error: ' + (error.response?.data?.detail || error.message || 'Unknown error'))
      setIsExecuting(false)
      setExecutionProgress(null)
    }
  }

  // Sortează site-urile după relevanță (cel mai mare score primul)
  // Dacă nu au relevanță, sortăm după rank
  // Folosește competitive_map dacă există, altfel folosește competitors din agent
  const rawMapData = competitiveMap?.competitive_map || []
  let mapData = Array.isArray(rawMapData) ? [...rawMapData].sort((a, b) => {
    const scoreA = a?.relevance_score || 0
    const scoreB = b?.relevance_score || 0
    if (scoreA !== scoreB) {
      return scoreB - scoreA // Descrescător după relevanță
    }
    return (a?.rank || 999) - (b?.rank || 999) // Apoi după rank
  }) : []
  
  // Dacă competitive_map este gol, folosește competitors din agent
  if (mapData.length === 0 && agent?.competitors && Array.isArray(agent.competitors)) {
    mapData = agent.competitors.map((domain, idx) => {
      const domainStr = typeof domain === 'string' ? domain : domain?.domain || domain
      return {
        domain: domainStr,
        url: `https://${domainStr}`,
        selected: false,
        has_agent: false,
        rank: idx + 1,
        relevance_score: 50, // Default score
        keyword_positions: []
      }
    })
  }
  
  const keywordSiteMapping = competitiveMap?.keyword_site_mapping || {}
  const keywordsUsed = competitiveMap?.keywords_used || []
  
  // Filtrează site-urile relevante în funcție de threshold
  const relevantSites = mapData.filter(site => (site.relevance_score || 0) >= relevanceThreshold)
  
  // Organizează site-urile relevante pe keyword cu ranking
  const relevantSitesByKeyword = {}
  relevantSites.forEach(site => {
    const keywordPositions = site.keyword_positions || []
    keywordPositions.forEach(kp => {
      const keyword = kp.keyword
      if (!relevantSitesByKeyword[keyword]) {
        relevantSitesByKeyword[keyword] = []
      }
      // Verifică dacă site-ul nu este deja adăugat pentru acest keyword
      if (!relevantSitesByKeyword[keyword].find(s => s.domain === site.domain)) {
        relevantSitesByKeyword[keyword].push({
          ...site,
          position: kp.position,
          keyword: keyword
        })
      }
    })
  })
  
  // Sortează site-urile în fiecare keyword după poziție (cel mai bun primul)
  Object.keys(relevantSitesByKeyword).forEach(keyword => {
    relevantSitesByKeyword[keyword].sort((a, b) => {
      // Mai întâi după poziție (cel mai bun primul)
      if (a.position !== b.position) {
        return a.position - b.position
      }
      // Apoi după relevanță
      return (b.relevance_score || 0) - (a.relevance_score || 0)
    })
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Competitive Strategy</h2>
          <p className="text-text-muted mt-1">
            Import keywords, execute SERP search, and discover competitors
          </p>
        </div>
      </div>

      {/* Strategy Overview */}
      <Card>
        <Card.Header>
          <Card.Title>Strategy Overview</Card.Title>
        </Card.Header>
        <Card.Body>
          <div className="space-y-3 text-sm text-text-muted">
            <div className="flex items-start gap-2">
              <Target className="w-4 h-4 mt-0.5 text-blue-400" />
              <span>For each keyword, perform Google search and extract top 20 results</span>
            </div>
            <div className="flex items-start gap-2">
              <Network className="w-4 h-4 mt-0.5 text-green-400" />
              <span>Transform each discovered site into a slave agent</span>
            </div>
            <div className="flex items-start gap-2">
              <TrendingUp className="w-4 h-4 mt-0.5 text-purple-400" />
              <span>Rank competitors by relevance and create competitive map</span>
            </div>
            <div className="flex items-start gap-2">
              <Map className="w-4 h-4 mt-0.5 text-yellow-400" />
              <span>Track positions over time to see evolution</span>
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* Keywords Management */}
      <Card>
        <Card.Header>
          <div className="flex items-center justify-between">
            <Card.Title>Keywords ({selectedKeywords.length})</Card.Title>
            <div className="flex gap-2">
              <input
                type="text"
                value={customKeyword}
                onChange={(e) => setCustomKeyword(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    addKeyword(customKeyword)
                  }
                }}
                placeholder="Add keyword..."
                className="input-custom"
              />
              <Button
                size="sm"
                onClick={() => addKeyword(customKeyword)}
                icon={<Plus className="w-4 h-4" />}
              >
                Add
              </Button>
            </div>
          </div>
        </Card.Header>
        <Card.Body>
          {selectedKeywords.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {selectedKeywords.map((keyword, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 bg-primary-700 rounded-full text-sm text-text-primary flex items-center gap-2"
                >
                  {keyword}
                  <button
                    onClick={() => removeKeyword(keyword)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-text-muted text-center py-4">
              No keywords selected. Import from subdomains or add manually.
            </p>
          )}
        </Card.Body>
      </Card>

      {/* Execute Strategy */}
      <Card>
        <Card.Body className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-text-primary">Execute Strategy</h3>
              <p className="text-sm text-text-muted mt-1">
                {selectedKeywords.length} keywords selected • Will search Google for sites (you'll review before creating agents)
              </p>
            </div>
            <Button
              onClick={executeStrategy}
              disabled={isExecuting || selectedKeywords.length === 0}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
              icon={isExecuting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            >
              {isExecuting ? 'Executing...' : 'Execute Strategy'}
            </Button>
          </div>

          {executionProgress && (
            <div className={`mt-4 p-4 rounded-lg border ${
              executionProgress.status === 'completed'
                ? 'bg-green-900/20 border-green-700'
                : executionProgress.status === 'running'
                ? 'bg-blue-900/20 border-blue-700'
                : 'bg-yellow-900/20 border-yellow-700'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {executionProgress.status === 'running' && (
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                )}
                {executionProgress.status === 'completed' && (
                  <Target className="w-4 h-4 text-green-400" />
                )}
                <h4 className={`font-semibold ${
                  executionProgress.status === 'completed'
                    ? 'text-green-400'
                    : executionProgress.status === 'running'
                    ? 'text-blue-400'
                    : 'text-yellow-400'
                }`}>
                  {executionProgress.message}
                </h4>
              </div>
              {executionProgress.status === 'running' && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-muted">Progress:</span>
                    <span className="text-text-primary">
                      {executionProgress.keywords_processed} / {executionProgress.total_keywords} keywords
                    </span>
                  </div>
                  <div className="w-full bg-primary-700 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{
                        width: `${(executionProgress.keywords_processed / executionProgress.total_keywords) * 100}%`
                      }}
                    />
                  </div>
                  {executionProgress.estimated_time_minutes && (
                    <p className="text-xs text-text-muted">
                      Estimated time: ~{executionProgress.estimated_time_minutes} minutes
                    </p>
                  )}
                </div>
              )}
              {executionProgress.status === 'completed' && (
                <div className="grid grid-cols-3 gap-4 text-sm mt-2">
                  <div>
                    <span className="text-text-muted">Keywords Processed:</span>
                    <span className="text-text-primary ml-2">{executionProgress.keywords_processed}</span>
                  </div>
                  <div>
                    <span className="text-text-muted">Sites Found:</span>
                    <span className="text-text-primary ml-2">{executionProgress.sites_found || 0}</span>
                  </div>
                  <div>
                    <span className="text-text-muted">Slave Agents:</span>
                    <span className="text-text-primary ml-2">{executionProgress.slave_agents_created || 0}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card.Body>
      </Card>

          {/* Relevance Analysis Progress Bar */}
          {isAnalyzingRelevance && relevanceProgress && (
            <Card>
              <Card.Body className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">
                      Analyzing Relevance...
                    </span>
                    <span className="text-sm text-text-muted">
                      {relevanceProgress.analyzed} / {relevanceProgress.total} sites ({relevanceProgress.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-primary-700 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-purple-600 h-full transition-all duration-500 ease-out"
                      style={{ width: `${relevanceProgress.percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-text-muted">
                    Sites are being analyzed and sorted by relevance in real-time...
                  </p>
                </div>
              </Card.Body>
            </Card>
          )}

          {/* Agent Creation Progress Bar */}
          {isCreatingAgents && agentCreationProgress && (
            <Card>
              <Card.Body className="p-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-primary">
                      Creating Agents...
                    </span>
                    <span className="text-sm text-text-muted">
                      {agentCreationProgress.completed} / {agentCreationProgress.total} agents ({agentCreationProgress.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-primary-700 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-green-600 h-full transition-all duration-500 ease-out"
                      style={{ width: `${agentCreationProgress.percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-text-muted">
                    Agents are being created in parallel using GPU acceleration. Each agent includes full scraping, chunks, and embeddings...
                  </p>
                  {competitiveMap?.slave_agents_created && (
                    <p className="text-xs text-green-400 mt-1">
                      ✓ {competitiveMap.slave_agents_created} agents created successfully
                    </p>
                  )}
                </div>
              </Card.Body>
            </Card>
          )}

          {/* Sites Found - Review and Select */}
      {((mapData && mapData.length > 0) || competitiveMap || (agent?.competitors && agent.competitors.length > 0)) && (
        <div id="sites-found-section" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold text-text-primary">
                Sites Found ({showSelectedOnly ? mapData.filter(s => s.selected).length : (mapData?.length || competitiveMap?.sites_found || agent?.competitor_count || agent?.competitors?.length || 0)})
                {showSelectedOnly && (
                  <span className="ml-2 text-sm text-blue-400">
                    (Showing selected only)
                  </span>
                )}
              </h3>
              <p className="text-sm text-text-muted mt-1">
                Review and select sites to create agents. Unselected sites will be ignored.
                {competitiveMap?.relevance_analyzed && (
                  <span className="ml-2 text-green-400">
                    ✓ Relevance analysis completed
                    {competitiveMap?.recommended_sites_count !== undefined && (
                      <span className="ml-2">
                        • {competitiveMap.recommended_sites_count} recommended sites
                        {competitiveMap?.high_relevance_sites_count !== undefined && competitiveMap.high_relevance_sites_count !== competitiveMap.recommended_sites_count && (
                          <span> • {competitiveMap.high_relevance_sites_count} with relevance ≥ 70%</span>
                        )}
                      </span>
                    )}
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="ghost"
                size="sm"
                icon={<Info className="w-4 h-4" />}
                onClick={async () => {
                  try {
                    const response = await api.get(`/agents/${agentId}/competitive-map/relevance-mechanism`)
                    setMechanismData(response.data)
                    setShowMechanism(true)
                  } catch (error) {
                    alert('Error: ' + (error.response?.data?.detail || error.message))
                  }
                }}
              >
                How It Works
              </Button>
              <div className="flex gap-1 bg-primary-700 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1 rounded text-sm ${
                    viewMode === 'list' ? 'bg-primary-600 text-text-primary' : 'text-text-muted'
                  }`}
                >
                  List
                </button>
                <button
                  onClick={() => setViewMode('by-keyword')}
                  className={`px-3 py-1 rounded text-sm ${
                    viewMode === 'by-keyword' ? 'bg-primary-600 text-text-primary' : 'text-text-muted'
                  }`}
                >
                  By Keyword
                </button>
              </div>
              <Button
                variant="ghost"
                size="sm"
                icon={<RefreshCw className="w-4 h-4" />}
                onClick={() => refetchMap()}
              >
                Refresh
              </Button>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 bg-primary-700 rounded-lg px-3 py-1.5">
                  <label className="text-xs text-text-muted">Select all >=</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={selectThreshold}
                    onChange={(e) => {
                      const value = Math.min(100, Math.max(0, Number(e.target.value) || 0))
                      setSelectThreshold(value)
                    }}
                    className="w-16 px-2 py-1 bg-primary-800 border border-primary-600 rounded text-text-primary text-sm focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-xs text-text-muted">%</span>
                </div>
                <Button
                  onClick={async () => {
                    const sitesToSelect = mapData.filter(site => (site.relevance_score || 0) >= selectThreshold && !site.selected && !site.has_agent)
                    if (sitesToSelect.length === 0) {
                      alert(`No sites to select. All sites with relevance >= ${selectThreshold}% are already selected or have agents.`)
                      return
                    }
                    
                    if (!confirm(`Select ${sitesToSelect.length} sites with relevance >= ${selectThreshold}%?`)) {
                      return
                    }
                    
                    try {
                      // Selectează toate site-urile cu relevanță >= selectThreshold într-un singur request
                      const response = await api.post(`/agents/${agentId}/competitive-map/select-multiple`, {
                        threshold: selectThreshold
                      })
                      if (response.data.ok) {
                        refetchMap()
                        setShowSelectedOnly(true) // Deschide lista cu selecția
                        alert(`Selected ${response.data.selected_count} sites with relevance >= ${selectThreshold}%`)
                      } else {
                        alert('Failed to select sites: ' + (response.data.error || 'Unknown error'))
                      }
                    } catch (error) {
                      alert('Error: ' + (error.response?.data?.detail || error.message))
                    }
                  }}
                  className="bg-blue-600 hover:bg-blue-700"
                  icon={<Target className="w-4 h-4" />}
                >
                  Select
                </Button>
              </div>
              <Button
                onClick={async () => {
                  const sitesToAnalyze = mapData && mapData.length > 0 ? mapData.length : 0
                  if (sitesToAnalyze === 0) {
                    alert('No sites to analyze. Add sites manually or execute the strategy to discover sites.')
                    return
                  }
                  setIsAnalyzingRelevance(true)
                  setRelevanceProgress({ analyzed: 0, total: sitesToAnalyze, percentage: 0 })
                  try {
                    const response = await api.post(`/agents/${agentId}/competitive-map/analyze-relevance`, {}, {
                      timeout: 10000  // Timeout scurt - răspuns imediat
                    })
                    if (response.data.ok) {
                      // Nu mai afișăm alert, doar pornim polling-ul
                      // Polling-ul se face automat prin refetchInterval din useQuery
                      refetchMap()
                    } else {
                      setIsAnalyzingRelevance(false)
                      setRelevanceProgress(null)
                      alert('Failed to start analysis: ' + (response.data.error || 'Unknown error'))
                    }
                  } catch (error) {
                    setIsAnalyzingRelevance(false)
                    setRelevanceProgress(null)
                    alert('Error: ' + (error.response?.data?.detail || error.message))
                  }
                }}
                disabled={isAnalyzingRelevance || !mapData || mapData.length === 0}
                className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                icon={isAnalyzingRelevance ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
                title={
                  isAnalyzingRelevance 
                    ? 'Analysis in progress...'
                    : !mapData || mapData.length === 0
                    ? 'Add sites manually or execute strategy to discover sites, then analyze their relevance.'
                    : `Analyze relevance of ${mapData.length} sites`
                }
              >
                {isAnalyzingRelevance 
                  ? (relevanceProgress 
                      ? `Analyzing... ${relevanceProgress.analyzed}/${relevanceProgress.total} (${relevanceProgress.percentage}%)`
                      : 'Analyzing...')
                  : 'Analyze Relevance'}
              </Button>
              {/* Buton pentru selectare automată site-uri recomandate */}
              {competitiveMap?.relevance_analyzed && competitiveMap?.recommended_sites_count > 0 && (
                <Button
                  onClick={async () => {
                    const recommendedSites = mapData.filter(s => s.recommended && !s.has_agent)
                    if (recommendedSites.length === 0) {
                      alert('All recommended sites already have agents or are already selected.')
                      return
                    }
                    
                    if (!confirm(`Select ${recommendedSites.length} recommended sites?`)) {
                      return
                    }
                    
                    try {
                      // Selectează toate site-urile recomandate
                      const response = await api.post(`/agents/${agentId}/competitive-map/select-recommended`)
                      if (response.data.ok) {
                        refetchMap()
                        alert(`Selected ${response.data.selected_count} recommended sites. You can now create agents.`)
                      } else {
                        alert('Failed to select recommended sites: ' + (response.data.error || 'Unknown error'))
                      }
                    } catch (error) {
                      alert('Error: ' + (error.response?.data?.detail || error.message))
                    }
                  }}
                  className="bg-yellow-600 hover:bg-yellow-700"
                  icon={<Target className="w-4 h-4" />}
                  title={`Select all ${competitiveMap?.recommended_sites_count || 0} recommended sites`}
                >
                  Select Recommended ({competitiveMap?.recommended_sites_count || 0})
                </Button>
              )}
              <Button
                onClick={async () => {
                  const selectedCount = mapData.filter(s => s.selected).length
                  if (selectedCount === 0) {
                    // Dacă nu sunt site-uri selectate, oferă opțiunea de a crea direct pentru recomandate
                    if (competitiveMap?.relevance_analyzed && competitiveMap?.recommended_sites_count > 0) {
                      const recommendedCount = competitiveMap.recommended_sites_count
                      if (confirm(`No sites selected. Would you like to create agents for all ${recommendedCount} recommended sites directly?`)) {
                        try {
                          setIsCreatingAgents(true)
                          setAgentCreationProgress({ completed: 0, total: recommendedCount, percentage: 0 })
                          // Selectează și creează direct pentru recomandate
                          const selectResponse = await api.post(`/agents/${agentId}/competitive-map/select-recommended`)
                          if (selectResponse.data.ok) {
                            await refetchMap()
                            // Apoi creează agenții
                            const createResponse = await api.post(`/agents/${agentId}/competitive-map/create-agents`)
                            if (createResponse.data.ok) {
                              refetchMap()
                            } else {
                              setIsCreatingAgents(false)
                              setAgentCreationProgress(null)
                              alert('Failed to start agent creation: ' + (createResponse.data.error || 'Unknown error'))
                            }
                          } else {
                            setIsCreatingAgents(false)
                            setAgentCreationProgress(null)
                            alert('Failed to select recommended sites: ' + (selectResponse.data.error || 'Unknown error'))
                          }
                        } catch (error) {
                          setIsCreatingAgents(false)
                          setAgentCreationProgress(null)
                          alert('Error: ' + (error.response?.data?.detail || error.message))
                        }
                      }
                      return
                    }
                    alert('Please select at least one site to create agents')
                    return
                  }
                  
                  if (!confirm(`Create agents for ${selectedCount} selected sites? This will use GPU acceleration for parallel processing.`)) {
                    return
                  }
                  
                  try {
                    setIsCreatingAgents(true)
                    setAgentCreationProgress({ completed: 0, total: selectedCount, percentage: 0 })
                    const response = await api.post(`/agents/${agentId}/competitive-map/create-agents`)
                    if (response.data.ok) {
                      // Nu mai afișăm alert, doar pornim polling-ul
                      // Polling-ul se face automat prin refetchInterval din useQuery
                      refetchMap()
                    } else {
                      setIsCreatingAgents(false)
                      setAgentCreationProgress(null)
                      alert('Failed to start agent creation: ' + (response.data.error || 'Unknown error'))
                    }
                  } catch (error) {
                    setIsCreatingAgents(false)
                    setAgentCreationProgress(null)
                    alert('Error: ' + (error.response?.data?.detail || error.message))
                  }
                }}
                disabled={isCreatingAgents || !mapData || (mapData.filter(s => s.selected).length === 0 && (!competitiveMap?.relevance_analyzed || !competitiveMap?.recommended_sites_count))}
                className="bg-green-600 hover:bg-green-700 disabled:opacity-50"
                icon={isCreatingAgents ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                title={
                  mapData.filter(s => s.selected).length === 0 && competitiveMap?.relevance_analyzed && competitiveMap?.recommended_sites_count > 0
                    ? `Click to create agents for all ${competitiveMap.recommended_sites_count} recommended sites`
                    : undefined
                }
              >
                {isCreatingAgents 
                  ? (agentCreationProgress 
                      ? `Creating... ${agentCreationProgress.completed}/${agentCreationProgress.total} (${agentCreationProgress.percentage}%)`
                      : 'Creating Agents...')
                  : mapData.filter(s => s.selected).length === 0 && competitiveMap?.relevance_analyzed && competitiveMap?.recommended_sites_count > 0
                    ? `Create Agents for Recommended (${competitiveMap.recommended_sites_count})`
                    : `Create Agents for Selected (${mapData.filter(s => s.selected).length})`}
              </Button>
              {isCreatingAgents && (
                <Button
                  onClick={async () => {
                    if (!confirm('Stop agent creation? Progress will be saved.')) {
                      return
                    }
                    try {
                      const response = await api.post(`/agents/${agentId}/competitive-map/stop-creation`)
                      if (response.data.ok) {
                        setIsCreatingAgents(false)
                        setAgentCreationProgress(null)
                        refetchMap()
                        alert('Agent creation stopped. You can restart it now.')
                      } else {
                        alert('Error stopping creation: ' + (response.data.error || 'Unknown error'))
                      }
                    } catch (error) {
                      alert('Error: ' + (error.response?.data?.detail || error.message))
                    }
                  }}
                  className="bg-red-600 hover:bg-red-700 text-white font-semibold px-3 py-2"
                  icon={<X className="w-4 h-4" />}
                  title="Stop agent creation"
                  size="sm"
                >
                  Stop
                </Button>
              )}
            </div>
          </div>
          
          {/* Add Site Manually */}
          <Card>
            <Card.Body className="p-4">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newSiteDomain}
                  onChange={(e) => setNewSiteDomain(e.target.value)}
                  onKeyPress={async (e) => {
                    if (e.key === 'Enter' && newSiteDomain.trim()) {
                      try {
                        const domain = newSiteDomain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '')
                        await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(domain)}`, {
                          action: 'add',
                          url: `https://${domain}`,
                          keywords: [],
                          relevance_score: 50
                        })
                        setNewSiteDomain('')
                        refetchMap()
                      } catch (error) {
                        alert('Error: ' + (error.response?.data?.detail || error.message))
                      }
                    }
                  }}
                  placeholder="Add site domain manually (e.g., example.com)"
                  className="input-custom flex-1"
                />
                <Button
                  size="sm"
                  onClick={async () => {
                    if (!newSiteDomain.trim()) return
                    try {
                      const domain = newSiteDomain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '')
                      await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(domain)}`, {
                        action: 'add',
                        url: `https://${domain}`,
                        keywords: [],
                        relevance_score: 50
                      })
                      setNewSiteDomain('')
                      refetchMap()
                    } catch (error) {
                      alert('Error: ' + (error.response?.data?.detail || error.message))
                    }
                  }}
                  icon={<Plus className="w-4 h-4" />}
                >
                  Add Site
                </Button>
              </div>
            </Card.Body>
          </Card>
          
          {/* Toggle pentru a afișa doar site-urile selectate */}
          {competitiveMap?.relevance_analyzed && (
            <div className="flex items-center justify-end gap-2 mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSelectedOnly(!showSelectedOnly)}
                className={showSelectedOnly ? 'bg-blue-900/20 border border-blue-700' : ''}
                icon={<Target className="w-4 h-4" />}
              >
                {showSelectedOnly ? 'Show All Sites' : 'Show Selected Only'}
              </Button>
            </div>
          )}

          {/* Sites List with Selection */}
          {viewMode === 'list' ? (
            <Card>
              <Card.Body className="p-4">
                {(showSelectedOnly ? mapData.filter(s => s.selected) : mapData).length > 0 ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {(showSelectedOnly ? mapData.filter(s => s.selected) : mapData).map((site, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border flex items-center justify-between ${
                        site.selected
                          ? 'bg-blue-900/20 border-blue-700'
                          : 'bg-primary-700 border-primary-600'
                      } ${site.has_agent ? 'opacity-75' : ''}`}
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <input
                          type="checkbox"
                          checked={site.selected || false}
                          onChange={async () => {
                            try {
                              await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(site.domain)}`, {
                                action: 'toggle_selection'
                              })
                              refetchMap()
                            } catch (error) {
                              alert('Error: ' + (error.response?.data?.detail || error.message))
                            }
                          }}
                          disabled={site.has_agent}
                          className="w-4 h-4"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-text-primary">{site.domain}</span>
                            {site.has_agent && (
                              <span className="px-2 py-0.5 bg-green-900/20 text-green-400 text-xs rounded">
                                Agent Created
                              </span>
                            )}
                            {site.recommended && (
                              <span className="px-2 py-0.5 bg-purple-900/20 text-purple-400 text-xs rounded">
                                Recommended
                              </span>
                            )}
                            <span className="text-xs text-text-muted">Rank: {site.rank}</span>
                            {site.relevance_score !== undefined && (
                              <span className="text-xs text-text-muted">
                                Relevance: {site.relevance_score}%
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-text-muted mt-1">
                            Appearances: {site.appearances} • Best Position: {site.best_position} • 
                            Keywords: {site.keywords?.length || 0}
                            {site.reasoning && (
                              <div className="mt-1 text-xs italic">{site.reasoning}</div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={async () => {
                            if (confirm(`Remove ${site.domain} from list?`)) {
                              try {
                                await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(site.domain)}`, {
                                  action: 'remove'
                                })
                                refetchMap()
                              } catch (error) {
                                alert('Error: ' + (error.response?.data?.detail || error.message))
                              }
                            }
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-text-muted">No sites found yet. Execute the strategy to discover competitor sites.</p>
                  </div>
                )}
              </Card.Body>
            </Card>
          ) : (
            <Card>
              <Card.Body className="p-4">
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {Object.entries(keywordSiteMapping).map(([keyword, sites]) => (
                    <div key={keyword} className="border-b border-primary-600 pb-4 last:border-0">
                      <h4 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
                        <span className="text-accent-blue">Keyword:</span>
                        <span>{keyword}</span>
                        <span className="text-xs text-text-muted">({sites.length} sites)</span>
                      </h4>
                      <div className="space-y-2 ml-4">
                        {sites
                          .sort((a, b) => a.position - b.position)
                          .map((siteInfo, idx) => {
                            const site = mapData.find(s => s.domain === siteInfo.domain)
                            return (
                              <div
                                key={idx}
                                className={`p-2 rounded border flex items-center justify-between ${
                                  site?.selected
                                    ? 'bg-blue-900/20 border-blue-700'
                                    : 'bg-primary-800 border-primary-700'
                                }`}
                              >
                                <div className="flex items-center gap-3 flex-1">
                                  <input
                                    type="checkbox"
                                    checked={site?.selected || false}
                                    onChange={async () => {
                                      try {
                                        await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(siteInfo.domain)}`, {
                                          action: 'toggle_selection'
                                        })
                                        refetchMap()
                                      } catch (error) {
                                        alert('Error: ' + (error.response?.data?.detail || error.message))
                                      }
                                    }}
                                    disabled={site?.has_agent}
                                    className="w-4 h-4"
                                  />
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-text-muted">Position:</span>
                                    <span className="font-semibold text-accent-yellow">{siteInfo.position}</span>
                                  </div>
                                  <span className="font-medium text-text-primary">{siteInfo.domain}</span>
                                  {site?.relevance_score !== undefined && (
                                    <span className="text-xs text-text-muted">
                                      Relevance: {site.relevance_score}%
                                    </span>
                                  )}
                                  {site?.recommended && (
                                    <span className="px-2 py-0.5 bg-purple-900/20 text-purple-400 text-xs rounded">
                                      Recommended
                                    </span>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}
          
          {/* Competitive Map Visualization */}
          <CompetitiveMap
            mapData={mapData.filter(s => s.selected || s.has_agent)}
            onNodeClick={(competitor) => {
              console.log('Selected competitor:', competitor)
            }}
          />
        </div>
      )}

      {/* Mechanism Explanation Modal */}
      {showMechanism && mechanismData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowMechanism(false)}>
          <div className="bg-primary-800 rounded-lg p-6 max-w-4xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-text-primary">Mecanismul de Selecție a Site-urilor Relevante</h2>
              <button
                onClick={() => setShowMechanism(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            {mechanismData.mechanism && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-text-primary mb-2">Procesul de Analiză</h3>
                  <div className="space-y-4">
                    {mechanismData.mechanism.steps.map((step, idx) => (
                      <Card key={idx}>
                        <Card.Body>
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center text-white font-bold">
                              {step.step}
                            </div>
                            <div className="flex-1">
                              <h4 className="font-semibold text-text-primary mb-1">{step.name}</h4>
                              <p className="text-sm text-text-muted mb-2">{step.description}</p>
                              {step.criteria && (
                                <div className="mt-3 space-y-2">
                                  {Object.entries(step.criteria).map(([key, value]) => (
                                    <div key={key} className="text-sm">
                                      <span className="font-medium text-text-primary">{key}:</span>
                                      <span className="text-text-muted ml-2">({value.weight}) {value.description}</span>
                                      {value.example && (
                                        <div className="text-xs text-text-muted mt-1 ml-4">Ex: {value.example}</div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                              {step.scoring && (
                                <div className="mt-3 space-y-1">
                                  {Object.entries(step.scoring).map(([range, desc]) => (
                                    <div key={range} className="text-sm">
                                      <span className="font-medium text-text-primary">{range}:</span>
                                      <span className="text-text-muted ml-2">{desc}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                              {step.conditions && (
                                <div className="mt-3">
                                  <div className="text-sm">
                                    <span className="font-medium text-text-primary">Condiții necesare:</span>
                                    <ul className="list-disc list-inside text-text-muted mt-1">
                                      {step.conditions.required.map((cond, i) => (
                                        <li key={i}>{cond}</li>
                                      ))}
                                    </ul>
                                  </div>
                                  {step.conditions.optional && (
                                    <div className="text-sm mt-2">
                                      <span className="font-medium text-text-primary">Condiții opționale:</span>
                                      <ul className="list-disc list-inside text-text-muted mt-1">
                                        {step.conditions.optional.map((cond, i) => (
                                          <li key={i}>{cond}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </Card.Body>
                      </Card>
                    ))}
                  </div>
                </div>

                {mechanismData.mechanism.tools_used && (
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Unelte Folosite</h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(mechanismData.mechanism.tools_used).map(([tool, info]) => (
                        <Card key={tool}>
                          <Card.Body>
                            <h4 className="font-semibold text-text-primary mb-2">{tool === 'deepseek' ? 'DeepSeek' : 'Qwen (GPU)'}</h4>
                            <div className="text-sm space-y-1">
                              <div><span className="text-text-muted">Scop:</span> <span className="text-text-primary">{info.purpose}</span></div>
                              <div><span className="text-text-muted">Viteză:</span> <span className="text-text-primary">{info.speed}</span></div>
                              <div><span className="text-text-muted">Precizie:</span> <span className="text-text-primary">{info.accuracy}</span></div>
                              {info.batch_size && (
                                <div><span className="text-text-muted">Batch size:</span> <span className="text-text-primary">{info.batch_size} site-uri</span></div>
                              )}
                              {info.parallel_batches && (
                                <div><span className="text-text-muted">Batch-uri paralele:</span> <span className="text-text-primary">{info.parallel_batches}</span></div>
                              )}
                            </div>
                          </Card.Body>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {mechanismData.current_status && (
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Status Actual</h3>
                    <Card>
                      <Card.Body>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-text-muted">Site-uri găsite:</span>
                            <span className="text-text-primary ml-2 font-semibold">{mechanismData.current_status.sites_found}</span>
                          </div>
                          <div>
                            <span className="text-text-muted">Site-uri analizate:</span>
                            <span className="text-text-primary ml-2 font-semibold">{mechanismData.current_status.sites_analyzed}</span>
                          </div>
                          <div>
                            <span className="text-text-muted">Site-uri recomandate:</span>
                            <span className="text-text-primary ml-2 font-semibold">{mechanismData.current_status.recommended_sites}</span>
                          </div>
                          {mechanismData.current_status.statistics && (
                            <>
                              <div>
                                <span className="text-text-muted">Scor mediu relevanță:</span>
                                <span className="text-text-primary ml-2 font-semibold">{mechanismData.current_status.statistics.avg_relevance_score.toFixed(1)}%</span>
                              </div>
                              <div>
                                <span className="text-text-muted">Scor minim:</span>
                                <span className="text-text-primary ml-2">{mechanismData.current_status.statistics.min_relevance_score}%</span>
                              </div>
                              <div>
                                <span className="text-text-muted">Scor maxim:</span>
                                <span className="text-text-primary ml-2">{mechanismData.current_status.statistics.max_relevance_score}%</span>
                              </div>
                            </>
                          )}
                        </div>
                        {mechanismData.current_status.statistics?.sites_by_score_range && (
                          <div className="mt-4 pt-4 border-t border-primary-600">
                            <h4 className="font-semibold text-text-primary mb-2">Distribuție după scor:</h4>
                            <div className="grid grid-cols-4 gap-2 text-sm">
                              {Object.entries(mechanismData.current_status.statistics.sites_by_score_range).map(([range, count]) => (
                                <div key={range} className="text-center">
                                  <div className="text-text-primary font-semibold">{count}</div>
                                  <div className="text-text-muted text-xs">{range}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </Card.Body>
                    </Card>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Final Selection - Relevant Sites */}
      {competitiveMap?.relevance_analyzed && mapData.length > 0 && (
        <Card>
          <Card.Header>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-text-primary">
                  Final Selection - Relevant Sites
                </h3>
                <p className="text-sm text-text-muted mt-1">
                  Select relevant sites based on relevance threshold and create agents
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowFinalSelection(!showFinalSelection)}
                icon={showFinalSelection ? <X className="w-4 h-4" /> : <Target className="w-4 h-4" />}
              >
                {showFinalSelection ? 'Hide' : 'Show'} Final Selection
              </Button>
            </div>
          </Card.Header>
          {showFinalSelection && (
            <Card.Body className="p-6 space-y-6">
              {/* Relevance Threshold Control */}
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-text-primary">
                    Relevance Threshold
                  </label>
                  <span className="text-xs text-text-muted">
                    {relevantSites.length} sites match this threshold
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={relevanceThreshold}
                    onChange={(e) => setRelevanceThreshold(Number(e.target.value))}
                    className="flex-1 h-2 bg-primary-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
                  />
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={relevanceThreshold}
                      onChange={(e) => {
                        const value = Math.min(100, Math.max(0, Number(e.target.value) || 0))
                        setRelevanceThreshold(value)
                      }}
                      className="w-20 px-3 py-2 bg-primary-700 border border-primary-600 rounded-lg text-text-primary text-sm focus:outline-none focus:border-purple-500"
                    />
                    <span className="text-sm text-text-muted">%</span>
                    <Button
                      onClick={() => {
                        // Lista se regenerează automat, dar facem refresh pentru a actualiza datele
                        refetchMap()
                      }}
                      size="sm"
                      className="bg-purple-600 hover:bg-purple-700"
                      icon={<Target className="w-4 h-4" />}
                    >
                      Generate List
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between text-xs text-text-muted">
                  <span>0%</span>
                  <span>25%</span>
                  <span>50%</span>
                  <span>75%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Relevant Sites by Keyword */}
              {Object.keys(relevantSitesByKeyword).length > 0 ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-semibold text-text-primary">
                      Relevant Sites by Keyword ({Object.keys(relevantSitesByKeyword).length} keywords)
                    </h4>
                    <Button
                      onClick={async () => {
                        const selectedCount = relevantSites.filter(s => s.selected).length
                        if (selectedCount === 0) {
                          alert('Please select at least one site to create agents')
                          return
                        }
                        
                        if (!confirm(`Create agents for ${selectedCount} selected relevant sites?`)) {
                          return
                        }
                        
                        try {
                          const response = await api.post(`/agents/${agentId}/competitive-map/create-agents`)
                          if (response.data.ok) {
                            alert(`Agent creation started for ${selectedCount} sites. This will take a few minutes.`)
                            refetchMap()
                          }
                        } catch (error) {
                          alert('Error: ' + (error.response?.data?.detail || error.message))
                        }
                      }}
                      className="bg-green-600 hover:bg-green-700"
                      icon={<Zap className="w-4 h-4" />}
                    >
                      Create Agents for Selected ({relevantSites.filter(s => s.selected).length})
                    </Button>
                  </div>

                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {Object.entries(relevantSitesByKeyword)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([keyword, sites]) => (
                        <Card key={keyword}>
                          <Card.Body className="p-4">
                            <div className="flex items-center justify-between mb-3">
                              <h5 className="font-semibold text-text-primary">
                                {keyword} ({sites.length} sites)
                              </h5>
                              <span className="text-xs text-text-muted">
                                Ranked by position
                              </span>
                            </div>
                            <div className="space-y-2">
                              {sites.map((site, idx) => (
                                <div
                                  key={`${keyword}-${site.domain}`}
                                  className={`p-3 rounded-lg border flex items-center justify-between ${
                                    site.selected
                                      ? 'bg-blue-900/20 border-blue-700'
                                      : 'bg-primary-700 border-primary-600'
                                  }`}
                                >
                                  <div className="flex items-center gap-3 flex-1">
                                    <input
                                      type="checkbox"
                                      checked={site.selected || false}
                                      onChange={async () => {
                                        try {
                                          await api.put(`/agents/${agentId}/competitive-map/sites/${encodeURIComponent(site.domain)}`, {
                                            action: 'toggle_selection'
                                          })
                                          refetchMap()
                                        } catch (error) {
                                          alert('Error: ' + (error.response?.data?.detail || error.message))
                                        }
                                      }}
                                      disabled={site.has_agent}
                                      className="w-4 h-4"
                                    />
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2">
                                        <span className="px-2 py-0.5 bg-purple-900/20 text-purple-400 text-xs rounded">
                                          Position: {site.position}
                                        </span>
                                        <span className="font-semibold text-text-primary">{site.domain}</span>
                                        {site.recommended && (
                                          <span className="px-2 py-0.5 bg-purple-900/20 text-purple-400 text-xs rounded">
                                            Recommended
                                          </span>
                                        )}
                                        <span className="text-xs text-text-muted">
                                          Relevance: {site.relevance_score}%
                                        </span>
                                        {site.has_agent && (
                                          <span className="px-2 py-0.5 bg-green-900/20 text-green-400 text-xs rounded">
                                            Agent Created
                                          </span>
                                        )}
                                      </div>
                                      {site.reasoning && (
                                        <div className="text-xs text-text-muted mt-1 italic">
                                          {site.reasoning}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </Card.Body>
                        </Card>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-text-muted">
                    No sites match the relevance threshold of {relevanceThreshold}%. 
                    Try lowering the threshold.
                  </p>
                </div>
              )}
            </Card.Body>
          )}
        </Card>
      )}
    </div>
  )
}

export default CompetitiveStrategyTab

