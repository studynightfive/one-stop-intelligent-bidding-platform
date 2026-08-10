"""任务API路由.

实现任务相关接口：
- GET /jobs/{jobId} - 获取任务详情
- POST /jobs/{jobId}/cancel - 取消任务
- POST /realtime/tickets - 获取WebSocket票据
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.domains.jobs.models.job import Job
from app.domains.jobs.schemas.job import (
    JobCancelResponse,
    JobResponse,
    RealtimeTicketRequest,
    RealtimeTicketResponse,
)
from app.domains.jobs.services.job_dispatcher import job_dispatcher
from app.domains.jobs.services.job_service import JobService

router = APIRouter(tags=["任务"])


def _job_to_response(job: Job) -> JobResponse:
    """将Job模型转换为响应模型."""
    return JobResponse(
        id=job.id,
        type=job.type.value,
        status=job.status.value,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="获取任务详情",
    description="获取指定任务的详细信息。只能获取当前用户或同租户管理员创建的任务。",
    responses={
        200: {"description": "任务详情"},
        403: {"description": "无权访问"},
        404: {"description": "任务不存在"},
    },
)
async def get_job(
    job_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JobResponse:
    """获取任务详情."""
    job_service = JobService(db)

    try:
        job = await job_service.get_job_for_user(
            job_id=job_id,
            user_id=UUID(current_user["id"]),
            tenant_id=UUID(current_user["tenant_id"]),
            is_admin=current_user.get("role") == "admin",
        )
        if getattr(job, "celery_task_id", None):
            refreshed = await job_dispatcher.refresh(job, service=job_service)
            if refreshed is not None:
                job = refreshed
        return _job_to_response(job)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobCancelResponse,
    summary="取消任务",
    description="取消一个正在排队或执行的任务。只能取消自己创建的任务或管理员可以取消任何任务。",
    responses={
        200: {"description": "任务已取消"},
        400: {"description": "任务无法取消"},
        403: {"description": "无权操作"},
        404: {"description": "任务不存在"},
    },
)
async def cancel_job(
    job_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JobCancelResponse:
    """取消任务."""
    job_service = JobService(db)

    try:
        # 先获取任务进行权限检查
        await job_service.get_job_for_user(
            job_id=job_id,
            user_id=UUID(current_user["id"]),
            tenant_id=UUID(current_user["tenant_id"]),
            is_admin=current_user.get("role") == "admin",
        )

        # 执行取消
        cancelled_job = await job_service.cancel_job(job_id)
        await job_dispatcher.revoke(getattr(cancelled_job, "celery_task_id", None))
        return JobCancelResponse(
            id=cancelled_job.id,
            status=cancelled_job.status.value,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/realtime/tickets",
    response_model=RealtimeTicketResponse,
    summary="获取WebSocket票据",
    description="获取一次性票据用于建立WebSocket连接。票据有效期30秒。",
    responses={
        200: {"description": "票据已生成"},
        401: {"description": "未登录"},
    },
)
async def create_realtime_ticket(
    request: RealtimeTicketRequest,
    current_user: AuthenticatedUser,
) -> RealtimeTicketResponse:
    """获取WebSocket票据."""
    from app.domains.jobs.services.realtime_ticket_service import realtime_ticket_service

    ticket, expires_at = await realtime_ticket_service.create_ticket(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
        channel=request.channel,
    )

    return RealtimeTicketResponse(
        ticket=ticket,
        expires_at=expires_at,
    )
