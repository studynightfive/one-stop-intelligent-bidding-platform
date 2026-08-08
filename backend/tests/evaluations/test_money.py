"""金额工具单元测试。"""

from decimal import Decimal

import pytest

from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.money import format_money, parse_money, weighted_score


def test_parse_and_format_money() -> None:
    assert format_money(parse_money("1234.50")) == "1234.50"


def test_reject_floatish_money() -> None:
    with pytest.raises(DomainError) as exc:
        parse_money("10.1")
    assert exc.value.code == "VALIDATION_ERROR"


def test_weighted_score_uses_decimal() -> None:
    assert weighted_score(Decimal("80.00"), Decimal("25.00")) == Decimal("20.00")
