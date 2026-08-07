# M6 ↔ M4 端口对接说明书（柠檬汁 / M6 独占）

> 状态：M6 职责文档（可随 M6 PR 提交）  
> 对照来源：`M4_SERVICE_USAGE.md`（只读参考；**不要**把根目录该文件放进 M6 PR）  
> 代码入口：`ports.py`（稳定协议）+ `m4_adapters.py`（真实 M4 适配）+ `container.py`

---

## 1. M6 职责边界（不变）

| 项 | 内容 |
|---|---|
| 领域 | `evaluations` / `portal` / `pricing` / `scoring` |
| HTTP | 总提示词 §8.4、§8.5 |
| 禁止 | 改 `core/`、改 M4 域、改 OpenAPI、改中央 Router、改迁移 versions |
| 依赖 | **只经 Port** 使用 M4；投标数据只经 M5 `BidTaskSnapshotPort` |

---

## 2. M4 服务 → M6 Port 映射

| M4（文档导入路径） | M6 Port | 适配器 | M6 使用场景 |
|---|---|---|---|
| `job_dispatcher.dispatch` | `JobDispatcherPort.enqueue` | `M4JobDispatcherAdapter` | 材料检查 / 风险 / AI 评分 / 报告 |
| `NotificationService.create_notification` | `NotificationServicePort.notify` | `M4NotificationAdapter` | 发布后通知内部用户 |
| `AuditService.log` | `AuditServicePort.append` | `M4AuditAdapter` | 发布、关闭、改分、门户提交等 |
| `FileService` 下载/预览/元数据 | `FileServicePort` | `M4FileServiceAdapter` | Portal 材料、报告下载元数据 |
| `AuthenticatedUser` + DBSession | `AuthPrincipal`（路由注入） | L0/M4 中间件写 `request.state` | 全部内部 API |
| （M5）投标快照 | `BidTaskSnapshotPort` | M5 提供 | `from-bid-task` |

`SettingsService`：**M6 评标域不直接调**（模型密钥归 M7）。

---

## 3. Job 类型映射（重要差异）

总提示词场景名保留在 `input_data.m6JobType`；M4 枚举较粗：

| M6 `job_type` | M4 `JobType` |
|---|---|
| `evaluation.material_check` | `ai_analysis` |
| `evaluation.risk_check` | `ai_analysis` |
| `evaluation.ai_scoring` | `ai_analysis` |
| `evaluation.report_generate` | `document_generation` |

M7 Worker 必须读 `input_data["m6JobType"]` 区分场景，不能只看 M4 `JobType`。

---

## 4. 审计 / 通知字段对齐

### Audit（已对齐）

M6 `AuditEventInput` 现含：`tenant_id`、`aggregate_*`、`actor_*`、`action`、`summary`、`changes`、`request_id`、`ip_address`。  
适配器调用：

```python
await audit_service.log(
    tenant_id=...,
    aggregate_type=...,
    aggregate_id=UUID(...),
    actor_type=ActorType(...),
    ...
)
```

建议 `action` 使用可读点分名（如 `evaluation.published`）；与 M4 文档建议的 `create/submit` 可并存，评审域以点分名为准便于检索。

### Notification（缺口）

- M4 当前按 **内部 `user_id`** 发站内信。
- 发布邀请供应商时 M6 只有 **email**，无内部用户 ID → 适配器 **跳过**（不报错）。
- 需 L0/M4：`BOUNDARY-CHANGE` 增加邮件通知，或邀请仅写审计 + 由前端展示 inviteUrl。

---

## 5. 集成装配（给 L0）

```python
# 伪代码：main 或 lifespan（L0 独占文件）
from app.domains.evaluations.container import build_m6_container_with_m4
from app.domains.evaluations.router import router as evaluations_router
from app.domains.portal.router import router as portal_router

app.state.m6 = build_m6_container_with_m4(db_session_factory_or_session, bid_snapshot=m5_port)
api_router.include_router(evaluations_router)
api_router.include_router(portal_router)
```

鉴权：生产由 M4 写入 `request.state.auth_principal`（`AuthPrincipal`）；调试 Header 仅测试。

---

## 6. M6 自检清单（对接 M4 后）

- [ ] `develop` 已含 M4 域代码与中央 Router 注册
- [ ] `build_m6_container_with_m4` 可 import，无 `ModuleNotFoundError`
- [ ] 发布评标 → Job/Audit 落库；邀请邮件缺口已知
- [ ] Portal 上传绑定的 `fileId` 经 `FileServicePort.assert_accessible` 校验租户
- [ ] AI/报告 Job 的 `m6JobType` 被 M7 正确消费
- [ ] 人工改分有 `AuditService.log` 留痕
- [ ] M6 PR **不含** 根目录 `M4_SERVICE_USAGE.md`、不含 `core/`、不含 M4 域文件

---

## 7. 本地开发策略

| 阶段 | 用法 |
|---|---|
| 现分支单测 | `build_m6_container()` → `RecordingPorts` |
| 已 merge M4 的 develop | `build_m6_container_with_m4(db, bid_snapshot=...)` |
| 只读 M4 文档 | worktree / `git show`；职责说明写本文件 |

---

## 8. 待提交流程

1. M6 继续只提交 `backend/app/domains/{evaluations,portal,pricing,scoring}/**` 与对应 tests  
2. 根目录 `M4_SERVICE_USAGE.md`：本地参考即可，**M6 PR 请勿纳入**（属 M4/文档所有权）  
3. 契约不足（供应商邮件通知、JobType 细粒度）→ 提 `CONTRACT-CHANGE` / `BOUNDARY-CHANGE` 给 L0+M4
