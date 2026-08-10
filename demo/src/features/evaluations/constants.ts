export const EVAL_PORTAL_ROUTE = '/evaluation/portal/EVAL-2026-001'

export const EVAL_STATUS_LABELS: Record<string, string> = {
  collecting: '材料收集中',
  ai_review: 'AI 初审中',
  human_review: '人工复核',
  completed: '已完成',
  closed: '已关闭',
}

export const EVAL_STATUS_META: Record<string, { label: string; color: string; step: string }> = {
  collecting: { label: '材料收集中', color: 'blue', step: '供应商提交中' },
  pending: { label: '待评审', color: 'default', step: '等待开始' },
  ai_review: { label: 'AI 初审中', color: 'purple', step: 'AI 智能初审' },
  human_review: { label: '人工复审', color: 'orange', step: '人工复审' },
  completed: { label: '已完成', color: 'green', step: '评标完成' },
  closed: { label: '已关闭', color: 'default', step: '评标已关闭' },
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
