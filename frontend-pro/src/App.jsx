import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import DashboardLayout from './components/layout/DashboardLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import Dashboard from './pages/Dashboard'
import MasterAgents from './pages/MasterAgents'
import AgentDetail from './pages/AgentDetail'
import CreateAgent from './pages/CreateAgent'
import Intelligence from './pages/Intelligence'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import WorkflowMonitor from './pages/WorkflowMonitor'
import ControlCenter from './pages/ControlCenter'
import LearningCenter from './pages/LearningCenter'
import GoogleRankingsMap from './pages/GoogleRankingsMap'
import SERPDashboard from './pages/SERPDashboard'
import LiveMonitor from './pages/LiveMonitor'
import ActionsQueue from './pages/ActionsQueue'
import AlertsCenter from './pages/AlertsCenter'
import OrganizationGraph from './pages/OrganizationGraph'
import GoogleAds from './pages/GoogleAds'
import WorkflowTracker from './pages/WorkflowTracker'
import AgentChat from './pages/AgentChat'
import TaskAIAgent from './pages/TaskAIAgent'
import IndustryTransformation from './pages/IndustryTransformation'
import IndustryTransformationTest from './pages/IndustryTransformation.test'
import ClientDashboard from './pages/ClientDashboard'
import ClientChat from './pages/ClientChat'
import ClientRecommendations from './pages/ClientRecommendations'
import AIConsulting from './pages/AIConsulting'
import BusinessIntelligence from './pages/BusinessIntelligence'

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Auth Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Client Routes - Simplified Interface */}
        <Route path="/client/:agentId" element={<ClientDashboard />} />
        <Route path="/client/:agentId/chat" element={<ClientChat />} />
        <Route path="/client/:agentId/recommendations" element={<ClientRecommendations />} />

        {/* Protected Routes with Dashboard Layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="agents" element={<MasterAgents />} />
          <Route path="agents/:id" element={<AgentDetail />} />
          <Route path="agents/new" element={<CreateAgent />} />
          <Route path="agents/:agentId/live" element={<LiveMonitor />} />
          <Route path="agents/workflow/:workflowId/live" element={<LiveMonitor />} />
          <Route path="agents/:agentId/chat" element={<AgentChat />} />
          <Route path="agents/:agentId/consulting" element={<AIConsulting />} />
          <Route path="agents/:agentId/business-intelligence" element={<BusinessIntelligence />} />
          <Route path="task-ai" element={<TaskAIAgent />} />
          <Route path="agents/:agentId/rankings" element={<GoogleRankingsMap />} />
          <Route path="agents/:agentId/serp" element={<SERPDashboard />} />
          <Route path="workflows" element={<WorkflowMonitor />} />
          <Route path="workflow-tracker" element={<WorkflowTracker />} />
          <Route path="workflow-tracker/:agentId" element={<WorkflowTracker />} />
          <Route path="actions" element={<ActionsQueue />} />
          <Route path="alerts" element={<AlertsCenter />} />
          <Route path="graph" element={<OrganizationGraph />} />
          <Route path="graph/:id" element={<OrganizationGraph />} />
          <Route path="ads" element={<GoogleAds />} />
          <Route path="control-center" element={<ControlCenter />} />
          <Route path="learning" element={<LearningCenter />} />
          <Route path="intelligence" element={<Intelligence />} />
          <Route path="reports" element={<Reports />} />
          <Route path="industry" element={<IndustryTransformation />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Catch all - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
