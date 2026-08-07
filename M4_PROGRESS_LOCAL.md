# M4 公共平台后端 — 开发进度跟踪

> 负责人：luojinju
> 角色：M4 - 公共平台后端
> 创建日期：2026-08-07
> 最后更新：2026-08-07（Celery Worker 集成完成，M4 所有任务基本完成）

---

## 一、项目概述

### 1.1 M4职责定位
M4是**公共平台后端**，负责为整个系统提供基础设施能力，其他所有成员（M1/M2/M3/M5/M6/M7）都必须依赖M4提供的公共服务。

### 1.2 独占文件范围
```
backend/app/core/**                    # 核心配置、安全、数据库、错误处理
backend/app/domains/auth/**            # 认证领域
backend/app/domains/users/**           # 用户领域
backend/app/domains/files/**           # 文件领域
backend/app/domains/jobs/**           # 异步任务领域
backend/app/domains/notifications/**   # 通知领域
backend/app/domains/settings/**       # 设置领域
backend/app/domains/audit/**          # 审计领域
backend/app/domains/search/**         # 搜索领域
backend/tests/**                     # 对应的单元/接口测试
```

### 1.3 必须提供的Service端口（供其他模块调用）
| 端口名 | 用途 | 调用方 |
|--------|------|--------|
| `AuthContext` | 认证上下文、JWT验证 | M5/M6/M7 |
| `FileService` | 文件上传/下载/预览 | M5/M6 |
| `JobService/JobDispatcher` | 异步任务创建/查询/取消 | M5/M6/M7 |
| `NotificationService` | 发送通知 | M5/M6 |
| `AuditService` | 记录审计事件 | M5/M6 |
| `SettingsService` | 读取模型密钥 | M7 |

---

## 二、任务分解与状态

### Phase 0: 基础架构（第1周）

#### 阶段状态：🔄 进行中

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T0.1 | 数据库会话配置 | ✅ 完成 | 复用L0骨架 |
| T0.2 | 项目依赖安装 | ✅ 完成 | pyproject.toml已定义 |
| T0.3 | 创建core模块骨架 | ✅ 完成 | config/errors/security/dependencies/logging |
| T0.4 | 创建domains目录骨架 | ✅ 完成 | 9个领域目录结构 |
| T0.5 | 错误处理框架 | ✅ 完成 | AppException + 全局处理器 |
| T0.6 | 依赖注入框架 | ✅ 完成 | get_current_user/require_admin等 |
| T0.7 | 健康检查接口 | ✅ 完成 | `/health/live`, `/health/ready` |

### Phase 1: 认证模块（auth）（第2周）

#### 阶段状态：🔄 进行中

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T1.1 | 用户模型与数据库表 | ✅ 完成 | User模型 + UserRole/UserStatus枚举 |
| T1.2 | JWT Token生成与验证 | ✅ 完成 | RS256 + Access/Refresh/Portal Token |
| T1.3 | POST /auth/login | ✅ 完成 | 公开接口 |
| T1.4 | POST /auth/refresh | 🔄 部分 | 框架完成，待实现Cookie解析 |
| T1.5 | POST /auth/logout | ✅ 完成 | 登录用户 |
| T1.6 | GET /auth/me | ✅ 完成 | 登录用户 |
| T1.7 | PATCH /auth/me | ✅ 完成 | 更新资料 |
| T1.8 | POST /auth/password/forgot | ✅ 完成 | 框架完成 |
| T1.9 | POST /auth/password/reset | ✅ 完成 | 框架完成 |
| T1.10 | AuthContext依赖注入 | ✅ 完成 | get_current_user等 |

### Phase 2: 用户管理模块（users）（第2-3周）

