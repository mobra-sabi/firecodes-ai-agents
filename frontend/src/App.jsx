import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardLayout from './layouts/DashboardLayout'
import DashboardPage from './pages/DashboardPage'
import MasterAgentsPage from './pages/MasterAgentsPage'
import AgentDetailPage from './pages/AgentDetailPage'
// import WorkflowProgressPage from './pages/WorkflowProgressPage'

// Protected Route wrapper - BYPASSED for demo
const ProtectedRoute = ({ children }) => {
  // DEMO MODE: Always allow access
  return children
}

// Public Route wrapper - BYPASSED for demo  
const PublicRoute = ({ children }) => {
  // DEMO MODE: Redirect to dashboard
  return <Navigate to="/dashboard" replace />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="agents" element={<MasterAgentsPage />} />
          <Route path="agents/:agentId" element={<AgentDetailPage />} />
          {/* <Route path="workflow/:workflowId" element={<WorkflowProgressPage />} /> */}
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

