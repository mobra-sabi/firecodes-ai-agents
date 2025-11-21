import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

const DashboardLayout = () => {
  return (
    <div className="flex min-h-screen bg-primary-900">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container-custom py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default DashboardLayout

