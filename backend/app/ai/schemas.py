"""AI 层数据契约。

参考 OpenAPI ``JobRef`` / ``JobError`` / ``Scene`` 等已锁定的枚举，
本模块使用 ``strEnum`` 形式确保序列化与契约一致。

注意：
- 本模块不依赖任何 M5/M6 业务表或 ORM；
- 序列化字段名沿用 ``camelCase``，与前后端生成类型一致；
- ``PromptVersion`` 字段严格匹配 PROJECT_MASTER_PROMPT.md V3.1 § 8.7 提示词版本管理要求。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Celery 任务对外可见状态。"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderStatus(str, Enum):
    """Provider 路由级别状态。"""

    PRIMARY = "primary"
    FALLBACK = "fallback"
    OFFLINE = "offline"


class Scene(str, Enum):
    """AI 调用业务场景（OpenAPI Scene 枚举）。"""

    TENDER_PARSE = "tender_parse"
    REQUIREMENT_EXTRACT = "requirement_extract"
    MATERIAL_MATCH = "material_match"
    BID_GENERATE = "bid_generate"
    BID_REVIEW = "bid_review"
    EVALUATION_CHECK = "evaluation_check"
    RISK_CHECK = "risk_check"
    EVALUATION_SCORE = "evaluation_score"
    REPORT_GENERATE = "report_generate"


@dataclass(frozen=True)
class TokenUsage:
    """Provider 返回的 Token 用量。"""

    prompt: int = 0
    completion: int = 0
    total: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"prompt": self.prompt, "completion": self.completion, "total": self.total}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> TokenUsage:
        if not payload:
            return cls()
        return cls(
            prompt=int(payload.get("prompt", 0) or 0),
            completion=int(payload.get("completion", 0) or 0),
            total=int(payload.get("total", 0) or 0),
        )

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt=self.prompt + other.prompt,
            completion=self.completion + other.completion,
            total=self.total + other.total,
        )


@dataclass(frozen=True)
class PromptVersion:
    """提示词版本快照（PROJECT_MASTER_PROMPT.md § 8.7）。"""

    name: str
    version: str
    provider: str
    model: str
    input_hash: str
    output_hash: str
    token_usage: TokenUsage
    latency_ms: int
    status: str  # success / fallback_used / offline_used / partial / failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "model": self.model,
            "inputHash": self.input_hash,
            "outputHash": self.output_hash,
            "tokenUsage": self.token_usage.to_dict(),
            "latencyMs": self.latency_ms,
            "status": self.status,
        }


@dataclass(frozen=True)
class JobSpec:
    """Worker 任务入参（业务无关）。"""

    job_id: str
    scene: str
    aggregate_id: str
    aggregate_type: str  # bidTask | evaluation | supplier | job | notification
    prompt_name: str
    prompt_version: str
    input_payload: dict[str, Any]
    tenant_id: str | None = None
    user_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class ProviderOutput:
    """Provider 调用返回（业务无关）。"""

    text: str
    structured: dict[str, Any] | None
    prompt_version: PromptVersion
    provider_status: ProviderStatus


@dataclass
class JobResult:
    """Worker 任务返回（业务无关）。M5/M6 service 负责落库。"""

    job_id: str
    status: JobStatus
    provider_used: ProviderStatus
    output: dict[str, Any]
    prompt_versions: list[PromptVersion]
    token_usage: TokenUsage
    error_code: str | None = None
    error_message: str | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "status": self.status.value,
            "providerUsed": self.provider_used.value,
            "output": self.output,
            "promptVersions": [pv.to_dict() for pv in self.prompt_versions],
            "tokenUsage": self.token_usage.to_dict(),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "completedAt": self.completed_at.isoformat(),
        }


def hash_payload(payload: Mapping[str, Any] | str | bytes) -> str:
    """对输入负载计算 SHA-256。``str``/``bytes`` 直接哈希；``Mapping`` 序列化后哈希。"""

    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        raw = payload
    else:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
