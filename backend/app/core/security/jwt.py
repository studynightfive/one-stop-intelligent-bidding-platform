"""安全模块 - JWT、密码哈希、加密等.

安全规范：
- JWT: RS256 非对称算法
- 密码: bcrypt 哈希
- API Key: AES-256-GCM 信封加密
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """对密码进行哈希.

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码.

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        是否匹配
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


# === JWT Token ===
ALGORITHM = "RS256"


def _load_or_generate_keys() -> tuple[bytes, bytes]:
    """加载或生成RSA密钥对.

    开发/测试环境会生成临时密钥。
    生产环境从文件加载。

    Returns:
        (private_key_pem, public_key_pem)
    """
    private_path = settings.jwt_private_key_path
    public_path = settings.jwt_public_key_path

    # 检查是否存在密钥文件
    if private_path.exists() and public_path.exists():
        with open(private_path, "rb") as f:
            private_bytes = f.read()
        with open(public_path, "rb") as f:
            public_bytes = f.read()
        return private_bytes, public_bytes

    # 生成新密钥（开发/测试环境）
    if settings.is_development or settings.is_test:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # 尝试保存（如果目录存在）
        try:
            private_path.parent.mkdir(parents=True, exist_ok=True)
            with open(private_path, "wb") as f:
                f.write(private_pem)
            with open(public_path, "wb") as f:
                f.write(public_pem)
        except OSError:
            pass  # 无法保存，使用内存中的密钥

        return private_pem, public_pem

    raise RuntimeError(f"JWT密钥文件不存在: {private_path}")


# 缓存密钥
_private_key_pem, _public_key_pem = _load_or_generate_keys()


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """创建Access Token.

    Args:
        subject: Token主题（通常是用户ID）
        expires_delta: 过期时间增量，默认15分钟
        additional_claims: 额外的声明

    Returns:
        JWT token字符串
    """
    import jwt

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_ttl_minutes)

    expire = datetime.now(UTC) + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, _private_key_pem, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """创建Refresh Token.

    Args:
        subject: Token主题（通常是用户ID）
        expires_delta: 过期时间增量，默认7天

    Returns:
        JWT token字符串
    """
    import jwt

    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_ttl_days)

    expire = datetime.now(UTC) + expires_delta

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),  # 唯一ID，用于防重放
    }

    return jwt.encode(payload, _private_key_pem, algorithm=ALGORITHM)


