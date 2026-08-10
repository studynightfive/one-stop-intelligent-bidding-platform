"""M5 dependency assembly; L0 only needs to mount the exported container and router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domains.bids.m4_adapters import M5BidTaskSnapshotAdapter
from app.domains.bids.ports import (
    AuditServicePort,
    FileServicePort,
    JobDispatcherPort,
    NotificationServicePort,
    RecordingPorts,
)
from app.domains.bids.service import BidService
from app.domains.bids.store import BidStore
from app.domains.documents.repository import DocumentStore
from app.domains.documents.service import DocumentService
from app.domains.fragments.ports import SemanticSearchPort
from app.domains.fragments.service import FragmentService
from app.domains.fragments.store import FragmentStore
from app.domains.qualifications.service import QualificationService
from app.domains.qualifications.store import QualificationStore


@dataclass
class M5BidsContainer:
    store: BidStore
    document_store: DocumentStore
    qualification_store: QualificationStore
    fragment_store: FragmentStore
    bids: BidService
    qualifications: QualificationService
    fragments: FragmentService
    snapshot: M5BidTaskSnapshotAdapter
    ports: RecordingPorts | None = None


def build_m5_bids_container(
    *,
    store: BidStore | None = None,
    document_store: DocumentStore | None = None,
    qualification_store: QualificationStore | None = None,
    fragment_store: FragmentStore | None = None,
    files: FileServicePort | None = None,
    jobs: JobDispatcherPort | None = None,
    notifications: NotificationServicePort | None = None,
    audit: AuditServicePort | None = None,
    semantic_search: SemanticSearchPort | None = None,
) -> M5BidsContainer:
    """Build the in-process M5 container used by focused tests and local demos."""
    recording = RecordingPorts()
    bid_store = store or BidStore()
    docs_store = document_store or DocumentStore()
    qualifications_store = qualification_store or QualificationStore()
    fragments_store = fragment_store or FragmentStore()
    file_port = files or recording
    job_port = jobs or recording
    notification_port = notifications or recording
    audit_port = audit or recording

    documents = DocumentService(docs_store)
    bids = BidService(
        bid_store,
        files=file_port,
        jobs=job_port,
        notifications=notification_port,
        audit=audit_port,
        documents=documents,
    )
    qualifications = QualificationService(
        qualifications_store,
        files=file_port,
        jobs=job_port,
        audit=audit_port,
        notifications=notification_port,
    )
    fragments = FragmentService(
        fragments_store,
        bid_store=bid_store,
        files=file_port,
        audit=audit_port,
        semantic_search=semantic_search,
    )
    return M5BidsContainer(
        store=bid_store,
        document_store=docs_store,
        qualification_store=qualifications_store,
        fragment_store=fragments_store,
        bids=bids,
        qualifications=qualifications,
        fragments=fragments,
        snapshot=M5BidTaskSnapshotAdapter(bid_store),
        ports=recording,
    )


def build_m5_bids_container_with_m4(
    db: Any,
    *,
    store: BidStore,
    document_store: DocumentStore,
    qualification_store: QualificationStore,
    fragment_store: FragmentStore,
    files: FileServicePort,
    semantic_search: SemanticSearchPort | None = None,
) -> M5BidsContainer:
    """Build M5 against M4 services using L0-owned stores and authorized files."""
    from app.domains.bids.m4_adapters import build_m4_ports

    jobs, notifications, audit, file_port = build_m4_ports(db, files=files)
    container = build_m5_bids_container(
        store=store,
        document_store=document_store,
        qualification_store=qualification_store,
        fragment_store=fragment_store,
        files=file_port,
        jobs=jobs,
        notifications=notifications,
        audit=audit,
        semantic_search=semantic_search,
    )
    container.ports = None
    return container
