import { useState, useEffect } from 'react'
import Card from '@/components/ui/Card'
import { FileText, Map, BarChart3, Calendar, Eye, Download } from 'lucide-react'

const Reports = () => {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState(null)
  const [filter, setFilter] = useState('all') // all, ci_report, ceo_report, ceo_map

  useEffect(() => {
    fetchReports()
    const interval = setInterval(fetchReports, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchReports = async () => {
    try {
      const response = await fetch('/api/reports')
      const data = await response.json()
      setReports(data.reports || [])
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch reports:', err)
      setLoading(false)
    }
  }

  const fetchReportDetails = async (reportId, reportType) => {
    try {
      const response = await fetch(`/api/reports/${reportId}?report_type=${reportType}`)
      const data = await response.json()
      setSelectedReport(data)
    } catch (err) {
      console.error('Failed to fetch report details:', err)
    }
  }

  const getReportIcon = (type) => {
    switch (type) {
      case 'ci_report':
        return <BarChart3 className="w-5 h-5" />
      case 'ceo_report':
        return <FileText className="w-5 h-5" />
      case 'ceo_map':
        return <Map className="w-5 h-5" />
      default:
        return <FileText className="w-5 h-5" />
    }
  }

  const getReportColor = (type) => {
    switch (type) {
      case 'ci_report':
        return 'text-blue-400 bg-blue-900/30'
      case 'ceo_report':
        return 'text-green-400 bg-green-900/30'
      case 'ceo_map':
        return 'text-purple-400 bg-purple-900/30'
      default:
        return 'text-gray-400 bg-gray-800'
    }
  }

  const formatDate = (date) => {
    if (!date) return 'N/A'
    try {
      return new Date(date).toLocaleString('ro-RO', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return date.toString()
    }
  }

  const filteredReports = filter === 'all' 
    ? reports 
    : reports.filter(r => r.type === filter)

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
      <div>
        <h1 className="text-3xl font-bold text-text-primary">SEO Reports</h1>
        <p className="text-text-muted mt-1">Strategic SEO analysis and competitive reports</p>
      </div>

      {/* Filters */}
      <div className="flex space-x-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            filter === 'all'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-800 text-text-muted hover:bg-gray-700'
          }`}
        >
          All ({reports.length})
        </button>
        <button
          onClick={() => setFilter('ci_report')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            filter === 'ci_report'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-800 text-text-muted hover:bg-gray-700'
          }`}
        >
          CI Reports ({reports.filter(r => r.type === 'ci_report').length})
        </button>
        <button
          onClick={() => setFilter('ceo_report')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            filter === 'ceo_report'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-800 text-text-muted hover:bg-gray-700'
          }`}
        >
          CEO Reports ({reports.filter(r => r.type === 'ceo_report').length})
        </button>
        <button
          onClick={() => setFilter('ceo_map')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            filter === 'ceo_map'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-800 text-text-muted hover:bg-gray-700'
          }`}
        >
          CEO Maps ({reports.filter(r => r.type === 'ceo_map').length})
        </button>
      </div>

      {/* Reports List */}
      {filteredReports.length === 0 ? (
        <Card>
          <Card.Body>
            <p className="text-text-muted text-center py-12">
              No reports found. Reports will be automatically generated when agents complete their analysis.
            </p>
          </Card.Body>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredReports.map((report) => (
            <Card
              key={report.id}
              className="hover:border-primary-500 transition-colors cursor-pointer"
              onClick={() => fetchReportDetails(report.id, report.type)}
            >
              <Card.Body className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${getReportColor(report.type)}`}>
                    {getReportIcon(report.type)}
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${getReportColor(report.type)}`}>
                    {report.type.replace('_', ' ').toUpperCase()}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-text-primary mb-2">
                  {report.title}
                </h3>

                <div className="space-y-2 text-sm text-text-muted">
                  <div className="flex items-center">
                    <Calendar className="w-4 h-4 mr-2" />
                    {formatDate(report.generated_at)}
                  </div>

                  {report.master_domain && (
                    <div className="flex items-center">
                      <span className="font-medium">Domain:</span>
                      <span className="ml-2">{report.master_domain}</span>
                    </div>
                  )}

                  {report.competitors_analyzed !== undefined && (
                    <div className="flex items-center">
                      <span className="font-medium">Competitors:</span>
                      <span className="ml-2">{report.competitors_analyzed}</span>
                    </div>
                  )}

                  {report.keywords_covered !== undefined && (
                    <div className="flex items-center">
                      <span className="font-medium">Keywords:</span>
                      <span className="ml-2">{report.keywords_covered} / {report.total_keywords}</span>
                    </div>
                  )}

                  {report.subdomains_count !== undefined && (
                    <div className="flex items-center">
                      <span className="font-medium">Subdomains:</span>
                      <span className="ml-2">{report.subdomains_count}</span>
                    </div>
                  )}

                  {report.competitors_count !== undefined && (
                    <div className="flex items-center">
                      <span className="font-medium">Competitors:</span>
                      <span className="ml-2">{report.competitors_count}</span>
                    </div>
                  )}
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    fetchReportDetails(report.id, report.type)
                  }}
                  className="mt-4 w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors flex items-center justify-center"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  View Details
                </button>
              </Card.Body>
            </Card>
          ))}
        </div>
      )}

      {/* Report Details Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedReport(null)}>
          <div className="bg-gray-900 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-700 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-text-primary">{selectedReport.type.replace('_', ' ').toUpperCase()}</h2>
                <p className="text-text-muted mt-1">{formatDate(selectedReport.generated_at || selectedReport.created_at)}</p>
              </div>
              <button
                onClick={() => setSelectedReport(null)}
                className="text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-6">
              {selectedReport.type === 'ci_report' && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Master Agent</h3>
                    <p className="text-text-muted">{selectedReport.master_agent}</p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Statistics</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-gray-800 rounded">
                        <div className="text-sm text-text-muted">Competitors Analyzed</div>
                        <div className="text-2xl font-bold text-text-primary">{selectedReport.competitors_analyzed}</div>
                      </div>
                      <div className="p-4 bg-gray-800 rounded">
                        <div className="text-sm text-text-muted">Total Keywords</div>
                        <div className="text-2xl font-bold text-text-primary">{selectedReport.total_keywords}</div>
                      </div>
                    </div>
                  </div>

                  {selectedReport.strategic_insights && selectedReport.strategic_insights.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Strategic Insights</h3>
                      <ul className="space-y-2">
                        {selectedReport.strategic_insights.map((insight, idx) => (
                          <li key={idx} className="p-3 bg-gray-800 rounded text-text-muted">
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedReport.competitors_list && selectedReport.competitors_list.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Competitors</h3>
                      <div className="space-y-2">
                        {selectedReport.competitors_list.slice(0, 10).map((comp, idx) => (
                          <div key={idx} className="p-3 bg-gray-800 rounded flex items-center justify-between">
                            <span className="text-text-primary">{comp.domain || comp}</span>
                            {comp.score && (
                              <span className="text-text-muted text-sm">Score: {comp.score}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {selectedReport.type === 'ceo_report' && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Master Domain</h3>
                    <p className="text-text-muted">{selectedReport.master_domain}</p>
                  </div>

                  {selectedReport.report && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Report Content</h3>
                      <div className="p-4 bg-gray-800 rounded text-text-muted whitespace-pre-wrap">
                        {selectedReport.report}
                      </div>
                    </div>
                  )}

                  {selectedReport.data && Object.keys(selectedReport.data).length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Data</h3>
                      <pre className="p-4 bg-gray-800 rounded text-text-muted text-sm overflow-x-auto">
                        {JSON.stringify(selectedReport.data, null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              )}

              {selectedReport.type === 'ceo_map' && (
                <>
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Master Domain</h3>
                    <p className="text-text-muted">{selectedReport.master_domain}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-800 rounded">
                      <div className="text-sm text-text-muted">Subdomains</div>
                      <div className="text-2xl font-bold text-text-primary">{selectedReport.subdomains?.length || 0}</div>
                    </div>
                    <div className="p-4 bg-gray-800 rounded">
                      <div className="text-sm text-text-muted">Competitors</div>
                      <div className="text-2xl font-bold text-text-primary">{selectedReport.competitors?.length || 0}</div>
                    </div>
                  </div>

                  {selectedReport.subdomains && selectedReport.subdomains.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Subdomains</h3>
                      <div className="space-y-2">
                        {selectedReport.subdomains.slice(0, 10).map((subdomain, idx) => (
                          <div key={idx} className="p-3 bg-gray-800 rounded text-text-primary">
                            {subdomain}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedReport.competitors && selectedReport.competitors.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary mb-2">Competitors</h3>
                      <div className="space-y-2">
                        {selectedReport.competitors.slice(0, 10).map((comp, idx) => (
                          <div key={idx} className="p-3 bg-gray-800 rounded text-text-primary">
                            {comp.domain || comp}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Reports
