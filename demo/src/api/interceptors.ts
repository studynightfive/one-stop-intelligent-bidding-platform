export type ApiErrorCode =
  | 'bad_request'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'version_conflict'
  | 'validation_failed'
  | 'rate_limited'
  | 'server_error'
  | 'network_error'
  | 'timeout'
  | 'cancelled'
  | 'unknown'

export interface ApiErrorPayload {
  code?: string
  message?: string
  details?: unknown
  requestId?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: ApiErrorCode
  readonly requestId?: string
  readonly details?: unknown
  readonly retryable: boolean

  constructor(options: {
    message: string
    status?: number
    code?: ApiErrorCode
    requestId?: string
    details?: unknown
    retryable?: boolean
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.status = options.status ?? 0
    this.code = options.code ?? 'unknown'
    this.requestId = options.requestId
    this.details = options.details
    this.retryable = options.retryable ?? false
  }
}

export class VersionConflictError extends ApiError {
  constructor(message: string, requestId?: string, details?: unknown) {
    super({
      message,
      status: 409,
      code: 'version_conflict',
      requestId,
      details,
      retryable: false,
    })
    this.name = 'VersionConflictError'
  }
}

const statusMessages: Record<number, string> = {
  400: '请求内容不正确，请检查后重试',
  401: '登录状态已失效，请重新登录',
  403: '当前账号没有执行此操作的权限',
  404: '请求的内容不存在或已被删除',
  409: '数据已被其他成员更新，请刷新后重试',
  422: '部分字段未通过校验，请检查输入内容',
  429: '操作过于频繁，请稍后再试',
}

export function createRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function mapHttpError(status: number, payload: ApiErrorPayload | undefined, fallbackRequestId?: string) {
  const requestId = payload?.requestId || fallbackRequestId
  const message = payload?.message || statusMessages[status] || (status >= 500 ? '服务暂时不可用，请稍后重试' : '请求失败，请稍后重试')

  if (status === 409) return new VersionConflictError(message, requestId, payload?.details)

  const code: ApiErrorCode = status === 400
    ? 'bad_request'
    : status === 401
      ? 'unauthorized'
      : status === 403
        ? 'forbidden'
        : status === 404
          ? 'not_found'
          : status === 422
            ? 'validation_failed'
            : status === 429
              ? 'rate_limited'
              : status >= 500
                ? 'server_error'
                : 'unknown'

  return new ApiError({
    message,
    status,
    code,
    requestId,
    details: payload?.details,
    retryable: status === 429 || status >= 500,
  })
}

export function mapTransportError(error: unknown, requestId?: string) {
  if (error instanceof ApiError) return error
  if (error instanceof DOMException && error.name === 'AbortError') {
    return new ApiError({ message: '请求已取消', code: 'cancelled', requestId })
  }
  return new ApiError({
    message: '网络连接异常，请检查网络后重试',
    code: 'network_error',
    requestId,
    retryable: true,
    details: error,
  })
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
