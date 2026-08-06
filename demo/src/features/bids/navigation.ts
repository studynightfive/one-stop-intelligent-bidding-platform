import { LayoutDashboard, Plus } from 'lucide-react'

/** Bid-domain navigation exports for M3 layout aggregation. */
export const bidNavigation = [
  {
    key: '/dashboard',
    label: '投标工作台',
    icon: LayoutDashboard,
    section: 'main' as const,
    owner: 'M1' as const,
  },
  {
    key: '/tasks/create',
    label: '新建投标',
    icon: Plus,
    section: 'main' as const,
    owner: 'M1' as const,
    hiddenInSidebar: true,
  },
]

export default bidNavigation
