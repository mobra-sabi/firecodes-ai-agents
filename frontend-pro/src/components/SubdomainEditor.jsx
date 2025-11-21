import { useState } from 'react'
import { Edit2, Trash2, Plus, Check, X } from 'lucide-react'
import api from '@/services/api'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'

const SubdomainEditor = ({ subdomain, index, agentId, onUpdate, onDelete }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedSubdomain, setEditedSubdomain] = useState(subdomain)

  const handleSave = async () => {
    try {
      const response = await api.put(`/agents/${agentId}/subdomains/${index}`, editedSubdomain)
      if (response.data.ok) {
        onUpdate()
        setIsEditing(false)
      }
    } catch (error) {
      alert('Error updating subdomain: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleAddKeyword = (keyword) => {
    if (keyword.trim() && !editedSubdomain.keywords?.includes(keyword.trim())) {
      setEditedSubdomain({
        ...editedSubdomain,
        keywords: [...(editedSubdomain.keywords || []), keyword.trim()]
      })
    }
  }

  const handleRemoveKeyword = (keywordToRemove) => {
    setEditedSubdomain({
      ...editedSubdomain,
      keywords: editedSubdomain.keywords?.filter(kw => kw !== keywordToRemove) || []
    })
  }

  const handleAddSuggestedKeyword = (keyword) => {
    handleAddKeyword(keyword)
    // Șterge din suggested
    setEditedSubdomain({
      ...editedSubdomain,
      suggested_keywords: editedSubdomain.suggested_keywords?.filter(kw => kw !== keyword) || []
    })
  }

  if (isEditing) {
    return (
      <Card>
        <Card.Body className="p-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Name</label>
              <input
                type="text"
                value={editedSubdomain.name || ''}
                onChange={(e) => setEditedSubdomain({ ...editedSubdomain, name: e.target.value })}
                className="input-custom w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Description</label>
              <textarea
                value={editedSubdomain.description || ''}
                onChange={(e) => setEditedSubdomain({ ...editedSubdomain, description: e.target.value })}
                className="input-custom w-full"
                rows={3}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Keywords</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {editedSubdomain.keywords?.map((kw, kwIndex) => (
                  <span key={kwIndex} className="px-2 py-1 bg-primary-700 rounded text-sm text-text-primary flex items-center gap-1">
                    {kw}
                    <button
                      onClick={() => handleRemoveKeyword(kw)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add keyword..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleAddKeyword(e.target.value)
                      e.target.value = ''
                    }
                  }}
                  className="input-custom flex-1"
                />
                <Button onClick={() => {
                  const input = document.querySelector(`input[placeholder="Add keyword..."]`)
                  if (input) {
                    handleAddKeyword(input.value)
                    input.value = ''
                  }
                }}>
                  Add
                </Button>
              </div>
            </div>
            
            {editedSubdomain.suggested_keywords && editedSubdomain.suggested_keywords.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">Suggested Keywords</label>
                <div className="flex flex-wrap gap-2">
                  {editedSubdomain.suggested_keywords.map((kw, kwIndex) => (
                    <button
                      key={kwIndex}
                      onClick={() => handleAddSuggestedKeyword(kw)}
                      className="px-2 py-1 bg-purple-700 hover:bg-purple-600 rounded text-sm text-text-primary"
                    >
                      + {kw}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            <div className="flex gap-2">
              <Button onClick={handleSave} className="bg-green-600 hover:bg-green-700">
                <Check className="w-4 h-4 mr-2" />
                Save
              </Button>
              <Button variant="secondary" onClick={() => {
                setEditedSubdomain(subdomain)
                setIsEditing(false)
              }}>
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>
    )
  }

  return (
    <Card>
      <Card.Header>
        <div className="flex items-center justify-between">
          <Card.Title>{subdomain.name || `Subdomain ${index + 1}`}</Card.Title>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsEditing(true)}
            >
              <Edit2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                if (confirm('Delete this subdomain?')) {
                  try {
                    await api.delete(`/agents/${agentId}/subdomains/${index}`)
                    onDelete()
                  } catch (error) {
                    alert('Error: ' + (error.response?.data?.detail || error.message))
                  }
                }
              }}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card.Header>
      <Card.Body>
        <p className="text-text-muted mb-4">{subdomain.description || 'No description'}</p>
        
        <div className="space-y-3">
          <div>
            <h4 className="text-sm font-medium text-text-primary mb-2">Keywords ({subdomain.keywords?.length || 0})</h4>
            <div className="flex flex-wrap gap-2">
              {subdomain.keywords && subdomain.keywords.length > 0 ? (
                subdomain.keywords.map((kw, kwIndex) => (
                  <span key={kwIndex} className="px-2 py-1 bg-primary-700 rounded text-sm text-text-primary">
                    {kw}
                  </span>
                ))
              ) : (
                <span className="text-text-muted text-sm">No keywords</span>
              )}
            </div>
          </div>
          
          {subdomain.suggested_keywords && subdomain.suggested_keywords.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-text-primary mb-2">Suggested Keywords ({subdomain.suggested_keywords.length})</h4>
              <div className="flex flex-wrap gap-2">
                {subdomain.suggested_keywords.map((kw, kwIndex) => (
                  <span key={kwIndex} className="px-2 py-1 bg-purple-700 rounded text-sm text-text-primary">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              try {
                const response = await api.post(`/agents/${agentId}/subdomains/${index}/suggest-keywords`)
                if (response.data.ok) {
                  onUpdate()
                }
              } catch (error) {
                alert('Error: ' + (error.response?.data?.detail || error.message))
              }
            }}
          >
            Suggest More Keywords
          </Button>
        </div>
      </Card.Body>
    </Card>
  )
}

export default SubdomainEditor

