import type { BidTaskStatus } from './types'

export const BID_BOARD_COLUMNS: { key: BidTaskStatus | string; title: string }[] = [
  { key: 'parsing', title: 'AI解析中' },
  { key: 'material_prep', title: '材料准备' },
  { key: 'ai_review', title: 'AI审核中' },
  { key: 'pending_output', title: '待输出' },
  { key: 'completed', title: '已完成' },
]

export const BID_STATUS_COLORS: Record<string, string> = {
  blue: '#2563EB',
  orange: '#D97706',
  purple: '#7C3AED',
  cyan: '#0891B2',
  green: '#16A34A',
}

export const BID_CREATE_DRAFT_KEY = 'bid-m1-create-draft-v1'

export const BID_ACCEPT_UPLOAD_TYPES =
  '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.png,.jpg,.jpeg'

export const BID_MAX_UPLOAD_BYTES = 200 * 1024 * 1024

/** Local fallback labels when shared mock statusMap lacks OpenAPI statuses. */
export const BID_STATUS_FALLBACK: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  archived: { label: '已归档', color: 'default' },
  failed: { label: '失败', color: 'error' },
}

/** Stable selectors for M7 Playwright E2E. */
export const BID_TEST_IDS = {
  dashboard: 'bid-dashboard',
  dashboardCreate: 'bid-dashboard-create',
  dashboardEmpty: 'bid-dashboard-empty',
  dashboardArchive: 'bid-dashboard-archive',
  create: 'bid-create',
  createSaveDraft: 'bid-create-save-draft',
  createStartParse: 'bid-create-start-parse',
  createRetryParse: 'bid-create-retry-parse',
  createSubmit: 'bid-create-submit',
  taskDetail: 'bid-task-detail',
  taskNotFound: 'bid-task-not-found',
  taskMaterialsTab: 'bid-task-materials',
  taskReviewTab: 'bid-task-review',
  taskOutputTab: 'bid-task-output',
  taskRequirementsTab: 'bid-task-requirements',
  stateLoading: 'bid-state-loading',
  stateEmpty: 'bid-state-empty',
  stateError: 'bid-state-error',
  stateForbidden: 'bid-state-forbidden',
  stateTimeout: 'bid-state-timeout',
  stateConflict: 'bid-state-conflict',
  stateTaskFailed: 'bid-state-task-failed',
  uiStateSwitcher: 'bid-ui-state-switcher',
  materialsBatchDelete: 'bid-materials-batch-delete',
  materialsSelectAll: 'bid-materials-select-all',
  workflowNext: 'bid-workflow-next',
  workflowPrev: 'bid-workflow-prev',
  dashboardPagination: 'bid-dashboard-pagination',
  createUploadProgress: 'bid-create-upload-progress',
  outputGenerate: 'bid-output-generate',
  outputCompare: 'bid-output-compare',
  outputRollback: 'bid-output-rollback',
} as const
