"""M6 报价公式辅助（禁止 float）。"""

from __future__ import annotations

from decimal import Decimal

from app.domains.evaluations.money import SCORE_QUANT, format_score


def price_score(*, quote: Decimal, lowest_quote: Decimal, max_score: Decimal) -> str:
    """常见最低价得满分公式：lowest / quote * max_score。"""
    if quote <= 0:
        return format_score(Decimal("0"))
    raw = (lowest_quote / quote) * max_score
    return format_score(raw.quantize(SCORE_QUANT))
