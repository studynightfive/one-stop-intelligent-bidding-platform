import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useDemo } from '../../context/DemoContext'

export default function AuthenticatedRoute() {
  const { loggedIn } = useDemo()
  const location = useLocation()
  if (!loggedIn) return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}${location.hash}` }} />
  return <Outlet />
}
