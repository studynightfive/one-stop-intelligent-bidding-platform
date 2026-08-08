"""文件平台服务.

提供文件上传、下载、预览等功能。
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from minio import Minio, S3Error
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
from app.domains.files.models.file import (
    File,
    FileUploadSession,
    UploadStatus,
)


class FileService:
    """文件服务."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client: Minio | None = None  # 延迟初始化

    def _get_minio_client(self) -> Minio:
        """获取MinIO客户端."""
        if self.minio_client is None:
            endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
            self.minio_client = Minio(
                endpoint=endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self.minio_client

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
        """创建文件上传会话.

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            file_name: 文件名
            mime_type: MIME类型
            size_bytes: 文件大小
            sha256: SHA-256哈希
            purpose: 上传目的
            resource_id: 关联资源ID

        Returns:
            上传会话对象
        """
        # 验证文件大小
        if size_bytes > settings.upload_max_size_bytes:
            raise FileTooLargeError(
                max_size=settings.upload_max_size_bytes,
                actual_size=size_bytes,
            )

        # 验证文件扩展名
        ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in settings.upload_allowed_extensions:
            raise UnsupportedFileTypeError(
                file_extension=ext,
                allowed_extensions=list(settings.upload_allowed_extensions),
            )

        # 计算分片数
        part_size = settings.upload_chunk_size_bytes
        total_parts = (size_bytes + part_size - 1) // part_size

        # 创建会话
        session = FileUploadSession(
            tenant_id=tenant_id,
            user_id=user_id,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
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
        """获取上传会话.

        Args:
            session_id: 会话ID
            user_id: 用户ID（验证权限）

        Returns:
            会话对象或None
        """
        stmt = select(FileUploadSession).where(
            FileUploadSession.id == session_id,
            FileUploadSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session and session.is_expired:
            session.status = UploadStatus.CANCELLED
            await self.db.commit()
            return None

        return session

    async def record_uploaded_part(
        self,
        session_id: UUID,
        part_number: int,
        etag: str,
    ) -> FileUploadSession:
        """记录已上传的分片.

        Args:
            session_id: 会话ID
            part_number: 分片编号（从1开始）
            etag: 分片的ETag

        Returns:
            更新后的会话对象
        """
        stmt = select(FileUploadSession).where(FileUploadSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))

        # 更新状态
        if session.status == UploadStatus.CREATED:
            session.status = UploadStatus.UPLOADING

        # 记录分片
        session.uploaded_parts = session.uploaded_parts + [{"part_number": part_number, "etag": etag}]

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def complete_upload(
        self,
        session_id: UUID,
        parts: list[dict[str, Any]],
    ) -> File:
        """完成文件上传.

        Args:
            session_id: 会话ID
            parts: 完整的分片信息列表

        Returns:
            创建的文件元数据对象
        """
        stmt = select(FileUploadSession).where(FileUploadSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise NotFoundError(resource_type="upload_session", resource_id=str(session_id))

        # 验证所有分片已上传
        uploaded_parts = {p["part_number"] for p in session.uploaded_parts}
        expected_parts = set(range(1, session.total_parts + 1))
        if uploaded_parts != expected_parts:
            raise FileRejectedError(
                message=f"分片不完整：已上传 {len(uploaded_parts)}/{session.total_parts}",
            )

        # 合并分片到 MinIO
        minio_object_key = f"uploads/{session.id}/{session.file_name}"
        await self._compose_object_from_parts(session, parts, minio_object_key)

        # 创建文件元数据
        file_record = File(
            tenant_id=session.tenant_id,
            uploader_id=session.user_id,
            file_name=session.file_name,
            mime_type=session.mime_type,
            size_bytes=session.size_bytes,
            sha256=session.sha256,
            minio_bucket=settings.minio_bucket,
            minio_object_key=minio_object_key,
            purpose=session.purpose,
            resource_id=session.resource_id,
        )
        self.db.add(file_record)

        # 更新会话状态
        session.status = UploadStatus.COMPLETED
        session.minio_object_key = minio_object_key

        await self.db.commit()
        await self.db.refresh(file_record)

        return file_record

    async def _compose_object_from_parts(
        self,
        session: FileUploadSession,
        parts: list[dict[str, Any]],
        destination_key: str,
    ) -> None:
        """将分片合并为单个对象存储到 MinIO.

        Args:
            session: 上传会话
            parts: 分片信息列表（包含 part_number 和 etag）
            destination_key: 目标对象键
        """
        client = self._get_minio_client()

        # 确保存储桶存在
        try:
            if not client.bucket_exists(settings.minio_bucket):
                client.make_bucket(settings.minio_bucket)
        except S3Error:
            pass

        # 按分片编号排序
        sorted_parts = sorted(parts, key=lambda p: p["part_number"])

        compose_sources: list[ComposeSource] = []
        for part_info in sorted_parts:
            part_number = int(part_info["part_number"])
            # 分片对象的 key：uploads/{session_id}/parts/{part_number}
            part_key = f"uploads/{session.id}/parts/{part_number}"

            # 创建源对象，指定对象大小（最后一页可能小于分片大小）
            file_offset = (part_number - 1) * session.part_size_bytes
            remaining = session.size_bytes - file_offset
            length = min(session.part_size_bytes, remaining)

            compose_sources.append(
                ComposeSource(
                    bucket_name=settings.minio_bucket,
                    object_name=part_key,
                    offset=0,
                    length=length,
                    match_etag=cast(str | None, part_info.get("etag")),
                )
            )

        # 使用 compose_object 合并
        try:
            client.compose_object(
                settings.minio_bucket,
                destination_key,
                compose_sources,
            )
        except S3Error as e:
            raise FileRejectedError(
                message=f"合并分片失败: {str(e)}",
            ) from e

    async def get_file(self, file_id: UUID, tenant_id: UUID) -> File | None:
        """获取文件元数据.

        Args:
            file_id: 文件ID
            tenant_id: 租户ID（验证权限）

        Returns:
            文件元数据或None
        """
        stmt = select(File).where(
            File.id == file_id,
            File.tenant_id == tenant_id,
            File.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_download_url(self, file_id: UUID, tenant_id: UUID) -> str:
        """获取文件下载URL（签名URL）.

        Args:
            file_id: 文件ID
            tenant_id: 租户ID

        Returns:
            签名下载URL

        Raises:
            NotFoundError: 文件不存在
        """
        file = await self.get_file(file_id, tenant_id)
        if not file:
            raise NotFoundError(resource_type="file", resource_id=str(file_id))

        client = self._get_minio_client()

        # 生成预签名URL（有效期1小时）
        url = client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=file.minio_object_key,
            expires=timedelta(hours=1),
        )
        return url

    async def get_preview_url(self, file_id: UUID, tenant_id: UUID) -> str:
        """获取文件预览URL.

        Args:
            file_id: 文件ID
            tenant_id: 租户ID

        Returns:
            签名预览URL
        """
        return await self.get_download_url(file_id, tenant_id)

    async def delete_file(self, file_id: UUID, tenant_id: UUID) -> None:
        """删除文件（软删除）.

        Args:
            file_id: 文件ID
            tenant_id: 租户ID
        """
        stmt = (
            update(File)
            .where(
                File.id == file_id,
                File.tenant_id == tenant_id,
            )
            .values(deleted_at=datetime.now(UTC))
        )

        await self.db.execute(stmt)
        await self.db.commit()

    async def cancel_upload_session(self, session_id: UUID, user_id: UUID) -> None:
        """取消上传会话.

        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        stmt = select(FileUploadSession).where(
            FileUploadSession.id == session_id,
            FileUploadSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.status = UploadStatus.CANCELLED
            await self.db.commit()

    async def verify_file_hash(self, file_id: UUID, content: bytes) -> bool:
        """验证文件哈希.

        Args:
            file_id: 文件ID
            content: 文件内容

        Returns:
            是否匹配
        """
        stmt = select(File).where(File.id == file_id)
        result = await self.db.execute(stmt)
        file = result.scalar_one_or_none()

        if not file:
            return False

        return file.sha256 == compute_sha256(content)
