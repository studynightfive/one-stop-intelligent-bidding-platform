"""提示词版本管理包。

- :mod:`registry`：版本注册表与加载接口；
- :mod:`templates`：按场景的 PromptTemplate 工厂集合。

升级提示词时仅改 ``templates.py``，由 ``registry.build_default_registry`` 自动加载。
"""

from __future__ import annotations

from app.ai.prompts.registry import (
    PromptFactory,
    PromptRegistry,
    PromptTemplate,
    build_default_registry,
    load_prompt,
)
from app.ai.prompts.templates import all_template_factories

__all__ = [
    "PromptFactory",
    "PromptRegistry",
    "PromptTemplate",
    "all_template_factories",
    "build_default_registry",
    "load_prompt",
]
