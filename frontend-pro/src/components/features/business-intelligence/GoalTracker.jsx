// GoalTracker.jsx
// 🎯 Sistem de obiective
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { Target, Plus, CheckCircle, Clock, AlertTriangle, Trophy } from 'lucide-react';

const GoalTracker = () => {
  const { agentId } = useParams();
  const [goals, setGoals] = useState([]);
  const [goalTypes, setGoalTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newGoal, setNewGoal] = useState({
    goal_type: 'score',
    target_value: 70,
    deadline_days: 30,
    notes: ''
  });
  
  const fetchGoals = async () => {
    try {
      const response = await api.get(`/api/agents/${agentId}/business-intelligence/goals`);
      setGoals(response.data.goals || []);
      setGoalTypes(response.data.goal_types || {});
    } catch (err) {
      console.error('Error fetching goals:', err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchGoals();
  }, [agentId]);
  
  const createGoal = async () => {
    try {
      await api.post(`/api/agents/${agentId}/business-intelligence/goals`, newGoal);
      setShowForm(false);
      setNewGoal({ goal_type: 'score', target_value: 70, deadline_days: 30, notes: '' });
      fetchGoals();
    } catch (err) {
      console.error('Error creating goal:', err);
    }
  };
  
  const completeGoal = async (goalId) => {
    try {
      await api.put(`/api/agents/${agentId}/business-intelligence/goals/${goalId}/complete`);
      fetchGoals();
    } catch (err) {
      console.error('Error completing goal:', err);
    }
  };
  
  const getProgressColor = (percent, isOverdue) => {
    if (isOverdue) return 'bg-red-500';
    if (percent >= 100) return 'bg-green-500';
    if (percent >= 50) return 'bg-blue-500';
    return 'bg-yellow-500';
  };
  
  if (loading) {
    return <div className="animate-pulse h-64 bg-gray-800/50 rounded-2xl"></div>;
  }
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Target className="w-5 h-5 text-purple-400" />
          Obiective
        </h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          Obiectiv Nou
        </button>
      </div>
      
      {/* Form pentru obiectiv nou */}
      {showForm && (
        <div className="mb-6 p-4 bg-gray-700/50 rounded-xl">
          <h4 className="font-medium text-white mb-4">Setează un obiectiv nou</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400">Tip Obiectiv</label>
              <select
                value={newGoal.goal_type}
                onChange={(e) => setNewGoal({ ...newGoal, goal_type: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white"
              >
                {Object.entries(goalTypes).map(([key, val]) => (
                  <option key={key} value={key}>{val.icon} {val.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-400">Valoare Țintă</label>
              <input
                type="number"
                value={newGoal.target_value}
                onChange={(e) => setNewGoal({ ...newGoal, target_value: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400">Deadline (zile)</label>
              <select
                value={newGoal.deadline_days}
                onChange={(e) => setNewGoal({ ...newGoal, deadline_days: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white"
              >
                <option value={7}>1 săptămână</option>
                <option value={14}>2 săptămâni</option>
                <option value={30}>1 lună</option>
                <option value={60}>2 luni</option>
                <option value={90}>3 luni</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-400">Note (opțional)</label>
              <input
                type="text"
                value={newGoal.notes}
                onChange={(e) => setNewGoal({ ...newGoal, notes: e.target.value })}
                placeholder="De ce acest obiectiv?"
                className="w-full mt-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={createGoal}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
            >
              Creează Obiectiv
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg"
            >
              Anulează
            </button>
          </div>
        </div>
      )}
      
      {/* Lista obiective */}
      {goals.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <Trophy className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nu ai obiective setate încă.</p>
          <p className="text-sm mt-1">Setează primul obiectiv pentru a-ți urmări progresul!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {goals.map((goal) => (
            <div
              key={goal._id}
              className={`p-4 rounded-xl border ${
                goal.is_completed ? 'bg-green-500/10 border-green-500/30' :
                goal.is_overdue ? 'bg-red-500/10 border-red-500/30' :
                'bg-gray-700/50 border-gray-600'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{goal.type_info?.icon}</span>
                  <div>
                    <h4 className="font-medium text-white">{goal.type_info?.label}</h4>
                    <p className="text-sm text-gray-400">
                      {goal.current_value} / {goal.target_value} {goal.type_info?.unit}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {goal.is_completed ? (
                    <span className="flex items-center gap-1 text-green-400">
                      <CheckCircle className="w-4 h-4" />
                      Completat!
                    </span>
                  ) : goal.is_overdue ? (
                    <span className="flex items-center gap-1 text-red-400">
                      <AlertTriangle className="w-4 h-4" />
                      Expirat
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-gray-400">
                      <Clock className="w-4 h-4" />
                      {goal.days_remaining} zile rămase
                    </span>
                  )}
                </div>
              </div>
              
              {/* Progress bar */}
              <div className="mt-3">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Progres</span>
                  <span className="text-white">{goal.progress_percent}%</span>
                </div>
                <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getProgressColor(goal.progress_percent, goal.is_overdue)} transition-all`}
                    style={{ width: `${Math.min(100, goal.progress_percent)}%` }}
                  />
                </div>
              </div>
              
              {goal.notes && (
                <p className="text-sm text-gray-400 mt-2 italic">"{goal.notes}"</p>
              )}
              
              {!goal.is_completed && goal.progress_percent >= 100 && (
                <button
                  onClick={() => completeGoal(goal._id)}
                  className="mt-3 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
                >
                  🎉 Marchează ca Completat
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GoalTracker;

