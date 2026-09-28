"""Payload-free operational diagnostics for the Ask Pete product adapter."""

from dataclasses import dataclass
from contextlib import contextmanager
import json
import logging
import math
import re
from threading import RLock
from time import monotonic

from services.ai_foundation import AITrace
from services.ai_foundation.errors import AnswerContractError, GroundingValidationError, ExecutionLimitError


_LOGGER = logging.getLogger("peerslate.ask_pete.operations")
_CONFIG_LOCK = RLock()
_PHASES = {"sink_ready", "trace", "stage", "sources", "generation", "support",
           "grounding_quality", "support_verdict", "currentness", "serialization", "request", "route"}
_STAGES = {"request", "sources", "credential", "transport", "response_validation",
           "grounding_quality", "support_verdict", "currentness", "serialization", "route"}
_OUTCOMES = {"ready", "started", "completed", "failed", "degraded", "unavailable",
             "supported", "partially_supported", "not_established", "ambiguous", "refused", "invalid_request"}
_REASONS = {"credential_unavailable", "transport_unavailable", "http_non_success",
            "response_validation_unknown", "completion_incomplete", "answer_contract",
            "grounding_invalid", "execution_limit", "support_rejected", "source_unavailable",
            "currentness_failed", "serialization_failed", "capacity_occupied", "deadline_exceeded",
            "request_failed", "invalid_request", "unexpected_failure", "provider_unavailable"}
_NUMBERS = {"source_count", "source_bytes", "claim_count", "citation_count", "duration_ms",
            "provider_calls", "input_tokens", "output_tokens", "cached_input_tokens",
            "cache_write_input_tokens", "reasoning_tokens", "estimated_micro_usd",
            "deadline_seconds", "quality_resamples", "corrective_retries"}
_ENUMS = {"phase": _PHASES, "stage": _STAGES, "last_stage": _STAGES,
          "outcome": _OUTCOMES, "reason": _REASONS, "operation": {"generation", "support"},
          "completion_status": {"completed", "incomplete", "failed", "cancelled", "queued", "in_progress", "unknown"}}


def safe_execution_event(event):
    """No arbitrary values or nested provider/user objects cross the log boundary."""
    if type(event) is not dict:
        return {}
    clean = {}
    for key, values in _ENUMS.items():
        value = event.get(key)
        if type(value) is str and value in values:
            clean[key] = value
    request_id = event.get("request_id")
    if type(request_id) is str and len(request_id) == 41 and re.fullmatch(r"ask-pete-[0-9a-f]{32}", request_id):
        clean["request_id"] = request_id
    for key in _NUMBERS:
        value = event.get(key)
        if type(value) in (int, float) and 0 <= value <= 10**9 and math.isfinite(value):
            clean[key] = value
    for key in ("usage_available", "provider_called", "late"):
        if type(event.get(key)) is bool:
            clean[key] = event[key]
    status = event.get("http_status")
    if type(status) is int and 100 <= status <= 599:
        clean["http_status"] = status
    return clean


def configure_execution_logging():
    """Enable only this payload-free sink, once per process; never the SDK/root."""
    with _CONFIG_LOCK:
        _LOGGER.setLevel(logging.INFO)
        _LOGGER.disabled = False
        _LOGGER.propagate = False
        if not any(getattr(handler, "_ask_pete_safe_sink", False) for handler in _LOGGER.handlers):
            handler = logging.StreamHandler()
            handler._ask_pete_safe_sink = True
            handler.setFormatter(logging.Formatter("Ask Pete execution %(message)s"))
            _LOGGER.addHandler(handler)
            record_execution({"phase": "sink_ready", "outcome": "ready"})


class _SafeLogEvent:
    """Format only safe fields when the stream handler actually writes."""
    def __init__(self, event):
        self.event = event

    def __str__(self):
        # StreamHandler formats under its own output lock. If a worker waits
        # before reaching that lock, request close can still mark its event
        # late; if it holds the lock, its record writes before terminal.
        return json.dumps(safe_execution_event(self.event), sort_keys=True, allow_nan=False)


def record_execution(event):
    try:
        if safe_execution_event(event).get("phase"):
            _LOGGER.info("%s", _SafeLogEvent(event))
    except Exception:
        pass  # Telemetry cannot change an answer or expose an exception payload.


def emit_safely(sink, event):
    if sink:
        try:
            sink(event)
        except Exception:
            pass


def failure_reason(error, default):
    # Typed local deadline reasons are checked without inspecting error text.
    from .deadline import AskPeteDeadlineError
    if isinstance(error, AskPeteDeadlineError):
        return error.reason
    if isinstance(error, GroundingValidationError):
        return "grounding_invalid"
    if isinstance(error, AnswerContractError):
        return "answer_contract"
    if isinstance(error, ExecutionLimitError):
        return "execution_limit"
    return default


@contextmanager
def observed_phase(sink, request_id, phase, reason):
    started = monotonic()
    emit_safely(sink, {"request_id": request_id, "phase": "stage", "stage": phase, "outcome": "started"})
    event = {"request_id": request_id, "phase": phase, "stage": phase, "outcome": "completed"}
    try:
        yield event
    except Exception as error:
        event.update(outcome="failed", reason=failure_reason(error, reason))
        raise
    finally:
        event["duration_ms"] = round((monotonic() - started) * 1000)
        emit_safely(sink, event)


@dataclass(frozen=True)
class AskPeteDiagnostic:
    request_id: str
    manifest_id: str
    purpose: str
    context_applied: bool
    source_count: int
    source_character_count: int
    outcome: str
    answer_state: str | None
    claim_count: int
    citation_count: int
    provider_called: bool | None
    duration_ms: int
    error_category: str | None

    @classmethod
    def from_trace(
        cls,
        trace: AITrace,
        *,
        manifest_id: str,
        context_applied: bool,
    ) -> "AskPeteDiagnostic":
        return cls(
            request_id=trace.request_id,
            manifest_id=manifest_id,
            purpose=trace.purpose,
            context_applied=context_applied,
            source_count=trace.source_count,
            source_character_count=trace.source_character_count,
            outcome=trace.outcome,
            answer_state=trace.answer_state,
            claim_count=trace.claim_count,
            citation_count=trace.citation_count,
            provider_called=trace.provider_called,
            duration_ms=trace.duration_ms,
            error_category=trace.error_category,
        )
