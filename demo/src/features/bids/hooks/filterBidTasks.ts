import dayjs from 'dayjs'
import type { BidQuickFilter, BidStatusFilter, BidTaskViewModel } from '../types'

export function deadlineDays(deadline: string, now = dayjs()) {
  return dayjs(deadline).startOf('day').diff(now.startOf('day'), 'day')
}

export function filterBidTasks(
  tasks: BidTaskViewModel[],
  options: {
    statusFilter: BidStatusFilter | string
    keyword: string
    assignee: string
    quickFilter: BidQuickFilter | string
    currentUserName: string
    includeArchived?: boolean
  },
) {
  const {
    statusFilter,
    keyword,
    assignee,
    quickFilter,
    currentUserName,
    includeArchived = false,
  } = options

  return tasks.filter(task => {
    if (!includeArchived && task.status === 'archived') return false

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active'
        ? task.status !== 'completed' && task.status !== 'archived'
        : task.status === statusFilter)

    const normalizedKeyword = keyword.trim().toLowerCase()
    const matchesKeyword =
      !normalizedKeyword ||
      [task.projectName, task.tenderNo, task.tenderEntity].some(value =>
        String(value).toLowerCase().includes(normalizedKeyword),
      )

    const matchesAssignee = assignee === 'all' || task.assignee === assignee
    const days = deadlineDays(task.deadline)
    const matchesQuick =
      quickFilter === 'all' ||
      (quickFilter === 'mine' && task.assignee === currentUserName) ||
      (quickFilter === 'due' && task.status !== 'completed' && task.status !== 'archived' && days >= 0 && days <= 14) ||
      (quickFilter === 'risk' &&
        task.status !== 'completed' &&
        task.status !== 'archived' &&
        (task.materialMissing > 0 || days < 0))

    return matchesStatus && matchesKeyword && matchesAssignee && matchesQuick
  })
}

export function buildDashboardStats(tasks: BidTaskViewModel[]) {
  const visible = tasks.filter(task => task.status !== 'archived')
  return {
    total: visible.length,
    active: visible.filter(t => t.status !== 'completed').length,
    aiReview: visible.filter(t => t.status === 'ai_review').length,
    completed: visible.filter(t => t.status === 'completed').length,
    archived: tasks.filter(t => t.status === 'archived').length,
  }
}

export function formatDeadlineText(task: BidTaskViewModel) {
  if (task.status === 'completed' || task.status === 'archived') {
    return task.status === 'archived' ? '已归档' : '已完成'
  }
  const days = deadlineDays(task.deadline)
  if (days < 0) return `已逾期 ${Math.abs(days)} 天`
  if (days === 0) return '今天截止'
  return `剩余 ${days} 天`
}
