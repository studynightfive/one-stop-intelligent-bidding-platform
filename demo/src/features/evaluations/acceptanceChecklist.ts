/**
 * M2 internal evaluation acceptance checklist for M7 Playwright E2E.
 * Selectors: see EVAL_TEST_IDS in features/evaluations/constants.ts
 *
 * Happy path
 * - [ ] /evaluation dashboard renders task list and status labels (eval-dashboard)
 * - [ ] dashboard create button opens the create wizard (eval-dashboard-create, eval-create)
 * - [ ] create wizard saves draft, previews, cancels, and publishes (eval-create-save-draft, eval-create-preview, eval-create-cancel, eval-create-publish)
 * - [ ] dashboard portal entry opens the supplier portal (eval-dashboard-portal)
 * - [ ] /evaluation/:id renders six-step progress and task actions (eval-task-detail, eval-task-back, eval-task-ai-review, eval-task-close)
 *
 * Failure path
 * - [ ] cancel returns to the dashboard without discarding the saved draft (eval-create-cancel)
 * - [ ] reset restores dashboard filters to defaults (eval-dashboard-reset)
 *
 * Permission path
 * - [ ] AI review and close actions render only for assigned/owner roles (eval-task-ai-review, eval-task-close)
 */
export const evalAcceptanceChecklist = {
  owner: 'M2',
  consumers: ['M7'],
  testIds: [
    'eval-dashboard',
    'eval-dashboard-create',
    'eval-dashboard-portal',
    'eval-dashboard-reset',
    'eval-create',
    'eval-create-save-draft',
    'eval-create-preview',
    'eval-create-cancel',
    'eval-create-publish',
    'eval-task-detail',
    'eval-task-back',
    'eval-task-ai-review',
    'eval-task-close',
  ],
} as const
