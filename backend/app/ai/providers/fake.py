"""Fake / 离线 Provider。

用于 CI、Phase 0 启动和单元测试，无网络依赖。
基于规则匹配 ``prompt_name`` 返回可重复的 JSON 结构。

约定：
- 输入 ``prompt_name`` 形如 ``tender_parse``；
- 返回结构由 ``_BUILTIN_HANDLERS`` 注册，
  未匹配时回落到 ``_default_handler`` 返回带 ``echo`` 字段的空结构。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.ai.providers.base import GenerationRequest, GenerationResponse, SyncAIProvider
from app.ai.schemas import ProviderStatus, TokenUsage

Handler = Callable[[GenerationRequest, str], dict[str, Any]]


def _token_estimate(text: str) -> int:
    """粗略估算 Token 数（CJK 1 字符 ≈ 1 token，英文按空格切分）。"""

    if not text:
        return 0
    chinese = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    rest = re.sub(r"[\u4e00-\u9fff]+", " ", text)
    english_words = len([w for w in rest.split() if w])
    return chinese + english_words


def _default_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "echo": True,
        "promptName": request.prompt_name,
        "promptVersion": request.prompt_version,
        "model": request.model,
        "inputLength": len(payload_text),
    }


def _tender_parse_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    """离线解析：把原文切成 Markdown 段落并返回前 5 段 + 元数据。"""

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", payload_text) if p.strip()]
    sections = [
        {
            "index": idx,
            "title": p.splitlines()[0][:80] if p else "",
            "wordCount": len(p),
        }
        for idx, p in enumerate(paragraphs[:5])
    ]
    return {
        "summary": paragraphs[0][:280] if paragraphs else "",
        "sectionCount": len(paragraphs),
        "sections": sections,
        "provider": "fake",
    }


def _requirement_extract_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    """离线提取：返回固定评分项与资格要求占位结构。"""

    return {
        "qualificationRequirements": ["ISO 9001 证书", "三年以上业绩"],
        "technicalRequirements": ["支持国产化部署", "需提供方案设计文档"],
        "scoringItems": [
            {"name": "技术方案", "score": "40", "basis": "技术指标响应度"},
            {"name": "报价", "score": "30", "basis": "总价得分"},
            {"name": "实施与服务", "score": "30", "basis": "团队与案例"},
        ],
        "disqualificationItems": [
            {"name": "近三年重大违法", "basis": "《招标投标法》第三十二条"},
        ],
        "provider": "fake",
    }


def _material_match_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    """离线匹配：每项材料返回 0.8 固定置信度，便于 UI 联调。"""

    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError:
        data = {"materials": []}
    materials = data.get("materials", []) if isinstance(data, dict) else []
    matches = [{"materialName": m.get("name", ""), "confidence": 0.8, "matchedSource": "fake"} for m in materials]
    return {"matches": matches, "provider": "fake"}


def _bid_review_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    """离线审核：返回空 finding + 1 条 info 提示。"""

    return {
        "summary": "AI 离线审核未发现问题，请人工复核关键项。",
        "findings": [
            {
                "type": "content",
                "severity": "info",
                "title": "离线占位提示",
                "description": "当前为离线模式，AI 审核建议仅作占位，请人工确认。",
                "suggestion": "在生产环境开启 Qwen / DeepSeek 后重跑。",
            }
        ],
        "provider": "fake",
    }


def _bid_generate_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "outline": [
            {"section": "投标函", "estimatedWords": 280},
            {"section": "技术方案", "estimatedWords": 1800},
            {"section": "商务条款响应", "estimatedWords": 600},
            {"section": "资质与业绩", "estimatedWords": 500},
            {"section": "实施与服务承诺", "estimatedWords": 400},
        ],
        "wordCountEstimate": 3580,
        "provider": "fake",
    }


def _bid_generate_plan_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "planApproved": True,
        "sectionPlan": [],
        "warnings": [],
        "provider": "fake",
    }


def _bid_generate_paragraph_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    heading_match = re.search(r"## 当前章节\n([^\n]+)", payload_text)
    paragraph_match = re.search(r"当前段落：(\d+)/(\d+)", payload_text)
    heading = heading_match.group(1).strip() if heading_match else "技术方案"
    paragraph_index = int(paragraph_match.group(1)) if paragraph_match else 1
    paragraph_count = int(paragraph_match.group(2)) if paragraph_match else 1
    paragraph = (
        f"{heading}第{paragraph_index}段围绕招标要求展开说明。"
        "方案以需求可追溯、实施过程可检查、交付结果可验收为原则，结合已提供的项目资料明确工作边界、"
        "技术路径和质量控制措施，并通过阶段评审、问题闭环与版本留痕保证方案执行的一致性。"
        f"本段为该章节共{paragraph_count}段中的第{paragraph_index}段，正式提交前仍需项目负责人复核事实依据。"
    )
    return {
        "paragraph": paragraph,
        "evidence": [
            {
                "sourceType": "project_context",
                "sourceId": "offline-demo",
                "summary": "依据当前任务提供的项目资料生成，需人工复核。",
            }
        ],
        "provider": "fake",
    }


def _risk_check_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "findings": [],
        "highRiskCount": 0,
        "summary": "离线模式未发现风险。",
        "provider": "fake",
    }


def _evaluation_check_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "completeness": 0.92,
        "missing": ["未提交近三年财务报表"],
        "provider": "fake",
    }


def _evaluation_score_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "scores": [
            {"criterionName": "技术方案", "score": "82.00", "confidence": 0.78, "basis": "响应完整"},
            {"criterionName": "报价", "score": "76.00", "confidence": 0.75, "basis": "区间合理"},
        ],
        "overall": {"score": "79.00", "confidence": 0.77},
        "provider": "fake",
    }


def _report_generate_handler(request: GenerationRequest, payload_text: str) -> dict[str, Any]:
    return {
        "reportTitle": "评标报告（离线占位）",
        "sections": [
            {"heading": "项目概况", "body": "由离线 Provider 生成，请人工补全。"},
            {"heading": "评分汇总", "body": "见附表。"},
        ],
        "provider": "fake",
    }


_BUILTIN_HANDLERS: dict[str, Handler] = {
    "tender_parse": _tender_parse_handler,
    "requirement_extract": _requirement_extract_handler,
    "material_match": _material_match_handler,
    "bid_review": _bid_review_handler,
    "bid_generate": _bid_generate_handler,
    "bid_generate_plan": _bid_generate_plan_handler,
    "bid_generate_paragraph": _bid_generate_paragraph_handler,
    "risk_check": _risk_check_handler,
    "evaluation_check": _evaluation_check_handler,
    "evaluation_score": _evaluation_score_handler,
    "report_generate": _report_generate_handler,
}


def _resolve_handler(prompt_name: str, extra: dict[str, Handler]) -> Handler:
    handlers: dict[str, Handler] = {**_BUILTIN_HANDLERS, **extra}
    if prompt_name in handlers:
        return handlers[prompt_name]
    # 兼容 ``xxx_v1`` 形式
    base = prompt_name.split("_v")[0] if "_v" in prompt_name else prompt_name
    return handlers.get(base, _default_handler)


@dataclass
class FakeProvider(SyncAIProvider):
    """离线 Provider：根据 prompt_name 选择 handler，返回可重复结构。"""

    name: str = "fake"
    latency_ms: int = 5
    extra_handlers: dict[str, Handler] | None = None

    def is_available(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        started = time.perf_counter()
        handler = _resolve_handler(request.prompt_name, self.extra_handlers or {})
        payload = f"{request.system_prompt}\n\n{request.user_prompt}"
        structured = handler(request, payload)
        text = json.dumps(structured, ensure_ascii=False, sort_keys=True)
        usage = TokenUsage(
            prompt=_token_estimate(request.user_prompt) + _token_estimate(request.system_prompt),
            completion=_token_estimate(text),
            total=_token_estimate(request.user_prompt) + _token_estimate(request.system_prompt) + _token_estimate(text),
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000) + self.latency_ms
        return GenerationResponse(
            text=text,
            structured=structured,
            token_usage=usage,
            model=request.model,
            provider=self.name,
            latency_ms=elapsed_ms,
            provider_status=ProviderStatus.OFFLINE,
        )


def build_fake_provider(name: str = "fake") -> FakeProvider:
    return FakeProvider(name=name)