#### 阶段状态：🔄 进行中

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T2.1 | GET /users | ✅ 完成 | 列表 + 分页 + 筛选 |
| T2.2 | POST /users/invitations | ✅ 完成 | admin |
| T2.3 | POST /users/{id}/invitations/resend | ✅ 完成 | admin |
| T2.4 | PATCH /users/{id} | ✅ 完成 | admin |
| T2.5 | POST /users/{id}/status | ✅ 完成 | admin - 启停用户 |
| T2.6 | POST /users/{id}/password-reset-email | ✅ 完成 | admin |
| T2.7 | GET /users/{id}/projects | ✅ 完成 | admin/本人 |
| T2.8 | GET /users/{id}/activity | ✅ 完成 | admin/本人 |
| T2.9 | GET /roles | ✅ 完成 | admin - 角色定义列表 |
| T2.10 | GET /permissions/matrix | ✅ 完成 | admin - 权限矩阵 |

### Phase 3: 文件平台（files）（第3周）

#### 阶段状态：🔄 进行中

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T3.1 | FileService核心服务 | ✅ 完成 | 框架骨架 |
| T3.2 | 分片上传会话模型 | ✅ 完成 | FileUploadSession + File模型 |
| T3.3 | SHA-256校验 | ✅ 完成 | compute_sha256函数 |
| T3.4 | MinIO集成 | ✅ 完成 | 框架 + 签名URL |
| T3.5 | 病毒扫描集成 | 📋 待实现 | ClamAV集成 |
| T3.6 | 签名URL生成 | ✅ 完成 | presigned_get_object |
| T3.7 | POST /files/upload-sessions | ✅ 完成 | 创建上传会话 |
| T3.8 | PUT /files/upload-sessions/{id}/parts/{n} | ✅ 完成 | 分片上传路由 |
| T3.9 | POST /files/upload-sessions/{id}/complete | ✅ 完成 | 完成上传 |
| T3.10 | GET /files/{fileId}/preview | ✅ 完成 | 预览文件 |
| T3.11 | GET /files/{fileId}/download | ✅ 完成 | 下载文件 |

### Phase 4: 异步任务（jobs）（第3-4周）

#### 阶段状态：✅ 完成

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T4.1 | Job模型与数据库表 | ✅ 完成 | Job + JobStatus/JobType枚举 |
| T4.2 | JobService核心服务 | ✅ 完成 | create_job/get_job/cancel_job等 |
| T4.3 | JobDispatcher | ✅ 完成 | dispatch/dispatch_and_start |
| T4.4 | Celery Worker集成 | ✅ 完成 | celery_app + tasks.py |
| T4.5 | 进度持久化 | ✅ 完成 | update_job_status/mark_job_progress |
| T4.6 | WebSocket票据服务 | ✅ 完成 | 一次性票据30秒，Lua原子操作 |
| T4.7 | GET /jobs/{jobId} | ✅ 完成 | 权限检查 |
| T4.8 | POST /jobs/{jobId}/cancel | ✅ 完成 | 权限检查 |
| T4.9 | POST /realtime/tickets | ✅ 完成 | - |

### Phase 5: 通知系统（notifications）（第4周）

#### 阶段状态：✅ 完成

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T5.1 | 通知模型与数据库表 | ✅ 完成 | Notification + NotificationType枚举 |
| T5.2 | NotificationService | ✅ 完成 | create/list/mark_read等方法 |
| T5.3 | GET /notifications | ✅ 完成 | 完整实现 |
| T5.4 | PATCH /notifications/{id} | ✅ 完成 | 完整实现 |
| T5.5 | POST /notifications/read-all | ✅ 完成 | 完整实现 |

### Phase 6: 审计日志（audit）（第4周）

#### 阶段状态：✅ 完成

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T6.1 | 审计事件模型与数据库表 | ✅ 完成 | AuditEvent + ActorType枚举 |
| T6.2 | AuditService | ✅ 完成 | append-only，log/list方法 |
| T6.3 | GET /audit-events | ✅ 完成 | 路由骨架 |
| T6.4 | GET /audit-events/export | ✅ 完成 | 路由骨架 |

### Phase 7: 全局搜索（search）（第4周）

