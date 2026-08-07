"""WebSocket 票据服务.

提供一次性票据用于 WebSocket 连接认证。
票据有效期30秒，使用后立即失效。
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.redis import redis_client
from app.core.security.jwt import create_access_token


# 配置
WEBSOCKET_TICKET_TTL_SECONDS = 30  # 票据有效期（秒）
WEBSOCKET_TICKET_PREFIX = "ws_ticket:"


class RealtimeTicketService:
    """WebSocket 票据服务."""

    async def create_ticket(
        self,
        user_id: UUID,
        tenant_id: UUID,
        channel: str = "internal",
    ) -> tuple[str, datetime]:
        """创建一次性 WebSocket 票据.

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            channel: 通道类型 (internal/portal)

        Returns:
            (票据字符串, 过期时间)
        """
        # 生成唯一票据ID
        ticket_id = str(uuid4())

        # 创建短期 Access Token 作为票据
        # 使用 30 秒有效期，与票据TTL一致
        ticket_token = create_access_token(
            subject=str(user_id),
            expires_delta=timedelta(seconds=WEBSOCKET_TICKET_TTL_SECONDS),
            additional_claims={
                "tenant_id": str(tenant_id),
                "type": "websocket_ticket",
                "channel": channel,
                "ticket_id": ticket_id,
            },
        )

        # 将票据ID存入 Redis，记录关联信息
        client = await redis_client.get_client()
        key = f"{WEBSOCKET_TICKET_PREFIX}{ticket_id}"

        await client.hset(key, mapping={
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "channel": channel,
            "used": "0",
        })
        await client.expire(key, WEBSOCKET_TICKET_TTL_SECONDS)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=WEBSOCKET_TICKET_TTL_SECONDS)
        return ticket_token, expires_at

    async def validate_ticket(self, ticket_token: str) -> dict | None:
        """验证票据并标记为已使用.

        Args:
            ticket_token: 票据Token

        Returns:
            票据信息字典，验证失败返回 None
        """
        from app.core.security.jwt import verify_token
        from app.core.errors import AuthenticationError

        try:
            payload = verify_token(ticket_token, token_type="access")
        except Exception:
            return None

        # 检查票据类型
        if payload.get("type") != "websocket_ticket":
            return None

        ticket_id = payload.get("ticket_id")
        if not ticket_id:
            return None

        # 检查 Redis 中的票据状态
        client = await redis_client.get_client()
        key = f"{WEBSOCKET_TICKET_PREFIX}{ticket_id}"

        # 使用 Lua 脚本保证原子性：检查并标记为已使用
        lua_script = """
        local used = redis.call('HGET', KEYS[1], 'used')
        if used == '1' then
            return 0
        end
        redis.call('HSET', KEYS[1], 'used', '1')
        return 1
        """
        result = await client.eval(lua_script, 1, key)

        if result == 0:
            # 票据已被使用
            return None

        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "channel": payload.get("channel"),
            "ticket_id": ticket_id,
        }

    async def invalidate_ticket(self, ticket_id: str) -> None:
        """使票据失效（主动作废）.

        Args:
            ticket_id: 票据ID
        """
        client = await redis_client.get_client()
        key = f"{WEBSOCKET_TICKET_PREFIX}{ticket_id}"
        await client.delete(key)


# 全局实例
realtime_ticket_service = RealtimeTicketService()
