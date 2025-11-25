// BusinessIntelligence.jsx
// 🎯 Pagina principală Business Intelligence
import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import BusinessIntelligenceDashboard from '@/components/features/business-intelligence/BusinessIntelligenceDashboard';
import DiscoveryWizard from '@/components/features/business-intelligence/DiscoveryWizard';
import TrendChart from '@/components/features/business-intelligence/TrendChart';
import GoalTracker from '@/components/features/business-intelligence/GoalTracker';
import ActionChecklist from '@/components/features/business-intelligence/ActionChecklist';
import AIContentGenerator from '@/components/features/business-intelligence/AIContentGenerator';
import ROICalculator from '@/components/features/business-intelligence/ROICalculator';
import Leaderboard from '@/components/features/business-intelligence/Leaderboard';
import { 
  ArrowLeft, LayoutDashboard, Compass, FileText, 
  MessageSquare, Bell, Users, TrendingUp, Target,
  CheckSquare, Sparkles, Calculator, Trophy
} from 'lucide-react';

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'trends', label: 'Trenduri', icon: TrendingUp },
  { id: 'goals', label: 'Obiective', icon: Target },
  { id: 'checklist', label: 'Checklist', icon: CheckSquare },
  { id: 'content', label: 'AI Content', icon: Sparkles },
  { id: 'roi', label: 'ROI', icon: Calculator },
  { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
  { id: 'discovery', label: 'Discovery', icon: Compass },
  { id: 'coach', label: 'AI Coach', icon: MessageSquare },
];

const BusinessIntelligencePage = () => {
  const { agentId } = useParams();
  const [activeTab, setActiveTab] = useState('dashboard');
  
  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <BusinessIntelligenceDashboard />;
      case 'trends':
        return <TrendChart />;
      case 'goals':
        return <GoalTracker />;
      case 'checklist':
        return <ActionChecklist />;
      case 'content':
        return <AIContentGenerator />;
      case 'roi':
        return <ROICalculator />;
      case 'leaderboard':
        return <Leaderboard />;
      case 'discovery':
        return <DiscoveryWizard />;
      case 'coach':
        return <AICoachView agentId={agentId} />;
      default:
        return <BusinessIntelligenceDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800/50 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link 
                to={`/agents/${agentId}`}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold">🎯 Business Intelligence</h1>
                <p className="text-sm text-gray-400">Ghid AI pentru îmbunătățirea afacerii</p>
              </div>
            </div>
          </div>
          
          {/* Tabs */}
          <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {renderContent()}
      </div>
    </div>
  );
};

