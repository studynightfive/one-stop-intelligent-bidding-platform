import { ApiClient, apiClient } from '../../api/client'
import type { components } from '../../api/generated/schema'
import type { EvaluationTaskSummary } from './types'

export type EvaluationTask = components['schemas']['EvaluationTask']
export type EvaluationTaskDetail = components['schemas']['EvaluationTaskDetail']
type EvaluationStats = components['schemas']['EvaluationStats']
type EvaluationMaterial = components['schemas']['EvaluationMaterial']
type ScoringCriterion = components['schemas']['ScoringCriterion']
type ReviewSettings = components['schemas']['ReviewSettings']
type ValidationResult = components['schemas']['ValidationResult']
type SupplierInvitationInput = components['schemas']['SupplierInvitationInput']
type CreateEvaluationDraftRequest = components['schemas']['CreateEvaluationDraftRequest']
type UpdateEvaluationRequest = components['schemas']['UpdateEvaluationRequest']
export type Supplier = components['schemas']['Supplier']
export type SupplierSubmission = components['schemas']['SupplierSubmission']
export type SupplierInviteSummary = components['schemas']['SupplierInviteSummary']
export type SupplementNotice = components['schemas']['SupplementNotice']
export type PriceRound = components['schemas']['PriceRound']
export type PriceComparison = components['schemas']['PriceComparison']
export type MaterialCheckResult = components['schemas']['MaterialCheckResult']
export type RiskFinding = components['schemas']['RiskFinding']
export type ScoreItem = components['schemas']['ScoreItem']
export type EvaluationRanking = components['schemas']['EvaluationRanking']
export type EvaluationReport = components['schemas']['EvaluationReport']
export type AuditEvent = components['schemas']['AuditEvent']
export type JobRef = components['schemas']['JobRef']

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

export function cancelEvaluation(evaluationId: string, reason: string) {
  return apiClient.post<EvaluationTask>(`/evaluations/${evaluationId}/cancel`, { reason })
}

export function fetchEvaluationSuppliers(evaluationId: string) {
  return apiClient.get<Supplier[]>(`/evaluations/${evaluationId}/suppliers`, { query: { page: 1, pageSize: 100 } })
}

export function fetchSupplierSubmissions(evaluationId: string, supplierId: string) {
  return apiClient.get<SupplierSubmission[]>(`/evaluations/${evaluationId}/suppliers/${supplierId}/submissions`)
}

export function fetchSupplierInvites(evaluationId: string) {
  return apiClient.get<SupplierInviteSummary[]>(`/evaluations/${evaluationId}/supplier-invites`)
}

export function rotateSupplierInvite(evaluationId: string, supplierId: string, reason: string) {
  return apiClient.post<SupplierInviteSummary>(`/evaluations/${evaluationId}/supplier-invites/${supplierId}/rotate`, { reason })
}

export function revokeSupplierInvite(evaluationId: string, supplierId: string, reason: string) {
  return apiClient.post<{ revoked: true }>(`/evaluations/${evaluationId}/supplier-invites/${supplierId}/revoke`, { reason })
}

export function createSupplementNotice(evaluationId: string, payload: components['schemas']['CreateSupplementNoticeRequest']) {
  return apiClient.post<SupplementNotice>(`/evaluations/${evaluationId}/supplement-notices`, payload)
}

export function fetchSupplementNotices(evaluationId: string) {
  return apiClient.get<SupplementNotice[]>(`/evaluations/${evaluationId}/supplement-notices`, { query: { page: 1, pageSize: 100 } })
}

export function createPriceRound(evaluationId: string, payload: components['schemas']['CreatePriceRoundRequest']) {
  return apiClient.post<PriceRound>(`/evaluations/${evaluationId}/price-rounds`, payload)
}

export function fetchPriceRounds(evaluationId: string) {
  return apiClient.get<PriceRound[]>(`/evaluations/${evaluationId}/price-rounds`)
}

export function closePriceRound(evaluationId: string, roundId: string) {
  return apiClient.post<PriceRound>(`/evaluations/${evaluationId}/price-rounds/${roundId}/close`)
}

export function fetchPriceComparison(evaluationId: string) {
  return apiClient.get<PriceComparison>(`/evaluations/${evaluationId}/price-comparison`)
}

export function startMaterialCheck(evaluationId: string) {
  return apiClient.post<JobRef>(`/evaluations/${evaluationId}/material-checks`)
}

export function fetchLatestMaterialCheck(evaluationId: string) {
  return apiClient.get<MaterialCheckResult>(`/evaluations/${evaluationId}/material-checks/latest`)
}

export function startRiskCheck(evaluationId: string) {
  return apiClient.post<JobRef>(`/evaluations/${evaluationId}/risk-checks`)
}

export function fetchRisks(evaluationId: string) {
  return apiClient.get<RiskFinding[]>(`/evaluations/${evaluationId}/risks`)
}

export function decideRisk(evaluationId: string, riskId: string, decision: 'passed' | 'rejected', reason: string) {
  return apiClient.post<RiskFinding>(`/evaluations/${evaluationId}/risks/${riskId}/decision`, { decision, reason })
}

export function startAiScoring(evaluationId: string) {
  return apiClient.post<JobRef>(`/evaluations/${evaluationId}/ai-scoring`)
}

export function fetchScores(evaluationId: string, supplierId?: string, category?: string) {
  return apiClient.get<ScoreItem[]>(`/evaluations/${evaluationId}/scores`, { query: { supplierId, category } })
}

