import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useDemo } from '../../context/DemoContext'

export default function AuthenticatedRoute() {
  const { loggedIn, authReady } = useDemo()
  const location = useLocation()
  if (!authReady) return <div className="flex min-h-screen items-center justify-center text-sm text-[#64748B]" role="status">正在验证登录状态…</div>
  if (!loggedIn) return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}${location.hash}` }} />
  return <Outlet />
}
