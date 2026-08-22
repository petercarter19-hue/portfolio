"""Content-free server_call telemetry for Interview AI (telemetry-contract@1).

One row per attempt, assembled at response time, validated against the
frozen contract before any append, and written through the dedicated
append procedure in one bounded attempt. A telemetry failure never alters
the member response, status, or provider-call count. Raw member text,
model text, URLs, request ids, and stringified exceptions are prohibited
values everywhere here — the sentinel validation enforces shape, and the
assembly never receives content in the first place.
"""

import json
import logging
import time
import uuid
from contextlib import contextmanager

import anthropic

from services.database_service import DatabaseServiceError, database_service
from services.interview_ai.constants import (
    COMPOSITIONS,
    COST_MICROUSD_RANGE,
    DURATION_MS_RANGE,
    EVENT_KINDS,
    EXCEPTION_ATTR_SPEC,
    EXCEPTION_CLASSES,
    FAILURE_REASONS,
    FAILURE_STATES,
    HTTP_STATUS_RANGE,
    OUTCOMES,
    REPLY_CHARS_RANGE,
    RESERVED_FAILURE_REASONS,
    RESERVED_OUTCOMES,
    RETRY_ORDINAL_RANGE,
    ROW_STATE_MATRIX,
    SOURCE_CLASSES,
    SOURCE_CLASS_COUNT_CAP,
    STOP_REASONS,
    TOKEN_RANGE,
    VALIDATION_EXCEPTION_CLASSES,
    VALIDATION_RESULTS,
)
from services.interview_ai.identity import is_full_sha256
from services.interview_ai.pricing import price_usage

logger = logging.getLogger(__name__)

DURATION_FIELDS = (
    "dur_receive_ms",
    "dur_retrieval_ms",
    "dur_manifest_ms",
    "dur_provider_ms",
    "dur_validate_ms",
    "dur_respond_ms",
)

# The legacy low-cardinality validation-cause labels, carried forward
# unchanged (they are also the frozen telemetry failure reasons).
VALIDATION_REASON_BY_MESSAGE = {
    "no JSON object in reply": "no_json_object",
    "review is not an object": "not_an_object",
    "model answer is not an object": "not_an_object",
    "improvement is not an object": "not_an_object",
    "nudge is not an object": "not_an_object",
    "expected a list": "wrong_field_type",
    "model answer evidence is not a list": "wrong_field_type",
    "improvement evidence is not a list": "wrong_field_type",
    "review summary is incomplete": "empty_required_field",
    "model answer is incomplete": "empty_required_field",
    "improvement is incomplete": "empty_required_field",
    "nudge is incomplete": "empty_required_field",
    "dimensions missing": "incomplete_dimensions",
    "incomplete dimensions": "incomplete_dimensions",
    "dimension is not an object": "invalid_dimension_shape",
    "dimension fields are invalid": "invalid_dimension_shape",
    "dimension explanation is incomplete": "incomplete_dimensions",
    "invalid dimension status": "invalid_dimension_status",
    "duplicate dimensions": "duplicate_dimensions",
    "numeric or universal review fields are not allowed": "numeric_universal_field",
    "numeric dimension scores are not allowed": "numeric_dimension_score",
    "review fields are invalid": "invalid_review_shape",
    "duplicate review list item": "duplicate_review_list_item",
    "evidence suggestion is not an object": "invalid_evidence_suggestion_shape",
    "evidence suggestion fields are invalid": "invalid_evidence_suggestion_shape",
    "evidence suggestions are invalid": "invalid_evidence_suggestion_shape",
    "duplicate evidence suggestions": "duplicate_evidence_suggestions",
    "duplicate JSON field": "duplicate_json_field",
    "opportunity context is too long": "opportunity_context_too_long",
    "review referenced unauthorized evidence": "unauthorized_evidence",
    "model answer referenced unauthorized evidence": "unauthorized_evidence",
    "improvement referenced unauthorized evidence": "unauthorized_evidence",
    "model answer has no approved evidence references": "no_evidence_reference",
    "duplicate evidence references": "duplicate_evidence",
    "model answer status is invalid": "invalid_status",
}

UNCLASSIFIED_REASON = "unclassified"

_VALIDATION_CLASS_BY_TYPE = {
    ValueError: "validation_value",
    TypeError: "validation_type",
    KeyError: "validation_key",
}


def normalize_stop_reason(raw):
    value = raw if isinstance(raw, str) and raw else "unknown"
    return value if value in STOP_REASONS else "unknown"


