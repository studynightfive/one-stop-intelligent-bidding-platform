"""发布前五步校验与日期关系校验。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domains.evaluations.entities import EvaluationEntity
from app.domains.evaluations.money import WEIGHT_QUANT


def validate_evaluation(entity: EvaluationEntity, *, now: datetime) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    # step 1 基本信息 / 日期
    if entity.supplier_deadline >= entity.evaluation_start_at:
        errors.append(
            {
                "step": 1,
                "field": "supplierDeadline",
                "code": "DATE_ORDER",
                "message": "供应商截止时间必须早于评标开始时间",
            }
        )
    if entity.evaluation_start_at >= entity.evaluation_end_at:
        errors.append(
            {
                "step": 1,
                "field": "evaluationEndAt",
                "code": "DATE_ORDER",
                "message": "评标结束时间必须晚于开始时间",
            }
        )
    if entity.supplier_deadline <= now and entity.status == "draft":
        warnings.append(
            {
                "step": 1,
                "field": "supplierDeadline",
                "code": "DEADLINE_SOON",
                "message": "供应商截止时间已过或临近",
            }
        )

    # step 2 材料
    if not entity.materials:
        errors.append({"step": 2, "field": "materials", "code": "REQUIRED", "message": "至少配置一项材料"})
    elif not any(m.required for m in entity.materials):
        warnings.append({"step": 2, "field": "materials", "code": "NO_REQUIRED", "message": "未设置任何必交材料"})

    # step 3 评分标准
    if not entity.criteria:
        errors.append({"step": 3, "field": "criteria", "code": "REQUIRED", "message": "至少配置一项评分标准"})
    else:
        total_weight = sum((c.weight_percent for c in entity.criteria), Decimal("0"))
        if total_weight.quantize(WEIGHT_QUANT) != Decimal("100.00"):
            errors.append(
                {
                    "step": 3,
                    "field": "criteria.weightPercent",
                    "code": "WEIGHT_SUM",
                    "message": f"评分权重合计必须为 100.00，当前为 {total_weight}",
                }
            )

    # step 4 评审设置 / 评委
    if not entity.reviewer_ids:
        errors.append({"step": 4, "field": "reviewers", "code": "REQUIRED", "message": "至少指定一名评委"})
    if entity.review_settings.multi_round_pricing and entity.review_settings.max_rounds < 2:
        errors.append(
            {
                "step": 4,
                "field": "reviewSettings.maxRounds",
                "code": "INVALID",
                "message": "启用多轮报价时 maxRounds 至少为 2",
            }
        )

    # step 5 供应商
    if len(entity.suppliers) < 1:
        errors.append({"step": 5, "field": "suppliers", "code": "REQUIRED", "message": "至少邀请一家供应商"})
    emails = [s.email.lower() for s in entity.suppliers]
    if len(emails) != len(set(emails)):
        errors.append({"step": 5, "field": "suppliers.email", "code": "DUPLICATE", "message": "供应商邮箱不可重复"})

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
