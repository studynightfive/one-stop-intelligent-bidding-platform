"""Eager demo mode must apply M7 results back into the M6 read models."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.demo_seed import (
    DEMO_ADMIN_USER_ID,
    DEMO_EVALUATION_ID,
    DEMO_TENANT_ID,
)
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.ports import AuthPrincipal, JobRefSnapshot


class EagerResultJobs:
    async def enqueue(
        self,
        *,
        tenant_id: str,
        job_type: str,
        payload: dict[str, Any],
        created_by: str,
        project_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> JobRefSnapshot:
        _ = tenant_id, created_by, project_id, idempotency_key
        outputs: dict[str, dict[str, Any]] = {
            "evaluation.material_check": {"completeness": 0.9, "missing": ["报价清单"]},
            "evaluation.risk_check": {
                "findings": [
                    {
                        "supplierId": payload.get("suppliers", [{}])[0].get("id"),
                        "type": "quote_anomaly",
                        "severity": "high",
                        "title": "报价偏离风险",
                        "evidence": ["报价与预算偏离"],
                        "confidence": 0.88,
                    }
                ]
            },
            "evaluation.ai_scoring": {
                "scores": [
                    {"criterionName": "技术方案", "score": "82.00", "basis": "技术响应完整"},
                    {"criterionName": "商务报价", "score": "76.00", "basis": "报价处于合理区间"},
                ]
            },
            "evaluation.report_generate": {
                "reportTitle": "智慧园区评标报告",
                "sections": [
                    {"heading": "项目概况", "body": "本项目已完成资格、技术与商务评审。"},
                    {"heading": "评审结论", "body": "排名与风险项详见系统留痕。"},
                ],
            },
        }
        return JobRefSnapshot(
            id=new_id(),
            type=job_type,
            status="succeeded",
            progress_percent=100,
            created_at=datetime.now(UTC),
            current_step="completed",
            result={"status": "succeeded", "output": outputs[job_type]},
        )


@pytest.mark.asyncio
async def test_eager_results_populate_checks_scores_and_downloadable_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    container = build_m6_container(jobs=EagerResultJobs())
    actor = AuthPrincipal(
        user_id=DEMO_ADMIN_USER_ID,
        tenant_id=DEMO_TENANT_ID,
        name="演示管理员",
        role="admin",
    )

    material_job = await container.scoring.start_material_check(actor, DEMO_EVALUATION_ID)
    material_check = await container.scoring.latest_material_check(actor, DEMO_EVALUATION_ID)
    assert material_job["status"] == "succeeded"
    assert material_check["status"] == "succeeded"
    assert len(material_check["rows"]) == 12

    risk_job = await container.scoring.start_risk_check(actor, DEMO_EVALUATION_ID)
    risks = await container.scoring.list_risks(actor, DEMO_EVALUATION_ID)
    assert risk_job["status"] == "succeeded"
    assert any(item["title"] == "报价偏离风险" for item in risks)

    score_job = await container.scoring.start_ai_scoring(actor, DEMO_EVALUATION_ID)
    scores = await container.scoring.list_scores(actor, DEMO_EVALUATION_ID)
    assert score_job["status"] == "succeeded"
    assert scores
    assert any(item["aiBasis"] == "技术响应完整" for item in scores)

    evaluation = container.store.get_evaluation(DEMO_EVALUATION_ID, tenant_id=DEMO_TENANT_ID)
    evaluation.status = "completed"
    container.store.save_evaluation(evaluation)
    report_job = await container.scoring.start_report(actor, DEMO_EVALUATION_ID, ["docx", "pdf"])
    reports = await container.scoring.list_reports(actor, DEMO_EVALUATION_ID)
    assert report_job["status"] == "succeeded"
    assert {item["format"] for item in reports} == {"docx", "pdf"}

    stored = [container.store.get_report(item["id"]) for item in reports]
    pdf = next(item for item in stored if item.format == "pdf")
    docx = next(item for item in stored if item.format == "docx")
    assert pdf.content is not None and pdf.content.startswith(b"%PDF")
    assert docx.content is not None
    with zipfile.ZipFile(BytesIO(docx.content)) as archive:
        assert "word/document.xml" in archive.namelist()
