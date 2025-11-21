import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Globe, Loader2, CheckCircle } from 'lucide-react'
import api from '../lib/api'
import { useQueryClient } from '@tanstack/react-query'

export default function CreateAgentModal({ isOpen, onClose }) {
  const [siteUrl, setSiteUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const queryClient = useQueryClient()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!siteUrl.trim()) {
      setError('Please enter a valid URL')
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccess(false)

    try {
      // Validate URL format
      try {
        new URL(siteUrl.startsWith('http') ? siteUrl : `https://${siteUrl}`)
      } catch {
        setError('Invalid URL format. Please include http:// or https://')
        setIsSubmitting(false)
        return
      }

      const finalUrl = siteUrl.startsWith('http') ? siteUrl : `https://${siteUrl}`
      
      // Call API to create agent
      const { data } = await api.post('/agents', {
        site_url: finalUrl,
        agent_type: 'master',
      })

      setSuccess(true)
      
      // Refresh agents list
      queryClient.invalidateQueries(['agents'])
      queryClient.invalidateQueries(['stats'])

      // Close modal after 2 seconds
      setTimeout(() => {
        onClose()
        setSiteUrl('')
        setSuccess(false)
      }, 2000)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to create agent')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 relative"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-600" />
          </button>

          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center space-x-3 mb-2">
              <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg">
                <Globe className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900">Create Master Agent</h2>
            </div>
            <p className="text-sm text-slate-600">
              Enter a website URL to create a new master agent. The system will crawl and index the site.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Website URL
              </label>
              <input
                type="text"
                value={siteUrl}
                onChange={(e) => setSiteUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isSubmitting || success}
              />
              <p className="mt-1 text-xs text-slate-500">
                Include http:// or https://
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Success */}
            {success && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <p className="text-sm text-green-700">Agent created successfully!</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 btn-primary flex items-center justify-center space-x-2"
                disabled={isSubmitting || success}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating...</span>
                  </>
                ) : (
                  <span>Create Agent</span>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

