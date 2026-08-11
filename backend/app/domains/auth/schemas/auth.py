"""Validated request payloads for authentication and user management."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_strong_password(value: str) -> str:
    if not any(character.isupper() for character in value):
        raise ValueError("密码必须包含大写字母")
    if not any(character.islower() for character in value):
        raise ValueError("密码必须包含小写字母")
    if not any(character.isdigit() for character in value):
        raise ValueError("密码必须包含数字")
    return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("密码不能为空")
        return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    company_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_strong_password(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reset_token: str = Field(..., alias="resetToken", min_length=1)
    new_password: str = Field(..., alias="newPassword", min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_strong_password(value)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=100)


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    role: str
    department: str = Field(..., max_length=100)


class UpdateUserRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    role: str | None = None
    department: str | None = Field(None, max_length=100)


class UserStatusRequest(BaseModel):
    status: str
    reason: str = Field(..., min_length=1)