def classify_validation_error(error):
    """Map one rejected model reply to (failure_reason, exception_class)."""
    if isinstance(error, json.JSONDecodeError):
        return "unparseable_json", "validation_json_decode"
    if isinstance(error, (KeyError, TypeError)):
        return "unexpected_shape", _VALIDATION_CLASS_BY_TYPE[type(error)]
    reason = VALIDATION_REASON_BY_MESSAGE.get(str(error), UNCLASSIFIED_REASON)
    if isinstance(error, ValueError):
        return reason, "validation_value"
    return UNCLASSIFIED_REASON, "runtime_unexpected"


def normalize_provider_error(error):
    """Map a pinned-SDK exception to (failure_reason, class, status_code).

    ``failure_reason`` is the canonical §3 provider taxonomy (C6) and the
    persisted exception class mirrors it under the closed B4 enum:
    ``provider_timeout`` | ``provider_transport`` | ``provider_rejected``.
    Only ``provider_rejected`` may carry an attribute, and only the
    integer ``status_code`` (100-599). Raw SDK class names, messages,
    request ids, URLs, and bodies are never stored.
    """
    if isinstance(error, anthropic.APITimeoutError):
        return "timeout", "provider_timeout", None
    if isinstance(error, anthropic.APIConnectionError):
        return "transport", "provider_transport", None
    if isinstance(error, anthropic.APIStatusError):
        status = getattr(error, "status_code", None)
        return "rejected", "provider_rejected", (
            status if isinstance(status, int)
            and HTTP_STATUS_RANGE[0] <= status <= HTTP_STATUS_RANGE[1]
            else None
        )
    return "unexpected_server_fault", "runtime_unexpected", None


def normalize_exception_class(error):
    """Map ANY exception to the closed class allowlist, for bounded logs
    and the generic handlers. Corrections C7/B4: raw Python/SDK class
    names never reach a log line or a row; an unknown class becomes
    ``runtime_unexpected``; a malformed provider response envelope
    (IndexError/AttributeError while reading it) is
    ``provider_response_shape``; the database adapter's own failure class
    is the log-only ``database_error``.
    """
    if isinstance(error, json.JSONDecodeError):
        return "validation_json_decode"
    if isinstance(error, anthropic.APIError):
        return normalize_provider_error(error)[1]
    if isinstance(error, DatabaseServiceError):
        return "database_error"
    if isinstance(error, (IndexError, AttributeError)):
        return "provider_response_shape"
    for exception_type, enum in (
        (ValueError, "validation_value"),
        (TypeError, "validation_type"),
        (KeyError, "validation_key"),
    ):
        if isinstance(error, exception_type):
            return enum
    return "runtime_unexpected"


def persisted_exception_class(error):
    """The normalized class, restricted to the persisted B4 enum (the
    log-only ``database_error`` becomes ``runtime_unexpected`` in a row)."""
    normalized = normalize_exception_class(error)
    return (
        normalized if normalized in EXCEPTION_CLASSES else "runtime_unexpected"
    )


def source_class_counts(question=0, answer=0, role_context=0,
                        member_evidence=0, history_selection=0,
                        confirmed_context=0):
    counts = {
        "question": question,
        "answer": answer,
        "role_context": role_context,
        "member_evidence": member_evidence,
        "history_selection": history_selection,
        "confirmed_context": confirmed_context,
    }
    # Consolidated correction B4: never clamp or coerce. A negative,
    # over-cap, Boolean, float, or string count is a caller bug and is
    # rejected here, exactly as the SQL boundary rejects it.
    for key, value in counts.items():
        if (
            not isinstance(value, int) or isinstance(value, bool)
            or not 0 <= value <= SOURCE_CLASS_COUNT_CAP
        ):
            raise ValueError(
                "telemetry contract violation: source count %r must be an "
                "integer 0-%d" % (key, SOURCE_CLASS_COUNT_CAP)
            )
    return counts


class ServerCallAttempt:
    """Phase timing and identity for one server_call row."""

    def __init__(self):
        self.attempt_uuid = str(uuid.uuid4())
        self.durations = {name: 0 for name in DURATION_FIELDS}

    @contextmanager
    def phase(self, name):
        field = "dur_%s_ms" % name
        if field not in self.durations:
            raise ValueError("unknown telemetry phase: %s" % name)
        started = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
            self.durations[field] += int(elapsed_ms)


