export const EVAL_PORTAL_ROUTE = '/evaluation/portal/EVAL-2026-001'

export const EVAL_STATUS_LABELS: Record<string, string> = {
  collecting: '材料收集中',
  ai_review: 'AI 初审中',
  human_review: '人工复核',
  completed: '已完成',
  closed: '已关闭',
}

/** Stable selectors for M7 Playwright E2E. */
export const EVAL_TEST_IDS = {
  dashboard: 'eval-dashboard',
  dashboardCreate: 'eval-dashboard-create',
  dashboardPortal: 'eval-dashboard-portal',
  dashboardReset: 'eval-dashboard-reset',
  create: 'eval-create',
  createSaveDraft: 'eval-create-save-draft',
  createPreview: 'eval-create-preview',
  createCancel: 'eval-create-cancel',
  createPublish: 'eval-create-publish',
  taskDetail: 'eval-task-detail',
  taskBack: 'eval-task-back',
  taskAiReview: 'eval-task-ai-review',
  taskClose: 'eval-task-close',
} as const
