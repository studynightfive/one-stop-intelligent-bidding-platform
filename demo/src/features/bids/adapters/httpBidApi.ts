import { apiClient, type ApiClient } from '../../../api/client'
import type { BidTaskViewModel } from '../types'
import type { BidApiPort } from './bidApiPort'
import { newIdempotencyKey, sha256Hex } from './cryptoUtils'
import { mapBidTaskToViewModel } from './mapBidTask'
import type {
  BidTaskApi,
  CreateBidReviewRequest,
  CreateBidTaskRequest,
  CreateUploadSessionRequest,
  DocumentDiff,
  DocumentVersion,
  FileRef,
  GenerateBidDocumentRequest,
  JobRef,
  ListBidTasksQuery,
  PageResult,
  UploadPart,
  UploadProgress,
  UploadPurpose,
  UploadSession,
} from './schemaTypes'

type LegacyJobResponse = {
  id: string
  type: string
  status: JobRef['status']
  progress_percent: number
  current_step?: string | null
  result?: Record<string, unknown> | null
  error?: JobRef['error'] | null
  created_at: string
}

function normalizeJob(value: JobRef | LegacyJobResponse): JobRef {
  if ('progressPercent' in value) return value
  return {
    id: String(value.id),
    type: value.type,
    status: value.status,
    progressPercent: value.progress_percent,
    currentStep: value.current_step || undefined,
    result: value.result || undefined,
    error: value.error || undefined,
    createdAt: value.created_at,
  }
}

function listQuery(query: ListBidTasksQuery) {
  const mappedQuickFilter = query.quickFilter === 'mine'
    ? 'my'
    : query.quickFilter === 'due'
      ? 'due_soon'
      : undefined
  return {
    page: query.page,
    pageSize: query.pageSize,
    sortBy: query.sortBy,
    sortOrder: query.sortOrder,
    keyword: query.keyword || undefined,
    status: query.status && !['all', 'active'].includes(query.status) ? query.status : undefined,
    assigneeId: query.assigneeId,
    quickFilter: mappedQuickFilter,
  }
}

function abortError(): Error {
  return new DOMException('Upload cancelled', 'AbortError')
}

function wait(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(abortError())
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, milliseconds)
    signal?.addEventListener('abort', () => {
      window.clearTimeout(timer)
      reject(abortError())
    }, { once: true })
  })
}

async function uploadPartWithRetry(
  adapter: BidApiPort,
  uploadId: string,
  partNumber: number,
  blob: Blob,
  signal?: AbortSignal,
): Promise<UploadPart> {
  let lastError: unknown
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    if (signal?.aborted) throw abortError()
    try {
      return await adapter.uploadPart(uploadId, partNumber, blob)
    } catch (error) {
      lastError = error
      if (attempt < 3) await wait(250 * 2 ** (attempt - 1), signal)
    }
  }
  throw lastError
}

