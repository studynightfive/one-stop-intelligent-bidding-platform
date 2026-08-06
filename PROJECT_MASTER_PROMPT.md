# 一站式智能招投标平台：全栈项目总提示词与协作契约 V3.0

> 文档状态：**唯一权威开发提示词（Single Source of Truth）**
> 适用对象：组长 + 7 名组员 + 所有辅助编码 AI
> 基线日期：2026-08-06
> 前端基线：当前 `demo/` 目录中的 React Demo
> 旧文档关系：`PRD.md`、`ARCHITECTURE.md`、`DESIGN.md`、`SPEC.md` 仅作背景材料；与本文冲突时，**无条件以本文为准**。

---

## 0. 如何使用本提示词

每一名成员开始编码前，必须把本文完整提供给自己的编码 AI，并追加一句：

```text
我是成员 Mx，只实现本文“人员分工”中分配给 Mx 的模块。先读取接口契约、状态机、目录所有权和验收标准，再输出本次实施计划。不得修改未分配目录，不得自行新增或更名接口；若契约不足，先提交 CONTRACT-CHANGE 提案，等待组长合并契约后再编码。
```

编码 AI 的固定工作顺序：

1. 确认自己的成员编号和文件所有权。
2. 阅读本文件对应功能、接口、状态机、RBAC 与验收项。
3. 检查 `contracts/openapi.yaml` 与生成客户端；禁止手写重复 DTO。
4. 先写或更新测试，再实现功能。
5. 本地运行规定的 lint、类型检查、单元测试和相关 E2E。
6. 提交 PR，列出完成的验收编号、接口变化和截图/测试证据。

---

## 1. 不可妥协的总规则

### 1.1 功能完整性

- 当前 Demo 中出现的每个页面、Tab、按钮、筛选器、表单、上传区、下载入口、状态卡片、通知和确认弹窗都必须有真实实现。
- 禁止出现点击无反应、仅 `message.info('开发中')`、假进度、硬编码成功、固定下载文本、`TODO`、`FIXME`、HTTP 501 或生产环境 Mock。
- 按钮只有两种合法状态：
  1. 可操作并调用真实接口；
  2. 因权限或业务状态不可操作，同时明确显示禁用原因。
- 所有读操作必须有 loading、empty、error、permission-denied 四种状态；所有写操作必须有 submitting、success、business-error、network-error、duplicate-submit 五种状态。
- AI 只给建议或评分依据；废标确认、人工评分调整、发布、关闭、停用用户、回滚版本等高风险动作必须人工确认并留痕。
- `VITE_USE_MOCKS=true` 只允许本地视觉开发；CI、集成环境和生产构建必须为 `false`。CI 必须扫描并阻止 Mock 数据进入生产路径。

### 1.2 契约唯一性

- API 基础路径统一为 `/api/v1`。
- HTTP JSON 字段统一使用 `camelCase`；Python 内部模型可使用 snake_case，但必须通过 Pydantic alias 输出 camelCase。
- PostgreSQL 表名、列名统一使用 `snake_case`。
- 前端不得手写 API 返回类型；类型只能由 `contracts/openapi.yaml` 生成到 `demo/src/api/generated/`。
- `demo/src/api/generated/` 是生成目录，任何人不得手工编辑。
- 只有组长可以合并 `contracts/openapi.yaml`、数据库迁移主链、根级 Compose 和 CI 工作流的改动。
- 不允许成员在自己的模块中创建第二套 `fetch`、Axios 实例、错误格式、分页格式、状态枚举或日期格式。
- 初始仓库尚未进入全栈 Phase 0 时，以本文第 7、8 节为接口源；L0 的第一个开发 PR 必须把它无损落为 `contracts/openapi.yaml`。此后每次契约变化必须在同一 PR 同步修改本文、OpenAPI、示例和生成客户端，禁止二者漂移。

### 1.3 安全与审计

- 内部用户使用短期 Access JWT；Refresh Token 只存于 `HttpOnly + Secure + SameSite=Lax` Cookie，禁止写入 localStorage。
- 供应商邀请码只能交换一次短期 Portal Access Token；完整令牌不得写入日志、URL 查询日志或审计详情。
- API Key 只能由后端加密保存；前端永远只能读取脱敏值和末四位。
- 所有资源查询必须应用 `tenantId` 隔离；禁止只在前端过滤租户数据。
- 评标审计日志 append-only，数据库触发器禁止 UPDATE 和 DELETE。
- 文件必须校验扩展名、MIME、魔数、大小和 SHA-256，并通过病毒扫描后才可进入业务流程。
- 金额计算禁止浮点数；API 金额使用两位小数字符串，数据库使用 `NUMERIC(18,2)`。

### 1.4 完成定义

一个功能只有同时满足以下条件才算完成：真实接口、权限校验、数据库持久化、异常状态、审计记录、单元测试、接口测试、关键 E2E、无障碍名称、中文文案和文档全部完成。

---

## 2. 产品目标与完整功能范围

平台包含“投标中心”和“评标中心”两条业务线，以及资质库、文档片段库、用户权限、通知、系统配置和审计等公共能力。

### 2.1 投标中心七步闭环

1. 上传招标文件并创建任务：PDF、Word、Excel、PPT、图片、压缩包；支持续传、取消和失败重试。
2. AI 解析：提取项目基本信息、评分项、废标项、资质要求、技术参数并允许人工修正。
3. 材料清单：生成、增删改、排序；自动匹配资质库与片段库；展示来源和置信度。
4. 清单与模板：导出 Excel；按缺失项生成并下载 Word 模板；已有材料可预览下载。
5. 材料处理：单个/批量上传、自动匹配、手工改绑、替换、删除、冲突提示和历史记录。
6. AI 审核：签字盖章、价格填充、内容响应、跨章节一致性；建议可接受、忽略或修改后重审。
7. 文档输出：按要求生成资质标、商务标、技术标或合并 Word；版本比较、下载、回滚和重新生成。

### 2.2 评标中心六步闭环

1. 创建与发布：可从投标任务导入；草稿自动保存/恢复；材料、评分、评审、供应商和评审人校验；预览后发布。
2. 供应商提交：每家独立邀请链接、身份锁定、草稿、材料上传/替换、正式提交、回执和截止控制。
3. 材料审核：完整性、疑似伪造、补材料通知、响应倒计时和超时处理。
4. 评标评审：废标风险、AI 初评、人工复审、调整原因、多轮报价与价格公式。
5. 综合结果：技术/商务/资质分、总分、排名、候选人、废标供应商、评标报告 Word/PDF。
6. 评标关闭：关闭全部 Portal 能力，归档文件、报告和 append-only 审计日志。

### 2.3 页面级“不得缺失”矩阵

| 路由/区域 | 必须完整实现的交互 |
|---|---|
| `/login` | 登录、密码可见性、表单校验、忘记密码、会话刷新、退出后失效 |
| 全局布局 | 投标/评标切换、响应式侧栏、Ctrl/Cmd+K 全局搜索、通知已读、账号菜单、退出 |
| `/dashboard` | 统计下钻、关键词/负责人/状态/我的/临期/风险筛选、重置、CSV 导出、表格/看板、复制任务、归档、发起评标 |
| `/tasks/create` | 项目信息、招标文件续传、格式校验、解析进度、解析失败重试、解析结果确认、创建任务 |
| `/tasks/:id` | 七步进度、关联评标、材料 CRUD/上传/模板/导出、AI 审核及建议动作、Word 生成、版本下载/比较/回滚、招标要求查看 |
| `/admin/qualifications` | 搜索/分类/状态筛选、动态有效期、来源/发证机构/版本、上传/编辑/更新/预览/下载、批量导入、30/60/90 天提醒 |
| `/admin/fragments` | 关键词/语义搜索、分类、匹配度与理由、来源/版本、上传/编辑/预览/引用、版本历史、引用统计 |
| `/admin/users` | 搜索、角色/部门/状态筛选、邀请/编辑、项目下钻、密码重置邮件、启停确认、活动日志、RBAC 矩阵 |
| `/admin/settings` | 模型服务商、脱敏密钥更新、连接测试、场景路由、生成参数、智能体状态、部署/存储、备份、文档模板、通知事件、操作日志导出 |
| `/evaluation` | 统计下钻、搜索/负责人/状态筛选、表格/看板、相对截止时间、风险明细、创建任务、外部门户入口 |
| `/evaluation/create` | 投标项目导入、五步向导、自动/手动草稿、恢复、日期关系校验、材料/权重/供应商/评审人校验、发布预览、发布确认 |
| `/evaluation/:id` | 六步进度、供应商提交、独立邀请链接、补材料通知、多轮报价、资格审查、废标人工确认、技术/商务人工复审、综合排名、报告、关闭、审计导出 |
| `/evaluation/portal/:inviteCode` | 邀请码交换、供应商锁定、项目与倒计时、材料草稿/上传/替换/正式提交/回执、补材料、多轮报价、提交记录、结束页 |

### 2.4 公共功能

- 多租户隔离、4 个内部角色和供应商外部身份。
- 站内实时通知；开发环境使用 Mailpit 验证邮件发送。
- 文件中心、异步任务中心、统一审计、全局搜索。
- 模型服务商、业务场景路由、熔断、重试和使用量记录。
- 系统部署、存储用量、备份、文档模板和通知策略设置。
- 所有列表具备服务端搜索、筛选、排序、分页；导出使用当前筛选条件。

