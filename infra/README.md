# 本地集成环境

所有容器、网络和卷固定使用 `bidplat2026_` 前缀，端口只能使用 `.env.example` 与总提示词第 4 节规定的值。

```powershell
./scripts/start.ps1
```

该命令会从空数据库执行迁移并等待 API 与 Web 健康；使用 `./scripts/stop.ps1` 停止服务且保留数据卷。macOS/Linux 使用同名 `.sh` 脚本。

可选服务：

```powershell
# M7 完成 Worker 后
docker compose --env-file .env -f infra/compose.yaml --profile workers up -d

# M4/M7 完成 metrics 后
docker compose --env-file .env -f infra/compose.yaml --profile observability up -d
```

默认核心栈不会启动尚未由 M7 实现的 Celery Worker。`workers` 与 `observability` Profile 已锁定镜像、端口和挂载，成员不得另建 Compose 文件。
