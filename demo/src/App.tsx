import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter, Navigate, useLocation, useNavigate, useRoutes } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Login from './pages/Login'
import SupplierPortal from './pages/SupplierPortal'
import { DemoProvider, useDemo } from './context/DemoContext'
import { bidRoutes } from './features/bids/routes'
import { adminRoutes } from './features/admin/routes'
import { evaluationRoutes } from './features/admin/evaluationBridge'
import AuthenticatedRoute from './features/admin/AuthenticatedRoute'
import { AppErrorBoundary, ForbiddenPage, NotFoundPage, ServerErrorPage } from './components/common'

const theme = {
  token: {
    colorPrimary: '#2563EB',
    colorSuccess: '#16A34A',
    colorWarning: '#D97706',
    colorError: '#DC2626',
    colorInfo: '#2563EB',
    borderRadius: 6,
    fontFamily: "'Inter', 'Noto Sans SC', sans-serif",
  },
}

export default function App() {
  return (
    <ConfigProvider theme={theme} locale={zhCN}>
      <AppErrorBoundary>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <DemoProvider>
            <AppRoutes />
          </DemoProvider>
        </BrowserRouter>
      </AppErrorBoundary>
    </ConfigProvider>
  )
}

function LoginRoute() {
  const { loggedIn, login } = useDemo()
  const location = useLocation()
  const navigate = useNavigate()
  const from = (location.state as { from?: string } | null)?.from || '/dashboard'
  if (loggedIn) return <Navigate to={from} replace />
  return (
    <Login
      onLogin={async values => {
        await login(values)
        navigate(from, { replace: true })
      }}
    />
  )
}

function AppRoutes() {
  return useRoutes([
    { path: '/login', element: <LoginRoute /> },
    { path: '/evaluation/portal/:id', element: <SupplierPortal /> },
    {
      element: <AuthenticatedRoute />,
      children: [
        {
          path: '/',
          element: <MainLayout />,
          children: [
            { index: true, element: <Navigate to="/dashboard" replace /> },
            ...bidRoutes,
            ...evaluationRoutes,
            ...adminRoutes,
            { path: '403', element: <ForbiddenPage /> },
            { path: '500', element: <ServerErrorPage /> },
            { path: '*', element: <NotFoundPage /> },
          ],
        },
      ],
    },
    { path: '*', element: <Navigate to="/login" replace /> },
  ])
}
