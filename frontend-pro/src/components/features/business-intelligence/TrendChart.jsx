// TrendChart.jsx
// 📊 Grafic pentru trenduri poziționare
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { TrendingUp, TrendingDown, Minus, RefreshCw, Calendar } from 'lucide-react';

const TrendChart = () => {
  const { agentId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  
  const fetchTrends = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/agents/${agentId}/business-intelligence/trends/analysis`);
      setData(response.data);
    } catch (err) {
      console.error('Error fetching trends:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const recordSnapshot = async () => {
    try {
      await api.post(`/api/agents/${agentId}/business-intelligence/trends/snapshot`);
      fetchTrends();
    } catch (err) {
      console.error('Error recording snapshot:', err);
    }
  };
  
  useEffect(() => {
    fetchTrends();
  }, [agentId, days]);
  
  if (loading) {
    return (
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10 animate-pulse">
        <div className="h-8 bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-gray-700 rounded"></div>
      </div>
    );
  }
  
  if (!data?.has_data) {
    return (
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          Trend Poziționare
        </h3>
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-500" />
          <p className="text-gray-400">{data?.message || "Nu există date suficiente"}</p>
          <button
            onClick={recordSnapshot}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 mx-auto"
          >
            <RefreshCw className="w-4 h-4" />
            Salvează Snapshot Acum
          </button>
        </div>
      </div>
    );
  }
  
  const { chart_data, trend, trend_message, score_change, ranking_change } = data;
  
  // Calculează min/max pentru grafic
  const scores = chart_data?.scores || [];
  const minScore = Math.min(...scores) - 5;
  const maxScore = Math.max(...scores) + 5;
  const range = maxScore - minScore;
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          Trend Poziționare
        </h3>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-gray-700 text-white rounded-lg px-3 py-1 text-sm border border-gray-600"
          >
            <option value={7}>7 zile</option>
            <option value={30}>30 zile</option>
            <option value={90}>90 zile</option>
          </select>
          <button
            onClick={recordSnapshot}
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
            title="Salvează snapshot"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>
      
      {/* Trend Summary */}
      <div className={`p-4 rounded-xl mb-6 ${
        trend === 'up' ? 'bg-green-500/10 border border-green-500/30' :
        trend === 'down' ? 'bg-red-500/10 border border-red-500/30' :
        'bg-gray-700/50 border border-gray-600'
      }`}>
        <div className="flex items-center gap-3">
          {trend === 'up' && <TrendingUp className="w-6 h-6 text-green-400" />}
          {trend === 'down' && <TrendingDown className="w-6 h-6 text-red-400" />}
          {trend === 'stable' && <Minus className="w-6 h-6 text-gray-400" />}
          <p className="text-gray-200">{trend_message}</p>
        </div>
        <div className="flex gap-6 mt-3 text-sm">
          <span className={score_change >= 0 ? 'text-green-400' : 'text-red-400'}>
            Scor: {score_change >= 0 ? '+' : ''}{score_change} puncte
          </span>
          <span className={ranking_change >= 0 ? 'text-green-400' : 'text-red-400'}>
            Poziție: {ranking_change >= 0 ? '+' : ''}{ranking_change} locuri
          </span>
        </div>
      </div>
      
      {/* Simple Line Chart */}
      <div className="relative h-48">
        <svg className="w-full h-full" viewBox={`0 0 ${scores.length * 40} 200`} preserveAspectRatio="none">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map(y => (
            <line
              key={y}
              x1="0"
              y1={200 - (y / 100) * 200}
              x2={scores.length * 40}
              y2={200 - (y / 100) * 200}
              stroke="#374151"
              strokeWidth="1"
            />
          ))}
          
          {/* Line */}
          <polyline
            fill="none"
            stroke="#8B5CF6"
            strokeWidth="3"
            points={scores.map((score, i) => {
              const x = i * 40 + 20;
              const y = 200 - ((score - minScore) / range) * 180 - 10;
              return `${x},${y}`;
            }).join(' ')}
          />
          
          {/* Points */}
          {scores.map((score, i) => {
            const x = i * 40 + 20;
            const y = 200 - ((score - minScore) / range) * 180 - 10;
            return (
              <g key={i}>
                <circle cx={x} cy={y} r="6" fill="#8B5CF6" />
                <text x={x} y={y - 12} textAnchor="middle" fill="#fff" fontSize="10">
                  {score}
                </text>
              </g>
            );
          })}
        </svg>
        
        {/* X-axis labels */}
        <div className="flex justify-between mt-2 text-xs text-gray-500 overflow-x-auto">
          {chart_data?.labels?.map((label, i) => (
            <span key={i} className="min-w-[40px] text-center">
              {label?.slice(5)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TrendChart;

