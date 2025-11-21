import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { Building2, Loader2 } from 'lucide-react'

// Versiune minimală pentru testare
const IndustryTransformationTest = () => {
  const [testError, setTestError] = useState(null)
  
  // Un singur query simplu
  const { data: progress, isLoading, error } = useQuery({
    queryKey: ['industry-progress-test'],
    queryFn: async () => {
      try {
        const response = await api.get('/industry/construction/progress')
        return response.data
      } catch (err) {
        setTestError(err.message)
        throw err
      }
    },
    retry: 1,
  })

  if (testError) {
    return (
      <div className="p-8">
        <h1 className="text-2xl text-red-400 mb-4">Eroare: {testError}</h1>
        <button onClick={() => setTestError(null)}>Reîncearcă</button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-2xl text-red-400 mb-4">Eroare Query: {error.message}</h1>
      </div>
    )
  }

  const stats = progress?.statistics || {
    total_companies_discovered: 0,
    companies_pending: 0,
    companies_created: 0,
    construction_agents_created: 0
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-3xl font-bold text-white">Industry Transformation - TEST</h1>
      
      <Card>
        <Card.Body>
          <h2 className="text-xl font-semibold text-white mb-4">Statistici</h2>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <p className="text-gray-400">Descoperite</p>
              <p className="text-2xl text-white">{stats.total_companies_discovered}</p>
            </div>
            <div>
              <p className="text-gray-400">Pending</p>
              <p className="text-2xl text-white">{stats.companies_pending}</p>
            </div>
            <div>
              <p className="text-gray-400">Creați</p>
              <p className="text-2xl text-white">{stats.companies_created}</p>
            </div>
            <div>
              <p className="text-gray-400">Agenți</p>
              <p className="text-2xl text-white">{stats.construction_agents_created}</p>
            </div>
          </div>
        </Card.Body>
      </Card>

      <div className="text-green-400">
        ✅ Componenta funcționează! Acum poți înlocui cu versiunea completă.
      </div>
    </div>
  )
}

export default IndustryTransformationTest

