import { describe, expect, it } from 'vitest'
import { buildDashboardStats, filterBidTasks } from '../hooks/filterBidTasks'
import { bidTaskListContractExample } from '../fixtures/contractExamples'

describe('filterBidTasks', () => {
  it('hides archived tasks by default', () => {
    const result = filterBidTasks(bidTaskListContractExample, {
      statusFilter: 'all',
      keyword: '',
      assignee: 'all',
      quickFilter: 'all',
      currentUserName: '张明远',
    })
    expect(result.every(task => task.status !== 'archived')).toBe(true)
    expect(result).toHaveLength(2)
  })

  it('filters by keyword against tender fields', () => {
    const result = filterBidTasks(bidTaskListContractExample, {
      statusFilter: 'all',
      keyword: '临期',
      assignee: 'all',
      quickFilter: 'all',
      currentUserName: '张明远',
      includeArchived: true,
    })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('TASK-EXAMPLE-002')
  })

  it('supports mine quick filter', () => {
    const result = filterBidTasks(bidTaskListContractExample, {
      statusFilter: 'all',
      keyword: '',
      assignee: 'all',
      quickFilter: 'mine',
      currentUserName: '张明远',
    })
    expect(result.every(task => task.assignee === '张明远')).toBe(true)
  })
})

describe('buildDashboardStats', () => {
  it('counts archived separately and excludes them from total', () => {
    const stats = buildDashboardStats(bidTaskListContractExample)
    expect(stats.total).toBe(2)
    expect(stats.archived).toBe(1)
    expect(stats.aiReview).toBe(1)
  })
})
