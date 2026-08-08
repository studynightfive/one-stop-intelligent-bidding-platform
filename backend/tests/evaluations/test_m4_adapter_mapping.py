"""M4 适配映射纯函数测试（不 import 真实 M4 模块）。"""

from app.domains.evaluations.m4_adapters import M4_STATUS_TO_CONTRACT, M6_JOB_TYPE_TO_M4


def test_m6_job_types_map_to_m4_enums() -> None:
    assert M6_JOB_TYPE_TO_M4["evaluation.material_check"] == "ai_analysis"
    assert M6_JOB_TYPE_TO_M4["evaluation.report_generate"] == "document_generation"


def test_m4_status_normalized_to_contract() -> None:
    assert M4_STATUS_TO_CONTRACT["pending"] == "queued"
    assert M4_STATUS_TO_CONTRACT["completed"] == "succeeded"
