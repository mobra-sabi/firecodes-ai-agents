// DiscoveryWizard.jsx
// 🧙 Business Discovery Wizard - Întrebări pentru personalizare
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { 
  ChevronRight, ChevronLeft, CheckCircle, 
  Sparkles, Target, Users, DollarSign, Clock,
  Briefcase, TrendingUp, AlertCircle
} from 'lucide-react';

const questionIcons = {
  business_type: Briefcase,
  employees: Users,
  monthly_budget: DollarSign,
  main_goal: Target,
  available_resources: Sparkles,
  timeline: Clock,
  biggest_challenge: AlertCircle,
  current_marketing: TrendingUp
};

const DiscoveryWizard = ({ onComplete }) => {
  const { agentId } = useParams();
  const [questions, setQuestions] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  
  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const response = await api.get(`/api/agents/${agentId}/business-intelligence/discovery-wizard`);
        setQuestions(response.data.questions || []);
      } catch (err) {
        console.error('Error fetching questions:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchQuestions();
  }, [agentId]);
  
  const handleAnswer = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };
  
  const handleMultiSelect = (questionId, value) => {
    setAnswers(prev => {
      const current = prev[questionId] || [];
      if (current.includes(value)) {
        return { ...prev, [questionId]: current.filter(v => v !== value) };
      }
      return { ...prev, [questionId]: [...current, value] };
    });
  };
  
  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const response = await api.post(
        `/api/agents/${agentId}/business-intelligence/discovery-wizard/submit`,
        { answers }
      );
      setRecommendations(response.data);
      if (onComplete) onComplete(response.data);
    } catch (err) {
      console.error('Error submitting answers:', err);
    } finally {
      setSubmitting(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }
  
  // Show recommendations if submitted
  if (recommendations) {
    return (
      <div className="bg-gray-800/50 rounded-2xl p-8 border border-white/10">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-white">Recomandări Personalizate</h2>
          <p className="text-gray-400 mt-2">Bazate pe răspunsurile tale</p>
        </div>
        
        {/* Priority Focus */}
        {recommendations.priority_focus && recommendations.priority_focus.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-white mb-4">🎯 Focus Principal</h3>
            <div className="space-y-4">
              {recommendations.priority_focus.map((focus, idx) => (
                <div key={idx} className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                  <div className="font-medium text-purple-400">{focus.area}</div>
                  <div className="text-gray-300 mt-1">{focus.reason}</div>
                  <ul className="mt-3 space-y-1">
                    {focus.actions.map((action, aidx) => (
                      <li key={aidx} className="flex items-start gap-2 text-sm text-gray-400">
                        <ChevronRight className="w-4 h-4 mt-0.5 text-purple-400" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Recommendations */}
        {recommendations.recommendations && recommendations.recommendations.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-white mb-4">💡 Recomandări</h3>
            <div className="space-y-3">
              {recommendations.recommendations.map((rec, idx) => (
                <div key={idx} className="bg-gray-700/50 rounded-lg p-4">
                  <div className="text-gray-300">{rec.message}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Next Steps */}
        {recommendations.next_steps && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-white mb-4">📋 Următorii Pași</h3>
            <div className="space-y-2">
              {recommendations.next_steps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-3 text-gray-300">
                  <span className="w-6 h-6 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center text-sm">
                    {idx + 1}
                  </span>
                  {step}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Estimated Improvement */}
        {recommendations.estimated_improvement && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
            <div className="text-green-400 font-medium">Îmbunătățire Estimată</div>
            <div className="text-2xl font-bold text-white mt-1">
              {recommendations.estimated_improvement.if_implemented}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              în {recommendations.estimated_improvement.timeline}
            </div>
          </div>
        )}
        
        <button
          onClick={() => {
            setRecommendations(null);
            setCurrentStep(0);
            setAnswers({});
          }}
          className="mt-6 w-full py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
        >
          Refă Chestionarul
        </button>
      </div>
    );
  }
  
  const currentQuestion = questions[currentStep];
  const Icon = currentQuestion ? questionIcons[currentQuestion.id] || Target : Target;
  const progress = ((currentStep + 1) / questions.length) * 100;
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-8 border border-white/10">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>Întrebarea {currentStep + 1} din {questions.length}</span>
          <span>{Math.round(progress)}% completat</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      
      {currentQuestion && (
        <div className="min-h-[300px]">
          {/* Question */}
          <div className="flex items-start gap-4 mb-8">
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
              <Icon className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">{currentQuestion.question}</h3>
              {currentQuestion.type === 'multiselect' && (
                <p className="text-gray-400 text-sm mt-1">Poți selecta mai multe opțiuni</p>
              )}
            </div>
          </div>
          
          {/* Options */}
          <div className="space-y-3">
            {currentQuestion.options.map((option) => {
              const isSelected = currentQuestion.type === 'multiselect'
                ? (answers[currentQuestion.id] || []).includes(option.value)
                : answers[currentQuestion.id] === option.value;
              
              return (
                <button
                  key={option.value}
                  onClick={() => {
                    if (currentQuestion.type === 'multiselect') {
                      handleMultiSelect(currentQuestion.id, option.value);
                    } else {
                      handleAnswer(currentQuestion.id, option.value);
                    }
                  }}
                  className={`w-full p-4 rounded-xl border text-left transition-all ${
                    isSelected
                      ? 'bg-purple-500/20 border-purple-500 text-white'
                      : 'bg-gray-700/50 border-gray-600 text-gray-300 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      isSelected ? 'border-purple-500 bg-purple-500' : 'border-gray-500'
                    }`}>
                      {isSelected && <CheckCircle className="w-3 h-3 text-white" />}
                    </div>
                    {option.label}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
      
      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
          disabled={currentStep === 0}
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          Înapoi
        </button>
        
        {currentStep < questions.length - 1 ? (
          <button
            onClick={() => setCurrentStep(prev => prev + 1)}
            disabled={!answers[currentQuestion?.id]}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            Următoarea
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting || !answers[currentQuestion?.id]}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Se procesează...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Obține Recomandări
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default DiscoveryWizard;

