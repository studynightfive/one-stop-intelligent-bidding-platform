# M4 公共平台后端 - Service 使用指南

> 版本：1.0.0
> 更新时间：2026-08-07

---

## 一、概述

M4 是系统的公共平台后端，提供以下核心服务供 M5/M6/M7 调用：

| 服务 | 用途 |
|------|------|
| JobDispatcher | 异步任务管理 |
| NotificationService | 通知系统 |
| AuditService | 审计日志 |
| SettingsService | 系统设置 |
| FileService | 文件管理 |

---

## 二、JobDispatcher - 异步任务服务

### 2.1 功能说明

用于创建和管理异步任务，支持进度跟踪、取消等操作。

### 2.2 导入方式

```python
from app.domains.jobs.services.job_dispatcher import job_dispatcher, dispatch_job
from app.domains.jobs.models.job import JobType, JobStatus
```

### 2.3 任务类型枚举

```python
class JobType(str, Enum):
    FILE_SCAN = "file_scan"           # 文件扫描
    FILE_IMPORT = "file_import"        # 文件导入
    DOCUMENT_GENERATION = "document_generation"  # 文档生成
    AI_ANALYSIS = "ai_analysis"        # AI分析
    EXPORT = "export"                 # 导出
    OTHER = "other"                    # 其他
```

### 2.4 使用示例

```python
# 创建异步任务
job = await job_dispatcher.dispatch(
    user_id=user_id,           # UUID - 创建者ID
    tenant_id=tenant_id,        # UUID - 租户ID
    job_type=JobType.AI_ANALYSIS,
    input_data={
        "content": "待分析内容",
        "analysis_type": "summary",
    },
    project_id=project_id,      # 可选，关联项目ID
)
print(f"任务已创建: {job.id}")
```

### 2.5 Job 模型字段

```python
class Job:
    id: UUID              # 任务ID
    tenant_id: UUID       # 租户ID
    user_id: UUID         # 创建者ID
    project_id: UUID      # 关联项目ID
    type: JobType         # 任务类型
    status: JobStatus     # 状态
    progress_percent: int  # 进度 0-100
    current_step: str     # 当前步骤
    input_data: dict      # 输入参数
    result: dict          # 结果数据
    error: dict           # 错误信息
    created_at: datetime # 创建时间
    started_at: datetime  # 开始时间
    completed_at: datetime # 完成时间
```

---

## 三、NotificationService - 通知服务

### 3.1 功能说明

用于向用户发送站内通知，支持多种通知类型。

### 3.2 导入方式

```python
from app.domains.notifications.services.notification_service import NotificationService
from app.domains.notifications.models.notification import NotificationType
```

### 3.3 通知类型枚举

```python
class NotificationType(str, Enum):
    SYSTEM = "system"      # 系统通知
    TASK = "task"         # 任务通知
    REVIEW = "review"      # 评审通知
    APPROVAL = "approval"  # 审批通知
    MESSAGE = "message"     # 消息通知
    ASSIGNMENT = "assignment"  # 分配通知
```

### 3.4 使用示例

```python
# 在 API 路由中使用
notification_service = NotificationService(db)

# 方式1：创建通知
notification = await notification_service.create_notification(
    user_id=user_id,
    tenant_id=tenant_id,
    notification_type=NotificationType.TASK,
    title="任务完成",
    content="文件扫描任务已完成，请查看结果。",
    resource_type="job",
    resource_id=job_id,
    extra_data={"score": 95},
)

# 方式2：快捷方法 - 创建系统通知
await notification_service.create_system_notification(
    user_id=user_id,
    tenant_id=tenant_id,
    title="系统消息",
    content="您的账号已审核通过。",
)

# 方式3：快捷方法 - 创建任务通知
await notification_service.create_task_notification(
    user_id=user_id,
    tenant_id=tenant_id,
    title="任务通知",
    content="您有一个新任务待处理。",
    task_id=task_id,
)

# 批量发送通知
user_ids = [uuid1, uuid2, uuid3]
for uid in user_ids:
    await notification_service.create_notification(
        user_id=uid,
        tenant_id=tenant_id,
        notification_type=NotificationType.SYSTEM,
        title="批量通知",
        content="这是一条批量通知。",
    )
```

---

## 四、AuditService - 审计服务

### 4.1 功能说明

用于记录所有业务操作，提供 append-only 的审计日志。

### 4.2 导入方式

```python
from app.domains.audit.services.audit_service import AuditService
from app.domains.audit.models.audit_event import ActorType
```

### 4.3 操作者类型枚举

```python
class ActorType(str, Enum):
    USER = "user"         # 用户操作
    SUPPLIER = "supplier" # 供应商操作
    SYSTEM = "system"      # 系统操作
```

### 4.4 使用示例

```python
# 在 API 路由中使用
audit_service = AuditService(db)

# 方式1：记录审计事件
await audit_service.log(
    tenant_id=tenant_id,
    aggregate_type="project",
    aggregate_id=project_id,
    actor_type=ActorType.USER,
    actor_id=user_id,
    actor_name="张三",
    action="create",
    summary="创建了新项目：招标管理系统",
    changes={
        "before": {},
        "after": {"name": "招标管理系统", "status": "draft"},
    },
    request_id=request.state.request_id,  # 请求追踪ID
    ip_address=request.client.host if request.client else None,
)

# 方式2：记录用户操作（快捷方法）
await audit_service.log_user_action(
    tenant_id=tenant_id,
    user_id=user_id,
    user_name="张三",
    aggregate_type="bid",
    aggregate_id=bid_id,
    action="submit",
    summary="提交了投标文件",
    changes={"status": ["draft", "submitted"]},
)

# 方式3：记录系统操作（快捷方法）
await audit_service.log_system_action(
    tenant_id=tenant_id,
    aggregate_type="job",
    aggregate_id=job_id,
    action="complete",
    summary="自动任务完成",
)

# 查询资源的操作历史
history = await audit_service.get_resource_history(
    tenant_id=tenant_id,
    aggregate_type="project",
    aggregate_id=project_id,
)
for event in history:
    print(f"{event.actor_name} {event.action} at {event.created_at}")
```