---

## 3. 锁定架构与仓库目录

```text
repo-root/
├─ demo/                         # React 前端，现有 Demo 在此渐进替换为真实接口
│  ├─ src/api/generated/         # OpenAPI 生成代码，禁止手改
│  ├─ src/api/client.ts          # 唯一 HTTP 客户端
│  ├─ src/features/              # 新增功能按领域拆分
│  └─ src/pages/                 # 现有路由页，保留视觉基线
├─ backend/
│  ├─ app/api/v1/                # FastAPI 路由
│  ├─ app/domains/               # auth/users/bids/evaluations/libraries/settings
│  ├─ app/ai/                    # LangGraph、模型路由、提示词版本
│  ├─ app/workers/               # Celery 任务
│  ├─ app/core/                  # 配置、安全、数据库、错误、日志
│  ├─ migrations/                # Alembic 单一迁移链
│  └─ tests/
├─ contracts/
│  ├─ openapi.yaml               # 唯一接口契约
│  ├─ events.schema.json         # WebSocket 事件契约
│  └─ examples/                  # 请求响应示例
├─ infra/
│  ├─ compose.yaml
│  ├─ postgres/
│  ├─ minio/
│  ├─ nginx/
│  └─ monitoring/
├─ e2e/                          # Playwright 跨端 E2E
├─ scripts/                      # bootstrap、生成契约、检查环境
├─ PROJECT_MASTER_PROMPT.md      # 本文件
├─ .env.example
└─ README.md
```

架构规定：

- 前端：React SPA，通过生成客户端调用 FastAPI。
- 后端：模块化单体 FastAPI；小组作业期间禁止拆微服务。
- 异步：Celery + Redis；解析、AI、报告、导出、通知均通过任务队列。
- 数据：PostgreSQL 16 + pgvector；SQLAlchemy 2 async；Alembic 迁移。
- 文件：MinIO；数据库只保存元数据、对象键和哈希。
- 实时：WebSocket；先通过 REST 获取 30 秒有效的一次性连接票据。
- AI：LangGraph；场景路由配置存数据库，API Key 使用 AES-256-GCM 信封加密。

---

## 4. 运行环境与冲突隔离（锁定）

### 4.1 版本锚点

| 层 | 锁定版本 |
|---|---|
| Node.js | `24.16.0` |
| npm | `11.13.0`；只允许 `npm ci`，禁止删除 `package-lock.json` |
| React / React DOM | `18.3.1` |
| TypeScript | `5.9.3` |
| Vite | `5.4.21` |
| Ant Design | `5.29.3` |
| React Router | `6.30.4` |
| Tailwind CSS | `3.4.19` |
| Lucide React | `0.400.0`，唯一图标库 |
| Python | `3.11.11`，禁止使用主机 Python 3.12/3.13 创建锁文件 |
| uv | `0.5.11`；只允许 `uv sync --frozen` |
| FastAPI | `0.115.6` |
| Pydantic | `2.10.4` |
| SQLAlchemy | `2.0.36` |
| Alembic | `1.14.0` |
| Celery | `5.4.0` |
| LangGraph | `0.2.60` |
| PostgreSQL | `16.4` |
| pgvector | `0.7.4` |
| Redis | `7.2.5` |
| MinIO | `RELEASE.2024-07-16T23-46-41Z` |
| Docker Engine | 参考 `29.6.1`；不得低于 27 |
| Docker Compose | 参考 `5.2.0`；不得低于 v2.29 |

新增依赖必须单独 PR，说明用途、许可证、包体积/安全影响，并由组长更新本表和锁文件。

### 4.2 唯一端口表

| 服务 | 主机端口 | 容器端口 | 地址 |
|---|---:|---:|---|
| Web | 3210 | 3210 | `http://127.0.0.1:3210` |
| API / OpenAPI | 8210 | 8000 | `http://127.0.0.1:8210/api/v1` / `/docs` |
| PostgreSQL | 55432 | 5432 | 仅开发机访问 |
| Redis | 56379 | 6379 | 仅开发机访问 |
| MinIO API | 59000 | 9000 | `http://127.0.0.1:59000` |
| MinIO Console | 59001 | 9001 | `http://127.0.0.1:59001` |
| Mailpit SMTP | 51025 | 1025 | 仅开发机访问 |
| Mailpit Web | 58025 | 8025 | `http://127.0.0.1:58025` |
| Flower | 5556 | 5555 | `http://127.0.0.1:5556` |
| Prometheus | 59090 | 9090 | `http://127.0.0.1:59090` |
| Grafana | 53000 | 3000 | `http://127.0.0.1:53000` |

禁止成员自行修改端口。若端口占用，先停止冲突进程，不得给自己的分支另设端口。

### 4.3 容器与命名隔离

- Compose 项目名固定：`bidplat2026`。
- 容器名、网络和卷统一以 `bidplat2026_` 开头。
- PostgreSQL 数据库：`bid_platform`；测试库：`bid_platform_test`。
- Redis Key 前缀：`bidplat:{environment}:{tenantId}:`。
- MinIO Bucket：`bidplat-{environment}-{tenantId}`。
- 所有服务时区设为 `UTC`；数据库保存 UTC；前端统一按 `Asia/Shanghai` 显示。
- 文件编码 UTF-8、换行 LF；不得提交 CRLF 批量改写。

### 4.4 环境文件

- 只提交 `.env.example`，绝不提交 `.env`、私钥、API Key、数据库快照或真实供应商文件。
- 前端只允许 `VITE_` 前缀变量；密钥不得放入前端环境变量。
- 本地、测试、CI、生产各用独立数据库、Redis DB/前缀和 MinIO Bucket。
- 本地启动顺序：

```bash
docker compose -p bidplat2026 --env-file .env up -d postgres redis minio mailpit clamav
cd backend && uv sync --frozen && uv run alembic upgrade head
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd backend && uv run celery -A app.workers.celery_app worker -l INFO
cd demo && npm ci && npm run dev -- --port 3210
```

禁止在仓库根目录、`demo/`、`backend/` 之间复用 `node_modules`、`.venv` 或 lock 文件。

---

## 5. 八人小组任务拆分

### 5.1 角色总览

| 编号 | 角色 | 独占范围 | 核心交付 |
|---|---|---|---|
| L0 | 组长 | 契约、迁移主链、Compose、CI、集成与发布 | 架构决策、接口合并、数据库审查、联调、版本发布 |
| M1 | 投标前端 | `demo/src/pages/Dashboard.tsx`、`BidCreate.tsx`、`TaskDetail.tsx`、投标 feature | 投标七步、列表/看板、上传、审核、输出、版本 UI |
| M2 | 评标前端 | `EvaluationDashboard.tsx`、`EvaluationCreate.tsx`、`EvaluationTaskDetail.tsx`、`SupplierPortal.tsx` | 评标六步、外部门户、评分、报价、审计 UI |
| M3 | 管理与公共前端 | `MainLayout.tsx`、Login、Qualification、Fragment、User、Settings、前端 API 适配层 | 登录/导航/通知/库管理/权限/设置/错误与状态组件 |
| M4 | 平台后端 | `backend/app/domains/auth`、`users`、`files`、`notifications`、`settings` | JWT、RBAC、用户、统一文件、通知、配置、全局审计 |
| M5 | 投标后端 | `backend/app/domains/bids`、`qualifications`、`fragments`、`documents` | 投标任务、材料、资源库、审核编排接口、Word/版本服务 |
| M6 | 评标后端 | `backend/app/domains/evaluations`、`portal`、`pricing`、`scoring` | 评标任务、供应商、报价、补材料、评分、排名、关闭、审计 |
| M7 | AI 与质量 | `backend/app/ai`、`backend/app/workers`、`e2e/`、AI 测试数据 | 解析、匹配、审核、评分、报告、模型降级、异步任务、关键 E2E |

### 5.2 每人详细任务与验收

#### L0 组长

- 维护 `PROJECT_MASTER_PROMPT.md`、`contracts/*`、根环境文件、Compose、CI 和迁移编号。
- 建立 `main`、`develop` 保护规则；所有 PR 至少一人审查，接口/迁移 PR 必须由组长审查。
- 每日合并契约和生成客户端，主持接口联调；禁止亲自绕过契约做临时接口。
- 维护集成环境、种子数据、演示账号、版本标签和最终答辩脚本。
- 验收：全量 CI 通过、所有页面无死按钮、关键 E2E 全绿、可从空数据库一键启动。

#### M1 投标前端

- 将现有投标 Demo 状态逐步替换为生成 API 客户端；不得改动评标页面。
- 完成上传续传、解析进度、材料 CRUD/匹配/上传、审核建议、文档生成与版本操作。
- 完成列表筛选、统计下钻、CSV 导出、空/错/权限状态和响应式。
- 测试：投标组件测试 + `bid-flow.spec.ts`。

#### M2 评标前端

- 完成任务导入、草稿、五步校验、发布、供应商链接、门户身份锁定。
- 完成补材料、多轮报价、资格审查、废标确认、AI/人工评分、排名、报告、关闭和审计。
- Portal 不得复用内部 JWT；过期、撤销、关闭必须有独立页面。
- 测试：评标组件测试 + `evaluation-flow.spec.ts` + `supplier-portal.spec.ts`。

