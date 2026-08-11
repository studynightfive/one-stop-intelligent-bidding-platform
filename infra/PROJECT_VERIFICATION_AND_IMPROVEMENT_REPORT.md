# 一站式智能招投标平台：项目核查、修复与本地验证报告

> 核查日期：2026-08-11<br>
> 核查基线：`develop` 分支 `b7054bf`，以及本报告所在的 L0 收口提交<br>
> 当前阶段：课程小组前端 Demo 功能验收；业务数据长期持久化和生产容量不属于本轮重点

## 1. 结论

本轮已经按“契约、后端、前端、页面交互、端到端流程、部署隔离”的顺序完成核查和修复。现有 Demo 的预设业务板块均能进入并完成对应演示流程，前端不再依赖会污染在线状态的 Mock 数据，关键按钮、路由和下载操作均有真实接口或明确的前端状态反馈。

新增的技术标书文档生成功能已形成完整链路：用户可以按照给定章节格式逐节配置要求和段落数，上传章节参考图片；服务端先生成提纲，再按段落逐次调用统一的大模型接口，使用受限上下文和续写摘要控制上下文长度；生成过程中保存检查点，最终把文字和图片组装成可下载的 DOCX。默认本地环境使用确定性的 Fake Provider，保证离线演示和 CI 稳定；接入真实模型时需关闭 Fake Provider 并配置 OpenAI 兼容服务。

截至本报告生成时，没有发现阻塞 Demo 演示的已知功能缺口。仍有三个非阻塞改进项：前端大包拆分、React Router 7 升级，以及生产环境持久化/真实模型配置，详见第 8 节。

## 2. 核查范围与方法

| 层级 | 核查内容 | 判定方式 |
| --- | --- | --- |
| API 契约 | 158 个 OpenAPI operation、DTO、鉴权头、幂等键、并发版本和接口负责人 | 契约检查脚本、生成代码确定性校验 |
| 后端 | 招标、投标、评标、供应商门户、文件、通知、管理员和 AI 文档链路 | Ruff、mypy、388 个 pytest |
| 前端 | 页面路由、加载/错误态、表单校验、真实 API 调用、下载和搜索跳转 | TypeScript、ESLint、73 个 Vitest、生产构建 |
| 浏览器业务流 | 登录、创建/提交投标、评标、供应商门户、管理员、技术文档生成和 DOCX 下载 | Playwright 桌面业务流与多设备 UI 冒烟 |
| 部署 | Docker Compose 配置、服务健康、端口占用和镜像名隔离 | 独立项目名、独立端口、健康检查、容器日志 |

完整验证入口为 [`scripts/verify.ps1`](../scripts/verify.ps1)。默认执行静态检查、单元/集成测试和构建；已经启动健康的本地栈时，使用 `-IncludeE2E` 执行真实浏览器流程。

## 3. 查找到的问题与解决方案

| 问题 | 影响 | 已采用的解决方案 | 验证结果 |
| --- | --- | --- | --- |
| 管理员页面部分功能仍读 Mock 数据 | 页面展示与服务端真实状态不一致 | 管理员用户、租户、审计和配置页统一接入生成客户端与真实 API | 管理员页面与后端测试通过 |
| 评标详情、供应商门户和上传流程不完整 | 能进入页面但无法完成端到端操作 | 补齐详情查询、提交动作、鉴权上传、加载态和下载动作 | 评标及门户 E2E 通过 |
| 投标任务在在线模式仍可落回 Mock 链接 | 搜索/跳转可能进入不存在的业务数据 | 在线模式只使用服务端任务和真实资源标识 | 路由与业务流通过 |
| 评标任务缺少可重复演示的初始化状态 | Demo 无法稳定展示结果和报告 | 加入确定性种子数据、自动生成评标结果和报告、关闭/幂等边界 | 后端集成与 E2E 通过 |
| 报告生成按钮在错误状态可触发 | 产生无效请求或难以理解的错误 | 按任务状态、权限和已有结果控制按钮并提供反馈 | 前端测试通过 |
| 在线上下文混入 Mock 项目 | 真实接口数据被示例数据覆盖 | 拆分在线/Mock 数据入口，在线页面不再读取 Mock 上下文 | 在线路由测试通过 |
| 默认管理员邮箱使用 `.local` | 表单校验失败，首次登录体验不一致 | 统一为 `admin@bid-platform.dev`，引导数据改为幂等初始化 | 登录与引导流程通过 |
| 中文评标报告文件名导致下载 500 | 中文项目无法下载报告 | 使用安全 ASCII fallback 和 RFC 5987 `filename*` | 中文、混合字符和注入用例通过 |
| E2E 存在占位测试且视频工具是隐藏依赖 | CI 显示通过但未覆盖真实业务，机器缺工具时失败 | 替换为真实 API/UI 流程；录屏变成可选能力；统一测试代码风格 | 15 通过、6 个按设备策略跳过 |
| 全局搜索中同一项目的投标/评标结果外观相同 | 用户误以为是重复结果 | 标签明确标注“投标任务”“评标任务”等资源类型 | 浏览器人工核查及测试通过 |
| Compose 使用通用容器/镜像/端口 | 可能与其他本地项目冲突 | 支持项目名、镜像标签和全部宿主端口覆盖；启动前检查端口 | 独立栈健康运行 |
| CI 只构建镜像，没有执行真实浏览器业务流 | 合并后可能遗漏跨层错误 | 基础设施 Job 安装锁定版 Chromium，启动完整栈并运行 E2E，始终清理容器 | 本地等价命令已完整通过，CI 作为合并门禁 |

