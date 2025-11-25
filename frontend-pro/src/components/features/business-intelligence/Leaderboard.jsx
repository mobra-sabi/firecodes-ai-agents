// Leaderboard.jsx
// 🏆 Leaderboard competitori
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { Trophy, Crown, Medal, Star, Eye, Plus, X, RefreshCw } from 'lucide-react';

const Leaderboard = () => {
  const { agentId } = useParams();
  const [leaderboard, setLeaderboard] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yourPosition, setYourPosition] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newWatchDomain, setNewWatchDomain] = useState('');
  
  const fetchData = async () => {
    try {
      const [lbResponse, wlResponse] = await Promise.all([
        api.get(`/api/agents/${agentId}/business-intelligence/leaderboard`),
        api.get(`/api/agents/${agentId}/business-intelligence/watchlist`)
      ]);
      setLeaderboard(lbResponse.data.leaderboard || []);
      setYourPosition(lbResponse.data.your_position);
      setWatchlist(wlResponse.data.watchlist || []);
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const addToWatchlist = async () => {
    if (!newWatchDomain.trim()) return;
    try {
      await api.post(`/api/agents/${agentId}/business-intelligence/watchlist`, {
        competitor_domain: newWatchDomain,
        notes: ''
      });
      setNewWatchDomain('');
      setShowAddForm(false);
      fetchData();
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      alert(err.response?.data?.detail || 'Eroare la adăugare');
    }
  };
  
  const removeFromWatchlist = async (domain) => {
    try {
      await api.delete(`/api/agents/${agentId}/business-intelligence/watchlist/${domain}`);
      fetchData();
    } catch (err) {
      console.error('Error removing from watchlist:', err);
    }
  };
  
  useEffect(() => {
    fetchData();
  }, [agentId]);
  
  const getPositionIcon = (position) => {
    switch (position) {
      case 1: return <Crown className="w-5 h-5 text-yellow-400" />;
      case 2: return <Medal className="w-5 h-5 text-gray-300" />;
      case 3: return <Medal className="w-5 h-5 text-amber-600" />;
      default: return <span className="w-5 text-center text-gray-400">{position}</span>;
    }
  };
  
  if (loading) {
    return <div className="animate-pulse h-64 bg-gray-800/50 rounded-2xl"></div>;
  }
  
  return (
    <div className="space-y-6">
      {/* Leaderboard */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            Leaderboard Competitori
          </h3>
          <button
            onClick={fetchData}
            className="p-2 hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
        </div>
        
        {/* Your Position Highlight */}
        {yourPosition && (
          <div className="mb-4 p-4 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-xl border border-purple-500/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Star className="w-6 h-6 text-purple-400" />
                <span className="text-white">Poziția ta în clasament</span>
              </div>
              <span className="text-3xl font-bold text-purple-400">#{yourPosition}</span>
            </div>
          </div>
        )}
        
        {/* Leaderboard Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                <th className="pb-3 w-12">#</th>
                <th className="pb-3">Domeniu</th>
                <th className="pb-3 text-center">Scor</th>
                <th className="pb-3 text-center">Pagini</th>
                <th className="pb-3 text-center">Keywords</th>
                <th className="pb-3 text-center">Chunks</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.slice(0, 15).map((entry) => (
                <tr
                  key={entry.domain}
                  className={`border-b border-gray-700/50 ${
                    entry.is_you ? 'bg-purple-500/10' : 'hover:bg-gray-700/30'
                  }`}
                >
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      {getPositionIcon(entry.position)}
                      {entry.medal}
                    </div>
                  </td>
                  <td className="py-3">
                    <span className={`${entry.is_you ? 'text-purple-400 font-bold' : 'text-white'}`}>
                      {entry.domain}
                      {entry.is_you && <span className="ml-2 text-xs">(TU)</span>}
                    </span>
                  </td>
                  <td className="py-3 text-center">
                    <span className={`font-bold ${
                      entry.score >= 70 ? 'text-green-400' :
                      entry.score >= 40 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {entry.score}
                    </span>
                  </td>
                  <td className="py-3 text-center text-gray-300">{entry.pages}</td>
                  <td className="py-3 text-center text-gray-300">{entry.keywords}</td>
                  <td className="py-3 text-center text-gray-300">{entry.chunks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Watchlist */}
      <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Eye className="w-5 h-5 text-blue-400" />
            Watchlist ({watchlist.length})
          </h3>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 text-sm"
          >
            <Plus className="w-4 h-4" />
            Adaugă
          </button>
        </div>
        
        {showAddForm && (
          <div className="mb-4 p-4 bg-gray-700/50 rounded-xl">
            <div className="flex gap-2">
              <input
                type="text"
                value={newWatchDomain}
                onChange={(e) => setNewWatchDomain(e.target.value)}
                placeholder="Domeniu competitor (ex: competitor.ro)"
                className="flex-1 px-4 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white placeholder-gray-400"
              />
              <button
                onClick={addToWatchlist}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
              >
                Adaugă
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg"
              >
                Anulează
              </button>
            </div>
          </div>
        )}
        
        {watchlist.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Nu ai competitori în watchlist.</p>
            <p className="text-sm mt-1">Adaugă competitori pentru a-i urmări îndeaproape.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {watchlist.map((item) => (
              <div key={item.domain} className="p-4 bg-gray-700/50 rounded-xl">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-white">{item.domain}</h4>
                    <p className="text-sm text-gray-400">
                      Adăugat: {new Date(item.added_at).toLocaleDateString('ro-RO')}
                    </p>
                  </div>
                  <button
                    onClick={() => removeFromWatchlist(item.domain)}
                    className="p-2 hover:bg-red-500/20 rounded-lg"
                  >
                    <X className="w-4 h-4 text-red-400" />
                  </button>
                </div>
                
                {item.current && (
                  <div className="grid grid-cols-3 gap-4 mt-3">
                    <div className="text-center p-2 bg-gray-600/50 rounded-lg">
                      <p className="text-xs text-gray-400">Pagini</p>
                      <p className="font-bold text-white">{item.current.pages}</p>
                      {item.changes?.pages !== 0 && (
                        <p className={`text-xs ${item.changes?.pages > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {item.changes?.pages > 0 ? '+' : ''}{item.changes?.pages}
                        </p>
                      )}
                    </div>
                    <div className="text-center p-2 bg-gray-600/50 rounded-lg">
                      <p className="text-xs text-gray-400">Keywords</p>
                      <p className="font-bold text-white">{item.current.keywords}</p>
                      {item.changes?.keywords !== 0 && (
                        <p className={`text-xs ${item.changes?.keywords > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {item.changes?.keywords > 0 ? '+' : ''}{item.changes?.keywords}
                        </p>
                      )}
                    </div>
                    <div className="text-center p-2 bg-gray-600/50 rounded-lg">
                      <p className="text-xs text-gray-400">Chunks</p>
                      <p className="font-bold text-white">{item.current.chunks}</p>
                      {item.changes?.chunks !== 0 && (
                        <p className={`text-xs ${item.changes?.chunks > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {item.changes?.chunks > 0 ? '+' : ''}{item.changes?.chunks}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Leaderboard;

