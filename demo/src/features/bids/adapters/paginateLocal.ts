import type { BidTaskViewModel } from '../types'
import type { ListBidTasksQuery, PaginationMeta, PageResult } from './schemaTypes'

export function buildPaginationMeta(page: number, pageSize: number, total: number): PaginationMeta {
  const safePageSize = Math.min(100, Math.max(1, pageSize || 20))
  const totalPages = Math.max(1, Math.ceil(total / safePageSize) || 1)
  const safePage = Math.min(Math.max(1, page || 1), totalPages)
  return { page: safePage, pageSize: safePageSize, total, totalPages }
}

export function paginateItems<T>(items: T[], page = 1, pageSize = 20): PageResult<T> {
  const meta = buildPaginationMeta(page, pageSize, items.length)
  const start = (meta.page - 1) * meta.pageSize
  return {
    data: items.slice(start, start + meta.pageSize),
    meta,
    requestId: `req-local-${Date.now()}`,
  }
}

/** Local filter mirroring GET /bid-tasks query params (demo until M5 serves them). */
export function filterTasksForListQuery(tasks: BidTaskViewModel[], query: ListBidTasksQuery): BidTaskViewModel[] {
  const keyword = (query.keyword || '').trim().toLowerCase()
  const status = query.status || 'all'
  const assignee = query.assigneeId || 'all'
  const quick = query.quickFilter || 'all'
  const includeArchived = query.includeArchived || status === 'archived'

  return tasks.filter(task => {
    if (!includeArchived && task.status === 'archived') return false
    if (status === 'active') {
      if (['completed', 'archived', 'failed'].includes(String(task.status))) return false
    } else if (status !== 'all' && task.status !== status) {
      return false
    }
    if (keyword) {
      const hay = `${task.projectName} ${task.tenderNo} ${task.tenderEntity}`.toLowerCase()
      if (!hay.includes(keyword)) return false
    }
    if (assignee !== 'all' && task.assignee !== assignee) return false
    if (quick === 'mine' && query.currentUserName && task.assignee !== query.currentUserName) return false
    if (quick === 'due') {
      const days = Math.ceil((new Date(task.deadline).getTime() - Date.now()) / 86400000)
      if (!(days >= 0 && days <= 7) || task.status === 'completed') return false
    }
    if (quick === 'risk' && !(task.materialMissing > 0 || task.status === 'failed')) return false
    return true
  })
}