#### M3 管理与公共前端

- 完成认证会话、全局错误边界、生成客户端包装、搜索、通知、响应式布局。
- 完成资质来源/版本/提醒、片段语义搜索/版本、用户 RBAC、全部系统设置。
- 建立复用的 Loading/Empty/Error/Forbidden/Confirm/Upload/JobProgress 组件。
- 测试：`admin-flow.spec.ts`、无障碍扫描和前端错误状态测试。

#### M4 平台后端

- 实现认证、Token 轮换、密码重置、用户邀请/启停、RBAC、租户隔离。
- 实现统一文件上传会话、分片、哈希、病毒扫描、MinIO 和附件权限。
- 实现站内/邮件通知、一次性 WebSocket Ticket、系统设置、密钥加密和连接测试。
- 所有模块提供依赖注入接口，禁止业务模块绕过文件/通知服务直连 MinIO/SMTP。

#### M5 投标后端

- 实现投标任务状态机、招标文件挂载、材料清单、库匹配、资源库、分配和导出。
- 对接 M7 异步解析/审核/生成任务，持久化进度和结果。
- 实现文档版本哈希、比较、回滚为新版本，禁止覆盖历史文件。
- 负责投标域数据库模型、服务测试和接口测试。

#### M6 评标后端

- 实现评标草稿/导入/验证/发布状态机；独立供应商邀请码的生成、交换、撤销和轮换。
- 实现供应商材料草稿/正式提交/回执、补材料、多轮报价和并发幂等。
- 实现废标人工确认、评分调整、排名、报告元数据、关闭和 append-only 审计。
- 负责评标域数据库模型、状态迁移测试和接口测试。

#### M7 AI 与质量

- LangGraph 节点：解析、需求提取、材料生成、语义匹配、四类投标审核、完整性、废标风险、评分、报告。
- 所有 AI 输出必须用 Pydantic Schema 校验；失败进入重试/降级/人工处理，不得把未校验文本写入业务表。
- 建立离线固定样本和评估指标；AI 测试默认使用 Fake Provider，真实 Key 仅在手工受控测试使用。
- 维护 Celery 进度、取消、重试、幂等；编写三条核心 E2E 和错误流测试。

### 5.3 避免冲突的文件所有权

- 同一 PR 不得同时大改前端公共布局和领域页面。
- M1/M2 需要公共组件时向 M3 提交需求；M3 合并组件后再引用。
- M5/M6 需要平台能力时依赖 M4 的接口，不得复制认证、文件或通知代码。
- M7 不直接写业务表，通过 M5/M6 提供的 repository/service 接口回写结果。
- Alembic revision 由成员生成后交 L0 重新编号/合并，任何人不得自行解决双 head 后直接推送。

---

## 6. Git 与合并流程

- 长期分支：`main`（稳定演示）、`develop`（集成）。禁止直接提交。
- 成员分支：`feat/m1-bid-web-*`、`feat/m2-eval-web-*`、`feat/m3-admin-web-*`、`feat/m4-platform-api-*`、`feat/m5-bid-api-*`、`feat/m6-eval-api-*`、`feat/m7-ai-qa-*`。
- 修复分支：`fix/mX-issue-number-description`；契约提案：`contract/issue-number-description`。
- Commit 使用 Conventional Commits：`feat(bid): ...`、`fix(portal): ...`、`test(e2e): ...`、`docs(contract): ...`。
- 禁止提交生成物 `node_modules/`、`dist/`、`.venv/`、真实 `.env`、上传文件和数据库卷。
- 接口变更顺序严格为：
  1. CONTRACT-CHANGE Issue；
  2. 修改 OpenAPI + 示例 + 契约测试；
  3. L0 合并并生成客户端；
  4. 后端实现；
  5. 前端接入；
  6. E2E 验证。
- PR 合并门禁：format、lint、typecheck、unit、API test、OpenAPI breaking check、migration check、critical E2E、secret scan 全部通过。

---

## 7. 统一 API 基础契约

### 7.1 通用规则

```ts
type Id = string;                  // UUID v7，小写带连字符
type IsoDate = string;             // YYYY-MM-DD
type IsoDateTime = string;         // RFC3339 UTC，例如 2026-08-06T04:30:00Z
type Money = string;               // ^(0|[1-9]\d*)\.\d{2}$，单位由 currency 指定
type Currency = 'CNY';

interface ApiSuccess<T> {
  success: true;
  data: T;
  meta?: { page?: number; pageSize?: number; total?: number; totalPages?: number };
  requestId: string;
}

interface ApiError {
  success: false;
  error: {
    code: ErrorCode;
    message: string;
    fieldErrors?: Array<{ field: string; code: string; message: string }>;
    details?: Record<string, unknown>;
  };
  requestId: string;
}

type ErrorCode =
  | 'VALIDATION_ERROR' | 'UNAUTHENTICATED' | 'TOKEN_EXPIRED' | 'FORBIDDEN'
  | 'NOT_FOUND' | 'CONFLICT' | 'VERSION_CONFLICT' | 'RATE_LIMITED'
  | 'DEADLINE_PASSED' | 'INVALID_STATE_TRANSITION' | 'FILE_REJECTED'
  | 'VIRUS_DETECTED' | 'AI_PROVIDER_UNAVAILABLE' | 'JOB_FAILED'
  | 'INTERNAL_ERROR';
```

- HTTP：GET 查询、POST 创建/动作、PATCH 局部更新、DELETE 软删除或撤销。
- 创建返回 201；异步动作返回 202 + `JobRef`；删除成功返回 204；业务冲突返回 409。
- 查询分页参数固定 `page`（从 1 开始）、`pageSize`（默认 20，最大 100）、`sortBy`、`sortOrder=asc|desc`。
- 时间全部 UTC；用户输入必须含时区；响应不得返回无时区时间。
- 所有可编辑实体有整数 `version`；PATCH 必须带 `If-Match: "<version>"`，冲突返回 409 `VERSION_CONFLICT`。
- 发布、正式提交、报价、关闭、回滚、发送通知等 POST 动作必须带 `Idempotency-Key`。
- 请求头统一：`Authorization`、`X-Request-Id`、`Idempotency-Key`、`If-Match`；不得自创同义 Header。
- 二进制下载不套 JSON Envelope，必须返回 `Content-Disposition`、`Content-Type`、`X-File-Sha256`。

### 7.2 核心枚举

```ts
type Role = 'admin' | 'project_lead' | 'member' | 'reviewer';
type UserStatus = 'invited' | 'active' | 'disabled';
type BidTaskStatus = 'draft' | 'parsing' | 'material_prep' | 'ai_review' | 'pending_output' | 'completed' | 'archived' | 'failed';
type BidMaterialStatus = 'pending' | 'have' | 'missing' | 'template' | 'uploaded' | 'expiring' | 'rejected';
type EvaluationStatus = 'draft' | 'collecting' | 'pending' | 'ai_review' | 'human_review' | 'completed' | 'closed' | 'cancelled';
type SupplierStatus = 'invited' | 'partial' | 'submitted' | 'supplementing' | 'qualified' | 'disqualified' | 'overdue' | 'withdrawn';
type QualificationStatus = 'valid' | 'expiring' | 'expired' | 'revoked';
type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
type RiskSeverity = 'info' | 'warning' | 'high' | 'critical';
type Decision = 'pending' | 'passed' | 'rejected';
```

### 7.3 核心 DTO

