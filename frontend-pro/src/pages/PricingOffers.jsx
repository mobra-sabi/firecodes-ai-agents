import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  FileText, Plus, Search, Filter, Download, Copy, Trash2, 
  Edit, Eye, Send, CheckCircle, XCircle, Clock, Sparkles,
  Upload, Settings, BarChart3, Package, FileUp, Wand2
} from 'lucide-react';
import api from '../services/api';

// Componenta principală pentru Management Oferte
const PricingOffers = () => {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('offers');
  const [offers, setOffers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [clientSpace, setClientSpace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const effectiveClientId = clientId || 'default';

  useEffect(() => {
    loadData();
  }, [effectiveClientId, statusFilter, searchTerm]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [offersRes, templatesRes, catalogRes, statsRes, spaceRes] = await Promise.all([
        api.get(`/offers/${effectiveClientId}?status=${statusFilter}&search=${searchTerm}`),
        api.get(`/offers/${effectiveClientId}/templates`),
        api.get(`/offers/${effectiveClientId}/catalog`),
        api.get(`/offers/${effectiveClientId}/statistics`),
        api.get(`/offers/space/${effectiveClientId}`)
      ]);
      
      setOffers(offersRes.data.offers || []);
      setTemplates(templatesRes.data.templates || []);
      setCatalog(catalogRes.data.items || []);
      setStatistics(statsRes.data);
      setClientSpace(spaceRes.data.space);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-700',
      sent: 'bg-blue-100 text-blue-700',
      accepted: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
      expired: 'bg-yellow-100 text-yellow-700'
    };
    const labels = {
      draft: 'Ciornă',
      sent: 'Trimisă',
      accepted: 'Acceptată',
      rejected: 'Respinsă',
      expired: 'Expirată'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.draft}`}>
        {labels[status] || status}
      </span>
    );
  };

  const handleDeleteOffer = async (offerId) => {
    if (!confirm('Sigur vrei să ștergi această ofertă?')) return;
    try {
      await api.delete(`/offers/${effectiveClientId}/${offerId}`);
      loadData();
    } catch (error) {
      console.error('Error deleting offer:', error);
    }
  };

  const handleDuplicateOffer = async (offerId) => {
    try {
      const res = await api.post(`/offers/${effectiveClientId}/${offerId}/duplicate`);
      if (res.data.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error duplicating offer:', error);
    }
  };

  const handleExportOffer = async (offerId) => {
    try {
      window.open(`/api/offers/${effectiveClientId}/${offerId}/export?format=html`, '_blank');
    } catch (error) {
      console.error('Error exporting offer:', error);
    }
  };

  const tabs = [
    { id: 'offers', label: 'Oferte', icon: FileText },
    { id: 'templates', label: 'Template-uri', icon: Copy },
    { id: 'catalog', label: 'Catalog Articole', icon: Package },
    { id: 'statistics', label: 'Statistici', icon: BarChart3 },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            💼 Management Oferte de Preț
          </h1>
          <p className="text-slate-400 mt-1">
            Creează, gestionează și trimite oferte profesionale
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowSettingsModal(true)}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Setări
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button
            onClick={() => setShowAIModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-lg flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Generează cu AI
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-700 hover:to-cyan-700 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Ofertă Nouă
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      {statistics && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="text-2xl font-bold text-emerald-400">
              {statistics.statistics?.total_offers || 0}
            </div>
            <div className="text-slate-400 text-sm">Total Oferte</div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="text-2xl font-bold text-cyan-400">
              {(statistics.statistics?.total_value || 0).toLocaleString()} RON
            </div>
            <div className="text-slate-400 text-sm">Valoare Totală</div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="text-2xl font-bold text-green-400">
              {statistics.statistics?.accepted_offers || 0}
            </div>
            <div className="text-slate-400 text-sm">Acceptate</div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="text-2xl font-bold text-yellow-400">
              {statistics.statistics?.pending_offers || 0}
            </div>
            <div className="text-slate-400 text-sm">În Așteptare</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-700 pb-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
              activeTab === tab.id 
                ? 'bg-emerald-600 text-white' 
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'offers' && (
        <OffersTab 
          offers={offers}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          onDelete={handleDeleteOffer}
          onDuplicate={handleDuplicateOffer}
          onExport={handleExportOffer}
          clientId={effectiveClientId}
          navigate={navigate}
          getStatusBadge={getStatusBadge}
          loading={loading}
        />
      )}

      {activeTab === 'templates' && (
        <TemplatesTab 
          templates={templates}
          clientId={effectiveClientId}
          onRefresh={loadData}
        />
      )}

      {activeTab === 'catalog' && (
        <CatalogTab 
          catalog={catalog}
          clientId={effectiveClientId}
          onRefresh={loadData}
        />
      )}

      {activeTab === 'statistics' && (
        <StatisticsTab statistics={statistics} />
      )}

      {/* Modals */}
      {showCreateModal && (
        <CreateOfferModal 
          clientId={effectiveClientId}
          templates={templates}
          catalog={catalog}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => { setShowCreateModal(false); loadData(); }}
        />
      )}

      {showAIModal && (
        <AIGenerateModal 
          clientId={effectiveClientId}
          onClose={() => setShowAIModal(false)}
          onSuccess={() => { setShowAIModal(false); loadData(); }}
        />
      )}

      {showImportModal && (
        <ImportModal 
          clientId={effectiveClientId}
          onClose={() => setShowImportModal(false)}
          onSuccess={() => { setShowImportModal(false); loadData(); }}
        />
      )}

      {showSettingsModal && (
        <SettingsModal 
          clientId={effectiveClientId}
          settings={clientSpace?.settings}
          onClose={() => setShowSettingsModal(false)}
          onSuccess={() => { setShowSettingsModal(false); loadData(); }}
        />
      )}
    </div>
  );
};

// Tab Oferte
const OffersTab = ({ offers, searchTerm, setSearchTerm, statusFilter, setStatusFilter, onDelete, onDuplicate, onExport, clientId, navigate, getStatusBadge, loading }) => {
  return (
    <div>
      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Caută oferte..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-emerald-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-emerald-500"
        >
          <option value="">Toate statusurile</option>
          <option value="draft">Ciornă</option>
          <option value="sent">Trimise</option>
          <option value="accepted">Acceptate</option>
          <option value="rejected">Respinse</option>
          <option value="expired">Expirate</option>
        </select>
      </div>

      {/* Offers List */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Se încarcă...</div>
      ) : offers.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>Nu ai nicio ofertă încă</p>
          <p className="text-sm mt-2">Creează prima ta ofertă sau generează una cu AI</p>
        </div>
      ) : (
        <div className="space-y-4">
          {offers.map(offer => (
            <div 
              key={offer._id}
              className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition-all"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-lg">{offer.title}</h3>
                    {getStatusBadge(offer.status)}
                    <span className="text-slate-500 text-sm">#{offer.reference_number}</span>
                  </div>
                  <p className="text-slate-400 text-sm mb-2">
                    {offer.recipient?.company || offer.recipient?.name || 'Client nespecificat'}
                  </p>
                  <div className="flex gap-4 text-sm text-slate-500">
                    <span>{offer.items?.length || 0} articole</span>
                    <span>•</span>
                    <span>{new Date(offer.created_at).toLocaleDateString('ro-RO')}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-emerald-400">
                    {(offer.total || 0).toLocaleString()} {offer.currency}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button 
                      onClick={() => navigate(`/offers/${clientId}/${offer._id}`)}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg"
                      title="Vizualizează"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => navigate(`/offers/${clientId}/${offer._id}/edit`)}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg"
                      title="Editează"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onDuplicate(offer._id)}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg"
                      title="Duplică"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onExport(offer._id)}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg"
                      title="Export"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => onDelete(offer._id)}
                      className="p-2 bg-red-900/50 hover:bg-red-800/50 rounded-lg text-red-400"
                      title="Șterge"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Tab Templates
const TemplatesTab = ({ templates, clientId, onRefresh }) => {
  const [showCreate, setShowCreate] = useState(false);
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Template-uri Salvate</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Template Nou
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Copy className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>Nu ai niciun template salvat</p>
          <p className="text-sm mt-2">Salvează oferte ca template pentru reutilizare rapidă</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {templates.map(template => (
            <div 
              key={template._id}
              className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-emerald-500/50 transition-all cursor-pointer"
            >
              <h3 className="font-semibold mb-2">{template.name}</h3>
              <p className="text-slate-400 text-sm mb-3">{template.description}</p>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-500">{template.default_items?.length || 0} articole</span>
                <span className="text-emerald-400">Folosit de {template.usage_count || 0}x</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Tab Catalog
const CatalogTab = ({ catalog, clientId, onRefresh }) => {
  const [showAdd, setShowAdd] = useState(false);
  const [newItem, setNewItem] = useState({ name: '', description: '', unit: 'buc', unit_price: 0, category: 'general' });

  const handleAddItem = async () => {
    try {
      await api.post(`/offers/${clientId}/catalog`, newItem);
      setShowAdd(false);
      setNewItem({ name: '', description: '', unit: 'buc', unit_price: 0, category: 'general' });
      onRefresh();
    } catch (error) {
      console.error('Error adding catalog item:', error);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Catalog Servicii & Produse</h2>
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Adaugă Articol
        </button>
      </div>

      {showAdd && (
        <div className="bg-slate-800/50 rounded-xl p-4 border border-emerald-500/50 mb-6">
          <h3 className="font-semibold mb-4">Articol Nou</h3>
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Nume articol"
              value={newItem.name}
              onChange={(e) => setNewItem({...newItem, name: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
            <input
              type="text"
              placeholder="Descriere"
              value={newItem.description}
              onChange={(e) => setNewItem({...newItem, description: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
            <input
              type="text"
              placeholder="Unitate (buc, mp, ora)"
              value={newItem.unit}
              onChange={(e) => setNewItem({...newItem, unit: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
            <input
              type="number"
              placeholder="Preț unitar"
              value={newItem.unit_price}
              onChange={(e) => setNewItem({...newItem, unit_price: parseFloat(e.target.value)})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={handleAddItem} className="px-4 py-2 bg-emerald-600 rounded-lg">Salvează</button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 bg-slate-700 rounded-lg">Anulează</button>
          </div>
        </div>
      )}

      {catalog.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <p>Catalogul este gol</p>
          <p className="text-sm mt-2">Adaugă servicii și produse pentru utilizare rapidă în oferte</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4">Articol</th>
                <th className="text-left py-3 px-4">Descriere</th>
                <th className="text-center py-3 px-4">Unitate</th>
                <th className="text-right py-3 px-4">Preț</th>
                <th className="text-center py-3 px-4">Utilizări</th>
              </tr>
            </thead>
            <tbody>
              {catalog.map(item => (
                <tr key={item._id} className="border-b border-slate-700/50 hover:bg-slate-800/50">
                  <td className="py-3 px-4 font-medium">{item.name}</td>
                  <td className="py-3 px-4 text-slate-400">{item.description}</td>
                  <td className="py-3 px-4 text-center">{item.unit}</td>
                  <td className="py-3 px-4 text-right text-emerald-400">{item.unit_price?.toLocaleString()} RON</td>
                  <td className="py-3 px-4 text-center text-slate-500">{item.usage_count || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Tab Statistici
const StatisticsTab = ({ statistics }) => {
  if (!statistics) return <div className="text-center py-12 text-slate-400">Se încarcă statisticile...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold mb-4">Statistici pe Status</h2>
        <div className="grid grid-cols-5 gap-4">
          {Object.entries(statistics.by_status || {}).map(([status, data]) => (
            <div key={status} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
              <div className="text-lg font-bold">{data.count}</div>
              <div className="text-slate-400 text-sm capitalize">{status}</div>
              <div className="text-emerald-400 text-sm mt-1">{data.value?.toLocaleString()} RON</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Evoluție Lunară</h2>
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <div className="flex items-end gap-2 h-40">
            {(statistics.monthly || []).reverse().map((month, i) => (
              <div key={i} className="flex-1 flex flex-col items-center">
                <div 
                  className="w-full bg-gradient-to-t from-emerald-600 to-cyan-600 rounded-t"
                  style={{ height: `${Math.max(10, (month.value / Math.max(...statistics.monthly.map(m => m.value))) * 100)}%` }}
                />
                <div className="text-xs text-slate-500 mt-2">{month.month}/{month.year % 100}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Modal Creare Ofertă
const CreateOfferModal = ({ clientId, templates, catalog, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    recipient_name: '',
    recipient_company: '',
    recipient_email: '',
    items: []
  });
  const [newItem, setNewItem] = useState({ name: '', quantity: 1, unit: 'buc', unit_price: 0 });

  const addItem = () => {
    if (newItem.name) {
      setFormData({...formData, items: [...formData.items, {...newItem}]});
      setNewItem({ name: '', quantity: 1, unit: 'buc', unit_price: 0 });
    }
  };

  const addFromCatalog = (catalogItem) => {
    setFormData({
      ...formData, 
      items: [...formData.items, {
        name: catalogItem.name,
        description: catalogItem.description,
        quantity: 1,
        unit: catalogItem.unit,
        unit_price: catalogItem.unit_price,
        vat_rate: catalogItem.vat_rate || 19
      }]
    });
  };

  const handleSubmit = async () => {
    try {
      await api.post(`/offers/${clientId}`, formData);
      onSuccess();
    } catch (error) {
      console.error('Error creating offer:', error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-2xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-6">Creare Ofertă Nouă</h2>
        
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Titlu ofertă"
            value={formData.title}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
          
          <textarea
            placeholder="Descriere"
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg h-24"
          />

          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Nume client"
              value={formData.recipient_name}
              onChange={(e) => setFormData({...formData, recipient_name: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
            <input
              type="text"
              placeholder="Companie client"
              value={formData.recipient_company}
              onChange={(e) => setFormData({...formData, recipient_company: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>

          {/* Articole */}
          <div className="border border-slate-600 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Articole</h3>
            
            {formData.items.length > 0 && (
              <div className="space-y-2 mb-4">
                {formData.items.map((item, i) => (
                  <div key={i} className="flex justify-between items-center bg-slate-700/50 p-2 rounded">
                    <span>{item.name} x{item.quantity} {item.unit}</span>
                    <span className="text-emerald-400">{(item.quantity * item.unit_price).toLocaleString()} RON</span>
                  </div>
                ))}
              </div>
            )}

            {/* Adaugă din catalog */}
            {catalog.length > 0 && (
              <div className="mb-4">
                <p className="text-sm text-slate-400 mb-2">Adaugă din catalog:</p>
                <div className="flex flex-wrap gap-2">
                  {catalog.slice(0, 5).map(item => (
                    <button
                      key={item._id}
                      onClick={() => addFromCatalog(item)}
                      className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm"
                    >
                      + {item.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Adaugă manual */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Nume articol"
                value={newItem.name}
                onChange={(e) => setNewItem({...newItem, name: e.target.value})}
                className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded"
              />
              <input
                type="number"
                placeholder="Cant."
                value={newItem.quantity}
                onChange={(e) => setNewItem({...newItem, quantity: parseFloat(e.target.value)})}
                className="w-20 px-3 py-2 bg-slate-700 border border-slate-600 rounded"
              />
              <input
                type="number"
                placeholder="Preț"
                value={newItem.unit_price}
                onChange={(e) => setNewItem({...newItem, unit_price: parseFloat(e.target.value)})}
                className="w-24 px-3 py-2 bg-slate-700 border border-slate-600 rounded"
              />
              <button onClick={addItem} className="px-4 py-2 bg-emerald-600 rounded">+</button>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-6 py-2 bg-slate-700 rounded-lg">Anulează</button>
          <button onClick={handleSubmit} className="px-6 py-2 bg-emerald-600 rounded-lg">Creează Oferta</button>
        </div>
      </div>
    </div>
  );
};

// Modal Generare AI
const AIGenerateModal = ({ clientId, onClose, onSuccess }) => {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await api.post(`/offers/${clientId}/generate`, { description });
      setPreview(res.data.offer_data);
    } catch (error) {
      console.error('Error generating offer:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.post(`/offers/${clientId}`, preview);
      onSuccess();
    } catch (error) {
      console.error('Error saving offer:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-2xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-purple-400" />
          Generare Ofertă cu AI
        </h2>
        <p className="text-slate-400 mb-6">Descrie ce servicii/produse vrei să oferi și AI-ul va genera o ofertă completă</p>

        {!preview ? (
          <>
            <textarea
              placeholder="Ex: Vreau să fac o ofertă pentru renovarea unui apartament de 3 camere. Include zugrăvit, parchet, instalații sanitare și electrice."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg h-40"
            />
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={onClose} className="px-6 py-2 bg-slate-700 rounded-lg">Anulează</button>
              <button 
                onClick={handleGenerate} 
                disabled={loading || !description}
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg disabled:opacity-50"
              >
                {loading ? 'Se generează...' : 'Generează Oferta'}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-lg mb-2">{preview.title}</h3>
              <p className="text-slate-400 mb-4">{preview.description}</p>
              
              <div className="space-y-2">
                {preview.items?.map((item, i) => (
                  <div key={i} className="flex justify-between bg-slate-800/50 p-2 rounded">
                    <span>{item.name} x{item.quantity} {item.unit}</span>
                    <span className="text-emerald-400">{(item.quantity * item.unit_price).toLocaleString()} RON</span>
                  </div>
                ))}
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-600 text-right">
                <span className="text-2xl font-bold text-emerald-400">
                  Total estimat: {preview.items?.reduce((sum, item) => sum + (item.quantity * item.unit_price * 1.19), 0).toLocaleString()} RON
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button onClick={() => setPreview(null)} className="px-6 py-2 bg-slate-700 rounded-lg">Regenerează</button>
              <button onClick={handleSave} disabled={loading} className="px-6 py-2 bg-emerald-600 rounded-lg">
                {loading ? 'Se salvează...' : 'Salvează Oferta'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Modal Import
const ImportModal = ({ clientId, onClose, onSuccess }) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const handleImport = async () => {
    setLoading(true);
    try {
      await api.post(`/offers/${clientId}/import`, { text });
      onSuccess();
    } catch (error) {
      console.error('Error importing offer:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-2xl p-6 w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
          <FileUp className="w-6 h-6 text-cyan-400" />
          Import Ofertă
        </h2>
        <p className="text-slate-400 mb-6">Lipește textul unei oferte existente (din PDF, Word, email) și AI-ul o va parsa automat</p>

        <textarea
          placeholder="Lipește aici conținutul ofertei..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg h-60 font-mono text-sm"
        />

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-6 py-2 bg-slate-700 rounded-lg">Anulează</button>
          <button 
            onClick={handleImport} 
            disabled={loading || !text}
            className="px-6 py-2 bg-cyan-600 rounded-lg disabled:opacity-50"
          >
            {loading ? 'Se importă...' : 'Importă Oferta'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Modal Setări
const SettingsModal = ({ clientId, settings, onClose, onSuccess }) => {
  const [formData, setFormData] = useState(settings || {});

  const handleSave = async () => {
    try {
      await api.put(`/offers/space/${clientId}/settings`, formData);
      onSuccess();
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-2xl p-6 w-full max-w-xl">
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Settings className="w-6 h-6" />
          Setări Companie
        </h2>

        <div className="space-y-4">
          <input
            type="text"
            placeholder="Numele companiei"
            value={formData.company_name || ''}
            onChange={(e) => setFormData({...formData, company_name: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
          <textarea
            placeholder="Adresa companiei"
            value={formData.company_address || ''}
            onChange={(e) => setFormData({...formData, company_address: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Telefon"
              value={formData.company_phone || ''}
              onChange={(e) => setFormData({...formData, company_phone: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
            <input
              type="email"
              placeholder="Email"
              value={formData.company_email || ''}
              onChange={(e) => setFormData({...formData, company_email: e.target.value})}
              className="px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
            />
          </div>
          <textarea
            placeholder="Detalii bancare (IBAN, Bancă)"
            value={formData.bank_details || ''}
            onChange={(e) => setFormData({...formData, bank_details: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
          <input
            type="text"
            placeholder="Termeni de plată (ex: 30 zile)"
            value={formData.payment_terms || ''}
            onChange={(e) => setFormData({...formData, payment_terms: e.target.value})}
            className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-6 py-2 bg-slate-700 rounded-lg">Anulează</button>
          <button onClick={handleSave} className="px-6 py-2 bg-emerald-600 rounded-lg">Salvează</button>
        </div>
      </div>
    </div>
  );
};

export default PricingOffers;