def build_event(
    attempt,
    event_kind,
    outcome,
    http_status,
    validation_result,
    counts,
    specialist=None,
    composition=None,
    bundle=None,
    release_set_id=None,
    parent_attempt_uuid=None,
    failure_state=None,
    failure_reason=None,
    exception_class=None,
    exception_attrs=None,
    provider_response=None,
):
    """Assemble one validated server_call event dict."""
    usage = getattr(provider_response, "usage", None) if provider_response else None
    model = bundle.model if bundle is not None else None
    provider_usage, cost, schedule_id = price_usage(model, usage)

    event = {
        "attempt_uuid": attempt.attempt_uuid,
        "event_kind": event_kind,
        "outcome": outcome,
        "http_status": int(http_status),
        "retry_ordinal": 0,
        "specialist": specialist,
        "composition": composition,
        "bundle_label": bundle.bundle_label if bundle is not None else None,
        "bundle_content_sha256": (
            bundle.content_sha256 if bundle is not None else None
        ),
        "release_set_id": release_set_id,
        "parent_attempt_uuid": parent_attempt_uuid,
        "operation_id": None,
        "failure_state": failure_state,
        "failure_reason": failure_reason,
        "guardian_rejections": [],
        "validation_result": validation_result,
        "source_class_counts": counts,
        "provider_usage": provider_usage,
        "cost_microusd": cost,
        "pricing_schedule_id": schedule_id,
        # B4: only a genuinely absent attrs map defaults to {}; a falsy
        # non-dict (like []) passes through and is REJECTED, never coerced.
        "exception": (
            {
                "class": exception_class,
                "attrs": exception_attrs if exception_attrs is not None else {},
            }
            if exception_class is not None
            else None
        ),
    }
    # Consolidated correction B4: durations pass through unclamped; an
    # out-of-bounds value fails validation instead of being silently
    # rewritten into a false in-bounds measurement.
    for field in DURATION_FIELDS:
        event[field] = attempt.durations[field]
    event["dur_total_server_ms"] = sum(
        event[field] for field in DURATION_FIELDS
    )
    validate_event(event)
    return event