```ts
interface FileRef {
  id: Id; fileName: string; mimeType: string; sizeBytes: number;
  sha256: string; scanStatus: 'pending' | 'clean' | 'infected' | 'failed';
  previewUrl?: string; downloadUrl?: string; createdAt: IsoDateTime;
}

interface JobRef {
  id: Id; type: string; status: JobStatus; progressPercent: number;
  currentStep?: string; createdAt: IsoDateTime;
}

interface User {
  id: Id; tenantId: Id; name: string; email: string; phone?: string;
  role: Role; department: string; status: UserStatus; projectCount: number;
  lastLoginAt?: IsoDateTime; version: number; createdAt: IsoDateTime; updatedAt: IsoDateTime;
}

interface BidTask {
  id: Id; projectName: string; tenderNo: string; tenderEntity: string;
  deadline: IsoDateTime; status: BidTaskStatus; currentStep: 1|2|3|4|5|6|7;
  progressPercent: number; assignee: Pick<User,'id'|'name'>; tags: string[];
  materialSummary: { total: number; have: number; missing: number };
  linkedEvaluationId?: Id; version: number; createdAt: IsoDateTime; updatedAt: IsoDateTime;
}

interface BidMaterial {
  id: Id; taskId: Id; name: string; category: 'qualification'|'commercial'|'technical';
  requirement: string; status: BidMaterialStatus; required: boolean; sortOrder: number;
  source: 'qualification'|'fragment'|'upload'|'template'|'manual'; sourceId?: Id;
  matchConfidence?: number; file?: FileRef; version: number;
}

interface Qualification {
  id: Id; name: string; category: string; certNumber: string; issuer: string;
  validFrom?: IsoDate; expiryDate?: IsoDate; status: QualificationStatus;
  file: FileRef; documentVersion: string; reminderDays: number[]; tags: string[];
  version: number; createdAt: IsoDateTime; updatedAt: IsoDateTime;
}

interface Fragment {
  id: Id; title: string; category: string; summary: string; content: string;
  tags: string[]; sourceFile?: FileRef; documentVersion: string; useCount: number;
  matchScore?: number; matchReason?: string; version: number;
  createdAt: IsoDateTime; updatedAt: IsoDateTime;
}

interface EvaluationTask {
  id: Id; sourceBidTaskId?: Id; projectName: string; tenderNo: string; tenderEntity: string;
  budgetAmount: Money; currency: Currency; supplierDeadline: IsoDateTime;
  evaluationStartAt: IsoDateTime; evaluationEndAt: IsoDateTime;
  status: EvaluationStatus; currentStep: 1|2|3|4|5|6; progressPercent: number;
  assignee: Pick<User,'id'|'name'>; supplierCount: number; riskCount: number;
  version: number; createdAt: IsoDateTime; updatedAt: IsoDateTime;
}

interface EvaluationMaterial {
  id: Id; evaluationId: Id; name: string; category: 'qualification'|'commercial'|'technical';
  required: boolean; allowedMimeTypes: string[]; maxSizeBytes: number; sortOrder: number;
}

interface ScoringCriterion {
  id: Id; evaluationId: Id; name: string;
  category: 'qualification'|'commercial'|'technical'|'service';
  maxScore: string; weightPercent: string; method: 'expert'|'formula'|'objective';
  formula?: string; description: string; sortOrder: number;
}

interface Supplier {
  id: Id; evaluationId: Id; name: string; contactName: string; email: string;
  phone?: string; status: SupplierStatus; submittedMaterialCount: number;
  requiredMaterialCount: number; currentQuote?: Money; submittedAt?: IsoDateTime;
}

interface ScoreItem {
  supplierId: Id; criterionId: Id; aiScore?: string; aiBasis?: string;
  humanScore?: string; adjustmentReason?: string; finalScore: string;
  adjustedBy?: Pick<User,'id'|'name'>; adjustedAt?: IsoDateTime; version: number;
}

interface RiskFinding {
  id: Id; evaluationId: Id; supplierId: Id; type: string; severity: RiskSeverity;
  title: string; evidence: string[]; aiConfidence?: number;
  decision: Decision; decisionReason?: string; decidedBy?: Pick<User,'id'|'name'>;
  decidedAt?: IsoDateTime; version: number;
}

interface AuditEvent {
  id: Id; tenantId: Id; aggregateType: string; aggregateId: Id;
  actorType: 'user'|'supplier'|'system'; actorId?: Id; actorName: string;
  action: string; targetType?: string; targetId?: Id; summary: string;
  changes?: Array<{ field: string; oldValue: unknown; newValue: unknown }>;
  requestId: string; ipAddress?: string; createdAt: IsoDateTime;
}
```

### 7.4 写接口请求 DTO（字段锁定）

未标 `?` 的字段均为必填。字符串写入前后端都必须 trim；未知字段由后端以 422 拒绝，不得静默忽略。

```ts
interface LoginRequest { email: string; password: string }
interface AuthSession {
  accessToken: string; accessTokenExpiresAt: IsoDateTime;
  user: User; permissions: string[];
}
interface UpdateProfileRequest { name?: string; phone?: string; department?: string }
interface InviteUserRequest { email: string; name: string; phone?: string; role: Role; department: string }
interface UpdateUserRequest { name?: string; phone?: string; role?: Role; department?: string }

interface CreateBidTaskRequest {
  projectName: string; tenderNo?: string; tenderEntity?: string;
  deadline: IsoDateTime; assigneeId: Id; tenderFileId: Id;
  tags?: string[]; description?: string;
}
interface UpdateBidTaskRequest {
  projectName?: string; tenderNo?: string; tenderEntity?: string;
  deadline?: IsoDateTime; assigneeId?: Id; tags?: string[]; description?: string;
}
interface CreateBidMaterialRequest {
  name: string; category: BidMaterial['category']; requirement: string;
  required: boolean; sortOrder: number;
}
interface UpdateBidMaterialRequest {
  name?: string; category?: BidMaterial['category']; requirement?: string;
  required?: boolean; sortOrder?: number; sourceId?: Id;
}
interface BatchBindRequest {
  bindings: Array<{ materialId: Id; fileId: Id }>;
  replaceExisting: boolean;
}
interface CreateBidReviewRequest {
  types: Array<'signature'|'price'|'content'|'consistency'>;
  fileVersionIds?: Id[];
}
interface GenerateBidDocumentRequest {
  mode: 'split'|'merged';
  sections: Array<'qualification'|'commercial'|'technical'>;
  templateMode: 'tender_requirement'|'standard';
  documentTemplateId?: Id;
  includeWatermark: boolean;
}

interface CreateQualificationRequest {
  name: string; category: string; certNumber: string; issuer: string;
  validFrom?: IsoDate; expiryDate?: IsoDate; fileId: Id;
  documentVersion: string; reminderDays: number[]; tags: string[];
}
type UpdateQualificationRequest = Partial<Omit<CreateQualificationRequest,'fileId'>>;

interface CreateFragmentRequest {
  title: string; category: string; summary: string; content?: string;
  sourceFileId?: Id; documentVersion: string; tags: string[];
}
type UpdateFragmentRequest = Partial<Omit<CreateFragmentRequest,'sourceFileId'>>;

interface CreateEvaluationDraftRequest {
  sourceBidTaskId?: Id;
  projectName: string; tenderNo: string; tenderEntity: string;
  budgetAmount: Money; currency: 'CNY'; supplierDeadline: IsoDateTime;
  evaluationStartAt: IsoDateTime; evaluationEndAt: IsoDateTime;
  description?: string; assigneeId: Id;
}
type UpdateEvaluationRequest = Partial<Omit<CreateEvaluationDraftRequest,'sourceBidTaskId'>>;
interface ReviewSettings {
  multiRoundPricing: boolean; maxRounds: number;
  supplementDeadlineMinutes: number; allowModifyBeforeDeadline: boolean;
  notifyOnMissing: boolean; closeSubmissionAtDeadline: boolean;
}
interface SupplierInvitationInput {
  name: string; contactName: string; email: string; phone?: string;
}
interface CreateSupplementNoticeRequest {
  supplierId: Id; materialIds: Id[]; deadlineMinutes: number; message: string;
}
interface CreatePriceRoundRequest {
  title: string; opensAt: IsoDateTime; deadline: IsoDateTime;
  eligibleSupplierIds: Id[]; rankingVisibleToSupplier: boolean;
}

interface CreateUploadSessionRequest {
  fileName: string; mimeType: string; sizeBytes: number; sha256: string;
  purpose: 'tender'|'bidMaterial'|'qualification'|'fragment'|'supplierMaterial'|'template';
  resourceId?: Id;
}
interface UploadSession {
  id: Id; fileName: string; sizeBytes: number; partSizeBytes: number;
  totalParts: number; uploadedParts: Array<{partNumber:number;etag:string}>;
  status: 'created'|'uploading'|'verifying'|'scanning'|'completed'|'cancelled'|'failed';
  expiresAt: IsoDateTime;
}

interface CreateModelProviderRequest {
  provider: 'qwen'|'deepseek'|'zhipu'|'custom_openai_compatible';
  displayName: string; baseUrl: string; apiKey: string; enabled: boolean;
}
interface UpdateModelProviderRequest {
  displayName?: string; baseUrl?: string; apiKey?: string; enabled?: boolean;
}
interface ModelRoute {
  scene: 'tender_parse'|'requirement_extract'|'material_match'|'bid_generate'|'bid_review'|'evaluation_check'|'risk_check'|'evaluation_score'|'report_generate';
  primaryProviderId: Id; primaryModel: string;
  fallbackProviderId: Id; fallbackModel: string;
  timeoutSeconds: number; maxRetries: number; circuitBreakerFailures: number;
}
interface GenerationSettings {
  temperature: number; topP: number; maxOutputTokens: number;
  requestTimeoutSeconds: number; autoRetry: boolean; circuitBreakerEnabled: boolean;
}
```

### 7.5 关键聚合响应（字段锁定）

