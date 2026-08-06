import type { RouteObject } from 'react-router-dom'
import DashboardView from './views/DashboardView'
import BidCreateView from './views/BidCreateView'
import TaskDetailView from './views/TaskDetailView'

/**
 * Bid routes for M3 App.tsx aggregation (Phase 0 protocol).
 * Until M3 wires these exports, page entry files re-export the same views.
 */
export const bidRoutes: RouteObject[] = [
  { path: 'dashboard', element: <DashboardView /> },
  { path: 'tasks/create', element: <BidCreateView /> },
  { path: 'tasks/:id', element: <TaskDetailView /> },
]

export default bidRoutes
