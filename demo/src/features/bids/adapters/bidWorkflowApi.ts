import { apiClient } from '../../../api/client'
import type { components } from '../../../api/generated/schema'
import type { BidTaskViewModel } from '../types'
import { mapBidTaskToViewModel } from './mapBidTask'
import type { JobRef } from './schemaTypes'

export type BidTaskDetail = components['schemas']['BidTaskDetail']
export type BidTaskStats = components['schemas']['BidTaskStats']
export type BidMaterial = components['schemas']['BidMaterial']
export type TenderRequirements = components['schemas']['TenderRequirements']
export type BidReviewReport = components['schemas']['BidReviewReport']
export type BidReviewFinding = components['schemas']['BidReviewFinding']
export type CreateBidMaterialRequest = components['schemas']['CreateBidMaterialRequest']
export type UpdateBidMaterialRequest = components['schemas']['UpdateBidMaterialRequest']

type MaterialListQuery = {
  page?: number
  pageSize?: number
  category?: BidMaterial['category']
  status?: BidMaterial['status']
  required?: boolean
  sortBy?: 'name' | 'category' | 'status' | 'sortOrder'
  sortOrder?: 'asc' | 'desc'
}

function taskPath(taskId: string) {
  return `/bid-tasks/${encodeURIComponent(taskId)}`
}

export function fetchBidTaskStats() {
  return apiClient.get<BidTaskStats>('/bid-tasks/stats')
}

export function fetchBidTaskDetail(taskId: string) {
  return apiClient.get<BidTaskDetail>(taskPath(taskId))
}

export async function cloneBidTask(taskId: string, projectName: string): Promise<BidTaskViewModel> {
  const task = await apiClient.post<components['schemas']['BidTask']>(`${taskPath(taskId)}/clone`, { projectName })
  return mapBidTaskToViewModel(task)
}

export async function archiveBidTask(taskId: string, reason: string): Promise<BidTaskViewModel> {
  const task = await apiClient.post<components['schemas']['BidTask']>(`${taskPath(taskId)}/archive`, { reason })
  return mapBidTaskToViewModel(task)
}

export async function fetchBidMaterials(taskId: string, query: MaterialListQuery = {}) {
  const page = await apiClient.getPage<BidMaterial[]>(`${taskPath(taskId)}/materials`, {
    query: { page: 1, pageSize: 100, sortBy: 'sortOrder', sortOrder: 'asc', ...query },
  })
  return page.data
}

export function createBidMaterial(taskId: string, payload: CreateBidMaterialRequest) {
  return apiClient.post<BidMaterial>(`${taskPath(taskId)}/materials`, payload)
}

export function updateBidMaterial(
  taskId: string,
  materialId: string,
  payload: UpdateBidMaterialRequest,
  version: number,
) {
  return apiClient.patch<BidMaterial>(
    `${taskPath(taskId)}/materials/${encodeURIComponent(materialId)}`,
    payload,
    { ifMatch: version },
  )
}

export function deleteBidMaterial(taskId: string, materialId: string) {
  return apiClient.delete<void>(`${taskPath(taskId)}/materials/${encodeURIComponent(materialId)}`)
}

export function bindBidMaterialFile(taskId: string, materialId: string, fileId: string) {
  return apiClient.put<BidMaterial>(
    `${taskPath(taskId)}/materials/${encodeURIComponent(materialId)}/file`,
    { fileId },
  )
}

export function startBidMaterialMatch(taskId: string, materialIds: string[], idempotencyKey: string) {
  return apiClient.post<JobRef>(
    `${taskPath(taskId)}/materials/match`,
    { materialIds },
    { idempotencyKey },
  )
}

export function exportBidMaterials(taskId: string) {
  return apiClient.get<Blob>(`${taskPath(taskId)}/materials/export`, { responseType: 'blob' })
}

export function generateBidMaterialTemplates(taskId: string, materialIds: string[], idempotencyKey: string) {
  return apiClient.post<JobRef>(
    `${taskPath(taskId)}/materials/templates`,
    { materialIds },
    { idempotencyKey },
  )
}

export function decideBidReviewFinding(
  taskId: string,
  findingId: string,
  decision: 'accepted' | 'ignored' | 'modified',
  comment?: string,
) {
  return apiClient.post<BidReviewFinding>(
    `${taskPath(taskId)}/review-findings/${encodeURIComponent(findingId)}/decision`,
    { decision, comment },
  )
}

export function fetchFilePreview(fileId: string) {
  return apiClient.get<Blob>(`/files/${encodeURIComponent(fileId)}/preview`, { responseType: 'blob' })
}

export function fetchFileDownload(fileId: string) {
  return apiClient.get<Blob>(`/files/${encodeURIComponent(fileId)}/download`, { responseType: 'blob' })
}
