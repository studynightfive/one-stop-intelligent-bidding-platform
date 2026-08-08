"""文件API路由.

实现文件上传相关接口：
- POST /files/upload-sessions - 创建上传会话
- GET /files/upload-sessions/{uploadId} - 查询上传会话
- PUT /files/upload-sessions/{uploadId}/parts/{partNumber} - 上传分片
- POST /files/upload-sessions/{uploadId}/complete - 完成上传
- DELETE /files/upload-sessions/{uploadId} - 取消上传
- GET /files/{fileId}/preview - 预览文件
- GET /files/{fileId}/download - 下载文件
"""

import secrets
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi import File as FastAPIFile

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import FileRejectedError, NotFoundError
from app.domains.files.schemas.file import (
    CompleteUploadRequest,
    FileResponse,
    FileUploadSessionResponse,
    PartUploadResponse,
)
from app.domains.files.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件平台"])


def _session_to_response(session: Any) -> FileUploadSessionResponse:
    """将会话模型转换为响应模型."""
    return FileUploadSessionResponse(
        id=session.id,
        file_name=session.file_name,
        size_bytes=session.size_bytes,
        part_size_bytes=session.part_size_bytes,
        total_parts=session.total_parts,
        uploaded_parts=session.uploaded_parts,
        status=session.status.value,
        expires_at=session.expires_at,
    )


def _file_to_response(file: Any) -> FileResponse:
    """将文件模型转换为响应模型."""
    return FileResponse(
        id=file.id,
        file_name=file.file_name,
        mime_type=file.mime_type,
        size_bytes=file.size_bytes,
        sha256=file.sha256,
        scan_status=file.scan_status.value,
        preview_url=None,  # TODO: 需要生成签名URL
        download_url=None,
        created_at=file.created_at,
    )


@router.post(
    "/upload-sessions",
    response_model=FileUploadSessionResponse,
    summary="创建上传会话",
    description="创建大文件分片上传会话，返回会话ID和分片信息。",
    responses={
        201: {"description": "会话创建成功"},
        400: {"description": "文件不符合要求"},
    },
)
async def create_upload_session(
    request: dict[str, Any],
    current_user: AuthenticatedUser,
    db: DBSession,
) -> FileUploadSessionResponse:
    """创建上传会话."""
    file_service = FileService(db)

    session = await file_service.create_upload_session(
        tenant_id=UUID(current_user["tenant_id"]),
        user_id=UUID(current_user["id"]),
        file_name=request["file_name"],
        mime_type=request["mime_type"],
        size_bytes=request["size_bytes"],
        sha256=request["sha256"],
        purpose=request.get("purpose", "general"),
        resource_id=UUID(request["resource_id"]) if request.get("resource_id") else None,
    )

    return _session_to_response(session)


@router.get(
    "/upload-sessions/{upload_id}",
    response_model=FileUploadSessionResponse,
    summary="查询上传会话",
    description="查询上传会话状态和进度。",
    responses={
        200: {"description": "成功"},
        404: {"description": "会话不存在"},
    },
)
async def get_upload_session(
    upload_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> FileUploadSessionResponse:
    """获取上传会话."""
    file_service = FileService(db)

    session = await file_service.get_upload_session(
        session_id=upload_id,
        user_id=UUID(current_user["id"]),
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "上传会话不存在或已过期"},
        )

    return _session_to_response(session)


@router.put(
    "/upload-sessions/{upload_id}/parts/{part_number}",
    response_model=PartUploadResponse,
    summary="上传分片",
    description="上传单个分片内容。",
    responses={
        200: {"description": "上传成功"},
        400: {"description": "分片无效"},
        404: {"description": "会话不存在"},
    },
)
async def upload_part(
    upload_id: UUID,
    part_number: int,
    current_user: AuthenticatedUser,
    db: DBSession,
    file: UploadFile = FastAPIFile(...),
) -> PartUploadResponse:
    """上传分片."""
    file_service = FileService(db)

    # TODO: 实现实际的MinIO分片上传
    # 目前返回模拟的ETag
    etag = f"etag-{secrets.token_hex(16)}"

    await file_service.record_uploaded_part(
        session_id=upload_id,
        part_number=part_number,
        etag=etag,
    )

    return PartUploadResponse(
        part_number=part_number,
        etag=etag,
    )


@router.post(
    "/upload-sessions/{upload_id}/complete",
    response_model=FileResponse,
    summary="完成上传",
    description="完成分片上传，合并文件并创建元数据。",
    responses={
        200: {"description": "上传完成"},
        400: {"description": "分片不完整"},
        404: {"description": "会话不存在"},
    },
)
async def complete_upload(
    upload_id: UUID,
    request: CompleteUploadRequest,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> FileResponse:
    """完成上传."""
    file_service = FileService(db)

    try:
        file_record = await file_service.complete_upload(
            session_id=upload_id,
            parts=request.parts,
        )
        return _file_to_response(file_record)
    except FileRejectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.delete(
    "/upload-sessions/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消上传",
    description="取消上传会话，清理已上传的分片。",
    responses={
        204: {"description": "已取消"},
        404: {"description": "会话不存在"},
    },
)
async def cancel_upload(
    upload_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> None:
    """取消上传."""
    file_service = FileService(db)
    await file_service.cancel_upload_session(
        session_id=upload_id,
        user_id=UUID(current_user["id"]),
    )


@router.get(
    "/{file_id}/preview",
    summary="预览文件",
    description="获取文件预览URL（预签名URL，有效期1小时）。",
    responses={
        200: {"description": "成功"},
        404: {"description": "文件不存在"},
    },
)
async def preview_file(
    file_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> dict[str, str]:
    """预览文件."""
    file_service = FileService(db)

    try:
        url = await file_service.get_preview_url(
            file_id=file_id,
            tenant_id=UUID(current_user["tenant_id"]),
        )
        return {"preview_url": url}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.get(
    "/{file_id}/download",
    summary="下载文件",
    description="获取文件下载URL（预签名URL，有效期1小时）。",
    responses={
        200: {"description": "成功"},
        404: {"description": "文件不存在"},
    },
)
async def download_file(
    file_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> dict[str, str]:
    """下载文件."""
    file_service = FileService(db)

    try:
        url = await file_service.get_download_url(
            file_id=file_id,
            tenant_id=UUID(current_user["tenant_id"]),
        )
        return {"download_url": url}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e