```ts
interface BidTaskStats { total: number; active: number; aiReview: number; completed: number; risk: number }
interface BidBoardColumn { status: BidTaskStatus; title: string; count: number; tasks: BidTask[] }
interface BidTaskDetail extends BidTask {
  tenderFile?: FileRef; assignments: TaskAssignment[];
  requirements?: TenderRequirements; latestReview?: BidReviewReport;
  documents: BidDocument[];
}
interface TenderRequirements {
  projectInfo: Record<string,string>;
  scoringItems: Array<{name:string;score:string;basis:string}>;
  disqualificationItems: Array<{name:string;basis:string}>;
  qualificationRequirements: string[]; technicalRequirements: string[];
  version: number;
}
interface BidReviewFinding {
  id: Id; type: 'signature'|'price'|'content'|'consistency'; severity: RiskSeverity;
  title: string; description: string; fileId: Id; page?: number; excerpt?: string;
  suggestion: string; decision: 'pending'|'accepted'|'ignored'|'modified'; version: number;
}
interface BidReviewReport {
  id: Id; taskId: Id; status: JobStatus; summary: string;
  counts: {error:number;warning:number;info:number}; findings: BidReviewFinding[];
  completedAt?: IsoDateTime;
}
interface DocumentVersion {
  id: Id; documentId: Id; versionNumber: number; file: FileRef;
  changeSummary: string; createdBy: Pick<User,'id'|'name'>; createdAt: IsoDateTime;
}

interface EvaluationTaskDetail extends EvaluationTask {
  description?: string; materials: EvaluationMaterial[]; scoringCriteria: ScoringCriterion[];
  reviewSettings: ReviewSettings; reviewers: Array<Pick<User,'id'|'name'>>;
  suppliers: Supplier[]; latestJobs: JobRef[]; allowedActions: string[];
}
interface ValidationResult {
  valid: boolean;
  errors: Array<{step:1|2|3|4|5;field:string;code:string;message:string}>;
  warnings: Array<{step:1|2|3|4|5;field?:string;code:string;message:string}>;
}
interface SupplierInviteSummary {
  supplierId: Id; supplierName: string; inviteCodeMasked: string;
  inviteUrl: string; status: 'active'|'used'|'revoked'|'expired'; expiresAt: IsoDateTime;
}
interface PortalSession {
  portalAccessToken: string; accessTokenExpiresAt: IsoDateTime;
  supplier: Pick<Supplier,'id'|'name'|'contactName'|'status'>;
}
interface PortalContext {
  evaluation: Pick<EvaluationTask,'id'|'projectName'|'tenderNo'|'tenderEntity'|'supplierDeadline'|'status'>;
  supplier: Pick<Supplier,'id'|'name'|'status'>;
  submissionSummary: {required:number;submitted:number;missing:number;finalSubmitted:boolean};
  allowedActions: string[];
}
interface SubmissionReceipt {
  receiptNo: string; evaluationId: Id; supplierId: Id;
  submittedAt: IsoDateTime; submittedMaterialCount: number; sha256: string;
}
interface EvaluationRanking {
  rows: Array<{supplierId:Id;supplierName:string;qualificationScore:string;technicalScore:string;commercialScore:string;totalScore:string;rank:number;status:SupplierStatus}>;
  recommendedSupplierId?: Id; generatedAt: IsoDateTime; version: number;
}
```

### 7.6 其余公共响应 DTO（禁止各模块自行定义同名结构）

```ts
interface ProjectSummary { id: Id; kind: 'bid'|'evaluation'; title: string; code: string; status: string; userRole: string; updatedAt: IsoDateTime }
interface RoleDefinition { role: Role; label: string; description: string; permissions: string[]; userCount: number }
interface PermissionMatrix { modules: Array<{module:string;actions:Record<Role,string[]>}> }
interface TaskAssignment { taskId: Id; user: Pick<User,'id'|'name'|'role'>; roleInTask: 'owner'|'collaborator'|'reviewer'; assignedAt: IsoDateTime }
interface BatchBindResult { succeeded: Id[]; failed: Array<{materialId:Id;code:string;message:string}> }
interface BidDocument { id: Id; taskId: Id; type: 'qualification'|'commercial'|'technical'|'merged'; currentVersion: number; latestFile?: FileRef; createdAt: IsoDateTime }
interface DocumentDiff { from: DocumentVersion; to: DocumentVersion; changes: Array<{section:string;type:'added'|'removed'|'changed';before?:string;after?:string}> }
interface QualificationStats { total: number; valid: number; expiring: number; expired: number }
interface FragmentStats { total: number; categoryCount: number; totalReferences: number; semanticRecommended: number }
interface EvaluationStats { total: number; collecting: number; aiReview: number; humanReview: number; completed: number; risk: number }
interface EvaluationPreview { evaluation: EvaluationTaskDetail; validation: ValidationResult; supplierVisibleMaterials: EvaluationMaterial[] }
interface SupplierSubmission { id: Id; supplierId: Id; materialId: Id; file: FileRef; status: 'draft'|'submitted'|'replaced'; submittedAt?: IsoDateTime; replacedAt?: IsoDateTime; version: number }
interface SupplementNotice { id: Id; evaluationId: Id; supplierId: Id; materialIds: Id[]; message: string; deadline: IsoDateTime; status: 'sent'|'viewed'|'responded'|'expired'; sentAt: IsoDateTime; respondedAt?: IsoDateTime }
interface QuoteSubmission { id: Id; roundId: Id; supplierId: Id; amount: Money; currency: 'CNY'; submittedAt: IsoDateTime; version: number }
interface PriceRound { id: Id; evaluationId: Id; roundNumber: number; title: string; opensAt: IsoDateTime; deadline: IsoDateTime; status: 'scheduled'|'open'|'closed'; eligibleSupplierIds: Id[]; submissionCount: number; version: number }
interface PortalPriceRound extends Pick<PriceRound,'id'|'roundNumber'|'title'|'opensAt'|'deadline'|'status'> { myQuote?: QuoteSubmission; myRank?: number; rankingVisible: boolean }
interface PriceComparison { rounds: Array<{round:PriceRound;quotes:QuoteSubmission[]}>; supplierTrends: Array<{supplierId:Id;points:Array<{roundNumber:number;amount:Money;decreasePercent?:string;rank?:number}>}> }
interface MaterialCheckResult { id: Id; evaluationId: Id; status: JobStatus; rows: Array<{supplierId:Id;materialId:Id;result:'provided'|'missing'|'suspicious';evidence:string[];confidence?:number}>; completedAt?: IsoDateTime }
interface EvaluationReport { id: Id; evaluationId: Id; format: 'docx'|'pdf'; versionNumber: number; file: FileRef; createdBy: Pick<User,'id'|'name'>; createdAt: IsoDateTime }
interface PortalMaterial { id: Id; name: string; category: EvaluationMaterial['category']; required: boolean; allowedMimeTypes: string[]; maxSizeBytes: number; file?: FileRef; status: 'missing'|'draft'|'submitted'|'rejected'; submittedAt?: IsoDateTime }
interface PortalDraft { supplierId: Id; note?: string; quoteDraft?: Money; savedAt: IsoDateTime; version: number }
interface PortalActivity { id: Id; action: string; summary: string; occurredAt: IsoDateTime }
interface ModelProviderMasked { id: Id; provider: CreateModelProviderRequest['provider']; displayName: string; baseUrl: string; apiKeyMasked: string; keyLastFour: string; enabled: boolean; connectionStatus: 'unknown'|'connected'|'failed'; lastTestedAt?: IsoDateTime; version: number }
interface DeploymentSettings { mode: 'saas'|'private'; companyName: string; storageQuotaBytes: number; maxProjects: number; maxUsers: number; autoBackup: boolean; backupCron: string; versionControlEnabled: boolean; version: number }
interface DocumentTemplateSettings { format: 'standard'|'custom'; pageSize: 'A4'|'A3'|'Letter'; bodyFont: string; bodyFontSizePt: number; lineSpacing: number; marginMode: 'standard'|'narrow'|'wide'; splitBySection: boolean; watermarkEnabled: boolean; watermarkText?: string; version: number }
interface NotificationSettings { inAppEnabled: boolean; emailEnabled: boolean; qualificationReminderDays: number[]; events: Record<string,boolean>; version: number }
interface AgentStatus { name: string; scene: ModelRoute['scene']; status: 'online'|'degraded'|'offline'|'standby'; activeProvider?: string; activeModel?: string; queueDepth: number; lastHeartbeatAt?: IsoDateTime }
interface Notification { id: Id; type: string; title: string; content: string; isRead: boolean; resourceType?: string; resourceId?: Id; createdAt: IsoDateTime }
interface SearchResult { type: 'page'|'bidTask'|'evaluation'|'qualification'|'fragment'; id: string; title: string; subtitle?: string; route: string; score: number }
interface DependencyHealth { status: 'ok'|'degraded'|'down'; dependencies: Array<{name:string;status:'ok'|'down';latencyMs?:number;message?:string}>; checkedAt: IsoDateTime }
```

---

## 8. 唯一端点目录

下表中的名称必须原样进入 OpenAPI。`Page<T>` 表示 `ApiSuccess<T[]>` 加分页 `meta`；`Binary` 表示二进制响应。

### 8.1 认证、用户与权限（M4）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| POST | `/auth/login` | `LoginRequest` | `AuthSession` | 公开 |
| POST | `/auth/refresh` | Cookie | `AuthSession` | Refresh Cookie |
| POST | `/auth/logout` | 无 | `{loggedOut:true}` | 登录用户 |
| GET | `/auth/me` | 无 | `User` | 登录用户 |
| PATCH | `/auth/me` | `UpdateProfileRequest` | `User` | 登录用户 |
| POST | `/auth/password/forgot` | `{email}` | `{accepted:true}` | 公开 |
| POST | `/auth/password/reset` | `{resetToken,newPassword}` | `{reset:true}` | 公开 |
| GET | `/users` | 分页+keyword+role+department+status | `Page<User>` | admin |
| POST | `/users/invitations` | `InviteUserRequest` | `{user:User,invitationExpiresAt}` | admin |
| POST | `/users/{userId}/invitations/resend` | 无 | `{sent:true}` | admin |
| PATCH | `/users/{userId}` | `UpdateUserRequest` | `User` | admin |
| POST | `/users/{userId}/status` | `{status,reason}` | `User` | admin |
| POST | `/users/{userId}/password-reset-email` | 无 | `{sent:true}` | admin |
| GET | `/users/{userId}/projects` | 分页 | `Page<ProjectSummary>` | admin/本人 |
| GET | `/users/{userId}/activity` | 分页+日期 | `Page<AuditEvent>` | admin/本人 |
| GET | `/roles` | 无 | `RoleDefinition[]` | admin |
| GET | `/permissions/matrix` | 无 | `PermissionMatrix` | admin |

