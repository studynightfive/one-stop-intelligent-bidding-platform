"""M5 bid-document generation worker.

Short-form requests retain the original single-call outline behavior.  Technical
documents use a plan call followed by one model call per paragraph so long input
does not overflow a provider context window and completed work can be resumed.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, cast

from app.ai.router import invoke
from app.ai.schemas import (
    JobResult,
    JobSpec,
    PromptVersion,
    ProviderOutput,
    ProviderStatus,
    TokenUsage,
    hash_payload,
)
from app.ai.technical_document import (
    SectionTemplate,
    TechnicalDocumentOptions,
    TechnicalDocumentValidationError,
    build_bounded_context,
    compact_json,
)
from app.workers.base import M7Task, run_task_handler

logger = logging.getLogger(__name__)

_PLAN_PROMPT = "bid_generate_plan"
_PARAGRAPH_PROMPT = "bid_generate_paragraph"
_TECHNICAL_PROMPT_VERSION = "1.0.0"


class GeneratedContentValidationError(ValueError):
    """Raised when an LLM response cannot satisfy the locked output structure."""


@dataclass
class _GenerationCheckpoint:
    fingerprint: str
    plan: dict[str, Any]
    sections: list[dict[str, Any]] = field(default_factory=list)
    prompt_versions: list[PromptVersion] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    provider_statuses: list[ProviderStatus] = field(default_factory=list)

    @property
    def completed_paragraphs(self) -> int:
        return sum(len(section.get("paragraphs", [])) for section in self.sections)


_CHECKPOINTS: dict[str, _GenerationCheckpoint] = {}
_CHECKPOINT_LOCK = Lock()


class BiddingGeneratorTask(M7Task):
    """Generate either a legacy outline or a locked-format technical document."""

    name = "app.workers.bidding_generator.generate"
    scene = "bid_generate"
    prompt_name = "bid_generate"
    prompt_version = "1.0.0"
    max_retries = 3

    async def _execute(self, spec: JobSpec, payload: dict[str, Any]) -> JobResult:
        raw_options = payload.get("technicalDocument")
        if raw_options is None:
            return await self._execute_legacy(spec, payload)
        if not isinstance(raw_options, Mapping):
            raise TechnicalDocumentValidationError("technicalDocument must be an object")
        options = TechnicalDocumentOptions.from_mapping(raw_options)
        return await self._execute_technical_document(spec, payload, options)

    async def _execute_legacy(self, spec: JobSpec, payload: dict[str, Any]) -> JobResult:
        output = await invoke(spec, payload=payload)
        prompt_versions = [output.prompt_version]
        token_usage = output.prompt_version.token_usage
        structured = output.structured or {}
        result_output = {"outline": structured.get("outline", [])}
        if output.provider_status == ProviderStatus.OFFLINE:
            return self.make_partial_result(
                job_id=spec.job_id,
                output=result_output,
                prompt_versions=prompt_versions,
                token_usage=token_usage,
                error_code="AI_PROVIDER_UNAVAILABLE",
                error_message="provider unavailable, fallback to offline mode",
            )
        return self.make_success_result(
            job_id=spec.job_id,
            provider_used=output.provider_status,
            output=result_output,
            prompt_versions=prompt_versions,
            token_usage=token_usage,
        )

    async def _execute_technical_document(
        self,
        spec: JobSpec,
        payload: dict[str, Any],
        options: TechnicalDocumentOptions,
    ) -> JobResult:
        fingerprint = hash_payload(
            {
                "technicalDocument": options.to_dict(),
                "projectInfo": payload.get("projectInfo", {}),
                "requirements": payload.get("requirements", payload.get("tenderRequirements", [])),
                "library": payload.get("library", []),
            }
        )
        checkpoint = _load_checkpoint(spec.job_id, fingerprint)
        if checkpoint is None:
            checkpoint = await self._create_plan(spec, payload, options, fingerprint)
            _save_checkpoint(spec.job_id, checkpoint)

        self._report_progress(checkpoint.completed_paragraphs, options.total_paragraphs, "生成技术文档")
        for section_index, section in enumerate(options.sections):
            generated_section = _ensure_section(checkpoint, section, options)
            paragraph_start = len(generated_section["paragraphs"])
            for paragraph_index in range(paragraph_start + 1, section.target_paragraphs + 1):
                context = build_bounded_context(
                    payload,
                    options=options,
                    section=section,
                    completed_paragraphs=_flatten_paragraphs(checkpoint.sections),
                )
                call_payload = {
                    "templateName": options.template_name,
                    "sectionHeading": section.heading,
                    "headingLevel": section.heading_level,
                    "sectionInstructions": section.instructions,
                    "paragraphIndex": paragraph_index,
                    "paragraphCount": section.target_paragraphs,
                    "targetWords": section.target_words_per_paragraph,
                    "requireEvidence": options.require_evidence,
                    "imageAnchors": compact_json(
                        [image.to_dict() for image in options.images_for_section(section.key)]
                    ),
                    "approvedPlan": compact_json(checkpoint.plan),
                    "context": context,
                }
                child_spec = _child_spec(
                    spec,
                    prompt_name=_PARAGRAPH_PROMPT,
                    payload=call_payload,
                    stage=f"section:{section.key}:paragraph:{paragraph_index}",
                )
                model_output = await invoke(child_spec, payload=call_payload)
                paragraph = _normalize_paragraph(
                    model_output,
                    require_evidence=options.require_evidence,
                )
                generated_section["paragraphs"].append(
                    {
                        "index": paragraph_index,
                        "text": paragraph["paragraph"],
                        "evidence": paragraph["evidence"],
                    }
                )
                _record_call(checkpoint, model_output)
                _save_checkpoint(spec.job_id, checkpoint)
                self._report_progress(
                    checkpoint.completed_paragraphs,
                    options.total_paragraphs,
                    f"{section.heading} · 第 {paragraph_index}/{section.target_paragraphs} 段",
                )

            if section_index + 1 < len(options.sections):
                _save_checkpoint(spec.job_id, checkpoint)

        technical_document = _document_output(checkpoint, options, status="completed")
        result_output = {
            "outline": _canonical_outline(options),
            "technicalDocument": technical_document,
            "generationCheckpoint": _checkpoint_summary(checkpoint, options, completed=True),
        }
        provider_status = _aggregate_provider_status(checkpoint.provider_statuses)
        _delete_checkpoint(spec.job_id)
        self._report_progress(options.total_paragraphs, options.total_paragraphs, "技术文档生成完成")
        if provider_status == ProviderStatus.OFFLINE:
            return self.make_partial_result(
                job_id=spec.job_id,
                output=result_output,
                prompt_versions=checkpoint.prompt_versions,
                token_usage=checkpoint.token_usage,
                error_code="AI_PROVIDER_UNAVAILABLE",
                error_message="one or more paragraphs used the offline provider; manual review is required",
            )
        return self.make_success_result(
            job_id=spec.job_id,
            provider_used=provider_status,
            output=result_output,
            prompt_versions=checkpoint.prompt_versions,
            token_usage=checkpoint.token_usage,
        )

    async def _create_plan(
        self,
        spec: JobSpec,
        payload: dict[str, Any],
        options: TechnicalDocumentOptions,
        fingerprint: str,
    ) -> _GenerationCheckpoint:
        context = build_bounded_context(
            payload,
            options=options,
            section=options.sections[0],
            completed_paragraphs=[],
        )
        call_payload = {
            "templateName": options.template_name,
            "sections": compact_json([section.to_dict() for section in options.sections]),
            "imageAnchors": compact_json([image.to_dict() for image in options.reference_images]),
            "context": context,
        }
        child_spec = _child_spec(
            spec,
            prompt_name=_PLAN_PROMPT,
            payload=call_payload,
            stage="plan",
        )
        model_output = await invoke(child_spec, payload=call_payload)
        plan = _normalize_plan(model_output)
        checkpoint = _GenerationCheckpoint(fingerprint=fingerprint, plan=plan)
        _record_call(checkpoint, model_output)
        return checkpoint

    def _report_progress(self, completed: int, total: int, step: str) -> None:
        percent = 5 if total <= 0 else min(99, 5 + int((completed / total) * 94))
        if completed >= total > 0:
            percent = 100
        try:
            self.update_progress(percent, step)
        except Exception:  # pragma: no cover - direct unit calls do not have a Celery request/backend
            logger.debug("unable to publish generation progress", exc_info=True)

    def execute(self, spec: JobSpec, payload: dict[str, Any]) -> JobResult:
        return cast(JobResult, _run_async(self._execute(spec, payload)))

    def run(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return run_task_handler(self, lambda spec, data: self.execute(spec, dict(data)))(job_id, payload)


def _child_spec(
    parent: JobSpec,
    *,
    prompt_name: str,
    payload: dict[str, Any],
    stage: str,
) -> JobSpec:
    return JobSpec(
        job_id=parent.job_id,
        scene=parent.scene,
        aggregate_id=parent.aggregate_id,
        aggregate_type=parent.aggregate_type,
        prompt_name=prompt_name,
        prompt_version=_TECHNICAL_PROMPT_VERSION,
        input_payload=payload,
        tenant_id=parent.tenant_id,
        user_id=parent.user_id,
        idempotency_key=parent.idempotency_key,
        metadata={**parent.metadata, "technicalDocumentStage": stage},
    )


def _normalize_plan(output: ProviderOutput) -> dict[str, Any]:
    structured = _structured_mapping(output)
    raw_section_plan = structured.get("sectionPlan", [])
    raw_warnings = structured.get("warnings", [])
    if not isinstance(raw_section_plan, list) or not isinstance(raw_warnings, list):
        raise GeneratedContentValidationError("planning response must contain sectionPlan and warnings arrays")
    return {
        "planApproved": bool(structured.get("planApproved", True)),
        "sectionPlan": raw_section_plan,
        "warnings": raw_warnings,
    }


def _normalize_paragraph(output: ProviderOutput, *, require_evidence: bool) -> dict[str, Any]:
    structured = _structured_mapping(output)
    paragraph = structured.get("paragraph")
    evidence = structured.get("evidence", [])
    if not isinstance(paragraph, str) or not paragraph.strip():
        raise GeneratedContentValidationError("paragraph response must contain non-empty paragraph text")
    if not isinstance(evidence, list):
        raise GeneratedContentValidationError("paragraph evidence must be an array")
    if require_evidence and not evidence:
        raise GeneratedContentValidationError("paragraph evidence is required by the document template")
    return {"paragraph": paragraph.strip(), "evidence": evidence}


def _structured_mapping(output: ProviderOutput) -> Mapping[str, Any]:
    if isinstance(output.structured, Mapping):
        return output.structured
    try:
        decoded = json.loads(output.text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise GeneratedContentValidationError("model response is not a JSON object") from exc
    if not isinstance(decoded, Mapping):
        raise GeneratedContentValidationError("model response is not a JSON object")
    return decoded


def _ensure_section(
    checkpoint: _GenerationCheckpoint,
    section: SectionTemplate,
    options: TechnicalDocumentOptions,
) -> dict[str, Any]:
    section_index = len(checkpoint.sections)
    if section_index < len(options.sections) and options.sections[section_index].key == section.key:
        generated = {
            "key": section.key,
            "heading": section.heading,
            "headingLevel": section.heading_level,
            "instructions": section.instructions,
            "required": section.required,
            "targetParagraphs": section.target_paragraphs,
            "targetWordsPerParagraph": section.target_words_per_paragraph,
            "paragraphs": [],
            "images": [image.to_dict() for image in options.images_for_section(section.key)],
        }
        checkpoint.sections.append(generated)
        return generated

    for generated in checkpoint.sections:
        if generated.get("key") == section.key:
            return generated
    raise GeneratedContentValidationError("generation checkpoint section order is inconsistent")


def _record_call(checkpoint: _GenerationCheckpoint, output: ProviderOutput) -> None:
    checkpoint.prompt_versions.append(output.prompt_version)
    checkpoint.token_usage = checkpoint.token_usage + output.prompt_version.token_usage
    checkpoint.provider_statuses.append(output.provider_status)


def _canonical_outline(options: TechnicalDocumentOptions) -> list[dict[str, Any]]:
    return [
        {
            "section": section.heading,
            "sectionKey": section.key,
            "headingLevel": section.heading_level,
            "estimatedWords": section.target_paragraphs * section.target_words_per_paragraph,
        }
        for section in options.sections
    ]


def _document_output(
    checkpoint: _GenerationCheckpoint,
    options: TechnicalDocumentOptions,
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "strategy": options.strategy,
        "templateName": options.template_name,
        "preserveHeadingNumbering": options.preserve_heading_numbering,
        "requireEvidence": options.require_evidence,
        "status": status,
        "sections": copy.deepcopy(checkpoint.sections),
        "referenceImages": [image.to_dict() for image in options.reference_images],
        "plan": copy.deepcopy(checkpoint.plan),
    }


def _checkpoint_summary(
    checkpoint: _GenerationCheckpoint,
    options: TechnicalDocumentOptions,
    *,
    completed: bool,
) -> dict[str, Any]:
    completed_count = checkpoint.completed_paragraphs
    next_section_key: str | None = None
    next_paragraph_index: int | None = None
    if not completed:
        for section in options.sections:
            generated = next((item for item in checkpoint.sections if item.get("key") == section.key), None)
            count = len(generated.get("paragraphs", [])) if generated else 0
            if count < section.target_paragraphs:
                next_section_key = section.key
                next_paragraph_index = count + 1
                break
    return {
        "fingerprint": checkpoint.fingerprint,
        "status": "completed" if completed else "resumable",
        "completedParagraphs": completed_count,
        "totalParagraphs": options.total_paragraphs,
        "nextSectionKey": next_section_key,
        "nextParagraphIndex": next_paragraph_index,
    }


def _flatten_paragraphs(sections: list[dict[str, Any]]) -> list[Mapping[str, Any]]:
    flattened: list[Mapping[str, Any]] = []
    for section in sections:
        section_key = str(section.get("key", ""))
        for paragraph in section.get("paragraphs", []):
            if isinstance(paragraph, Mapping):
                flattened.append({"sectionKey": section_key, **dict(paragraph)})
    return flattened


def _aggregate_provider_status(statuses: list[ProviderStatus]) -> ProviderStatus:
    if ProviderStatus.OFFLINE in statuses or not statuses:
        return ProviderStatus.OFFLINE
    if ProviderStatus.FALLBACK in statuses:
        return ProviderStatus.FALLBACK
    return ProviderStatus.PRIMARY


def _load_checkpoint(job_id: str, fingerprint: str) -> _GenerationCheckpoint | None:
    with _CHECKPOINT_LOCK:
        checkpoint = _CHECKPOINTS.get(job_id)
        if checkpoint is None or checkpoint.fingerprint != fingerprint:
            return None
        return copy.deepcopy(checkpoint)


def _save_checkpoint(job_id: str, checkpoint: _GenerationCheckpoint) -> None:
    with _CHECKPOINT_LOCK:
        _CHECKPOINTS[job_id] = copy.deepcopy(checkpoint)


def _delete_checkpoint(job_id: str) -> None:
    with _CHECKPOINT_LOCK:
        _CHECKPOINTS.pop(job_id, None)


def reset_technical_document_checkpoints_for_tests() -> None:
    """Clear process-local checkpoints between deterministic tests."""

    with _CHECKPOINT_LOCK:
        _CHECKPOINTS.clear()


def _run_async(coro: Any) -> Any:  # noqa: ANN401
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        return asyncio.ensure_future(coro)
    return loop.run_until_complete(coro)


__all__ = [
    "BiddingGeneratorTask",
    "GeneratedContentValidationError",
    "reset_technical_document_checkpoints_for_tests",
]

# Register with Celery once when the worker module is imported.
from app.workers.registry import register_task as _register_task  # noqa: E402

_register_task(BiddingGeneratorTask())
