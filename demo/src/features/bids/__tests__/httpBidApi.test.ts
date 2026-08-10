import { describe, expect, it, vi } from 'vitest'
import { ApiClient } from '../../../api/client'
import { createHttpBidApi } from '../adapters/httpBidApi'

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'server-request' },
  })
}

const now = '2026-08-11T00:00:00Z'

describe('httpBidApi', () => {
  it('lists tasks through the shared client and maps the contract view model', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({
      success: true,
      data: [{
        id: 'TASK-2026-002',
        projectName: '数字化转型咨询服务',
        tenderNo: 'HNZX-2026-0089',
        tenderEntity: '工业互联网协会',
        deadline: '2026-08-15T17:00:00Z',
        status: 'ai_review',
        currentStep: 6,
        progressPercent: 80,
        assignee: { id: 'U1', name: '演示管理员', role: 'admin' },
        tags: ['AI逐段生成'],
        materialSummary: { total: 4, have: 4, missing: 0 },
        version: 1,
        createdAt: now,
        updatedAt: now,
      }],
      meta: { page: 1, pageSize: 20, total: 1, totalPages: 1 },
      requestId: 'list-request',
    })) as unknown as typeof fetch
    const api = createHttpBidApi(new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock }))

    const result = await api.listBidTasks({ page: 1, pageSize: 20, status: 'all', quickFilter: 'mine' })

    expect(result.data[0]).toMatchObject({
      id: 'TASK-2026-002',
      progress: 80,
      materialTotal: 4,
      materialHave: 4,
    })
    expect(String(vi.mocked(fetchMock).mock.calls[0][0])).toContain('quickFilter=my')
    expect(String(vi.mocked(fetchMock).mock.calls[0][0])).not.toContain('status=all')
  })

  it('runs the real resumable protocol with raw binary parts', async () => {
    const uploadedBodies: Blob[] = []
    const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
      const url = String(request)
      if (url.endsWith('/files/upload-sessions') && init?.method === 'POST') {
        return jsonResponse({
          success: true,
          data: {
            id: 'UPLOAD-1',
            fileName: 'architecture.png',
            sizeBytes: 6,
            partSizeBytes: 4,
            totalParts: 2,
            uploadedParts: [],
            status: 'created',
            expiresAt: now,
          },
          requestId: 'session-request',
        }, 201)
      }
      if (url.includes('/parts/')) {
        uploadedBodies.push(init?.body as Blob)
        const partNumber = Number(url.slice(url.lastIndexOf('/') + 1))
        return jsonResponse({
          success: true,
          data: { partNumber, etag: `etag-${partNumber}` },
          requestId: `part-${partNumber}`,
        })
      }
      if (url.endsWith('/complete')) {
        return jsonResponse({
          success: true,
          data: {
            id: 'FILE-1',
            fileName: 'architecture.png',
            mimeType: 'image/png',
            sizeBytes: 6,
            sha256: 'a'.repeat(64),
            scanStatus: 'clean',
            createdAt: now,
          },
          requestId: 'complete-request',
        })
      }
      throw new Error(`Unexpected request: ${init?.method} ${url}`)
    }) as unknown as typeof fetch
    const api = createHttpBidApi(new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock }))
    const progress: number[] = []

    const file = new File(['abcdef'], 'architecture.png', { type: 'image/png' })
    const result = await api.uploadFile(file, 'bidIllustration', {
      resourceId: 'TASK-2026-002',
      onProgress: value => progress.push(value.percent),
    })

    expect(result.id).toBe('FILE-1')
    expect(uploadedBodies.map(body => body.size)).toEqual([4, 2])
    expect(progress[progress.length - 1]).toBe(100)
    const sessionCall = vi.mocked(fetchMock).mock.calls.find(([, init]) => init?.method === 'POST')
    const sessionBody = JSON.parse(String(sessionCall?.[1]?.body))
    expect(sessionBody.purpose).toBe('bidIllustration')
    expect(sessionBody.resourceId).toBe('TASK-2026-002')
    expect(sessionBody.sha256).toMatch(/^[a-f0-9]{64}$/)
    const partCall = vi.mocked(fetchMock).mock.calls.find(([request]) => String(request).includes('/parts/'))
    expect(new Headers(partCall?.[1]?.headers).get('Content-Type')).toBe('application/octet-stream')
  })

  it('uses the document, version and job endpoints without mock injection', async () => {
    const job = {
      id: 'JOB-1',
      type: 'document_generation',
      status: 'succeeded' as const,
      progressPercent: 100,
      currentStep: 'done',
      result: { versionNumber: 1 },
      createdAt: now,
    }
    const version = {
      id: 'VERSION-1',
      documentId: 'DOCUMENT-1',
      versionNumber: 1,
      file: {
        id: 'FILE-1',
        fileName: '技术标.docx',
        mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        sizeBytes: 1024,
        sha256: 'a'.repeat(64),
        scanStatus: 'clean' as const,
        createdAt: now,
      },
      changeSummary: 'AI逐段生成',
      createdBy: { id: 'U1', name: '演示管理员' },
      createdAt: now,
    }
    const task = {
      id: 'TASK-NEW',
      projectName: '新建项目',
      tenderNo: 'NEW-001',
      tenderEntity: '采购单位',
      deadline: now,
      status: 'material_prep' as const,
      currentStep: 3,
      progressPercent: 35,
      assignee: { id: 'U1', name: '演示管理员' },
      tags: ['AI解析'],
      materialSummary: { total: 4, have: 0, missing: 4 },
      version: 2,
      createdAt: now,
      updatedAt: now,
    }
    const fetchMock = vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
      const url = String(request)
      if (url.endsWith('/bid-tasks') && init?.method === 'POST') {
        return jsonResponse({ success: true, data: task, requestId: 'create-request' }, 201)
      }
      if (url.endsWith('/bid-tasks/TASK-NEW') && init?.method === 'GET') {
        return jsonResponse({ success: true, data: task, requestId: 'detail-request' })
      }
      if (url.endsWith('/bid-tasks/TASK-NEW/parse') && init?.method === 'POST') {
        return jsonResponse({ success: true, data: job, requestId: 'parse-request' }, 202)
      }
      if (url.endsWith('/bid-tasks/TASK-NEW/reviews') && init?.method === 'POST') {
        return jsonResponse({ success: true, data: job, requestId: 'review-request' }, 202)
      }
      if (url.endsWith('/documents') && init?.method === 'POST') {
        return jsonResponse({ success: true, data: job, requestId: 'generate-request' }, 202)
      }
      if (url.endsWith('/document-versions?page=1&pageSize=20')) {
        return jsonResponse({
          success: true,
          data: [version],
          meta: { page: 1, pageSize: 20, total: 1, totalPages: 1 },
          requestId: 'versions-request',
        })
      }
      if (url.endsWith('/jobs/JOB-LEGACY')) {
        return jsonResponse({
          id: 'JOB-LEGACY',
          type: 'document_generation',
          status: 'running',
          progress_percent: 60,
          current_step: 'paragraph 3/5',
          created_at: now,
        })
      }
      if (url.endsWith('/documents/DOCUMENT-1/download')) {
        return new Response(new Blob(['docx']), { status: 200 })
      }
      throw new Error(`Unexpected request: ${init?.method} ${url}`)
    }) as unknown as typeof fetch
    const api = createHttpBidApi(new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock }))

    await expect(api.createBidTask({
      projectName: task.projectName,
      tenderNo: task.tenderNo,
      tenderEntity: task.tenderEntity,
      deadline: now,
      assigneeId: 'U1',
      tenderFileId: 'FILE-TENDER',
    })).resolves.toMatchObject({ id: 'TASK-NEW', progress: 35 })
    await expect(api.getBidTask('TASK-NEW')).resolves.toMatchObject({ id: 'TASK-NEW' })
    await expect(api.parseBidTask('TASK-NEW', 'parse-key')).resolves.toEqual(job)
    await expect(api.startBidReview('TASK-NEW', {
      types: ['signature', 'price', 'content', 'consistency'],
      fileVersionIds: [],
    }, 'review-key')).resolves.toEqual(job)
    await expect(api.generateDocuments('TASK-2026-002', {
      mode: 'split',
      sections: ['technical'],
      templateMode: 'tender_requirement',
      includeWatermark: false,
    }, 'generate-idempotency')).resolves.toEqual(job)
    await expect(api.listDocumentVersions('TASK-2026-002', { page: 1, pageSize: 20 })).resolves.toMatchObject({
      data: [version],
    })
    await expect(api.getJob('JOB-LEGACY')).resolves.toMatchObject({
      id: 'JOB-LEGACY',
      progressPercent: 60,
      currentStep: 'paragraph 3/5',
    })
    await expect(api.downloadDocumentBlob('TASK-2026-002', 'DOCUMENT-1')).resolves.toBeInstanceOf(Blob)
    const parseCall = vi.mocked(fetchMock).mock.calls.find(([request]) => String(request).endsWith('/parse'))
    expect(new Headers(parseCall?.[1]?.headers).get('Idempotency-Key')).toBe('parse-key')
    const reviewCall = vi.mocked(fetchMock).mock.calls.find(([request]) => String(request).endsWith('/reviews'))
    expect(JSON.parse(String(reviewCall?.[1]?.body)).types).toContain('consistency')
  })
})
