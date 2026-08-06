# 契约目录

本目录由 L0 维护，是前后端联调的唯一机器可读契约来源。

- `openapi.yaml`：HTTP API 契约，固定前缀 `/api/v1`。
- `events.schema.json`：WebSocket 事件 JSON Schema。
- `examples/`：契约测试和联调使用的固定请求/响应示例。

任何路径、方法、字段、枚举、错误码或事件变化必须先完成 `CONTRACT-CHANGE`，再由 L0 修改契约、重新生成前后端类型并单独合并。业务成员不得手工修改生成目录。

校验与生成：

```powershell
./scripts/validate-contract.ps1
./scripts/generate-contracts.ps1
```

CI 会检查 OpenAPI 有效性、158 个 `operationId` 唯一、所有响应带 `X-Request-Id`、事件示例符合 Schema，并确保重新生成后工作区无差异。
