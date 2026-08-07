"""金额与分数：禁止 float，统一 Decimal <-> Money 字符串。"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.domains.evaluations.errors import validation_error

MONEY_QUANT = Decimal("0.01")
SCORE_QUANT = Decimal("0.01")
WEIGHT_QUANT = Decimal("0.01")
MONEY_PATTERN = re.compile(r"^-?(0|[1-9]\d*)\.\d{2}$")


def parse_money(value: str) -> Decimal:
    text = str(value).strip()
    if not MONEY_PATTERN.fullmatch(text):
        raise validation_error("金额必须为两位小数字符串")
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise validation_error("金额格式无效") from exc
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def parse_score(value: str) -> Decimal:
    try:
        score = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise validation_error("分数字段格式无效") from exc
    return score.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


def format_score(value: Decimal) -> str:
    return str(value.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP))


def parse_weight(value: str) -> Decimal:
    try:
        weight = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise validation_error("权重格式无效") from exc
    return weight.quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP)


def weighted_score(raw: Decimal, weight_percent: Decimal) -> Decimal:
    return (raw * weight_percent / Decimal("100")).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)
