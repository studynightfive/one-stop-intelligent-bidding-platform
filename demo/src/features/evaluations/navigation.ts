import { Gavel, Link2, Plus } from 'lucide-react'
import { EVAL_PORTAL_ROUTE } from './constants'

/** M2 evaluation navigation exports for M3 layout aggregation. */
export const evaluationNavigation = [
  {
    key: '/evaluation',
    label: '评标工作台',
    icon: Gavel,
    section: 'main' as const,
    owner: 'M2' as const,
  },
  {
    key: '/evaluation/create',
    label: '创建评标任务',
    icon: Plus,
    section: 'main' as const,
    owner: 'M2' as const,
  },
  {
    key: EVAL_PORTAL_ROUTE,
    label: '供应商门户（外部）',
    icon: Link2,
    section: 'main' as const,
    owner: 'M2' as const,
  },
]

export default evaluationNavigation
