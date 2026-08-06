import type { BidTaskViewModel } from '../types'
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

/**
 * M1 bid domain port — shapes match OpenAPI.
 * Swap implementation in getBidApi() when M3 HTTP client is ready.
 */
export type BidApiPort = {
  listBidTasks(query: ListBidTasksQuery): Promise<PageResult<BidTaskViewModel>>

  createUploadSession(body: CreateUploadSessionRequest): Promise<UploadSession>
  getUploadSession(uploadId: string): Promise<UploadSession>
  uploadPart(uploadId: string, partNumber: number, blob: Blob): Promise<UploadPart>
  completeUpload(uploadId: string, parts: UploadPart[], idempotencyKey: string): Promise<FileRef>
  cancelUpload(uploadId: string): Promise<void>
  /** Full resumable upload: hash → session → parts → complete */
  uploadFile(
    file: File,
    purpose: UploadPurpose,
    options?: { resourceId?: string; onProgress?: (p: UploadProgress) => void; signal?: AbortSignal },
  ): Promise<FileRef>

  generateDocuments(taskId: string, body: GenerateBidDocumentRequest, idempotencyKey: string): Promise<JobRef>
  listDocumentVersions(
    taskId: string,
    query?: { page?: number; pageSize?: number; sortBy?: string; sortOrder?: 'asc' | 'desc' },
  ): Promise<PageResult<DocumentVersion>>
  compareDocumentVersions(taskId: string, fromVersionId: string, toVersionId: string): Promise<DocumentDiff>
  rollbackDocumentVersion(
    taskId: string,
    versionId: string,
    reason: string,
    idempotencyKey: string,
  ): Promise<JobRef>
  downloadDocumentBlob(taskId: string, documentId: string): Promise<Blob>
}
