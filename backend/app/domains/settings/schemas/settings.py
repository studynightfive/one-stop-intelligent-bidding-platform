"""设置schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelProviderRequest(BaseModel):
    """模型服务商请求."""

    provider: str = Field(..., description="提供商: qwen/deepseek/zhipu/custom_openai_compatible")
    display_name: str = Field(..., description="显示名称")
    base_url: str = Field(..., description="API地址")
    api_key: str = Field(..., description="API密钥")
    enabled: bool = Field(True, description="是否启用")


class ModelProviderResponse(BaseModel):
    """模型服务商响应."""

    id: UUID = Field(..., description="ID")
    provider: str = Field(..., description="提供商")
    display_name: str = Field(..., description="显示名称")
    base_url: str = Field(..., description="API地址")
    api_key_masked: str = Field(..., description="脱敏密钥")
    key_last_four: str = Field(..., description="密钥末四位")
    enabled: bool = Field(..., description="是否启用")
    connection_status: str = Field(..., description="连接状态")
    last_tested_at: datetime | None = Field(None, description="最后测试时间")
    version: int = Field(..., description="版本号")


class ModelRouteRequest(BaseModel):
    """模型路由请求."""

    scene: str = Field(..., description="场景")
    primary_provider_id: UUID = Field(..., description="主提供商ID")
    primary_model: str = Field(..., description="主模型")
    fallback_provider_id: UUID = Field(..., description="备用提供商ID")
    fallback_model: str = Field(..., description="备用模型")
    timeout_seconds: int = Field(60, description="超时时间")
    max_retries: int = Field(3, description="最大重试次数")
    circuit_breaker_failures: int = Field(3, description="熔断失败次数")


class ModelRouteResponse(BaseModel):
    """模型路由响应."""

    scene: str = Field(..., description="场景")
    primary_provider_id: UUID = Field(..., description="主提供商ID")
    primary_model: str = Field(..., description="主模型")
    fallback_provider_id: UUID = Field(..., description="备用提供商ID")
    fallback_model: str = Field(..., description="备用模型")
    timeout_seconds: int = Field(..., description="超时时间")
    max_retries: int = Field(..., description="最大重试次数")
    circuit_breaker_failures: int = Field(..., description="熔断失败次数")


class GenerationSettingsRequest(BaseModel):
    """生成参数请求."""

    temperature: float = Field(0.3, ge=0, le=2, description="温度参数")
    top_p: float = Field(0.9, ge=0, le=1, description="Top-P参数")
    max_output_tokens: int = Field(8192, ge=1, description="最大输出Token数")
    request_timeout_seconds: int = Field(60, ge=1, description="请求超时秒数")
    auto_retry: bool = Field(True, description="自动重试")
    circuit_breaker_enabled: bool = Field(True, description="启用熔断")


class GenerationSettingsResponse(BaseModel):
    """生成参数响应."""

    temperature: float = Field(..., description="温度参数")
    top_p: float = Field(..., description="Top-P参数")
    max_output_tokens: int = Field(..., description="最大输出Token数")
    request_timeout_seconds: int = Field(..., description="请求超时秒数")
    auto_retry: bool = Field(..., description="自动重试")
    circuit_breaker_enabled: bool = Field(..., description="启用熔断")


class DeploymentSettingsRequest(BaseModel):
    """部署设置请求."""

    mode: str = Field(..., description="模式: saas/private")
    company_name: str = Field(..., description="公司名称")
    storage_quota_bytes: int = Field(..., description="存储配额(字节)")
    max_projects: int = Field(..., description="最大项目数")
    max_users: int = Field(..., description="最大用户数")
    auto_backup: bool = Field(True, description="自动备份")
    backup_cron: str = Field("0 2 * * *", description="备份Cron表达式")
    version_control_enabled: bool = Field(True, description="启用版本控制")


class DeploymentSettingsResponse(BaseModel):
    """部署设置响应."""

    mode: str = Field(..., description="模式")
    company_name: str = Field(..., description="公司名称")
    storage_quota_bytes: int = Field(..., description="存储配额")
    max_projects: int = Field(..., description="最大项目数")
    max_users: int = Field(..., description="最大用户数")
    auto_backup: bool = Field(..., description="自动备份")
    backup_cron: str = Field(..., description="备份Cron")
    version_control_enabled: bool = Field(..., description="启用版本控制")
    version: int = Field(..., description="版本号")


class DocumentTemplateRequest(BaseModel):
    """文档模板设置请求."""

    format: str = Field("standard", description="格式: standard/custom")
    page_size: str = Field("A4", description="页面大小")
    body_font: str = Field("宋体", description="正文字体")
    body_font_size_pt: int = Field(12, description="正文字号(pt)")
    line_spacing: float = Field(1.5, description="行间距")
    margin_mode: str = Field("standard", description="边距模式")
    split_by_section: bool = Field(True, description="按章节拆分")
    watermark_enabled: bool = Field(False, description="启用水印")
    watermark_text: str | None = Field(None, description="水印文本")


class DocumentTemplateResponse(BaseModel):
    """文档模板设置响应."""

    format: str = Field(..., description="格式")
    page_size: str = Field(..., description="页面大小")
    body_font: str = Field(..., description="正文字体")
    body_font_size_pt: int = Field(..., description="正文字号")
    line_spacing: float = Field(..., description="行间距")
    margin_mode: str = Field(..., description="边距模式")
    split_by_section: bool = Field(..., description="按章节拆分")
    watermark_enabled: bool = Field(..., description="启用水印")
    watermark_text: str | None = Field(None, description="水印文本")
    version: int = Field(..., description="版本号")


class NotificationSettingsRequest(BaseModel):
    """通知设置请求."""

    in_app_enabled: bool = Field(True, description="启用站内通知")
    email_enabled: bool = Field(False, description="启用邮件通知")
    qualification_reminder_days: list[int] = Field([30, 60, 90], description="资质提醒天数")
    events: dict[str, bool] = Field(..., description="事件开关")


class NotificationSettingsResponse(BaseModel):
    """通知设置响应."""

    in_app_enabled: bool = Field(..., description="启用站内通知")
    email_enabled: bool = Field(..., description="启用邮件通知")
    qualification_reminder_days: list[int] = Field(..., description="资质提醒天数")
    events: dict[str, bool] = Field(..., description="事件开关")
    version: int = Field(..., description="版本号")


class AgentStatusResponse(BaseModel):
    """Agent状态响应."""

    name: str = Field(..., description="Agent名称")
    scene: str = Field(..., description="场景")
    status: str = Field(..., description="状态: online/degraded/offline/standby")
    active_provider: str | None = Field(None, description="当前提供商")
    active_model: str | None = Field(None, description="当前模型")
    queue_depth: int = Field(..., description="队列深度")
    last_heartbeat_at: datetime | None = Field(None, description="最后心跳时间")
