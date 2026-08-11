"""认证API模块."""

from app.domains.auth.api.auth import router as auth_router
from app.domains.auth.api.users import metadata_router
from app.domains.auth.api.users import router as users_router

__all__ = ["auth_router", "metadata_router", "users_router"]
