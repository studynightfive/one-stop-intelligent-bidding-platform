import type { BidTaskViewModel } from '../types'
import type { BidApiPort } from './bidApiPort'
import { newIdempotencyKey, sha256Hex } from './cryptoUtils'
import { filterTasksForListQuery, paginateItems } from './paginateLocal'
import type {
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

type SessionRecord = UploadSession & { parts: Map<number, UploadPart>; sha256: string; mimeType: string }

const DEFAULT_PART_SIZE = 256 * 1024

let taskSource: () => BidTaskViewModel[] = () => []
const sessions = new Map<string, SessionRecord>()
const versionsByTask = new Map<string, DocumentVersion[]>()
const fileBlobs = new Map<string, Blob>()

export function setMockBidTaskSource(getter: () => BidTaskViewModel[]) {
  taskSource = getter
}

export function resetMockBidApiState() {
  sessions.clear()
  versionsByTask.clear()
  fileBlobs.clear()
}

function delay(ms = 40) {
  return new Promise<void>(resolve => window.setTimeout(resolve, ms))
}

function ensureSeedVersions(taskId: string): DocumentVersion[] {
  if (!versionsByTask.has(taskId)) {
    const now = new Date().toISOString()
    versionsByTask.set(taskId, [
      {
        id: `${taskId}-ver-3`,
        documentId: `${taskId}-doc-merged`,
        versionNumber: 3,
        file: {
          id: `${taskId}-file-3`,
          fileName: '投标文件-v3.docx',
          mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          sizeBytes: 102400,
          sha256: 'a'.repeat(64),
          scanStatus: 'clean',
          createdAt: now,
        },
        changeSummary: '按 AI 审核建议修正工期与多租户方案',
        createdBy: { id: 'U-01', name: '张明远' },
        createdAt: now,
      },
      {
        id: `${taskId}-ver-2`,
        documentId: `${taskId}-doc-merged`,
        versionNumber: 2,
        file: {
          id: `${taskId}-file-2`,
          fileName: '投标文件-v2.docx',
          mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          sizeBytes: 98000,
          sha256: 'b'.repeat(64),
          scanStatus: 'clean',
          createdAt: now,
        },
        changeSummary: '更新报价表，修正对象存储单价',
        createdBy: { id: 'U-01', name: '张明远' },
        createdAt: now,
      },
      {
        id: `${taskId}-ver-1`,
        documentId: `${taskId}-doc-merged`,
        versionNumber: 1,
        file: {
          id: `${taskId}-file-1`,
          fileName: '投标文件-v1.docx',
          mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          sizeBytes: 90000,
          sha256: 'c'.repeat(64),
          scanStatus: 'clean',
          createdAt: now,
        },
        changeSummary: '完成全部材料上传，生成完整投标文件',
        createdBy: { id: 'U-01', name: '张明远' },
        createdAt: now,
      },
    ])
  }
  return versionsByTask.get(taskId)!
}

export function createMockBidApi(): BidApiPort {
  return {
    async listBidTasks(query: ListBidTasksQuery): Promise<PageResult<BidTaskViewModel>> {
      await delay(30)
      const filtered = filterTasksForListQuery(taskSource(), query)
      return paginateItems(filtered, query.page ?? 1, query.pageSize ?? 20)
    },

    async createUploadSession(body: CreateUploadSessionRequest): Promise<UploadSession> {
      await delay()
      const totalParts = Math.max(1, Math.ceil(body.sizeBytes / DEFAULT_PART_SIZE))
      const id = `upl-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      const session: SessionRecord = {
        id,
        fileName: body.fileName,
        sizeBytes: body.sizeBytes,
        partSizeBytes: DEFAULT_PART_SIZE,
        totalParts,
        uploadedParts: [],
        status: 'created',
        expiresAt: new Date(Date.now() + 3600_000).toISOString(),
        parts: new Map(),
        sha256: body.sha256,
        mimeType: body.mimeType,
      }
      sessions.set(id, session)
      return { ...session, uploadedParts: [] }
    },

    async getUploadSession(uploadId: string): Promise<UploadSession> {
      const session = sessions.get(uploadId)
      if (!session) throw new Error('UPLOAD_SESSION_NOT_FOUND')
      return {
        id: session.id,
        fileName: session.fileName,
        sizeBytes: session.sizeBytes,
        partSizeBytes: session.partSizeBytes,
        totalParts: session.totalParts,
        uploadedParts: Array.from(session.parts.values()).sort((a, b) => a.partNumber - b.partNumber),
        status: session.status,
        expiresAt: session.expiresAt,
      }
    },

    async uploadPart(uploadId: string, partNumber: number, _blob: Blob): Promise<UploadPart> {
      await delay(20)
      const session = sessions.get(uploadId)
      if (!session) throw new Error('UPLOAD_SESSION_NOT_FOUND')
      if (session.status === 'cancelled' || session.status === 'failed') throw new Error('UPLOAD_SESSION_INVALID')
      session.status = 'uploading'
      const part: UploadPart = { partNumber, etag: `etag-${uploadId}-${partNumber}` }
      session.parts.set(partNumber, part)
      session.uploadedParts = Array.from(session.parts.values())
      return part
    },

    async completeUpload(uploadId: string, parts: UploadPart[], _idempotencyKey: string): Promise<FileRef> {
      await delay(40)
      const session = sessions.get(uploadId)
      if (!session) throw new Error('UPLOAD_SESSION_NOT_FOUND')
      if (parts.length < session.totalParts) throw new Error('UPLOAD_INCOMPLETE')
      session.status = 'verifying'
      await delay(30)
      session.status = 'scanning'
      await delay(30)
      session.status = 'completed'
      const file: FileRef = {
        id: `file-${uploadId}`,
        fileName: session.fileName,
        mimeType: session.mimeType,
        sizeBytes: session.sizeBytes,
        sha256: session.sha256,
        scanStatus: 'clean',
        createdAt: new Date().toISOString(),
      }
      fileBlobs.set(file.id, new Blob([`demo-file:${session.fileName}`], { type: session.mimeType }))
      return file
    },

    async cancelUpload(uploadId: string): Promise<void> {
      const session = sessions.get(uploadId)
      if (!session) return
      session.status = 'cancelled'
    },

    async uploadFile(file, purpose: UploadPurpose, options) {
      const onProgress = options?.onProgress
      onProgress?.({ status: 'hashing', percent: 0, uploadedParts: 0, totalParts: 0 })
      const sha256 = await sha256Hex(file)
      if (options?.signal?.aborted) throw new Error('UPLOAD_ABORTED')
      const session = await this.createUploadSession({
        fileName: file.name,
        mimeType: file.type || 'application/octet-stream',
        sizeBytes: file.size,
        sha256,
        purpose,
        resourceId: options?.resourceId,
      })
      onProgress?.({
        uploadId: session.id,
        status: 'uploading',
        percent: 5,
        uploadedParts: 0,
        totalParts: session.totalParts,
      })
      const parts: UploadPart[] = []
      for (let partNumber = 1; partNumber <= session.totalParts; partNumber += 1) {
        if (options?.signal?.aborted) {
          await this.cancelUpload(session.id)
          throw new Error('UPLOAD_ABORTED')
        }
        const start = (partNumber - 1) * session.partSizeBytes
        const blob = file.slice(start, start + session.partSizeBytes)
        const part = await this.uploadPart(session.id, partNumber, blob)
        parts.push(part)
        onProgress?.({
          uploadId: session.id,
          status: 'uploading',
          percent: Math.min(95, Math.round((partNumber / session.totalParts) * 90) + 5),
          uploadedParts: partNumber,
          totalParts: session.totalParts,
        })
      }
      onProgress?.({
        uploadId: session.id,
        status: 'verifying',
        percent: 96,
        uploadedParts: parts.length,
        totalParts: session.totalParts,
      })
      const fileRef = await this.completeUpload(session.id, parts, newIdempotencyKey('upload'))
      onProgress?.({
        uploadId: session.id,
        status: 'completed',
        percent: 100,
        uploadedParts: parts.length,
        totalParts: session.totalParts,
      })
      return fileRef
    },

    async generateDocuments(taskId, body: GenerateBidDocumentRequest, _idempotencyKey: string): Promise<JobRef> {
      await delay(200)
      const list = ensureSeedVersions(taskId)
      const nextNumber = (list[0]?.versionNumber || 0) + 1
      const version: DocumentVersion = {
        id: `${taskId}-ver-${nextNumber}`,
        documentId: `${taskId}-doc-merged`,
        versionNumber: nextNumber,
        file: {
          id: `${taskId}-file-${nextNumber}`,
          fileName: `投标文件-v${nextNumber}.docx`,
          mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          sizeBytes: 110000,
          sha256: `${nextNumber}`.padStart(64, 'd'),
          scanStatus: 'clean',
          createdAt: new Date().toISOString(),
        },
        changeSummary: `生成模式 ${body.mode}，章节 ${body.sections.join('/')}`,
        createdBy: { id: 'U-01', name: '张明远' },
        createdAt: new Date().toISOString(),
      }
      versionsByTask.set(taskId, [version, ...list])
      fileBlobs.set(
        version.file.id,
        new Blob(
          [`${taskId}\nmode=${body.mode}\nsections=${body.sections.join(',')}\nversion=${nextNumber}\n`],
          { type: version.file.mimeType },
        ),
      )
      return {
        id: `job-gen-${nextNumber}`,
        type: 'bid_generate',
        status: 'succeeded',
        progressPercent: 100,
        currentStep: 'done',
        result: { versionId: version.id, versionNumber: nextNumber },
        createdAt: new Date().toISOString(),
      }
    },

    async listDocumentVersions(taskId, query) {
      await delay(20)
      const list = ensureSeedVersions(taskId)
      return paginateItems(list, query?.page ?? 1, query?.pageSize ?? 20)
    },

    async compareDocumentVersions(taskId, fromVersionId, toVersionId): Promise<DocumentDiff> {
      await delay(40)
      const list = ensureSeedVersions(taskId)
      const from = list.find(item => item.id === fromVersionId)
      const to = list.find(item => item.id === toVersionId)
      if (!from || !to) throw new Error('DOCUMENT_VERSION_NOT_FOUND')
      return {
        from,
        to,
        changes: [
          {
            section: '商务标/报价表',
            type: 'changed',
            before: from.changeSummary,
            after: to.changeSummary,
          },
          {
            section: '技术标/实施方案',
            type: 'changed',
            before: `v${from.versionNumber}`,
            after: `v${to.versionNumber}`,
          },
          {
            section: '目录页码',
            type: 'added',
            after: '新增材料索引 3 处',
          },
        ],
      }
    },

    async rollbackDocumentVersion(taskId, versionId, reason, _idempotencyKey): Promise<JobRef> {
      await delay(120)
      if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('forceConflict') === '1') {
        const err = new Error('VERSION_CONFLICT') as Error & { code?: string }
        err.code = 'VERSION_CONFLICT'
        throw err
      }
      const list = ensureSeedVersions(taskId)
      const target = list.find(item => item.id === versionId)
      if (!target) throw new Error('DOCUMENT_VERSION_NOT_FOUND')
      const nextNumber = (list[0]?.versionNumber || 0) + 1
      const rolled: DocumentVersion = {
        ...target,
        id: `${taskId}-ver-${nextNumber}`,
        versionNumber: nextNumber,
        changeSummary: `回滚自 v${target.versionNumber}：${reason}`,
        createdAt: new Date().toISOString(),
        file: {
          ...target.file,
          id: `${taskId}-file-${nextNumber}`,
          fileName: `投标文件-v${nextNumber}.docx`,
          createdAt: new Date().toISOString(),
        },
      }
      versionsByTask.set(taskId, [rolled, ...list])
      return {
        id: `job-rollback-${nextNumber}`,
        type: 'bid_document_rollback',
        status: 'succeeded',
        progressPercent: 100,
        result: { versionId: rolled.id },
        createdAt: new Date().toISOString(),
      }
    },

    async downloadDocumentBlob(taskId, documentId): Promise<Blob> {
      await delay(20)
      const list = ensureSeedVersions(taskId)
      const version = list.find(item => item.id === documentId || item.documentId === documentId || item.file.id === documentId)
      if (version && fileBlobs.has(version.file.id)) return fileBlobs.get(version.file.id)!
      return new Blob([`${taskId} document ${documentId}`], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      })
    },
  }
}