def validate_event(event):
    """Sentinel validation of every frozen field, bound, and pairing rule.

    Correction B4: numeric bounds, the exact six-key integer source-count
    shape, the closed nine-value exception enum with per-class attribute
    rules, canonical 64-lowercase-hex identities, and the parent/child
    shape rules are enforced here exactly as the SQL boundary enforces
    them — the same values pass and fail on both sides.
    """

    def fail(reason):
        raise ValueError("telemetry contract violation: %s" % reason)

    def bounded_int(value, low, high):
        return (
            isinstance(value, int) and not isinstance(value, bool)
            and low <= value <= high
        )

    if not isinstance(event.get("attempt_uuid"), str):
        fail("attempt_uuid")
    uuid.UUID(event["attempt_uuid"])
    if event.get("event_kind") not in EVENT_KINDS:
        fail("event_kind")
    if event.get("outcome") not in OUTCOMES:
        fail("outcome")
    if not bounded_int(event.get("http_status"), *HTTP_STATUS_RANGE):
        fail("http_status out of 100-599")
    if not bounded_int(event.get("retry_ordinal"), *RETRY_ORDINAL_RANGE):
        fail("retry_ordinal out of 0-15")
    for field in DURATION_FIELDS + ("dur_total_server_ms",):
        if not bounded_int(event.get(field), *DURATION_MS_RANGE):
            fail("%s out of duration bounds" % field)
    for field in DURATION_FIELDS:
        if event["dur_total_server_ms"] < event[field]:
            fail("dur_total_server_ms below stage %s" % field)

    specialist_row = event["event_kind"] == "specialist_call"
    if specialist_row:
        if event.get("specialist") not in (
            "coach", "revision", "grounded_example", "generic_example",
            "planning_hints",
        ):
            fail("specialist")
        if event.get("composition") is not None:
            fail("composition must be null on a specialist row")
        label = event.get("bundle_label")
        content = event.get("bundle_content_sha256")
        if (label is None) != (content is None):
            fail("bundle_ref halves must be null together")
        if content is not None:
            if not is_full_sha256(content):
                fail("bundle_content_sha256")
            if event.get("release_set_id") is None:
                fail("a resolved specialist row carries release identity")
        if content is None:
            if not (
                event.get("outcome") == "failed"
                and event.get("failure_state") == "service_not_configured"
                and event.get("failure_reason") == "active_release_unresolved"
            ):
                fail("null bundle_ref is only lawful pre-resolution")
            if event.get("release_set_id") is not None:
                fail("a pre-resolution row carries no release identity")
    else:
        if event.get("composition") not in COMPOSITIONS:
            fail("composition")
        for field in ("specialist", "bundle_label", "bundle_content_sha256",
                      "parent_attempt_uuid"):
            if event.get(field) is not None:
                fail("%s must be null on a composition parent" % field)
        if event.get("provider_usage") is not None:
            fail("provider usage must be null on a composition parent")
        if event.get("cost_microusd") is not None:
            fail("cost must be null on a composition parent")
        if event.get("exception") is not None:
            fail("exception must be null on a composition parent")

    release = event.get("release_set_id")
    if release is not None and not is_full_sha256(release):
        fail("release_set_id")
    parent = event.get("parent_attempt_uuid")
    if parent is not None:
        uuid.UUID(parent)
    if event.get("operation_id") is not None:
        fail("operation_id is never set in slice 1")

    # Consolidated correction B4: the one closed state matrix. Every
    # (outcome, failure_state, failure_reason, exception_class,
    # validation_result, release nullability) combination outside
    # ROW_STATE_MATRIX is rejected — semantically impossible rows such as
    # invalid_output+transport, provider_failure+a validation reason,
    # internal_error+validation_rejected, or a resolved release on a
    # service_not_configured row cannot be persisted.
    state = event.get("failure_state")
    reason = event.get("failure_reason")
    exception = event.get("exception")
    if event.get("validation_result") not in VALIDATION_RESULTS:
        fail("validation_result")
    if event["outcome"] in RESERVED_OUTCOMES:
        fail("outcome %r is reserved for a later slice" % event["outcome"])
    if reason in RESERVED_FAILURE_REASONS:
        fail("failure_reason %r is reserved for a later slice" % reason)
    if event["outcome"] == "failed":
        if state not in ROW_STATE_MATRIX:
            fail("failure_state")
        matrix = ROW_STATE_MATRIX[state]
        if reason not in matrix["failure_reasons"]:
            fail("failure_reason %r is impossible under failure_state %r"
                 % (reason, state))
        expected_validation = (
            matrix["specialist_validation_result"] if specialist_row
            else "not_applicable"
        )
        if event["validation_result"] != expected_validation:
            fail("validation_result %r is impossible under failure_state %r"
                 % (event["validation_result"], state))
        if matrix["release_identity"] == "forbidden":
            if event.get("release_set_id") is not None:
                fail("release identity is forbidden under %s" % state)
        elif event.get("release_set_id") is None:
            fail("release identity is required under %s" % state)
        if specialist_row:
            if matrix["exception_required"] and exception is None:
                fail("a failed %s specialist row requires its exception"
                     % state)
            if not matrix["exception_required"] and exception is not None:
                fail("exception is forbidden under %s" % state)
            if exception is not None:
                exception_class = exception.get("class")
                pairs = matrix.get("reason_exception_pairs")
                if pairs is not None:
                    if exception_class != pairs.get(reason):
                        fail("exception class %r does not pair with "
                             "failure_reason %r" % (exception_class, reason))
                elif exception_class not in matrix["exception_classes"]:
                    fail("exception class %r is impossible under "
                         "failure_state %r" % (exception_class, state))
    else:
        if state is not None:
            fail("failure_state must be null on success outcomes")
        if reason is not None:
            fail("failure_reason must be null unless failed")
        if exception is not None:
            fail("exception requires a failed outcome")
        if event.get("release_set_id") is None:
            fail("a non-failed row always carries release identity")
        expected_validation = "passed" if specialist_row else "not_applicable"
        if event["validation_result"] != expected_validation:
            fail("validation_result %r is impossible on a non-failed %s row"
                 % (event["validation_result"], event["event_kind"]))

    if event.get("guardian_rejections") != []:
        fail("guardian_rejections must be [] under guardian-runtime-legacy@1")

    counts = event.get("source_class_counts")
    if not isinstance(counts, dict) or set(counts) != set(SOURCE_CLASSES):
        fail("source_class_counts must carry exactly the six source classes")
    for value in counts.values():
        if not bounded_int(value, 0, SOURCE_CLASS_COUNT_CAP):
            fail("source_class_counts values must be integers 0-32")
    if not specialist_row and any(value != 0 for value in counts.values()):
        fail("a composition parent carries all-zero source counts")

    usage = event.get("provider_usage")
    if usage is not None:
        # Usage exists only where a provider response exists: never on a
        # composition parent (checked above), never before resolution, and
        # never on a provider_failure row (timeout/transport/rejected all
        # mean no usable response object).
        if not specialist_row:
            fail("provider usage only accompanies a specialist row")
        if state in ("provider_failure", "service_not_configured"):
            fail("provider usage is impossible under failure_state %r" % state)
        if set(usage) != {"input_tokens", "output_tokens"}:
            fail("provider_usage keys")
        for value in usage.values():
            if not bounded_int(value, *TOKEN_RANGE):
                fail("provider token out of bounds")
    cost = event.get("cost_microusd")
    schedule = event.get("pricing_schedule_id")
    if (cost is None) != (schedule is None):
        fail("cost and pricing identity must be null together")
    if cost is not None:
        if not bounded_int(cost, *COST_MICROUSD_RANGE):
            fail("cost_microusd")
        if not is_full_sha256(schedule):
            fail("pricing_schedule_id")
        if usage is None:
            fail("cost without usage")

    if exception is not None:
        if set(exception) != {"class", "attrs"}:
            fail("exception carries exactly class and attrs")
        exception_class = exception.get("class")
        if exception_class not in EXCEPTION_CLASSES:
            fail("exception class outside the closed enum")
        attrs = exception.get("attrs")
        # B4: attrs must be a JSON OBJECT — never an array, scalar, or
        # null — and class and attrs travel together (a class always has
        # its attrs map, empty where the spec says empty).
        if not isinstance(attrs, dict):
            fail("exception attrs must be an object")
        spec = EXCEPTION_ATTR_SPEC[exception_class]
        for required_key in spec["required"]:
            if required_key not in attrs:
                fail("exception class %r requires attribute %r"
                     % (exception_class, required_key))
        allowed = set(spec["required"]) | set(spec["optional"])
        for key, value in attrs.items():
            if key not in allowed:
                fail("attribute %r is not allowed for this exception class"
                     % key)
            if key == "provider_stop_reason":
                if value not in STOP_REASONS:
                    fail("provider_stop_reason outside the closed enum")
            elif key == "reply_chars":
                if not bounded_int(value, *REPLY_CHARS_RANGE):
                    fail("reply_chars out of 0-100000")
            elif key == "status_code":
                if not bounded_int(value, *HTTP_STATUS_RANGE):
                    fail("exception status_code out of 100-599")
    return True


