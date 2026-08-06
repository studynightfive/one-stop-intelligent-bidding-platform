# 本地集成环境

所有容器、网络和卷固定使用 `bidplat2026_` 前缀，端口只能使用 `.env.example` 与总提示词第 4 节规定的值。

```powershell
./scripts/bootstrap.ps1
docker compose --env-file .env -f infra/compose.yaml up -d postgres redis minio minio-init mailpit api web
```

可选服务：

```powershell
# M7 完成 Worker 后
docker compose --env-file .env -f infra/compose.yaml --profile workers up -d

# M4/M7 完成 metrics 后
docker compose --env-file .env -f infra/compose.yaml --profile observability up -d
```

默认核心栈不会启动尚未由 M7 实现的 Celery Worker。`workers` 与 `observability` Profile 已锁定镜像、端口和挂载，成员不得另建 Compose 文件。
