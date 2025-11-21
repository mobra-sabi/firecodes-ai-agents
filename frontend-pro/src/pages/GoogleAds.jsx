import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdsOAuthUrl, setCustomerId, createCampaign, getCampaigns, syncFromSEO } from '@/api/ads'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Dialog from '@/components/ui/Dialog'
import { DollarSign, Plus, RefreshCw, ExternalLink, Target, TrendingUp } from 'lucide-react'
import { format } from 'date-fns'

const GoogleAds = () => {
  const [selectedAgent, setSelectedAgent] = useState('')
  const [showOAuthDialog, setShowOAuthDialog] = useState(false)
  const [showCampaignDialog, setShowCampaignDialog] = useState(false)
  const [showCustomerDialog, setShowCustomerDialog] = useState(false)
  const [customerId, setCustomerId] = useState('')
  const [newCampaign, setNewCampaign] = useState({
    campaign_name: '',
    budget_amount_micros: 10000000, // 10 currency units
    bidding_strategy: 'MAXIMIZE_CONVERSIONS'
  })
  
  const queryClient = useQueryClient()
  
  const { data: campaignsData, isLoading } = useQuery({
    queryKey: ['campaigns', selectedAgent],
    queryFn: () => getCampaigns(selectedAgent || null),
    enabled: !!selectedAgent,
    refetchInterval: 30000
  })
  
  const oauthUrlMutation = useMutation({
    mutationFn: () => getAdsOAuthUrl(selectedAgent),
    onSuccess: (data) => {
      if (data.auth_url) {
        window.open(data.auth_url, '_blank')
      }
    }
  })
  
  const setCustomerMutation = useMutation({
    mutationFn: () => setCustomerId(selectedAgent, customerId),
    onSuccess: () => {
      queryClient.invalidateQueries(['campaigns'])
      setShowCustomerDialog(false)
      setCustomerId('')
    }
  })
  
  const createCampaignMutation = useMutation({
    mutationFn: () => createCampaign({ ...newCampaign, agent_id: selectedAgent }),
    onSuccess: () => {
      queryClient.invalidateQueries(['campaigns'])
      setShowCampaignDialog(false)
      setNewCampaign({ campaign_name: '', budget_amount_micros: 10000000, bidding_strategy: 'MAXIMIZE_CONVERSIONS' })
    }
  })
  
  const syncFromSEOMutation = useMutation({
    mutationFn: () => syncFromSEO(selectedAgent),
    onSuccess: () => {
      queryClient.invalidateQueries(['campaigns'])
    }
  })
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Google Ads</h1>
        <p className="text-text-muted mt-1">Manage Google Ads campaigns and sync from SEO insights</p>
      </div>
      
      {/* Agent Selection */}
      <Card>
        <Card.Body className="p-6">
          <div className="flex items-center space-x-4">
            <input
              type="text"
              placeholder="Enter Agent ID..."
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            />
            <Button
              onClick={() => setShowOAuthDialog(true)}
              disabled={!selectedAgent}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Connect Google Ads
            </Button>
            <Button
              variant="secondary"
              onClick={() => setShowCustomerDialog(true)}
              disabled={!selectedAgent}
            >
              Set Customer ID
            </Button>
          </div>
        </Card.Body>
      </Card>
      
      {/* Actions */}
      {selectedAgent && (
        <div className="flex space-x-4">
          <Button onClick={() => setShowCampaignDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Campaign
          </Button>
          <Button
            variant="secondary"
            onClick={() => syncFromSEOMutation.mutate()}
            disabled={syncFromSEOMutation.isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncFromSEOMutation.isLoading ? 'animate-spin' : ''}`} />
            Sync from SEO
          </Button>
        </div>
      )}
      
      {/* Campaigns List */}
      <Card>
        <Card.Header>
          <Card.Title>Campaigns</Card.Title>
        </Card.Header>
        <Card.Body className="p-0">
          {!selectedAgent ? (
            <p className="text-text-muted text-center py-12">Select an agent to view campaigns</p>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-400"></div>
            </div>
          ) : campaignsData?.campaigns?.length === 0 ? (
            <p className="text-text-muted text-center py-12">No campaigns found. Create one or sync from SEO.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Campaign</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Budget</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Bidding</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Created</th>
                  </tr>
                </thead>
                <tbody className="bg-gray-900 divide-y divide-gray-800">
                  {campaignsData?.campaigns?.map((campaign) => (
                    <tr key={campaign._id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-text-primary">
                        {campaign.campaign_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-text-muted">
                        {(campaign.budget_amount_micros / 1000000).toFixed(2)} units
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-text-muted">
                        {campaign.bidding_strategy}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          campaign.status === 'enabled' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-300'
                        }`}>
                          {campaign.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                        {campaign.created_at ? format(new Date(campaign.created_at), 'yyyy-MM-dd HH:mm') : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* OAuth Dialog */}
      <Dialog open={showOAuthDialog} onOpenChange={setShowOAuthDialog}>
        <Dialog.Content>
          <Dialog.Header>
            <Dialog.Title>Connect Google Ads Account</Dialog.Title>
            <Dialog.Description>Authorize access to your Google Ads account</Dialog.Description>
          </Dialog.Header>
          <div className="space-y-4">
            <p className="text-text-muted text-sm">
              Click the button below to open Google OAuth authorization in a new window.
              After authorizing, you'll be redirected back to complete the connection.
            </p>
            <div className="flex justify-end space-x-4">
              <Button variant="secondary" onClick={() => setShowOAuthDialog(false)}>Cancel</Button>
              <Button
                onClick={() => oauthUrlMutation.mutate()}
                disabled={oauthUrlMutation.isLoading}
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Open Authorization
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog>
      
      {/* Customer ID Dialog */}
      <Dialog open={showCustomerDialog} onOpenChange={setShowCustomerDialog}>
        <Dialog.Content>
          <Dialog.Header>
            <Dialog.Title>Set Google Ads Customer ID</Dialog.Title>
            <Dialog.Description>Enter your Google Ads customer ID (format: 123-456-7890)</Dialog.Description>
          </Dialog.Header>
          <div className="space-y-4">
            <input
              type="text"
              placeholder="123-456-7890"
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
            />
            <div className="flex justify-end space-x-4">
              <Button variant="secondary" onClick={() => setShowCustomerDialog(false)}>Cancel</Button>
              <Button
                onClick={() => setCustomerMutation.mutate()}
                disabled={!customerId || setCustomerMutation.isLoading}
              >
                {setCustomerMutation.isLoading ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog>
      
      {/* Create Campaign Dialog */}
      <Dialog open={showCampaignDialog} onOpenChange={setShowCampaignDialog}>
        <Dialog.Content className="sm:max-w-[600px]">
          <Dialog.Header>
            <Dialog.Title>Create Google Ads Campaign</Dialog.Title>
            <Dialog.Description>Create a new campaign from SEO insights</Dialog.Description>
          </Dialog.Header>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Campaign Name</label>
              <input
                type="text"
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newCampaign.campaign_name}
                onChange={(e) => setNewCampaign({ ...newCampaign, campaign_name: e.target.value })}
                placeholder="SEO Insights Campaign"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Budget (currency units)</label>
              <input
                type="number"
                min="1"
                step="0.01"
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newCampaign.budget_amount_micros / 1000000}
                onChange={(e) => setNewCampaign({ ...newCampaign, budget_amount_micros: parseFloat(e.target.value) * 1000000 })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Bidding Strategy</label>
              <select
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-md text-text-primary"
                value={newCampaign.bidding_strategy}
                onChange={(e) => setNewCampaign({ ...newCampaign, bidding_strategy: e.target.value })}
              >
                <option value="MAXIMIZE_CONVERSIONS">Maximize Conversions</option>
                <option value="TARGET_CPA">Target CPA</option>
              </select>
            </div>
            <div className="flex justify-end space-x-4">
              <Button variant="secondary" onClick={() => setShowCampaignDialog(false)}>Cancel</Button>
              <Button
                onClick={() => createCampaignMutation.mutate()}
                disabled={!newCampaign.campaign_name || createCampaignMutation.isLoading}
              >
                {createCampaignMutation.isLoading ? 'Creating...' : 'Create Campaign'}
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog>
    </div>
  )
}

export default GoogleAds

