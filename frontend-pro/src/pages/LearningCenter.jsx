import { useState, useEffect } from 'react'
import { Brain, Play, Pause, BookOpen, TrendingUp, CheckCircle, AlertCircle, FileText } from 'lucide-react'
import { getLearningStats, getTrainingStatus, processLearningData, buildJsonl } from '../services/workflows'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'

/**
 * Learning Center - Continuous Learning & Training Management
 */
const LearningCenter = () => {
  const [stats, setStats] = useState(null)
  const [trainingStatus, setTrainingStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [building, setBuilding] = useState(false)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 15000) // Refresh every 15s
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [statsData, trainingData] = await Promise.all([
        getLearningStats(),
        getTrainingStatus(),
      ])
      setStats(statsData)
      setTrainingStatus(trainingData)
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch learning data:', err)
      setLoading(false)
    }
  }

  const handleProcessData = async () => {
    try {
      setProcessing(true)
      await processLearningData()
      setTimeout(fetchData, 3000) // Refresh after processing
    } catch (err) {
      console.error('Failed to process data:', err)
    } finally {
      setProcessing(false)
    }
  }

  const handleBuildJsonl = async () => {
    try {
      setBuilding(true)
      await buildJsonl()
      setTimeout(fetchData, 3000) // Refresh after building
    } catch (err) {
      console.error('Failed to build JSONL:', err)
    } finally {
      setBuilding(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Learning Center</h1>
          <p className="text-text-muted mt-2">
            Continuous learning and model training management
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            onClick={handleProcessData}
            loading={processing}
            icon={<Brain className="w-4 h-4" />}
            variant="secondary"
          >
            Process Data
          </Button>
          <Button
            onClick={handleBuildJsonl}
            loading={building}
            icon={<FileText className="w-4 h-4" />}
          >
            Build JSONL
          </Button>
        </div>
      </div>

      {/* Learning Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Learning Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-primary-400">
                {stats?.total_conversations || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Conversations</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-green-400">
                {stats?.processed_conversations || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Processed</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-blue-400">
                {stats?.training_examples || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Examples</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-yellow-400">
                {stats?.jsonl_files || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">JSONL Files</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-purple-400">
                {stats?.total_tokens || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Total Tokens</div>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body className="p-4 text-center">
              <div className="text-3xl font-bold text-red-400">
                {stats?.training_runs || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Training Runs</div>
            </Card.Body>
          </Card>
        </div>
      </div>

      {/* Training Status */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Training Status</h2>
        
        {trainingStatus?.is_training ? (
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                  <Play className="w-6 h-6 text-blue-400 animate-pulse" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-text-primary">
                    Training in Progress
                  </h3>
                  <p className="text-text-muted mt-1">
                    Model: {trainingStatus.model_name || 'Unknown'}
                  </p>
                  
                  {/* Progress Bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-text-muted">Progress</span>
                      <span className="text-text-primary font-semibold">
                        {Math.round(trainingStatus.progress || 0)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-primary-400 h-3 rounded-full transition-all duration-300"
                        style={{ width: `${trainingStatus.progress || 0}%` }}
                      />
                    </div>
                  </div>

                  {/* Training Details */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div>
                      <div className="text-sm text-text-muted">Epoch</div>
                      <div className="text-lg font-semibold text-text-primary">
                        {trainingStatus.current_epoch || 0} / {trainingStatus.total_epochs || 0}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-text-muted">Loss</div>
                      <div className="text-lg font-semibold text-text-primary">
                        {trainingStatus.current_loss?.toFixed(4) || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-text-muted">Elapsed</div>
                      <div className="text-lg font-semibold text-text-primary">
                        {trainingStatus.elapsed_time || '0m'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-text-muted">ETA</div>
                      <div className="text-lg font-semibold text-text-primary">
                        {trainingStatus.eta || 'Unknown'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card.Body>
          </Card>
        ) : (
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center">
                  <Pause className="w-6 h-6 text-gray-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-text-primary">
                    No Active Training
                  </h3>
                  <p className="text-text-muted mt-1">
                    Ready to start a new training session
                  </p>
                </div>
              </div>
            </Card.Body>
          </Card>
        )}
      </div>

      {/* Learning Pipeline */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Learning Pipeline</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Step 1: Data Collection */}
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-primary-700 rounded-full flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-primary-300" />
                </div>
                <CheckCircle className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                1. Data Collection
              </h3>
              <p className="text-sm text-text-muted mb-4">
                Collecting conversations and feedback from all agents
              </p>
              <div className="text-2xl font-bold text-text-primary">
                {stats?.total_conversations || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Total collected</div>
            </Card.Body>
          </Card>

          {/* Step 2: Processing */}
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-blue-700 rounded-full flex items-center justify-center">
                  <Brain className="w-5 h-5 text-blue-300" />
                </div>
                {processing ? (
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
                ) : (
                  <CheckCircle className="w-6 h-6 text-green-400" />
                )}
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                2. Processing
              </h3>
              <p className="text-sm text-text-muted mb-4">
                Analyzing and extracting training examples
              </p>
              <div className="text-2xl font-bold text-text-primary">
                {stats?.training_examples || 0}
              </div>
              <div className="text-xs text-text-muted mt-1">Examples ready</div>
            </Card.Body>
          </Card>

          {/* Step 3: Training */}
          <Card>
            <Card.Body className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-green-700 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-green-300" />
                </div>
                {trainingStatus?.is_training ? (
                  <Play className="w-6 h-6 text-blue-400 animate-pulse" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-yellow-400" />
                )}
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                3. Training
              </h3>
              <p className="text-sm text-text-muted mb-4">
                Fine-tuning models with processed data
              </p>
              <div className="text-2xl font-bold text-text-primary">
                {trainingStatus?.is_training ? 'Running' : 'Idle'}
              </div>
              <div className="text-xs text-text-muted mt-1">Current status</div>
            </Card.Body>
          </Card>
        </div>
      </div>

      {/* Recent Training History */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-4">Recent Training History</h2>
        <Card>
          <Card.Body className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-800 border-b border-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">
                      Model
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                      Examples
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                      Epochs
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                      Final Loss
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                      Duration
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {/* Mock data - would come from API */}
                  <tr className="hover:bg-gray-800/50">
                    <td className="px-6 py-4 text-sm text-text-primary">
                      2024-01-15 14:30
                    </td>
                    <td className="px-6 py-4 text-sm text-text-primary">
                      Llama-3.1-70B
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      1,245
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      3
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      0.0234
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      2h 15m
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="px-2 py-1 bg-green-900/30 text-green-400 border border-green-700 rounded text-xs">
                        Completed
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-gray-800/50">
                    <td className="px-6 py-4 text-sm text-text-primary">
                      2024-01-14 09:15
                    </td>
                    <td className="px-6 py-4 text-sm text-text-primary">
                      DeepSeek-V3
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      987
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      5
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      0.0189
                    </td>
                    <td className="px-6 py-4 text-center text-sm text-text-primary">
                      3h 42m
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="px-2 py-1 bg-green-900/30 text-green-400 border border-green-700 rounded text-xs">
                        Completed
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default LearningCenter

