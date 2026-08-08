"""系统设置 API 路由.

当前 Demo 尚未引入 ModelProvider 与设置表，因此配置保存在进程内；密钥始终
先加密再保存。接口形状保持稳定，后续切换数据库实现时前端和 M7 无需改动。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, status

from app.core.dependencies import AdminUser, DBSession
from app.core.errors import NotFoundError
from app.domains.settings.schemas.settings import (
    AgentStatusResponse,
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
)
from app.domains.settings.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["系统设置"])

_model_providers: dict[tuple[UUID | None, UUID], ModelProviderResponse] = {}
_model_routes: dict[UUID | None, list[ModelRouteResponse]] = {}
_generation_settings: dict[UUID | None, GenerationSettingsResponse] = {}
_deployment_settings: dict[UUID | None, DeploymentSettingsResponse] = {}
_document_templates: dict[UUID | None, DocumentTemplateResponse] = {}
_notification_settings: dict[UUID | None, NotificationSettingsResponse] = {}


def _tenant_id(current_user: dict[str, Any]) -> UUID | None:
    """Extract the optional tenant UUID from an authenticated user context."""
    value = current_user.get("tenant_id")
    return UUID(str(value)) if value else None


def _provider_key(current_user: dict[str, Any], provider_id: UUID) -> tuple[UUID | None, UUID]:
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
        events={},
        version=1,
    )


@router.get("/model-providers", response_model=list[ModelProviderResponse])
async def list_model_providers(
    current_user: AdminUser,
    db: DBSession,
) -> list[ModelProviderResponse]:
    """获取当前租户的模型服务商列表（密钥仅返回脱敏值）."""
    tenant_id = _tenant_id(current_user)
    return [provider for (tenant, _), provider in _model_providers.items() if tenant == tenant_id]


@router.post(
    "/model-providers",
    response_model=ModelProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_provider(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> ModelProviderResponse:
    """添加模型服务商并加密保存 API Key."""
    payload = ModelProviderRequest.model_validate(request)
    provider_id = uuid4()
    tenant_id = _tenant_id(current_user)
    await SettingsService(db).save_model_provider_api_key(provider_id, payload.api_key, tenant_id)
    response = ModelProviderResponse(
        id=provider_id,
        provider=payload.provider,
        display_name=payload.display_name,
        base_url=payload.base_url,
        api_key_masked=SettingsService(db).mask_key(payload.api_key),
        key_last_four=payload.api_key[-4:],
        enabled=payload.enabled,
        connection_status="untested",
        last_tested_at=None,
        version=1,
    )
    _model_providers[(tenant_id, provider_id)] = response
    return response


@router.patch("/model-providers/{provider_id}", response_model=ModelProviderResponse)
async def update_model_provider(
    provider_id: UUID,
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> ModelProviderResponse:
    """更新模型服务商配置，并在提供新密钥时重新加密保存."""
    key = _provider_key(current_user, provider_id)
    existing = _model_providers.get(key)
    if existing is None:
        raise NotFoundError(
            message="模型服务商不存在",
            resource_type="model_provider",
            resource_id=str(provider_id),
        )

    values = existing.model_dump()
    for field in ("provider", "display_name", "base_url", "enabled"):
        if field in request:
            values[field] = request[field]
    api_key = request.get("api_key")
    if api_key is not None:
        api_key = str(api_key)
        await SettingsService(db).save_model_provider_api_key(provider_id, api_key, key[0])
        values["api_key_masked"] = SettingsService(db).mask_key(api_key)
        values["key_last_four"] = api_key[-4:]
        values["connection_status"] = "untested"
        values["last_tested_at"] = None
    values["version"] = existing.version + 1
    updated = ModelProviderResponse.model_validate(values)
    _model_providers[key] = updated
    return updated


@router.post(
    "/model-providers/{provider_id}/test",
    status_code=status.HTTP_202_ACCEPTED,
)
async def test_model_provider(
    provider_id: UUID,
    current_user: AdminUser,
    db: DBSession,
) -> dict[str, Any]:
    """启动 Demo 连接测试并返回可跟踪的任务标识."""
    key = _provider_key(current_user, provider_id)
    provider = _model_providers.get(key)
    if provider is None:
        raise NotFoundError(
            message="模型服务商不存在",
            resource_type="model_provider",
            resource_id=str(provider_id),
        )
    _model_providers[key] = provider.model_copy(
        update={"connection_status": "connected", "last_tested_at": datetime.now(UTC)}
    )
    return {"job_id": str(uuid4())}


@router.get("/model-routes", response_model=list[ModelRouteResponse])
async def get_model_routes(
    current_user: AdminUser,
    db: DBSession,
) -> list[ModelRouteResponse]:
    """获取当前租户的场景路由配置."""
    return list(_model_routes.get(_tenant_id(current_user), []))


@router.put("/model-routes", response_model=list[ModelRouteResponse])
async def update_model_routes(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> list[ModelRouteResponse]:
    """整体替换当前租户的场景路由配置."""
    routes = [
        ModelRouteResponse.model_validate(ModelRouteRequest.model_validate(item).model_dump())
        for item in request.get("routes", [])
    ]
    _model_routes[_tenant_id(current_user)] = routes
    return routes


@router.get("/generation", response_model=GenerationSettingsResponse)
async def get_generation_settings(
    current_user: AdminUser,
    db: DBSession,
) -> GenerationSettingsResponse:
    """获取 AI 生成参数."""
    return _generation_settings.get(_tenant_id(current_user), _default_generation_settings())


@router.put("/generation", response_model=GenerationSettingsResponse)
async def update_generation_settings(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> GenerationSettingsResponse:
    """更新 AI 生成参数."""
    current = await get_generation_settings(current_user, db)
    payload = GenerationSettingsRequest.model_validate({**current.model_dump(), **request})
    updated = GenerationSettingsResponse.model_validate(payload.model_dump())
    _generation_settings[_tenant_id(current_user)] = updated
    return updated


@router.get("/deployment", response_model=DeploymentSettingsResponse)
async def get_deployment_settings(
    current_user: AdminUser,
    db: DBSession,
) -> DeploymentSettingsResponse:
    """获取部署设置."""
    return _deployment_settings.get(_tenant_id(current_user), _default_deployment_settings())


@router.put("/deployment", response_model=DeploymentSettingsResponse)
async def update_deployment_settings(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> DeploymentSettingsResponse:
    """更新部署设置并递增乐观锁版本号."""
    current = await get_deployment_settings(current_user, db)
    values = {**current.model_dump(exclude={"version"}), **request}
    payload = DeploymentSettingsRequest.model_validate(values)
    updated = DeploymentSettingsResponse(**payload.model_dump(), version=current.version + 1)
    _deployment_settings[_tenant_id(current_user)] = updated
    return updated


@router.get("/document-template", response_model=DocumentTemplateResponse)
async def get_document_template(
    current_user: AdminUser,
    db: DBSession,
) -> DocumentTemplateResponse:
    """获取投标文档模板设置."""
    return _document_templates.get(_tenant_id(current_user), _default_document_template())


@router.put("/document-template", response_model=DocumentTemplateResponse)
async def update_document_template(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> DocumentTemplateResponse:
    """更新投标文档模板设置."""
    current = await get_document_template(current_user, db)
    values = {**current.model_dump(exclude={"version"}), **request}
    payload = DocumentTemplateRequest.model_validate(values)
    updated = DocumentTemplateResponse(**payload.model_dump(), version=current.version + 1)
    _document_templates[_tenant_id(current_user)] = updated
    return updated


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: AdminUser,
    db: DBSession,
) -> NotificationSettingsResponse:
    """获取通知策略设置."""
    return _notification_settings.get(_tenant_id(current_user), _default_notification_settings())


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> NotificationSettingsResponse:
    """更新通知策略设置."""
    current = await get_notification_settings(current_user, db)
    values = {**current.model_dump(exclude={"version"}), **request}
    payload = NotificationSettingsRequest.model_validate(values)
    updated = NotificationSettingsResponse(**payload.model_dump(), version=current.version + 1)
    _notification_settings[_tenant_id(current_user)] = updated
    return updated


@router.get("/agents/status", response_model=list[AgentStatusResponse])
async def get_agents_status(
    current_user: AdminUser,
    db: DBSession,
) -> list[AgentStatusResponse]:
    """返回智能体状态；M7 接入运行时心跳前默认无已注册实例."""
    return []
