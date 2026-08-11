"""L0 独占的 SQLAlchemy 模型基类与中央注册点。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有领域 ORM 模型必须继承的唯一基类。"""


def _register_m4_models() -> None:
    """Explicitly register the shared platform models for Alembic."""
    from app.domains.audit.models.audit_event import AuditEvent
    from app.domains.auth.models.user import User
    from app.domains.files.models.file import File, FileUploadSession
    from app.domains.jobs.models.job import Job
    from app.domains.notifications.models.notification import Notification

    # Keep registration discoverable without package scanning or hidden imports.
    _ = (AuditEvent, File, FileUploadSession, Job, Notification, User)


def _register_m6_models() -> None:
    """Explicitly register the evaluation and supplier portal models."""
    from app.domains.evaluations.models import (
        EvaluationIdempotencyModel,
        EvaluationMaterialModel,
        EvaluationReportModel,
        EvaluationReviewerModel,
        EvaluationSupplierModel,
        EvaluationTaskModel,
        MaterialCheckModel,
        PortalActivityModel,
        PortalDraftModel,
        PortalSessionModel,
        PriceRoundModel,
        QuoteSubmissionModel,
        RiskFindingModel,
        ScoreItemModel,
        ScoringCriterionModel,
        SupplementNoticeModel,
        SupplierInviteModel,
        SupplierSubmissionModel,
    )

    _ = (
        EvaluationIdempotencyModel,
        EvaluationMaterialModel,
        EvaluationReportModel,
        EvaluationReviewerModel,
        EvaluationSupplierModel,
        EvaluationTaskModel,
        MaterialCheckModel,
        PortalActivityModel,
        PortalDraftModel,
        PortalSessionModel,
        PriceRoundModel,
        QuoteSubmissionModel,
        RiskFindingModel,
        ScoreItemModel,
        ScoringCriterionModel,
        SupplementNoticeModel,
        SupplierInviteModel,
        SupplierSubmissionModel,
    )


def _register_m5_models() -> None:
    """Explicitly register bid, document, qualification and fragment models."""

    from app.domains.bids.models import (
        BidIdempotencyModel,
        BidJobBindingModel,
        BidMaterialModel,
        BidReviewFindingModel,
        BidReviewReportModel,
        BidTaskAssignmentModel,
        BidTaskModel,
        BidTenderRequirementModel,
    )
    from app.domains.documents.models import BidDocumentModel, BidDocumentVersionModel
    from app.domains.fragments.models import FragmentModel, FragmentReferenceModel, FragmentVersionModel
    from app.domains.qualifications.models import (
        QualificationImportJobModel,
        QualificationModel,
        QualificationVersionModel,
    )

    _ = (
        BidDocumentModel,
        BidDocumentVersionModel,
        BidIdempotencyModel,
        BidJobBindingModel,
        BidMaterialModel,
        BidReviewFindingModel,
        BidReviewReportModel,
        BidTaskAssignmentModel,
        BidTaskModel,
        BidTenderRequirementModel,
        FragmentModel,
        FragmentReferenceModel,
        FragmentVersionModel,
        QualificationImportJobModel,
        QualificationModel,
        QualificationVersionModel,
    )


def register_models() -> None:
    """Load every merged domain model after the central Base is initialized."""
    _register_m4_models()
    _register_m5_models()
    _register_m6_models()
