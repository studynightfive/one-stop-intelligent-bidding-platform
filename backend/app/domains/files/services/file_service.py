"""Resumable file upload, verification, and object-storage access."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from minio import Minio
from minio.commonconfig import ComposeSource
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    FileRejectedError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from app.core.security import compute_sha256
from app.domains.files.models.file import File, FileUploadSession, ScanStatus, UploadStatus


class FileService:
    """Persist upload state in SQL and file bytes in MinIO."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client: Minio | None = None

    def _get_minio_client(self) -> Minio:
        if self.minio_client is None:
            endpoint = settings.minio_endpoint.removeprefix("http://").removeprefix("https://")
            self.minio_client = Minio(
                endpoint=endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self.minio_client

    @staticmethod
    def _part_key(session_id: UUID, part_number: int) -> str:
        return f"uploads/{session_id}/parts/{part_number}"

    def _ensure_bucket_sync(self) -> None:
        client = self._get_minio_client()
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)

    async def create_upload_session(
        self,
        tenant_id: UUID,
        user_id: UUID,
        file_name: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        purpose: str = "general",
        resource_id: UUID | None = None,
    ) -> FileUploadSession:
        """Validate metadata and create a 24-hour resumable upload session."""
        if size_bytes < 1:
            raise FileRejectedError(message="文件不能为空")
        if size_bytes > settings.upload_max_size_bytes:
            raise FileTooLargeError(
                max_size=settings.upload_max_size_bytes,
                actual_size=size_bytes,
            )

        safe_name = Path(file_name).name
        if safe_name != file_name or safe_name in {"", ".", ".."}:
            raise FileRejectedError(message="文件名不能包含路径")
        extension = Path(safe_name).suffix.lower()
        if extension not in settings.upload_allowed_extensions:
            raise UnsupportedFileTypeError(
                file_extension=extension,
                allowed_extensions=sorted(settings.upload_allowed_extensions),
            )

        part_size = settings.upload_chunk_size_bytes
        total_parts = (size_bytes + part_size - 1) // part_size
        session = FileUploadSession(
            tenant_id=tenant_id,
            user_id=user_id,
            file_name=safe_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256.lower(),
            part_size_bytes=part_size,
            total_parts=total_parts,
            purpose=purpose,
            resource_id=resource_id,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_upload_session(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> FileUploadSession | None:
        stmt = select(FileUploadSession).where(
            FileUploadSession.id == session_id,
            FileUploadSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session and session.is_expired:
            session.status = UploadStatus.CANCELLED
            await self.db.commit()
            await self._cleanup_parts(session)
            return None
        return session

    async def upload_part(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        part_number: int,
        content: bytes,
    ) -> tuple[FileUploadSession, str]:
        """Write one part to MinIO and persist its real ETag.

        Re-uploading the same part replaces the object and the recorded ETag,
        which makes client retries and resume operations idempotent.
        """
        session = await self.get_upload_session(session_id, user_id)
        if session is None:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))
        if session.status not in {UploadStatus.CREATED, UploadStatus.UPLOADING}:
            raise FileRejectedError(message=f"上传会话状态不允许上传分片: {session.status.value}")
        if not 1 <= part_number <= session.total_parts:
            raise FileRejectedError(
                message=f"分片编号超出范围: {part_number}",
                details={"totalParts": session.total_parts},
            )

        offset = (part_number - 1) * session.part_size_bytes
        expected_size = min(session.part_size_bytes, session.size_bytes - offset)
        if len(content) != expected_size:
            raise FileRejectedError(
                message="分片大小不正确",
                details={
                    "partNumber": part_number,
                    "expectedSizeBytes": expected_size,
                    "actualSizeBytes": len(content),
                },
            )

        try:
            await asyncio.to_thread(self._ensure_bucket_sync)
            result = await asyncio.to_thread(
                self._get_minio_client().put_object,
                settings.minio_bucket,
                self._part_key(session.id, part_number),
                BytesIO(content),
                len(content),
                content_type="application/octet-stream",
            )
        except Exception as exc:
            raise FileRejectedError(message="分片写入对象存储失败，请稍后重试") from exc

        etag = str(result.etag).strip().strip('"')
        session = await self.record_uploaded_part(session.id, part_number, etag)
        return session, etag

    async def record_uploaded_part(
        self,
        session_id: UUID,
        part_number: int,
        etag: str,
    ) -> FileUploadSession:
        """Record or replace a persisted part.

        This method remains public for worker integrations; HTTP uploads should
        use :meth:`upload_part` so an ETag can never be recorded before storage.
        """
        stmt = select(FileUploadSession).where(FileUploadSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))
        if not 1 <= part_number <= session.total_parts:
            raise FileRejectedError(message=f"分片编号超出范围: {part_number}")
        if session.status not in {UploadStatus.CREATED, UploadStatus.UPLOADING}:
            raise FileRejectedError(message=f"上传会话状态不允许更新: {session.status.value}")

        normalized_etag = etag.strip().strip('"')
        parts_by_number = {
            int(item["part_number"]): {
                "part_number": int(item["part_number"]),
                "etag": str(item["etag"]).strip().strip('"'),
            }
            for item in session.uploaded_parts
        }
        parts_by_number[part_number] = {"part_number": part_number, "etag": normalized_etag}
        session.uploaded_parts = [parts_by_number[index] for index in sorted(parts_by_number)]
        session.status = UploadStatus.UPLOADING
        await self.db.commit()
        await self.db.refresh(session)
        return session

    @staticmethod
    def _normalize_submitted_parts(parts: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in parts:
            if isinstance(item, dict):
                part_number = item.get("part_number", item.get("partNumber"))
                etag = item.get("etag")
            else:
                part_number = getattr(item, "part_number", None)
                etag = getattr(item, "etag", None)
            if not isinstance(part_number, int) or part_number < 1 or not isinstance(etag, str) or not etag.strip():
                raise FileRejectedError(message="完成上传时的分片信息无效")
            normalized.append({"part_number": part_number, "etag": etag.strip().strip('"')})
        return normalized

    async def complete_upload(
        self,
        session_id: UUID,
        parts: list[Any],
        *,
        user_id: UUID | None = None,
    ) -> File:
        """Compose all uploaded parts, verify SHA-256, and create file metadata."""
        conditions = [FileUploadSession.id == session_id]
        if user_id is not None:
            conditions.append(FileUploadSession.user_id == user_id)
        result = await self.db.execute(select(FileUploadSession).where(*conditions))
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))
        if session.is_expired or session.status in {UploadStatus.CANCELLED, UploadStatus.FAILED}:
            raise FileRejectedError(message="上传会话已过期或已取消")
        if session.status == UploadStatus.COMPLETED:
            file_result = await self.db.execute(select(File).where(File.minio_object_key == session.minio_object_key))
            existing = file_result.scalar_one_or_none()
            if existing is not None:
                return existing
            raise FileRejectedError(message="上传会话状态与文件记录不一致")

        submitted = self._normalize_submitted_parts(parts)
        submitted_by_number = {item["part_number"]: item["etag"] for item in submitted}
        if len(submitted_by_number) != len(submitted):
            raise FileRejectedError(message="完成上传请求包含重复分片")
        recorded_by_number = {
            int(item["part_number"]): str(item["etag"]).strip().strip('"') for item in session.uploaded_parts
        }
        expected_numbers = set(range(1, session.total_parts + 1))
        if set(recorded_by_number) != expected_numbers or set(submitted_by_number) != expected_numbers:
            raise FileRejectedError(
                message=f"分片不完整：已上传 {len(recorded_by_number)}/{session.total_parts}",
                details={"expectedParts": session.total_parts},
            )
        if submitted_by_number != recorded_by_number:
            raise FileRejectedError(message="完成上传请求中的 ETag 与已上传分片不一致")

        destination_key = f"uploads/{session.tenant_id}/{session.id}/{session.file_name}"
        session.status = UploadStatus.VERIFYING
        await self.db.commit()
        try:
            await self._compose_object_from_parts(session, submitted, destination_key)
            verified = await self._verify_object_sha256(destination_key, session.sha256)
            if not verified:
                await self._remove_object(destination_key)
                raise FileRejectedError(message="文件 SHA-256 校验失败，请重新上传")
        except FileRejectedError:
            session.status = UploadStatus.FAILED
            await self.db.commit()
            raise

        file_record = File(
            tenant_id=session.tenant_id,
            uploader_id=session.user_id,
            file_name=session.file_name,
            mime_type=session.mime_type,
            size_bytes=session.size_bytes,
            sha256=session.sha256,
            minio_bucket=settings.minio_bucket,
            minio_object_key=destination_key,
            purpose=session.purpose,
            resource_id=session.resource_id,
            scan_status=ScanStatus.CLEAN,
        )
        self.db.add(file_record)
        session.status = UploadStatus.COMPLETED
        session.scan_status = ScanStatus.CLEAN
        session.minio_object_key = destination_key
        await self.db.commit()
        await self.db.refresh(file_record)
        await self._cleanup_parts(session)
        return file_record

    async def _compose_object_from_parts(
        self,
        session: FileUploadSession,
        parts: list[dict[str, Any]],
        destination_key: str,
    ) -> None:
        try:
            await asyncio.to_thread(self._ensure_bucket_sync)
            sources: list[ComposeSource] = []
            for item in sorted(parts, key=lambda value: int(value["part_number"])):
                part_number = int(item["part_number"])
                offset = (part_number - 1) * session.part_size_bytes
                length = min(session.part_size_bytes, session.size_bytes - offset)
                sources.append(
                    ComposeSource(
                        bucket_name=settings.minio_bucket,
                        object_name=self._part_key(session.id, part_number),
                        offset=0,
                        length=length,
                        match_etag=cast(str, item["etag"]),
                    )
                )
            await asyncio.to_thread(
                self._get_minio_client().compose_object,
                settings.minio_bucket,
                destination_key,
                sources,
            )
        except Exception as exc:
            raise FileRejectedError(message="合并上传分片失败，请稍后重试") from exc

    async def _verify_object_sha256(self, object_key: str, expected_sha256: str) -> bool:
        def verify() -> bool:
            response = self._get_minio_client().get_object(settings.minio_bucket, object_key)
            digest = hashlib.sha256()
            try:
                for chunk in response.stream(1024 * 1024):
                    digest.update(chunk)
            finally:
                response.close()
                response.release_conn()
            return digest.hexdigest() == expected_sha256.lower()

        try:
            return await asyncio.to_thread(verify)
        except Exception as exc:
            raise FileRejectedError(message="读取已合并文件进行校验时失败") from exc

    async def _remove_object(self, object_key: str) -> None:
        try:
            await asyncio.to_thread(
                self._get_minio_client().remove_object,
                settings.minio_bucket,
                object_key,
            )
        except Exception:
            # Cleanup is best effort; upload status still captures the failure.
            return

    async def _cleanup_parts(self, session: FileUploadSession) -> None:
        for part_number in range(1, session.total_parts + 1):
            await self._remove_object(self._part_key(session.id, part_number))

    async def get_file(self, file_id: UUID, tenant_id: UUID) -> File | None:
        result = await self.db.execute(
            select(File).where(
                File.id == file_id,
                File.tenant_id == tenant_id,
                File.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def open_file(self, file_id: UUID, tenant_id: UUID) -> tuple[File, Any]:
        """Open a MinIO response for proxy streaming through the API."""
        file_record = await self.get_file(file_id, tenant_id)
        if file_record is None:
            raise NotFoundError(resource_type="file", resource_id=str(file_id))
        try:
            response = await asyncio.to_thread(
                self._get_minio_client().get_object,
                file_record.minio_bucket,
                file_record.minio_object_key,
            )
        except Exception as exc:
            raise FileRejectedError(message="文件暂时无法读取，请稍后重试") from exc
        return file_record, response

    async def get_download_url(self, file_id: UUID, tenant_id: UUID) -> str:
        file_record = await self.get_file(file_id, tenant_id)
        if file_record is None:
            raise NotFoundError(resource_type="file", resource_id=str(file_id))
        return await asyncio.to_thread(
            self._get_minio_client().presigned_get_object,
            file_record.minio_bucket,
            file_record.minio_object_key,
            expires=timedelta(hours=1),
        )

    async def get_preview_url(self, file_id: UUID, tenant_id: UUID) -> str:
        return await self.get_download_url(file_id, tenant_id)

    async def delete_file(self, file_id: UUID, tenant_id: UUID) -> None:
        file_record = await self.get_file(file_id, tenant_id)
        if file_record is None:
            raise NotFoundError(resource_type="file", resource_id=str(file_id))
        await self.db.execute(
            update(File).where(File.id == file_id, File.tenant_id == tenant_id).values(deleted_at=datetime.now(UTC))
        )
        await self.db.commit()
        try:
            await asyncio.to_thread(
                self._get_minio_client().remove_object,
                file_record.minio_bucket,
                file_record.minio_object_key,
            )
        except Exception:
            return

    async def cancel_upload_session(self, session_id: UUID, user_id: UUID) -> None:
        result = await self.db.execute(
            select(FileUploadSession).where(
                FileUploadSession.id == session_id,
                FileUploadSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))
        if session.status == UploadStatus.COMPLETED:
            raise FileRejectedError(message="已完成的上传会话不能取消")
        session.status = UploadStatus.CANCELLED
        await self.db.commit()
        await self._cleanup_parts(session)

    async def verify_file_hash(self, file_id: UUID, content: bytes) -> bool:
        result = await self.db.execute(select(File).where(File.id == file_id))
        file_record = result.scalar_one_or_none()
        return file_record is not None and file_record.sha256 == compute_sha256(content)
