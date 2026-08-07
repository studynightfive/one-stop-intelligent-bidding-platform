import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import EvaluationDashboardView from './views/EvaluationDashboardView'
import EvaluationCreateView from './views/EvaluationCreateView'
import EvaluationTaskDetailView from './views/EvaluationTaskDetailView'
import { EVAL_PORTAL_ROUTE } from './constants'

/** M2 evaluation routes discovered by the M3 bridge via the feature routes protocol. */
export const evaluationRoutes: RouteObject[] = [
  { path: 'evaluation', element: <EvaluationDashboardView /> },
  { path: 'evaluation/create', element: <EvaluationCreateView /> },
  { path: 'evaluation/portal', element: <Navigate to={EVAL_PORTAL_ROUTE} replace /> },
  { path: 'evaluation/:id', element: <EvaluationTaskDetailView /> },
]

export default evaluationRoutes