export function createHttpBidApi(client: ApiClient = apiClient): BidApiPort {
  const adapter: BidApiPort = {
    async listBidTasks(query: ListBidTasksQuery): Promise<PageResult<BidTaskViewModel>> {
      const page = await client.getPage<BidTaskApi[]>('/bid-tasks', { query: listQuery(query) })
      return { ...page, data: page.data.map(mapBidTaskToViewModel) }
    },

    async getBidTask(taskId: string): Promise<BidTaskViewModel> {
      const task = await client.get<BidTaskApi>(`/bid-tasks/${encodeURIComponent(taskId)}`)
      return mapBidTaskToViewModel(task)
    },

    async createBidTask(body: CreateBidTaskRequest): Promise<BidTaskViewModel> {
      const task = await client.post<BidTaskApi>('/bid-tasks', body)
      return mapBidTaskToViewModel(task)
    },

    parseBidTask(taskId: string, idempotencyKey: string): Promise<JobRef> {
      return client.post(`/bid-tasks/${encodeURIComponent(taskId)}/parse`, undefined, { idempotencyKey })
    },

    startBidReview(
      taskId: string,
      body: CreateBidReviewRequest,
      idempotencyKey: string,
    ): Promise<JobRef> {
      return client.post(`/bid-tasks/${encodeURIComponent(taskId)}/reviews`, body, { idempotencyKey })
    },

    createUploadSession(body: CreateUploadSessionRequest): Promise<UploadSession> {
      return client.post('/files/upload-sessions', body)
    },

    getUploadSession(uploadId: string): Promise<UploadSession> {
      return client.get(`/files/upload-sessions/${encodeURIComponent(uploadId)}`)
    },

    uploadPart(uploadId: string, partNumber: number, blob: Blob): Promise<UploadPart> {
      return client.put(
        `/files/upload-sessions/${encodeURIComponent(uploadId)}/parts/${partNumber}`,
        blob,
        { bodyMode: 'raw', headers: { 'Content-Type': 'application/octet-stream' } },
      )
    },

    completeUpload(uploadId: string, parts: UploadPart[], idempotencyKey: string): Promise<FileRef> {
      return client.post(
        `/files/upload-sessions/${encodeURIComponent(uploadId)}/complete`,
        { parts },
        { idempotencyKey },
      )
    },

    cancelUpload(uploadId: string): Promise<void> {
      return client.delete(`/files/upload-sessions/${encodeURIComponent(uploadId)}`)
    },

    async uploadFile(
      file: File,
      purpose: UploadPurpose,
      options?: { resourceId?: string; onProgress?: (progress: UploadProgress) => void; signal?: AbortSignal },
    ): Promise<FileRef> {
      const onProgress = options?.onProgress
      onProgress?.({ status: 'hashing', percent: 0, uploadedParts: 0, totalParts: 0 })
      const sha256 = await sha256Hex(file)
      if (options?.signal?.aborted) throw abortError()

      let uploadId: string | undefined
      try {
        const session = await adapter.createUploadSession({
          fileName: file.name,
          mimeType: file.type || 'application/octet-stream',
          sizeBytes: file.size,
          sha256,
          purpose,
          resourceId: options?.resourceId,
        })
        uploadId = session.id
        onProgress?.({
          uploadId,
          status: 'uploading',
          percent: 5,
          uploadedParts: 0,
          totalParts: session.totalParts,
        })

        const alreadyUploaded = new Map(session.uploadedParts.map(part => [part.partNumber, part]))
        const parts: UploadPart[] = []
        for (let partNumber = 1; partNumber <= session.totalParts; partNumber += 1) {
          if (options?.signal?.aborted) throw abortError()
          const existing = alreadyUploaded.get(partNumber)
          const part = existing || await uploadPartWithRetry(
            adapter,
            session.id,
            partNumber,
            file.slice((partNumber - 1) * session.partSizeBytes, partNumber * session.partSizeBytes),
            options?.signal,
          )
          parts.push(part)
          onProgress?.({
            uploadId,
            status: 'uploading',
            percent: Math.min(95, Math.round((partNumber / session.totalParts) * 90) + 5),
            uploadedParts: partNumber,
            totalParts: session.totalParts,
          })
        }

        onProgress?.({
          uploadId,
          status: 'verifying',
          percent: 96,
          uploadedParts: parts.length,
          totalParts: session.totalParts,
        })
        const fileRef = await adapter.completeUpload(session.id, parts, newIdempotencyKey('upload'))
        onProgress?.({
          uploadId,
          status: 'completed',
          percent: 100,
          uploadedParts: parts.length,
          totalParts: session.totalParts,
        })
        return fileRef
      } catch (error) {
        if (uploadId) {
          try {
            await adapter.cancelUpload(uploadId)
          } catch {
            // Preserve the original upload error.
          }
        }
        if (options?.signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) {
          throw Object.assign(new Error('UPLOAD_ABORTED'), { cause: error })
        }
        throw error
      }
    },

    generateDocuments(
      taskId: string,
      body: GenerateBidDocumentRequest,
      idempotencyKey: string,
    ): Promise<JobRef> {
      return client.post(`/bid-tasks/${encodeURIComponent(taskId)}/documents`, body, { idempotencyKey })
    },

    async getJob(jobId: string): Promise<JobRef> {
      const result = await client.get<JobRef | LegacyJobResponse>(`/jobs/${encodeURIComponent(jobId)}`)
      return normalizeJob(result)
    },

    async listDocumentVersions(taskId, query) {
      return client.getPage<DocumentVersion[]>(`/bid-tasks/${encodeURIComponent(taskId)}/document-versions`, {
        query,
      })
    },

    compareDocumentVersions(taskId, fromVersionId, toVersionId): Promise<DocumentDiff> {
      return client.get(`/bid-tasks/${encodeURIComponent(taskId)}/document-versions/compare`, {
        query: { fromVersionId, toVersionId },
      })
    },

    rollbackDocumentVersion(taskId, versionId, reason, idempotencyKey): Promise<JobRef> {
      return client.post(
        `/bid-tasks/${encodeURIComponent(taskId)}/document-versions/${encodeURIComponent(versionId)}/rollback`,
        { reason },
        { idempotencyKey },
      )
    },

    downloadDocumentBlob(taskId, documentId): Promise<Blob> {
      return client.get(
        `/bid-tasks/${encodeURIComponent(taskId)}/documents/${encodeURIComponent(documentId)}/download`,
        { responseType: 'blob' },
      )
    },
  }
  return adapter
}
