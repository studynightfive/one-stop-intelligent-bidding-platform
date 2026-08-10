"""HTTP contract mappers for platform jobs."""

from __future__ import annotations

from app.domains.jobs.models.job import Job


def job_to_data(job: Job) -> dict[str, object]:
    """Map a job to the locked camelCase ``JobRef`` shape."""
    data: dict[str, object] = {
        "id": str(job.id),
        "type": job.type.value,
        "status": job.status.value,
        "progressPercent": job.progress_percent,
        "createdAt": job.created_at,
    }
    if job.current_step is not None:
        data["currentStep"] = job.current_step
    if job.result is not None:
        data["result"] = job.result
    if job.error is not None:
        data["error"] = job.error
    return data
