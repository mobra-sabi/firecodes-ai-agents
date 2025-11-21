import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { getGraph, updateGraph, getSimilarSlaves } from '@/api/graph'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { Network, RefreshCw, Users, TrendingUp, Target } from 'lucide-react'

const OrganizationGraph = () => {
  const { id } = useParams()
  const [agentId, setAgentId] = useState(id || '')
  
  const queryClient = useQueryClient()
  
  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graph', agentId],
    queryFn: () => getGraph(agentId),
    enabled: !!agentId,
    refetchInterval: 30000
  })
  
  const { data: similarData } = useQuery({
    queryKey: ['similarSlaves', agentId],
    queryFn: () => getSimilarSlaves(agentId, 10),
    enabled: !!agentId
  })
  
  const updateGraphMutation = useMutation({
    mutationFn: () => updateGraph(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries(['graph'])
      queryClient.invalidateQueries(['similarSlaves'])
    }
  })
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Organization Graph</h1>
          <p className="text-text-muted mt-1">Master-slave relationships and similarities</p>
        </div>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Enter Agent ID..."
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          />
          <Button
            onClick={() => updateGraphMutation.mutate()}
            disabled={!agentId || updateGraphMutation.isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${updateGraphMutation.isLoading ? 'animate-spin' : ''}`} />
            Update Graph
          </Button>
        </div>
      </div>
      
      {!agentId ? (
        <Card>
          <Card.Body className="p-12 text-center">
            <Network className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-text-muted">Enter an Agent ID to view the organization graph</p>
          </Card.Body>
        </Card>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
        </div>
      ) : graphData ? (
        <>
          {/* Graph Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <Card.Body className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-muted">Total Nodes</h3>
                  <Network className="w-5 h-5 text-primary-400" />
                </div>
                <p className="text-3xl font-bold text-text-primary mt-2">
                  {graphData.nodes?.length || 0}
                </p>
              </Card.Body>
            </Card>
            <Card>
              <Card.Body className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-muted">Total Edges</h3>
                  <Target className="w-5 h-5 text-blue-400" />
                </div>
                <p className="text-3xl font-bold text-text-primary mt-2">
                  {graphData.edges?.length || 0}
                </p>
              </Card.Body>
            </Card>
            <Card>
              <Card.Body className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-muted">Slave Agents</h3>
                  <Users className="w-5 h-5 text-green-400" />
                </div>
                <p className="text-3xl font-bold text-text-primary mt-2">
                  {graphData.total_slaves || 0}
                </p>
              </Card.Body>
            </Card>
            <Card>
              <Card.Body className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-muted">Avg Similarity</h3>
                  <TrendingUp className="w-5 h-5 text-yellow-400" />
                </div>
                <p className="text-3xl font-bold text-text-primary mt-2">
                  {graphData.avg_similarity ? (graphData.avg_similarity * 100).toFixed(1) : 0}%
                </p>
              </Card.Body>
            </Card>
          </div>
          
          {/* Graph Visualization Placeholder */}
          <Card>
            <Card.Header>
              <Card.Title>Graph Visualization</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="bg-gray-800 rounded-lg p-8 min-h-[400px] flex items-center justify-center">
                <div className="text-center">
                  <Network className="w-24 h-24 text-gray-600 mx-auto mb-4" />
                  <p className="text-text-muted mb-2">Graph visualization coming soon</p>
                  <p className="text-sm text-gray-600">
                    {graphData.nodes?.length || 0} nodes, {graphData.edges?.length || 0} edges
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>
          
          {/* Similar Slaves */}
          {similarData && similarData.similar_slaves?.length > 0 && (
            <Card>
              <Card.Header>
                <Card.Title>Top Similar Slaves</Card.Title>
              </Card.Header>
              <Card.Body className="p-0">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-700">
                    <thead className="bg-gray-800">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Domain</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Similarity</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Type</th>
                      </tr>
                    </thead>
                    <tbody className="bg-gray-900 divide-y divide-gray-800">
                      {similarData.similar_slaves.map((slave, index) => (
                        <tr key={index}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-text-primary">
                            {slave.domain}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-900 text-primary-300">
                              {(slave.similarity_score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                            {slave.relationship_type}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card.Body>
            </Card>
          )}
        </>
      ) : null}
    </div>
  )
}

export default OrganizationGraph

