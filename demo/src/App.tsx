import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import MainLayout from './layouts/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import TaskDetail from './pages/TaskDetail'
import QualificationLibrary from './pages/QualificationLibrary'
import FragmentLibrary from './pages/FragmentLibrary'
import UserPermissions from './pages/UserPermissions'
import SystemSettings from './pages/SystemSettings'
import EvaluationDashboard from './pages/EvaluationDashboard'
import EvaluationTaskDetail from './pages/EvaluationTaskDetail'
import EvaluationCreate from './pages/EvaluationCreate'
import SupplierPortal from './pages/SupplierPortal'
import BidCreate from './pages/BidCreate'
import { DemoProvider, useDemo } from './context/DemoContext'

export default function App() {
  const theme = {
    token: {
      colorPrimary: '#2563EB',
      colorSuccess: '#16A34A',
      colorWarning: '#D97706',
      colorError: '#DC2626',
      colorInfo: '#2563EB',
      borderRadius: 6,
      fontFamily: "'Inter', 'Noto Sans SC', sans-serif"
    }
  }

  return (
    <ConfigProvider theme={theme} locale={zhCN}>
      <BrowserRouter>
        <DemoProvider>
          <AppRoutes />
        </DemoProvider>
      </BrowserRouter>
    </ConfigProvider>
  )
}

function AppRoutes() {
  const location = useLocation()
  const { loggedIn, login } = useDemo()
  const isSupplierPortal = /^\/evaluation\/portal\/[^/]+$/.test(location.pathname)

  if (isSupplierPortal) {
    return (
      <Routes>
        <Route path="/evaluation/portal/:id" element={<SupplierPortal />} />
        <Route path="*" element={<Navigate to="/evaluation/portal/EVAL-2026-001" replace />} />
      </Routes>
    )
  }

  if (!loggedIn) return <Login onLogin={login} />

  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="login" element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="tasks/create" element={<BidCreate />} />
        <Route path="tasks/:id" element={<TaskDetail />} />
        <Route path="admin/qualifications" element={<QualificationLibrary />} />
        <Route path="admin/fragments" element={<FragmentLibrary />} />
        <Route path="admin/users" element={<UserPermissions />} />
        <Route path="admin/settings" element={<SystemSettings />} />
        <Route path="evaluation" element={<EvaluationDashboard />} />
        <Route path="evaluation/create" element={<EvaluationCreate />} />
        <Route path="evaluation/portal" element={<Navigate to="/evaluation/portal/EVAL-2026-001" replace />} />
        <Route path="evaluation/portal/:id" element={<SupplierPortal />} />
        <Route path="evaluation/:id" element={<EvaluationTaskDetail />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
