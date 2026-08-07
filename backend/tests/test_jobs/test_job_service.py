"""Job 模型和服务测试."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.jobs.models.job import Job, JobStatus, JobType
from app.domains.jobs.services.job_service import JobService


class TestJobModel:
    """Job 模型测试."""

    def test_job_status_enum_values(self) -> None:
        """测试 JobStatus 枚举值."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.SUCCEEDED.value == "succeeded"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_type_enum_values(self) -> None:
        """测试 JobType 枚举值."""
        assert JobType.FILE_SCAN.value == "file_scan"
        assert JobType.FILE_IMPORT.value == "file_import"
        assert JobType.DOCUMENT_GENERATION.value == "document_generation"
        assert JobType.AI_ANALYSIS.value == "ai_analysis"
        assert JobType.EXPORT.value == "export"
        assert JobType.OTHER.value == "other"

    def test_job_is_finished_property(self) -> None:
        """测试 is_finished 属性."""
        job = Job(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=JobType.OTHER,
            status=JobStatus.QUEUED,
        )
        assert not job.is_finished

        job.status = JobStatus.RUNNING
        assert not job.is_finished

        job.status = JobStatus.SUCCEEDED
        assert job.is_finished

        job.status = JobStatus.FAILED
        assert job.is_finished

        job.status = JobStatus.CANCELLED
        assert job.is_finished

    def test_job_is_cancellable_property(self) -> None:
        """测试 is_cancellable 属性."""
        job = Job(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=JobType.OTHER,
            status=JobStatus.QUEUED,
        )
        assert job.is_cancellable

        job.status = JobStatus.RUNNING
        assert job.is_cancellable

        job.status = JobStatus.SUCCEEDED
        assert not job.is_cancellable

        job.status = JobStatus.FAILED
        assert not job.is_cancellable

        job.is_cancelled = True
        assert not job.is_cancellable

    def test_job_to_dict(self) -> None:
        """测试 to_dict 方法."""
        job_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        job = Job(
            id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            type=JobType.FILE_SCAN,
            status=JobStatus.QUEUED,
            progress_percent=0,
            current_step="等待中",
        )

        result = job.to_dict()

        assert result["id"] == str(job_id)
        assert result["tenant_id"] == str(tenant_id)
        assert result["user_id"] == str(user_id)
        assert result["type"] == "file_scan"
        assert result["status"] == "queued"
        assert result["progress_percent"] == 0
        assert result["current_step"] == "等待中"


class TestJobService:
    """JobService 测试."""

    @pytest_asyncio.fixture
    async def job_service(self, db_session: AsyncSession) -> JobService:
        """创建 JobService 实例."""
        return JobService(db_session)

    @pytest.mark.asyncio
    async def test_create_job(self, job_service: JobService) -> None:
        """测试创建任务."""
        user_id = uuid4()
        tenant_id = uuid4()
        input_data = {"file_id": str(uuid4())}

        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
            input_data=input_data,
        )

        assert job.id is not None
        assert job.user_id == user_id
        assert job.tenant_id == tenant_id
        assert job.type == JobType.FILE_SCAN
        assert job.status == JobStatus.QUEUED
        assert job.progress_percent == 0
        assert job.input_data == input_data

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, job_service: JobService) -> None:
        """测试根据ID获取任务."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建任务
        created_job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.DOCUMENT_GENERATION,
        )

        # 查询任务
        fetched_job = await job_service.get_job_by_id(created_job.id)

        assert fetched_job is not None
        assert fetched_job.id == created_job.id
        assert fetched_job.type == JobType.DOCUMENT_GENERATION

    @pytest.mark.asyncio
    async def test_get_job_by_id_not_found(self, job_service: JobService) -> None:
        """测试查询不存在的任务."""
        job = await job_service.get_job_by_id(uuid4())
        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_status(self, job_service: JobService) -> None:
        """测试更新任务状态."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建任务
        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.AI_ANALYSIS,
        )

        # 更新状态
        updated_job = await job_service.update_job_status(
            job_id=job.id,
            status=JobStatus.RUNNING,
            progress_percent=50,
            current_step="正在分析...",
        )

        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.progress_percent == 50
        assert updated_job.current_step == "正在分析..."
        assert updated_job.started_at is not None

    @pytest.mark.asyncio
    async def test_mark_job_succeeded(self, job_service: JobService) -> None:
        """测试标记任务成功."""
        user_id = uuid4()
        tenant_id = uuid4()

        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.EXPORT,
        )

        result_data = {"download_url": "/files/export.xlsx"}
        completed_job = await job_service.mark_job_succeeded(
            job_id=job.id,
            result=result_data,
        )

        assert completed_job.status == JobStatus.SUCCEEDED
        assert completed_job.progress_percent == 100
        assert completed_job.result == result_data
        assert completed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_mark_job_failed(self, job_service: JobService) -> None:
        """测试标记任务失败."""
        user_id = uuid4()
        tenant_id = uuid4()

        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_IMPORT,
        )

        error_data = {"code": "IMPORT_ERROR", "message": "文件格式错误"}
        failed_job = await job_service.mark_job_failed(
            job_id=job.id,
            error=error_data,
        )

        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error == error_data
        assert failed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_job(self, job_service: JobService) -> None:
        """测试取消任务."""
        user_id = uuid4()
        tenant_id = uuid4()

        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
        )

        cancelled_job = await job_service.cancel_job(job.id)

        assert cancelled_job.status == JobStatus.CANCELLED
        assert cancelled_job.is_cancelled is True
        assert cancelled_job.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_already_finished_job(
        self,
        job_service: JobService,
    ) -> None:
        """测试取消已结束的任务（应失败）."""
        from app.core.errors import ValidationError

        user_id = uuid4()
        tenant_id = uuid4()

        job = await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.OTHER,
        )

        # 先标记为成功
        await job_service.mark_job_succeeded(job.id)

        # 尝试取消
        with pytest.raises(ValidationError):
            await job_service.cancel_job(job.id)

    @pytest.mark.asyncio
    async def test_list_jobs(self, job_service: JobService) -> None:
        """测试查询任务列表."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建多个任务
        for i in range(5):
            await job_service.create_job(
                user_id=user_id,
                tenant_id=tenant_id,
                job_type=JobType.OTHER,
            )

        # 查询列表
        jobs, total = await job_service.list_jobs(
            tenant_id=tenant_id,
            limit=10,
        )

        assert total == 5
        assert len(jobs) == 5

    @pytest.mark.asyncio
    async def test_list_jobs_with_filter(self, job_service: JobService) -> None:
        """测试带筛选条件的任务列表."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建不同类型的任务
        await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
        )
        await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
        )
        await job_service.create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            job_type=JobType.DOCUMENT_GENERATION,
        )

        # 按类型筛选
        jobs, total = await job_service.list_jobs(
            tenant_id=tenant_id,
            job_type=JobType.FILE_SCAN,
        )

        assert total == 2
        assert all(j.type == JobType.FILE_SCAN for j in jobs)
