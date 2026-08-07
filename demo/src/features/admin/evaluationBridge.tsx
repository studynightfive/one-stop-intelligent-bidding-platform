import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { Gavel, Link2, Plus } from 'lucide-react'
import EvaluationDashboard from '../../pages/EvaluationDashboard'
import EvaluationTaskDetail from '../../pages/EvaluationTaskDetail'
import EvaluationCreate from '../../pages/EvaluationCreate'

const fallbackEvaluationRoutes: RouteObject[] = [
  { path: 'evaluation', element: <EvaluationDashboard /> },
  { path: 'evaluation/create', element: <EvaluationCreate /> },
  { path: 'evaluation/portal', element: <Navigate to="/evaluation/portal/EVAL-2026-001" replace /> },
  { path: 'evaluation/:id', element: <EvaluationTaskDetail /> },
]

const fallbackEvaluationNavigation = [
  { key: '/evaluation', label: '评标工作台', icon: Gavel, section: 'main' as const, owner: 'M2' as const },
  { key: '/evaluation/create', label: '创建评标任务', icon: Plus, section: 'main' as const, owner: 'M2' as const },
  { key: '/evaluation/portal/EVAL-2026-001', label: '供应商门户（外部）', icon: Link2, section: 'main' as const, owner: 'M2' as const },
]

type EvaluationRouteModule = { evaluationRoutes?: RouteObject[]; default?: RouteObject[] }
type EvaluationNavigationModule = {
  evaluationNavigation?: typeof fallbackEvaluationNavigation
  default?: typeof fallbackEvaluationNavigation
}

// The wildcard always matches M1/M3 modules today. When M2 adds its owned
// features/evaluations exports, this bridge discovers them without an App.tsx conflict.
const routeModules = import.meta.glob<EvaluationRouteModule>('../*/routes.tsx', { eager: true })
const navigationModules = import.meta.glob<EvaluationNavigationModule>('../*/navigation.ts', { eager: true })
const m2RouteModule = Object.entries(routeModules).find(([path]) => path.includes('/evaluations/'))?.[1]
const m2NavigationModule = Object.entries(navigationModules).find(([path]) => path.includes('/evaluations/'))?.[1]

export const evaluationRoutes = m2RouteModule?.evaluationRoutes || m2RouteModule?.default || fallbackEvaluationRoutes
export const evaluationNavigation = m2NavigationModule?.evaluationNavigation || m2NavigationModule?.default || fallbackEvaluationNavigation
