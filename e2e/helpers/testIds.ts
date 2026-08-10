/**
 * 稳定选择器字典（`data-testid`）。
 *
 * M1（投标 UI）/ M2（评标 UI）/ M3（公共前端）需在最终 UI 中为关键元素添加
 * 对应的 `data-testid`，M7 在 E2E 中通过此字典访问，避免依赖 CSS / 文案。
 *
 * 当前 Phase 0 占位：所有 ID 为空对象，Phase 1+ 由 M1/M2/M3 提供。
 */
export const testIds = {
  // 全局
  appShell: 'app-shell',
  primaryNav: 'primary-nav',

  // 登录（M3）
  loginEmailInput: 'login.email',
  loginPasswordInput: 'login.password',
  loginSubmitButton: 'login.submit',

  // 投标（M1 / M3）
  bidCreateButton: 'bid.create',
  bidDetailTitle: 'bid.detail.title',
  bidMaterialUploadButton: 'bid.material.upload',

  // 评标（M2 / M3）
  evaluationCreateButton: 'evaluation.create',
  evaluationRiskList: 'evaluation.risk.list',

  // Portal（M2）
  portalLoginCodeInput: 'portal.code',
  portalSubmitButton: 'portal.submit',

  // AI 状态（M3 → M7 通过 WebSocket）
  jobProgressBar: 'job.progress',
  jobOfflineBadge: 'job.offline-badge',
} as const;

export type TestId = (typeof testIds)[keyof typeof testIds];