export function updateScore(evaluationId: string, score: ScoreItem, humanScore: string, adjustmentReason: string) {
  return apiClient.patch<ScoreItem>(`/evaluations/${evaluationId}/scores/${score.supplierId}/${score.criterionId}`, { humanScore, adjustmentReason }, { ifMatch: score.version })
}

export function confirmScores(evaluationId: string, supplierId?: string, comment?: string) {
  return apiClient.post<{ confirmed: boolean }>(`/evaluations/${evaluationId}/scores/confirm`, { supplierId, comment })
}

export function fetchRanking(evaluationId: string) {
  return apiClient.get<EvaluationRanking>(`/evaluations/${evaluationId}/ranking`)
}

export function createEvaluationReport(evaluationId: string, formats: Array<'docx' | 'pdf'>) {
  return apiClient.post<JobRef>(`/evaluations/${evaluationId}/reports`, { formats })
}

export function fetchEvaluationReports(evaluationId: string) {
  return apiClient.get<EvaluationReport[]>(`/evaluations/${evaluationId}/reports`)
}

export function downloadEvaluationReport(evaluationId: string, reportId: string) {
  return apiClient.get<Blob>(`/evaluations/${evaluationId}/reports/${reportId}/download`, { responseType: 'blob' })
}

export function closeEvaluation(evaluationId: string, resultSummary: string, idempotencyKey: string) {
  return apiClient.post<EvaluationTask>(`/evaluations/${evaluationId}/close`, { resultSummary }, { idempotencyKey })
}

export function fetchEvaluationAuditEvents(evaluationId: string) {
  return apiClient.get<AuditEvent[]>(`/evaluations/${evaluationId}/audit-events`, { query: { page: 1, pageSize: 100 } })
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
// ── Portal API ──────────────────────────────────────────────────────
type PortalContext = components['schemas']['PortalContext']
type PortalMaterial = components['schemas']['PortalMaterial']
type PortalDraft = components['schemas']['PortalDraft']
type PortalPriceRound = components['schemas']['PortalPriceRound']
type PortalActivity = components['schemas']['PortalActivity']
type SubmissionReceipt = components['schemas']['SubmissionReceipt']
type QuoteSubmission = components['schemas']['QuoteSubmission']
export type PortalSession = components['schemas']['PortalSession']

/** Create a client whose Bearer token is isolated from the internal admin session. */
export function createPortalApiClient(portalAccessToken: string) {
  return new ApiClient({ auth: { getAccessToken: () => portalAccessToken } })
}

/** Exchange a one-time supplier invitation code for a short-lived portal session. */
export function exchangePortalSession(inviteCode: string) {
  const publicClient = new ApiClient()
  return publicClient.post<PortalSession>('/portal/session/exchange', { inviteCode })
}

/** Refresh a portal session through the HttpOnly refresh cookie. */
export function refreshPortalSession() {
  const publicClient = new ApiClient()
  return publicClient.post<PortalSession>('/portal/session/refresh')
}

function portalClient(portalAccessToken: string) {
  return createPortalApiClient(portalAccessToken)
}

/** Fetch supplier portal context (evaluation + supplier identity + submission summary). */
export function fetchPortalContext(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<PortalContext>('/portal/me')
}

/** Fetch the list of required/optional materials for this supplier. */
export function fetchPortalMaterials(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<PortalMaterial[]>('/portal/materials')
}

/** Bind an uploaded file to a portal material row. */
export function uploadPortalMaterialFile(portalAccessToken: string, materialId: string, fileId: string) {
  return portalClient(portalAccessToken).put<PortalMaterial>(`/portal/materials/${materialId}/file`, { fileId })
}

/** Remove a previously uploaded file from a material row. */
export function deletePortalMaterialFile(portalAccessToken: string, materialId: string) {
  return portalClient(portalAccessToken).delete<PortalMaterial>(`/portal/materials/${materialId}/file`)
}

/** Save portal draft (note + optional quote draft). */
export function savePortalDraft(portalAccessToken: string, payload: { note?: string; quoteDraft?: number }) {
  return portalClient(portalAccessToken).put<PortalDraft>('/portal/draft', payload)
}

/** Finalise and submit all materials. Returns a receipt. */
export function submitPortalMaterials(portalAccessToken: string, idempotencyKey: string) {
  return portalClient(portalAccessToken).post<SubmissionReceipt>(
    '/portal/submit',
    { confirmed: true },
    { idempotencyKey },
  )
}

/** Download the submission receipt as a blob. */
export function fetchPortalReceipt(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<Blob>('/portal/receipt', { responseType: 'blob' })
}

/** Fetch supplement notices for the current portal supplier. */
export function fetchPortalNotices(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<SupplementNotice[]>('/portal/notices')
}

/** Respond to a supplement notice by binding replacement files. */
export function respondPortalNotice(portalAccessToken: string, noticeId: string, fileBindings: { materialId: string; fileId: string }[]) {
  return portalClient(portalAccessToken).post<SupplementNotice>(`/portal/notices/${noticeId}/respond`, { fileBindings })
}

/** Fetch price rounds visible to the portal supplier. */
export function fetchPortalPriceRounds(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<PortalPriceRound[]>('/portal/price-rounds')
}

/** Submit a quote for a specific price round. */
export function submitPortalQuote(portalAccessToken: string, roundId: string, amount: number, idempotencyKey: string) {
  return portalClient(portalAccessToken).post<QuoteSubmission>(
    `/portal/price-rounds/${roundId}/quotes`,
    { amount, currency: 'CNY' },
    { idempotencyKey },
  )
}

/** Fetch portal audit-trail / activity log. */
export function fetchPortalActivity(portalAccessToken: string) {
  return portalClient(portalAccessToken).get<PortalActivity[]>('/portal/activity')
}
