"""资质库仓储；测试和当前模块化单体阶段使用可替换的内存实现。"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Sequence
from dataclasses import replace
from typing import Any, Literal

from app.domains.bids.errors import conflict, not_found
from app.domains.bids.ports import JobRefSnapshot, Role
from app.domains.qualifications.entities import (
    QualificationEntity,
    QualificationImportBindingEntity,
    QualificationVersionEntity,
)


class QualificationStore:
    def __init__(self) -> None:
        self.import_lock = asyncio.Lock()
        self.qualifications: dict[str, QualificationEntity] = {}
        self.versions: dict[str, QualificationVersionEntity] = {}
        self.import_jobs: dict[tuple[str, str], JobRefSnapshot] = {}
        self.import_bindings: dict[str, QualificationImportBindingEntity] = {}
        self.import_results: dict[str, tuple[str, str, str, str, Any]] = {}

    def save(self, entity: QualificationEntity) -> QualificationEntity:
        self.qualifications[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get(self, qualification_id: str, *, tenant_id: str) -> QualificationEntity:
        entity = self.qualifications.get(qualification_id)
        if entity is None or entity.tenant_id != tenant_id or entity.deleted_at is not None:
            raise not_found("资质不存在", qualificationId=qualification_id)
        return copy.deepcopy(entity)

    def list(self, *, tenant_id: str) -> list[QualificationEntity]:
        return [
            copy.deepcopy(item)
            for item in self.qualifications.values()
            if item.tenant_id == tenant_id and item.deleted_at is None
        ]

    def cert_number_exists(self, *, tenant_id: str, cert_number: str, exclude_id: str | None = None) -> bool:
        return any(
            item.tenant_id == tenant_id
            and item.cert_number.casefold() == cert_number.casefold()
            and item.id != exclude_id
            for item in self.qualifications.values()
        )

    def save_version(self, entity: QualificationVersionEntity) -> QualificationVersionEntity:
        self.versions[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_import_job(self, *, tenant_id: str, file_id: str) -> JobRefSnapshot | None:
        job = self.import_jobs.get((tenant_id, file_id))
        return copy.deepcopy(job) if job is not None else None

    def remember_import_job(
        self,
        *,
        tenant_id: str,
        file_id: str,
        job: JobRefSnapshot,
        category: str,
        actor_id: str,
        actor_name: str,
        actor_role: Role,
    ) -> JobRefSnapshot:
        binding = QualificationImportBindingEntity(
            job_id=job.id,
            tenant_id=tenant_id,
            category=category,
            source_file_id=file_id,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
        )
        existing = self.import_bindings.get(job.id)
        if existing is not None and existing != binding:
            raise conflict("异步任务已绑定到其他资质导入请求", jobId=job.id)
        self.import_jobs[(tenant_id, file_id)] = copy.deepcopy(job)
        self.import_bindings[job.id] = copy.deepcopy(binding)
        return copy.deepcopy(job)

    def get_import_binding(self, job_id: str, *, tenant_id: str) -> QualificationImportBindingEntity:
        binding = self.import_bindings.get(job_id)
        if binding is None or binding.tenant_id != tenant_id:
            raise not_found("资质导入任务不存在", jobId=job_id)
        return copy.deepcopy(binding)

    def get_import_result(
        self,
        binding: QualificationImportBindingEntity,
        *,
        outcome: Literal["succeeded", "failed"],
    ) -> Any | None:
        stored = self.import_results.get(binding.job_id)
        if stored is None:
            return None
        tenant_id, category, source_file_id, stored_outcome, value = stored
        if (tenant_id, category, source_file_id) != (
            binding.tenant_id,
            binding.category,
            binding.source_file_id,
        ):
            raise conflict("资质导入结果与原始任务不匹配", jobId=binding.job_id)
        if stored_outcome != outcome:
            raise conflict(
                "资质导入任务已有相反的终态结果",
                jobId=binding.job_id,
                terminalOutcome=stored_outcome,
            )
        return copy.deepcopy(value)

    def remember_import_result(
        self,
        binding: QualificationImportBindingEntity,
        *,
        outcome: Literal["succeeded", "failed"],
        value: Any,
        qualifications: Sequence[QualificationEntity] | None = None,
        versions: Sequence[QualificationVersionEntity] | None = None,
    ) -> None:
        existing = self.import_results.get(binding.job_id)
        expected_prefix = (binding.tenant_id, binding.category, binding.source_file_id, outcome)
        if existing is not None:
            if existing[:4] != expected_prefix:
                raise conflict(
                    "资质导入任务已有相反的终态结果",
                    jobId=binding.job_id,
                    terminalOutcome=existing[3],
                )
            return
        for entity in qualifications or []:
            if self.cert_number_exists(tenant_id=entity.tenant_id, cert_number=entity.cert_number):
                raise conflict("同一租户内证书编号已存在", certNumber=entity.cert_number)
        self.qualifications.update({entity.id: copy.deepcopy(entity) for entity in qualifications or []})
        self.versions.update({version.id: copy.deepcopy(version) for version in versions or []})
        self.import_results[binding.job_id] = (*expected_prefix, copy.deepcopy(value))
        import_key = (binding.tenant_id, binding.source_file_id)
        job = self.import_jobs.get(import_key)
        if job is not None and job.id == binding.job_id:
            self.import_jobs[import_key] = replace(
                job,
                status=outcome,
                progress_percent=100 if outcome == "succeeded" else job.progress_percent,
                current_step=outcome,
            )


def qualification_from_orm_row(row: Any, *, file: Any) -> QualificationEntity:
    """供 L0 持久化适配器把 ORM 行映射为领域实体。"""
    return QualificationEntity(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        name=str(row.name),
        category=str(row.category),
        cert_number=str(row.cert_number),
        issuer=str(row.issuer),
        valid_from=row.valid_from,
        expiry_date=row.expiry_date,
        file=file,
        document_version=str(row.document_version),
        reminder_days=list(row.reminder_days or []),
        tags=list(row.tags or []),
        version=int(row.version),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        deleted_by=str(row.deleted_by) if row.deleted_by else None,
        deleted_reason=row.deleted_reason,
    )
