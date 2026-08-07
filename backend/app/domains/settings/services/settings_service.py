"""设置服务.

提供系统设置的读取和管理功能。
供 M7 调用以获取模型密钥等敏感信息。
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.security.jwt import decrypt_api_key, encrypt_api_key, mask_api_key


class SettingsService:
    """设置服务.

    使用示例:
        settings_service = SettingsService(db)

        # 获取解密后的 API Key（供 M7 使用）
        api_key = await settings_service.get_decrypted_api_key(provider_id)

        # 保存加密的 API Key
        await settings_service.save_model_provider_api_key(provider_id, api_key)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_decrypted_api_key(
        self,
        provider_id: UUID,
        tenant_id: UUID | None = None,
    ) -> str:
        """获取解密后的模型 API Key.

        这是 SettingsService 的核心功能，供 M7 调用。

        Args:
            provider_id: 服务商ID
            tenant_id: 租户ID（用于权限检查，可选）

        Returns:
            解密后的明文 API Key

        Raises:
            NotFoundError: 服务商不存在
            PermissionDeniedError: 无权访问
        """
        # TODO: 从数据库查询加密的 API Key 并解密
        # 目前返回空字符串，后续需要实现数据库模型
        raise NotImplementedError("需要先实现 ModelProvider 模型")

    def encrypt_key(self, plain_key: str) -> str:
        """加密 API Key.

        Args:
            plain_key: 明文 API Key

        Returns:
            加密后的字符串
        """
        return encrypt_api_key(plain_key)

    def decrypt_key(self, encrypted_key: str) -> str:
        """解密 API Key.

        Args:
            encrypted_key: 加密的字符串

        Returns:
            明文 API Key
        """
        return decrypt_api_key(encrypted_key)

    def mask_key(self, api_key: str, visible_chars: int = 4) -> str:
        """脱敏 API Key.

        Args:
            api_key: 原始 API Key
            visible_chars: 显示末尾字符数

        Returns:
            脱敏后的字符串
        """
        return mask_api_key(api_key, visible_chars)


# === 全局快捷函数 ===

async def get_model_api_key(
    db: AsyncSession,
    provider_id: UUID,
    tenant_id: UUID | None = None,
) -> str:
    """获取模型 API Key 的快捷函数.

    Args:
        db: 数据库会话
        provider_id: 服务商ID
        tenant_id: 租户ID

    Returns:
        解密后的明文 API Key
    """
    service = SettingsService(db)
    return await service.get_decrypted_api_key(provider_id, tenant_id)
