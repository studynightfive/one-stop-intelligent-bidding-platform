import type { APIRequestContext } from '@playwright/test';

export interface RequestOptions {
  path: string;
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  data?: unknown;
  query?: Record<string, string | number | boolean>;
}

/**
 * 极简 API Client：仅做基础 HTTP 封装，便于 Phase 1 smoke 验证。
 *
 * 注意：完整 API Client（含鉴权 / 错误处理 / 请求 Id）由 M3 维护；
 * M7 仅在 E2E 中辅助做后端可达性 + 契约断言，不重复造客户端。
 */
export class ApiClient {
  constructor(
    private readonly request: APIRequestContext,
    private readonly baseURL: string = 'http://127.0.0.1:8210',
  ) {}

  async send<T = unknown>(options: RequestOptions): Promise<T> {
    const { method = 'GET', path, headers, data, query } = options;
    const url = new URL(path, this.baseURL);
    if (query) {
      for (const [key, value] of Object.entries(query)) {
        url.searchParams.set(key, String(value));
      }
    }
    const response = await this.request.fetch(url.toString(), {
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
      data: data !== undefined ? JSON.stringify(data) : undefined,
    });
    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `API ${method} ${path} failed: ${response.status()} ${response.statusText()}\n${body}`,
      );
    }
    if (response.headers()['content-type']?.includes('application/json')) {
      return (await response.json()) as T;
    }
    return undefined as T;
  }
}