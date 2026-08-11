"""任务API路由.

实现任务相关接口：
- GET /jobs/{jobId} - 获取任务详情
- POST /jobs/{jobId}/cancel - 取消任务
- POST /realtime/tickets - 获取WebSocket票据
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.http import success_response
from app.domains.jobs.mappers import job_to_data
from app.domains.jobs.schemas.job import RealtimeTicketRequest
from app.domains.jobs.services.job_dispatcher import job_dispatcher
from app.domains.jobs.services.job_service import JobService

router = APIRouter(tags=["任务"])


@router.get(
    "/jobs/{job_id}",
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
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
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
        return success_response(job_to_data(job), request=request)
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
    status_code=202,
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
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
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
        return success_response(job_to_data(cancelled_job), request=request, status_code=202)
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
    summary="获取WebSocket票据",
    description="获取一次性票据用于建立WebSocket连接。票据有效期30秒。",
    responses={
        200: {"description": "票据已生成"},
        401: {"description": "未登录"},
    },
)
async def create_realtime_ticket(
    request: RealtimeTicketRequest,
    http_request: Request,
    current_user: AuthenticatedUser,
) -> JSONResponse:
    """获取WebSocket票据."""
    from app.domains.jobs.services.realtime_ticket_service import realtime_ticket_service

    ticket, expires_at = await realtime_ticket_service.create_ticket(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
        channel=request.channel,
    )

    return success_response(
        {"ticket": ticket, "expiresAt": expires_at},
        request=http_request,
    )
