"""Contract-aligned schemas for resumable file uploads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractModel(BaseModel):
    """Accept camelCase at the HTTP boundary while keeping Python snake_case."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CreateUploadSessionRequest(ContractModel):
    file_name: str = Field(alias="fileName", min_length=1, max_length=255)
    mime_type: str = Field(alias="mimeType", min_length=1, max_length=100)
    size_bytes: int = Field(alias="sizeBytes", ge=1, le=200 * 1024 * 1024)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    purpose: Literal[
        "tender",
        "bidMaterial",
        "bidIllustration",
        "qualification",
        "fragment",
        "supplierMaterial",
        "template",
    ]
    resource_id: UUID | None = Field(default=None, alias="resourceId")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        name = value.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("fileName must be a plain file name without path segments")
        return name

    @field_validator("sha256")
    @classmethod
    def normalize_sha256(cls, value: str) -> str:
        return value.lower()


class UploadPart(ContractModel):
    part_number: int = Field(alias="partNumber", ge=1)
    etag: str = Field(min_length=1)

    @field_validator("etag")
    @classmethod
    def normalize_etag(cls, value: str) -> str:
        return value.strip().strip('"')


class CompleteUploadRequest(ContractModel):
    parts: list[UploadPart] = Field(min_length=1)


class FileUploadSessionResponse(ContractModel):
    id: UUID
    file_name: str = Field(alias="fileName")
    size_bytes: int = Field(alias="sizeBytes", ge=1)
    part_size_bytes: int = Field(alias="partSizeBytes", ge=1)
    total_parts: int = Field(alias="totalParts", ge=1)
    uploaded_parts: list[UploadPart] = Field(alias="uploadedParts", default_factory=list)
    status: Literal[
        "created",
        "uploading",
        "verifying",
        "scanning",
        "completed",
        "cancelled",
        "failed",
    ]
    expires_at: datetime = Field(alias="expiresAt")


class PartUploadResponse(UploadPart):
    """Response returned after a part has been persisted to object storage."""


class FileResponse(ContractModel):
    id: UUID
    file_name: str = Field(alias="fileName")
    mime_type: str = Field(alias="mimeType")
    size_bytes: int = Field(alias="sizeBytes", ge=0)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    scan_status: Literal["pending", "clean", "infected", "failed"] = Field(alias="scanStatus")
    preview_url: str | None = Field(default=None, alias="previewUrl")
    download_url: str | None = Field(default=None, alias="downloadUrl")
    created_at: datetime = Field(alias="createdAt")
