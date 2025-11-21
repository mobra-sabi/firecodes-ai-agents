import { useState, useEffect } from 'react'
import { Network, TrendingUp, Target, MapPin, ExternalLink } from 'lucide-react'
import Card from '../../ui/Card'

/**
 * Hartă interactivă a concurenței
 * Vizualizare interactivă cu network graph
 */
const CompetitiveMap = ({ mapData, onNodeClick }) => {
  const [selectedNode, setSelectedNode] = useState(null)
  const [viewMode, setViewMode] = useState('network') // network, list, grid

  if (!mapData || mapData.length === 0) {
    return (
      <Card>
        <Card.Body className="text-center py-12">
          <MapPin className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-text-muted">No competitive map data yet. Execute strategy first.</p>
        </Card.Body>
      </Card>
    )
  }

  // Sortare după rank
  const sortedData = [...mapData].sort((a, b) => a.rank - b.rank)

  return (
    <div className="space-y-4">
      {/* View Mode Toggle */}
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => setViewMode('network')}
          className={`px-3 py-1 rounded text-sm ${
            viewMode === 'network'
              ? 'bg-purple-600 text-white'
              : 'bg-primary-700 text-text-muted hover:text-text-primary'
          }`}
        >
          <Network className="w-4 h-4 inline mr-1" />
          Network
        </button>
        <button
          onClick={() => setViewMode('list')}
          className={`px-3 py-1 rounded text-sm ${
            viewMode === 'list'
              ? 'bg-purple-600 text-white'
              : 'bg-primary-700 text-text-muted hover:text-text-primary'
          }`}
        >
          List
        </button>
        <button
          onClick={() => setViewMode('grid')}
          className={`px-3 py-1 rounded text-sm ${
            viewMode === 'grid'
              ? 'bg-purple-600 text-white'
              : 'bg-primary-700 text-text-muted hover:text-text-primary'
          }`}
        >
          Grid
        </button>
      </div>

      {/* Network View */}
      {viewMode === 'network' && (
        <div className="relative">
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center justify-center min-h-[400px] relative">
                {/* Central Node (Master Agent) */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
                  <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg border-4 border-primary-900">
                    <Target className="w-8 h-8 text-white" />
                  </div>
                  <div className="text-center mt-2">
                    <p className="text-xs font-semibold text-text-primary">Master</p>
                  </div>
                </div>

                {/* Competitor Nodes */}
                <div className="absolute inset-0">
                  {sortedData.slice(0, 12).map((competitor, index) => {
                    const angle = (index * 360) / Math.min(12, sortedData.length)
                    const radius = 150
                    const x = Math.cos((angle * Math.PI) / 180) * radius
                    const y = Math.sin((angle * Math.PI) / 180) * radius

                    return (
                      <div
                        key={index}
                        className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                        style={{
                          left: `calc(50% + ${x}px)`,
                          top: `calc(50% + ${y}px)`,
                        }}
                        onClick={() => {
                          setSelectedNode(competitor)
                          if (onNodeClick) onNodeClick(competitor)
                        }}
                      >
                        {/* Connection Line */}
                        <svg
                          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                          style={{
                            width: `${Math.sqrt(x * x + y * y)}px`,
                            height: '2px',
                            transform: `translate(-50%, -50%) rotate(${Math.atan2(y, x) * (180 / Math.PI)}deg)`,
                          }}
                        >
                          <line
                            x1="0"
                            y1="0"
                            x2="100%"
                            y2="0"
                            stroke="rgba(139, 92, 246, 0.3)"
                            strokeWidth="2"
                          />
                        </svg>

                        {/* Node */}
                        <div
                          className={`w-16 h-16 rounded-full flex items-center justify-center shadow-lg border-2 transition-all ${
                            selectedNode?.domain === competitor.domain
                              ? 'bg-purple-600 border-yellow-400 scale-110'
                              : 'bg-primary-700 border-primary-600 hover:scale-105'
                          }`}
                        >
                          <span className="text-xs font-bold text-text-primary">
                            #{competitor.rank}
                          </span>
                        </div>

                        {/* Label */}
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 w-32">
                          <p className="text-xs text-center text-text-primary truncate">
                            {competitor.domain}
                          </p>
                          <p className="text-xs text-center text-text-muted">
                            {competitor.relevance_score}%
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </Card.Body>
          </Card>
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <div className="space-y-3">
          {sortedData.map((competitor, index) => (
            <Card
              key={index}
              className={`cursor-pointer transition-all ${
                selectedNode?.domain === competitor.domain
                  ? 'border-purple-500 bg-purple-900/20'
                  : 'hover:border-primary-600'
              }`}
              onClick={() => {
                setSelectedNode(competitor)
                if (onNodeClick) onNodeClick(competitor)
              }}
            >
              <Card.Body className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center">
                      <span className="text-white font-bold">#{competitor.rank}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-text-primary">
                        {competitor.domain}
                      </h4>
                      <div className="flex items-center gap-4 mt-1 text-sm text-text-muted">
                        <span>Relevance: {competitor.relevance_score}%</span>
                        <span>•</span>
                        <span>Appearances: {competitor.appearances}</span>
                        <span>•</span>
                        <span>Best Position: #{competitor.best_position}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-green-600/20 text-green-400 rounded text-xs">
                      {competitor.keywords?.length || 0} keywords
                    </span>
                    <ExternalLink className="w-4 h-4 text-text-muted" />
                  </div>
                </div>
              </Card.Body>
            </Card>
          ))}
        </div>
      )}

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedData.map((competitor, index) => (
            <Card
              key={index}
              className={`cursor-pointer transition-all ${
                selectedNode?.domain === competitor.domain
                  ? 'border-purple-500 bg-purple-900/20'
                  : 'hover:border-primary-600'
              }`}
              onClick={() => {
                setSelectedNode(competitor)
                if (onNodeClick) onNodeClick(competitor)
              }}
            >
              <Card.Body className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold text-sm">#{competitor.rank}</span>
                  </div>
                  <span className="px-2 py-1 bg-green-600/20 text-green-400 rounded text-xs">
                    {competitor.relevance_score}%
                  </span>
                </div>
                <h4 className="text-lg font-semibold text-text-primary mb-2 truncate">
                  {competitor.domain}
                </h4>
                <div className="space-y-1 text-sm text-text-muted">
                  <div>Appearances: {competitor.appearances}</div>
                  <div>Best Position: #{competitor.best_position}</div>
                  <div>Keywords: {competitor.keywords?.length || 0}</div>
                </div>
              </Card.Body>
            </Card>
          ))}
        </div>
      )}

      {/* Selected Node Details */}
      {selectedNode && (
        <Card className="border-purple-500">
          <Card.Header>
            <Card.Title>Competitor Details</Card.Title>
          </Card.Header>
          <Card.Body>
            <div className="space-y-4">
              <div>
                <h4 className="text-xl font-semibold text-text-primary">{selectedNode.domain}</h4>
                <p className="text-sm text-text-muted">Rank #{selectedNode.rank}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-text-muted">Relevance Score</p>
                  <p className="text-lg font-semibold text-purple-400">
                    {selectedNode.relevance_score}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Appearances</p>
                  <p className="text-lg font-semibold text-text-primary">
                    {selectedNode.appearances}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Best Position</p>
                  <p className="text-lg font-semibold text-text-primary">
                    #{selectedNode.best_position}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-text-muted">Total Rank</p>
                  <p className="text-lg font-semibold text-text-primary">
                    {selectedNode.total_rank}
                  </p>
                </div>
              </div>
              {selectedNode.keywords && selectedNode.keywords.length > 0 && (
                <div>
                  <p className="text-sm text-text-muted mb-2">Keywords ({selectedNode.keywords.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedNode.keywords.map((kw, kwIndex) => (
                      <span
                        key={kwIndex}
                        className="px-2 py-1 bg-primary-700 rounded text-xs text-text-primary"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

export default CompetitiveMap

