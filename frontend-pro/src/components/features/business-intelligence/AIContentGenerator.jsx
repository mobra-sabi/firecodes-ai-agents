// AIContentGenerator.jsx
// 🤖 Generator de conținut AI
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '@/services/api';
import { Sparkles, FileText, Type, ListOrdered, Lightbulb, Loader2, Copy, Check } from 'lucide-react';

const AIContentGenerator = () => {
  const { agentId } = useParams();
  const [activeTab, setActiveTab] = useState('titles');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [copied, setCopied] = useState(null);
  
  // Form states
  const [keyword, setKeyword] = useState('');
  const [title, setTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [targetWords, setTargetWords] = useState(1500);
  
  const generateTitles = async () => {
    if (!keyword.trim()) return;
    setLoading(true);
    try {
      const response = await api.post(`/api/agents/${agentId}/business-intelligence/content/titles`, {
        keyword,
        count: 5
      });
      setResults({ type: 'titles', data: response.data });
    } catch (err) {
      console.error('Error generating titles:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const generateMetaDescription = async () => {
    if (!title.trim() || !keyword.trim()) return;
    setLoading(true);
    try {
      const response = await api.post(`/api/agents/${agentId}/business-intelligence/content/meta-description`, {
        title,
        keyword
      });
      setResults({ type: 'meta', data: response.data });
    } catch (err) {
      console.error('Error generating meta description:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const generateOutline = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const response = await api.post(`/api/agents/${agentId}/business-intelligence/content/outline`, {
        topic,
        target_words: targetWords
      });
      setResults({ type: 'outline', data: response.data });
    } catch (err) {
      console.error('Error generating outline:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const generateIdeas = async () => {
    setLoading(true);
    try {
      const response = await api.post(`/api/agents/${agentId}/business-intelligence/content/ideas?count=10`);
      setResults({ type: 'ideas', data: response.data });
    } catch (err) {
      console.error('Error generating ideas:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };
  
  const tabs = [
    { id: 'titles', label: 'Titluri SEO', icon: Type },
    { id: 'meta', label: 'Meta Description', icon: FileText },
    { id: 'outline', label: 'Outline Articol', icon: ListOrdered },
    { id: 'ideas', label: 'Idei Conținut', icon: Lightbulb }
  ];
  
  return (
    <div className="bg-gray-800/50 rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-6">
        <Sparkles className="w-5 h-5 text-yellow-400" />
        Generator Conținut AI
      </h3>
      
      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setResults(null); }}
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
      
      {/* Titles Generator */}
      {activeTab === 'titles' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Keyword Principal</label>
            <div className="flex gap-2 mt-1">
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="ex: amenajări interioare București"
                className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400"
              />
              <button
                onClick={generateTitles}
                disabled={loading || !keyword.trim()}
                className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generează
              </button>
            </div>
          </div>
          
          {results?.type === 'titles' && results.data?.titles && (
            <div className="space-y-2">
              <p className="text-sm text-gray-400">Titluri generate pentru "{results.data.keyword}":</p>
              {results.data.titles.map((t, i) => (
                <div key={i} className="flex items-center gap-2 p-3 bg-gray-700/50 rounded-lg">
                  <span className="flex-1 text-white">{t}</span>
                  <button
                    onClick={() => copyToClipboard(t, `title-${i}`)}
                    className="p-2 hover:bg-gray-600 rounded"
                  >
                    {copied === `title-${i}` ? (
                      <Check className="w-4 h-4 text-green-400" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Meta Description Generator */}
      {activeTab === 'meta' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Titlu Pagină</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ex: Amenajări Interioare București - Servicii Premium"
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400">Keyword Principal</label>
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="ex: amenajări interioare București"
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400"
            />
          </div>
          <button
            onClick={generateMetaDescription}
            disabled={loading || !title.trim() || !keyword.trim()}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generează Meta Description
          </button>
          
          {results?.type === 'meta' && results.data?.meta_description && (
            <div className="p-4 bg-gray-700/50 rounded-lg">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm text-gray-400 mb-2">Meta Description ({results.data.meta_description.length} caractere):</p>
                  <p className="text-white">{results.data.meta_description}</p>
                </div>
                <button
                  onClick={() => copyToClipboard(results.data.meta_description, 'meta')}
                  className="p-2 hover:bg-gray-600 rounded flex-shrink-0"
                >
                  {copied === 'meta' ? (
                    <Check className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-400" />
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Outline Generator */}
      {activeTab === 'outline' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400">Topic Articol</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="ex: Ghid complet pentru renovarea apartamentului"
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400">Lungime Țintă (cuvinte)</label>
            <select
              value={targetWords}
              onChange={(e) => setTargetWords(Number(e.target.value))}
              className="w-full mt-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
            >
              <option value={800}>800 cuvinte (articol scurt)</option>
              <option value={1500}>1500 cuvinte (articol mediu)</option>
              <option value={2500}>2500 cuvinte (articol lung)</option>
              <option value={4000}>4000+ cuvinte (ghid comprehensiv)</option>
            </select>
          </div>
          <button
            onClick={generateOutline}
            disabled={loading || !topic.trim()}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generează Outline
          </button>
          
          {results?.type === 'outline' && results.data?.outline && (
            <div className="p-4 bg-gray-700/50 rounded-lg space-y-4">
              {results.data.outline.h1 && (
                <div>
                  <p className="text-sm text-gray-400">H1:</p>
                  <p className="text-xl font-bold text-white">{results.data.outline.h1}</p>
                </div>
              )}
              {results.data.outline.intro_hook && (
                <div>
                  <p className="text-sm text-gray-400">Introducere:</p>
                  <p className="text-gray-300">{results.data.outline.intro_hook}</p>
                </div>
              )}
              {results.data.outline.sections && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-400">Secțiuni:</p>
                  {results.data.outline.sections.map((section, i) => (
                    <div key={i} className="p-3 bg-gray-600/50 rounded-lg">
                      <p className="font-medium text-white">H2: {section.h2}</p>
                      {section.key_points && (
                        <ul className="mt-2 space-y-1">
                          {section.key_points.map((point, j) => (
                            <li key={j} className="text-sm text-gray-300 flex items-start gap-2">
                              <span className="text-purple-400">•</span>
                              {point}
                            </li>
                          ))}
                        </ul>
                      )}
                      {section.image_suggestion && (
                        <p className="text-xs text-gray-500 mt-2">📷 {section.image_suggestion}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {results.data.outline.conclusion_cta && (
                <div>
                  <p className="text-sm text-gray-400">Concluzie CTA:</p>
                  <p className="text-gray-300">{results.data.outline.conclusion_cta}</p>
                </div>
              )}
              {results.data.outline.raw_outline && (
                <div>
                  <p className="text-sm text-gray-400">Outline:</p>
                  <pre className="text-gray-300 whitespace-pre-wrap text-sm">{results.data.outline.raw_outline}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Ideas Generator */}
      {activeTab === 'ideas' && (
        <div className="space-y-4">
          <p className="text-gray-400">Generează idei de conținut bazate pe gap-urile identificate în analiza competitivă.</p>
          <button
            onClick={generateIdeas}
            disabled={loading}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4" />}
            Generează Idei
          </button>
          
          {results?.type === 'ideas' && results.data?.ideas && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400">
                {results.data.ideas.length} idei generate (bazate pe {results.data.based_on_gaps} gaps):
              </p>
              {results.data.ideas.map((idea, i) => (
                <div key={i} className="p-4 bg-gray-700/50 rounded-lg">
                  <div className="flex items-start justify-between">
                    <h4 className="font-medium text-white">{idea.title}</h4>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      idea.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                      idea.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {idea.priority}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="text-xs bg-gray-600 px-2 py-1 rounded text-gray-300">
                      {idea.type}
                    </span>
                    {idea.keywords?.map((kw, j) => (
                      <span key={j} className="text-xs bg-purple-500/20 px-2 py-1 rounded text-purple-300">
                        {kw}
                      </span>
                    ))}
                    {idea.effort_hours && (
                      <span className="text-xs text-gray-500">⏱️ {idea.effort_hours}h</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIContentGenerator;

