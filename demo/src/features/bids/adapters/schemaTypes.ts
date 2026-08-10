/** OpenAPI-aligned aliases for M1 adapters (types from generated schema only). */
import type { components } from '../../../api/generated/schema'

export type PaginationMeta = components['schemas']['PaginationMeta']
export type FileRef = components['schemas']['FileRef']
export type JobRef = components['schemas']['JobRef']
export type UploadSession = components['schemas']['UploadSession']
export type UploadPart = components['schemas']['UploadPart']
export type CreateUploadSessionRequest = components['schemas']['CreateUploadSessionRequest']
export type CreateBidTaskRequest = components['schemas']['CreateBidTaskRequest']
export type CreateBidReviewRequest = components['schemas']['CreateBidReviewRequest']
export type GenerateBidDocumentRequest = components['schemas']['GenerateBidDocumentRequest']
export type TechnicalDocumentGenerationOptions = components['schemas']['TechnicalDocumentGenerationOptions']
export type TechnicalDocumentSectionTemplate = components['schemas']['TechnicalDocumentSectionTemplate']
export type TechnicalDocumentImage = components['schemas']['TechnicalDocumentImage']
export type DocumentVersion = components['schemas']['DocumentVersion']
export type DocumentDiff = components['schemas']['DocumentDiff']
export type BidDocument = components['schemas']['BidDocument']
export type BidTaskApi = components['schemas']['BidTask']

export type PageResult<T> = {
  data: T[]
  meta: PaginationMeta
  requestId: string
}

export type ListBidTasksQuery = {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  keyword?: string
  status?: string
  assigneeId?: string
  quickFilter?: string
  /** Demo-only: include archived when status filter is archived */
  includeArchived?: boolean
  currentUserName?: string
}

export type UploadPurpose = CreateUploadSessionRequest['purpose']

export type UploadProgress = {
  uploadId?: string
  status: UploadSession['status'] | 'hashing' | 'idle'
  percent: number
  uploadedParts: number
  totalParts: number
}
