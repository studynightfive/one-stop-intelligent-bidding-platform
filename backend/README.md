# 后端基础骨架

本目录由 L0 建立中央骨架，M4/M5/M6/M7 只能在 `PROJECT_MASTER_PROMPT.md` 分配的领域目录中实现代码。

```powershell
../scripts/uv.ps1 sync --frozen
../scripts/uv.ps1 run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

当前中央应用直接加载 `contracts/openapi.yaml` 作为 Swagger 契约。领域成员在自己的目录导出 `router`，由 L0 在 `app/api/v1/router.py` 中统一注册。

迁移规则：业务成员只提交 ORM 模型和 PR 中的 `MIGRATION-NOTE`；只有 L0 可以新增或修改 `migrations/versions/`。
