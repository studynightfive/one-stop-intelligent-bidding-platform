/**
 * Stable selectors mirrored from the domain-owned web constants. Keeping a
 * small E2E dictionary avoids coupling the Playwright project to web sources.
 */
export const testIds = {
  loginPage: 'login-page',

  bidDashboard: 'bid-dashboard',
  bidCreateButton: 'bid-dashboard-create',
  bidCreate: 'bid-create',
  bidDetail: 'bid-task-detail',
  bidMaterialsTab: 'bid-task-materials',
  bidOutputTab: 'bid-task-output',
  bidOutputGenerate: 'bid-output-generate',

  evaluationDashboard: 'eval-dashboard',
  evaluationCreateButton: 'eval-dashboard-create',
  evaluationCreate: 'eval-create',
  evaluationDetail: 'eval-task-detail',
  evaluationAiReview: 'eval-task-ai-review',

  portal: 'eval-portal',
  portalSubmitButton: 'eval-portal-submit',
  portalClosed: 'eval-portal-closed',

  jobProgress: 'common-job-progress',
} as const;

export type TestId = (typeof testIds)[keyof typeof testIds];