### 8.2 投标任务（M5）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| GET | `/bid-tasks/stats` | 当前筛选参数 | `BidTaskStats` | internal |
| GET | `/bid-tasks` | 分页+keyword+status+assigneeId+quickFilter | `Page<BidTask>` | internal |
| GET | `/bid-tasks/board` | 同列表筛选 | `BidBoardColumn[]` | internal |
| POST | `/bid-tasks` | `CreateBidTaskRequest` | `BidTask` | admin/project_lead |
| GET | `/bid-tasks/{taskId}` | 无 | `BidTaskDetail` | assigned/internal |
| PATCH | `/bid-tasks/{taskId}` | `UpdateBidTaskRequest` | `BidTask` | owner/admin |
| POST | `/bid-tasks/{taskId}/clone` | `{projectName}` | `BidTask` | owner/admin |
| POST | `/bid-tasks/{taskId}/archive` | `{reason}` | `BidTask` | owner/admin |
| POST | `/bid-tasks/{taskId}/assignments` | `{userId,roleInTask}` | `TaskAssignment` | owner/admin |
| DELETE | `/bid-tasks/{taskId}/assignments/{userId}` | 无 | 204 | owner/admin |
| PUT | `/bid-tasks/{taskId}/tender-file` | `{fileId}` | `BidTask` | owner/admin |
| POST | `/bid-tasks/{taskId}/parse` | 无 | `JobRef` | owner/member |
| GET | `/bid-tasks/{taskId}/requirements` | 无 | `TenderRequirements` | assigned |
| PATCH | `/bid-tasks/{taskId}/requirements` | `UpdateRequirementsRequest` | `TenderRequirements` | owner/admin |
| GET | `/bid-tasks/{taskId}/materials` | 筛选+分页 | `Page<BidMaterial>` | assigned |
| POST | `/bid-tasks/{taskId}/materials` | `CreateBidMaterialRequest` | `BidMaterial` | owner/member |
| PATCH | `/bid-tasks/{taskId}/materials/{materialId}` | `UpdateBidMaterialRequest` | `BidMaterial` | owner/member |
| DELETE | `/bid-tasks/{taskId}/materials/{materialId}` | 无 | 204 | owner |
| POST | `/bid-tasks/{taskId}/materials/match` | `{materialIds?}` | `JobRef` | owner/member |
| PUT | `/bid-tasks/{taskId}/materials/{materialId}/file` | `{fileId}` | `BidMaterial` | owner/member |
| DELETE | `/bid-tasks/{taskId}/materials/{materialId}/file` | 无 | `BidMaterial` | owner/member |
| POST | `/bid-tasks/{taskId}/materials/batch-bind` | `BatchBindRequest` | `BatchBindResult` | owner/member |
| GET | `/bid-tasks/{taskId}/materials/export` | 当前筛选 | `Binary(xlsx)` | assigned |
| POST | `/bid-tasks/{taskId}/materials/templates` | `{materialIds}` | `JobRef` | assigned |
| POST | `/bid-tasks/{taskId}/reviews` | `CreateBidReviewRequest` | `JobRef` | owner/reviewer |
| GET | `/bid-tasks/{taskId}/reviews/latest` | 无 | `BidReviewReport` | assigned |
| POST | `/bid-tasks/{taskId}/review-findings/{findingId}/decision` | `{decision,comment?}` | `BidReviewFinding` | owner/reviewer |
| POST | `/bid-tasks/{taskId}/documents` | `GenerateBidDocumentRequest` | `JobRef` | owner |
| GET | `/bid-tasks/{taskId}/documents` | 无 | `BidDocument[]` | assigned |
| GET | `/bid-tasks/{taskId}/documents/{documentId}/download` | 无 | `Binary(docx)` | assigned |
| GET | `/bid-tasks/{taskId}/document-versions` | 分页 | `Page<DocumentVersion>` | assigned |
| GET | `/bid-tasks/{taskId}/document-versions/compare` | `fromVersionId,toVersionId` | `DocumentDiff` | assigned |
| POST | `/bid-tasks/{taskId}/document-versions/{versionId}/rollback` | `{reason}` | `JobRef` | owner/admin |

### 8.3 资质与片段库（M5）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| GET | `/qualifications/stats` | 无 | `QualificationStats` | internal |
| GET | `/qualifications` | 分页+keyword+category+status+expiresWithinDays | `Page<Qualification>` | internal |
| POST | `/qualifications` | `CreateQualificationRequest`（含 fileId） | `Qualification` | lead/admin |
| GET | `/qualifications/{id}` | 无 | `Qualification` | internal |
| PATCH | `/qualifications/{id}` | `UpdateQualificationRequest` | `Qualification` | lead/admin |
| POST | `/qualifications/{id}/versions` | `{fileId,documentVersion,changeNote}` | `Qualification` | lead/admin |
| DELETE | `/qualifications/{id}` | `{reason}` | 204 | admin |
| POST | `/qualifications/imports` | `{fileId}` | `JobRef` | lead/admin |
| GET | `/qualifications/import-template` | 无 | `Binary(xlsx)` | internal |
| GET | `/qualifications/{id}/download` | 无 | `Binary` | internal |
| GET | `/fragments/stats` | 无 | `FragmentStats` | internal |
| GET | `/fragments` | 分页+keyword+category+searchMode | `Page<Fragment>` | internal |
| POST | `/fragments/semantic-search` | `{query,category?,limit}` | `Fragment[]` | internal |
| POST | `/fragments` | `CreateFragmentRequest` | `Fragment` | lead/admin |
| GET | `/fragments/{id}` | 无 | `Fragment` | internal |
| PATCH | `/fragments/{id}` | `UpdateFragmentRequest` | `Fragment` | lead/admin |
| POST | `/fragments/{id}/versions` | `{fileId?,content?,changeNote}` | `Fragment` | lead/admin |
| POST | `/fragments/{id}/references` | `{bidTaskId,materialId?}` | `{referenced:true,useCount}` | assigned |
| DELETE | `/fragments/{id}` | `{reason}` | 204 | admin |

### 8.4 评标任务、供应商、报价、评分（M6）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| GET | `/evaluations/stats` | 当前筛选 | `EvaluationStats` | internal |
| GET | `/evaluations` | 分页+keyword+status+assigneeId | `Page<EvaluationTask>` | internal |
| POST | `/evaluations` | `CreateEvaluationDraftRequest` | `EvaluationTask` | admin/project_lead |
| POST | `/evaluations/from-bid-task/{bidTaskId}` | `{copyMaterials:true}` | `EvaluationTaskDetail` | admin/project_lead |
| GET | `/evaluations/{evaluationId}` | 无 | `EvaluationTaskDetail` | assigned |
| PATCH | `/evaluations/{evaluationId}` | `UpdateEvaluationRequest` | `EvaluationTask` | owner/admin |
| PUT | `/evaluations/{evaluationId}/materials` | `{items:EvaluationMaterial[]}` | `EvaluationMaterial[]` | owner/admin |
| PUT | `/evaluations/{evaluationId}/criteria` | `{items:ScoringCriterion[]}` | `ScoringCriterion[]` | owner/admin |
| PUT | `/evaluations/{evaluationId}/review-settings` | `ReviewSettings` | `ReviewSettings` | owner/admin |
| PUT | `/evaluations/{evaluationId}/reviewers` | `{reviewerIds:Id[]}` | `UserSummary[]` | owner/admin |
| PUT | `/evaluations/{evaluationId}/suppliers` | `{items:SupplierInvitationInput[]}` | `Supplier[]` | owner/admin |
| POST | `/evaluations/{evaluationId}/validate` | 无 | `ValidationResult` | owner/admin |
| GET | `/evaluations/{evaluationId}/preview` | 无 | `EvaluationPreview` | owner/admin |
| POST | `/evaluations/{evaluationId}/publish` | 无 | `{evaluation:EvaluationTask,invites:SupplierInviteSummary[]}` | owner/admin |
| POST | `/evaluations/{evaluationId}/cancel` | `{reason}` | `EvaluationTask` | owner/admin |
| GET | `/evaluations/{evaluationId}/suppliers` | 分页+status | `Page<Supplier>` | assigned |
| GET | `/evaluations/{evaluationId}/suppliers/{supplierId}/submissions` | 无 | `SupplierSubmission[]` | assigned |
| GET | `/evaluations/{evaluationId}/supplier-invites` | 无 | `SupplierInviteSummary[]` | owner/admin |
| POST | `/evaluations/{evaluationId}/supplier-invites/{supplierId}/rotate` | `{reason}` | `SupplierInviteSummary` | owner/admin |
| POST | `/evaluations/{evaluationId}/supplier-invites/{supplierId}/revoke` | `{reason}` | `{revoked:true}` | owner/admin |
| POST | `/evaluations/{evaluationId}/supplement-notices` | `CreateSupplementNoticeRequest` | `SupplementNotice` | owner/admin |
| GET | `/evaluations/{evaluationId}/supplement-notices` | 分页 | `Page<SupplementNotice>` | assigned |
| POST | `/evaluations/{evaluationId}/price-rounds` | `CreatePriceRoundRequest` | `PriceRound` | owner/admin |
| GET | `/evaluations/{evaluationId}/price-rounds` | 无 | `PriceRound[]` | assigned |
| POST | `/evaluations/{evaluationId}/price-rounds/{roundId}/close` | 无 | `PriceRound` | owner/admin |
| GET | `/evaluations/{evaluationId}/price-comparison` | 无 | `PriceComparison` | assigned |
| POST | `/evaluations/{evaluationId}/material-checks` | 无 | `JobRef` | owner/reviewer |
| GET | `/evaluations/{evaluationId}/material-checks/latest` | 无 | `MaterialCheckResult` | assigned |
| POST | `/evaluations/{evaluationId}/risk-checks` | 无 | `JobRef` | owner/reviewer |
| GET | `/evaluations/{evaluationId}/risks` | severity+decision+supplierId | `RiskFinding[]` | assigned |
| POST | `/evaluations/{evaluationId}/risks/{riskId}/decision` | `{decision,reason}` | `RiskFinding` | owner/reviewer |
| POST | `/evaluations/{evaluationId}/ai-scoring` | 无 | `JobRef` | owner/reviewer |
| GET | `/evaluations/{evaluationId}/scores` | supplierId+category | `ScoreItem[]` | assigned |
| PATCH | `/evaluations/{evaluationId}/scores/{supplierId}/{criterionId}` | `{humanScore,adjustmentReason}` | `ScoreItem` | reviewer |
| POST | `/evaluations/{evaluationId}/scores/confirm` | `{supplierId?,comment}` | `{confirmed:true}` | reviewer |
| GET | `/evaluations/{evaluationId}/ranking` | 无 | `EvaluationRanking` | assigned |
| POST | `/evaluations/{evaluationId}/reports` | `{formats:['docx','pdf']}` | `JobRef` | owner/reviewer |
| GET | `/evaluations/{evaluationId}/reports` | 无 | `EvaluationReport[]` | assigned |
| GET | `/evaluations/{evaluationId}/reports/{reportId}/download` | 无 | `Binary` | assigned |
| POST | `/evaluations/{evaluationId}/close` | `{resultSummary}` | `EvaluationTask` | owner/admin |

