"""提示词版本管理测试。"""

from __future__ import annotations

import pytest

from app.ai.prompts.registry import (
    PromptRegistry,
    PromptTemplate,
    build_default_registry,
    load_prompt,
)


def test_default_registry_has_nine_templates() -> None:
    reg = build_default_registry()
    names = reg.names()
    assert set(names) == {
        "tender_parse",
        "requirement_extract",
        "material_match",
        "bid_review",
        "bid_generate",
        "risk_check",
        "evaluation_check",
        "evaluation_score",
        "report_generate",
    }


def test_latest_version_is_semver_sorted() -> None:
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="demo", version="1.0.0", system_prompt="s", user_template="{x}"))
    reg.register(PromptTemplate(name="demo", version="1.2.0", system_prompt="s", user_template="{x}"))
    reg.register(PromptTemplate(name="demo", version="1.10.0", system_prompt="s", user_template="{x}"))
    latest = reg.latest("demo")
    assert latest.version == "1.10.0"


def test_load_prompt_returns_specific_version() -> None:
    reg = build_default_registry()
    template = load_prompt("tender_parse", "1.0.0", registry=reg)
    assert template.name == "tender_parse"
    assert template.version == "1.0.0"


def test_duplicate_registration_is_rejected() -> None:
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="dup", version="1.0.0", system_prompt="s", user_template="hi"))
    with pytest.raises(ValueError):
        reg.register(PromptTemplate(name="dup", version="1.0.0", system_prompt="s", user_template="hi"))


def test_render_uses_safedict() -> None:
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="tpl", version="1.0.0", system_prompt="SYS", user_template="hello {missing}"))
    template = reg.latest("tpl")
    system, user = template.render({})
    assert system == "SYS"
    assert user == "hello "


def test_render_raises_on_braces_mismatch() -> None:
    reg = PromptRegistry()
    reg.register(PromptTemplate(name="tpl", version="1.0.0", system_prompt="SYS", user_template="hello {"))
    template = reg.latest("tpl")
    with pytest.raises(ValueError):
        template.render({})
