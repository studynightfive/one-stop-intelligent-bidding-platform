"""Technical document input validation and bounded-context helpers.

The public request shape is defined in ``contracts/openapi.yaml``.  This module
keeps the worker independent from the generated Pydantic models while applying
the same limits before any model call is made.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

_SECTION_KEY = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
_IMAGE_PLACEMENTS = {"before_section", "after_paragraph", "after_section"}


class TechnicalDocumentValidationError(ValueError):
    """Raised when a technical-document request violates the locked contract."""


@dataclass(frozen=True, slots=True)
class SectionTemplate:
    key: str
    heading: str
    heading_level: int
    instructions: str
    target_paragraphs: int
    target_words_per_paragraph: int
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "heading": self.heading,
            "headingLevel": self.heading_level,
            "instructions": self.instructions,
            "targetParagraphs": self.target_paragraphs,
            "targetWordsPerParagraph": self.target_words_per_paragraph,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class ImageAnchor:
    file_id: str
    section_key: str
    caption: str
    alt_text: str | None
    placement: str
    after_paragraph_index: int | None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "fileId": self.file_id,
            "sectionKey": self.section_key,
            "caption": self.caption,
            "placement": self.placement,
        }
        if self.alt_text is not None:
            data["altText"] = self.alt_text
        if self.after_paragraph_index is not None:
            data["afterParagraphIndex"] = self.after_paragraph_index
        return data


@dataclass(frozen=True, slots=True)
class TechnicalDocumentOptions:
    strategy: str
    template_name: str
    sections: tuple[SectionTemplate, ...]
    reference_images: tuple[ImageAnchor, ...]
    context_window_characters: int
    carry_forward_paragraphs: int
    preserve_heading_numbering: bool
    require_evidence: bool

    @property
    def total_paragraphs(self) -> int:
        return sum(section.target_paragraphs for section in self.sections)

    def images_for_section(self, section_key: str) -> list[ImageAnchor]:
        return [image for image in self.reference_images if image.section_key == section_key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "templateName": self.template_name,
            "sections": [section.to_dict() for section in self.sections],
            "referenceImages": [image.to_dict() for image in self.reference_images],
            "contextWindowCharacters": self.context_window_characters,
            "carryForwardParagraphs": self.carry_forward_paragraphs,
            "preserveHeadingNumbering": self.preserve_heading_numbering,
            "requireEvidence": self.require_evidence,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> TechnicalDocumentOptions:
        _reject_unknown_fields(
            raw,
            {
                "strategy",
                "templateName",
                "sections",
                "referenceImages",
                "contextWindowCharacters",
                "carryForwardParagraphs",
                "preserveHeadingNumbering",
                "requireEvidence",
            },
            "technicalDocument",
        )
        strategy = _required_string(raw, "strategy", "technicalDocument", maximum=40)
        if strategy != "paragraph_by_paragraph":
            raise TechnicalDocumentValidationError("technicalDocument.strategy must be 'paragraph_by_paragraph'")
        template_name = _required_string(raw, "templateName", "technicalDocument", maximum=200)
        raw_sections = _required_list(raw, "sections", "technicalDocument", minimum=1, maximum=60)
        sections = tuple(_parse_section(item, index) for index, item in enumerate(raw_sections))
        keys = [section.key for section in sections]
        if len(keys) != len(set(keys)):
            raise TechnicalDocumentValidationError("technicalDocument.sections contains duplicate keys")

        raw_images = _required_list(raw, "referenceImages", "technicalDocument", minimum=0, maximum=50)
        images = tuple(_parse_image(item, index) for index, item in enumerate(raw_images))
        sections_by_key = {section.key: section for section in sections}
        for image in images:
            section = sections_by_key.get(image.section_key)
            if section is None:
                raise TechnicalDocumentValidationError(
                    f"reference image {image.file_id!r} points to unknown section {image.section_key!r}"
                )
            if image.placement == "after_paragraph":
                if image.after_paragraph_index is None:
                    raise TechnicalDocumentValidationError(
                        f"reference image {image.file_id!r} requires afterParagraphIndex"
                    )
                if image.after_paragraph_index > section.target_paragraphs:
                    raise TechnicalDocumentValidationError(
                        f"reference image {image.file_id!r} is anchored after a missing paragraph"
                    )
            elif image.after_paragraph_index is not None:
                raise TechnicalDocumentValidationError(
                    f"reference image {image.file_id!r} may only set afterParagraphIndex with after_paragraph"
                )

        context_window = _required_int(
            raw,
            "contextWindowCharacters",
            "technicalDocument",
            minimum=2_000,
            maximum=200_000,
        )
        carry_forward = _required_int(
            raw,
            "carryForwardParagraphs",
            "technicalDocument",
            minimum=0,
            maximum=10,
        )
        preserve_numbering = _required_bool(raw, "preserveHeadingNumbering", "technicalDocument")
        require_evidence = _required_bool(raw, "requireEvidence", "technicalDocument")
        return cls(
            strategy=strategy,
            template_name=template_name,
            sections=sections,
            reference_images=images,
            context_window_characters=context_window,
            carry_forward_paragraphs=carry_forward,
            preserve_heading_numbering=preserve_numbering,
            require_evidence=require_evidence,
        )


def build_bounded_context(
    payload: Mapping[str, Any],
    *,
    options: TechnicalDocumentOptions,
    section: SectionTemplate,
    completed_paragraphs: Sequence[Mapping[str, Any]],
) -> str:
    """Build deterministic context without exceeding the configured character cap.

    Current-section images and recent generated paragraphs have highest priority;
    large project/library inputs are truncated last.  Image bytes are not placed
    in prompts: the model receives the locked file identifier, caption and alt
    text, while the document assembler later inserts the original binary.
    """

    recent = list(completed_paragraphs[-options.carry_forward_paragraphs :])
    chunks = [
        ("CURRENT_SECTION_IMAGES", [image.to_dict() for image in options.images_for_section(section.key)]),
        ("RECENT_GENERATED_PARAGRAPHS", recent),
        ("TENDER_REQUIREMENTS", payload.get("requirements", payload.get("tenderRequirements", []))),
        ("PROJECT_INFORMATION", payload.get("projectInfo", {})),
        ("QUALIFICATIONS_AND_FRAGMENT_LIBRARY", payload.get("library", [])),
    ]
    return _join_bounded_chunks(chunks, options.context_window_characters)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _join_bounded_chunks(chunks: Sequence[tuple[str, Any]], limit: int) -> str:
    result = ""
    for label, value in chunks:
        rendered = f"## {label}\n{compact_json(value)}\n"
        remaining = limit - len(result)
        if remaining <= 0:
            break
        if len(rendered) <= remaining:
            result += rendered
            continue
        marker = "\n...[context truncated]"
        if remaining <= len(marker):
            result += marker[:remaining]
        else:
            result += rendered[: remaining - len(marker)] + marker
        break
    return result


def _parse_section(raw: Any, index: int) -> SectionTemplate:
    path = f"technicalDocument.sections[{index}]"
    item = _mapping(raw, path)
    _reject_unknown_fields(
        item,
        {
            "key",
            "heading",
            "headingLevel",
            "instructions",
            "targetParagraphs",
            "targetWordsPerParagraph",
            "required",
        },
        path,
    )
    key = _required_string(item, "key", path, maximum=64)
    if not _SECTION_KEY.fullmatch(key):
        raise TechnicalDocumentValidationError(f"{path}.key has an invalid format")
    return SectionTemplate(
        key=key,
        heading=_required_string(item, "heading", path, maximum=200),
        heading_level=_required_int(item, "headingLevel", path, minimum=1, maximum=3),
        instructions=_required_string(item, "instructions", path, maximum=4_000),
        target_paragraphs=_required_int(item, "targetParagraphs", path, minimum=1, maximum=30),
        target_words_per_paragraph=_required_int(
            item,
            "targetWordsPerParagraph",
            path,
            minimum=80,
            maximum=1_500,
        ),
        required=_required_bool(item, "required", path),
    )


def _parse_image(raw: Any, index: int) -> ImageAnchor:
    path = f"technicalDocument.referenceImages[{index}]"
    item = _mapping(raw, path)
    _reject_unknown_fields(
        item,
        {"fileId", "sectionKey", "caption", "altText", "placement", "afterParagraphIndex"},
        path,
    )
    section_key = _required_string(item, "sectionKey", path, maximum=64)
    if not _SECTION_KEY.fullmatch(section_key):
        raise TechnicalDocumentValidationError(f"{path}.sectionKey has an invalid format")
    placement = _required_string(item, "placement", path, maximum=30)
    if placement not in _IMAGE_PLACEMENTS:
        raise TechnicalDocumentValidationError(f"{path}.placement is invalid")
    alt_text = _optional_string(item, "altText", path, maximum=500)
    after_index = None
    if "afterParagraphIndex" in item and item["afterParagraphIndex"] is not None:
        after_index = _required_int(item, "afterParagraphIndex", path, minimum=1, maximum=30)
    return ImageAnchor(
        file_id=_required_string(item, "fileId", path, maximum=200),
        section_key=section_key,
        caption=_required_string(item, "caption", path, maximum=300),
        alt_text=alt_text,
        placement=placement,
        after_paragraph_index=after_index,
    )


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TechnicalDocumentValidationError(f"{path} must be an object")
    return value


def _required_list(
    raw: Mapping[str, Any],
    key: str,
    path: str,
    *,
    minimum: int,
    maximum: int,
) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise TechnicalDocumentValidationError(f"{path}.{key} must be an array")
    if not minimum <= len(value) <= maximum:
        raise TechnicalDocumentValidationError(f"{path}.{key} must contain {minimum}..{maximum} items")
    return value


def _required_string(raw: Mapping[str, Any], key: str, path: str, *, maximum: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TechnicalDocumentValidationError(f"{path}.{key} must be a non-empty string")
    value = value.strip()
    if len(value) > maximum:
        raise TechnicalDocumentValidationError(f"{path}.{key} exceeds {maximum} characters")
    return value


def _optional_string(raw: Mapping[str, Any], key: str, path: str, *, maximum: int) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TechnicalDocumentValidationError(f"{path}.{key} must be a string")
    value = value.strip()
    if len(value) > maximum:
        raise TechnicalDocumentValidationError(f"{path}.{key} exceeds {maximum} characters")
    return value


def _required_int(
    raw: Mapping[str, Any],
    key: str,
    path: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TechnicalDocumentValidationError(f"{path}.{key} must be an integer")
    if not minimum <= value <= maximum:
        raise TechnicalDocumentValidationError(f"{path}.{key} must be between {minimum} and {maximum}")
    return value


def _required_bool(raw: Mapping[str, Any], key: str, path: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise TechnicalDocumentValidationError(f"{path}.{key} must be a boolean")
    return value


def _reject_unknown_fields(raw: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise TechnicalDocumentValidationError(f"{path} contains unknown fields: {', '.join(unknown)}")


__all__ = [
    "ImageAnchor",
    "SectionTemplate",
    "TechnicalDocumentOptions",
    "TechnicalDocumentValidationError",
    "build_bounded_context",
    "compact_json",
]