### 8.5 供应商 Portal（M6）

生产 Portal API 不在 URL 中传长期 Token。邀请链接中的 `inviteCode` 只用于交换会话。

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| POST | `/portal/session/exchange` | `{inviteCode}` | `PortalSession` | 有效邀请码 |
| POST | `/portal/session/refresh` | Portal Refresh Cookie | `PortalSession` | Portal |
| POST | `/portal/session/logout` | 无 | `{loggedOut:true}` | Portal |
| GET | `/portal/me` | 无 | `PortalContext` | Portal |
| GET | `/portal/materials` | 无 | `PortalMaterial[]` | Portal |
| PUT | `/portal/materials/{materialId}/file` | `{fileId}` | `PortalMaterial` | Portal，截止前 |
| DELETE | `/portal/materials/{materialId}/file` | 无 | `PortalMaterial` | Portal，截止前 |
| PUT | `/portal/draft` | `{note?,quoteDraft?}` | `PortalDraft` | Portal，截止前 |
| POST | `/portal/submit` | `{confirmed:true}` | `SubmissionReceipt` | Portal，截止前 |
| GET | `/portal/receipt` | 无 | `Binary(pdf)` | Portal |
| GET | `/portal/notices` | 无 | `SupplementNotice[]` | Portal |
| POST | `/portal/notices/{noticeId}/respond` | `{fileBindings:[...]}` | `SupplementNotice` | Portal，通知期限前 |
| GET | `/portal/price-rounds` | 无 | `PortalPriceRound[]` | Portal |
| POST | `/portal/price-rounds/{roundId}/quotes` | `{amount:Money,currency:'CNY'}` | `QuoteSubmission` | Portal，轮次期限前 |
| GET | `/portal/activity` | 分页 | `Page<PortalActivity>` | Portal |

### 8.6 文件、异步任务与实时事件（M4/M7）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| POST | `/files/upload-sessions` | `CreateUploadSessionRequest` | `UploadSession` | internal/Portal |
| GET | `/files/upload-sessions/{uploadId}` | 无 | `UploadSession` | 创建者 |
| PUT | `/files/upload-sessions/{uploadId}/parts/{partNumber}` | 二进制 | `{partNumber,etag}` | 创建者 |
| POST | `/files/upload-sessions/{uploadId}/complete` | `{parts:[{partNumber,etag}]}` | `FileRef` | 创建者 |
| DELETE | `/files/upload-sessions/{uploadId}` | 无 | 204 | 创建者 |
| GET | `/files/{fileId}/preview` | 无 | Binary/短期重定向 | 有资源权限者 |
| GET | `/files/{fileId}/download` | 无 | Binary/短期重定向 | 有资源权限者 |
| GET | `/jobs/{jobId}` | 无 | `JobRef & {result?,error?}` | 发起者/管理员 |
| POST | `/jobs/{jobId}/cancel` | 无 | `JobRef` | 发起者/管理员 |
| POST | `/realtime/tickets` | `{channel:'internal'|'portal'}` | `{ticket,expiresAt}` | 当前会话 |

上传规则：分片 8 MiB；单文件最大 200 MiB；并发最多 4 片；SHA-256 必填；允许格式以业务材料配置为准；扫描未完成时业务状态只能是 `pending`。

### 8.7 通知、设置与审计（M4）

| Method | Path | 请求 | `data` 响应 | 权限 |
|---|---|---|---|---|
| GET | `/notifications` | 分页+unreadOnly+type | `Page<Notification>` | internal |
| PATCH | `/notifications/{id}` | `{isRead:true}` | `Notification` | 本人 |
| POST | `/notifications/read-all` | 无 | `{updatedCount}` | 本人 |
| GET | `/global-search` | `{keyword,limit}` | `SearchResult[]` | internal |
| GET | `/settings/model-providers` | 无 | `ModelProviderMasked[]` | admin |
| POST | `/settings/model-providers` | `CreateModelProviderRequest` | `ModelProviderMasked` | admin |
| PATCH | `/settings/model-providers/{id}` | `UpdateModelProviderRequest` | `ModelProviderMasked` | admin |
| POST | `/settings/model-providers/{id}/test` | 无 | `JobRef` | admin |
| GET | `/settings/model-routes` | 无 | `ModelRoute[]` | admin |
| PUT | `/settings/model-routes` | `{routes:ModelRoute[]}` | `ModelRoute[]` | admin |
| GET | `/settings/generation` | 无 | `GenerationSettings` | admin |
| PUT | `/settings/generation` | `GenerationSettings` | `GenerationSettings` | admin |
| GET | `/settings/deployment` | 无 | `DeploymentSettings` | admin |
| PUT | `/settings/deployment` | `DeploymentSettings` | `DeploymentSettings` | admin |
| GET | `/settings/document-template` | 无 | `DocumentTemplateSettings` | admin |
| PUT | `/settings/document-template` | `DocumentTemplateSettings` | `DocumentTemplateSettings` | admin |
| GET | `/settings/notifications` | 无 | `NotificationSettings` | admin |
| PUT | `/settings/notifications` | `NotificationSettings` | `NotificationSettings` | admin |
| GET | `/settings/agents/status` | 无 | `AgentStatus[]` | admin |
| GET | `/audit-events` | 分页+actor+action+resource+日期 | `Page<AuditEvent>` | admin |
| GET | `/evaluations/{evaluationId}/audit-events` | 同上 | `Page<AuditEvent>` | assigned |
| GET | `/audit-events/export` | 当前筛选 | `Binary(xlsx)` | admin |
| GET | `/health/live` | 无 | `{status:'ok'}` | 公开 |
| GET | `/health/ready` | 无 | `DependencyHealth` | 公开/受限 |

---

## 9. 状态机（后端唯一裁决）

前端不得通过 PATCH 直接修改状态，只能调用动作端点。

### 9.1 投标任务

```text
draft -> parsing -> material_prep -> ai_review -> pending_output -> completed -> archived
draft/parsing/material_prep/ai_review/pending_output -> failed
failed -> parsing | material_prep | ai_review | pending_output（按失败步骤重试）
```

### 9.2 评标任务

```text
draft -> collecting -> pending -> ai_review -> human_review -> completed -> closed
draft -> cancelled
collecting -> cancelled（必须有原因且无正式提交，或走管理员强制流程）
completed -> human_review（仅管理员复开，必须审计）
```

### 9.3 供应商

```text
invited -> partial -> submitted -> supplementing -> submitted
submitted -> qualified | disqualified
invited/partial -> overdue
invited/partial/submitted -> withdrawn
```

所有非法迁移返回 409 `INVALID_STATE_TRANSITION`，响应 details 必须包含 `currentStatus` 和 `allowedActions`。

---

## 10. RBAC 权限矩阵