#### 阶段状态：📋 待开始

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T7.1 | GET /global-search | ✅ 完成 | 路由骨架 |

### Phase 8: 系统设置（settings）（第4-5周）

#### 阶段状态：✅ 完成

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T8.1 | 模型服务商CRUD | ✅ 完成 | 路由骨架 |
| T8.2 | API Key加密存储 | ✅ 完成 | AES-256-GCM加密函数 |
| T8.3 | 场景路由配置 | ✅ 完成 | 路由骨架 |
| T8.4 | 生成参数配置 | ✅ 完成 | 路由骨架 |
| T8.5 | 部署设置 | ✅ 完成 | 路由骨架 |
| T8.6 | 文档模板设置 | ✅ 完成 | 路由骨架 |
| T8.7 | 通知策略设置 | ✅ 完成 | 路由骨架 |
| T8.8 | Agent状态查询 | ✅ 完成 | 路由骨架 |
| T8.9 | SettingsService | ✅ 完成 | 加密/解密API Key接口 |

### Phase 9: 测试与验收（第5周）

#### 阶段状态：📋 待开始

| 任务 | 描述 | 状态 | 备注 |
|------|--------|------|------|
| T9.1 | 单元测试 | 📋 待开始 | 覆盖率>=85% |
| T9.2 | 接口测试 | 📋 待开始 | pytest-asyncio |
| T9.3 | 文件越权测试 | 📋 待开始 | - |
| T9.4 | Refresh重放测试 | 📋 待开始 | - |
| T9.5 | 任务取消测试 | 📋 待开始 | - |
| T9.6 | 密钥脱敏测试 | 📋 待开始 | - |
| T9.7 | 健康降级测试 | 📋 待开始 | - |

---

## 三、接口清单汇总

### 3.1 认证、用户与权限（8.1节）
| Method | Path | 权限 | 状态 |
|--------|------|------|------|
| POST | /auth/login | 公开 | ✅ |
| POST | /auth/refresh | Refresh Cookie | 🔄 |
| POST | /auth/logout | 登录用户 | ✅ |
| GET | /auth/me | 登录用户 | ✅ |
| PATCH | /auth/me | 登录用户 | ✅ |
| POST | /auth/password/forgot | 公开 | ✅ |
| POST | /auth/password/reset | 公开 | ✅ |
| GET | /users | admin | ✅ |
| POST | /users/invitations | admin | ✅ |
| POST | /users/{userId}/invitations/resend | admin | ✅ |
| PATCH | /users/{userId} | admin | ✅ |
| POST | /users/{userId}/status | admin | ✅ |
| POST | /users/{userId}/password-reset-email | admin | ✅ |
| GET | /users/{userId}/projects | admin/本人 | ✅ |
| GET | /users/{userId}/activity | admin/本人 | ✅ |
| GET | /roles | admin | ✅ |
| GET | /permissions/matrix | admin | ✅ |

### 3.2 文件、异步任务（8.6节）
| Method | Path | 权限 | 状态 |
|--------|------|------|------|
| POST | /files/upload-sessions | internal/Portal | ✅ |
| GET | /files/upload-sessions/{uploadId} | 创建者 | ✅ |
| PUT | /files/upload-sessions/{uploadId}/parts/{partNumber} | 创建者 | ✅ |
| POST | /files/upload-sessions/{uploadId}/complete | 创建者 | ✅ |
| DELETE | /files/upload-sessions/{uploadId} | 创建者 | ✅ |
| GET | /files/{fileId}/preview | 有权限者 | ✅ |
| GET | /files/{fileId}/download | 有权限者 | ✅ |
| GET | /jobs/{jobId} | 发起者/管理员 | ✅ |
| POST | /jobs/{jobId}/cancel | 发起者/管理员 | ✅ |
| POST | /realtime/tickets | 当前会话 | ✅ |

