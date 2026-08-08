"""M4 公共平台后端 - settings 领域."""

from app.domains.settings.services.settings_service import (
    SettingsService,
    get_model_api_key,
)

__all__ = [
    "SettingsService",
    "get_model_api_key",
]
