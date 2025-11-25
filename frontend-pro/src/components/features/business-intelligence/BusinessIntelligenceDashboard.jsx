// BusinessIntelligenceDashboard.jsx
// 🎯 Dashboard complet pentru Business Intelligence
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { 
  TrendingUp, TrendingDown, Target, AlertTriangle, 
  Zap, Award, Users, FileText, Search, MessageSquare,
  ChevronRight, CheckCircle, Clock, ArrowUp, ArrowDown
} from 'lucide-react';

// Positioning Score Card
const PositioningScoreCard = ({ data }) => {
  if (!data) return null;
  
  const score = data.score || 0;
  const interpretation = data.interpretation || {};
  
  const getScoreColor = (s) => {
    if (s >= 80) return 'text-emerald-500';
    if (s >= 60) return 'text-blue-500';
    if (s >= 40) return 'text-yellow-500';
    return 'text-red-500';
  };
  
  const getScoreBg = (s) => {
    if (s >= 80) return 'from-emerald-500/20 to-emerald-600/10';
    if (s >= 60) return 'from-blue-500/20 to-blue-600/10';
    if (s >= 40) return 'from-yellow-500/20 to-yellow-600/10';
    return 'from-red-500/20 to-red-600/10';
  };

  return (
    <div className={`bg-gradient-to-br ${getScoreBg(score)} rounded-2xl p-6 border border-white/10`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Target className="w-5 h-5" />
          Scor Poziționare
        </h3>
        <span className="text-2xl">{interpretation.emoji}</span>
      </div>
      
      <div className="flex items-end gap-4 mb-4">
        <span className={`text-6xl font-bold ${getScoreColor(score)}`}>{score}</span>
        <span className="text-2xl text-gray-400 mb-2">/100</span>
      </div>
      
      <p className="text-gray-300 mb-4">{interpretation.message}</p>
      
      {data.ranking && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Award className="w-4 h-4" />
          <span>Poziția #{data.ranking} din {data.total_competitors} competitori</span>
        </div>
      )}
      
      {/* Score Breakdown */}
      {data.breakdown && (
        <div className="mt-6 space-y-3">
          {Object.entries(data.breakdown).map(([key, val]) => (
            <div key={key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">{val.label}</span>
                <span className="text-white">{val.score}/{val.max}</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getScoreColor(val.score * 4)} bg-current rounded-full transition-all`}
                  style={{ width: `${(val.score / val.max) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Gaps Summary Card
const GapsSummaryCard = ({ data }) => {
  if (!data) return null;
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
        <Search className="w-5 h-5 text-purple-400" />
        Gap Analysis
      </h3>
      
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-3 bg-red-500/10 rounded-xl">
          <div className="text-3xl font-bold text-red-400">{data.keyword_gaps || 0}</div>
          <div className="text-xs text-gray-400">Keywords lipsă</div>
        </div>
        <div className="text-center p-3 bg-orange-500/10 rounded-xl">
          <div className="text-3xl font-bold text-orange-400">{data.service_gaps || 0}</div>
          <div className="text-xs text-gray-400">Servicii lipsă</div>
        </div>
        <div className="text-center p-3 bg-green-500/10 rounded-xl">
          <div className="text-3xl font-bold text-green-400">{data.opportunities || 0}</div>
          <div className="text-xs text-gray-400">Oportunități</div>
        </div>
      </div>
      
      {data.top_keyword_gap && (
        <div className="p-3 bg-gray-700/50 rounded-lg mb-2">
          <div className="text-xs text-gray-400 mb-1">Top Keyword Gap</div>
          <div className="text-white font-medium">{data.top_keyword_gap.keyword}</div>
          <div className="text-xs text-red-400">{data.top_keyword_gap.competitors_with} competitori au acest keyword</div>
        </div>
      )}
      
      {data.top_service_gap && (
        <div className="p-3 bg-gray-700/50 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Top Serviciu Lipsă</div>
          <div className="text-white font-medium">{data.top_service_gap.service}</div>
          <div className="text-xs text-orange-400">{data.top_service_gap.competitors_with} competitori oferă acest serviciu</div>
        </div>
      )}
    </div>
  );
};

// Alerts Card
const AlertsCard = ({ data }) => {
  if (!data) return null;
  
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-500/20 border-red-500/50 text-red-400';
      case 'WARNING': return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400';
      default: return 'bg-blue-500/20 border-blue-500/50 text-blue-400';
    }
  };

  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-yellow-400" />
        Alerte Competitori
        {data.total > 0 && (
          <span className="ml-auto bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full text-sm">
            {data.total}
          </span>
        )}
      </h3>
      
      {data.latest && data.latest.length > 0 ? (
        <div className="space-y-3">
          {data.latest.map((alert, idx) => (
            <div key={idx} className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}>
              <div className="font-medium">{alert.title}</div>
              <div className="text-sm opacity-80 mt-1">{alert.message}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-400">
          <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-500" />
          <p>Nicio alertă activă</p>
        </div>
      )}
    </div>
  );
};

// Recommended Actions Card
const ActionsCard = ({ actions }) => {
  if (!actions || actions.length === 0) return null;
  
  const getImpactBadge = (impact) => {
    switch (impact) {
      case 'HIGH': return 'bg-green-500/20 text-green-400';
      case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
        <Zap className="w-5 h-5 text-yellow-400" />
        Acțiuni Recomandate
      </h3>
      
      <div className="space-y-3">
        {actions.map((action, idx) => (
          <div key={idx} className="p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="font-medium text-white">{action.title}</div>
                <div className="text-sm text-gray-400 mt-1">{action.description}</div>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs ${getImpactBadge(action.impact)}`}>
                {action.impact}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {action.estimated_time}
              </span>
              <span className="flex items-center gap-1">
                <FileText className="w-3 h-3" />
                {action.category}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Competitor Comparison Card
const ComparisonCard = ({ data }) => {
  if (!data || !data.you || !data.top_competitors) return null;
  
  const metrics = data.metrics || ['pages', 'keywords', 'services', 'chunks'];
  const labels = data.metric_labels || {};

  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
        <Users className="w-5 h-5 text-blue-400" />
        Tu vs Top Competitori
      </h3>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-gray-400 text-sm">
              <th className="pb-3">Metric</th>
              <th className="pb-3 text-center">Tu</th>
              {data.top_competitors.slice(0, 3).map((comp, idx) => (
                <th key={idx} className="pb-3 text-center">{comp.domain?.substring(0, 15)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(metric => (
              <tr key={metric} className="border-t border-gray-700">
                <td className="py-3 text-gray-300">{labels[metric] || metric}</td>
                <td className="py-3 text-center">
                  <span className="font-bold text-emerald-400">{data.you[metric]}</span>
                </td>
                {data.top_competitors.slice(0, 3).map((comp, idx) => (
                  <td key={idx} className="py-3 text-center text-gray-300">
                    {comp[metric]}
                    {comp[metric] > data.you[metric] && (
                      <ArrowUp className="w-3 h-3 inline ml-1 text-red-400" />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Main Dashboard Component
const BusinessIntelligenceDashboard = () => {
  const { agentId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  
  useEffect(() => {
    const fetchDashboard = async () => {
      if (!agentId) return;
      
      setLoading(true);
      try {
        const response = await api.get(`/api/agents/${agentId}/business-intelligence/dashboard`);
        setDashboardData(response.data);
      } catch (err) {
        console.error('Error fetching BI dashboard:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboard();
  }, [agentId]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-6 text-red-400">
        <AlertTriangle className="w-6 h-6 mb-2" />
        <p>Eroare la încărcarea dashboard-ului: {error}</p>
      </div>
    );
  }
  
  if (!dashboardData) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>Nu sunt date disponibile pentru acest agent.</p>
        <p className="text-sm mt-2">Asigură-te că ai competitori analizați.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">🎯 Business Intelligence</h2>
          <p className="text-gray-400 mt-1">Analiză completă a poziționării tale în piață</p>
        </div>
        <div className="text-sm text-gray-500">
          Actualizat: {new Date(dashboardData.generated_at).toLocaleString('ro-RO')}
        </div>
      </div>
      
      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Positioning Score */}
        <PositioningScoreCard data={dashboardData.positioning_score} />
        
        {/* Gaps Summary */}
        <GapsSummaryCard data={dashboardData.gaps_summary} />
        
        {/* Alerts */}
        <AlertsCard data={dashboardData.alerts} />
        
        {/* Recommended Actions */}
        <ActionsCard actions={dashboardData.recommended_actions} />
      </div>
      
      {/* Competitor Comparison - Full Width */}
      <ComparisonCard data={dashboardData.vs_top_competitors} />
      
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 transition-colors">
          <FileText className="w-4 h-4" />
          Vezi Plan Complet
        </button>
        <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition-colors">
          <Search className="w-4 h-4" />
          Gap Analysis Detaliat
        </button>
        <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition-colors">
          <MessageSquare className="w-4 h-4" />
          Întreabă AI Coach
        </button>
      </div>
    </div>
  );
};

export default BusinessIntelligenceDashboard;