### 4.5 常用操作类型

建议统一使用以下操作类型：

| 操作 | 说明 |
|------|------|
| `create` | 创建资源 |
| `update` | 更新资源 |
| `delete` | 删除资源 |
| `submit` | 提交 |
| `approve` | 审批通过 |
| `reject` | 审批拒绝 |
| `cancel` | 取消 |
| `assign` | 分配 |
| `notify` | 通知 |
| `login` | 登录 |
| `logout` | 登出 |

---

## 五、SettingsService - 设置服务

### 5.1 功能说明

用于管理系统设置，特别是 AI 模型 API 密钥的加密存储。

### 5.2 导入方式

```python
from app.domains.settings.services.settings_service import SettingsService, get_model_api_key
```

### 5.3 使用示例

```python
# 方式1：使用 Service 类
settings_service = SettingsService(db)

# 加密 API Key
encrypted = settings_service.encrypt_key("sk-xxx")
# 保存到数据库

# 解密 API Key
plain_key = settings_service.decrypt_key(encrypted)

# 脱敏显示
masked = settings_service.mask_key("sk-xxx")  # 返回 "sk-•••••xxx"

# 方式2：快捷函数（需要 M7 实现 ModelProvider 模型后使用）
api_key = await get_model_api_key(db, provider_id)
```

---

## 六、FileService - 文件服务

### 6.1 功能说明

用于文件上传、下载、预览等操作。集成 MinIO 对象存储。

### 6.2 导入方式

```python
from app.domains.files.services.file_service import FileService
from app.domains.files.models.file import UploadStatus, ScanStatus
```

### 6.2 使用示例

```python
# 在 API 路由中使用
file_service = FileService(db)

# 创建上传会话
session = await file_service.create_upload_session(
    user_id=user_id,
    tenant_id=tenant_id,
    file_name="document.pdf",
    file_size=1024000,
    content_type="application/pdf",
)

# 上传完成后完成会话
file = await file_service.complete_upload(
    session_id=session.id,
    parts=parts,  # 分片列表
    sha256_hash="abc123...",
)

# 获取下载 URL（签名 URL）
download_url = await file_service.get_download_url(file.id, expires_minutes=60)

# 获取预览 URL
preview_url = await file_service.get_preview_url(file.id, expires_minutes=30)
```

---

## 七、完整使用示例

### 7.1 M5/M6 投标模块示例

```python
"""M5 投标模块 - 提交投标时的完整流程"""

from uuid import UUID
from fastapi import APIRouter, Depends

from app.core.dependencies import AuthenticatedUser, DBSession
from app.domains.jobs.services.job_dispatcher import job_dispatcher
from app.domains.jobs.models.job import JobType
from app.domains.notifications.services.notification_service import NotificationService
from app.domains.notifications.models.notification import NotificationType
from app.domains.audit.services.audit_service import AuditService
from app.domains.audit.models.audit_event import ActorType


router = APIRouter(prefix="/bids", tags=["投标"])


@router.post("/{bid_id}/submit")
async def submit_bid(
    bid_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
):
    tenant_id = UUID(current_user["tenant_id"])
    user_id = UUID(current_user["id"])

    # 1. 创建 AI 文档分析任务
    analysis_job = await job_dispatcher.dispatch(
        user_id=user_id,
        tenant_id=tenant_id,
        job_type=JobType.AI_ANALYSIS,
        input_data={
            "bid_id": str(bid_id),
            "analysis_type": "compliance_check",
        },
    )

    # 2. 发送通知给项目负责人
    notification_service = NotificationService(db)
    await notification_service.create_task_notification(
        user_id=project_lead_id,
        tenant_id=tenant_id,
        title="新投标已提交",
        content=f"供应商 {supplier_name} 提交了投标文件，等待审核。",
        task_id=bid_id,
    )

    # 3. 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_user_action(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name=current_user.get("name", "未知用户"),
        aggregate_type="bid",
        aggregate_id=bid_id,
        action="submit",
        summary=f"提交投标：{bid_name}",
        changes={"status": ["draft", "submitted"]},
    )

    return {
        "message": "投标已提交",
        "analysis_job_id": str(analysis_job.id),
    }
```

---

## 八、错误处理

所有 M4 服务可能抛出的异常：

```python
from app.core.errors import (
    NotFoundError,      # 资源不存在
    ForbiddenError,    # 无权访问
    ValidationError,    # 数据验证失败
    AuthenticationError,  # 认证失败
)

# 使用示例
try:
    job = await job_service.get_job_for_user(...)
except NotFoundError:
    raise HTTPException(status_code=404, detail="任务不存在")
except ForbiddenError:
    raise HTTPException(status_code=403, detail="无权访问此任务")
```

---

## 九、依赖要求

使用 M4 服务需要在 `pyproject.toml` 中添加依赖：

```toml
dependencies = [
    "fastapi>=0.115.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.0.0",
]
```

---

## 十、注意事项

1. **数据库会话** - 所有 Service 需要传入 `AsyncSession` 对象
2. **租户隔离** - 所有操作都需要 `tenant_id` 参数确保多租户隔离
3. **权限检查** - M4 只负责数据层面，API 层权限由调用方检查
4. **事务管理** - Service 内部自动管理事务，外部无需额外处理
