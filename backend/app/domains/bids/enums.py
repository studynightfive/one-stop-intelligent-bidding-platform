"""M5 枚举常量（与 OpenAPI §8.2 / §7 一致）。"""

from __future__ import annotations

from typing import Literal

# 投标任务状态（§9.1）
BidTaskStatus = Literal[
    "draft",
    "parsing",
    "material_prep",
    "ai_review",
    "pending_output",
    "completed",
    "archived",
    "failed",
]
BID_TASK_STATUSES: tuple[str, ...] = (
    "draft",
    "parsing",
    "material_prep",
    "ai_review",
    "pending_output",
    "completed",
    "archived",
    "failed",
)

# 投标材料状态
BidMaterialStatus = Literal[
    "pending",
    "have",
    "missing",
    "template",
    "uploaded",
    "expiring",
    "rejected",
]
BID_MATERIAL_STATUSES: tuple[str, ...] = (
    "pending",
    "have",
    "missing",
    "template",
    "uploaded",
    "expiring",
    "rejected",
)

# 材料分类
BidMaterialCategory = Literal["qualification", "commercial", "technical"]
BID_MATERIAL_CATEGORIES: tuple[str, ...] = ("qualification", "commercial", "technical")

# 任务内分配角色
TaskAssignmentRole = Literal["owner", "collaborator", "reviewer"]
TASK_ASSIGNMENT_ROLES: tuple[str, ...] = ("owner", "collaborator", "reviewer")

# 文档类型
BidDocumentType = Literal["qualification", "commercial", "technical", "merged"]
BID_DOCUMENT_TYPES: tuple[str, ...] = ("qualification", "commercial", "technical", "merged")

# 文档模板模式
TemplateMode = Literal["tender_requirement", "standard"]
TEMPLATE_MODES: tuple[str, ...] = ("tender_requirement", "standard")

# 文档生成模式
DocumentGenMode = Literal["split", "merged"]
DOCUMENT_GEN_MODES: tuple[str, ...] = ("split", "merged")

# 文档生成 sections
DOCUMENT_SECTIONS: tuple[str, ...] = ("qualification", "commercial", "technical")

# 审核类型（CreateBidReviewRequest.types）
BidReviewType = Literal["signature", "price", "content", "consistency"]
BID_REVIEW_TYPES: tuple[str, ...] = ("signature", "price", "content", "consistency")

# 审核 Finding 严重度
BidReviewSeverity = Literal["info", "warning", "high", "critical"]
BID_REVIEW_SEVERITIES: tuple[str, ...] = ("info", "warning", "high", "critical")

# Finding 决定
BidReviewDecision = Literal["pending", "accepted", "ignored", "modified"]
BID_REVIEW_DECISIONS: tuple[str, ...] = ("pending", "accepted", "ignored", "modified")

# 材料来源
BidMaterialSource = Literal["qualification", "fragment", "upload", "template", "manual"]
BID_MATERIAL_SOURCES: tuple[str, ...] = (
    "qualification",
    "fragment",
    "upload",
    "template",
    "manual",
)

# Job 场景（M5 -> m5JobType）
JOB_TYPE_TENDER_PARSE = "bid.parse_tender"
JOB_TYPE_MATERIAL_MATCH = "bid.material_match"
JOB_TYPE_TEMPLATE_GENERATE = "bid.template_generate"
JOB_TYPE_REVIEW = "bid.review"
JOB_TYPE_DOCUMENT_GENERATE = "bid.document_generate"
JOB_TYPE_DOCUMENT_ROLLBACK = "bid.document_rollback"

# 看板列（七步）
BOARD_STATUSES: tuple[tuple[str, str], ...] = (
    ("draft", "项目立项"),
    ("parsing", "招标文件解析"),
    ("material_prep", "材料管理"),
    ("ai_review", "AI 审核"),
    ("pending_output", "文档生成"),
    ("completed", "评审留痕"),
    ("archived", "归档"),
)
