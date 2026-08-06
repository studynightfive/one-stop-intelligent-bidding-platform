# 单一迁移链

`versions/` 只允许 L0 修改。M4/M5/M6 在业务 PR 中提交 `MIGRATION-NOTE`，L0 按固定队列从最新 `develop` 生成 revision，并验证只有一个 head。
