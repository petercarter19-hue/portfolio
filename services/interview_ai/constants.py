"""Frozen enums for PS-INTERVIEW-AI-EXTRACT-001 (slice 1).

Values are bound by docs/initiatives/PS-INTERVIEW-AI-EXTRACT-001/
01_FROZEN_CONTRACTS.md and the consolidated architecture's canonical spine
(§3). A change here is a contracts change, never a casual edit.
"""

# §3 specialist enum restricted to the five present specialists, in the
# frozen bundle slot order (interim planning_hints last).
BUNDLE_SLOT_ORDER = (
    "coach",
    "revision",
    "grounded_example",
    "generic_example",
    "planning_hints",
)

SOURCE_CLASSES = (
    "question",
    "answer",
    "role_context",
    "member_evidence",
    "history_selection",
    "confirmed_context",
)
SOURCE_CLASS_COUNT_CAP = 32

EVENT_KINDS = ("specialist_call", "composition_parent")
COMPOSITIONS = ("compare",)
OUTCOMES = ("success", "computed_outcome", "refused", "failed")
VALIDATION_RESULTS = ("passed", "rejected", "not_applicable")

# §3 failure states reachable in slice 1.
FAILURE_STATES = (
    "invalid_output",
    "provider_failure",
    "internal_error",
    "service_not_configured",
)

VALIDATION_FAILURE_REASONS = (
    "no_json_object",
    "not_an_object",
    "wrong_field_type",
    "empty_required_field",
    "incomplete_dimensions",
    "invalid_dimension_shape",
    "invalid_dimension_status",
    "duplicate_dimensions",
    "numeric_universal_field",
    "numeric_dimension_score",
    "invalid_review_shape",
    "duplicate_review_list_item",
    "invalid_evidence_suggestion_shape",
    "duplicate_evidence_suggestions",
    "duplicate_json_field",
    "opportunity_context_too_long",
    "unauthorized_evidence",
    "no_evidence_reference",
    "duplicate_evidence",
    "invalid_status",
    "unparseable_json",
    "unexpected_shape",
    "unclassified",
)

# Correction C6: persisted provider failure_reason uses the canonical §3
# taxonomy, never SDK-shaped values. `abandoned` is reserved (the §3
# orphan-reaper state); no slice-1 runtime path emits it.
PROVIDER_FAILURE_REASONS = (
    "transport",
    "timeout",
    "rejected",
    "abandoned",
)

SERVER_FAILURE_REASONS = ("unexpected_server_fault", "active_release_unresolved")

FAILURE_REASONS = (
    VALIDATION_FAILURE_REASONS + PROVIDER_FAILURE_REASONS + SERVER_FAILURE_REASONS
)

# Correction B4: the persisted exception-class enum is closed to exactly
# nine values. The four validation classes may carry only
# provider_stop_reason + reply_chars; provider_rejected may carry only
# status_code; every other class requires an EMPTY attribute map. Raw
# SDK/Python class names, messages, tracebacks, URLs, bodies, headers,
# provider ids, member text, and model output are never persisted.
VALIDATION_EXCEPTION_CLASSES = (
    "validation_json_decode",
    "validation_value",
    "validation_key",
    "validation_type",
)

EXCEPTION_CLASSES = VALIDATION_EXCEPTION_CLASSES + (
    "provider_timeout",
    "provider_transport",
    "provider_rejected",
    "provider_response_shape",
    "runtime_unexpected",
)

# Bounded logs may additionally say `database_error` for the database
# adapter's own failure class; no telemetry row path emits it.
LOG_ONLY_EXCEPTION_CLASSES = ("database_error",)

EXCEPTION_ATTR_KEYS = ("status_code", "provider_stop_reason", "reply_chars")

