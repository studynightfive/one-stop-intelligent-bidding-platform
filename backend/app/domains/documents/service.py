"""Documents 域服务：版本管理、diff、roll-back-as-new-version、下载元数据。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domains.documents.diff import diff_sections
from app.domains.documents.docx import extract_docx_text
from app.domains.documents.entities import BINARY_CONTENT_TYPE, DocumentEntity, DocumentVersionEntity
from app.domains.documents.errors import conflict, not_found, validation_error
from app.domains.documents.hashing import sha256_hex
from app.domains.documents.mappers import (
    document_dict,
    document_diff_dict,
    document_version_dict,
)
from app.domains.documents.repository import DocumentStore


def _now() -> datetime:
    return datetime.now(UTC)


_VALID_DOC_TYPES = ("qualification", "commercial", "technical", "merged")


class DocumentService:
    def __init__(self, store: DocumentStore) -> None:
        self.store = store

    # ----------------- 查询 -----------------
    def list_by_task(self, *, tenant_id: str, task_id: str) -> list[dict[str, Any]]:
        return [document_dict(d) for d in self.store.list_documents_by_task(tenant_id=tenant_id, task_id=task_id)]

    def list_versions_by_task(
        self, *, tenant_id: str, task_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        all_versions = self.store.list_versions_by_task(tenant_id=tenant_id, task_id=task_id)
        total = len(all_versions)
        start = max(page - 1, 0) * page_size
        page_items = all_versions[start : start + page_size]
        data = [document_version_dict(v) for v in page_items]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta

    def get_document(self, *, tenant_id: str, task_id: str, document_id: str) -> dict[str, Any]:
        doc = self.store.get_document(document_id, tenant_id=tenant_id)
        if doc.task_id != task_id:
            raise not_found("文档不属于该投标任务", documentId=document_id)
        return document_dict(doc)

    def get_version(self, *, tenant_id: str, version_id: str) -> DocumentVersionEntity:
        return self.store.get_version(version_id, tenant_id=tenant_id)

    def validate_content(self, *, file_id: str, size_bytes: int, sha256: str, content: bytes) -> str:
        """Validate trusted DOCX bytes without mutating document state."""
        if size_bytes != len(content):
            raise conflict("文档内容大小与文件元数据不一致", fileId=file_id)
        if sha256_hex(content).lower() != sha256.lower():
            raise conflict("文档内容哈希与文件元数据不一致", fileId=file_id)
        return extract_docx_text(content)

    # ----------------- 创建版本（生成/回滚后） -----------------
    def ensure_document(
        self,
        *,
        tenant_id: str,
        task_id: str,
        doc_type: str,
        new_id_fn: Callable[[], str],
    ) -> DocumentEntity:
        if doc_type not in _VALID_DOC_TYPES:
            raise validation_error(
                "不支持的文档类型", field_errors=[{"field": "type", "code": "INVALID", "message": "文档类型非法"}]
            )
        existing = self.store.find_document_by_type(tenant_id=tenant_id, task_id=task_id, doc_type=doc_type)
        if existing:
            return existing
        now = _now()
        doc = DocumentEntity(
            id=new_id_fn(),
            task_id=task_id,
            tenant_id=tenant_id,
            doc_type=doc_type,
            current_version=0,
            created_at=now,
            updated_at=now,
        )
        return self.store.save_document(doc)

    def append_version(
        self,
        *,
        tenant_id: str,
        task_id: str,
        doc_type: str,
        new_id_fn: Callable[[], str],
        file_id: str,
        file_name: str,
        size_bytes: int,
        content: bytes | None = None,
        sha256: str | None = None,
        text_content: str | None = None,
        change_summary: str = "",
        created_by_id: str = "",
        created_by_name: str = "",
        source_version_id: str | None = None,
        roll_back: bool = False,
    ) -> DocumentVersionEntity:
        if content is None and not sha256:
            raise validation_error("文档版本缺少可验证的 SHA-256")
        digest = sha256_hex(content) if content is not None else str(sha256)
        if len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise validation_error("文档版本 SHA-256 格式无效")
        if sha256 and digest.lower() != sha256.lower():
            raise conflict("文档内容哈希与文件元数据不一致", fileId=file_id)
        trusted_text_content = text_content
        if content is not None:
            trusted_text_content = self.validate_content(
                file_id=file_id,
                size_bytes=size_bytes,
                sha256=digest,
                content=content,
            )
        doc = self.ensure_document(tenant_id=tenant_id, task_id=task_id, doc_type=doc_type, new_id_fn=new_id_fn)
        now = _now()
        version = DocumentVersionEntity(
            id=new_id_fn(),
            document_id=doc.id,
            tenant_id=tenant_id,
            version_number=self.store.next_version_number(doc.id),
            file_id=file_id,
            file_name=file_name,
            mime_type=BINARY_CONTENT_TYPE,
            size_bytes=len(content) if content is not None else size_bytes,
            sha256=digest,
            change_summary=change_summary or ("回滚" if roll_back else "生成新版本"),
            created_by_id=created_by_id,
            created_by_name=created_by_name,
            created_at=now,
            source_version_id=source_version_id,
            roll_back=roll_back,
            text_content=trusted_text_content,
            content=content,
        )
        self.store.save_version(version)
        doc.current_version = version.version_number
        doc.latest_file_id = file_id
        doc.updated_at = now
        self.store.save_document(doc)
        return version

    # ----------------- diff -----------------
    def compare_versions(
        self,
        *,
        tenant_id: str,
        task_id: str,
        from_version_id: str,
        to_version_id: str,
    ) -> dict[str, Any]:
        from_v = self.store.get_version(from_version_id, tenant_id=tenant_id)
        to_v = self.store.get_version(to_version_id, tenant_id=tenant_id)
        if from_v.document_id != to_v.document_id:
            raise validation_error(
                "两个版本不属于同一文档",
                field_errors=[{"field": "fromVersionId", "code": "MISMATCH", "message": "版本必须属于同一文档"}],
            )
        # 校验 task 一致性
        from_doc = self.store.get_document(from_v.document_id, tenant_id=tenant_id)
        if from_doc.task_id != task_id:
            raise conflict("版本与任务不匹配", taskId=task_id)
        before_text = _version_text(from_v)
        after_text = _version_text(to_v)
        changes = diff_sections(before_text, after_text)
        change_dicts = [
            {
                "section": c.section,
                "type": c.change_type,
                "before": c.before,
                "after": c.after,
            }
            for c in changes
        ]
        return document_diff_dict(
            from_version=from_v,
            to_version=to_v,
            changes=change_dicts,
        )

    # ----------------- 下载元数据 -----------------
    def build_download_meta(self, *, tenant_id: str, version_id: str) -> dict[str, Any]:
        version = self.store.get_version(version_id, tenant_id=tenant_id)
        return document_version_dict(version)

    # ----------------- 业务回滚：rollback as new version -----------------
    def rollback_to(
        self,
        *,
        tenant_id: str,
        task_id: str,
        document_id: str,
        target_version_id: str,
        new_id_fn: Callable[[], str],
        reason: str,
        actor_id: str,
        actor_name: str,
    ) -> DocumentVersionEntity:
        doc = self.store.get_document(document_id, tenant_id=tenant_id)
        if doc.task_id != task_id:
            raise conflict("文档不属于该投标任务", taskId=task_id)
        target = self.store.get_version(target_version_id, tenant_id=tenant_id)
        if target.document_id != document_id:
            raise conflict("目标版本不属于该文档")
        # 业务规则：archived/rolled-back 文档不允许回滚（demo 简化：只允许非 closed 状态）
        if doc.current_version == 0:
            raise conflict("文档尚无任何版本可回滚")
        return self.append_version(
            tenant_id=tenant_id,
            task_id=task_id,
            doc_type=doc.doc_type,
            new_id_fn=new_id_fn,
            file_id=target.file_id,
            file_name=target.file_name,
            size_bytes=target.size_bytes,
            content=target.content,
            sha256=target.sha256,
            text_content=target.text_content,
            change_summary=(reason or "回滚") + f" → v{target.version_number}",
            created_by_id=actor_id,
            created_by_name=actor_name,
            source_version_id=target.id,
            roll_back=True,
        )


def _version_text(version: DocumentVersionEntity) -> str:
    if version.content is not None:
        return extract_docx_text(version.content)
    return version.text_content or f"## 版本说明\n{version.change_summary}\n"
