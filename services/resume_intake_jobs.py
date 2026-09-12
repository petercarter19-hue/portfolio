"""Durable processing-job ledger for MVP1 increment C.

An explicit Add creates immutable submissions, owner-scoped sources and one
durable job per unit of provider work. Each job carries a lifecycle fence:
the owning source version, the submission version, the entrance policy
version and the owner's monotonic lifecycle epoch. A worker may only write a
result while that fence is still exactly current, so a late or replayed job
cannot resurrect purged input, overwrite a newer correction, or write after a
source was deleted.

The ledger is pure state over a snapshot dict, so the in-memory repository and
a future SQL transaction share the same rules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


JOB_KINDS = frozenset({"document_parse", "voice_transcription", "text_interpretation"})
JOB_STATES = frozenset({"queued", "leased", "completed", "failed", "refused", "stale"})
JOB_RESULTS = frozenset({"saved", "unresolved", "failed", "skipped"})


class IntakeJobError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class StaleJobError(IntakeJobError):
    """The job's fence moved. The result must not be written anywhere."""

    def __init__(self):
        super().__init__("stale_job")


@dataclass(frozen=True)
class JobFence:
    source_key: str
    source_version: int
    submission_key: str
    submission_version: int
    policy_version: int
    lifecycle_epoch: int

    def as_dict(self) -> dict:
        return asdict(self)


def new_job_key() -> str:
    return str(uuid4())


def _utc(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def fence_is_current(snapshot: dict, fence: dict) -> bool:
    """True only while every version in the fence still matches live state."""

    source = snapshot.get("sources", {}).get(fence.get("source_key"))
    if source is None or source.get("state") != "active":
        return False
    if int(source.get("version") or 0) != int(fence.get("source_version") or 0):
        return False
    submission = snapshot.get("submissions", {}).get(fence.get("submission_key"))
    if submission is None or submission.get("state") != "active":
        return False
    if int(submission.get("version") or 0) != int(fence.get("submission_version") or 0):
        return False
    if int(snapshot.get("policy_version") or 0) != int(fence.get("policy_version") or 0):
        return False
    if int(snapshot.get("lifecycle_epoch") or 0) != int(fence.get("lifecycle_epoch") or 0):
        return False
    return True


def enqueue(snapshot: dict, fence: JobFence, kind: str, *, now: datetime | None = None) -> dict:
    if kind not in JOB_KINDS:
        raise IntakeJobError("unknown_job_kind")
    moment = _utc(now)
    job = {
        "job_key": new_job_key(),
        "kind": kind,
        "state": "queued",
        "fence": fence.as_dict(),
        "lease_id": None,
        "attempts": 0,
        "result": None,
        "outcome": None,
        "created_at": moment.isoformat(),
        "updated_at": moment.isoformat(),
    }
    snapshot.setdefault("jobs", {})[job["job_key"]] = job
    return job


def lease(snapshot: dict, job_key: str, *, now: datetime | None = None) -> dict:
    """Lease one queued job. Refuses (and fences) a stale job."""

    job = snapshot.get("jobs", {}).get(job_key)
    if job is None:
        raise IntakeJobError("not_found")
    if job["state"] not in {"queued", "leased"}:
        raise IntakeJobError("not_leaseable")
    if not fence_is_current(snapshot, job["fence"]):
        job["state"] = "stale"
        job["updated_at"] = _utc(now).isoformat()
        raise StaleJobError()
    job["state"] = "leased"
    job["lease_id"] = str(uuid4())
    job["attempts"] = int(job.get("attempts") or 0) + 1
    job["updated_at"] = _utc(now).isoformat()
    return job


def complete(
    snapshot: dict,
    job_key: str,
    lease_id: str,
    *,
    result: str,
    outcome: str | None,
    now: datetime | None = None,
) -> dict:
    """Commit one typed job result, or refuse because the fence moved."""

    if result not in JOB_RESULTS:
        raise IntakeJobError("unknown_result")
    job = snapshot.get("jobs", {}).get(job_key)
    if job is None:
        raise IntakeJobError("not_found")
    if job.get("lease_id") != lease_id:
        raise IntakeJobError("lease_lost")
    if not fence_is_current(snapshot, job["fence"]):
        job["state"] = "stale"
        job["lease_id"] = None
        job["updated_at"] = _utc(now).isoformat()
        raise StaleJobError()
    job["state"] = "completed" if result != "failed" else "failed"
    job["result"] = result
    job["outcome"] = outcome
    job["lease_id"] = None
    job["updated_at"] = _utc(now).isoformat()
    return job


def fail(snapshot: dict, job_key: str, lease_id: str, code: str, *, now: datetime | None = None) -> dict:
    job = snapshot.get("jobs", {}).get(job_key)
    if job is None:
        raise IntakeJobError("not_found")
    if job.get("lease_id") != lease_id:
        raise IntakeJobError("lease_lost")
    job["state"] = "failed"
    job["result"] = "failed"
    job["outcome"] = code
    job["lease_id"] = None
    job["updated_at"] = _utc(now).isoformat()
    return job


def invalidate_for_source(snapshot: dict, source_key: str, *, now: datetime | None = None) -> int:
    """Mark every outstanding job of one source stale. Returns the count."""

    moment = _utc(now)
    affected = 0
    for job in snapshot.get("jobs", {}).values():
        if job["fence"]["source_key"] != source_key:
            continue
        if job["state"] in {"queued", "leased"}:
            job["state"] = "stale"
            job["lease_id"] = None
            job["updated_at"] = moment.isoformat()
            affected += 1
    return affected


def present(job: dict) -> dict:
    return {
        "job_key": job["job_key"],
        "kind": job["kind"],
        "state": job["state"],
        "result": job.get("result"),
        "outcome": job.get("outcome"),
        "attempts": job.get("attempts", 0),
        "created_at": job.get("created_at"),
    }