| 能力 | admin | project_lead | member | reviewer | supplier |
|---|---:|---:|---:|---:|---:|
| 系统/用户/模型配置 | 全部 | 无 | 无 | 无 | 无 |
| 创建投标/评标任务 | 是 | 是 | 否 | 否 | 否 |
| 修改自己负责的任务 | 是 | 是 | 指派范围 | 只读 | 无 |
| 上传投标材料 | 是 | 是 | 指派范围 | 只读 | 无 |
| 发起投标 AI 审核 | 是 | 是 | 否 | 是 | 无 |
| 处理投标审核建议 | 是 | 是 | 否 | 是 | 无 |
| 发布/取消/关闭评标 | 是 | 自己负责 | 否 | 否 | 无 |
| 发送补材料/发起报价 | 是 | 自己负责 | 否 | 否 | 无 |
| AI 评标与人工评分 | 是 | 查看/发起 | 否 | 是 | 无 |
| 确认废标风险 | 是 | 自己负责 | 否 | 是 | 无 |
| Portal 提交/报价 | 无 | 无 | 无 | 无 | 仅自身任务 |
| 审计导出 | 是 | 自己负责 | 否 | 自己参与 | 仅自身活动 |

权限必须同时在路由依赖、Service 查询条件和数据库 tenant 过滤三层执行。

---

## 11. 实时事件契约

连接方式：先调用 `/realtime/tickets`，再连接 `ws://127.0.0.1:8210/api/v1/ws?ticket=<one-time-ticket>`。Ticket 30 秒过期且只能使用一次。

```ts
interface RealtimeEvent<T = unknown> {
  eventId: Id;
  type: RealtimeEventType;
  occurredAt: IsoDateTime;
  aggregateType: 'bidTask'|'evaluation'|'supplier'|'job'|'notification';
  aggregateId: Id;
  data: T;
}

type RealtimeEventType =
  | 'job.progress' | 'job.succeeded' | 'job.failed'
  | 'notification.created'
  | 'bidTask.updated' | 'bidMaterial.updated' | 'bidReview.completed'
  | 'evaluation.updated' | 'supplier.submitted' | 'supplement.created'
  | 'priceRound.opened' | 'priceRound.closed' | 'evaluation.closed';
```

- 事件至少一次投递；客户端按 `eventId` 去重。
- 断线指数退避 1/2/4/8/15 秒，最多 15 秒；重连后通过 REST 重新拉取权威状态。
- WebSocket 仅做通知，不得成为唯一数据源。

---

## 12. AI 与异步任务硬性规范

- 每个 AI 场景都有主模型、降级模型、超时、最大重试、温度、Top P、最大输出 Token 配置。
- 默认降级链：Qwen-Plus -> DeepSeek-V3 -> GLM-4-Plus；连续 3 次失败熔断 10 分钟。
- 提示词版本必须记录 `promptName`、`promptVersion`、`modelProvider`、`modelName`、输入哈希、输出哈希、耗时和 Token 用量。
- 任何 AI 结论必须保留证据位置（文件、页码/段落、原文摘要）和置信度。
- 评分、废标风险、资质疑似伪造必须标明“AI 建议，待人工确认”。
- Celery 任务必须支持幂等、进度、取消、重试、超时、死信记录；同一 Idempotency-Key 不得产生重复业务结果。
- AI 服务全部不可用时，材料清单、人工审核、人工评分、文档手工上传等核心流程仍可继续。

---

## 13. 数据库与迁移规则

- 所有业务表必须有 `id UUIDv7`、`tenant_id`、`created_at`、`updated_at`；可编辑表另有 `version`。
- 所有外键建索引；列表筛选组合按真实查询建复合索引。
- 软删除字段统一 `deleted_at`、`deleted_by`；审计表禁止软删除和硬删除。
- 金额 `NUMERIC(18,2)`；分数 `NUMERIC(8,2)`；权重 `NUMERIC(5,2)`。
- 文件只保存 `file_id` 外键；禁止在业务表重复存完整对象路径。
- 迁移必须可从空库顺序升级；生产迁移禁止自动 downgrade。
- 每个迁移 PR 必须提供升级验证、回滚策略和数据兼容说明。

---

## 14. 测试与验收门禁

### 14.1 工具与覆盖率

- 前端：Vitest + React Testing Library；语句覆盖率 >= 80%，核心状态机适配器 100%。
- 后端：pytest + pytest-asyncio + httpx；语句覆盖率 >= 85%，权限/状态机/金额公式 100%。
- E2E：Playwright；桌面 1440×900、平板 1024×768、移动 390×844。
- 契约：OpenAPI lint + breaking-change 检查 + 生成客户端无 diff。
- 安全：依赖审计、secret scan、文件恶意样本测试、越权测试。

### 14.2 必须通过的 E2E

1. 登录 -> 创建投标 -> 上传招标文件 -> 解析 -> 材料匹配/上传 -> AI 审核 -> 处理建议 -> 生成三份 Word -> 版本比较/回滚。
2. 投标详情 -> 从投标发起评标 -> 草稿恢复 -> 五步校验 -> 发布 -> 每家独立邀请链接。
3. 供应商 A 邀请码不能访问供应商 B；草稿 -> 上传 -> 正式提交 -> 回执 -> 补材料 -> 二轮报价。
4. 评标人完整性检查 -> 风险复核 -> AI 初评 -> 人工调分并填原因 -> 排名 -> Word/PDF 报告 -> 关闭。
5. 普通成员访问系统设置返回 403；停用用户 Token 立即失效；跨租户 ID 返回 404。
6. 截止后上传/报价返回 `DEADLINE_PASSED`；重复提交使用同一 Idempotency-Key 只产生一条记录。
7. 主模型失败自动降级；全部模型失败时 UI 显示可重试和人工流程。
8. 审计日志 UPDATE/DELETE 在数据库层失败，导出内容与筛选结果一致。

### 14.3 UI 验收

- 无浏览器 Console Error、无未处理 Promise、无失败网络请求、无横向溢出。
- 键盘可达、可见焦点、表单 Label、图标按钮 aria-label、颜色对比满足 WCAG AA。
- 删除、发布、关闭、废标、停用、回滚均有明确对象和影响说明的二次确认。
- 所有下载文件可打开且内容正确；禁止下载假文本冒充 Word/PDF/Excel。

---

## 15. 分阶段交付顺序

### Phase 0：契约与骨架

- L0 创建目录、环境、Compose、OpenAPI、CI、数据库基线。
- M3 建唯一前端 Client；M4 建 FastAPI Envelope/错误/RBAC/健康检查。
- 完成标准：空库启动、登录、`/health/ready`、生成客户端通过。

### Phase 1：公共平台和双工作台

- M4 完成认证/用户/文件/通知；M1/M2/M3 接真实列表与状态。
- M5/M6 完成任务 CRUD 和状态机骨架。
- 完成标准：无 Mock 登录，投标/评标/管理列表均来自数据库。

### Phase 2：投标完整闭环

- M1 + M5 + M7 完成七步流程、资源库、审核、Word 与版本。
- 完成标准：投标 E2E 全绿，输出 Word 可打开。

### Phase 3：评标与 Portal 完整闭环

- M2 + M6 + M7 完成六步流程、供应商、报价、评分、报告、审计。
- 完成标准：评标和 Portal E2E 全绿，跨供应商隔离通过。

### Phase 4：系统设置、稳定性与答辩

- M3 + M4 完成全部设置；M7 完成降级和全量 E2E；L0 集成和发布。
- 完成标准：本文所有页面矩阵和验收项都有测试证据，无死按钮。

---

## 16. 禁止事项

- 禁止改变已锁定路由、接口路径、字段名、枚举或端口后只通知口头消息。
- 禁止直接在页面中调用 `fetch`；只能通过唯一 API Client 和生成 SDK。
- 禁止把数据库 ORM 对象直接作为 API 响应。
- 禁止在 UI 或日志打印 Access Token、Portal Token、密码、完整 API Key。
- 禁止把供应商切换器带入生产 Portal。
- 禁止用 `float` 计算金额和评分公式。
- 禁止覆盖文件版本、修改审计日志、物理删除已经参与评标的记录。
- 禁止以“课程 Demo”为理由跳过权限、异常、测试、幂等和数据隔离。
- 禁止在一个 PR 中混入无关格式化、依赖升级或跨成员目录重构。

---

## 17. 给编码 AI 的最终执行指令

```text
你正在开发“一站式智能招投标平台”。PROJECT_MASTER_PROMPT.md 是唯一权威规格。

必须做到：
1. 完成分配模块的所有页面与真实后端能力，不保留 Mock、TODO、空按钮或假下载。
2. 严格复用 OpenAPI 生成类型、统一错误结构、状态枚举、RBAC、幂等与版本控制。
3. 不修改其他成员拥有的文件；共享契约不足时停止并提交 CONTRACT-CHANGE。
4. 每个功能同时实现 loading/empty/error/forbidden、审计、测试和中文反馈。
5. 高风险操作必须二次确认；AI 结论必须有依据且由人工最终裁决。
6. 完成后运行本模块 lint、typecheck、unit、API test 和对应 Playwright E2E。

开始前先输出：成员编号、允许修改的路径、将实现的接口、相关验收项、依赖其他成员的内容。
结束时输出：修改文件、完成接口、测试命令和结果、未决契约提案；若有任何未完成项，不得声称完成。
```
