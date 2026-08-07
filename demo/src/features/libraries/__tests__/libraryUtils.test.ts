import { describe, expect, it } from 'vitest'
import dayjs from 'dayjs'
import { appendLibraryVersion, deriveQualificationStatus, nextDocumentVersion, paginate, qualificationRemainingDays, rankFragmentsSemantic } from '../utils'

describe('qualification status', () => {
  const now = dayjs('2026-08-07')

  it('derives permanent, expired, warning and valid states dynamically', () => {
    expect(deriveQualificationStatus('-', 60, now)).toBe('permanent')
    expect(deriveQualificationStatus('2026-08-06', 60, now)).toBe('expired')
    expect(deriveQualificationStatus('2026-09-01', 30, now)).toBe('expiring')
    expect(deriveQualificationStatus('2027-01-01', 90, now)).toBe('valid')
    expect(qualificationRemainingDays('2026-08-17', now)).toBe(10)
  })
})
describe('semantic fragment search', () => {
  const fragments = [
    { id: 'F1', title: '政务云等保三级安全方案', category: '解决方案', preview: '包含网络隔离、数据加密与安全审计', tags: ['政务云', '等保'], useCount: 1, updatedAt: '2026-08-01' },
    { id: 'F2', title: '培训计划', category: '培训方案', preview: '面向业务人员开展系统培训', tags: ['培训'], useCount: 1, updatedAt: '2026-08-01' },
  ]

  it('ranks related content first and explains the match', () => {
    const ranked = rankFragmentsSemantic(fragments, '需要政务云等保安全建设内容')
    expect(ranked[0].id).toBe('F1')
    expect(ranked[0].matchScore).toBeGreaterThan(ranked[1].matchScore || 0)
    expect(ranked[0].matchReason).toBeTruthy()
  })
})

describe('versioning and pagination', () => {
  it('increments major document versions', () => {
    expect(nextDocumentVersion('v2.4')).toBe('v3.0')
    expect(nextDocumentVersion(undefined)).toBe('v1.0')
  })

  it('prepends a complete version record', () => {
    const versions = appendLibraryVersion([], { version: 'v2.0', changeNote: '更新', fileName: 'new.docx', createdAt: 'now', createdBy: 'tester' })
    expect(versions[0]).toEqual({ version: 'v2.0', changeNote: '更新', fileName: 'new.docx', createdAt: 'now', createdBy: 'tester' })
  })

  it('clamps pagination to a valid page', () => {
    expect(paginate([1, 2, 3, 4, 5], 9, 2)).toMatchObject({ items: [5], page: 3, total: 5, totalPages: 3 })
  })
})
