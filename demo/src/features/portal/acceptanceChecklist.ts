/**
 * M2 supplier portal acceptance checklist for M7 Playwright E2E.
 * Selectors: see PORTAL_TEST_IDS in features/portal/constants.ts
 *
 * Supplier submission
 * - [ ] invite link opens the portal and locks supplier identity (eval-portal)
 * - [ ] material draft can be saved and resumed (eval-portal-save-draft)
 * - [ ] formal submission completes with a receipt (eval-portal-submit)
 * - [ ] multi-round quote can be submitted (eval-portal-quote-submit)
 *
 * Link invalidation
 * - [ ] revoked or expired invite shows the closed state instead of forms (eval-portal-closed)
 *
 * Deadline
 * - [ ] portal blocks submission and quote actions after the deadline (eval-portal-closed)
 */
export const portalAcceptanceChecklist = {
  owner: 'M2',
  consumers: ['M7'],
  testIds: [
    'eval-portal',
    'eval-portal-save-draft',
    'eval-portal-submit',
    'eval-portal-quote-submit',
    'eval-portal-closed',
  ],
} as const
