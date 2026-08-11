"""M5 输入校验：DTO 字段必填/范围/一致性检查。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.ai.technical_document import TechnicalDocumentOptions, TechnicalDocumentValidationError
from app.domains.bids.enums import (
    BID_MATERIAL_CATEGORIES,
    BID_REVIEW_DECISIONS,
    BID_REVIEW_TYPES,
    DOCUMENT_GEN_MODES,
    DOCUMENT_SECTIONS,
    TASK_ASSIGNMENT_ROLES,
    TEMPLATE_MODES,
)
from app.domains.bids.errors import validation_error

_SID_PATTERN = re.compile(r"^[A-Za-z0-9_.\-:]{1,128}$")


def reject_unknown(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise validation_error(
            "请求体包含未定义字段",
            field_errors=[{"field": key, "code": "EXTRA_FORBIDDEN", "message": "契约未定义该字段"} for key in unknown],
        )


def parse_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise validation_error(
            "布尔字段格式错误",
            field_errors=[{"field": field, "code": "TYPE", "message": f"{field} 必须为布尔值"}],
        )
    return value


def parse_non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise validation_error(
            "整数字段格式错误",
            field_errors=[{"field": field, "code": "RANGE", "message": f"{field} 必须为非负整数"}],
        )
    return value


def require_str(payload: dict[str, Any], key: str, *, max_length: int = 255) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise validation_error(
            "请求体缺少必要字段", field_errors=[{"field": key, "code": "REQUIRED", "message": f"{key} 必填"}]
        )
    text = value.strip()
    if len(text) > max_length:
        raise validation_error(
            "字段过长", field_errors=[{"field": key, "code": "MAX_LENGTH", "message": f"{key} 最长 {max_length} 字符"}]
        )
    return text


def require_id(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise validation_error(
            "请求体缺少必要字段", field_errors=[{"field": key, "code": "REQUIRED", "message": f"{key} 必填"}]
        )
    text = value.strip()
    if not _SID_PATTERN.match(text):
        raise validation_error(
            "字段格式错误", field_errors=[{"field": key, "code": "FORMAT", "message": f"{key} 仅支持字母数字与 _.-:"}]
        )
    return text


def parse_dt(value: Any, *, field: str = "date") -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif not isinstance(value, str):
        raise validation_error(
            "时间字段缺失", field_errors=[{"field": field, "code": "REQUIRED", "message": f"{field} 必填"}]
        )
    else:
        try:
            # 兼容 OpenAPI IsoDateTime 字符串（Z 后缀或带时区）
            text = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise validation_error(
                "时间字段格式错误",
                field_errors=[{"field": field, "code": "FORMAT", "message": f"{field} 无法解析为时间"}],
            ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise validation_error(
            "时间字段必须包含时区",
            field_errors=[{"field": field, "code": "TIMEZONE_REQUIRED", "message": f"{field} 必须包含时区"}],
        )
    return parsed


def parse_enum(value: Any, allowed: tuple[str, ...], *, field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise validation_error(
            "枚举值不合法",
            field_errors=[{"field": field, "code": "ENUM", "message": f"{field} 必须为 {','.join(allowed)}"}],
        )
    return value


def parse_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise validation_error(
            "tags 必须是字符串数组", field_errors=[{"field": "tags", "code": "TYPE", "message": "tags 必须是数组"}]
        )
    cleaned: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise validation_error(
                "tags 必须是非空字符串数组",
                field_errors=[{"field": f"tags[{index}]", "code": "TYPE", "message": "必须为非空字符串"}],
            )
        cleaned.append(item.strip())
    if len(cleaned) != len(set(cleaned)):
        raise validation_error("tags 不可重复")
    return cleaned


def optional_str(payload: dict[str, Any], key: str, *, max_length: int) -> str:
    if key not in payload:
        return ""
    value = payload[key]
    if not isinstance(value, str):
        raise validation_error(
            "字符串字段格式错误",
            field_errors=[{"field": key, "code": "TYPE", "message": f"{key} 必须为字符串"}],
        )
    text = value.strip()
    if len(text) > max_length:
        raise validation_error(
            "字段过长", field_errors=[{"field": key, "code": "MAX_LENGTH", "message": f"{key} 最长 {max_length} 字符"}]
        )
    return text


def validate_create_bid_task(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(
        payload,
        {
            "projectName",
            "tenderNo",
            "tenderEntity",
            "deadline",
            "assigneeId",
            "tenderFileId",
            "tags",
            "description",
        },
    )
    return {
        "project_name": require_str(payload, "projectName"),
        "tender_no": optional_str(payload, "tenderNo", max_length=128),
        "tender_entity": optional_str(payload, "tenderEntity", max_length=255),
        "deadline": parse_dt(payload.get("deadline"), field="deadline"),
        "assignee_id": require_id(payload, "assigneeId"),
        "tender_file_id": require_id(payload, "tenderFileId"),
        "tags": parse_tags(payload["tags"]) if "tags" in payload else [],
        "description": optional_str(payload, "description", max_length=5000) or None
        if "description" in payload
        else None,
    }


def validate_update_bid_task(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(
        payload,
        {"projectName", "tenderNo", "tenderEntity", "deadline", "assigneeId", "tags", "description"},
    )
    cleaned: dict[str, Any] = {}
    if "projectName" in payload:
        cleaned["project_name"] = require_str(payload, "projectName")
    if "tenderNo" in payload:
        cleaned["tender_no"] = require_str(payload, "tenderNo", max_length=128)
    if "tenderEntity" in payload:
        cleaned["tender_entity"] = require_str(payload, "tenderEntity")
    if "deadline" in payload:
        cleaned["deadline"] = parse_dt(payload["deadline"], field="deadline")
    if "assigneeId" in payload:
        cleaned["assignee_id"] = require_id(payload, "assigneeId")
    if "tags" in payload:
        cleaned["tags"] = parse_tags(payload["tags"])
    if "description" in payload:
        cleaned["description"] = optional_str(payload, "description", max_length=5000) or None
    return cleaned


def validate_assignment(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(payload, {"userId", "roleInTask"})
    return {
        "user_id": require_id(payload, "userId"),
        "role_in_task": parse_enum(payload.get("roleInTask"), TASK_ASSIGNMENT_ROLES, field="roleInTask"),
    }


def validate_create_material(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(payload, {"name", "category", "requirement", "required", "sortOrder"})
    return {
        "name": require_str(payload, "name"),
        "category": parse_enum(payload.get("category"), BID_MATERIAL_CATEGORIES, field="category"),
        "requirement": require_str(payload, "requirement", max_length=2000),
        "required": parse_bool(payload.get("required"), field="required"),
        "sort_order": parse_non_negative_int(payload.get("sortOrder"), field="sortOrder"),
        "source": "manual",
        "source_id": None,
    }


def validate_update_material(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(payload, {"name", "category", "requirement", "required", "sortOrder", "sourceId"})
    cleaned: dict[str, Any] = {}
    if "name" in payload:
        cleaned["name"] = require_str(payload, "name")
    if "category" in payload:
        cleaned["category"] = parse_enum(payload["category"], BID_MATERIAL_CATEGORIES, field="category")
    if "requirement" in payload:
        cleaned["requirement"] = require_str(payload, "requirement", max_length=2000)
    if "required" in payload:
        cleaned["required"] = parse_bool(payload["required"], field="required")
    if "sortOrder" in payload:
        cleaned["sort_order"] = parse_non_negative_int(payload["sortOrder"], field="sortOrder")
    if "sourceId" in payload:
        cleaned["source_id"] = require_id(payload, "sourceId")
    return cleaned


def validate_batch_bind(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise validation_error("请求体格式错误")
    reject_unknown(payload, {"bindings", "replaceExisting"})
    bindings = payload.get("bindings", [])
    if not isinstance(bindings, list) or not bindings:
        raise validation_error(
            "bindings 必填且至少 1 项",
            field_errors=[{"field": "bindings", "code": "REQUIRED", "message": "bindings 必填"}],
        )
    cleaned: list[dict[str, str]] = []
    for idx, raw in enumerate(bindings):
        if not isinstance(raw, dict):
            raise validation_error(
                "binding 格式错误",
                field_errors=[{"field": f"bindings[{idx}]", "code": "TYPE", "message": "binding 必须为对象"}],
            )
        reject_unknown(raw, {"materialId", "fileId"})
        cleaned.append(
            {
                "materialId": require_id(raw, "materialId"),
                "fileId": require_id(raw, "fileId"),
            }
        )
    material_ids = [item["materialId"] for item in cleaned]
    if len(material_ids) != len(set(material_ids)):
        raise validation_error("bindings.materialId 不可重复")
    replace = parse_bool(payload.get("replaceExisting"), field="replaceExisting")
    return {"bindings": cleaned, "replaceExisting": replace}


def validate_create_review(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise validation_error("请求体格式错误")
    reject_unknown(payload, {"types", "fileVersionIds"})
    types = payload.get("types", [])
    if not isinstance(types, list) or not types:
        raise validation_error(
            "types 必填且至少 1 项",
            field_errors=[{"field": "types", "code": "REQUIRED", "message": "types 必填"}],
        )
    parsed = [parse_enum(item, BID_REVIEW_TYPES, field=f"types[{i}]") for i, item in enumerate(types)]
    if len(set(parsed)) != len(parsed):
        raise validation_error(
            "types 含重复项", field_errors=[{"field": "types", "code": "DUPLICATE", "message": "types 不可重复"}]
        )
    cleaned_versions: list[str] = []
    if "fileVersionIds" in payload:
        file_version_ids = payload["fileVersionIds"]
        if not isinstance(file_version_ids, list):
            raise validation_error("fileVersionIds 必须为数组")
        for fid in file_version_ids:
            if not isinstance(fid, str) or not fid.strip() or not _SID_PATTERN.match(fid.strip()):
                raise validation_error("fileVersionIds 包含非法 ID")
            cleaned_versions.append(fid.strip())
        if len(cleaned_versions) != len(set(cleaned_versions)):
            raise validation_error("fileVersionIds 不可重复")
    return {"types": parsed, "fileVersionIds": cleaned_versions}


def validate_review_decision(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise validation_error("请求体格式错误")
    reject_unknown(payload, {"decision", "comment"})
    comment = optional_str(payload, "comment", max_length=2000) or None if "comment" in payload else None
    return {
        "decision": parse_enum(payload.get("decision"), BID_REVIEW_DECISIONS, field="decision"),
        "comment": comment,
    }


def validate_requirements_patch(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise validation_error("请求体格式错误")
    reject_unknown(
        payload,
        {
            "projectInfo",
            "scoringItems",
            "disqualificationItems",
            "qualificationRequirements",
            "technicalRequirements",
        },
    )
    cleaned: dict[str, Any] = {}
    if "projectInfo" in payload:
        info = payload["projectInfo"]
        if not isinstance(info, dict):
            raise validation_error(
                "projectInfo 必须是对象", field_errors=[{"field": "projectInfo", "code": "TYPE", "message": "对象"}]
            )
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in info.items()):
            raise validation_error("projectInfo 的键和值必须为字符串")
        cleaned["project_info"] = dict(info)
    if "scoringItems" in payload:
        items = payload["scoringItems"]
        if not isinstance(items, list):
            raise validation_error("scoringItems 必须是数组")
        cleaned["scoring_items"] = [
            _require_requirement_item(item, fields=("name", "score", "basis"), field=f"scoringItems[{index}]")
            for index, item in enumerate(items)
        ]
    if "disqualificationItems" in payload:
        items = payload["disqualificationItems"]
        if not isinstance(items, list):
            raise validation_error("disqualificationItems 必须是数组")
        cleaned["disqualification_items"] = [
            _require_requirement_item(item, fields=("name", "basis"), field=f"disqualificationItems[{index}]")
            for index, item in enumerate(items)
        ]
    if "qualificationRequirements" in payload:
        items = payload["qualificationRequirements"]
        if not isinstance(items, list):
            raise validation_error("qualificationRequirements 必须是数组")
        cleaned["qualification_requirements"] = _require_string_list(items, field="qualificationRequirements")
    if "technicalRequirements" in payload:
        items = payload["technicalRequirements"]
        if not isinstance(items, list):
            raise validation_error("technicalRequirements 必须是数组")
        cleaned["technical_requirements"] = _require_string_list(items, field="technicalRequirements")
    return cleaned


def validate_document_generate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise validation_error("请求体格式错误")
    reject_unknown(
        payload,
        {"mode", "sections", "templateMode", "documentTemplateId", "includeWatermark", "technicalDocument"},
    )
    mode = payload.get("mode")
    sections = payload.get("sections") or []
    if not isinstance(sections, list) or not sections:
        raise validation_error(
            "sections 必填且至少 1 项",
            field_errors=[{"field": "sections", "code": "REQUIRED", "message": "sections 必填"}],
        )
    parsed_mode = parse_enum(mode, DOCUMENT_GEN_MODES, field="mode")
    parsed_sections = [parse_enum(s, DOCUMENT_SECTIONS, field=f"sections[{i}]") for i, s in enumerate(sections)]
    if len(set(parsed_sections)) != len(parsed_sections):
        raise validation_error("sections 含重复项")
    template_mode = parse_enum(payload.get("templateMode"), TEMPLATE_MODES, field="templateMode")
    technical_document: dict[str, Any] | None = None
    if "technicalDocument" in payload and payload["technicalDocument"] is not None:
        try:
            validated = TechnicalDocumentOptions.from_mapping(payload["technicalDocument"])
        except TechnicalDocumentValidationError as exc:
            raise validation_error(
                "technicalDocument 格式错误",
                field_errors=[
                    {
                        "field": "technicalDocument",
                        "code": "INVALID_TECHNICAL_DOCUMENT",
                        "message": str(exc),
                    }
                ],
            ) from exc
        if "technical" not in parsed_sections:
            raise validation_error(
                "technicalDocument 仅能用于技术文档生成",
                field_errors=[
                    {
                        "field": "sections",
                        "code": "MISSING_TECHNICAL_SECTION",
                        "message": "提供 technicalDocument 时 sections 必须包含 technical",
                    }
                ],
            )
        technical_document = validated.to_dict()
    return {
        "mode": parsed_mode,
        "sections": parsed_sections,
        "templateMode": template_mode,
        "documentTemplateId": require_id(payload, "documentTemplateId") if "documentTemplateId" in payload else None,
        "includeWatermark": parse_bool(payload.get("includeWatermark"), field="includeWatermark"),
        "technicalDocument": technical_document,
    }


def _require_requirement_item(
    value: Any,
    *,
    fields: tuple[str, ...],
    field: str,
) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise validation_error(f"{field} 字段不完整")
    if not all(isinstance(value[name], str) and value[name].strip() for name in fields):
        raise validation_error(f"{field} 的值必须为非空字符串")
    return {name: value[name].strip() for name in fields}


def _require_string_list(items: list[Any], *, field: str) -> list[str]:
    cleaned: list[str] = []
    for index, value in enumerate(items):
        if not isinstance(value, str) or not value.strip():
            raise validation_error(f"{field}[{index}] 必须为非空字符串")
        cleaned.append(value.strip())
    return cleaned
