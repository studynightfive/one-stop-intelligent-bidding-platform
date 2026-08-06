/**
 * M1 acceptance checklist for M7 Playwright E2E.
 * Selectors: see BID_TEST_IDS in features/bids/constants.ts
 *
 * Happy path
 * - [ ] /dashboard lists tasks, stats drill-down works
 * - [ ] dashboard pagination (bid-dashboard-pagination) uses page/pageSize meta
 * - [ ] create task via /tasks/create (upload session + parse + confirm)
 * - [ ] /tasks/:id materials CRUD, review decisions, document generate/compare/rollback
 *
 * Failure path
 * - [ ] parse failure shows retry (bid-create-retry-parse)
 * - [ ] unknown task id shows not-found (bid-task-not-found)
 * - [ ] empty filter result (bid-dashboard-empty)
 * - [ ] ?ui=loading|error|forbidden|timeout|conflict|empty 可预览异常态
 *
 * Permission path
 * - [ ] forbidden preview via ?ui=forbidden（真实 403 待 M3/M5）
 */
export const bidAcceptanceChecklist = {
  owner: 'M1',
  consumers: ['M7'],
  testIds: [
    'bid-dashboard',
    'bid-dashboard-create',
    'bid-dashboard-empty',
    'bid-create',
    'bid-create-save-draft',
    'bid-create-start-parse',
    'bid-create-retry-parse',
    'bid-create-submit',
    'bid-task-detail',
    'bid-task-not-found',
    'bid-task-materials',
    'bid-task-review',
    'bid-task-output',
    'bid-task-requirements',
    'bid-state-loading',
    'bid-state-empty',
    'bid-state-error',
    'bid-state-forbidden',
    'bid-state-timeout',
    'bid-state-conflict',
    'bid-state-task-failed',
    'bid-ui-state-switcher',
  ],
} as const
