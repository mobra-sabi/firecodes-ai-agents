import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import AgentDetail from './pages/AgentDetail'
import WorkflowMonitor from './pages/WorkflowMonitor'
import ReportsPage from './pages/ReportsPage'
import Layout from './components/Layout'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/agents" element={<Agents />} />
                <Route path="/agents/:id" element={<AgentDetail />} />
                <Route path="/agents/:id/workflow" element={<WorkflowMonitor />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
