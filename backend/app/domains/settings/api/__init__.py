"""Tenant-scoped system settings API with contract-consistent envelopes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import AdminUser, DBSession
from app.core.errors import NotFoundError
from app.core.http import contract_data, success_response
from app.domains.jobs.mappers import job_to_data
from app.domains.jobs.models.job import JobType
from app.domains.jobs.services.job_service import JobService
from app.domains.settings.schemas.settings import (
    DeploymentSettingsRequest,
    DeploymentSettingsResponse,
    DocumentTemplateRequest,
    DocumentTemplateResponse,
    GenerationSettingsRequest,
    GenerationSettingsResponse,
    ModelProviderRequest,
    ModelProviderResponse,
    ModelRouteRequest,
    ModelRouteResponse,
    NotificationSettingsRequest,
    NotificationSettingsResponse,
    UpdateModelProviderRequest,
)
from app.domains.settings.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["系统设置"])

# Demo settings are tenant-isolated and process-local. Secrets are encrypted before storage.
_model_providers: dict[tuple[UUID, UUID], ModelProviderResponse] = {}
_model_routes: dict[UUID, list[ModelRouteResponse]] = {}
_generation_settings: dict[UUID, GenerationSettingsResponse] = {}
_deployment_settings: dict[UUID, DeploymentSettingsResponse] = {}
_document_templates: dict[UUID, DocumentTemplateResponse] = {}
_notification_settings: dict[UUID, NotificationSettingsResponse] = {}


def _tenant_id(current_user: dict[str, Any]) -> UUID:
    return UUID(str(current_user["tenant_id"]))


def _provider_key(current_user: dict[str, Any], provider_id: UUID) -> tuple[UUID, UUID]:
    return (_tenant_id(current_user), provider_id)


def _default_generation_settings() -> GenerationSettingsResponse:
    return GenerationSettingsResponse(
        temperature=0.3,
        top_p=0.9,
        max_output_tokens=8192,
        request_timeout_seconds=60,
        auto_retry=True,
        circuit_breaker_enabled=True,
    )


def _default_deployment_settings() -> DeploymentSettingsResponse:
    return DeploymentSettingsResponse(
        mode="saas",
        company_name="示例公司",
        storage_quota_bytes=500 * 1024 * 1024 * 1024,
        max_projects=50,
        max_users=30,
        auto_backup=True,
        backup_cron="0 2 * * *",
        version_control_enabled=True,
        version=1,
    )


def _default_document_template() -> DocumentTemplateResponse:
    return DocumentTemplateResponse(
        format="standard",
        page_size="A4",
        body_font="宋体",
        body_font_size_pt=12,
        line_spacing=1.5,
        margin_mode="standard",
        split_by_section=True,
        watermark_enabled=False,
        watermark_text=None,
        version=1,
    )


def _default_notification_settings() -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        in_app_enabled=True,
        email_enabled=False,
        qualification_reminder_days=[30, 60, 90],
        events={
            "jobCompleted": True,
            "reviewCompleted": True,
            "qualificationExpiring": True,
        },
        version=1,
    )


def _version_guard(if_match: str, current_version: int) -> None:
    if if_match != f'"{current_version}"':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "VERSION_CONFLICT", "message": "设置已被其他操作更新，请刷新后重试"},
        )


@router.get("/model-providers")
async def list_model_providers(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    tenant_id = _tenant_id(current_user)
    providers = [provider for (tenant, _), provider in _model_providers.items() if tenant == tenant_id]
    _ = db
    return success_response(contract_data(providers), request=request)


@router.post("/model-providers", status_code=201)
async def create_model_provider(
    payload: ModelProviderRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    provider_id = uuid4()
    tenant_id = _tenant_id(current_user)
    service = SettingsService(db)
    await service.save_model_provider_api_key(provider_id, payload.api_key, tenant_id)
    response = ModelProviderResponse(
        id=provider_id,
        provider=payload.provider,
        display_name=payload.display_name,
        base_url=payload.base_url,
        api_key_masked=service.mask_key(payload.api_key),
        key_last_four=payload.api_key[-4:],
        enabled=payload.enabled,
        connection_status="unknown",
        last_tested_at=None,
        version=1,
    )
    _model_providers[(tenant_id, provider_id)] = response
    return success_response(contract_data(response), request=request, status_code=201)


@router.patch("/model-providers/{provider_id}")
async def update_model_provider(
    provider_id: UUID,
    payload: UpdateModelProviderRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
    if_match: str = Header(..., alias="If-Match"),
) -> JSONResponse:
    key = _provider_key(current_user, provider_id)
    existing = _model_providers.get(key)
    if existing is None:
        raise NotFoundError(message="模型服务商不存在", resource_type="model_provider", resource_id=str(provider_id))
    _version_guard(if_match, existing.version)

    values = existing.model_dump()
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    api_key = updates.pop("api_key", None)
    values.update(updates)
    if api_key is not None:
        service = SettingsService(db)
        await service.save_model_provider_api_key(provider_id, api_key, key[0])
        values["api_key_masked"] = service.mask_key(api_key)
        values["key_last_four"] = api_key[-4:]
        values["connection_status"] = "unknown"
        values["last_tested_at"] = None
    values["version"] = existing.version + 1
    updated = ModelProviderResponse.model_validate(values)
    _model_providers[key] = updated
    return success_response(contract_data(updated), request=request)


@router.post("/model-providers/{provider_id}/test", status_code=202)
async def test_model_provider(
    provider_id: UUID,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    """Run a real provider connectivity check and expose it through a JobRef."""
    key = _provider_key(current_user, provider_id)
    provider = _model_providers.get(key)
    if provider is None:
        raise NotFoundError(message="模型服务商不存在", resource_type="model_provider", resource_id=str(provider_id))

    job_service = JobService(db)
    job = await job_service.create_job(
        user_id=UUID(str(current_user["id"])),
        tenant_id=key[0],
        job_type=JobType.AI_ANALYSIS,
        input_data={"scene": "provider_connection_test", "providerId": str(provider_id)},
    )
    job = await job_service.mark_job_started(job.id)
    try:
        if settings.ai_fake_provider:
            result = {"connected": True, "mode": "configured_fake_provider"}
        else:
            api_key = await SettingsService(db).get_decrypted_api_key(provider_id, key[0])
            endpoint = provider.base_url.rstrip("/") + "/models"
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint, headers={"Authorization": f"Bearer {api_key}"})
                response.raise_for_status()
            result = {"connected": True, "statusCode": response.status_code}
        job = await job_service.mark_job_succeeded(job.id, result=result)
        _model_providers[key] = provider.model_copy(
            update={"connection_status": "connected", "last_tested_at": datetime.now(UTC)}
        )
    except Exception as exc:
        job = await job_service.mark_job_failed(
            job.id,
            error={"code": "AI_PROVIDER_UNAVAILABLE", "message": str(exc), "retryable": True},
        )
        _model_providers[key] = provider.model_copy(
            update={"connection_status": "failed", "last_tested_at": datetime.now(UTC)}
        )
    return success_response(job_to_data(job), request=request, status_code=202)


@router.get("/model-routes")
async def get_model_routes(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    _ = db
    return success_response(contract_data(_model_routes.get(_tenant_id(current_user), [])), request=request)


@router.put("/model-routes")
async def update_model_routes(
    payload: dict[str, Any],
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    routes = [
        ModelRouteResponse.model_validate(ModelRouteRequest.model_validate(item).model_dump())
        for item in payload["routes"]
    ]
    _model_routes[_tenant_id(current_user)] = routes
    _ = db
    return success_response(contract_data(routes), request=request)


def _generation_for(tenant_id: UUID) -> GenerationSettingsResponse:
    return _generation_settings.get(tenant_id, _default_generation_settings())


@router.get("/generation")
async def get_generation_settings(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    _ = db
    return success_response(contract_data(_generation_for(_tenant_id(current_user))), request=request)


@router.put("/generation")
async def update_generation_settings(
    payload: GenerationSettingsRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    updated = GenerationSettingsResponse.model_validate(payload.model_dump())
    _generation_settings[_tenant_id(current_user)] = updated
    _ = db
    return success_response(contract_data(updated), request=request)


def _deployment_for(tenant_id: UUID) -> DeploymentSettingsResponse:
    return _deployment_settings.get(tenant_id, _default_deployment_settings())


@router.get("/deployment")
async def get_deployment_settings(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    _ = db
    return success_response(contract_data(_deployment_for(_tenant_id(current_user))), request=request)


@router.put("/deployment")
async def update_deployment_settings(
    payload: DeploymentSettingsRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    tenant_id = _tenant_id(current_user)
    current = _deployment_for(tenant_id)
    updated = DeploymentSettingsResponse(**payload.model_dump(), version=current.version + 1)
    _deployment_settings[tenant_id] = updated
    _ = db
    return success_response(contract_data(updated), request=request)


def _document_template_for(tenant_id: UUID) -> DocumentTemplateResponse:
    return _document_templates.get(tenant_id, _default_document_template())


@router.get("/document-template")
async def get_document_template(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    _ = db
    return success_response(contract_data(_document_template_for(_tenant_id(current_user))), request=request)


@router.put("/document-template")
async def update_document_template(
    payload: DocumentTemplateRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    tenant_id = _tenant_id(current_user)
    current = _document_template_for(tenant_id)
    updated = DocumentTemplateResponse(**payload.model_dump(), version=current.version + 1)
    _document_templates[tenant_id] = updated
    _ = db
    return success_response(contract_data(updated), request=request)


def _notification_settings_for(tenant_id: UUID) -> NotificationSettingsResponse:
    return _notification_settings.get(tenant_id, _default_notification_settings())


@router.get("/notifications")
async def get_notification_settings(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    _ = db
    return success_response(contract_data(_notification_settings_for(_tenant_id(current_user))), request=request)


@router.put("/notifications")
async def update_notification_settings(
    payload: NotificationSettingsRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    tenant_id = _tenant_id(current_user)
    current = _notification_settings_for(tenant_id)
    updated = NotificationSettingsResponse(**payload.model_dump(), version=current.version + 1)
    _notification_settings[tenant_id] = updated
    _ = db
    return success_response(contract_data(updated), request=request)


def _worker_snapshot() -> tuple[str, int]:
    from app.workers.celery_app import celery_app

    if bool(celery_app.conf.task_always_eager):
        return "online", 0
    inspector = celery_app.control.inspect(timeout=0.75)
    ping = inspector.ping() or {}
    reserved = inspector.reserved() or {}
    queue_depth = sum(len(items) for items in reserved.values())
    return ("online" if ping else "offline"), queue_depth


@router.get("/agents/status")
async def get_agents_status(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    """Report the actual eager/worker runtime state for every AI scene group."""
    worker_status, queue_depth = await asyncio.to_thread(_worker_snapshot)
    now = datetime.now(UTC) if worker_status == "online" else None
    scenes = [
        ("投标解析智能体", "tender_parse"),
        ("标书生成智能体", "bid_generate"),
        ("标书评审智能体", "bid_review"),
        ("评标风控智能体", "risk_check"),
        ("评标报告智能体", "report_generate"),
    ]
    data = [
        {
            "name": name,
            "scene": scene,
            "status": worker_status,
            "activeProvider": "fake" if settings.ai_fake_provider else settings.ai_default_provider,
            "activeModel": "deterministic-demo" if settings.ai_fake_provider else None,
            "queueDepth": queue_depth,
            "lastHeartbeatAt": now,
        }
        for name, scene in scenes
    ]
    _ = current_user, db
    return success_response(data, request=request)
