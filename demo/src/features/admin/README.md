# M3 平台公共能力与后台管理验收清单

本目录负责 M3 独占路由、导航和后台能力。M1/M2 业务页面仅通过路由聚合接入，M3 不修改其业务实现。

## 必测路径

- `/login`：表单校验、密码显隐、记住登录、找回密码、登录后返回原访问页。
- 主框架：路由守卫、侧栏/移动端抽屉、面包屑、全局搜索、通知已读、用户菜单和演示数据重置。
- `/admin/qualifications`：查询筛选、30/60/90 天动态预警、增改删、批量导入、下载/预览、版本记录。
- `/admin/fragments`：关键词/语义检索、分类筛选、增改删、引用计数、引用明细、版本记录。
- `/admin/users`：邀请/重发、启停确认、密码重置、RBAC 矩阵、参与项目和活动记录。
- `/admin/settings`：模型路由与连通性、部署存储、模板、通知、操作日志、未保存提示。
- `/403`、`/500` 和不存在的地址：对应错误页可返回安全页面。

## 自动化定位点

- `login-page`
- `qualification-library-page` / `qualification-row`
- `fragment-library-page` / `fragment-card`
- `user-permissions-page`
- `system-settings-page`

## 网络层约束

后台业务请求统一经 `src/api/client.ts` 发起。该客户端负责 Base URL、Bearer Token、401 单次刷新、`X-Request-ID`、`If-Match`、幂等键、超时/取消、统一错误映射和 409 版本冲突；业务页面不得另建并行请求封装。