相关修复已分批通过 PR 合并到 `develop`，主要为 #51–#70；技术文档链路的前置实现为 #34、#35、#38 和 #48。

## 4. 大模型技术文档生成链路

### 4.1 统一输入格式

[`contracts/openapi.yaml`](../contracts/openapi.yaml) 定义了 `TechnicalDocumentGenerationOptions`，固定使用 `paragraph_by_paragraph` 策略。每个章节包含：

- 章节键、标题和章节级生成要求；
- 目标段落数和每段目标字数；
- 招标背景、评审重点等补充上下文；
- 与章节绑定的 PNG/JPEG 图片锚点及图片说明。

前端在 [`BidDocumentOutputTab.tsx`](../demo/src/features/bids/components/BidDocumentOutputTab.tsx) 中编辑上述信息，并由 [`technicalDocumentConfig.ts`](../demo/src/features/bids/adapters/technicalDocumentConfig.ts) 转换为契约请求。请求 DTO 由 OpenAPI 生成，避免前后端手写同名但不同结构的接口类型。

### 4.2 分段生成与长上下文控制

[`technical_document.py`](../backend/app/ai/technical_document.py) 负责校验章节、段落预算和图片锚点；[`bidding_generator.py`](../backend/app/workers/bidding_generator.py) 执行生成流程：

1. 根据模板、项目上下文和章节约束生成全局提纲。
2. 按章节顺序处理，每次只生成一个段落，不要求模型一次输出整本标书。
3. 每次请求携带已批准提纲、当前章节要求、必要证据、上一段续写摘要和当前章节图片锚点。
4. 对传入上下文做长度限制，防止大型技术文档持续累积后超过模型上下文窗口。
5. 每完成一段就记录检查点、调用版本、Token 用量和 Provider 状态；异常重试时从最后完成段落继续。
6. 所有段落完成后再进入文档装配阶段。

该设计使“大文档、长上下文、包含图片”的生成任务可拆解、可重试、可追踪，而不是把全部材料塞入单次模型调用。

### 4.3 图片与 DOCX 输出

[`service.py`](../backend/app/domains/bids/service.py) 根据文件权限读取并检查参考图片，[`generator.py`](../backend/app/domains/documents/generator.py) 把生成段落、章节层级和图片写入实际 DOCX。端到端测试会检查下载文件的 ZIP/DOCX 头以及 `word/media/` 中的嵌入媒体，不以假扩展名或纯文本代替文档。

真实业务覆盖位于 [`business-flow.spec.ts`](../e2e/specs/business-flow.spec.ts)，单元/集成覆盖位于 [`test_technical_document_generation.py`](../backend/tests/ai/test_technical_document_generation.py)、[`test_technical_document_eager_flow.py`](../backend/tests/bids/test_technical_document_eager_flow.py) 和 [`test_document_generator.py`](../backend/tests/documents/test_document_generator.py)。

### 4.4 模型环境说明

- 本地 Demo/CI：`.env.example` 默认 `AI_FAKE_PROVIDER=true`，无需联网和密钥，可稳定验证拆段、检查点、图片和 DOCX 全链路。
- 真实模型：设置 `AI_FAKE_PROVIDER=false`，并配置项目支持的 OpenAI 兼容 Provider 地址、模型和 API Key。
- Fake Provider 只替代模型内容生成，不绕过任务编排、文件鉴权、段落检查点或文档装配，因此本地验证仍覆盖应用自身逻辑。

## 5. 接口与代码风格一致性

- OpenAPI 当前包含 158 个唯一 operation；前端和后端 DTO 均从同一契约生成。
- 契约校验覆盖接口 owner、认证头、幂等键、并发控制字段和技术文档 Prompt 配置。
- Python 使用 Ruff 格式/静态检查与 mypy；当前共检查 266 个格式化文件、189 个 mypy 源文件。
- Demo 和 E2E 统一由 TypeScript 与 ESLint 约束；新增 E2E 已统一项目现行的无分号风格。
- `.editorconfig` 统一编码、缩进、换行和文件末尾规则。
- CI 使用锁文件安装依赖，并执行契约、后端、前端、基础设施和真实浏览器流程。

