"""Redis 客户端管理.

提供 Redis 连接和常用操作。
"""

from typing import cast

import redis.asyncio as redis

from app.core.config import settings


class RedisClient:
    """Redis 异步客户端."""

    _instance: "RedisClient | None" = None
    _client: redis.Redis | None = None

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_client(self) -> redis.Redis:
        """获取 Redis 客户端实例."""
        if self._client is None:
            self._client = cast(
                redis.Redis,
                redis.from_url(  # type: ignore[no-untyped-call]
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                ),
            )
        return self._client

    async def close(self) -> None:
        """关闭 Redis 连接."""
        if self._client:
            await self._client.close()
            self._client = None


# 全局实例
redis_client = RedisClient()


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端的依赖注入函数."""
    return await redis_client.get_client()


# === Token 黑名单操作 ===

TOKEN_BLACKLIST_PREFIX = f"{settings.redis_key_prefix}:token_blacklist:"


async def add_token_to_blacklist(jti: str, exp_seconds: int) -> None:
    """将 Token 加入黑名单.

    Args:
        jti: Token 的唯一标识 (jti claim)
        exp_seconds: Token 剩余有效期（秒），作为黑名单过期时间
    """
    client = await redis_client.get_client()
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    # 设置过期时间略大于 Token 剩余有效期
    # 加 60 秒缓冲，防止时序问题
    ttl = min(exp_seconds + 60, 7 * 24 * 60 * 60)  # 最多 7 天

    await client.setex(key, ttl, "revoked")


async def is_token_blacklisted(jti: str) -> bool:
    """检查 Token 是否在黑名单中.

    Args:
        jti: Token 的唯一标识 (jti claim)

    Returns:
        是否已被撤销
    """
    client = await redis_client.get_client()
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    count = await client.exists(key)
    return bool(count)


async def get_token_ttl(jti: str) -> int:
    """获取 Token 的剩余有效期.

    Args:
        jti: Token 的唯一标识 (jti claim)

    Returns:
        剩余秒数，-2 表示不存在，-1 表示无过期时间
    """
    client = await redis_client.get_client()
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    ttl = await client.ttl(key)
    return int(ttl)