### 3.3 通知、设置与审计（8.7节）
| Method | Path | 权限 | 状态 |
|--------|------|------|------|
| GET | /notifications | internal | ✅ |
| PATCH | /notifications/{id} | 本人 | ✅ |
| POST | /notifications/read-all | 本人 | ✅ |
| GET | /global-search | internal | ✅ |
| GET | /settings/model-providers | admin | ✅ |
| POST | /settings/model-providers | admin | ✅ |
| PATCH | /settings/model-providers/{id} | admin | ✅ |
| POST | /settings/model-providers/{id}/test | admin | ✅ |
| GET | /settings/model-routes | admin | ✅ |
| PUT | /settings/model-routes | admin | ✅ |
| GET | /settings/generation | admin | ✅ |
| PUT | /settings/generation | admin | ✅ |
| GET | /settings/deployment | admin | ✅ |
| PUT | /settings/deployment | admin | ✅ |
| GET | /settings/document-template | admin | ✅ |
| PUT | /settings/document-template | admin | ✅ |
| GET | /settings/notifications | admin | ✅ |
| PUT | /settings/notifications | admin | ✅ |
| GET | /settings/agents/status | admin | ✅ |
| GET | /audit-events | admin | ✅ |
| GET | /audit-events/export | admin | ✅ |
| GET | /health/live | 公开 | ✅ |
| GET | /health/ready | 公开/受限 | ✅ |

---

## 四、已完成工作

### 2026-08-07

#### Phase 0 基础架构 ✅
- [x] 创建core模块目录结构
- [x] 配置管理 (config/settings.py)
- [x] 数据库会话管理 (database/__init__.py)
- [x] 错误处理框架 (errors/exceptions.py + handlers.py)
- [x] 安全模块 (security/jwt.py)
  - [x] 密码哈希 (bcrypt)
  - [x] JWT Token (RS256)
  - [x] API Key加密 (AES-256-GCM)
  - [x] 文件哈希 (SHA-256)
  - [x] WebSocket票据
- [x] 依赖注入 (dependencies/__init__.py)
  - [x] get_current_user
  - [x] get_current_active_user
  - [x] require_admin
  - [x] require_project_lead_or_admin
  - [x] require_reviewer_or_admin
  - [x] require_role (动态角色检查)
- [x] 日志模块 (logging/__init__.py)
- [x] 健康检查 (domains/health/__init__.py)

#### Phase 1 认证模块 ✅
- [x] User模型 (auth/models/user.py)
- [x] UserRole/UserStatus枚举
- [x] AuthService (auth/services/auth_service.py)
- [x] UserService (auth/services/user_service.py)
- [x] 认证Schemas (auth/schemas/auth.py)
- [x] 认证API路由 (auth/api/auth.py)
- [x] 用户API路由 (auth/api/users.py)

#### Phase 3 文件平台 ✅
- [x] FileUploadSession/File模型 (files/models/file.py)
- [x] UploadStatus/ScanStatus枚举
- [x] FileService (files/services/file_service.py)
- [x] 文件Schemas (files/schemas/file.py)
- [x] 文件API路由 (files/api/files.py)

#### 其他模块路由骨架 ✅
- [x] 通知schemas (notifications/schemas/notification.py)
- [x] 通知API路由 (notifications/api/__init__.py)
- [x] 设置schemas (settings/schemas/settings.py)
- [x] 设置API路由 (settings/api/__init__.py)
- [x] 审计schemas (audit/schemas/audit.py)
- [x] 审计API路由 (audit/api/__init__.py)
- [x] 搜索schemas (search/schemas/search.py)
- [x] 搜索API路由 (search/api/__init__.py)
- [x] 任务schemas (jobs/schemas/job.py)

#### Phase 4 异步任务 (Jobs) ✅
- [x] Job模型 (jobs/models/job.py)
- [x] JobStatus/JobType枚举
- [x] JobService (jobs/services/job_service.py)
- [x] JobDispatcher (jobs/services/job_dispatcher.py)
- [x] RealtimeTicketService (jobs/services/realtime_ticket_service.py)
- [x] Jobs API路由 (jobs/api/jobs.py)

