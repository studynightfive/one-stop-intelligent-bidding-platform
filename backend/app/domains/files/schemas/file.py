"""文件schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileUploadSessionResponse(BaseModel):
    """上传会话响应."""
    id: UUID = Field(..., description="会话ID")
    file_name: str = Field(..., description="文件名")
    size_bytes: int = Field(..., description="文件大小(字节)")
    part_size_bytes: int = Field(..., description="分片大小(字节)")
    total_parts: int = Field(..., description="总分片数")
    uploaded_parts: list[dict] = Field(default_factory=list, description="已上传分片列表")
    status: str = Field(..., description="状态")
    expires_at: datetime = Field(..., description="过期时间")


class PartUploadResponse(BaseModel):
    """分片上传响应."""
    part_number: int = Field(..., description="分片编号")
    etag: str = Field(..., description="分片ETag")


class CompleteUploadRequest(BaseModel):
    """完成上传请求."""
    parts: list[dict] = Field(..., description="分片信息列表")


class FileResponse(BaseModel):
    """文件响应."""
    id: UUID = Field(..., description="文件ID")
    file_name: str = Field(..., description="文件名")
    mime_type: str = Field(..., description="MIME类型")
    size_bytes: int = Field(..., description="文件大小")
    sha256: str = Field(..., description="SHA-256哈希")
    scan_status: str = Field(..., description="扫描状态")
    preview_url: str | None = Field(None, description="预览URL")
    download_url: str | None = Field(None, description="下载URL")
    created_at: datetime = Field(..., description="创建时间")
