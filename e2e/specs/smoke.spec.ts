import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

/**
 * Phase 0 / Phase 1 跨端 smoke：仅验证 API 可达 + Web 健康检查。
 *
 * 真正的登录 / 投标 / 评标 E2E 待 M1/M2/M3 接入 `data-testid` 后再扩展。
 * 当前用例保证：
 * 1. 后端 OpenAPI 文档可访问；
 * 2. /health/ready 返回 200；
 * 3. 不依赖 mock。
 */
test.describe('m7 smoke @smoke', () => {
  test('backend OpenAPI is reachable', async ({ request }) => {
    const client = new ApiClient(request);
    const response = await client.send<{ openapi: string }>({
      path: '/api/v1/openapi.json',
    });
    expect(response.openapi).toBe('3.1.0');
  });

  test('ready health endpoint returns ok', async ({ request }) => {
    const client = new ApiClient(request);
    // /health/ready 由 M4 暴露；当前 OpenAPI 仅锁定路径，状态码断言即可
    const result = await client.send<unknown>({
      path: '/api/v1/health/ready',
    });
    expect(result).toBeDefined();
  });
});