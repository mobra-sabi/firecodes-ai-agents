import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle, XCircle, Clock, Play, FileText } from 'lucide-react'
import api from '../lib/api'

export default function WorkflowMonitor() {
  const { id } = useParams()
  
  const { data: progress, isLoading: progressLoading } = useQuery({
    queryKey: ['workflow-progress', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/workflow/progress/${id}`)
      return data
    },
    refetchInterval: 2000, // Refresh every 2 seconds
  })
  
  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ['workflow-logs', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/workflow/logs/${id}`)
      return data
    },
    refetchInterval: 2000,
  })
  
  const phases = [
    { num: 1, name: 'Creare Agent Master', desc: 'Crawl + embeddings' },
    { num: 2, name: 'Integrare LangChain', desc: 'Memorie conversațională' },
    { num: 3, name: 'DeepSeek Identificare', desc: 'Expert în domeniu' },
    { num: 4, name: 'Descompunere Subdomenii', desc: 'Keywords generation' },
    { num: 5, name: 'Google Search', desc: 'Descoperire competitori' },
    { num: 6, name: 'Hartă Competitivă', desc: 'CEO mapping' },
    { num: 7, name: 'Transformare Competitori', desc: 'Slave agents creation' },
    { num: 8, name: 'Organogramă + Învățare', desc: 'Raport final' },
  ]
  
  if (progressLoading || logsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }
  
  const currentPhase = progress?.current_phase || 0
  const progressPercent = progress?.progress || 0
  
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
          Workflow Monitor
        </h1>
        <p className="text-sm sm:text-base text-slate-600">
          Monitorizare în timp real a workflow-ului CEO
        </p>
      </div>
      
      {/* Progress Overview */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-slate-900">Progress Overview</h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            progress?.status === 'completed'
              ? 'bg-green-100 text-green-700'
              : progress?.status === 'running'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700'
          }`}>
            {progress?.status || 'not_started'}
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">
              {progress?.message || 'Waiting to start...'}
            </span>
            <span className="text-sm font-bold text-blue-600">
              {progressPercent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-3">
            <motion.div
              className="bg-gradient-to-r from-blue-600 to-indigo-600 h-3 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
        
        {/* Phases Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {phases.map((phase) => {
            const isCompleted = phase.num < currentPhase
            const isCurrent = phase.num === currentPhase
            const isPending = phase.num > currentPhase
            
            return (
              <div
                key={phase.num}
                className={`p-4 rounded-lg border-2 transition-all ${
                  isCompleted
                    ? 'bg-green-50 border-green-300'
                    : isCurrent
                    ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-center space-x-2 mb-2">
                  {isCompleted ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : isCurrent ? (
                    <Clock className="w-5 h-5 text-blue-600 animate-pulse" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                  )}
                  <span className="font-bold text-sm">Faza {phase.num}</span>
                </div>
                <h3 className="font-semibold text-slate-900 mb-1">{phase.name}</h3>
                <p className="text-xs text-slate-600">{phase.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
      
      {/* Live Logs */}
      <div className="card">
        <h2 className="text-xl font-bold text-slate-900 mb-4">Live Logs</h2>
        <div className="bg-slate-900 rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto">
          {logs?.logs && logs.logs.length > 0 ? (
            logs.logs.map((log, index) => (
              <div
                key={index}
                className={`mb-2 ${
                  log.status === 'error'
                    ? 'text-red-400'
                    : log.status === 'success'
                    ? 'text-green-400'
                    : 'text-slate-300'
                }`}
              >
                <span className="text-slate-500">
                  [{new Date(log.timestamp).toLocaleTimeString()}]
                </span>{' '}
                <span className="font-semibold">[{log.phase}]</span>{' '}
                {log.message}
              </div>
            ))
          ) : (
            <div className="text-slate-500">No logs yet...</div>
          )}
        </div>
      </div>
    </div>
  )
}