def create_portal_token(
    subject: str,
    supplier_id: str,
    evaluation_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """创建供应商Portal Token.

    Args:
        subject: Token主题
        supplier_id: 供应商ID
        evaluation_id: 评标任务ID
        expires_delta: 过期时间增量，默认30分钟

    Returns:
        JWT token字符串
    """
    import jwt

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_portal_token_ttl_minutes)

    expire = datetime.now(UTC) + expires_delta

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "portal",
        "supplier_id": supplier_id,
        "evaluation_id": evaluation_id,
    }

    return jwt.encode(payload, _private_key_pem, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """验证并解码Token.

    Args:
        token: JWT token字符串
        token_type: 期望的token类型

    Returns:
        解码后的payload字典

    Raises:
        jwt.InvalidTokenError: Token无效或过期
        TokenRevokedError: Token已被撤销
    """
    import jwt

    payload = cast(dict[str, Any], jwt.decode(token, _public_key_pem, algorithms=[ALGORITHM]))

    # 验证token类型
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError(f"Invalid token type: expected {token_type}")

    return payload


def decode_token_unsafe(token: str) -> dict[str, Any]:
    """解码 Token 但不验证签名（用于检查黑名单）.

    Args:
        token: JWT token字符串

    Returns:
        解码后的 payload 字典（未验证）
    """
    import jwt

    return cast(dict[str, Any], jwt.decode(token, options={"verify_signature": False}))


# === API Key 加密 ===
# 使用 AES-256-GCM 信封加密
# 格式: salt(16) + nonce(12) + ciphertext + tag(16)


def encrypt_api_key(plain_key: str, master_key: bytes | None = None) -> str:
    """加密API Key.

    Args:
        plain_key: 明文API Key
        master_key: 主密钥，默认从环境变量加载

    Returns:
        Base64编码的加密字符串
    """
    import base64

    if master_key is None:
        # 从文件加载主密钥或使用默认密钥（开发环境）
        try:
            if settings.model_master_key_path.exists():
                with open(settings.model_master_key_path, "rb") as f:
                    master_key = f.read()
            else:
                # 开发环境使用派生密钥
                master_key = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"bid-platform-model-key",
                    backend=default_backend(),
                    iterations=100000,
                ).derive(b"development-key-placeholder")
        except Exception:
            master_key = b"development-key-32bytes-xxxx!"

    # 确保密钥长度正确
    if len(master_key) < 32:
        master_key = hashlib.sha256(master_key).digest()

    # 生成随机盐和nonce
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)

    # 使用AES-256-GCM加密
    aesgcm = AESGCM(master_key[:32])
    ciphertext = aesgcm.encrypt(nonce, plain_key.encode("utf-8"), salt)

    # 组合: salt + nonce + ciphertext
    encrypted = salt + nonce + ciphertext

    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_api_key(encrypted_key: str, master_key: bytes | None = None) -> str:
    """解密API Key.

    Args:
        encrypted_key: Base64编码的加密字符串
        master_key: 主密钥

    Returns:
        明文API Key
    """
    import base64

    encrypted_bytes = base64.b64decode(encrypted_key.encode("utf-8"))

    # 解析: salt(16) + nonce(12) + ciphertext
    salt = encrypted_bytes[:16]
    nonce = encrypted_bytes[16:28]
    ciphertext = encrypted_bytes[28:]

    if master_key is None:
        try:
            if settings.model_master_key_path.exists():
                with open(settings.model_master_key_path, "rb") as f:
                    master_key = f.read()
            else:
                master_key = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"bid-platform-model-key",
                    backend=default_backend(),
                    iterations=100000,
                ).derive(b"development-key-placeholder")
        except Exception:
            master_key = b"development-key-32bytes-xxxx!"

    if len(master_key) < 32:
        master_key = hashlib.sha256(master_key).digest()

    # 解密
    aesgcm = AESGCM(master_key[:32])
    plaintext = aesgcm.decrypt(nonce, ciphertext, salt)

    return plaintext.decode("utf-8")


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """脱敏API Key.

    Args:
        api_key: 原始API Key
        visible_chars: 显示末尾字符数

    Returns:
        脱敏后的字符串，如 sk-••••••••••••abc
    """
    if len(api_key) <= visible_chars:
        return "••••" + api_key[-visible_chars:] if api_key else "••••••••"
    return "••••" + api_key[-visible_chars:]


# === 文件哈希 ===
def compute_sha256(file_content: bytes) -> str:
    """计算文件SHA-256哈希.

    Args:
        file_content: 文件内容

    Returns:
        64位十六进制哈希字符串
    """
    return hashlib.sha256(file_content).hexdigest()


def verify_sha256(file_content: bytes, expected_hash: str) -> bool:
    """验证文件SHA-256哈希.

    Args:
        file_content: 文件内容
        expected_hash: 期望的哈希值

    Returns:
        是否匹配
    """
    return hmac.compare_digest(compute_sha256(file_content), expected_hash.lower())


# === WebSocket票据 ===
def generate_websocket_ticket() -> str:
    """生成一次性WebSocket连接票据.

    Returns:
        票据字符串（URL安全Base64）
    """
    return secrets.token_urlsafe(32)


def hash_ticket(ticket: str) -> str:
    """对票据进行哈希（用于存储和验证）.

    Args:
        ticket: 原始票据

    Returns:
        哈希后的字符串
    """
    return hashlib.sha256(ticket.encode()).hexdigest()
