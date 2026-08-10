import type { APIRequestContext, APIResponse } from '@playwright/test';

export interface RequestOptions {
  path: string;
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  data?: unknown;
  body?: Buffer;
  query?: Record<string, string | number | boolean>;
}

interface SuccessEnvelope<T> {
  success: true;
  data: T;
  requestId: string;
}

/**
 * E2E-only API client. It keeps authentication, envelope handling and binary
 * uploads in one place without duplicating the browser application's client.
 */
export class ApiClient {
  private accessToken?: string;
  private readonly request: APIRequestContext;
  private readonly baseURL: string;

  constructor(
    request: APIRequestContext,
    baseURL: string = process.env.E2E_API_URL
      ?? `http://127.0.0.1:${process.env.API_PORT ?? '8210'}`,
  ) {
    this.request = request;
    this.baseURL = baseURL;
  }

  setAccessToken(token: string): this {
    this.accessToken = token;
    return this;
  }

  async raw(options: RequestOptions): Promise<APIResponse> {
    const { method = 'GET', path, headers, data, body: binaryBody, query } = options;
    const url = new URL(path, this.baseURL);
    if (query) {
      for (const [key, value] of Object.entries(query)) {
        url.searchParams.set(key, String(value));
      }
    }
    const requestHeaders: Record<string, string> = {
      'Content-Type': binaryBody ? 'application/octet-stream' : 'application/json',
      ...headers,
    };
    if (this.accessToken) requestHeaders.Authorization = `Bearer ${this.accessToken}`;
    const response = await this.request.fetch(url.toString(), {
      method,
      headers: requestHeaders,
      data: binaryBody ?? (data !== undefined ? JSON.stringify(data) : undefined),
    });
    if (!response.ok()) {
      const responseBody = await response.text();
      throw new Error(
        `API ${method} ${path} failed: ${response.status()} ${response.statusText()}\n${responseBody}`,
      );
    }
    return response;
  }

  async send<T = unknown>(options: RequestOptions): Promise<T> {
    const response = await this.raw(options);
    if (response.headers()['content-type']?.includes('application/json')) {
      return (await response.json()) as T;
    }
    return undefined as T;
  }

  async data<T>(options: RequestOptions): Promise<T> {
    const envelope = await this.send<SuccessEnvelope<T>>(options);
    if (envelope.success !== true || !envelope.requestId) {
      throw new Error(`API ${options.method ?? 'GET'} ${options.path} returned an invalid envelope`);
    }
    return envelope.data;
  }
}