## 6. 完整验证结果

本轮在同一工作树执行：

```powershell
$env:WEB_PORT = '33210'
$env:API_PORT = '38210'
$env:E2E_BASE_URL = 'http://127.0.0.1:33210'
$env:E2E_API_URL = 'http://127.0.0.1:38210'
.\scripts\verify.ps1 -IncludeE2E
```

| 检查项 | 结果 |
| --- | --- |
| OpenAPI 契约与生成代码 | 158 个 operation；契约一致；重复生成无差异 |
| Python Ruff | 全部通过，266 个文件格式一致 |
| Python mypy | 189 个源文件无错误 |
| 后端 pytest | 388 / 388 通过 |
| 数据库迁移 | 单一 Alembic head：`0004_m5_bids` |
| 前端 TypeScript / ESLint | 通过 |
| 前端 Vitest | 17 个测试文件、73 / 73 通过 |
| 前端生产构建 | 通过 |
| E2E TypeScript / ESLint | 通过 |
| Playwright | 15 通过、6 跳过 |
| Compose 配置 | 通过 |
| Git whitespace | 通过 |
| npm production audit（E2E） | 0 个漏洞 |

Playwright 的 6 个跳过不是缺失功能：会改变业务数据的完整流程只在桌面项目执行一次；登录、健康检查和基础 UI 仍在桌面、平板、手机项目执行，避免三个设备重复提交相同业务动作造成状态竞争。

浏览器人工验收还确认：

- 登录、导航菜单、全局搜索和投标/评标结果跳转正常；
- 搜索结果类型标签可辨认，不再把同一项目下的不同任务误判为重复项；
- 技术文档页显示 4 个预设章节，每节均可配置文字规则和参考图片，生成按钮状态正确；
- 页面控制台无新增 warning/error。

## 7. 隔离本地部署

启动前已逐一确认下列端口空闲。本轮使用独立 Compose 项目名和镜像标签，不占用项目默认的 3210/8210 端口，也不影响其他项目。

| 服务 | 本地地址/端口 |
| --- | --- |
| Web Demo | <http://127.0.0.1:33210> |
| API | <http://127.0.0.1:38210> |
| PostgreSQL | `55440` |
| Redis | `56380` |
| MinIO API / Console | `59010` / `59011` |
| Mailpit SMTP / Web | `51035` / `58035` |

- Compose 项目名：`bidplat_verify_20260811`
- API 镜像：`bidplat-verify-20260811/api:final`
- Web 镜像：`bidplat-verify-20260811/web:final`
- 演示账号：`admin@bid-platform.dev`
- 演示密码：`DemoAdmin123!`

验证完成后全部服务健康；为便于继续人工验收，本地隔离栈暂时保留运行。

## 8. 非阻塞风险与后续建议

### 8.1 前端主包较大

生产构建成功，但主 JavaScript 包约 1,706.50 kB（gzip 约 531.49 kB）。这不影响 Demo 功能，后续可按路由拆分管理员、评标、供应商门户和标书编辑器，并单独分离编辑器/图表依赖。

### 8.2 React Router 安全升级需要独立迁移

当前 production audit 报告 2 个 React Router 中等级别建议，自动修复会强制升级至 v7，属于破坏性变更。其中 SSR hydration 问题不适用于当前纯 SPA；开放重定向风险也因当前路由目标由应用内受控值产生而受到限制。建议另建升级任务迁移到 React Router 7，并重新执行全部路由和 E2E 用例，不应在本轮功能收口中使用 `--force` 冒险升级。

### 8.3 真实模型与生产数据

本地默认 Fake Provider 是为了离线和 CI 可重复，并不代表已配置生产模型。上线前必须使用受管密钥接入真实 OpenAI 兼容 Provider，完成成本、超时、内容合规和质量评测。部分 Demo 状态仍按课程演示需要使用进程内存；持久化、备份、灾备和生产容量应在进入真实数据阶段后单独设计。

## 9. 验收建议

组长可优先使用以下顺序验收：

1. 以管理员账号登录并检查全局导航、搜索及管理员功能。
2. 进入投标任务，检查材料上传、提交和状态流转。
3. 进入“文档输出”，逐节修改模板要求、上传图片并启动技术标书生成。
4. 下载 DOCX，检查章节顺序、段落内容和图片位置。
5. 进入评标任务及供应商门户，检查提交、结果、报告和下载。
6. 如需复验全部自动化，保持隔离栈健康后执行第 6 节命令。
