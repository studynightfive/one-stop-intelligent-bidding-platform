"""应用配置管理.

所有配置项从环境变量读取，使用 pydantic-settings 自动校验。
版本锚定见 PROJECT_MASTER_PROMPT.md 第4.1节。
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === 应用基本信息 ===
    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "一站式智能招投标平台 API"
    app_version: str = "1.0.0"
    debug: bool = False

    # === 数据库配置 ===
    database_url: str = Field(
        default="postgresql+asyncpg://bid_platform:change-me@postgres:5432/bid_platform",
        description="PostgreSQL数据库连接URL",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # === Redis配置 ===
    redis_url: str = Field(
        default="redis://redis:6379/0",
        description="Redis连接URL",
    )
    redis_key_prefix: str = "bidplat:development"

    # === MinIO配置 ===
    minio_endpoint: str = Field(
        default="http://minio:9000",
        description="MinIO API端点",
    )
    minio_bucket: str = "bid-platform"
    minio_access_key: str = "bid_platform_local"
    minio_secret_key: str = "change-me-local-only"
    minio_secure: bool = False
    minio_bucket_public: bool = False  # 生产环境必须为False

    # === JWT配置 ===
    jwt_private_key_path: Path = Path("/run/secrets/jwt_private_key")
    jwt_public_key_path: Path = Path("/run/secrets/jwt_public_key")
    jwt_algorithm: str = "RS256"
    jwt_access_token_ttl_minutes: int = 15
    jwt_refresh_token_ttl_days: int = 7
    jwt_portal_token_ttl_minutes: int = 30

    # === Cookie配置 ===
    refresh_token_cookie_name: str = "refresh_token"
    refresh_token_cookie_max_age: int = 7 * 24 * 60 * 60  # 7天（秒）
    refresh_token_cookie_secure: bool = True  # 生产环境必须为True
    refresh_token_cookie_http_only: bool = True
    refresh_token_cookie_same_site: Literal["lax", "strict", "none"] = "lax"

    # === AI配置 ===
    ai_fake_provider: bool = True  # 开发环境使用假Provider
    ai_default_provider: str = "qwen"
    ai_request_timeout_seconds: int = 60
    ai_max_retries: int = 3
    model_master_key_path: Path = Path("/run/secrets/model_master_key")

    # === 文件上传配置 ===
    upload_max_size_bytes: int = 200 * 1024 * 1024  # 200MB
    upload_chunk_size_bytes: int = 8 * 1024 * 1024  # 8MB
    upload_allowed_extensions: set[str] = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".zip", ".rar",
    }

    # === CORS配置 ===
    cors_origins: list[str] = ["http://127.0.0.1:3210"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # === 邮件配置 ===
    mail_host: str = "mailpit"
    mail_port: int = 1025
    mail_from: str = "no-reply@bid-platform.local"
    mail_username: str | None = None
    mail_password: str | None = None

    # === 日志配置 ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "json"  # json 或 text

    # === OpenAPI契约路径 ===
    openapi_contract_path: Path = Path(__file__).parents[2] / "contracts" / "openapi.yaml"

    # === 路径校验 ===
    @field_validator("jwt_private_key_path", "jwt_public_key_path", "model_master_key_path")
    @classmethod
    def validate_secret_path(cls, v: Path) -> Path:
        if not v.exists():
            # 开发/测试环境使用占位符，不检查文件存在性
            env = os.environ.get("ENVIRONMENT", "development")
            if env in ("development", "test") or "secrets" not in str(v):
                return v
            raise ValueError(f"密钥文件不存在: {v}")
        return v

    # === 计算属性 ===
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def api_prefix(self) -> str:
        return "/api/v1"

    @property
    def docs_url(self) -> str:
        return "/docs"

    @property
    def redoc_url(self) -> str:
        return "/redoc"

    @property
    def openapi_url(self) -> str:
        return f"{self.api_prefix}/openapi.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置单例."""
    return Settings()


# 全局配置实例
settings = get_settings()
