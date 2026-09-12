"""Proposal bindings for MVP1 increment C.

Extraction, inferred wording, ambiguous parent/entity matching, contradictions
and added details to existing facts are *proposals*, never canonical truth.
Each proposal carries an exact source span and source version, a typed intake
binding, the digest of the command that produced it, the content/access
versions of the record it would change, and a lifecycle fence.

Two integrity rules live here:

* Member approval is required before a proposal becomes canonical, and a change
  to an *existing* fact is routed through the Resume draft overlay against the
  versions **captured when the proposal was made** -- not a fresh re-read that
  would silently accept against a record the member has since edited.
* ``accept`` and ``edit`` enforce the same binding and member-wording checks.
  Only ``reject`` may act on a stale proposal, because discarding never writes.

Field intent travels with the proposal: ``provided_fields`` are the keys the
member actually supplied and ``explicit_clears`` are the keys the member
deliberately cleared. Unspecified fields stay absent so an overlay merge cannot
blank values the member never touched.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


PROPOSAL_STATES = frozenset({"pending", "accepted", "rejected", "invalidated"})
PROPOSAL_KINDS = frozenset(
    {
        "new_fact",
        "change_existing",
        "ambiguous_match",
        "additional_detail",
        "contradiction",
        "inferred_wording",
    }
)
# Only these are unambiguous enough to save without a second ceremonial step.
UNAMBIGUOUS_KINDS = frozenset({"new_fact"})
MEMBER_DECISIONS = frozenset({"accept", "reject", "edit"})
DECISIONS_REQUIRING_BINDING = frozenset({"accept", "edit"})

REDACTED_VALUE = {"redacted": True}


class ProposalError(RuntimeError):
    def __init__(self, code: str, *, proposed=None, conflicts=None):
        self.code = code
        self.proposed = proposed
        self.conflicts = list(conflicts or [])
        super().__init__(code)


def _utc(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class ProposalSpec:
    source_key: str
    source_version: int
    submission_key: str
    submission_version: int
    kind: str
    record_type: str
    quote: str
    span_start: int
    span_end: int
    proposed_values: dict
    target_key: str | None = None
    target_content_token: str | None = None
    target_access_revision: int | None = None
    provided_fields: tuple = ()
    explicit_clears: tuple = ()
    confidence: str = "certain"
    command_digest: str | None = None
    lifecycle_epoch: int = 0
    policy_version: int = 1

    @property
    def requires_member_wording(self) -> bool:
        return self.kind not in UNAMBIGUOUS_KINDS or self.confidence != "certain"


def new_proposal_key() -> str:
    return str(uuid4())


def create(snapshot: dict, spec: ProposalSpec, *, now: datetime | None = None) -> dict:
    if spec.kind not in PROPOSAL_KINDS:
        raise ProposalError("unknown_proposal_kind")
    if not (spec.quote or "").strip():
        raise ProposalError("proposal_quote_required")
    if spec.span_end < spec.span_start:
        raise ProposalError("invalid_span")
    if set(spec.explicit_clears) & set(spec.provided_fields):
        raise ProposalError("conflicting_field_intent")
    moment = _utc(now)
    proposal = {
        "proposal_key": new_proposal_key(),
        "state": "pending",
        "kind": spec.kind,
        "record_type": spec.record_type,
        "target_key": spec.target_key,
        "target_content_token": spec.target_content_token,
        "target_access_revision": spec.target_access_revision,
        "quote": spec.quote,
        "span_start": spec.span_start,
        "span_end": spec.span_end,
        "proposed_values": dict(spec.proposed_values or {}),
        "provided_fields": list(spec.provided_fields),
        "explicit_clears": list(spec.explicit_clears),
        "confirmed_values": None,
        "requires_member_wording": spec.requires_member_wording,
        "confidence": spec.confidence,
        "command_digest": spec.command_digest,
        "binding": {
            "source_key": spec.source_key,
            "source_version": spec.source_version,
            "submission_key": spec.submission_key,
            "submission_version": spec.submission_version,
            "lifecycle_epoch": spec.lifecycle_epoch,
            "policy_version": spec.policy_version,
        },
        # Retained historical provenance survives source purge; it is never
        # permission to resurrect the purged source text.
        "provenance": {
            "source_key": spec.source_key,
            "source_version": spec.source_version,
            "span_start": spec.span_start,
            "span_end": spec.span_end,
        },
        "decision": None,
        "decided_at": None,
        "created_at": moment.isoformat(),
    }
    snapshot.setdefault("proposals", {})[proposal["proposal_key"]] = proposal
    return proposal


def present(proposal: dict) -> dict:
    return {
        "proposal_key": proposal["proposal_key"],
        "state": proposal["state"],
        "kind": proposal["kind"],
        "record_type": proposal["record_type"],
        "target_key": proposal.get("target_key"),
        "quote": proposal.get("quote"),
        "span": [proposal.get("span_start"), proposal.get("span_end")],
        "proposed_values": dict(proposal.get("proposed_values") or {}),
        "provided_fields": list(proposal.get("provided_fields") or []),
        "explicit_clears": list(proposal.get("explicit_clears") or []),
        "confirmed_values": proposal.get("confirmed_values"),
        "requires_member_wording": proposal.get("requires_member_wording", True),
        "confidence": proposal.get("confidence"),
        "provenance": dict(proposal.get("provenance") or {}),
        "decision": proposal.get("decision"),
        "source_purged": bool(proposal.get("source_purged")),
        "created_at": proposal.get("created_at"),
    }


def binding_is_current(snapshot: dict, proposal: dict) -> bool:
    binding = proposal.get("binding") or {}
    source = snapshot.get("sources", {}).get(binding.get("source_key"))
    if source is None or source.get("state") != "active":
        return False
    if int(source.get("version") or 0) != int(binding.get("source_version") or 0):
        return False
    submission = snapshot.get("submissions", {}).get(binding.get("submission_key"))
    if submission is None or submission.get("state") != "active":
        return False
    if int(submission.get("version") or 0) != int(binding.get("submission_version") or 0):
        return False
    if int(snapshot.get("lifecycle_epoch") or 0) != int(binding.get("lifecycle_epoch") or 0):
        return False
    return True


def decide(
    snapshot: dict,
    proposal_key: str,
    *,
    decision: str,
    confirmed_values: dict | None = None,
    request_digest: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Record one member decision. Raises :class:`ProposalError` to conflict."""

    if decision not in MEMBER_DECISIONS:
        raise ProposalError("unknown_decision")
    proposal = snapshot.get("proposals", {}).get(proposal_key)
    if proposal is None:
        raise ProposalError("not_found")
    if proposal["state"] == "invalidated":
        raise ProposalError(
            "changed",
            proposed=proposal.get("proposed_values"),
            conflicts=[{"proposal_key": proposal_key, "reason": "binding_invalidated"}],
        )
    if proposal["state"] != "pending":
        raise ProposalError("already_decided", proposed=proposal.get("proposed_values"))
    # ``accept`` and ``edit`` both write canonical truth, so both must prove the
    # binding is still current. Only ``reject`` may act on a stale proposal.
    if decision in DECISIONS_REQUIRING_BINDING:
        if not binding_is_current(snapshot, proposal):
            proposal["state"] = "invalidated"
            raise ProposalError(
                "changed",
                proposed=proposal.get("proposed_values"),
                conflicts=[{"proposal_key": proposal_key, "reason": "binding_stale"}],
            )
        if decision == "accept" and proposal.get("requires_member_wording") and not confirmed_values:
            raise ProposalError(
                "reconciliation_required",
                proposed=proposal.get("proposed_values"),
                conflicts=[{"proposal_key": proposal_key, "reason": "member_wording_required"}],
            )
    moment = _utc(now)
    proposal["state"] = "accepted" if decision in {"accept", "edit"} else "rejected"
    proposal["decision"] = decision
    proposal["confirmed_values"] = dict(confirmed_values or proposal.get("proposed_values") or {})
    proposal["request_digest"] = request_digest
    proposal["decided_at"] = moment.isoformat()
    return proposal


