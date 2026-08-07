"""结构化日志模块.

使用 structlog 进行结构化日志记录。
支持 JSON 格式输出（生产环境）和彩色文本格式（开发环境）。
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

from app.core.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """添加应用上下文到日志事件."""
    event_dict["app"] = settings.app_name
    event_dict["environment"] = settings.environment
    return event_dict


def add_request_id(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """添加请求ID到日志事件（如果存在）。"""
    # 请求ID由上下文变量提供
    return event_dict


def rename_event_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """将 'event' 重命名为 'message'."""
    event_dict["message"] = event_dict.pop("event", "")
    return event_dict


def configure_logging() -> None:
    """配置结构化日志."""
    # 根据环境选择处理器
    if settings.is_production or settings.log_format == "json":
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_app_context,
            add_request_id,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # 开发环境使用彩色输出
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_app_context,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # 配置 structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


# 创建日志记录器
def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取日志记录器.

    Args:
        name: 日志记录器名称

    Returns:
        结构化日志记录器
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# 初始化日志
configure_logging()
