"""任务服务.

提供任务的创建、查询、取消等操作。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.domains.jobs.models.job import Job, JobStatus, JobType


class JobService:
    """任务服务."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        user_id: UUID,
        tenant_id: UUID,
        job_type: JobType,
        input_data: dict[str, Any] | None = None,
        project_id: UUID | None = None,
    ) -> Job:
        """创建新任务.

        Args:
            user_id: 创建者ID
            tenant_id: 租户ID
            job_type: 任务类型
            input_data: 输入参数
            project_id: 关联项目ID

        Returns:
            创建的任务对象
        """
        job = Job(
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            type=job_type,
            status=JobStatus.QUEUED,
            input_data=input_data,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job_by_id(self, job_id: UUID) -> Job | None:
        """根据ID获取任务.

        Args:
            job_id: 任务ID

        Returns:
            任务对象或None
        """
        stmt = select(Job).where(Job.id == job_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_job_for_user(
        self,
        job_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        is_admin: bool = False,
    ) -> Job:
        """获取任务（带权限检查）.

        Args:
            job_id: 任务ID
            user_id: 当前用户ID
            tenant_id: 当前租户ID
            is_admin: 是否管理员

        Returns:
            任务对象

        Raises:
            NotFoundError: 任务不存在
            PermissionDeniedError: 无权访问
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            raise NotFoundError(message="任务不存在")

        # 权限检查：同租户且是创建者或管理员
        if job.tenant_id != tenant_id:
            raise ForbiddenError(message="无权访问此任务")

        if not is_admin and job.user_id != user_id:
            raise ForbiddenError(message="无权访问此任务")

        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """查询任务列表.

        Args:
            tenant_id: 租户ID
            user_id: 筛选特定用户的任务（None表示全部）
            status: 筛选状态
            job_type: 筛选类型
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (任务列表, 总数)
        """
        # 基础查询
        conditions = [Job.tenant_id == tenant_id]

        if user_id:
            conditions.append(Job.user_id == user_id)
        if status:
            conditions.append(Job.status == status)
        if job_type:
            conditions.append(Job.type == job_type)

        # 查询总数
        from sqlalchemy import func as sql_func

        count_stmt = select(sql_func.count(Job.id)).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # 查询列表
        stmt = select(Job).where(*conditions).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        jobs = list(result.scalars().all())

        return jobs, total

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress_percent: int | None = None,
        current_step: str | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> Job:
        """更新任务状态.

        Args:
            job_id: 任务ID
            status: 新状态
            progress_percent: 进度百分比
            current_step: 当前步骤
            result: 结果数据
            error: 错误信息

        Returns:
            更新后的任务对象

        Raises:
            NotFoundError: 任务不存在
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            raise NotFoundError(message="任务不存在")

        job.status = status

        if progress_percent is not None:
            job.progress_percent = progress_percent
        if current_step is not None:
            job.current_step = current_step
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error

        # 设置时间戳
        now = datetime.now(UTC)
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = now
        if status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
            job.completed_at = now

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_job_started(self, job_id: UUID) -> Job:
        """标记任务开始执行.

        Args:
            job_id: 任务ID

        Returns:
            更新后的任务对象
        """
        return await self.update_job_status(
            job_id,
            JobStatus.RUNNING,
            progress_percent=0,
            current_step="任务开始执行",
        )

    async def mark_job_progress(
        self,
        job_id: UUID,
        progress_percent: int,
        current_step: str,
    ) -> Job:
        """更新任务进度.

        Args:
            job_id: 任务ID
            progress_percent: 进度百分比
            current_step: 当前步骤

        Returns:
            更新后的任务对象
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            raise NotFoundError(message="任务不存在")

        job.progress_percent = min(max(progress_percent, 0), 100)
        job.current_step = current_step

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_job_succeeded(
        self,
        job_id: UUID,
        result: dict[str, Any] | None = None,
    ) -> Job:
        """标记任务成功.

        Args:
            job_id: 任务ID
            result: 结果数据

        Returns:
            更新后的任务对象
        """
        return await self.update_job_status(
            job_id,
            JobStatus.SUCCEEDED,
            progress_percent=100,
            current_step="任务已完成",
            result=result,
        )

    async def mark_job_failed(
        self,
        job_id: UUID,
        error: dict[str, Any] | None = None,
    ) -> Job:
        """标记任务失败.

        Args:
            job_id: 任务ID
            error: 错误信息

        Returns:
            更新后的任务对象
        """
        return await self.update_job_status(
            job_id,
            JobStatus.FAILED,
            current_step="任务执行失败",
            error=error,
        )

    async def cancel_job(self, job_id: UUID) -> Job:
        """取消任务.

        Args:
            job_id: 任务ID

        Returns:
            更新后的任务对象

        Raises:
            NotFoundError: 任务不存在
            ValidationError: 任务不可取消
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            raise NotFoundError(message="任务不存在")

        if not job.is_cancellable:
            raise ValidationError(
                message=f"任务状态为 {job.status.value}，无法取消",
            )

        job.status = JobStatus.CANCELLED
        job.is_cancelled = True
        job.cancelled_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def bind_celery_task_id(self, job_id: UUID, celery_task_id: str) -> None:
        """绑定 Celery 任务ID.

        Args:
            job_id: 任务ID
            celery_task_id: Celery任务ID
        """
        job = await self.get_job_by_id(job_id)
        if job:
            job.celery_task_id = celery_task_id
            await self.db.commit()
