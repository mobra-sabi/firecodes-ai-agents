// ActionChecklist.jsx
// ✅ Checklist interactiv pentru acțiuni
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { CheckSquare, Square, RefreshCw, Plus, Clock, Zap, Target, ChevronDown, ChevronUp } from 'lucide-react';

const ActionChecklist = () => {
  const { agentId } = useParams();
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedItems, setExpandedItems] = useState({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItem, setNewItem] = useState({ title: '', description: '', priority: 'medium' });
  
  const fetchChecklist = async () => {
    try {
      const response = await api.get(`/api/agents/${agentId}/business-intelligence/checklist`);
      setChecklist(response.data);
    } catch (err) {
      console.error('Error fetching checklist:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const generateChecklist = async () => {
    setGenerating(true);
    try {
      await api.post(`/api/agents/${agentId}/business-intelligence/checklist/generate`);
      fetchChecklist();
    } catch (err) {
      console.error('Error generating checklist:', err);
    } finally {
      setGenerating(false);
    }
  };
  
  const toggleItem = async (itemId) => {
    try {
      await api.put(`/api/agents/${agentId}/business-intelligence/checklist/${itemId}/toggle`);
      fetchChecklist();
    } catch (err) {
      console.error('Error toggling item:', err);
    }
  };
  
  const addItem = async () => {
    if (!newItem.title.trim()) return;
    try {
      await api.post(`/api/agents/${agentId}/business-intelligence/checklist/item`, newItem);
      setNewItem({ title: '', description: '', priority: 'medium' });
      setShowAddForm(false);
      fetchChecklist();
    } catch (err) {
      console.error('Error adding item:', err);
    }
  };
  
  useEffect(() => {
    fetchChecklist();
  }, [agentId]);
  
  const getCategoryIcon = (category) => {
    switch (category) {
      case 'quick_win': return <Zap className="w-4 h-4 text-yellow-400" />;
      case 'medium_term': return <Clock className="w-4 h-4 text-blue-400" />;
      case 'long_term': return <Target className="w-4 h-4 text-purple-400" />;
      default: return <CheckSquare className="w-4 h-4 text-gray-400" />;
    }
  };
  
  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high': return 'bg-red-500/20 text-red-400';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400';
      case 'low': return 'bg-green-500/20 text-green-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };
  
  if (loading) {
    return <div className="animate-pulse h-64 bg-gray-800/50 rounded-2xl"></div>;
  }
  
  const items = checklist?.items || [];
  const completedCount = items.filter(i => i.completed).length;
  const progressPercent = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <CheckSquare className="w-5 h-5 text-green-400" />
          Plan de Acțiune
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2 text-sm"
          >
            <Plus className="w-4 h-4" />
            Adaugă
          </button>
          <button
            onClick={generateChecklist}
            disabled={generating}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 text-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
            {generating ? 'Generez...' : 'Regenerează'}
          </button>
        </div>
      </div>
      
      {/* Progress Overview */}
      <div className="mb-6 p-4 bg-gray-700/50 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-400">Progres Total</span>
          <span className="text-white font-bold">{completedCount}/{items.length} completate</span>
        </div>
        <div className="h-3 bg-gray-600 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-center text-2xl font-bold text-white mt-2">{progressPercent}%</p>
        {progressPercent === 100 && (
          <p className="text-center text-green-400 mt-2">🎉 Felicitări! Ai completat toate acțiunile!</p>
        )}
      </div>
      
      {/* Add Item Form */}
      {showAddForm && (
        <div className="mb-4 p-4 bg-gray-700/50 rounded-xl">
          <input
            type="text"
            value={newItem.title}
            onChange={(e) => setNewItem({ ...newItem, title: e.target.value })}
            placeholder="Titlu acțiune..."
            className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400 mb-2"
          />
          <div className="flex gap-2">
            <input
              type="text"
              value={newItem.description}
              onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
              placeholder="Descriere (opțional)"
              className="flex-1 px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400"
            />
            <select
              value={newItem.priority}
              onChange={(e) => setNewItem({ ...newItem, priority: e.target.value })}
              className="px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white"
            >
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <button
              onClick={addItem}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
            >
              Adaugă
            </button>
          </div>
        </div>
      )}
      
      {/* Checklist Items */}
      {items.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <CheckSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nu ai acțiuni în checklist.</p>
          <button
            onClick={generateChecklist}
            className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
          >
            Generează din Plan
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border transition-all ${
                item.completed 
                  ? 'bg-green-500/10 border-green-500/30' 
                  : 'bg-gray-700/50 border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="flex items-start gap-3">
                <button
                  onClick={() => toggleItem(item.id)}
                  className="mt-1 flex-shrink-0"
                >
                  {item.completed ? (
                    <CheckSquare className="w-5 h-5 text-green-400" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400 hover:text-white" />
                  )}
                </button>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getCategoryIcon(item.category)}
                    <span className={`font-medium ${item.completed ? 'text-gray-400 line-through' : 'text-white'}`}>
                      {item.title}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs ${getPriorityBadge(item.priority)}`}>
                      {item.priority}
                    </span>
                  </div>
                  
                  {item.description && (
                    <p className="text-sm text-gray-400 mt-1">{item.description}</p>
                  )}
                  
                  {item.estimated_time && (
                    <span className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                      <Clock className="w-3 h-3" />
                      {item.estimated_time}
                    </span>
                  )}
                </div>
                
                {item.steps && item.steps.length > 0 && (
                  <button
                    onClick={() => setExpandedItems({ ...expandedItems, [item.id]: !expandedItems[item.id] })}
                    className="p-1 hover:bg-gray-600 rounded"
                  >
                    {expandedItems[item.id] ? (
                      <ChevronUp className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                )}
              </div>
              
              {/* Expanded Steps */}
              {expandedItems[item.id] && item.steps && (
                <div className="mt-3 pl-8 space-y-1">
                  {item.steps.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-gray-400">
                      <span className="w-5 h-5 bg-gray-600 rounded-full flex items-center justify-center text-xs flex-shrink-0">
                        {idx + 1}
                      </span>
                      {step}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActionChecklist;

