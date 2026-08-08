"""文件平台服务测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import FileRejectedError, FileTooLargeError, UnsupportedFileTypeError
from app.core.security import compute_sha256
from app.domains.files.models.file import File, UploadStatus
from app.domains.files.services.file_service import FileService


@pytest.mark.asyncio
async def test_upload_session_validation_and_lifecycle(db_session: AsyncSession) -> None:
    service = FileService(db_session)
    tenant_id = uuid4()
    user_id = uuid4()

    with pytest.raises(FileTooLargeError):
        await service.create_upload_session(
            tenant_id,
            user_id,
            "large.pdf",
            "application/pdf",
            settings.upload_max_size_bytes + 1,
            "hash",
        )
    with pytest.raises(UnsupportedFileTypeError):
        await service.create_upload_session(tenant_id, user_id, "malware.exe", "binary", 10, "hash")

    session = await service.create_upload_session(
        tenant_id,
        user_id,
        "proposal.pdf",
        "application/pdf",
        settings.upload_chunk_size_bytes + 1,
        "hash",
        purpose="bid",
    )
    assert session.total_parts == 2
    assert await service.get_upload_session(session.id, user_id) is not None

    await service.record_uploaded_part(session.id, 1, "etag-1")
    updated = await service.record_uploaded_part(session.id, 2, "etag-2")
    assert updated.status == UploadStatus.UPLOADING
    assert updated.uploaded_count == 2

    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    assert await service.get_upload_session(session.id, user_id) is None


@pytest.mark.asyncio
async def test_complete_download_delete_and_hash(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    service = FileService(db_session)
    tenant_id = uuid4()
    user_id = uuid4()
    content = b"proposal"
    digest = compute_sha256(content)
    session = await service.create_upload_session(
        tenant_id,
        user_id,
        "proposal.pdf",
        "application/pdf",
        len(content),
        digest,
    )

    with pytest.raises(FileRejectedError, match="分片不完整"):
        await service.complete_upload(session.id, [])

    await service.record_uploaded_part(session.id, 1, "etag-1")
    compose = AsyncMock()
    monkeypatch.setattr(service, "_compose_object_from_parts", compose)
    file_record = await service.complete_upload(session.id, [{"part_number": 1, "etag": "etag-1"}])
    compose.assert_awaited_once()
    assert file_record.file_name == "proposal.pdf"
    assert await service.get_file(file_record.id, tenant_id) is not None
    assert await service.verify_file_hash(file_record.id, content)
    assert not await service.verify_file_hash(file_record.id, b"wrong")
    assert not await service.verify_file_hash(uuid4(), content)

    minio = Mock()
    minio.presigned_get_object.return_value = "https://files.example/download"
    service.minio_client = minio
    assert await service.get_download_url(file_record.id, tenant_id) == "https://files.example/download"
    assert await service.get_preview_url(file_record.id, tenant_id) == "https://files.example/download"

    await service.delete_file(file_record.id, tenant_id)
    assert await service.get_file(file_record.id, tenant_id) is None


@pytest.mark.asyncio
async def test_cancel_missing_parts_and_minio_compose(db_session: AsyncSession) -> None:
    service = FileService(db_session)
    tenant_id = uuid4()
    user_id = uuid4()

    with pytest.raises(Exception, match="不存在"):
        await service.record_uploaded_part(uuid4(), 1, "etag")

    await service.cancel_upload_session(uuid4(), user_id)
    session = await service.create_upload_session(
        tenant_id,
        user_id,
        "archive.zip",
        "application/zip",
        10,
        "hash",
    )
    await service.cancel_upload_session(session.id, user_id)
    await db_session.refresh(session)
    assert session.status == UploadStatus.CANCELLED

    minio = Mock()
    minio.bucket_exists.return_value = False
    service.minio_client = minio
    await service._compose_object_from_parts(
        session,
        [{"part_number": 1, "etag": "etag"}],
        "destination",
    )
    minio.make_bucket.assert_called_once_with(settings.minio_bucket)
    minio.compose_object.assert_called_once()


@pytest.mark.asyncio
async def test_download_missing_file(db_session: AsyncSession) -> None:
    service = FileService(db_session)
    with pytest.raises(Exception, match="不存在"):
        await service.get_download_url(uuid4(), uuid4())

    file_record = File(
        tenant_id=uuid4(),
        uploader_id=uuid4(),
        file_name="x.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        sha256="hash",
        minio_bucket="bucket",
        minio_object_key="key",
    )
    assert "x.pdf" in repr(file_record)
