"""HTTP API for contract-aligned resumable uploads and file delivery."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Header, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import NotFoundError
from app.domains.files.schemas.file import (
    CompleteUploadRequest,
    CreateUploadSessionRequest,
    FileResponse,
    FileUploadSessionResponse,
    PartUploadResponse,
    UploadPart,
)
from app.domains.files.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件、异步任务与实时事件"])


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-Id") or str(uuid4())


def _success(request: Request, data: Any, *, status_code: int = 200) -> JSONResponse:
    request_id = _request_id(request)
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json", by_alias=True, exclude_none=True)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"success": True, "data": data, "requestId": request_id}),
        headers={"X-Request-Id": request_id},
    )


def _session_to_response(session: Any) -> FileUploadSessionResponse:
    return FileUploadSessionResponse(
        id=session.id,
        file_name=session.file_name,
        size_bytes=session.size_bytes,
        part_size_bytes=session.part_size_bytes,
        total_parts=session.total_parts,
        uploaded_parts=[
            UploadPart(part_number=int(item["part_number"]), etag=str(item["etag"])) for item in session.uploaded_parts
        ],
        status=session.status.value,
        expires_at=session.expires_at,
    )


def _file_to_response(file_record: Any) -> FileResponse:
    return FileResponse(
        id=file_record.id,
        file_name=file_record.file_name,
        mime_type=file_record.mime_type,
        size_bytes=file_record.size_bytes,
        sha256=file_record.sha256,
        scan_status=file_record.scan_status.value,
        created_at=file_record.created_at,
    )


def _as_uuid(value: object, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": f"登录信息缺少有效的 {field}"},
        ) from exc


@router.post(
    "/upload-sessions",
    status_code=status.HTTP_201_CREATED,
    summary="创建上传会话",
)
async def create_upload_session(
    body: CreateUploadSessionRequest,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
    session = await FileService(db).create_upload_session(
        tenant_id=_as_uuid(current_user.get("tenant_id"), "tenant_id"),
        user_id=_as_uuid(current_user.get("id"), "user_id"),
        file_name=body.file_name,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
        sha256=body.sha256,
        purpose=body.purpose,
        resource_id=body.resource_id,
    )
    return _success(request, _session_to_response(session), status_code=status.HTTP_201_CREATED)


@router.get("/upload-sessions/{upload_id}", summary="查询上传会话")
async def get_upload_session(
    upload_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
    session = await FileService(db).get_upload_session(
        session_id=upload_id,
        user_id=_as_uuid(current_user.get("id"), "user_id"),
    )
    if session is None:
        raise NotFoundError(
            message="上传会话不存在或已过期", resource_type="upload_session", resource_id=str(upload_id)
        )
    return _success(request, _session_to_response(session))


@router.put(
    "/upload-sessions/{upload_id}/parts/{part_number}",
    summary="上传分片",
)
async def upload_part(
    upload_id: UUID,
    part_number: int,
    body: Annotated[bytes, Body(media_type="application/octet-stream")],
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
    _, etag = await FileService(db).upload_part(
        session_id=upload_id,
        user_id=_as_uuid(current_user.get("id"), "user_id"),
        part_number=part_number,
        content=body,
    )
    return _success(request, PartUploadResponse(part_number=part_number, etag=etag))


@router.post("/upload-sessions/{upload_id}/complete", summary="完成上传")
async def complete_upload(
    upload_id: UUID,
    body: CompleteUploadRequest,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> JSONResponse:
    _ = idempotency_key
    file_record = await FileService(db).complete_upload(
        session_id=upload_id,
        parts=body.parts,
        user_id=_as_uuid(current_user.get("id"), "user_id"),
    )
    return _success(request, _file_to_response(file_record))


@router.delete(
    "/upload-sessions/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消上传",
)
async def cancel_upload(
    upload_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> Response:
    await FileService(db).cancel_upload_session(
        session_id=upload_id,
        user_id=_as_uuid(current_user.get("id"), "user_id"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"X-Request-Id": _request_id(request)})


def _stream_object(response: Any) -> Iterator[bytes]:
    try:
        yield from response.stream(64 * 1024)
    finally:
        response.close()
        response.release_conn()


async def _file_stream_response(
    *,
    file_id: UUID,
    request: Request,
    current_user: dict[str, Any],
    db: Any,
    disposition: str,
) -> StreamingResponse:
    file_record, object_response = await FileService(db).open_file(
        file_id=file_id,
        tenant_id=_as_uuid(current_user.get("tenant_id"), "tenant_id"),
    )
    request_id = _request_id(request)
    encoded_name = quote(file_record.file_name, safe="")
    return StreamingResponse(
        _stream_object(object_response),
        media_type=file_record.mime_type or "application/octet-stream",
        headers={
            "X-Request-Id": request_id,
            "X-File-Sha256": file_record.sha256,
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_name}",
        },
    )


@router.get("/{file_id}/preview", summary="预览文件")
async def preview_file(
    file_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> StreamingResponse:
    return await _file_stream_response(
        file_id=file_id,
        request=request,
        current_user=current_user,
        db=db,
        disposition="inline",
    )


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> StreamingResponse:
    return await _file_stream_response(
        file_id=file_id,
        request=request,
        current_user=current_user,
        db=db,
        disposition="attachment",
    )
