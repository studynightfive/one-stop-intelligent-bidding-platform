"""片段库 CRUD、版本、引用、关键词过滤与语义检索编排。"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.errors.exceptions import AppException
from app.domains.bids.errors import (
    conflict,
    file_rejected,
    forbidden,
    not_found,
    validation_error,
    version_conflict,
)
from app.domains.bids.ports import (
    AuditEventInput,
    AuditServicePort,
    AuthPrincipal,
    FileRefSnapshot,
    FileServicePort,
)
from app.domains.fragments.entities import (
    FragmentEntity,
    FragmentReferenceEntity,
    FragmentVersionEntity,
)
from app.domains.fragments.ports import (
    SemanticSearchHit,
    SemanticSearchPort,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.domains.fragments.store import FragmentStore

_CREATE_FIELDS = {"title", "category", "summary", "content", "sourceFileId", "documentVersion", "tags"}
_UPDATE_FIELDS = {"title", "category", "summary", "content", "documentVersion", "tags"}
_VERSION_FIELDS = {"fileId", "content", "changeNote"}
_REFERENCE_FIELDS = {"bidTaskId", "materialId"}
_SEMANTIC_SEARCH_TIMEOUT_SECONDS = 10.0


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


def _semantic_unavailable() -> AppException:
    return AppException(
        message="语义检索服务未配置或暂不可用",
        code="SERVICE_UNAVAILABLE",
        status_code=503,
    )


def _iso(value: datetime | None) -> str:
    current = value or _now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_internal(actor: AuthPrincipal) -> None:
    if actor.role not in {"admin", "project_lead", "member", "reviewer"}:
        raise forbidden("需要内部用户身份")


def _require_writer(actor: AuthPrincipal) -> None:
    if actor.role not in {"admin", "project_lead"}:
        raise forbidden("仅管理员或项目负责人可维护片段")


def _require_admin(actor: AuthPrincipal) -> None:
    if actor.role != "admin":
        raise forbidden("仅管理员可删除片段")


def _reject_unknown(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise validation_error(
            "请求包含未定义字段",
            [{"field": name, "code": "UNKNOWN", "message": "字段不在契约中"} for name in unknown],
        )


def _text(payload: dict[str, Any], name: str, *, required: bool, allow_empty: bool = False) -> str | None:
    if name not in payload:
        if required:
            raise validation_error(
                f"{name} 必填",
                [{"field": name, "code": "REQUIRED", "message": f"{name} 必填"}],
            )
        return None
    value = payload[name]
    if not isinstance(value, str):
        raise validation_error(
            f"{name} 必须是字符串",
            [{"field": name, "code": "TYPE", "message": f"{name} 必须是字符串"}],
        )
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise validation_error(
            f"{name} 不能为空",
            [{"field": name, "code": "REQUIRED", "message": f"{name} 不能为空"}],
        )
    return cleaned


def _tags(payload: dict[str, Any], *, required: bool) -> list[str] | None:
    if "tags" not in payload:
        if required:
            raise validation_error("tags 必填", [{"field": "tags", "code": "REQUIRED", "message": "tags 必填"}])
        return None
    raw = payload["tags"]
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise validation_error(
            "tags 必须是字符串数组",
            [{"field": "tags", "code": "TYPE", "message": "tags 必须是字符串数组"}],
        )
    return list(dict.fromkeys(item.strip() for item in raw if item.strip()))


def _file_dict(file: FileRefSnapshot | None) -> dict[str, Any] | None:
    if file is None:
        return None
    data: dict[str, Any] = {
        "id": file.id,
        "fileName": file.file_name,
        "mimeType": file.mime_type,
        "sizeBytes": file.size_bytes,
        "sha256": file.sha256,
        "scanStatus": file.scan_status,
        "createdAt": _iso(file.created_at),
    }
    if file.preview_url:
        data["previewUrl"] = file.preview_url
    if file.download_url:
        data["downloadUrl"] = file.download_url
    return data


def _fragment_dict(
    fragment: FragmentEntity,
    *,
    match_score: float | None = None,
    match_reason: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": fragment.id,
        "title": fragment.title,
        "category": fragment.category,
        "summary": fragment.summary,
        "content": fragment.content,
        "tags": list(fragment.tags),
        "documentVersion": fragment.document_version,
        "useCount": fragment.use_count,
        "version": fragment.version,
        "createdAt": _iso(fragment.created_at),
        "updatedAt": _iso(fragment.updated_at),
    }
    source_file = _file_dict(fragment.source_file)
    if source_file is not None:
        data["sourceFile"] = source_file
    if match_score is not None:
        data["matchScore"] = match_score
    if match_reason is not None:
        data["matchReason"] = match_reason
    return data


class FragmentService:
    def __init__(
        self,
        store: FragmentStore,
        *,
        bid_store: Any,
        files: FileServicePort,
        audit: AuditServicePort,
        semantic_search: SemanticSearchPort | None = None,
    ) -> None:
        self.store = store
        self.bid_store = bid_store
        self.files = files
        self.audit = audit
        self.semantic_search_port = semantic_search

    async def _clean_file(self, actor: AuthPrincipal, file_id: str) -> FileRefSnapshot:
        try:
            file = await self.files.assert_accessible(
                tenant_id=actor.tenant_id,
                file_id=file_id,
                actor_id=actor.user_id,
                purpose="fragment",
            )
        except KeyError as exc:
            raise not_found("源文件不存在或不可访问", fileId=file_id) from exc
        if file.scan_status != "clean":
            raise file_rejected("源文件必须通过安全扫描", fileId=file_id, scanStatus=file.scan_status)
        if file.sha256 == "0" * 64 or re.fullmatch(r"[a-fA-F0-9]{64}", file.sha256) is None:
            raise file_rejected("源文件摘要无效", fileId=file_id)
        return file

    async def _audit(self, actor: AuthPrincipal, fragment_id: str, action: str, summary: str) -> None:
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="fragment",
                aggregate_id=fragment_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action=action,
                summary=summary,
            )
        )

    async def stats(self, actor: AuthPrincipal) -> dict[str, int]:
        _require_internal(actor)
        items = self.store.list_active(tenant_id=actor.tenant_id)
        return {
            "total": len(items),
            "categoryCount": len({item.category for item in items}),
            "totalReferences": sum(item.use_count for item in items),
            # 本地相关度不是模型推荐，不能计入模型推荐统计。
            "semanticRecommended": 0,
        }

    async def list_fragments(
        self,
        actor: AuthPrincipal,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str | None = None,
        keyword: str | None = None,
        category: str | None = None,
        search_mode: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        _require_internal(actor)
        if page < 1 or not 1 <= page_size <= 100:
            raise validation_error("分页参数超出范围")
        if search_mode not in {None, "keyword", "semantic"}:
            raise validation_error("searchMode 必须是 keyword 或 semantic")
        if sort_order not in {None, "asc", "desc"}:
            raise validation_error("sortOrder 必须是 asc 或 desc")
        start = (page - 1) * page_size
        if keyword and search_mode == "semantic":
            data, total = await self._semantic_page(
                actor,
                query=keyword,
                category=category,
                offset=start,
                limit=page_size,
            )
            return data, {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": (total + page_size - 1) // page_size,
            }

        items = self.store.list_active(tenant_id=actor.tenant_id, category=category)
        if keyword:
            needle = keyword.casefold().strip()
            items = [item for item in items if needle in self._searchable_text(item)]

        descending = (sort_order or "desc") == "desc"
        selected_sort = sort_by or "updatedAt"
        if selected_sort == "title":
            items.sort(key=lambda item: item.title.casefold(), reverse=descending)
        elif selected_sort == "category":
            items.sort(key=lambda item: item.category.casefold(), reverse=descending)
        elif selected_sort == "useCount":
            items.sort(key=lambda item: item.use_count, reverse=descending)
        elif selected_sort == "createdAt":
            items.sort(
                key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
                reverse=descending,
            )
        elif selected_sort == "updatedAt":
            items.sort(
                key=lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
                reverse=descending,
            )
        else:
            raise validation_error("sortBy 不受支持")

        total = len(items)
        selected = items[start : start + page_size]
        data = [_fragment_dict(item) for item in selected]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size,
        }
        return data, meta

    async def create(self, actor: AuthPrincipal, payload: dict[str, Any]) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, _CREATE_FIELDS)
        title = _text(payload, "title", required=True)
        category = _text(payload, "category", required=True)
        summary = _text(payload, "summary", required=True)
        document_version = _text(payload, "documentVersion", required=True)
        content = _text(payload, "content", required=False, allow_empty=True) or ""
        tags = _tags(payload, required=True)
        source_file_id = _text(payload, "sourceFileId", required=False)
        if not content and not source_file_id:
            raise validation_error(
                "content 与 sourceFileId 至少提供一个",
                [{"field": "content", "code": "REQUIRED_ONE_OF", "message": "请提供正文或源文件"}],
            )
        source_file = await self._clean_file(actor, source_file_id) if source_file_id else None
        now = _now()
        fragment = FragmentEntity(
            id=_new_id(),
            tenant_id=actor.tenant_id,
            title=title or "",
            category=category or "",
            summary=summary or "",
            content=content,
            tags=tags or [],
            document_version=document_version or "",
            source_file=source_file,
            created_at=now,
            updated_at=now,
        )
        saved = self.store.save(fragment)
        self.store.save_version(
            FragmentVersionEntity(
                id=_new_id(),
                tenant_id=actor.tenant_id,
                fragment_id=saved.id,
                version_number=1,
                content=saved.content,
                document_version=saved.document_version,
                change_note="初始版本",
                created_by_id=actor.user_id,
                created_by_name=actor.name,
                source_file=saved.source_file,
                created_at=now,
            )
        )
        await self._audit(actor, saved.id, "fragment.created", f"创建片段 {saved.title}")
        return _fragment_dict(saved)

    async def get(self, actor: AuthPrincipal, fragment_id: str) -> dict[str, Any]:
        _require_internal(actor)
        return _fragment_dict(self.store.get(fragment_id, tenant_id=actor.tenant_id))

    async def update(
        self,
        actor: AuthPrincipal,
        fragment_id: str,
        payload: dict[str, Any],
        *,
        if_match: int,
    ) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, _UPDATE_FIELDS)
        if not payload:
            raise validation_error("至少提供一个待更新字段")
        fragment = self.store.get(fragment_id, tenant_id=actor.tenant_id)
        if fragment.version != if_match:
            raise version_conflict(fragment.version)
        values: dict[str, Any] = {}
        for request_name, entity_name in (
            ("title", "title"),
            ("category", "category"),
            ("summary", "summary"),
            ("documentVersion", "document_version"),
        ):
            value = _text(payload, request_name, required=False)
            if value is not None:
                values[entity_name] = value
        if "content" in payload:
            values["content"] = _text(payload, "content", required=False, allow_empty=True) or ""
        tags = _tags(payload, required=False)
        if tags is not None:
            values["tags"] = tags
        for name, value in values.items():
            setattr(fragment, name, value)
        if not fragment.content and fragment.source_file is None:
            raise validation_error("片段必须保留正文或源文件")
        fragment.version += 1
        fragment.updated_at = _now()
        saved = self.store.save(fragment)
        await self._audit(actor, saved.id, "fragment.updated", f"更新片段 {saved.title}")
        return _fragment_dict(saved)

    async def delete(self, actor: AuthPrincipal, fragment_id: str, payload: dict[str, Any]) -> None:
        _require_admin(actor)
        _reject_unknown(payload, {"reason"})
        reason = _text(payload, "reason", required=True)
        fragment = self.store.get(fragment_id, tenant_id=actor.tenant_id)
        fragment.deleted_at = _now()
        fragment.deletion_reason = reason
        fragment.version += 1
        fragment.updated_at = fragment.deleted_at
        self.store.save(fragment)
        await self._audit(actor, fragment.id, "fragment.deleted", f"删除片段 {fragment.title}：{reason}")

    async def add_version(
        self,
        actor: AuthPrincipal,
        fragment_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, _VERSION_FIELDS)
        change_note = _text(payload, "changeNote", required=True)
        content = _text(payload, "content", required=False, allow_empty=True)
        file_id = _text(payload, "fileId", required=False)
        if content is None and file_id is None:
            raise validation_error("fileId 与 content 至少提供一个")
        fragment = self.store.get(fragment_id, tenant_id=actor.tenant_id)
        source_file = await self._clean_file(actor, file_id) if file_id else fragment.source_file
        next_content = fragment.content if content is None else content
        if not next_content and source_file is None:
            raise validation_error("片段版本必须包含正文或源文件")
        fragment.content = next_content
        fragment.source_file = source_file
        fragment.version += 1
        fragment.updated_at = _now()
        saved = self.store.save(fragment)
        self.store.save_version(
            FragmentVersionEntity(
                id=_new_id(),
                tenant_id=actor.tenant_id,
                fragment_id=fragment.id,
                version_number=self.store.next_version_number(fragment.id),
                content=fragment.content,
                document_version=fragment.document_version,
                change_note=change_note or "",
                created_by_id=actor.user_id,
                created_by_name=actor.name,
                source_file=fragment.source_file,
                created_at=fragment.updated_at,
            )
        )
        await self._audit(actor, saved.id, "fragment.version_created", f"新增片段版本：{change_note}")
        return _fragment_dict(saved)

    async def add_reference(
        self,
        actor: AuthPrincipal,
        fragment_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _require_internal(actor)
        _reject_unknown(payload, _REFERENCE_FIELDS)
        bid_task_id = _text(payload, "bidTaskId", required=True)
        material_id = _text(payload, "materialId", required=False)
        if self.bid_store is None:
            raise conflict("M5 投标仓储尚未装配")
        fragment = self.store.get(fragment_id, tenant_id=actor.tenant_id)
        task = self.bid_store.get_task(bid_task_id, tenant_id=actor.tenant_id)
        assigned = task.assignee_id == actor.user_id or any(
            assignment.user_id == actor.user_id for assignment in task.assignments
        )
        if not assigned:
            raise forbidden("仅已分配到该投标任务的用户可引用片段")
        if material_id:
            material = self.bid_store.get_material(material_id, tenant_id=actor.tenant_id)
            if material.task_id != task.id:
                raise not_found("材料不属于该投标任务", materialId=material_id, bidTaskId=bid_task_id)
        self.store.save_reference(
            FragmentReferenceEntity(
                id=_new_id(),
                tenant_id=actor.tenant_id,
                fragment_id=fragment.id,
                bid_task_id=bid_task_id or "",
                material_id=material_id,
                actor_id=actor.user_id,
                created_at=_now(),
            )
        )
        fragment.use_count += 1
        fragment.version += 1
        fragment.updated_at = _now()
        saved = self.store.save(fragment)
        await self._audit(actor, saved.id, "fragment.referenced", f"片段引用到投标任务 {bid_task_id}")
        return {"referenced": True, "useCount": saved.use_count}

    async def semantic_search(
        self,
        actor: AuthPrincipal,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        _require_internal(actor)
        _reject_unknown(payload, {"query", "category", "limit"})
        query = _text(payload, "query", required=True)
        category = _text(payload, "category", required=False)
        limit = payload.get("limit")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise validation_error("limit 必须是 1 到 100 的整数")
        data, _ = await self._semantic_page(
            actor,
            query=query or "",
            category=category,
            offset=0,
            limit=limit,
        )
        return data

    async def _semantic_page(
        self,
        actor: AuthPrincipal,
        *,
        query: str,
        category: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        port = self.semantic_search_port
        if port is None:
            raise _semantic_unavailable()
        available = {item.id: item for item in self.store.list_active(tenant_id=actor.tenant_id, category=category)}
        request = SemanticSearchRequest(
            tenant_id=actor.tenant_id,
            query=query,
            category=category,
            offset=offset,
            limit=limit,
        )
        try:
            result = await asyncio.wait_for(
                port.search(request),
                timeout=_SEMANTIC_SEARCH_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise _semantic_unavailable() from exc
        except Exception as exc:
            raise _semantic_unavailable() from exc
        if not isinstance(result, SemanticSearchResult):
            raise _semantic_unavailable()
        if (
            isinstance(result.total, bool)
            or not isinstance(result.total, int)
            or not 0 <= result.total <= len(available)
            or not isinstance(result.hits, tuple)
        ):
            raise _semantic_unavailable()
        expected_hits = min(limit, max(result.total - offset, 0))
        if len(result.hits) != expected_hits:
            raise _semantic_unavailable()

        seen: set[str] = set()
        data: list[dict[str, Any]] = []
        for hit in result.hits:
            if (
                not isinstance(hit, SemanticSearchHit)
                or not isinstance(hit.fragment_id, str)
                or not hit.fragment_id
                or not isinstance(hit.match_reason, str)
            ):
                raise _semantic_unavailable()
            fragment = available.get(hit.fragment_id)
            score = hit.match_score
            reason = hit.match_reason.strip()
            if (
                fragment is None
                or hit.fragment_id in seen
                or isinstance(score, bool)
                or not isinstance(score, int | float)
                or not 0 <= score <= 1
                or not reason
            ):
                raise _semantic_unavailable()
            seen.add(hit.fragment_id)
            data.append(
                _fragment_dict(
                    fragment,
                    match_score=float(score),
                    match_reason=reason,
                )
            )
        return data, result.total

    @staticmethod
    def _searchable_text(fragment: FragmentEntity) -> str:
        return " ".join(
            (fragment.title, fragment.category, fragment.summary, fragment.content, *fragment.tags)
        ).casefold()
