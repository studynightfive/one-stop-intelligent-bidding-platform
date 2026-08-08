# M6 交付与联调说明

详细端口映射见同目录 `M6_M4_PORT_ADAPTER.md`。

## L0 接入清单

1. 在中央 API Router 挂载 `evaluations.router` 与 `portal.router`。
2. 在 `models_registry.py` 显式导入 `app.domains.evaluations.models`。
3. 由 L0 根据 `models.py` 的 `MIGRATION-NOTE` 生成 Alembic 迁移。
4. 以应用级共享 `EvaluationStore` 保存 Demo 状态；每个请求使用当前 M4
   `DBSession` 构建 M4 端口适配器，避免跨请求复用数据库会话。
5. L0 覆盖 `get_actor` 依赖，将 M4 `AuthenticatedUser` 通过
   `auth_principal_from_context` 映射为 M6 `AuthPrincipal`。

## 依赖边界

- M4：`JobDispatcher`、`NotificationService`、`AuditService`、`FileService`，
  只经 `m4_adapters.py` 调用。
- M5：`BidTaskSnapshotPort`；尚未接入时导入接口返回标准 `NOT_FOUND`。
- M7：消费 `input_data.m6JobType` 并通过 M6 service 回写任务结果，禁止
  Worker 直接写业务表。

## Demo 阶段说明

- 评标、门户、报价、评分的完整状态链当前使用进程内 `EvaluationStore`。
- ORM 模型仍会由 L0 注册和迁移，为后续数据持久化阶段保留稳定表结构。
- 供应商只有邮箱而没有内部 `user_id` 时，站内通知适配器会跳过；邮件通道
  由后续 M4/M7 集成补充。