# Consolidated correction B4: ONE closed per-row state matrix, enforced
# identically in Python (telemetry.validate_event) and SQL
# (usp_AppendInterviewAIServerCall). Every combination outside this
# table is rejected on both sides.
#
# outcome semantics:
#   success / computed_outcome -> failure_state, failure_reason, and
#     exception are all NULL; validation_result is 'passed' on a
#     specialist row and 'not_applicable' on a composition parent.
#   failed -> failure_state selects one matrix row below.
#   refused -> RESERVED: no slice-1 runtime path emits it; rejected.
ROW_STATE_MATRIX = {
    "invalid_output": {
        "failure_reasons": VALIDATION_FAILURE_REASONS,
        "specialist_validation_result": "rejected",
        "exception_required": True,
        "exception_classes": VALIDATION_EXCEPTION_CLASSES,
        "release_identity": "required",
    },
    "provider_failure": {
        # 'abandoned' is the reserved §3 orphan-reaper value: lawful in
        # the enum, unreachable in slice 1, rejected by the matrix.
        "failure_reasons": ("transport", "timeout", "rejected"),
        "reason_exception_pairs": {
            "transport": "provider_transport",
            "timeout": "provider_timeout",
            "rejected": "provider_rejected",
        },
        "specialist_validation_result": "not_applicable",
        "exception_required": True,
        "release_identity": "required",
    },
    "internal_error": {
        "failure_reasons": ("unexpected_server_fault",),
        "specialist_validation_result": "not_applicable",
        "exception_required": True,
        "exception_classes": ("runtime_unexpected", "provider_response_shape"),
        "release_identity": "required",
    },
    "service_not_configured": {
        "failure_reasons": ("active_release_unresolved",),
        "specialist_validation_result": "not_applicable",
        "exception_required": False,
        "exception_classes": (),
        "release_identity": "forbidden",
    },
}
RESERVED_OUTCOMES = ("refused",)
RESERVED_FAILURE_REASONS = ("abandoned",)

# Per-class attribute contract: required keys must ALL be present,
# optional keys MAY be present, anything else is rejected. Values are
# checked against their own bounds/enums.
EXCEPTION_ATTR_SPEC = {
    "validation_json_decode": {
        "required": ("provider_stop_reason", "reply_chars"), "optional": (),
    },
    "validation_value": {
        "required": ("provider_stop_reason", "reply_chars"), "optional": (),
    },
    "validation_key": {
        "required": ("provider_stop_reason", "reply_chars"), "optional": (),
    },
    "validation_type": {
        "required": ("provider_stop_reason", "reply_chars"), "optional": (),
    },
    "provider_timeout": {"required": (), "optional": ()},
    "provider_transport": {"required": (), "optional": ()},
    "provider_rejected": {"required": (), "optional": ("status_code",)},
    "provider_response_shape": {"required": (), "optional": ()},
    "runtime_unexpected": {"required": (), "optional": ()},
}

# B4 numeric bounds, enforced identically in Python and SQL.
HTTP_STATUS_RANGE = (100, 599)
RETRY_ORDINAL_RANGE = (0, 15)
DURATION_MS_RANGE = (0, 86_400_000)
TOKEN_RANGE = (0, 2_147_483_647)
REPLY_CHARS_RANGE = (0, 100_000)
COST_MICROUSD_RANGE = (0, 2**63 - 1)

STOP_REASONS = (
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "unknown",
)

GUARDIAN_SET_VERSION = "guardian-runtime-legacy@1"
# interview-contracts@7 (B1-B3 second round): the manager trust record
# moves outside the writer's surfaces
# (docs/initiatives/PS-INTERVIEW-AI-ARCHITECTURE-001/ANCHOR_TRUST_ROOT.json);
# adjacent anchors must strictly advance a governed version; the retired
# /api/interview/coach 410 contract is a guarded fragment; requests can
# no longer initialize boot state (absent state answers 503 without
# touching release files).
# interview-contracts@6 (consolidated B1-B6 corrections): complete
# guarded app.py closure with a mechanical transitive test; boot-frozen
# release state; Flask/Flask-Limiter join the locked external closure;
# one closed Python+SQL telemetry state matrix with strict (never
# clamped/coerced) numerics; strict 42-source evaluation manifest with a
# shared parser; anchor chain bound to an external trust root with
# monotonic version enforcement. (@5 deployable evaluation manifest;
# @4 unified telemetry contract; @3 external runtime lock; @2 app.py
# fragments and guarded builder.)
CONTRACTS_VERSION = "interview-contracts@7"
THRESHOLD_SET_ID = "initial-extraction-parity"
THRESHOLD_SET_VERSION = "1"

ACTIVE_RELEASE_CONFIG_KEY = "PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET"

# Frozen member copy for the fail-closed unresolved-release state. This
# state is unreachable until release configuration exists; it is the
# machinery's fail-closed posture, not a change to current behaviour.
SERVICE_NOT_CONFIGURED_COPY = (
    "Interview AI is not configured right now. Retrying will not help until "
    "service configuration is restored."
)
