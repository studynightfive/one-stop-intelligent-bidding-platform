/** Backwards-compatible M1 aliases for the shared runtime configuration. */

import { ACCESS_TOKEN_KEY, readAccessToken } from '../../../api/authStorage'
import { apiBaseUrl, shouldUseMocks } from '../../../api/runtime'

export const BID_ACCESS_TOKEN_KEY = ACCESS_TOKEN_KEY

export function getBidApiBaseUrl(): string {
  return apiBaseUrl()
}

/** Default false: talk to real API. Set VITE_USE_MOCKS=true only for offline demo. */
export function shouldUseBidMocks(): boolean {
  return shouldUseMocks()
}

const DEMO_ADMIN_USER_ID = '0190f4dd-0000-7000-8000-000000000001'

/** Read the authenticated subject without adding a second auth state store. */
export function getCurrentBidUserId(): string {
  const token = readAccessToken()
  if (!token) return DEMO_ADMIN_USER_ID
  try {
    const payload = token.split('.')[1]
    if (!payload) return DEMO_ADMIN_USER_ID
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    const claims = JSON.parse(atob(padded)) as { sub?: unknown }
    return typeof claims.sub === 'string' && claims.sub ? claims.sub : DEMO_ADMIN_USER_ID
  } catch {
    return DEMO_ADMIN_USER_ID
  }
}

export { readAccessToken }
