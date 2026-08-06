# 本地密钥目录

执行 `scripts/bootstrap.ps1` 或 `scripts/bootstrap.sh` 后会生成未纳入 Git 的 `infra/secrets/dev/`：

- `jwt_private_key`
- `jwt_public_key`
- `model_master_key`

禁止提交真实密钥。CI 只生成临时测试密钥。
