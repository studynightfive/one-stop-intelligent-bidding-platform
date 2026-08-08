"""M6 依赖装配：默认 RecordingPorts；集成环境注入 M4 适配器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domains.evaluations.ports import (
    AuditServicePort,
    BidTaskSnapshotPort,
    FileServicePort,
    JobDispatcherPort,
    NotificationServicePort,
    RecordingPorts,
)
from app.domains.evaluations.service import EvaluationService
from app.domains.evaluations.store import EvaluationStore
from app.domains.portal.service import PortalService
from app.domains.pricing.service import PricingService
from app.domains.scoring.service import ScoringService


@dataclass
class M6Container:
    store: EvaluationStore
    evaluations: EvaluationService
    portal: PortalService
    pricing: PricingService
    scoring: ScoringService
    ports: RecordingPorts | None = None


def build_m6_container(
    *,
    store: EvaluationStore | None = None,
    bid_snapshot: BidTaskSnapshotPort | None = None,
    files: FileServicePort | None = None,
    jobs: JobDispatcherPort | None = None,
    notifications: NotificationServicePort | None = None,
    audit: AuditServicePort | None = None,
    portal_base_url: str = "http://127.0.0.1:3210/evaluation/portal",
) -> M6Container:
    """单元测试 / 无 M4 时：不传端口则使用 RecordingPorts。"""
    ports = RecordingPorts()
    store = store or EvaluationStore()
    bid_snapshot = bid_snapshot or ports
    files = files or ports
    jobs = jobs or ports
    notifications = notifications or ports
    audit = audit or ports
    evaluations = EvaluationService(
        store,
        bid_snapshot=bid_snapshot,
        jobs=jobs,
        notifications=notifications,
        audit=audit,
        portal_base_url=portal_base_url,
    )
    portal = PortalService(store, files=files, audit=audit)
    pricing = PricingService(store, audit=audit)
    scoring = ScoringService(store, jobs=jobs, audit=audit, files=files)
    return M6Container(
        store=store,
        evaluations=evaluations,
        portal=portal,
        pricing=pricing,
        scoring=scoring,
        ports=ports if jobs is ports else None,
    )


def build_m6_container_with_m4(
    db: Any,
    *,
    bid_snapshot: BidTaskSnapshotPort,
    store: EvaluationStore | None = None,
    portal_base_url: str = "http://127.0.0.1:3210/evaluation/portal",
) -> M6Container:
    """L0/集成层：在 M4 已合入后使用。

    示例::

        from app.domains.evaluations.container import build_m6_container_with_m4
        app.state.m6 = build_m6_container_with_m4(db, bid_snapshot=m5_port)
    """
    from app.domains.evaluations.m4_adapters import build_m4_ports

    jobs, notifications, audit, files = build_m4_ports(db)
    return build_m6_container(
        store=store,
        bid_snapshot=bid_snapshot,
        files=files,
        jobs=jobs,
        notifications=notifications,
        audit=audit,
        portal_base_url=portal_base_url,
    )
