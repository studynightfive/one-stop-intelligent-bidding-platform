"""M6 交付与联调说明（柠檬汁）。

详细端口映射见同目录 `M6_M4_PORT_ADAPTER.md`（以 M4_SERVICE_USAGE.md 为对照）。

## L0 接入清单
1. `backend/app/api/v1/router.py` include：
   - `evaluations.router`
   - `portal.router`
2. `models_registry.py` 显式：`import app.domains.evaluations.models`
3. 按 `models.py` 顶部 MIGRATION-NOTE 生成迁移（队列 M4→M5→M6）
4. 启动装配：
   - 有 M4：`build_m6_container_with_m4(db, bid_snapshot=m5_port)`
   - 无 M4：`build_m6_container()`（仅测试）
5. M4 中间件写入 `request.state.auth_principal`

## 依赖
- M4：JobDispatcher / NotificationService / AuditService / FileService（经 `m4_adapters.py`）
- M5：BidTaskSnapshotPort
- M7：消费 `input_data.m6JobType`，结果回写 M6 service（禁止 Worker 直写业务表）

## 已知缺口
- 供应商邀请目前只有 email，M4 站内通知需 user_id → 适配器跳过，待邮件通道
- Portal 回执 PDF / 报告 Binary 下载需接 FileService 签名 URL
- 内存 `EvaluationStore` 在 DB 迁移就绪后替换为 SQLAlchemy repository
"""
