"""全局异常处理器.

将所有 AppException 转换为标准API响应格式。
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.errors.exceptions import AppException


def create_error_response(
    code: str,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
    field_errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """创建标准错误响应."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    if field_errors:
        error["fieldErrors"] = field_errors

    result: dict[str, Any] = {"success": False, "error": error}
    if request_id:
        result["requestId"] = request_id
    return result


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """处理业务异常."""
        request_id = request.headers.get("X-Request-Id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                details=exc.details or None,
                field_errors=exc.field_errors or None,
            ),
            headers={"X-Request-Id": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理请求验证错误 (FastAPI Pydantic)."""
        request_id = request.headers.get("X-Request-Id", "unknown")

        field_errors = []
        for error in exc.errors():
            loc = ".".join(str(x) for x in error["loc"])
            field_errors.append(
                {
                    "field": loc,
                    "code": error["type"],
                    "message": error["msg"],
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=create_error_response(
                code="VALIDATION_ERROR",
                message="请求数据验证失败",
                request_id=request_id,
                field_errors=field_errors,
            ),
            headers={"X-Request-Id": request_id},
        )

    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        """处理Pydantic验证错误."""
        request_id = request.headers.get("X-Request-Id", "unknown")

        field_errors = []
        for error in exc.errors():
            loc = ".".join(str(x) for x in error["loc"])
            field_errors.append(
                {
                    "field": loc,
                    "code": error["type"],
                    "message": error["msg"],
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=create_error_response(
                code="VALIDATION_ERROR",
                message="数据验证失败",
                request_id=request_id,
                field_errors=field_errors,
            ),
            headers={"X-Request-Id": request_id},
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获的异常 (记录日志但不暴露详细信息)."""
        import logging

        logger = logging.getLogger(__name__)

        request_id = request.headers.get("X-Request-Id", "unknown")

        # 记录错误日志
        logger.exception(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "path": str(request.url),
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(
                code="INTERNAL_ERROR",
                message="服务器内部错误",
                request_id=request_id,
            ),
            headers={"X-Request-Id": request_id},
        )