def append_server_call(event):
    """One bounded append attempt. Returns True when the row was sent.

    Any failure is logged content-free and swallowed: the member response,
    status, and provider-call count are already decided and must not
    change.
    """
    try:
        validate_event(event)
        parameters = [
            ("@AttemptUuid", event["attempt_uuid"]),
            ("@EventKind", event["event_kind"]),
            ("@Outcome", event["outcome"]),
            ("@HttpStatus", event["http_status"]),
            ("@RetryOrdinal", event["retry_ordinal"]),
            ("@DurReceiveMs", event["dur_receive_ms"]),
            ("@DurRetrievalMs", event["dur_retrieval_ms"]),
            ("@DurManifestMs", event["dur_manifest_ms"]),
            ("@DurProviderMs", event["dur_provider_ms"]),
            ("@DurValidateMs", event["dur_validate_ms"]),
            ("@DurRespondMs", event["dur_respond_ms"]),
            ("@DurTotalServerMs", event["dur_total_server_ms"]),
            ("@Specialist", event["specialist"]),
            ("@BundleLabel", event["bundle_label"]),
            ("@BundleContentSha256", event["bundle_content_sha256"]),
            ("@Composition", event["composition"]),
            ("@ReleaseSetId", event["release_set_id"]),
            ("@ParentAttemptUuid", event["parent_attempt_uuid"]),
            ("@OperationId", event["operation_id"]),
            ("@FailureState", event["failure_state"]),
            ("@FailureReason", event["failure_reason"]),
            ("@GuardianRejectionsJson", json.dumps(
                event["guardian_rejections"], separators=(",", ":"))),
            ("@ValidationResult", event["validation_result"]),
            ("@SourceClassCountsJson", json.dumps(
                event["source_class_counts"], sort_keys=True,
                separators=(",", ":"))),
            ("@ProviderInputTokens", (
                event["provider_usage"]["input_tokens"]
                if event["provider_usage"] else None)),
            ("@ProviderOutputTokens", (
                event["provider_usage"]["output_tokens"]
                if event["provider_usage"] else None)),
            ("@CostMicrousd", event["cost_microusd"]),
            ("@PricingScheduleId", event["pricing_schedule_id"]),
            ("@ExceptionClass", (
                event["exception"]["class"] if event["exception"] else None)),
            ("@ExceptionAttrsJson", (
                json.dumps(event["exception"]["attrs"], sort_keys=True,
                           separators=(",", ":"))
                if event["exception"] else None)),
        ]
        database_service.execute_procedure(
            "usp_AppendInterviewAIServerCall", parameters
        )
        return True
    except Exception as error:
        logger.warning(
            "interview telemetry append failed: class=%s",
            normalize_exception_class(error),
        )
        return False