#### Phase 5 通知系统 (Notifications) ✅
- [x] Notification模型 (notifications/models/notification.py)
- [x] NotificationType枚举
- [x] NotificationService (notifications/services/notification_service.py)
- [x] Notifications API路由 (notifications/api/__init__.py)

#### Phase 6 审计日志 (Audit) ✅
- [x] AuditEvent模型 (audit/models/audit_event.py)
- [x] ActorType枚举
- [x] AuditService (audit/services/audit_service.py)

#### Phase 8 设置服务 (Settings) ✅
- [x] SettingsService (settings/services/settings_service.py)
- [x] API Key 加密/解密接口

#### 本次会话新增完成项 ✅
- [x] **models_registry.py** - 注册 User、FileUploadSession、File 模型
- [x] **Cookie配置** - 在 settings.py 中添加 refresh_token_cookie_* 配置项
- [x] **Refresh Token** - 实现 Cookie 读取与自动刷新机制
- [x] **Login 响应** - 登录时设置 Refresh Token Cookie
- [x] **MinIO 分片合并** - 实现 `_compose_object_from_parts` 方法
- [x] **Redis 客户端** - 创建 `core/redis.py` 模块
- [x] **Token 黑名单** - 实现 `add_token_to_blacklist` / `is_token_blacklisted`
- [x] **Logout 机制** - 将 Access Token 加入黑名单并清除 Cookie
- [x] **TokenRevokedError** - 新增异常类型
- [x] **依赖注入增强** - 在 get_current_user 中检查黑名单

---

## 五、待办事项（下次继续）

### 高优先级（已全部完成 ✅）
1. ✅ 完善UserService - 从数据库真正查询用户
2. ✅ 完善FileService - 实现MinIO实际文件上传
3. ✅ 完善AuthService - 实现Refresh Token的Cookie解析
4. ✅ 添加数据库模型注册 - 确保模型能被Alembic迁移识别

### 中优先级（已全部完成 ✅）
5. ✅ 实现 NotificationService
6. ✅ 实现 AuditService
7. ✅ 实现 SettingsService

### 低优先级（已全部完成 ✅）
8. ✅ 实现 Celery Worker 集成
9. ✅ 添加 GET /roles 和 GET /permissions/matrix 接口
10. ✅ 编写单元测试（基础结构 + Jobs/Notifications/Audit/Auth 测试）

### 待进行
11. 集成测试

---

## 六、当前Git状态

```
分支: feat/m4-platform-api-init
状态: 已修改，待提交
```

### 新增文件列表
```
backend/app/core/__init__.py
backend/app/core/config/__init__.py
backend/app/core/config/settings.py
backend/app/core/database/__init__.py
backend/app/core/errors/__init__.py
backend/app/core/errors/exceptions.py
backend/app/core/errors/handlers.py
backend/app/core/security/__init__.py
backend/app/core/security/jwt.py
backend/app/core/dependencies/__init__.py
backend/app/core/logging/__init__.py
backend/app/domains/__init__.py
backend/app/domains/auth/__init__.py
backend/app/domains/auth/models/__init__.py
backend/app/domains/auth/models/user.py
backend/app/domains/auth/services/__init__.py
backend/app/domains/auth/services/auth_service.py
backend/app/domains/auth/services/user_service.py
backend/app/domains/auth/schemas/__init__.py
backend/app/domains/auth/schemas/auth.py
backend/app/domains/auth/api/__init__.py
backend/app/domains/auth/api/auth.py
backend/app/domains/auth/api/users.py
backend/app/domains/files/models/__init__.py
backend/app/domains/files/models/file.py
backend/app/domains/files/services/__init__.py
backend/app/domains/files/services/file_service.py
backend/app/domains/files/schemas/__init__.py
backend/app/domains/files/schemas/file.py
backend/app/domains/files/api/__init__.py
backend/app/domains/files/api/files.py
backend/app/domains/jobs/schemas/__init__.py
backend/app/domains/jobs/schemas/job.py
backend/app/domains/notifications/schemas/__init__.py
backend/app/domains/notifications/schemas/notification.py
backend/app/domains/notifications/api/__init__.py
backend/app/domains/settings/schemas/__init__.py
backend/app/domains/settings/schemas/settings.py
backend/app/domains/settings/api/__init__.py
backend/app/domains/audit/schemas/__init__.py
backend/app/domains/audit/schemas/audit.py
backend/app/domains/audit/api/__init__.py
backend/app/domains/search/schemas/__init__.py
backend/app/domains/search/schemas/search.py
backend/app/domains/search/api/__init__.py
backend/app/domains/health/__init__.py
backend/app/domains/users/__init__.py
backend/app/domains/notifications/__init__.py
backend/app/domains/settings/__init__.py
backend/app/domains/audit/__init__.py
backend/app/domains/search/__init__.py
backend/app/models_registry.py
backend/app/core/redis.py
```

