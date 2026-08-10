import { apiBaseUrl } from './runtime'

export const ACCESS_TOKEN_KEY = 'bid-platform-access-token'
const TOKEN_EXPIRY_KEY = 'bid-platform-access-token-expires-at'

type AuthPayload = {
  accessToken?: string
  accessTokenExpiresAt?: string
  access_token?: string
  access_token_expires_at?: string
}

export function readAccessToken(): string | null {
  try {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY) || localStorage.getItem(ACCESS_TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeAccessToken(token: string, expiresAt: string, remember: boolean): void {
  const target = remember ? localStorage : sessionStorage
  const alternate = remember ? sessionStorage : localStorage
  alternate.removeItem(ACCESS_TOKEN_KEY)
  alternate.removeItem(TOKEN_EXPIRY_KEY)
  target.setItem(ACCESS_TOKEN_KEY, token)
  target.setItem(TOKEN_EXPIRY_KEY, expiresAt)
}

export function clearAccessToken(): void {
  try {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_EXPIRY_KEY)
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRY_KEY)
  } catch {
    // Storage can be unavailable in hardened browser contexts.
  }
}

function unwrapAuthPayload(payload: unknown): AuthPayload | null {
  if (!payload || typeof payload !== 'object') return null
  const value = payload as { success?: boolean; data?: unknown }
  const candidate = value.success === true ? value.data : payload
  return candidate && typeof candidate === 'object' ? candidate as AuthPayload : null
}

export async function refreshAccessToken(): Promise<string | null> {
  try {
    const response = await fetch(`${apiBaseUrl()}/auth/refresh`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'X-Request-ID': crypto.randomUUID() },
      credentials: 'include',
    })
    if (!response.ok) {
      clearAccessToken()
      return null
    }
    const payload = unwrapAuthPayload(await response.json())
    const token = payload?.accessToken || payload?.access_token
    const expiresAt = payload?.accessTokenExpiresAt || payload?.access_token_expires_at
    if (!token || !expiresAt) {
      clearAccessToken()
      return null
    }
    const remember = Boolean(localStorage.getItem(ACCESS_TOKEN_KEY))
    writeAccessToken(token, expiresAt, remember)
    return token
  } catch {
    clearAccessToken()
    return null
  }
}

export const browserAuthAdapter = {
  getAccessToken: readAccessToken,
  refresh: refreshAccessToken,
  onUnauthorized: clearAccessToken,
}
