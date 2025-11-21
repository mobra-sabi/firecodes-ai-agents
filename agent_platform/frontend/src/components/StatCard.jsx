import { motion } from 'framer-motion'

export default function StatCard({ title, value, icon: Icon, color, change }) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="stat-card group"
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg bg-gradient-to-br ${color} shadow-lg`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        {change && (
          <span className="text-sm font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full">
            {change}
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl sm:text-3xl font-bold text-slate-900 mb-1">{value.toLocaleString()}</p>
        <p className="text-xs sm:text-sm text-slate-600">{title}</p>
      </div>
    </motion.div>
  )
}

