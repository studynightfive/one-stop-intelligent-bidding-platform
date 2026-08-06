import { beforeEach, describe, expect, it } from 'vitest'
import { createMockBidApi, resetMockBidApiState, setMockBidTaskSource } from '../adapters/mockBidApi'
import { filterTasksForListQuery, paginateItems } from '../adapters/paginateLocal'
import type { BidTaskViewModel } from '../types'

const sampleTasks: BidTaskViewModel[] = [
  {
    id: 'T1',
    projectName: '政务云',
    tenderNo: 'A-1',
    tenderEntity: '局',
    deadline: '2099-01-01',
    status: 'material_prep',
    currentStep: 3,
    progress: 40,
    assignee: '张明远',
    materialTotal: 10,
    materialHave: 5,
    materialMissing: 5,
  },
  {
    id: 'T2',
    projectName: '归档项目',
    tenderNo: 'A-2',
    tenderEntity: '局',
    deadline: '2099-01-01',
    status: 'archived',
    currentStep: 7,
    progress: 100,
    assignee: '李雪琴',
    materialTotal: 10,
    materialHave: 10,
    materialMissing: 0,
  },
  {
    id: 'T3',
    projectName: '审核中',
    tenderNo: 'B-1',
    tenderEntity: '委',
    deadline: '2099-01-10',
    status: 'ai_review',
    currentStep: 6,
    progress: 80,
    assignee: '张明远',
    materialTotal: 10,
    materialHave: 9,
    materialMissing: 1,
  },
]

describe('paginateLocal', () => {
  it('builds pagination meta and slices page', () => {
    const page = paginateItems([1, 2, 3, 4, 5], 2, 2)
    expect(page.meta).toEqual({ page: 2, pageSize: 2, total: 5, totalPages: 3 })
    expect(page.data).toEqual([3, 4])
  })

  it('filters by status and keyword for list query', () => {
    const filtered = filterTasksForListQuery(sampleTasks, { status: 'ai_review', keyword: '审核' })
    expect(filtered.map(item => item.id)).toEqual(['T3'])
  })
})

describe('mockBidApi', () => {
  beforeEach(() => {
    resetMockBidApiState()
    setMockBidTaskSource(() => sampleTasks)
  })

  it('lists bid tasks with server-shaped pagination', async () => {
    const api = createMockBidApi()
    const result = await api.listBidTasks({ page: 1, pageSize: 1, status: 'all' })
    expect(result.meta.total).toBe(2) // archived excluded
    expect(result.data).toHaveLength(1)
    expect(result.requestId).toBeTruthy()
  })

  it('runs resumable upload session protocol', async () => {
    const api = createMockBidApi()
    const file = new File(['hello-tender-file-content'], 'tender.pdf', { type: 'application/pdf' })
    const events: string[] = []
    const ref = await api.uploadFile(file, 'tender', {
      onProgress: p => events.push(p.status),
    })
    expect(ref.fileName).toBe('tender.pdf')
    expect(ref.scanStatus).toBe('clean')
    expect(events).toContain('hashing')
    expect(events).toContain('uploading')
    expect(events[events.length - 1]).toBe('completed')
  })

  it('generates compares and rolls back document versions', async () => {
    const api = createMockBidApi()
    const taskId = 'TASK-DOC'
    const before = await api.listDocumentVersions(taskId)
    expect(before.data.length).toBeGreaterThan(0)
    const job = await api.generateDocuments(
      taskId,
      {
        mode: 'merged',
        sections: ['qualification', 'commercial', 'technical'],
        templateMode: 'tender_requirement',
        includeWatermark: false,
      },
      'idem-1',
    )
    expect(job.status).toBe('succeeded')
    const after = await api.listDocumentVersions(taskId)
    expect(after.data[0].versionNumber).toBeGreaterThan(before.data[0].versionNumber)

    const fromId = after.data[1].id
    const toId = after.data[0].id
    const diff = await api.compareDocumentVersions(taskId, fromId, toId)
    expect(diff.changes.length).toBeGreaterThan(0)

    const rollback = await api.rollbackDocumentVersion(taskId, fromId, '演示回滚', 'idem-2')
    expect(rollback.status).toBe('succeeded')
    const latest = await api.listDocumentVersions(taskId)
    expect(latest.data[0].changeSummary).toContain('回滚')
  })
})
