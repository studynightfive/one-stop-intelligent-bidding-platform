import { ApiError, createRequestId, mapHttpError, mapTransportError } from './interceptors'
import { browserAuthAdapter } from './authStorage'

export interface AuthAdapter {
  getAccessToken: () => string | null
  refresh?: () => Promise<string | null>
  onUnauthorized?: () => void
}

export interface ApiClientOptions {
  baseUrl?: string
  auth?: AuthAdapter
  fetchImpl?: typeof fetch
  requestIdFactory?: () => string
  defaultTimeoutMs?: number
}

export interface ApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  query?: Record<string, string | number | boolean | null | undefined | Array<string | number>>
  body?: unknown
  headers?: HeadersInit
  signal?: AbortSignal
  timeoutMs?: number
  ifMatch?: string | number
  idempotencyKey?: string
  responseType?: 'json' | 'blob' | 'text'
  /** Use `raw` for Blob/ArrayBuffer payloads such as resumable upload parts. */
  bodyMode?: 'json' | 'raw'
  preserveEnvelope?: boolean
}

type ApiEnvelope<T> = {
  success: boolean
  data?: T
  error?: { code?: string; message?: string; details?: unknown }
  requestId?: string
  meta?: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}

export type ApiPage<T> = {
  data: T
  meta: NonNullable<ApiEnvelope<unknown>['meta']>
  requestId: string
}

function joinUrl(baseUrl: string, path: string) {
  return `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

function buildQuery(query?: ApiRequestOptions['query']) {
  if (!query) return ''
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    const values = Array.isArray(value) ? value : [value]
    values.forEach(item => params.append(key, String(item)))
  })
  const serialized = params.toString()
  return serialized ? `?${serialized}` : ''
}

function createAbortController(signal: AbortSignal | undefined, timeoutMs: number) {
  const controller = new AbortController()
  let timedOut = false
  const onAbort = () => controller.abort(signal?.reason)
  signal?.addEventListener('abort', onAbort, { once: true })
  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort('timeout')
  }, timeoutMs)
  return {
    signal: controller.signal,
    timedOut: () => timedOut,
    cleanup: () => {
      window.clearTimeout(timeoutId)
      signal?.removeEventListener('abort', onAbort)
    },
  }
}

export class ApiClient {
  private readonly baseUrl: string
  private readonly auth?: AuthAdapter
  private readonly fetchImpl: typeof fetch
  private readonly requestIdFactory: () => string
  private readonly defaultTimeoutMs: number

  constructor(options: ApiClientOptions = {}) {
    const runtimeEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
    this.baseUrl = options.baseUrl ?? runtimeEnv?.VITE_API_BASE_URL ?? '/api/v1'
    this.auth = options.auth
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis)
    this.requestIdFactory = options.requestIdFactory ?? createRequestId
    this.defaultTimeoutMs = options.defaultTimeoutMs ?? 30_000
  }

  get<T>(path: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  getPage<T>(path: string, options: Omit<ApiRequestOptions, 'method' | 'body' | 'preserveEnvelope'> = {}) {
    return this.request<ApiPage<T>>(path, { ...options, method: 'GET', preserveEnvelope: true })
  }

  post<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
    return this.request<T>(path, { ...options, body, method: 'POST' })
  }

  put<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
    return this.request<T>(path, { ...options, body, method: 'PUT' })
  }

  patch<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
    return this.request<T>(path, { ...options, body, method: 'PATCH' })
  }

  delete<T>(path: string, body?: unknown, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}) {
    return this.request<T>(path, { ...options, body, method: 'DELETE' })
  }

  async request<T>(path: string, options: ApiRequestOptions = {}, hasRetriedAuth = false): Promise<T> {
    const requestId = this.requestIdFactory()
    const abort = createAbortController(options.signal, options.timeoutMs ?? this.defaultTimeoutMs)
    const token = this.auth?.getAccessToken()
    const headers = new Headers(options.headers)
    headers.set('Accept', options.responseType === 'blob' ? 'application/octet-stream' : 'application/json')
    headers.set('X-Request-ID', requestId)
    if (token) headers.set('Authorization', `Bearer ${token}`)
    if (options.ifMatch !== undefined) {
      const rawVersion = String(options.ifMatch).trim()
      headers.set('If-Match', /^\d+$/.test(rawVersion) ? `"${rawVersion}"` : rawVersion)
    }
    if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey)
    const isFormData = options.body instanceof FormData
    const isRawBody = options.bodyMode === 'raw'
    if (options.body !== undefined && !isFormData && !headers.has('Content-Type')) {
      const blobType = options.body instanceof Blob ? options.body.type : ''
      headers.set('Content-Type', isRawBody ? blobType || 'application/octet-stream' : 'application/json')
    }

    const requestBody = options.body === undefined
      ? undefined
      : isFormData || isRawBody
        ? options.body as BodyInit
        : JSON.stringify(options.body)

    try {
      const response = await this.fetchImpl(`${joinUrl(this.baseUrl, path)}${buildQuery(options.query)}`, {
        method: options.method ?? 'GET',
        headers,
        body: requestBody,
        signal: abort.signal,
        credentials: 'include',
      })

      const responseRequestId = response.headers.get('X-Request-ID') || requestId
      if (response.status === 401 && !hasRetriedAuth && this.auth?.refresh) {
        const refreshedToken = await this.auth.refresh()
        if (refreshedToken) {
          abort.cleanup()
          return this.request<T>(path, options, true)
        }
      }

      if (!response.ok) {
        let payload: ApiEnvelope<never> | undefined
        try {
          const raw = await response.json() as ApiEnvelope<never> & {
            detail?: ApiEnvelope<never> | { code?: string; message?: string; details?: unknown }
          }
          if (raw.detail && typeof raw.detail === 'object' && 'success' in raw.detail) {
            payload = raw.detail
          } else if (raw.detail && typeof raw.detail === 'object') {
            const detail = raw.detail as { code?: string; message?: string; details?: unknown }
            payload = { success: false, error: detail }
          } else {
            payload = raw
          }
        } catch {
          payload = undefined
        }
        if (response.status === 401) this.auth?.onUnauthorized?.()
        throw mapHttpError(response.status, {
          code: payload?.error?.code,
          message: payload?.error?.message,
          details: payload?.error?.details,
          requestId: payload?.requestId || responseRequestId,
        })
      }

      if (response.status === 204) return undefined as T
      if (options.responseType === 'blob') return await response.blob() as T
      if (options.responseType === 'text') return await response.text() as T

      const payload = await response.json() as ApiEnvelope<T> | T
      if (payload && typeof payload === 'object' && 'success' in payload) {
        const envelope = payload as ApiEnvelope<T>
        if (!envelope.success) {
          throw new ApiError({
            message: envelope.error?.message || '请求失败',
            code: 'unknown',
            requestId: envelope.requestId || responseRequestId,
            details: envelope.error?.details,
          })
        }
        if (options.preserveEnvelope) {
          if (!envelope.meta) throw new Error('API pagination metadata is missing')
          return {
            data: envelope.data,
            meta: envelope.meta,
            requestId: envelope.requestId || responseRequestId,
          } as T
        }
        return envelope.data as T
      }
      return payload as T
    } catch (error) {
      if (abort.timedOut()) {
        throw new ApiError({
          message: '请求超时，请稍后重试',
          code: 'timeout',
          requestId,
          retryable: true,
        })
      }
      throw mapTransportError(error, requestId)
    } finally {
      abort.cleanup()
    }
  }
}

export const apiClient = new ApiClient({ auth: browserAuthAdapter })
