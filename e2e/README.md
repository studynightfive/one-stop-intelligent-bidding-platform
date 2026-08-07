# M7 跨端 Playwright E2E

本目录由 M7 独占，V3.1 § 14.2 验收清单的全量 E2E 在此维护。

## 当前状态（Phase 0 / Phase 1）

- `playwright.config.ts`：3 viewport（1440 / 1024 / 390）+ webServer 占位
- `helpers/testIds.ts`：跨域稳定选择器字典（M1/M2/M3 负责填充真实 ID）
- `helpers/api-client.ts`：极简 API Client，仅做 Phase 0 后端可达性断言
- `pages/login-page.ts` / `pages/bid-workspace-page.ts` / `pages/evaluation-workspace-page.ts`：
  Page Object 占位，Phase 1+ 接入
- `specs/smoke.spec.ts`：API 可达 + 健康检查 smoke（`@smoke`）
- `specs/business-flow.spec.ts`：V3.1 § 14.2 清单占位（`@contract`）

## CI 启用条件

需由 L0 在 `infra/compose.yaml` 中加入 demo + api 服务且启动后再启用；
当前 `webServer.reuseExistingServer = true`，由 `start.sh / start.ps1` 预先启动。

## 安装

```bash
npm ci --ignore-scripts
npx playwright install --with-deps chromium
```

## 运行

```bash
npm run test           # 全部
npm run test:smoke     # 仅 @smoke
npm run typecheck      # 仅类型检查
```