// Action Plan View
const ActionPlanView = ({ agentId }) => {
  const [plan, setPlan] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  
  React.useEffect(() => {
    const fetchPlan = async () => {
      try {
        const response = await fetch(`/api/agents/${agentId}/business-intelligence/action-plan`);
        const data = await response.json();
        setPlan(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlan();
  }, [agentId]);
  
  if (loading) return <div className="text-center py-12">Se încarcă...</div>;
  if (!plan) return <div className="text-center py-12 text-gray-400">Nu s-a putut încărca planul.</div>;
  
  const renderActions = (phase) => {
    const phaseData = plan[phase];
    if (!phaseData) return null;
    
    return (
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-xl font-bold text-white mb-2">{phaseData.title}</h3>
        <p className="text-gray-400 mb-6">{phaseData.description}</p>
        
        <div className="space-y-4">
          {phaseData.actions?.map((action, idx) => (
            <div key={idx} className="bg-gray-700/50 rounded-xl p-4">
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-white">{action.title}</h4>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  action.impact === 'HIGH' ? 'bg-green-500/20 text-green-400' :
                  action.impact === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {action.impact}
                </span>
              </div>
              <p className="text-sm text-gray-400 mb-3">{action.description}</p>
              
              {action.steps && (
                <div className="space-y-2">
                  {action.steps.map((step, sidx) => (
                    <div key={sidx} className="flex items-start gap-2 text-sm text-gray-300">
                      <span className="w-5 h-5 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs flex-shrink-0">
                        {sidx + 1}
                      </span>
                      {step}
                    </div>
                  ))}
                </div>
              )}
              
              <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                <span>⏱️ {action.estimated_time}</span>
                <span>📁 {action.category}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">📋 Plan de Acțiune</h2>
          <p className="text-gray-400">
            {plan.total_actions} acțiuni identificate pentru îmbunătățirea poziționării
          </p>
        </div>
        <div className="text-sm text-gray-500">
          Scor curent: <span className="text-purple-400 font-bold">{plan.positioning_score}/100</span>
        </div>
      </div>
      
      {renderActions('quick_wins')}
      {renderActions('medium_term')}
      {renderActions('long_term')}
    </div>
  );
};

// AI Coach View
const AICoachView = ({ agentId }) => {
  const [checkin, setCheckin] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [question, setQuestion] = React.useState('');
  const [chatHistory, setChatHistory] = React.useState([]);
  
  React.useEffect(() => {
    const fetchCheckin = async () => {
      try {
        const response = await fetch(`/api/agents/${agentId}/business-intelligence/coach/weekly-checkin`);
        const data = await response.json();
        setCheckin(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchCheckin();
  }, [agentId]);
  
  const askCoach = async () => {
    if (!question.trim()) return;
    
    setChatHistory(prev => [...prev, { type: 'user', text: question }]);
    setQuestion('');
    
    try {
      const response = await fetch(`/api/agents/${agentId}/business-intelligence/coach/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await response.json();
      setChatHistory(prev => [...prev, { type: 'coach', text: data.answer }]);
    } catch (err) {
      console.error(err);
    }
  };
  
  if (loading) return <div className="text-center py-12">Se încarcă...</div>;
  
  return (
    <div className="space-y-6">
      {/* Weekly Check-in */}
      {checkin && (
        <div className={`rounded-2xl p-6 border ${
          checkin.mood === 'celebration' ? 'bg-green-500/10 border-green-500/30' :
          checkin.mood === 'positive' ? 'bg-blue-500/10 border-blue-500/30' :
          checkin.mood === 'concern' ? 'bg-yellow-500/10 border-yellow-500/30' :
          'bg-gray-800/50 border-white/10'
        }`}>
          <h3 className="text-xl font-bold text-white mb-4">🤖 Check-in Săptămânal</h3>
          <p className="text-lg text-gray-200 mb-4">{checkin.message}</p>
          
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className="text-3xl font-bold text-purple-400">{checkin.current_score}</div>
              <div className="text-xs text-gray-400">Scor Curent</div>
            </div>
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className={`text-3xl font-bold ${checkin.score_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {checkin.score_change >= 0 ? '+' : ''}{checkin.score_change}
              </div>
              <div className="text-xs text-gray-400">Schimbare</div>
            </div>
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className="text-3xl font-bold text-blue-400">#{checkin.ranking}</div>
              <div className="text-xs text-gray-400">Poziție</div>
            </div>
          </div>
          
          {checkin.suggestions_for_week && (
            <div>
              <h4 className="font-medium text-white mb-3">📌 Sugestii pentru săptămâna aceasta:</h4>
              <div className="space-y-2">
                {checkin.suggestions_for_week.map((sug, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      sug.impact === 'HIGH' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {sug.impact}
                    </span>
                    <span className="text-gray-300">{sug.action}</span>
                    <span className="text-gray-500 text-sm ml-auto">⏱️ {sug.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {checkin.motivational_tip && (
            <div className="mt-6 p-4 bg-purple-500/10 rounded-xl border border-purple-500/30">
              <p className="text-purple-300 italic">💡 {checkin.motivational_tip}</p>
            </div>
          )}
        </div>
      )}
      
      {/* Chat with Coach */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-xl font-bold text-white mb-4">💬 Întreabă Coach-ul AI</h3>
        
        {chatHistory.length > 0 && (
          <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-xl ${
                  msg.type === 'user' 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-700 text-gray-200'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
          </div>
        )}
        
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && askCoach()}
            placeholder="Întreabă orice despre afacerea ta..."
            className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
          />
          <button
            onClick={askCoach}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors"
          >
            Trimite
          </button>
        </div>
      </div>
    </div>
  );
};

// Alerts View
const AlertsView = ({ agentId }) => {
  const [alerts, setAlerts] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  
  React.useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch(`/api/agents/${agentId}/business-intelligence/alerts`);
        const data = await response.json();
        setAlerts(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, [agentId]);
  
  if (loading) return <div className="text-center py-12">Se încarcă...</div>;
  
  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-500/10 border-red-500/50 text-red-400';
      case 'WARNING': return 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400';
      default: return 'bg-blue-500/10 border-blue-500/50 text-blue-400';
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">🚨 Alerte Competitori</h2>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm">
            {alerts?.by_severity?.critical || 0} Critice
          </span>
          <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-sm">
            {alerts?.by_severity?.warning || 0} Atenționări
          </span>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm">
            {alerts?.by_severity?.info || 0} Info
          </span>
        </div>
      </div>
      
      {alerts?.alerts?.length > 0 ? (
        <div className="space-y-4">
          {alerts.alerts.map((alert, idx) => (
            <div key={idx} className={`rounded-xl p-5 border ${getSeverityStyle(alert.severity)}`}>
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-white">{alert.title}</h4>
                <span className="text-xs opacity-70">{alert.severity}</span>
              </div>
              <p className="text-gray-300 mb-3">{alert.message}</p>
              {alert.action && (
                <div className="text-sm opacity-80">
                  💡 <span className="italic">{alert.action}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-800/50 rounded-2xl">
          <div className="text-6xl mb-4">✅</div>
          <h3 className="text-xl font-medium text-white">Nicio alertă activă</h3>
          <p className="text-gray-400 mt-2">Totul arată bine! Continuă să monitorizezi.</p>
        </div>
      )}
    </div>
  );
};

// Compare View
const CompareView = ({ agentId }) => {
  const [competitors, setCompetitors] = React.useState([]);
  const [selectedCompetitor, setSelectedCompetitor] = React.useState(null);
  const [comparison, setComparison] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  
  React.useEffect(() => {
    const fetchCompetitors = async () => {
      try {
        const response = await fetch(`/api/agents/${agentId}/business-intelligence/positioning-score`);
        const data = await response.json();
        setCompetitors(data.comparison_with_top?.top_competitors || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchCompetitors();
  }, [agentId]);
  
  const compareWith = async (domain) => {
    setSelectedCompetitor(domain);
    try {
      const response = await fetch(`/api/agents/${agentId}/business-intelligence/competitor-comparison/${domain}`);
      const data = await response.json();
      setComparison(data);
    } catch (err) {
      console.error(err);
    }
  };
  
  if (loading) return <div className="text-center py-12">Se încarcă...</div>;
  
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">⚔️ Comparații Directe</h2>
      
      {/* Competitor Selection */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <h3 className="font-medium text-white mb-4">Selectează un competitor pentru comparație:</h3>
        <div className="flex flex-wrap gap-3">
          {competitors.map((comp, idx) => (
            <button
              key={idx}
              onClick={() => compareWith(comp.domain)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                selectedCompetitor === comp.domain
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {comp.domain}
            </button>
          ))}
        </div>
      </div>
      
      {/* Comparison Results */}
      {comparison && (
        <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
          <h3 className="text-xl font-bold text-white mb-6">
            Tu vs {comparison.comparison?.competitor?.domain}
          </h3>
          
          {/* Verdict */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-4 bg-green-500/10 rounded-xl">
              <div className="text-3xl font-bold text-green-400">{comparison.verdict?.wins}</div>
              <div className="text-sm text-gray-400">Câștiguri</div>
            </div>
            <div className="text-center p-4 bg-gray-700/50 rounded-xl">
              <div className="text-3xl font-bold text-gray-400">{comparison.verdict?.ties}</div>
              <div className="text-sm text-gray-400">Egaluri</div>
            </div>
            <div className="text-center p-4 bg-red-500/10 rounded-xl">
              <div className="text-3xl font-bold text-red-400">{comparison.verdict?.losses}</div>
              <div className="text-sm text-gray-400">Pierderi</div>
            </div>
          </div>
          
          {/* Metrics Comparison */}
          <div className="space-y-3">
            {comparison.differences && Object.entries(comparison.differences).map(([metric, data]) => (
              <div key={metric} className="flex items-center gap-4 p-3 bg-gray-700/50 rounded-lg">
                <span className="w-24 text-gray-400 capitalize">{metric}</span>
                <span className="font-medium text-white">{comparison.comparison?.you?.[metric]}</span>
                <span className="text-2xl">{data.label}</span>
                <span className="text-gray-400">{comparison.comparison?.competitor?.[metric]}</span>
                <span className={`ml-auto text-sm ${data.difference > 0 ? 'text-green-400' : data.difference < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                  {data.difference > 0 ? '+' : ''}{data.difference} ({data.percent}%)
                </span>
              </div>
            ))}
          </div>
          
          {/* Keywords Analysis */}
          {comparison.keywords_analysis && (
            <div className="mt-6 grid grid-cols-3 gap-4">
              <div className="p-4 bg-green-500/10 rounded-xl">
                <h4 className="font-medium text-green-400 mb-2">Doar tu ai</h4>
                <div className="text-sm text-gray-300">
                  {comparison.keywords_analysis.only_you_have?.slice(0, 5).join(', ') || 'Niciun keyword unic'}
                </div>
              </div>
              <div className="p-4 bg-red-500/10 rounded-xl">
                <h4 className="font-medium text-red-400 mb-2">Doar competitorul are</h4>
                <div className="text-sm text-gray-300">
                  {comparison.keywords_analysis.only_competitor_has?.slice(0, 5).join(', ') || 'Niciun keyword'}
                </div>
              </div>
              <div className="p-4 bg-blue-500/10 rounded-xl">
                <h4 className="font-medium text-blue-400 mb-2">Aveți amândoi</h4>
                <div className="text-sm text-gray-300">
                  {comparison.keywords_analysis.both_have?.slice(0, 5).join(', ') || 'Niciun keyword comun'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BusinessIntelligencePage;

