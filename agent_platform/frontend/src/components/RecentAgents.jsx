import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, CheckCircle, Clock } from 'lucide-react'

export default function RecentAgents({ agents = [] }) {
  const recentAgents = agents.slice(0, 5)
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900">Recent Agents</h2>
        <Link
          to="/agents"
          className="text-blue-600 hover:text-blue-700 font-medium flex items-center space-x-1 text-sm sm:text-base"
        >
          <span>View all</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
      
      {recentAgents.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <p>No agents found. Create your first agent to get started!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {recentAgents.map((agent, index) => (
            <motion.div
              key={agent._id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors gap-3"
            >
              <div className="flex items-center space-x-3 sm:space-x-4 flex-1 w-full sm:w-auto">
                <div className={`p-2 rounded-lg flex-shrink-0 ${
                  agent.agent_type === 'master' 
                    ? 'bg-blue-100 text-blue-600' 
                    : 'bg-purple-100 text-purple-600'
                }`}>
                  {agent.agent_type === 'master' ? 'M' : 'S'}
                </div>
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/agents/${agent._id}`}
                    className="font-semibold text-slate-900 hover:text-blue-600 transition-colors text-sm sm:text-base block truncate"
                  >
                    {agent.domain || 'Unknown'}
                  </Link>
                  <p className="text-xs sm:text-sm text-slate-600">
                    {agent.chunks_indexed || 0} chunks • {agent.keyword_count || 0} keywords
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2 sm:space-x-4 w-full sm:w-auto justify-end">
                {agent.status === 'validated' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <Clock className="w-5 h-5 text-yellow-600" />
                )}
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  agent.status === 'validated'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {agent.status || 'unknown'}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

