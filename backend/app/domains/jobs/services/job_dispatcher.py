"""任务调度器.

提供统一的任务创建和调度接口，供 M5/M6/M7 调用。
"""

from typing import Any
from uuid import UUID

from app.core.database import get_db_context
from app.domains.jobs.models.job import Job, JobType
from app.domains.jobs.services.job_service import JobService


class JobDispatcher:
    """任务调度器.

    使用示例:
        dispatcher = JobDispatcher()
        job = await dispatcher.dispatch(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
            input_data={"file_id": str(file_id)},
            project_id=project_id,
        )
    """

    async def dispatch(
        self,
        user_id: UUID,
        tenant_id: UUID,
        job_type: JobType,
        input_data: dict[str, Any] | None = None,
        project_id: UUID | None = None,
    ) -> Job:
        """调度一个新任务.

        Args:
            user_id: 创建者ID
            tenant_id: 租户ID
            job_type: 任务类型
            input_data: 输入参数
            project_id: 关联项目ID

        Returns:
            创建的任务对象
        """
        async with get_db_context() as db:
            service = JobService(db)
            job = await service.create_job(
                user_id=user_id,
                tenant_id=tenant_id,
                job_type=job_type,
                input_data=input_data,
                project_id=project_id,
            )
            # 返回轻量级字典，避免会话关闭后访问延迟加载属性
            return job

    async def dispatch_and_start(
        self,
        user_id: UUID,
        tenant_id: UUID,
        job_type: JobType,
        input_data: dict[str, Any] | None = None,
        project_id: UUID | None = None,
    ) -> Job:
        """调度任务并立即标记为运行中.

        适用于不需要 Celery Worker 的同步任务。

        Args:
            user_id: 创建者ID
            tenant_id: 租户ID
            job_type: 任务类型
            input_data: 输入参数
            project_id: 关联项目ID

        Returns:
            创建的任务对象（已标记为 RUNNING）
        """
        async with get_db_context() as db:
            service = JobService(db)
            job = await service.create_job(
                user_id=user_id,
                tenant_id=tenant_id,
                job_type=job_type,
                input_data=input_data,
                project_id=project_id,
            )
            job = await service.mark_job_started(job.id)
            return job


# 全局调度器实例
job_dispatcher = JobDispatcher()


async def dispatch_job(
    user_id: UUID,
    tenant_id: UUID,
    job_type: JobType,
    input_data: dict[str, Any] | None = None,
    project_id: UUID | None = None,
) -> Job:
    """快捷函数：调度任务.

    Args:
        user_id: 创建者ID
        tenant_id: 租户ID
        job_type: 任务类型
        input_data: 输入参数
        project_id: 关联项目ID

    Returns:
        创建的任务对象
    """
    return await job_dispatcher.dispatch(
        user_id=user_id,
        tenant_id=tenant_id,
        job_type=job_type,
        input_data=input_data,
        project_id=project_id,
    )
