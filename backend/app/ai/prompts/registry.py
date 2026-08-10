"""提示词版本注册表。

每个 AI 场景对应一个 ``PromptTemplate``：系统提示词 + 用户模板 + 版本号。
模板以代码形式声明（不读 DB），便于：
- 单元测试固定快照；
- 跨域 prompt 升级时 diff 对比；
- Worker 重启时无延迟加载。

升级流程：
1. 在 fixtures 增 sample 用例；
2. 新增版本号 ``v1.x.y`` 并实现同名 handler；
3. 更新路由默认版本。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptTemplate:
    """提示词模板（不可变）。"""

    name: str
    version: str
    system_prompt: str
    user_template: str
    model: str = "fake"
    temperature: float = 0.2
    top_p: float = 0.9
    max_output_tokens: int = 2048

    def render(self, payload: Mapping[str, object] | None = None) -> tuple[str, str]:
        """根据 payload 渲染 ``(system_prompt, user_prompt)``。"""

        context: dict[str, object] = dict(payload or {})
        try:
            rendered = self.user_template.format_map(_SafeDict(context))
        except KeyError as exc:  # pragma: no cover - 由调用方负责传齐字段
            raise ValueError(f"prompt {self.name} missing key: {exc.args[0]}") from exc
        return self.system_prompt, rendered


class _SafeDict(dict):  # type: ignore[type-arg]
    """模板 dict：未知字段渲染为空串，不抛 KeyError。"""

    def __missing__(self, key: str) -> str:
        return ""


@dataclass(frozen=True)
class PromptRegistry:
    """模板注册表。"""

    _templates: dict[tuple[str, str], PromptTemplate] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # ``frozen=True`` 不允许直接赋值，绕过一下。
        object.__setattr__(self, "_templates", {})

    def register(self, template: PromptTemplate, *, allow_override: bool = False) -> None:
        key = (template.name, template.version)
        if key in self._templates and not allow_override:
            raise ValueError(f"prompt {template.name}@{template.version} already registered")
        self._templates[key] = template

    def get(self, name: str, version: str) -> PromptTemplate:
        key = (name, version)
        if key not in self._templates:
            raise KeyError(f"prompt {name}@{version} not found")
        return self._templates[key]

    def latest(self, name: str) -> PromptTemplate:
        versions = [v for (n, v) in self._templates if n == name]
        if not versions:
            raise KeyError(f"prompt {name} has no registered versions")
        latest_version = sorted(versions, key=_semver_key, reverse=True)[0]
        return self._templates[(name, latest_version)]

    def all_versions(self, name: str) -> list[str]:
        return sorted([v for (n, v) in self._templates if n == name], key=_semver_key)

    def names(self) -> list[str]:
        return sorted({n for (n, _) in self._templates})


def _semver_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in version.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def build_default_registry() -> PromptRegistry:
    """构造默认注册表（基础场景）。"""

    from app.ai.prompts import templates as tpl

    registry = PromptRegistry()
    for factory in tpl.all_template_factories():
        template = factory()
        registry.register(template)
    return registry


def load_prompt(name: str, version: str | None = None, registry: PromptRegistry | None = None) -> PromptTemplate:
    reg = registry or build_default_registry()
    if version:
        return reg.get(name, version)
    return reg.latest(name)


PromptFactory = Callable[[], PromptTemplate]

__all__ = [
    "PromptFactory",
    "PromptRegistry",
    "PromptTemplate",
    "build_default_registry",
    "load_prompt",
]
