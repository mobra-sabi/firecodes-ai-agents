// ROICalculator.jsx
// 💰 Calculator ROI pentru acțiuni
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { Calculator, TrendingUp, DollarSign, Clock, CheckCircle, Search } from 'lucide-react';

const ROICalculator = () => {
  const { agentId } = useParams();
  const [planROI, setPlanROI] = useState(null);
  const [keywordROI, setKeywordROI] = useState(null);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [position, setPosition] = useState(5);
  const [calculating, setCalculating] = useState(false);
  
  const fetchPlanROI = async () => {
    try {
      const response = await api.get(`/api/agents/${agentId}/business-intelligence/roi/plan`);
      setPlanROI(response.data);
    } catch (err) {
      console.error('Error fetching plan ROI:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const calculateKeywordROI = async () => {
    if (!keyword.trim()) return;
    setCalculating(true);
    try {
      const response = await api.get(
        `/api/agents/${agentId}/business-intelligence/roi/keyword/${encodeURIComponent(keyword)}?position=${position}`
      );
      setKeywordROI(response.data);
    } catch (err) {
      console.error('Error calculating keyword ROI:', err);
    } finally {
      setCalculating(false);
    }
  };
  
  useEffect(() => {
    fetchPlanROI();
  }, [agentId]);
  
  if (loading) {
    return <div className="animate-pulse h-64 bg-gray-800/50 rounded-2xl"></div>;
  }
  
  return (
    <div className="space-y-6">
      {/* Plan ROI Overview */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-6">
          <Calculator className="w-5 h-5 text-green-400" />
          ROI Plan de Acțiune
        </h3>
        
        {planROI && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 bg-gray-700/50 rounded-xl text-center">
                <p className="text-sm text-gray-400">Investiție Totală</p>
                <p className="text-2xl font-bold text-white">{planROI.total_investment}</p>
              </div>
              <div className="p-4 bg-gray-700/50 rounded-xl text-center">
                <p className="text-sm text-gray-400">Beneficiu Anual</p>
                <p className="text-2xl font-bold text-green-400">{planROI.total_yearly_benefit}</p>
              </div>
              <div className="p-4 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-xl text-center border border-green-500/30">
                <p className="text-sm text-gray-400">ROI Total</p>
                <p className="text-2xl font-bold text-green-400">{planROI.total_roi}</p>
              </div>
              <div className="p-4 bg-gray-700/50 rounded-xl text-center">
                <p className="text-sm text-gray-400">Profit Net</p>
                <p className="text-2xl font-bold text-emerald-400">{planROI.net_benefit}</p>
              </div>
            </div>
            
            {/* Actions Breakdown */}
            <div className="space-y-3">
              <h4 className="font-medium text-white">Detalii pe Acțiuni ({planROI.total_actions})</h4>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {planROI.actions_breakdown?.map((action, i) => (
                  <div key={i} className="p-3 bg-gray-700/50 rounded-lg flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-white truncate">{action.action_title}</p>
                      <div className="flex gap-4 text-xs text-gray-400 mt-1">
                        <span>Cost: {action.estimated_cost}</span>
                        <span>Beneficiu/an: {action.yearly_benefit}</span>
                        <span>Payback: {action.payback_months}</span>
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <p className={`font-bold ${
                        parseInt(action.roi_percent) > 100 ? 'text-green-400' : 'text-yellow-400'
                      }`}>
                        {action.roi_percent}
                      </p>
                      <p className="text-xs text-gray-500">{action.recommendation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
      
      {/* Keyword ROI Calculator */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-6">
          <Search className="w-5 h-5 text-blue-400" />
          Calculator ROI Keyword
        </h3>
        
        <div className="flex gap-4 mb-6">
          <div className="flex-1">
            <label className="text-sm text-gray-400">Keyword</label>
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="ex: amenajări interioare București"
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400"
            />
          </div>
          <div className="w-32">
            <label className="text-sm text-gray-400">Poziție Țintă</label>
            <select
              value={position}
              onChange={(e) => setPosition(Number(e.target.value))}
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(p => (
                <option key={p} value={p}>#{p}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={calculateKeywordROI}
              disabled={calculating || !keyword.trim()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg"
            >
              {calculating ? 'Calculez...' : 'Calculează'}
            </button>
          </div>
        </div>
        
        {keywordROI && (
          <div className="p-4 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-xl border border-blue-500/30">
            <h4 className="font-medium text-white mb-4">
              Potențial pentru "{keywordROI.keyword}" (poziția #{keywordROI.estimated_position})
            </h4>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-sm text-gray-400">Căutări/lună</p>
                <p className="text-xl font-bold text-white">{keywordROI.monthly_searches}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">CTR Estimat</p>
                <p className="text-xl font-bold text-white">{keywordROI.ctr}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Vizitatori/lună</p>
                <p className="text-xl font-bold text-blue-400">{keywordROI.monthly_visitors}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Valoare Trafic</p>
                <p className="text-xl font-bold text-green-400">{keywordROI.traffic_value}</p>
              </div>
            </div>
            
            <div className="mt-4 pt-4 border-t border-gray-700 grid grid-cols-2 gap-4">
              <div className="text-center">
                <p className="text-sm text-gray-400">Conversii Potențiale</p>
                <p className="text-xl font-bold text-purple-400">{keywordROI.potential_conversions}/lună</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Venit Potențial Anual</p>
                <p className="text-2xl font-bold text-green-400">{keywordROI.yearly_potential}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ROICalculator;

