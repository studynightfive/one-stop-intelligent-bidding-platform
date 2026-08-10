import { apiClient } from '../../api/client'
import type { components } from '../../api/generated/schema'
import type { EvaluationTaskSummary } from './types'

type EvaluationTask = components['schemas']['EvaluationTask']
type EvaluationTaskDetail = components['schemas']['EvaluationTaskDetail']
type EvaluationStats = components['schemas']['EvaluationStats']
type EvaluationMaterial = components['schemas']['EvaluationMaterial']
type ScoringCriterion = components['schemas']['ScoringCriterion']
type ReviewSettings = components['schemas']['ReviewSettings']
type ValidationResult = components['schemas']['ValidationResult']
type SupplierInvitationInput = components['schemas']['SupplierInvitationInput']
type SupplierInviteSummary = components['schemas']['SupplierInviteSummary']
type CreateEvaluationDraftRequest = components['schemas']['CreateEvaluationDraftRequest']
type UpdateEvaluationRequest = components['schemas']['UpdateEvaluationRequest']

export type EvaluationMaterialInput = Omit<EvaluationMaterial, 'evaluationId'>
export type ScoringCriterionInput = Omit<ScoringCriterion, 'evaluationId'>
export type EvaluationPreview = components['schemas']['EvaluationPreview']

export type EvaluationPublishResult = {
  evaluation: EvaluationTask
  invites: SupplierInviteSummary[]
}

const ACCESS_TOKEN_KEY = 'bid-platform-access-token'

export function readCurrentUserId(): string | null {
  try {
    const raw = sessionStorage.getItem(ACCESS_TOKEN_KEY) || localStorage.getItem(ACCESS_TOKEN_KEY)
    if (!raw) return null
    const parts = raw.split('.')
    if (parts.length < 2) return null
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
    const payload = JSON.parse(atob(padded)) as { sub?: string }
    return typeof payload.sub === 'string' && payload.sub ? payload.sub : null
  } catch {
    return null
  }
}

export interface EvaluationListQuery {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  keyword?: string
  status?: string
  assigneeId?: string
  [key: string]: string | number | boolean | Array<string | number> | undefined
}

export interface EvaluationStatsQuery {
  keyword?: string
  status?: string
  assigneeId?: string
  [key: string]: string | number | boolean | Array<string | number> | undefined
}

export function fetchEvaluationTasks(query: EvaluationListQuery = {}) {
  return apiClient.get<EvaluationTask[]>('/evaluations', { query })
}

export function fetchEvaluationStats(query: EvaluationStatsQuery = {}) {
  return apiClient.get<EvaluationStats>('/evaluations/stats', { query })
}

export function fetchEvaluationDetail(evaluationId: string) {
  return apiClient.get<EvaluationTaskDetail>(`/evaluations/${evaluationId}`)
}

export function createEvaluationDraft(payload: CreateEvaluationDraftRequest) {
  return apiClient.post<EvaluationTask>('/evaluations', payload)
}

export function createEvaluationFromBidTask(bidTaskId: string) {
  return apiClient.post<EvaluationTaskDetail>(`/evaluations/from-bid-task/${bidTaskId}`, { copyMaterials: true })
}

export function updateEvaluationDraft(
  evaluationId: string,
  payload: UpdateEvaluationRequest,
  version?: number,
) {
  return apiClient.patch<EvaluationTask>(`/evaluations/${evaluationId}`, payload, { ifMatch: version })
}

export function putEvaluationMaterials(evaluationId: string, items: EvaluationMaterialInput[]) {
  return apiClient.put<EvaluationMaterial[]>(`/evaluations/${evaluationId}/materials`, { items })
}

export function putEvaluationCriteria(evaluationId: string, items: ScoringCriterionInput[]) {
  return apiClient.put<ScoringCriterion[]>(`/evaluations/${evaluationId}/criteria`, { items })
}

export function putEvaluationReviewSettings(evaluationId: string, settings: ReviewSettings) {
  return apiClient.put<ReviewSettings>(`/evaluations/${evaluationId}/review-settings`, settings)
}

export function putEvaluationReviewers(evaluationId: string, reviewerIds: string[]) {
  return apiClient.put<Array<{ id: string; name: string }>>(`/evaluations/${evaluationId}/reviewers`, { reviewerIds })
}

export function putEvaluationSuppliers(evaluationId: string, items: SupplierInvitationInput[]) {
  return apiClient.put<unknown>(`/evaluations/${evaluationId}/suppliers`, { items })
}

export function validateEvaluation(evaluationId: string) {
  return apiClient.post<ValidationResult>(`/evaluations/${evaluationId}/validate`)
}

export function previewEvaluation(evaluationId: string) {
  return apiClient.get<EvaluationPreview>(`/evaluations/${evaluationId}/preview`)
}

export function publishEvaluation(evaluationId: string, idempotencyKey: string) {
  return apiClient.post<EvaluationPublishResult>(
    `/evaluations/${evaluationId}/publish`,
    undefined,
    { idempotencyKey },
  )
}

export function toEvaluationTaskSummary(task: EvaluationTask): EvaluationTaskSummary {
  return {
    id: task.id,
    projectName: task.projectName,
    tenderNo: task.tenderNo,
    tenderEntity: task.tenderEntity,
    status: task.status,
    assignee: task.assignee?.name || '未分配',
    deadline: task.supplierDeadline,
    bidderCount: task.supplierCount,
    progress: task.progressPercent,
    budget: task.budgetAmount,
    riskCount: task.riskCount,
  }
}
