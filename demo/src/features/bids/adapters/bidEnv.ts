/** M1 bid env — respects repo `.env.example` `VITE_USE_MOCKS`. */

export const BID_ACCESS_TOKEN_KEY = 'bid-platform-access-token'

export function getBidApiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://127.0.0.1:8210/api/v1'
  return raw.replace(/\/$/, '')
}

/** Default false: talk to real API. Set VITE_USE_MOCKS=true only for offline demo. */
export function shouldUseBidMocks(): boolean {
  const flag = String(import.meta.env.VITE_USE_MOCKS ?? 'false').toLowerCase()
  return flag === 'true' || flag === '1' || flag === 'yes'
}

export function readAccessToken(): string | null {
  try {
    return sessionStorage.getItem(BID_ACCESS_TOKEN_KEY) || localStorage.getItem(BID_ACCESS_TOKEN_KEY)
  } catch {
    return null
  }
}

/** M3 login should call this after AuthSession is returned. */
export function writeAccessToken(token: string | null) {
  try {
    if (!token) {
      sessionStorage.removeItem(BID_ACCESS_TOKEN_KEY)
      localStorage.removeItem(BID_ACCESS_TOKEN_KEY)
      return
    }
    sessionStorage.setItem(BID_ACCESS_TOKEN_KEY, token)
  } catch {
    /* ignore */
  }
}
