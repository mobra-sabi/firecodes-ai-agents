import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FileText, Download, Image, Loader2, FileJson } from 'lucide-react'
import api from '../lib/api'
import { useState } from 'react'

export default function ReportsPage() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const { data } = await api.get('/api/reports/')
      return data.reports || []
    },
  })
  
  const [downloading, setDownloading] = useState(null)
  
  const handleDownload = async (domain, format) => {
    setDownloading(`${domain}-${format}`)
    try {
      const response = await api.get(`/api/reports/${domain}?format=${format}`, {
        responseType: 'blob',
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${domain}_report.${format === 'pdf' ? 'pdf' : format === 'graph' ? 'png' : format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Download error:', error)
    } finally {
      setDownloading(null)
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }
  
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
          Rapoarte CEO Workflow
        </h1>
        <p className="text-sm sm:text-base text-slate-600">Vizualizează și descarcă rapoarte pentru agenții creați</p>
      </div>
      
      {/* Reports Grid */}
      {reports && reports.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {reports.map((report, index) => (
            <motion.div
              key={report.domain}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-900 mb-1">
                    {report.domain}
                  </h3>
                  <p className="text-sm text-slate-600">Raport complet</p>
                </div>
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">Formate disponibile:</span>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleDownload(report.domain, 'json')}
                    disabled={downloading === `${report.domain}-json`}
                    className="flex items-center space-x-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors text-sm"
                  >
                    {downloading === `${report.domain}-json` ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileJson className="w-4 h-4" />
                    )}
                    <span>JSON</span>
                  </button>
                  
                  <button
                    onClick={() => handleDownload(report.domain, 'markdown')}
                    disabled={downloading === `${report.domain}-markdown`}
                    className="flex items-center space-x-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors text-sm"
                  >
                    {downloading === `${report.domain}-markdown` ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                    <span>MD</span>
                  </button>
                  
                  {report.pdf && (
                    <button
                      onClick={() => handleDownload(report.domain, 'pdf')}
                      disabled={downloading === `${report.domain}-pdf`}
                      className="flex items-center space-x-2 px-3 py-2 bg-red-100 hover:bg-red-200 rounded-lg transition-colors text-sm"
                    >
                      {downloading === `${report.domain}-pdf` ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      <span>PDF</span>
                    </button>
                  )}
                  
                  {report.graph && (
                    <button
                      onClick={() => handleDownload(report.domain, 'graph')}
                      disabled={downloading === `${report.domain}-graph`}
                      className="flex items-center space-x-2 px-3 py-2 bg-purple-100 hover:bg-purple-200 rounded-lg transition-colors text-sm"
                    >
                      {downloading === `${report.domain}-graph` ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Image className="w-4 h-4" />
                      )}
                      <span>PNG</span>
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-slate-500">
          <FileText className="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p>Nu există rapoarte generate încă.</p>
          <p className="text-sm mt-2">Rapoartele vor apărea aici după ce rulezi CEO Workflow.</p>
        </div>
      )}
    </div>
  )
}

