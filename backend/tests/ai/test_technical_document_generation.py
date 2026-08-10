"""Technical-document paragraph pipeline tests."""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.errors import ProviderTimeout
from app.ai.router import reset_router_for_tests
from app.ai.schemas import PromptVersion, ProviderOutput, ProviderStatus, TokenUsage
from app.ai.technical_document import (
    TechnicalDocumentOptions,
    TechnicalDocumentValidationError,
    build_bounded_context,
)
from app.workers.bidding_generator import (
    BiddingGeneratorTask,
    reset_technical_document_checkpoints_for_tests,
)


def _technical_options() -> dict[str, Any]:
    return {
        "strategy": "paragraph_by_paragraph",
        "templateName": "技术标书标准模板",
        "sections": [
            {
                "key": "overall",
                "heading": "1 技术总体方案",
                "headingLevel": 1,
                "instructions": "说明总体架构、实施边界与质量目标。",
                "targetParagraphs": 2,
                "targetWordsPerParagraph": 180,
                "required": True,
            },
            {
                "key": "delivery",
                "heading": "2 实施与交付",
                "headingLevel": 1,
                "instructions": "说明里程碑、验收方法与服务保障。",
                "targetParagraphs": 1,
                "targetWordsPerParagraph": 160,
                "required": True,
            },
        ],
        "referenceImages": [
            {
                "fileId": "file-architecture",
                "sectionKey": "overall",
                "caption": "图 1 系统总体架构",
                "altText": "三层系统架构示意图",
                "placement": "after_paragraph",
                "afterParagraphIndex": 1,
            },
            {
                "fileId": "file-schedule",
                "sectionKey": "delivery",
                "caption": "图 2 项目进度计划",
                "placement": "after_section",
            },
        ],
        "contextWindowCharacters": 2_000,
        "carryForwardParagraphs": 2,
        "preserveHeadingNumbering": True,
        "requireEvidence": True,
    }


@pytest.fixture(autouse=True)
def _reset_generation_state() -> None:
    reset_router_for_tests()
    reset_technical_document_checkpoints_for_tests()


@pytest.mark.asyncio
async def test_generates_locked_sections_one_paragraph_per_call() -> None:
    task = BiddingGeneratorTask()
    payload = {
        "projectInfo": {"name": "智慧园区平台"},
        "requirements": [{"id": "REQ-01", "text": "支持国产化部署"}],
        "library": [{"id": "FRAG-01", "text": "既有实施方法"}],
        "technicalDocument": _technical_options(),
    }
    spec = task._build_spec("job-tech-complete", payload)

    result = await task._execute(spec, payload)

    assert result.status.value == "succeeded"
    document = result.output["technicalDocument"]
    assert [section["key"] for section in document["sections"]] == ["overall", "delivery"]
    assert [len(section["paragraphs"]) for section in document["sections"]] == [2, 1]
    assert document["sections"][0]["images"][0]["fileId"] == "file-architecture"
    assert document["sections"][0]["images"][0]["afterParagraphIndex"] == 1
    assert result.output["generationCheckpoint"]["status"] == "completed"
    assert result.output["generationCheckpoint"]["completedParagraphs"] == 3
    assert [item.name for item in result.prompt_versions] == [
        "bid_generate_plan",
        "bid_generate_paragraph",
        "bid_generate_paragraph",
        "bid_generate_paragraph",
    ]
    assert result.token_usage == sum(
        (item.token_usage for item in result.prompt_versions),
        start=TokenUsage(),
    )


def test_rejects_duplicate_sections_and_invalid_image_anchor() -> None:
    duplicate = _technical_options()
    duplicate["sections"][1]["key"] = "overall"
    with pytest.raises(TechnicalDocumentValidationError, match="duplicate keys"):
        TechnicalDocumentOptions.from_mapping(duplicate)

    invalid_anchor = _technical_options()
    invalid_anchor["referenceImages"][0]["afterParagraphIndex"] = 3
    with pytest.raises(TechnicalDocumentValidationError, match="missing paragraph"):
        TechnicalDocumentOptions.from_mapping(invalid_anchor)


def test_bounded_context_prioritizes_images_and_recent_paragraphs() -> None:
    options = TechnicalDocumentOptions.from_mapping(_technical_options())
    context = build_bounded_context(
        {"projectInfo": {"description": "P" * 10_000}, "library": [{"text": "L" * 10_000}]},
        options=options,
        section=options.sections[0],
        completed_paragraphs=[{"index": 1, "text": "RECENT-PARAGRAPH", "evidence": []}],
    )

    assert len(context) <= options.context_window_characters
    assert "file-architecture" in context
    assert "RECENT-PARAGRAPH" in context
    assert "[context truncated]" in context


@pytest.mark.asyncio
async def test_resumes_from_last_completed_paragraph_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.workers.bidding_generator as generator_module

    task = BiddingGeneratorTask()
    options = _technical_options()
    options["sections"] = [options["sections"][0]]
    options["referenceImages"] = [options["referenceImages"][0]]
    payload = {
        "projectInfo": {"description": "P" * 5_000},
        "technicalDocument": options,
    }
    spec = task._build_spec("job-tech-resume", payload)
    calls: list[tuple[str, int | None]] = []
    fail_second_once = True

    async def fake_invoke(child_spec, *, payload):
        nonlocal fail_second_once
        paragraph_index = payload.get("paragraphIndex")
        calls.append((child_spec.prompt_name, paragraph_index))
        if child_spec.prompt_name == "bid_generate_paragraph" and paragraph_index == 2 and fail_second_once:
            fail_second_once = False
            raise ProviderTimeout("temporary", provider="fake")
        structured: dict[str, Any]
        if child_spec.prompt_name == "bid_generate_plan":
            structured = {"planApproved": True, "sectionPlan": [], "warnings": []}
        else:
            structured = {
                "paragraph": f"generated-paragraph-{paragraph_index}",
                "evidence": [{"sourceId": "REQ-01"}],
            }
            assert len(payload["context"]) <= 2_000
            if paragraph_index == 2:
                assert "generated-paragraph-1" in payload["context"]
        usage = TokenUsage(prompt=1, completion=2, total=3)
        return ProviderOutput(
            text="{}",
            structured=structured,
            prompt_version=PromptVersion(
                name=child_spec.prompt_name,
                version="1.0.0",
                provider="fake",
                model="fake",
                input_hash=f"in-{len(calls)}",
                output_hash=f"out-{len(calls)}",
                token_usage=usage,
                latency_ms=1,
                status="success",
            ),
            provider_status=ProviderStatus.PRIMARY,
        )

    monkeypatch.setattr(generator_module, "invoke", fake_invoke)

    with pytest.raises(ProviderTimeout):
        await task._execute(spec, payload)
    result = await task._execute(spec, payload)

    assert result.status.value == "succeeded"
    assert [item[0] for item in calls].count("bid_generate_plan") == 1
    assert calls.count(("bid_generate_paragraph", 1)) == 1
    assert calls.count(("bid_generate_paragraph", 2)) == 2
    assert len(result.prompt_versions) == 3
    paragraphs = result.output["technicalDocument"]["sections"][0]["paragraphs"]
    assert [paragraph["text"] for paragraph in paragraphs] == [
        "generated-paragraph-1",
        "generated-paragraph-2",
    ]
