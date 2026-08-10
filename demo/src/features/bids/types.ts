/** Domain types aligned with OpenAPI BidTaskStatus / UI view models. */

export type BidTaskStatus =
  | 'draft'
  | 'parsing'
  | 'material_prep'
  | 'ai_review'
  | 'pending_output'
  | 'completed'
  | 'archived'
  | 'failed'

export type BidQuickFilter = 'all' | 'mine' | 'due' | 'risk'
export type BidStatusFilter = 'all' | 'active' | BidTaskStatus
export type BidWorkbenchView = 'table' | 'board'

export type BidTaskViewModel = {
  id: string
  projectName: string
  tenderNo: string
  tenderEntity: string
  deadline: string
  status: BidTaskStatus | string
  currentStep: number
  progress: number
  assignee: string
  assigneeId?: string
  materialTotal: number
  materialHave: number
  materialMissing: number
  linkedEvaluationId?: string
  version?: number
  createdAt?: string
  tags?: string[]
}

export type BidCreateDraft = {
  projectName?: string
  tenderNo?: string
  tenderEntity?: string
  deadline?: string
  budget?: number
  fileName?: string
  fileSize?: number
  /** OpenAPI FileRef.id after resumable upload completes */
  tenderFileId?: string
  updatedAt: string
}

export type BidParseOutcome = 'idle' | 'running' | 'success' | 'failed'

export type BidUiState =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'forbidden'
  | 'timeout'
  | 'conflict'
  | 'not_found'

export const BID_UI_QUERY_KEY = 'ui'

export function parseBidUiState(value: string | null | undefined): BidUiState | null {
  if (!value) return null
  const allowed: BidUiState[] = [
    'ready',
    'loading',
    'empty',
    'error',
    'forbidden',
    'timeout',
    'conflict',
    'not_found',
  ]
  return allowed.includes(value as BidUiState) ? (value as BidUiState) : null
}
