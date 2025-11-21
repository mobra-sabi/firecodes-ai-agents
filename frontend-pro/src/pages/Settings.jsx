import Card from '@/components/ui/Card'
import { useAuthStore } from '@/stores/authStore'

const Settings = () => {
  const { user } = useAuthStore()

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Settings</h1>
        <p className="text-text-muted mt-1">Manage your account and preferences</p>
      </div>

      <Card>
        <Card.Header>
          <Card.Title>Profile Information</Card.Title>
        </Card.Header>
        <Card.Body>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={user?.full_name || ''}
                disabled
                className="input-custom w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Email
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input-custom w-full"
              />
            </div>
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <Card.Title>API Keys</Card.Title>
        </Card.Header>
        <Card.Body>
          <p className="text-text-muted">API key management coming soon</p>
        </Card.Body>
      </Card>
    </div>
  )
}

export default Settings

