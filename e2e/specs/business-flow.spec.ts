import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

/**
 * V3.1 § 14.2 E2E 清单（Phase 2+ 才完整启用，本 spec 仅为契约占位）。
 *
 * 真实业务流 E2E（投标主流程 / 评标主流程 / Portal 跨供应商隔离等）
 * 需要 M5/M6 后端接口稳定 + M1/M2/M3 的 `data-testid` 字典到位后逐项展开。
 */
test.describe('bidding main flow @contract', () => {
  test.skip('create → material → submit → status machine', async () => {
    // 业务流接口未到位（Phase 1 之前）
    expect(true).toBeTruthy();
  });
});

test.describe('evaluation main flow @contract', () => {
  test.skip('invite → submit → score → report', async () => {
    expect(true).toBeTruthy();
  });
});

test.describe('portal cross-supplier isolation @contract', () => {
  test.skip('two suppliers cannot view each other', async ({ request }) => {
    const client = new ApiClient(request);
    await client.send({ path: '/api/v1/portal/me' });
    expect(true).toBeTruthy();
  });
});