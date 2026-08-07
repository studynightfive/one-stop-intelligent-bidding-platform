"""离线固定样本（黄金快照）。

用于 ``tests/ai/test_regression.py``：每次升级提示词或 Provider 后，
用相同输入调用离线 Provider，确保输出结构稳定。

任何 prompt 升级必须：
1. 在此处新增一行 sample；
2. 在 PR 描述中列出 sample 与旧输出的 diff；
3. CI 通过 = 结构稳定（无需数值相等）。
"""

from __future__ import annotations

from typing import NamedTuple


class Sample(NamedTuple):
    prompt_name: str
    prompt_version: str
    payload: dict[str, object]
    expected_provider: str  # fake / offline
    required_keys: tuple[str, ...]


SAMPLES: tuple[Sample, ...] = (
    Sample(
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        payload={
            "projectName": "智慧校园",
            "rawText": "## 背景\n推进数字化\n\n## 范围\n教学管理平台\n",
        },
        expected_provider="fake",
        required_keys=("summary", "sections", "sectionCount"),
    ),
    Sample(
        prompt_name="requirement_extract",
        prompt_version="1.0.0",
        payload={
            "projectName": "智慧校园",
            "tenderText": "需 ISO9001 与三年业绩",
        },
        expected_provider="fake",
        required_keys=(
            "qualificationRequirements",
            "technicalRequirements",
            "scoringItems",
            "disqualificationItems",
        ),
    ),
    Sample(
        prompt_name="material_match",
        prompt_version="1.0.0",
        payload={
            "requirements": [{"name": "ISO 9001"}],
            "qualifications": [],
            "fragments": [],
        },
        expected_provider="fake",
        required_keys=("matches",),
    ),
    Sample(
        prompt_name="bid_review",
        prompt_version="1.0.0",
        payload={
            "reviewTypes": ["content"],
            "fileVersionIds": [],
            "materials": [],
        },
        expected_provider="fake",
        required_keys=("summary", "findings"),
    ),
    Sample(
        prompt_name="bid_generate",
        prompt_version="1.0.0",
        payload={"projectInfo": {}, "library": [], "mode": "split"},
        expected_provider="fake",
        required_keys=("outline", "wordCountEstimate"),
    ),
    Sample(
        prompt_name="risk_check",
        prompt_version="1.0.0",
        payload={"evaluationId": "eval-1", "suppliers": [], "history": []},
        expected_provider="fake",
        required_keys=("findings", "highRiskCount", "summary"),
    ),
    Sample(
        prompt_name="evaluation_check",
        prompt_version="1.0.0",
        payload={
            "evaluationId": "eval-1",
            "requiredMaterials": [{"name": "营业执照"}],
            "submissions": [],
        },
        expected_provider="fake",
        required_keys=("completeness", "missing"),
    ),
    Sample(
        prompt_name="evaluation_score",
        prompt_version="1.0.0",
        payload={
            "scoringCriteria": [{"name": "技术方案", "maxScore": "100"}],
            "supplierResponse": {},
        },
        expected_provider="fake",
        required_keys=("scores", "overall"),
    ),
    Sample(
        prompt_name="report_generate",
        prompt_version="1.0.0",
        payload={"evaluationId": "eval-1", "ranking": [], "risks": []},
        expected_provider="fake",
        required_keys=("reportTitle", "sections"),
    ),
)


__all__ = ["SAMPLES", "Sample"]
