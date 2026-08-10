# M7 跨端 Playwright E2E

本目录维护真实 API 模式下的跨端验收，不使用前端 Mock，也不保留跳过的占位用例。

## 覆盖范围

- 桌面、平板、移动端：登录、投标工作台、投标创建/详情、评标工作台、评标创建/详情、四个管理页面。
- 投标闭环：上传招标文件 → 创建任务 → AI 解析 → AI 审核 → 按模板逐段生成技术文档 → 嵌入图片 → 下载并校验 DOCX。
- 评标闭环：发布邀请 → 两家供应商提交 → AI 材料/风险/评分 → 人工复核 → 生成 PDF/DOCX 报告 → 关闭评标。
- 门户隔离：两个供应商令牌只能读取各自身份和材料上下文。

## 前置条件

先用隔离的 Compose 项目启动 `api` 和 `web`。Playwright 不隐式创建或遗留 Docker 资源，端口通过环境变量传入：

```powershell
$env:WEB_PORT = '33210'
$env:API_PORT = '38210'
$env:E2E_BASE_URL = 'http://127.0.0.1:33210'
$env:E2E_API_URL = 'http://127.0.0.1:38210'
npm run test
```

业务流会创建带随机后缀的测试任务，不依赖可重复消费的预置邀请码。状态变更用例仅在 desktop 项目执行一次，页面 smoke 在三个 viewport 都执行。

## 命令

```bash
npm ci --ignore-scripts
npm run typecheck
npm run lint
npm run test:smoke
npm run test
```

默认复用操作系统或 CI Runner 已安装的 Chrome，不额外下载浏览器；失败现场使用截图和 trace 留存，因此也不依赖 Playwright 的 ffmpeg。需要使用 Playwright 随附 Chromium 时，先执行 `npx playwright install chromium`，并设置 `E2E_BROWSER_CHANNEL=chromium`。测试机已经安装 ffmpeg 且需要录像时，可设置 `E2E_VIDEO=true`。
