import { describe, expect, it, vi } from 'vitest'
import { ApiClient } from '../client'
import { ApiError, VersionConflictError } from '../interceptors'

function jsonResponse(body: unknown, status = 200, requestId = 'server-request') {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId },
  })
}

describe('ApiClient', () => {
  it('adds auth, request id, query and unwraps success envelopes', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ success: true, data: { id: 'U1' } })) as unknown as typeof fetch
    const client = new ApiClient({
      baseUrl: 'https://api.example.test/v1',
      fetchImpl: fetchMock,
      requestIdFactory: () => 'client-request',
      auth: { getAccessToken: () => 'token-1' },
    })

    await expect(client.get<{ id: string }>('/users', { query: { page: 2, status: 'active', ignored: undefined } })).resolves.toEqual({ id: 'U1' })
    const [url, init] = vi.mocked(fetchMock).mock.calls[0]
    expect(url).toBe('https://api.example.test/v1/users?page=2&status=active')
    const headers = new Headers(init?.headers)
    expect(headers.get('Authorization')).toBe('Bearer token-1')
    expect(headers.get('X-Request-ID')).toBe('client-request')
    expect(init?.credentials).toBe('include')
  })

  it('preserves pagination metadata for list adapters', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({
      success: true,
      data: [{ id: 'T1' }],
      meta: { page: 2, pageSize: 10, total: 21, totalPages: 3 },
      requestId: 'page-request',
    })) as unknown as typeof fetch
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock })

    await expect(client.getPage<Array<{ id: string }>>('/bid-tasks', { query: { page: 2 } })).resolves.toEqual({
      data: [{ id: 'T1' }],
      meta: { page: 2, pageSize: 10, total: 21, totalPages: 3 },
      requestId: 'page-request',
    })
  })

  it('refreshes a session once after 401', async () => {
    let token = 'expired'
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ success: false, error: { message: 'expired' } }, 401))
      .mockResolvedValueOnce(jsonResponse({ success: true, data: { ok: true } })) as unknown as typeof fetch
    const refresh = vi.fn(async () => {
      token = 'fresh'
      return token
    })
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock, auth: { getAccessToken: () => token, refresh } })

    await expect(client.get<{ ok: boolean }>('/auth/me')).resolves.toEqual({ ok: true })
    expect(refresh).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(new Headers(vi.mocked(fetchMock).mock.calls[1][1]?.headers).get('Authorization')).toBe('Bearer fresh')
  })

  it('maps optimistic locking conflicts with request metadata', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ success: false, error: { message: '版本冲突', details: { currentVersion: 3 } }, requestId: 'conflict-request' }, 409)) as unknown as typeof fetch
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock })

    const error = await client.patch('/users/U1', { name: '新姓名' }, { ifMatch: 2 }).catch(value => value) as VersionConflictError
    expect(error).toBeInstanceOf(VersionConflictError)
    expect(error.requestId).toBe('conflict-request')
    expect(error.details).toEqual({ currentVersion: 3 })
    expect(new Headers(vi.mocked(fetchMock).mock.calls[0][1]?.headers).get('If-Match')).toBe('2')
  })

  it('maps FastAPI detail errors before the global envelope handler runs', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({
      detail: { code: 'UNAUTHENTICATED', message: '璇峰厛鐧诲綍' },
    }, 401)) as unknown as typeof fetch
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock })

    const error = await client.get('/auth/me').catch(value => value) as ApiError
    expect(error.code).toBe('unauthorized')
    expect(error.message).toBe('璇峰厛鐧诲綍')
  })

  it('marks server and network failures as retryable', async () => {
    const serverClient = new ApiClient({ baseUrl: '/api/v1', fetchImpl: vi.fn(async () => jsonResponse({}, 503)) as unknown as typeof fetch })
    const serverError = await serverClient.get('/health').catch(value => value) as ApiError
    expect(serverError.code).toBe('server_error')
    expect(serverError.retryable).toBe(true)

    const networkClient = new ApiClient({ baseUrl: '/api/v1', fetchImpl: vi.fn(async () => { throw new TypeError('offline') }) as unknown as typeof fetch })
    const networkError = await networkClient.get('/health').catch(value => value) as ApiError
    expect(networkError.code).toBe('network_error')
    expect(networkError.retryable).toBe(true)
  })

  it('sends idempotency keys and supports binary responses', async () => {
    const fetchMock = vi.fn(async () => new Response(new Blob(['demo']), { status: 200 })) as unknown as typeof fetch
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock })
    const result = await client.post<Blob>('/files', { name: 'demo' }, { idempotencyKey: 'idem-1', responseType: 'blob' })
    expect(result).toBeInstanceOf(Blob)
    expect(new Headers(vi.mocked(fetchMock).mock.calls[0][1]?.headers).get('Idempotency-Key')).toBe('idem-1')
  })

  it('sends upload parts as raw binary without JSON serialization', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({
      success: true,
      data: { partNumber: 1, etag: 'real-etag' },
      requestId: 'upload-request',
    })) as unknown as typeof fetch
    const client = new ApiClient({ baseUrl: '/api/v1', fetchImpl: fetchMock })
    const part = new Blob(['binary-part'], { type: 'application/octet-stream' })

    await expect(client.put<{ partNumber: number; etag: string }>(
      '/files/upload-sessions/U1/parts/1',
      part,
      { bodyMode: 'raw' },
    )).resolves.toEqual({ partNumber: 1, etag: 'real-etag' })

    const init = vi.mocked(fetchMock).mock.calls[0][1]
    expect(init?.body).toBe(part)
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/octet-stream')
  })
})