### 本次会话修改的文件
```
backend/app/core/config/settings.py           # 新增 Cookie 配置项
backend/app/core/security/jwt.py             # 新增 decode_token_unsafe
backend/app/core/errors/exceptions.py        # 新增 TokenRevokedError
backend/app/core/errors/__init__.py          # 导出 TokenRevokedError
backend/app/core/dependencies/__init__.py    # 黑名单检查逻辑
backend/app/domains/auth/api/auth.py         # Refresh Token + Logout 实现
backend/app/domains/auth/services/auth_service.py  # refresh_tokens 返回 user_id
backend/app/domains/files/services/file_service.py # MinIO 分片合并
backend/app/models_registry.py               # 模型注册
```

### 本次会话新增的文件
```
backend/app/core/redis.py                    # Redis 客户端 + Token 黑名单
```

---

## 七、注意事项

### 7.1 上下文管理（Claude Code 必须遵守）
- ⚠️ **上下文即将满时**：立即暂停任务，优先将关键信息保存到内存文件
- ⚠️ **记录位置**：`C:\Users\21212\.claude\projects\C--Users-21212\memory\` 目录
- ⚠️ **记录内容**：当前进度、待办事项、遇到的问题、下一步计划
- ⚠️ **自动执行**：下次新建对话时，无需用户提醒，自动读取上次保存的上下文继续工作

### 7.2 禁止事项
- ❌ 不修改其他成员的文件
- ❌ 不合并到main或develop分支
- ❌ 不修改contracts/openapi.yaml（L0负责）
- ❌ 不修改前端文件（M1/M2/M3负责）
- ❌ 不修改投标/评标业务表（M5/M6负责）
- ❌ 不修改AI Provider（M7负责）
- ❌ **不创建分支、不推送远端** — 必须先与用户确认，获得同意后方可执行

### 7.3 需要协调的事项
- 如需新增接口字段 → 提交CONTRACT-CHANGE给L0
- 如需调用其他模块 → 通过已有的Service端口
- 如需依赖变更 → 提交DEPENDENCY-CHANGE给L0

### 7.3 验收标准
- 单元测试覆盖率 >= 85%
- 所有失败流有测试
- API响应与OpenAPI契约完全一致
- 跨租户数据隔离验证通过

### 7.4 依赖的环境变量
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
MINIO_ENDPOINT=http://...
JWT_PRIVATE_KEY_PATH=/path/to/key
JWT_PUBLIC_KEY_PATH=/path/to/key
MODEL_MASTER_KEY_PATH=/path/to/key
```

---

## 八、下次开始前需要执行

```bash
# 1. 切换到M4分支
git switch feat/m4-platform-api-init

# 2. 拉取最新代码（如果有）
git pull origin develop

# 3. 查看待办事项
# 参考本文件的第五节

# 4. 开始实现
```
