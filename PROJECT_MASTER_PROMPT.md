# 一站式智能招投标平台：全栈项目总提示词与协作契约 V3.1

> 文档状态：**唯一权威开发提示词（Single Source of Truth）**
> 适用对象：组长 + 7 名组员 + 所有辅助编码 AI
> 基线日期：2026-08-06
> 前端基线：当前 `demo/` 目录中的 React Demo
> 旧文档关系：`PRD.md`、`ARCHITECTURE.md`、`DESIGN.md`、`SPEC.md` 仅作背景材料；与本文冲突时，**无条件以本文为准**。
> V3.1 重点：把 L0 与 M1-M7 的功能、目录、接口、交付物和禁止修改范围落实到唯一责任人，并增加低冲突合并流程。

---

## 0. 如何使用本提示词

每一名成员开始编码前，必须把本文完整提供给自己的编码 AI，并追加一句：

```text
我是成员 Mx，只实现本文“人员分工”中分配给 Mx 的模块。先读取接口契约、状态机、目录所有权和验收标准，再输出本次实施计划。不得修改未分配目录，不得自行新增或更名接口；若契约不足，先提交 CONTRACT-CHANGE；若需要公共文件、公共组件或依赖，先提交 BOUNDARY-CHANGE/DEPENDENCY-CHANGE，等待唯一所有者的前置 PR 合并后再编码。
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

| 路由/区域 | 前端 DRI | 后端 DRI | 必须完整实现的交互 |
|---|---|---|---|
| `/login` | M3 | M4 | 登录、密码可见性、表单校验、忘记密码、会话刷新、退出后失效 |
| 全局布局 | M3 | M4 | 投标/评标切换、响应式侧栏、Ctrl/Cmd+K 全局搜索、通知已读、账号菜单、退出 |
| `/dashboard` | M1 | M5 | 统计下钻、关键词/负责人/状态/我的/临期/风险筛选、重置、CSV 导出、表格/看板、复制任务、归档、发起评标 |
| `/tasks/create` | M1 | M5 | 项目信息、招标文件续传、格式校验、解析进度、解析失败重试、解析结果确认、创建任务 |
| `/tasks/:id` | M1 | M5 | 七步进度、关联评标、材料 CRUD/上传/模板/导出、AI 审核及建议动作、Word 生成、版本下载/比较/回滚、招标要求查看 |
| `/admin/qualifications` | M3 | M5 | 搜索/分类/状态筛选、动态有效期、来源/发证机构/版本、上传/编辑/更新/预览/下载、批量导入、30/60/90 天提醒 |
| `/admin/fragments` | M3 | M5 | 关键词/语义搜索、分类、匹配度与理由、来源/版本、上传/编辑/预览/引用、版本历史、引用统计 |
| `/admin/users` | M3 | M4 | 搜索、角色/部门/状态筛选、邀请/编辑、项目下钻、密码重置邮件、启停确认、活动日志、RBAC 矩阵 |
| `/admin/settings` | M3 | M4 | 模型服务商、脱敏密钥更新、连接测试、场景路由、生成参数、智能体状态、部署/存储、备份、文档模板、通知事件、操作日志导出 |
| `/evaluation` | M2 | M6 | 统计下钻、搜索/负责人/状态筛选、表格/看板、相对截止时间、风险明细、创建任务、外部门户入口 |
| `/evaluation/create` | M2 | M6 | 投标项目导入、五步向导、自动/手动草稿、恢复、日期关系校验、材料/权重/供应商/评审人校验、发布预览、发布确认 |
| `/evaluation/:id` | M2 | M6 | 六步进度、供应商提交、独立邀请链接、补材料通知、多轮报价、资格审查、废标人工确认、技术/商务人工复审、综合排名、报告、关闭、审计导出 |
| `/evaluation/portal/:inviteCode` | M2 | M6 | 邀请码交换、供应商锁定、项目与倒计时、材料草稿/上传/替换/正式提交/回执、补材料、多轮报价、提交记录、结束页 |

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

## 5. 八人小组任务拆分（功能板块与唯一所有权）

### 5.1 固定成员编号与责任总览

成员编号在项目周期内不得交换。每项需求只能有一个最终责任人（DRI）；“协助”不等于可以直接修改对方目录。组员跨板块协作必须通过第 5.4 节定义的接口或交付物完成。

| 编号 | 功能板块 | 必须交付的业务终态 | 独占实现范围 | 主要联调对象 |
|---|---|---|---|---|
| L0 | 组长、架构与集成 | 契约、环境、CI、迁移、生成代码、集成发布全部可复现 | 根配置、`contracts/`、`infra/`、`scripts/`、CI、中央注册文件、迁移版本 | 全员 |
| M1 | 投标中心前端 | 投标工作台和七步投标闭环全部可操作 | 投标三个页面、`demo/src/features/bids/` | M5、M3、M4、M7 |
| M2 | 评标中心与供应商门户前端 | 评标六步闭环和外部门户全部可操作 | 评标四个页面、`demo/src/features/evaluations/`、`portal/` | M6、M3、M4、M7 |
| M3 | 公共、管理端与资源库前端 | 登录、布局、搜索、通知、资质、片段、用户、设置完整 | 前端应用壳、公共组件、唯一 API 包装、管理与资源库页面 | M4、M5、M1、M2 |
| M4 | 公共平台后端 | 认证、RBAC、文件、任务元数据、通知、设置、审计、健康检查完整 | `core` 及平台公共领域 | M3、M5、M6、M7 |
| M5 | 投标与资源库后端 | 投标任务、材料、审核编排、文档版本、资质和片段接口完整 | `bids`、`qualifications`、`fragments`、`documents` | M1、M4、M7、M6 |
| M6 | 评标与门户后端 | 评标、供应商、补材料、报价、评分、排名、报告、关闭完整 | `evaluations`、`portal`、`pricing`、`scoring` | M2、M4、M7、M5 |
| M7 | AI、异步执行与质量 | AI 工作流、队列执行、降级、质量评估和跨域 E2E 完整 | `ai`、`workers`、`e2e` | M4、M5、M6、M1、M2、M3 |

### 5.2 每人功能任务卡

#### L0 组长：架构、契约、环境与发布

**负责功能**：

- 固化目录骨架、运行环境、Compose、数据库基线、CI、演示种子和一键启动脚本。
- 维护本文、`contracts/openapi.yaml`、事件 Schema、接口示例和所有错误码/枚举；口头约定无效。
- 根据锁定契约生成前端 SDK 和后端契约模型，确保生成结果来自同一个契约提交。
- 审核并生成 Alembic 单一迁移链；维护 `main`、`develop`、版本标签、发布说明和答辩脚本。
- 定义固定聚合协议：M3 建立前端路由聚合器；L0 建立后端 Router 聚合器和模型注册器。成员只导出自己的领域模块，禁止多人反复编辑中央文件。

**独占文件**：

- `PROJECT_MASTER_PROMPT.md`、`contracts/**`、`infra/**`、`scripts/**`、`.github/**`。
- `.env.example`、`.nvmrc`、`.python-version`、根目录工程配置。
- `demo/package.json`、`demo/package-lock.json`、Vite/TypeScript/Tailwind/PostCSS 配置。
- `backend/pyproject.toml`、`uv.lock`、`alembic.ini`、`backend/migrations/versions/**`。
- `backend/app/main.py`、`backend/app/api/v1/router.py`、中央模型注册文件。
- `demo/src/api/generated/**`、`backend/app/contracts/generated/**` 等全部生成代码。

**不得代替成员完成**：不得在没有契约变更记录的情况下临时增加接口，也不得直接接管 M1-M7 的领域文件来“快速修复”。需要跨域修复时指定领域所有者提交 PR。

**验收**：从空数据库执行一次命令即可启动；契约检查、单迁移头、全量 CI 和关键 E2E 全绿；`main` 始终可演示。

#### M1：投标中心前端

**负责路由**：`/dashboard`、`/tasks/create`、`/tasks/:id`。

**负责功能**：

- 投标工作台：统计卡片下钻、列表/看板切换、关键字与组合筛选、分页、负责人筛选、CSV 导出、任务进入、克隆、归档和发起评标入口。
- 新建投标：项目信息校验、招标文件上传/续传、文件类型与大小提示、草稿保存、创建成功跳转。
- 投标七步详情：文件解析进度、需求确认、材料清单 CRUD、资质/片段匹配、文件绑定、批量处理、AI 审核、人工处理意见、文档生成、下载、版本比较和回滚。
- 展示所有 Loading、Empty、Error、Forbidden、超时、任务失败、版本冲突和操作确认状态；不得只实现成功路径。

**独占文件**：`Dashboard.tsx`、`BidCreate.tsx`、`TaskDetail.tsx`、`demo/src/features/bids/**` 及其中的组件、hooks、适配器、领域测试和 fixtures。

**接口边界**：只通过生成 SDK 消费第 8.2 节投标接口、第 8.3 节只读资源库接口及第 8.6 节文件/任务/实时接口。需要新增字段时向 L0 提交契约变更，不得在页面内手写临时 DTO 或直接 `fetch`。

**交付与验收**：投标组件/集成测试由 M1 编写；向 M7 提供投标主流程、失败流和权限流验收清单。M5 的契约测试通过后，M1 的页面不得再依赖业务 Mock。

**禁止修改**：评标页面、公共布局、`App.tsx`、全局 CSS、公共 API Client、生成 SDK、依赖清单。

#### M2：评标中心与供应商门户前端

**负责路由**：`/evaluation`、`/evaluation/create`、`/evaluation/:id`、`/evaluation/portal/:inviteCode`。

**负责功能**：

- 评标工作台：统计、筛选、列表、任务进入、供应商链接入口和从投标项目导入。
- 创建评标：草稿、投标数据导入、材料配置、评分标准、评审设置、评委、供应商、五项发布前校验、预览和发布结果。
- 评标六步详情：供应商材料、补材料通知、多轮报价、价格对比、资格/完整性检查、废标风险人工确认、AI/人工评分、排名、报告、关闭和审计轨迹。
- 供应商 Portal：邀请码交换会话、身份锁定、材料草稿、正式提交与回执、补材料、报价、通知、过期/撤销/关闭/无权限独立页面。
- Portal 与内部系统必须使用不同会话；页面不得在 URL、日志或本地存储中暴露长期 Token。

**独占文件**：四个评标/Portal 页面、`demo/src/features/evaluations/**`、`demo/src/features/portal/**` 及其中的组件、hooks、适配器、领域测试和 fixtures。

**接口边界**：只消费第 8.4、8.5 节接口及第 8.6 节文件/任务/实时接口。不得直接读取投标前端状态；从投标创建评标只能调用 M6 提供的接口。

**交付与验收**：评标与 Portal 组件/集成测试由 M2 编写；向 M7 提供内部评标、供应商提交、链接失效和截止时间四类验收清单。M6 契约测试通过后不得依赖业务 Mock。

**禁止修改**：投标页面、公共布局、内部认证实现、生成 SDK、依赖清单和后端 Portal Token 逻辑。

#### M3：公共前端、管理端与资源库前端

**负责路由**：登录页、`/admin/qualifications`、`/admin/fragments`、`/admin/users`、`/admin/settings`，以及全局 404/403/500 页面。

**负责功能**：

- 应用壳：认证恢复、路由守卫、MainLayout、菜单、面包屑、用户菜单、全局搜索、通知中心、响应式和错误边界。
- 唯一前端网络层：Base URL、Token 刷新、Request ID、错误码映射、取消请求、版本冲突处理；业务页面只能调用该包装后的生成 SDK。
- 公共组件：Loading、Empty、Error、Forbidden、Confirm、Upload、FilePreview、JobProgress、PermissionGate、分页与筛选容器。
- 资质库：增删改查、来源、状态、有效期、到期提醒、文件下载、导入模板、版本记录。
- 片段库：增删改查、语义搜索、分类、来源、版本、引用记录和使用次数。
- 用户与权限：邀请、重发、启停、角色矩阵、项目记录、活动记录和密码重置邮件。
- 系统设置：模型服务商、场景路由、生成参数、部署、文档模板、通知、智能体状态、连接测试和未保存状态。

**独占文件**：`App.tsx`、`main.tsx`、`MainLayout.tsx`、`Login.tsx`、四个管理/资源库页面、`demo/src/app/**`、`demo/src/layouts/**`、`demo/src/components/common/**`、`demo/src/api/client.ts`、`demo/src/api/interceptors.ts`、`demo/src/features/admin/**`、`demo/src/features/libraries/**`、`demo/src/index.css`。

**低冲突路由规则**：M3 在 Phase 0 一次性让 `App.tsx` 聚合 `bidRoutes`、`evaluationRoutes`、`adminRoutes`。之后 M1/M2 只改各自 `features/*/routes.tsx`，不再修改 `App.tsx`；导航项同理通过各领域 `navigation.ts` 导出。

**接口边界**：消费第 8.1、8.3、8.7 节和第 8.6 节公共接口。资质/片段后端问题交给 M5，其余公共平台问题交给 M4。

**交付与验收**：公共组件测试、网络错误状态测试、管理端集成测试和无障碍扫描由 M3 编写；M1/M2 提出公共组件需求时，M3 先以独立 PR 交付公共组件。

**禁止修改**：投标/评标领域组件、生成 SDK、OpenAPI、依赖清单和后端代码。

#### M4：公共平台后端

**负责领域**：`auth`、`users`、`files`、`jobs`、`notifications`、`settings`、`audit`、`search`、`health` 及 `backend/app/core/**`。

**负责功能**：

- 内部认证：登录、Access/Refresh Token 轮换、退出、个人资料、忘记/重置密码、租户隔离、RBAC 和资源级鉴权依赖。
- 用户平台：邀请、重发、启停、角色/权限、项目与活动查询。
- 文件平台：上传会话、分片、合并、SHA-256、病毒扫描、MinIO、预览/下载签名地址和资源访问控制。
- 异步任务平台：`Job` 元数据、状态查询、取消、进度持久化和一次性 WebSocket Ticket；M4 不实现具体 AI 算法。
- 通知、全局搜索、设置、密钥加密、模型连接测试入口、全局审计、健康与依赖检查。

**独占文件**：`backend/app/core/**`、上述平台领域目录及对应的后端单元/接口测试。中央 `main.py` 和总 Router 仍归 L0。

**必须提供的端口（代码接口）**：`AuthContext`、`FileService`、`JobService/JobDispatcher`、`NotificationService`、`AuditService`、`SettingsService`。M5/M6/M7 只能经这些端口使用平台能力，不得直连 MinIO、Redis、SMTP 或密钥表。

**接口边界**：负责第 8.1、8.6、8.7 节 HTTP 接口和 OpenAPI 实现；M7 只实现 Job 后面的 Worker 执行器与 Provider 适配器。

**交付与验收**：平台领域单元/接口/权限/租户隔离测试；文件越权、Refresh 重放、任务取消、密钥脱敏和健康降级必须有失败流测试。

**禁止修改**：投标/评标业务表和规则、AI 工作流、中央 Router、迁移版本文件、契约文件。

#### M5：投标与资源库后端

**负责领域**：`bids`、`qualifications`、`fragments`、`documents`。

**负责功能**：

- 投标任务：CRUD、筛选/统计/看板、分配、克隆、归档、招标文件绑定和第 9.1 节状态机。
- 招标解析结果与需求确认、材料清单 CRUD、资源库匹配、文件绑定、批量绑定、模板和导出。
- 投标审核任务编排、审核结果/人工决定、Word 生成任务编排、文档元数据、版本哈希、比较和“回滚为新版本”。技术标必须校验并保留给定的章节格式、段落目标和图片锚点，禁止把大文档作为一次自由文本调用。
- 资质库和片段库完整 CRUD、导入/导出、版本、来源、有效期、语义搜索入口和引用记录。
- 向 M6 提供只读 `BidTaskSnapshotPort`，用于“从投标创建评标”；M6 不得直接查询投标 ORM 表。

**独占文件**：四个投标/资源库领域目录、领域模型、repository、service、router 和对应后端单元/接口测试。

**接口边界**：负责第 8.2、8.3 节实现。文件操作调用 M4 `FileService`；解析、匹配、审核和生成通过 M4 `JobDispatcher` 调度 M7；不得在请求线程直接调用模型。

**交付与验收**：每个状态迁移、幂等动作、版本冲突、越权和异步失败均有测试；接口返回必须与生成契约完全一致。

**禁止修改**：评标 ORM/服务、公共平台实现、AI Provider、迁移版本、OpenAPI 和前端文件。

#### M6：评标与供应商门户后端

**负责领域**：`evaluations`、`portal`、`pricing`、`scoring`。

**负责功能**：

- 评标草稿、从投标快照导入、材料/标准/设置/评委/供应商配置、验证、预览、发布、取消和第 9.2 节状态机。
- 供应商邀请：短期交换码、会话刷新、撤销、轮换、身份隔离、截止时间和防重放。
- Portal 材料草稿/删除/正式提交/回执、补材料通知与响应、多轮报价和价格比较。
- 材料完整性、废标风险任务编排与人工决定、AI/人工评分、确认、排名、报告元数据、关闭和评标域审计事件。
- 只通过 M5 `BidTaskSnapshotPort` 获取投标快照；只通过 M4 平台端口处理文件、通知、任务和审计。

**独占文件**：四个评标/Portal 领域目录、领域模型、repository、service、router 和对应后端单元/接口测试。

**接口边界**：负责第 8.4、8.5 节实现。AI 检查、评分和报告通过 `JobDispatcher` 调度 M7；正式提交、报价、发布、关闭必须幂等。

**交付与验收**：跨供应商数据隔离、截止边界、邀请码重放、重复提交、Decimal 金额、人工改分留痕和 append-only 审计必须有测试。

**禁止修改**：投标 ORM/服务、内部认证、公共文件实现、AI Provider、迁移版本、OpenAPI 和前端文件。

#### M7：AI、Worker 与跨域质量

**负责功能**：

- LangGraph 工作流：招标解析、需求提取、材料生成、语义匹配、四类投标审核、材料完整性、废标风险、AI 评分和评标报告。技术标生成必须先锁定格式大纲，再按章节、按段落逐次调用模型；每次调用只携带受控窗口、必要前文和图片说明，最终返回可验证的结构化段落与图片锚点。
- Provider 适配：阿里云百炼、DeepSeek、智谱 AI、Fake Provider、路由、超时、重试、熔断、降级、Token/费用/延迟指标；密钥只从 M4 `SettingsService` 获取脱敏后的运行凭据句柄。
- Celery Worker：任务注册、进度、取消、重试、幂等、死信/人工处理；通过 M4 `JobService` 报告状态。
- Pydantic 结构化输出校验、提示词版本、离线固定样本、质量指标和回归评估。
- Playwright E2E：投标、评标、Portal、管理端主流程和关键错误流；M7 是 `e2e/**` 唯一编辑人。

**独占文件**：`backend/app/ai/**`、`backend/app/workers/**`、`backend/tests/ai/**`、`e2e/**` 及 AI 固定样本。

**回写边界**：M7 不直接写任何业务表，不导入 M5/M6 repository。Worker 输出经已锁定的 `JobResult` Schema 返回，由 M5/M6 的领域 service 校验业务状态后落库。

**交付与验收**：Fake Provider 下 CI 结果确定；结构校验失败、Provider 超时、重试耗尽、取消和降级均有测试；真实 Key 仅用于手工受控测试且不得进入日志或仓库。

**禁止修改**：HTTP 业务 Router、投标/评标业务表、平台密钥存储、前端业务实现、迁移版本和 OpenAPI。

### 5.3 目录与文件唯一所有权表

| 路径或文件类型 | 唯一编辑人 | 其他成员的使用方式 |
|---|---|---|
| `contracts/**`、`PROJECT_MASTER_PROMPT.md` | L0 | 提 Issue/PR 建议，不直接修改 |
| 根环境、Compose、CI、脚本、依赖清单及所有 lock 文件 | L0 | 提 `DEPENDENCY-CHANGE` 或 `ENV-CHANGE` 请求 |
| 前后端生成代码 | L0 | 只导入使用，禁止手改 |
| Alembic `versions/**`、中央 Router/模型注册器 | L0 | 提迁移说明或导出领域 Router |
| `App.tsx`、布局、公共组件、全局样式、唯一 API 包装 | M3 | M1/M2 通过导出 API 使用 |
| 投标页面与 `features/bids/**` | M1 | 其他人只通过路由和公开组件使用 |
| 评标/Portal 页面与对应 features | M2 | 其他人只通过路由和公开组件使用 |
| `backend/app/core/**` 与平台公共领域 | M4 | M5/M6/M7 通过 Protocol/Service 端口调用 |
| 投标、资质、片段、文档领域 | M5 | M1 调 HTTP；M6 调 `BidTaskSnapshotPort` |
| 评标、Portal、报价、评分领域 | M6 | M2 调 HTTP；其他后端通过明确端口调用 |
| AI、Worker、跨域 E2E | M7 | 领域后端通过 Job Schema 调用；组员提交验收清单 |
| `demo/src/mock/**` 旧公共 Mock | M3 | Phase 1 后删除；领域临时 fixture 放各自目录 |

同一文件始终只有一个所有者。即使只是“一行修改”，非所有者也不得顺手提交；应由所有者先合并独立前置 PR，消费者随后更新自己的分支。

### 5.4 跨成员交付接口

| 提供者 | 稳定交付物 | 使用者 | 禁止的替代做法 |
|---|---|---|---|
| L0 | OpenAPI、事件 Schema、生成 SDK、环境与迁移 | 全员 | 群聊口头字段、手写重复 DTO |
| M3 | 公共组件、路由壳、API Client、错误映射 | M1/M2 | 各页面复制 Upload/JobProgress 或自己刷新 Token |
| M4 | Auth/File/Job/Notification/Audit/Settings 服务端口 | M5/M6/M7 | 业务域直连基础设施或复制鉴权代码 |
| M5 | 投标 HTTP API、`BidTaskSnapshotPort`、AI 任务输入 Schema | M1/M6/M7 | 跨域直接查询投标表 |
| M6 | 评标/Portal HTTP API、AI 任务输入 Schema | M2/M7 | 前端直接拼接状态或绕过 Portal 会话 |
| M7 | Worker 任务名、结构化 Job 结果、E2E 证据 | M4/M5/M6/L0 | Worker 直接写业务表或业务域解析自由文本 |
| M1/M2/M3 | 页面验收清单和稳定选择器 `data-testid` | M7 | 多人同时编辑同一个 E2E 文件 |

默认结对审查关系：M1↔M5、M2↔M6、M3↔M4；M7 审查所有异步/AI/E2E 变更；L0 审查契约、共享文件、迁移、环境和跨域变更。

### 5.5 跨边界变更申请

1. 发起 `BOUNDARY-CHANGE` Issue，写清业务原因、目标文件、当前所有者、接口变化、受影响成员和回滚方式。
2. 文件所有者决定是否接受；接受后由所有者创建独立前置 PR，禁止把共享修改混在调用方业务 PR 中。
3. 前置 PR 合入 `develop` 后，调用方同步 `develop`，再只修改自己的领域文件。
4. 紧急情况下仍不得多人共同编辑；L0 可以临时重新指定唯一所有者，并在 Issue 和 PR 中留下书面记录。
5. 未经所有者和 L0 同意的越界文件会在 PR 审查中直接退回，不通过“先合并再修复”。

---

## 6. Git 与低冲突合并流程

### 6.1 分支模型

- `main`：始终可演示，只接收 L0 从 `develop` 发起的阶段发布 PR。
- `develop`：唯一集成分支，只接收通过门禁的成员 PR；任何人不得直接 push。
- 功能分支必须从最新 `origin/develop` 创建，不得从另一名成员的功能分支继续开发。
- 一项工作一个短分支、一个 PR，目标在 1-2 个工作日内合并，避免长期分支积累大量冲突。
- 分支命名：
  - `feat/m1-bid-web-<issue>-<short-name>`
  - `feat/m2-eval-web-<issue>-<short-name>`
  - `feat/m3-platform-web-<issue>-<short-name>`
  - `feat/m4-platform-api-<issue>-<short-name>`
  - `feat/m5-bid-api-<issue>-<short-name>`
  - `feat/m6-eval-api-<issue>-<short-name>`
  - `feat/m7-ai-qa-<issue>-<short-name>`
  - 修复：`fix/mX-<issue>-<short-name>`；契约提案：`contract/<issue>-<short-name>`。
  - L0 文档/流程：`docs/l0-<short-name>`；L0 环境/集成：`chore/l0-<short-name>`。
- Commit 使用 Conventional Commits，并带领域：`feat(bid): ...`、`fix(portal): ...`、`test(e2e): ...`、`docs(contract): ...`。

### 6.2 开始开发与同步基线

创建分支前执行：

```bash
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feat/mX-domain-issue-short-name
```

提交 PR 前必须把最新 `develop` 合入自己的分支并在本地解决冲突：

```bash
git fetch origin
git switch <自己的功能分支>
git merge origin/develop
```

- 只能解决自己独占目录中的冲突。如果冲突出现在共享/他人文件，立即执行 `git merge --abort`，把冲突文件清单发给文件所有者和 L0，由唯一所有者准备前置修复 PR。
- 禁止对 `main`、`develop` 使用 force push；本流程不要求成员 rebase 已公开分支，避免误覆盖他人提交。
- 每天开始工作先同步一次；发现基线已变更时先同步再继续，禁止在旧契约上连续开发数日。

### 6.3 PR 原子性、大小和审查人

- 一个 PR 只完成一个可描述、可测试、可回滚的功能，不混入无关格式化、依赖升级、文件移动或跨领域重构。
- 普通 PR 建议不超过 15 个手写文件或 500 行手写差异；超过时必须拆成前置基础 PR 与业务 PR，或由 L0 在 PR 中批准例外。
- PR 描述必须列出：Issue、责任成员、功能范围、修改路径、接口版本/提交 SHA、数据库影响、测试命令、截图或接口证据、回滚方式。
- 作者先执行 `git diff --name-only origin/develop...HEAD`，确认所有文件都在自己的独占范围；越界文件必须拆出。
- 默认审查人：M1↔M5、M2↔M6、M3↔M4；异步/AI 由 M7 审查；共享/契约/迁移/环境由 L0 审查。
- PR 合并方式固定为 Squash merge；标题必须能直接作为发布日志。合并后删除功能分支，下一项任务重新从 `develop` 建分支。

### 6.4 接口契约变更顺序

任何接口路径、方法、字段、枚举、状态、错误码或事件变化都必须按以下顺序执行，禁止前后端并行猜字段：

1. 责任人创建 `CONTRACT-CHANGE` Issue，写出旧结构、新结构、兼容性、使用页面、后端领域和迁移策略。
2. L0 修改 `contracts/openapi.yaml`、事件 Schema、示例、本文第 7-11 节和契约测试；其他成员不直接编辑。
3. 契约 PR 单独合入 `develop`，L0 在独立提交中重新生成前端 SDK 与后端契约模型。
4. 后端所有者在新契约上实现并通过 API/契约测试；不允许先返回临时字段。
5. 前端所有者同步 `develop` 后接入生成 SDK；不得保留重复手写 DTO。
6. M7 最后补齐 E2E/错误流，L0 验证 OpenAPI 无破坏性漂移后关闭 Issue。

兼容规则：能新增可选字段时不得直接重命名/删除旧字段；确需破坏性变更时使用新端点或明确的版本迁移窗口。群聊截图、口头说明和前端 TypeScript 类型都不是契约来源。

### 6.5 依赖、锁文件与生成代码

- 只有 L0 可以修改 `package.json`、`package-lock.json`、`pyproject.toml`、`uv.lock` 及构建工具配置。
- 成员需要依赖时创建 `DEPENDENCY-CHANGE` Issue，说明用途、现有替代方案、许可证、体积和安全影响；L0 用独立 PR 安装并更新锁文件。
- 禁止成员删除锁文件、改用另一包管理器、手工合并 lock 冲突或把个人环境解析出的锁文件带入业务 PR。
- 只有 L0 可以运行契约代码生成并提交 `generated/**`。生成文件冲突时不手工选 `ours/theirs`；L0 以已合并契约重新生成。
- 禁止提交 `node_modules/`、`dist/`、`.venv/`、真实 `.env`、上传文件、数据库卷、IDE 缓存和本机绝对路径配置。

### 6.6 数据模型与 Alembic 迁移

- M4/M5/M6 只修改自己领域内的 ORM 模型；同一张表只能归一个领域所有者，其他领域通过 ID 和 service port 访问。
- 后端成员在业务 PR 描述中提交 `MIGRATION-NOTE`：表/列/索引变化、数据回填、兼容期、upgrade、downgrade 和数据风险，但不得提交 `versions/**`。
- L0 按 M4→M5→M6 的合并队列顺序接收模型变化，每合并一组后从最新 `develop` 生成一个迁移 PR。
- CI 必须验证 `alembic heads` 只有一个 head，并执行空库 `upgrade head` 及 `upgrade -> downgrade -> upgrade` 循环。
- 禁止成员自行重编号 revision、修改已进入 `develop` 的历史迁移、创建 merge revision 掩盖双 head，或跨领域顺手改表。

### 6.7 中央注册文件与公共代码

- 前端 `App.tsx` 只由 M3 编辑。M1/M2/M3 分别导出 `bidRoutes`、`evaluationRoutes`、`adminRoutes` 与各自 `navigation`，中央聚合器在 Phase 0 固定导入，后续新增领域页面不改中央文件。
- 后端每个领域在自身目录导出 `router`；`backend/app/api/v1/router.py` 只由 L0 维护固定 `include_router`，成员不得在中央 Router 中处理业务。
- ORM 模型由各领域导出，中央模型注册器只由 L0 维护；禁止用跨目录 import 的副作用临时注册模型。
- 公共前端组件和 API 包装只由 M3 实现；业务成员先提需求，公共 PR 合并后再引用，禁止复制一份稍作修改。
- 公共后端能力只由 M4 通过 Protocol/Service 端口提供；领域成员不得复制认证、文件、通知、审计、Job 状态代码。

### 6.8 冲突归属与处理矩阵

| 冲突位置 | 唯一处理人 | 处理规则 |
|---|---|---|
| M1/M2/M4/M5/M6 各自领域文件 | 对应领域所有者 | 所有者根据双方功能意图整合并补测试 |
| `App.tsx`、布局、公共组件、API Client、全局样式 | M3 | 业务成员说明调用需求，M3 提交解决方案 |
| OpenAPI、事件 Schema、生成代码、环境、依赖与 lock | L0 | 以权威契约/锁定版本重新生成，不手工拼接 |
| 中央 Router、模型注册器、Alembic revision | L0 | 按合并队列在最新 `develop` 上重新生成或注册 |
| 平台后端端口 | M4 | 保持向后兼容；确需变更走 CONTRACT/BOUNDARY 流程 |
| AI Workflow、Worker 注册、E2E | M7 | 先确认 Job Schema，再整合任务名和测试选择器 |
| 不属于任何现有目录的新跨域文件 | L0 指定一名所有者 | 指定前不得创建并并行开发 |

解决冲突时禁止简单选择整文件 `ours` 或 `theirs`，必须逐段核对两个功能是否都保留，并重新运行受影响单元测试、契约测试和 E2E。

### 6.9 固定合并队列与安全并行范围

同一功能纵向切片按以下顺序进入 `develop`：

1. L0：契约、环境或目录骨架。
2. M3/M4：所需公共前端组件与公共平台端口。
3. M5/M6：领域后端实现及领域测试。
4. M7：AI/Worker 实现和 Job 结果验证。
5. M1/M2/M3：使用稳定接口的页面功能。
6. M7：跨端 E2E 与错误流。
7. L0：阶段集成、回归和 `main` 发布。

允许的并行：M1 与 M5、M2 与 M6 可以在契约已合并后分别开发；前端先使用契约示例编写组件测试，但在 Phase 验收前必须接入真实 API。禁止的并行：多人同时改公共组件、契约、锁文件、迁移、中央 Router 或生成代码。

### 6.10 合并门禁清单

每个 PR 在合并前必须同时满足：

- [ ] 修改文件全部属于作者独占范围，或附有已批准的 `BOUNDARY-CHANGE`。
- [ ] 已同步最新 `origin/develop`，工作区干净且不存在未解决冲突。
- [ ] format、lint、typecheck、unit、API test 均通过。
- [ ] 契约变更通过 OpenAPI breaking check，且生成代码由 L0 更新。
- [ ] 模型变更附 `MIGRATION-NOTE`，迁移检查只有一个 head。
- [ ] 关键 E2E、权限/错误状态和回归测试按风险通过。
- [ ] 无真实密钥、个人数据、环境文件、构建产物或超大无关文件。
- [ ] PR 没有无关格式化、依赖升级或他人领域代码。
- [ ] 配对审查人和必要的 L0/M7 审查均已批准。

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
type RealtimeChannel = 'internal' | 'portal';
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

### 8.1 认证、用户与权限（后端 M4；前端 M3）

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

### 8.2 投标任务（后端 M5；前端 M1）

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

### 8.3 资质与片段库（后端 M5；前端 M3）

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

### 8.4 评标任务、供应商、报价、评分（后端 M6；前端 M2）

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

### 8.5 供应商 Portal（后端 M6；前端 M2）

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

### 8.6 文件、异步任务与实时事件（HTTP/状态 M4；Worker M7；前端 M1/M2/M3）

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
| POST | `/realtime/tickets` | `{channel:RealtimeChannel}` | `{ticket,expiresAt}` | 当前会话 |

上传规则：分片 8 MiB；单文件最大 200 MiB；并发最多 4 片；SHA-256 必填；允许格式以业务材料配置为准；扫描未完成时业务状态只能是 `pending`。

### 8.7 通知、设置与审计（后端 M4；前端 M3；模型运行时 M7）

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
- 技术标长文档禁止单次整篇生成：必须使用 `paragraph_by_paragraph` 策略，先校验唯一章节 `key` 与顺序，再逐段生成；每段记录独立 PromptVersion、输入/输出哈希、Token、耗时和重试状态。
- 技术标每次模型调用的上下文必须受 `contextWindowCharacters` 限制，只携带项目事实、当前章节指令、最近 `carryForwardParagraphs` 段和必要证据摘要；不得无限累积全文。
- 图片只能通过已扫描的 `fileId` 引用，并绑定 `sectionKey` 与确定的插入位置；模型接收图片说明或受控签名地址，Word 组装器按锚点插入真实图片并保留标题、替代文本和来源。
- 模型输出必须先通过结构校验、章节/段落计数校验和事实字段校验，再进入 Word 组装与版本落库；失败时保留已完成段落，允许从最后成功段落恢复。

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

- L0：创建目录、环境、Compose、OpenAPI、生成代码、CI、数据库基线、后端中央 Router 和模型注册器。
- M3：只在公共前端目录建立应用壳、唯一 API Client、公共状态组件和三组路由聚合接口。
- M4：只在平台后端目录建立 FastAPI Envelope、错误、鉴权依赖、数据库会话和健康检查。
- M5/M6：在各自领域目录建立 model/repository/service/router 空骨架和领域测试目录，不改中央 Router。
- M1/M2：在各自 feature 目录拆分页面组件、定义 UI 状态和基于契约示例的组件测试，不新增接口字段。
- M7：建立 Fake Provider、Worker 测试骨架、Playwright 配置和稳定选择器规范。
- 合并顺序：L0 → M3/M4 → M5/M6 → M1/M2 → M7。
- 完成标准：空库启动、登录骨架、`/health/ready`、生成客户端和各领域空测试通过。

### Phase 1：公共平台和双工作台

- M4 先完成认证、用户、文件、Job 元数据、通知和权限接口；M3 随后接入登录、布局、用户、通知和公共上传。
- M5 完成投标 CRUD、统计/筛选和状态机骨架；M1 在 M5 API 测试通过后接入投标工作台和创建页。
- M6 完成评标 CRUD、从投标快照创建和状态机骨架；M2 在 M6 API 测试通过后接入评标工作台和创建草稿。
- M7 完成登录、权限、文件上传和两个工作台的基础 E2E；不替 M1/M2 修改页面。
- L0 逐个生成模型迁移，按 M4→M5→M6 顺序合并，禁止三个后端 PR 同时携带 revision。
- 完成标准：无 Mock 登录，投标/评标/管理列表来自数据库，跨租户访问测试通过。

### Phase 2：投标完整闭环

- M5 先交付需求、材料、资质、片段、审核、文档和版本领域接口；M4 提供文件/Job/通知平台端口。
- M7 在 Job 输入 Schema 稳定后交付解析、匹配、审核和生成 Worker；M5 负责验证结果并落业务表。
- M1 在后端契约测试通过后接入投标七步页面；M3 同期只负责资质/片段 UI 和所需公共组件。
- M7 最后编写投标主流程、异步失败、版本冲突和越权 E2E；L0 负责集成回归。
- 合并顺序：M4 公共前置 → M5 API → M7 Worker → M3 资源库/M1 投标 UI → M7 E2E → L0 集成。
- 完成标准：投标 E2E 全绿，输出 Word 可打开，版本比较/回滚保留完整历史。

### Phase 3：评标与 Portal 完整闭环

- M6 先交付发布、供应商会话、材料提交、补材料、报价、风险、评分、排名、报告和关闭接口。
- M4 提供文件、通知、审计和 Job 平台能力；M7 再交付完整性、风险、评分和报告 Worker。
- M2 在 M6 契约测试通过后接入内部评标六步和供应商 Portal，禁止直接依赖 M5 或内部登录状态。
- M7 最后编写邀请交换、跨供应商隔离、截止时间、重复提交、AI 降级和关闭后只读 E2E。
- 合并顺序：M4 公共前置 → M6 API → M7 Worker → M2 UI → M7 E2E → L0 集成。
- 完成标准：评标和 Portal E2E 全绿，跨供应商隔离、金额精度、幂等和审计不可篡改通过。

### Phase 4：系统设置、稳定性与答辩

- M4 完成全部设置、连接测试、全局搜索、审计导出和监控接口；M3 完成对应管理页面和错误状态。
- M1/M2 分别清理自己领域的 Mock、无效按钮、Console 错误、响应式和无障碍问题；不得跨目录互相修页面。
- M5/M6 分别完成领域性能、权限、状态机和恢复测试；M7 完成 Provider 降级、全量 E2E 与演示数据复位脚本测试。
- L0 执行依赖/密钥/契约/迁移检查、全量构建、空库启动、演示回归、版本标签和 `develop → main` 发布。
- 完成标准：本文所有页面矩阵和验收项都有测试证据，无 Mock 业务数据、无死按钮、无契约漂移，`main` 可独立复现演示。

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
