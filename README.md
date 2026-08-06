# 一站式智能招投标平台

面向企业投标与采购评标的一站式平台。仓库包含 React 前端 Demo、统一接口契约、后端与基础设施骨架，以及供 8 人小组协作的权威开发提示词。

## 首先阅读

- [`PROJECT_MASTER_PROMPT.md`](PROJECT_MASTER_PROMPT.md)：唯一权威的功能范围、7 名组员分工、接口契约、环境版本和合并规则。
- [`Demo优化实施汇总_V1.1.md`](Demo优化实施汇总_V1.1.md)：当前 Demo 已完成的优化。
- `PRD.md`、`ARCHITECTURE.md`、`DESIGN.md`、`SPEC.md`：背景资料；冲突时以总提示词为准。

## L0 Phase 0 基础能力

- `contracts/openapi.yaml` 是 158 个 HTTP 操作的唯一事实源；`contracts/events.schema.json` 是实时事件事实源。
- 前端类型生成到 `demo/src/api/generated/`，后端契约模型生成到 `backend/app/contracts/generated/`，禁止手工修改生成文件。
- Python、Node、npm、uv 和容器服务版本均已锁定；本机已有其他 Python/uv 版本时，必须通过仓库脚本运行。
- 后端中央 Router、SQLAlchemy 模型注册器、Alembic 单迁移头、Compose 与 CI 已建立。
- CI 检查文件所有权、契约漂移、破坏性接口变更、前后端质量、镜像构建和密钥泄漏。

## 环境与初始化

要求 Node.js `24.16.0`、npm `11.13.0`、Python `3.11.11`、uv `0.5.11`、Docker `>=27.0.0`、Compose `>=2.29.0` 和 OpenSSL。仓库当前验收版本为 Docker `29.6.1`、Compose `5.2.0`。

Windows：

```powershell
.\scripts\check-environment.ps1
.\scripts\bootstrap.ps1
```

macOS/Linux：

```bash
./scripts/check-environment.sh
./scripts/bootstrap.sh
```

初始化脚本会创建本地 `.env` 和仅供开发使用的忽略密钥、安装锁定依赖、生成并校验契约代码。不会写入真实业务数据或生产密钥。

## 运行当前前端 Demo

```bash
cd demo
npm ci
npm run dev
```

浏览器打开：<http://127.0.0.1:3210>

后端与完整本地服务：

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d postgres redis minio minio-init mailpit api web
```

API 文档：<http://127.0.0.1:8210/docs>。容器化前端：<http://127.0.0.1:3210>。直接运行的 Vite Demo 与容器化前端使用同一端口，二者只启动一个。

## 提交前验收

Windows：

```powershell
.\scripts\verify.ps1
```

macOS/Linux：

```bash
./scripts/verify.sh
```

验收包含环境版本、契约一致性和可重复生成、后端 lint/类型/测试覆盖率、单迁移头、前端 lint/类型/测试/构建以及 Compose 配置。

## 小组协作

成员按 `PROJECT_MASTER_PROMPT.md` 的 M1-M7 文件所有权和分支规则开发。任何接口变化必须先走 CONTRACT-CHANGE，不允许口头约定或成员自行创建同义接口。成员不得直接编辑中央 Router、迁移版本、依赖锁或生成代码；由 L0 在对应基础 PR 中统一处理。

## 当前状态

- L0 Phase 0：契约、锁定环境、基础设施、生成代码、中央后端骨架和 CI 已完成并可重复验证。
- 前端 Demo：可运行、可构建、主要流程可交互。
- M1-M7 的正式业务实现、AI Worker 和跨域 E2E：按总提示词后续阶段由对应唯一所有者完成。
- 仓库默认不包含任何真实密钥、供应商文件或生产数据。
