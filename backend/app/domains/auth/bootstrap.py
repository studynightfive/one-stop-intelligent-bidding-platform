"""Idempotent development-only account bootstrap for the local demo stack."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, close_db
from app.core.security import get_password_hash
from app.domains.auth.models.user import User, UserRole, UserStatus


def _enabled(value: str | None) -> bool:
    return str(value or "false").lower() in {"true", "1", "yes"}


@dataclass(frozen=True, slots=True)
class DemoAdminConfig:
    enabled: bool
    environment: str
    tenant_id: UUID
    user_id: UUID
    email: str
    password: str
    name: str

    @classmethod
    def from_environment(cls) -> DemoAdminConfig:
        return cls(
            enabled=_enabled(os.getenv("DEMO_SEED_ENABLED")),
            environment=os.getenv("ENVIRONMENT", "development"),
            tenant_id=UUID(os.getenv("DEMO_TENANT_ID", "0190f4dd-0000-7000-8000-000000000002")),
            user_id=UUID(os.getenv("DEMO_ADMIN_USER_ID", "0190f4dd-0000-7000-8000-000000000001")),
            email=os.getenv("DEMO_ADMIN_EMAIL", "admin@bid-platform.local").strip().lower(),
            password=os.getenv("DEMO_ADMIN_PASSWORD", "DemoAdmin123!"),
            name=os.getenv("DEMO_ADMIN_NAME", "演示管理员").strip(),
        )

    def validate(self) -> None:
        if not self.enabled:
            return
        if self.environment != "development":
            raise RuntimeError("DEMO_SEED_ENABLED is only permitted when ENVIRONMENT=development")
        if "@" not in self.email:
            raise RuntimeError("DEMO_ADMIN_EMAIL must be a valid email address")
        if len(self.password) < 8:
            raise RuntimeError("DEMO_ADMIN_PASSWORD must contain at least 8 characters")
        if not self.name:
            raise RuntimeError("DEMO_ADMIN_NAME cannot be empty")


async def ensure_demo_admin(db: AsyncSession, config: DemoAdminConfig) -> str:
    """Create or refresh the fixed local administrator without duplicating rows."""

    config.validate()
    if not config.enabled:
        return "disabled"

    result = await db.execute(
        select(User).where(
            User.tenant_id == config.tenant_id,
            User.email == config.email,
        )
    )
    user = result.scalar_one_or_none()
    action = "updated"
    if user is None:
        action = "created"
        user = User(
            id=config.user_id,
            tenant_id=config.tenant_id,
            email=config.email,
            name=config.name,
        )
        db.add(user)

    user.password_hash = get_password_hash(config.password)
    user.name = config.name
    user.role = UserRole.ADMIN
    user.status = UserStatus.ACTIVE
    user.department = "项目管理组"
    user.is_super_admin = True
    user.deleted_at = None
    await db.commit()
    return action


async def _main() -> None:
    config = DemoAdminConfig.from_environment()
    async with AsyncSessionLocal() as db:
        result = await ensure_demo_admin(db, config)
    await close_db()
    print(f"demo admin bootstrap: {result}")


if __name__ == "__main__":
    asyncio.run(_main())