def invalidate(snapshot: dict, proposal_key: str, *, now: datetime | None = None) -> dict | None:
    proposal = snapshot.get("proposals", {}).get(proposal_key)
    if proposal is None or proposal["state"] != "pending":
        return None
    proposal["state"] = "invalidated"
    proposal["decided_at"] = _utc(now).isoformat()
    return proposal


def invalidate_for_target(snapshot: dict, target_key: str, *, now: datetime | None = None) -> int:
    """Manual edit / discard invalidates pending references to a record."""

    affected = 0
    for proposal in snapshot.get("proposals", {}).values():
        if proposal["state"] == "pending" and proposal.get("target_key") == target_key:
            invalidate(snapshot, proposal["proposal_key"], now=now)
            affected += 1
    return affected


def invalidate_for_source(snapshot: dict, source_key: str, *, now: datetime | None = None) -> int:
    """Mark pending proposals of one source; provenance is retained."""

    affected = 0
    for proposal in snapshot.get("proposals", {}).values():
        if (proposal.get("binding") or {}).get("source_key") != source_key:
            continue
        proposal["source_purged"] = True
        if proposal["state"] == "pending":
            invalidate(snapshot, proposal["proposal_key"], now=now)
            affected += 1
    return affected


def redact_source_text(snapshot: dict, source_key: str) -> int:
    """Remove purged source text from every retained copy in the snapshot.

    Retained provenance (keys, versions, spans) survives; the member's words do
    not. This covers the proposal row, its copy inside stored receipts, and the
    proposal text embedded in per-item results.
    """

    redacted = 0
    for source in snapshot.get("sources", {}).values():
        if source.get("source_key") != source_key:
            continue
        # Structured values are member words held outside source_text.
        source["structured_values"] = None
    for proposal in snapshot.get("proposals", {}).values():
        if (proposal.get("binding") or {}).get("source_key") != source_key:
            continue
        proposal["quote"] = None
        proposal["proposed_values"] = dict(REDACTED_VALUE)
        if proposal.get("confirmed_values") is not None:
            proposal["confirmed_values"] = dict(REDACTED_VALUE)
        redacted += 1
    for receipt in snapshot.get("receipts", {}).values():
        result = (receipt or {}).get("result")
        if not isinstance(result, dict):
            continue
        submission = result.get("submission") or {}
        touch = source_key in (submission.get("source_keys") or [])
        # A pre-Add transcription receipt has no submission; its own source_key
        # identifies it, and the member's words must be dropped there too.
        if result.get("source_key") == source_key:
            result.pop("transcript", None)
            nested = result.get("receipt")
            if isinstance(nested, dict):
                nested.pop("transcript", None)
            touch = True
        if not touch:
            continue
        for proposal_view in result.get("proposals") or []:
            if (proposal_view.get("provenance") or {}).get("source_key") == source_key:
                proposal_view["quote"] = None
                proposal_view["proposed_values"] = dict(REDACTED_VALUE)
        for row in result.get("results") or []:
            if row.get("source_key") == source_key:
                row["document"] = None
                row.pop("message", None)
    return redacted


def spec_as_dict(spec: ProposalSpec) -> dict:
    return asdict(spec)
