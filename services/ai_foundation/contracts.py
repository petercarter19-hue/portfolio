"""Provider-neutral request, source, answer, and handoff contracts.

Source text and its exact approved version, evidence-backed claims, labelled
interpretations, and unknown boundaries remain distinct. Nothing here
persists, publishes, or mutates member truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
import re


def _required_text(label: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required text")


def _bounded_identifier(label: str, value: object, *, maximum: int = 200) -> None:
    _required_text(label, value)
    if len(value) > maximum or not value.isprintable():
        raise ValueError(f"{label} is not a valid bounded identifier")


class Purpose(str, Enum):
    PUBLIC_PROFILE_ANSWER = "public_profile_answer"
    RECRUITER_BRIEF = "recruiter_brief"
    EVIDENCE_FINDER = "evidence_finder"
    INTERVIEW_PREPARATION = "interview_preparation"
    PRIVATE_COACHING = "private_coaching"


class Audience(str, Enum):
    PUBLIC = "public"
    OWNER = "owner"
    AUTHORIZED_RECRUITER = "authorized_recruiter"


class AnswerKind(str, Enum):
    EVIDENCE = "evidence"
    INTERPRETATION = "interpretation"
    BOUNDARY = "boundary"


class AnswerState(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    NOT_ESTABLISHED = "not_established"
    AMBIGUOUS = "ambiguous"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class HandoffReason(str, Enum):
    MISSING_PUBLIC_EVIDENCE = "missing_public_evidence"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    HUMAN_JUDGMENT = "human_judgment"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class ExtractionPurpose(str, Enum):
    """Closed purpose vocabulary for structured intake extraction work.

    Answer-oriented :class:`Purpose` values must never route extraction or
    matching traffic: those flows need their own explicit scope so a future
    purpose change cannot silently widen what the intake adapter may ask for.
    """

    MY_DATA_INTAKE_EXTRACTION = "my_data_intake_extraction"
    MY_DATA_INTAKE_MATCHING = "my_data_intake_matching"
    RESUME_PRIVATE_SYNTHESIS = "resume_private_synthesis"
    RESUME_CAREER_INTERVIEW = "resume_career_interview"


#: Medium and high are explicit My Data extraction comparisons; matching keeps xhigh.
STRUCTURED_MODEL_LUNA = "gpt-5.6-luna"
STRUCTURED_MODEL_SOL = "gpt-6-sol"
STRUCTURED_MODEL_NATIVE_LUNA = "gpt-6-luna"
STRUCTURED_MODEL_SOL61 = "gpt-6.1-sol"
REASONING_EFFORT_LOW = "low"
# Sol is opt-in only for owner intake extraction; the global Luna set stays closed.
SOL_EXTRACTION_REASONING_EFFORTS = frozenset({"low", "medium", "high"})
REASONING_EFFORT_XHIGH = "xhigh"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_HIGH = "high"
ALLOWED_REASONING_EFFORTS = frozenset(
    {REASONING_EFFORT_XHIGH, REASONING_EFFORT_MEDIUM, REASONING_EFFORT_HIGH}
)


@dataclass(frozen=True)
class GuideModelVariant:
    """A named immutable configuration, never a grant to spend or change a model."""

    name: str
    profile: str
    model_name: str
    deployment: str
    model_version: str
    reasoning_effort: str
    wire_bytes: int
    input_tokens: int
    output_tokens: int
    input_micro_usd_per_million: int
    output_micro_usd_per_million: int

    @property
    def reservation_micro_usd(self) -> int:
        return (self.input_tokens * self.input_micro_usd_per_million
                + self.output_tokens * self.output_micro_usd_per_million + 999999) // 1000000


GUIDE_MODEL_VARIANTS = MappingProxyType({record.name: record for record in (
    GuideModelVariant("turn.sol6_low", "interview", "gpt-6-sol", "eval0930-gpt-6-sol", "2026-09-22",
                      "low", 65536, 66560, 32768, 5000000, 15000000),
    GuideModelVariant("turn.sol61_medium", "interview", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29",
                      "medium", 65536, 66560, 16384, 100000000, 100000000),
    GuideModelVariant("turn.sol61_low", "interview", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29",
                      "low", 65536, 66560, 16384, 100000000, 100000000),
    GuideModelVariant("organize.luna_low", "extraction", "gpt-6-luna", "gpt-6-luna", "2026-09-22",
                      "low", 229376, 230400, 128000, 1000000, 6000000),
    GuideModelVariant("organize.sol61_medium", "extraction", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29",
                      "medium", 73728, 74752, 24576, 100000000, 100000000),
    GuideModelVariant("organize.sol61_low", "extraction", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29",
                      "low", 73728, 74752, 24576, 100000000, 100000000),
)})


def guide_model_variant(name: str, *, profile: str) -> GuideModelVariant:
    if not isinstance(name, str) or profile not in ("interview", "extraction"):
        raise ValueError("Closed Guide variant and profile required")
    record = GUIDE_MODEL_VARIANTS.get(name)
    if record is None or record.profile != profile:
        raise ValueError("Guide variant does not match its profile")
    return record


def validate_guide_variant_request(name: str, request: StructuredRequest, *, profile: str) -> GuideModelVariant:
    record = guide_model_variant(name, profile=profile)
    if type(request) is not StructuredRequest:
        raise ValueError("Structured Guide request required")
    request.__post_init__()
    product, purpose = (("my_data_intake", ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION)
                        if profile == "extraction" else
                        ("resume_private_assistance", ExtractionPurpose.RESUME_CAREER_INTERVIEW))
    if (request.product != product or request.purpose != purpose or request.audience != Audience.OWNER
            or request.model_name != record.model_name or request.reasoning_effort != record.reasoning_effort):
        raise ValueError("Guide request differs from its named variant")
    return record


def validate_guide_variant_bindings(name: str, *, profile: str, settings: dict,
                                  allocation: dict, contract: dict) -> GuideModelVariant:
    """Prove one record across all composition inputs before credentials/HTTP.

    Funding authority and purpose-specific caps still come from the reviewed
    allocation. Agreement here never creates an allocation or grants spending.
    """
    record = guide_model_variant(name, profile=profile)
    if any(type(value) is not dict for value in (settings, allocation, contract)):
        raise ValueError("Complete Guide variant bindings required")

    def require(actual, expected):
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError("Guide variant binding changed")
        if type(expected) is dict:
            for key in expected:
                require(actual[key], expected[key])
        elif type(expected) is list:
            for actual_item, expected_item in zip(actual, expected):
                require(actual_item, expected_item)

    for key, expected in {
        "variant": name, "model": record.model_name, "model_version": record.model_version,
        "alias": record.deployment, "effort": record.reasoning_effort, "tier": "default",
        "wire_bytes": record.wire_bytes, "input_tokens": record.input_tokens, "output_tokens": record.output_tokens,
        "safety_prices_per_million_micro_usd": [record.input_micro_usd_per_million, record.output_micro_usd_per_million],
    }.items():
        require(contract.get(key), expected)
    for key, expected in {
        "variant": name, "model": record.model_name, "model_version": record.model_version,
        "reasoning_effort": record.reasoning_effort, "service_tier": "default",
        "input_tokens": record.input_tokens, "output_tokens": record.output_tokens,
        "input_micro_usd_per_million": record.input_micro_usd_per_million,
        "output_micro_usd_per_million": record.output_micro_usd_per_million,
        "reservation_micro_usd": record.reservation_micro_usd, "maximum_calls": 100, "concurrent_requests": 1,
    }.items():
        require(allocation.get(key), expected)
    scope, cap = allocation.get("scope"), allocation.get("hard_cap_micro_usd")
    if (not isinstance(scope, str) or not re.fullmatch("[a-z0-9-]{1,80}", scope)
            or type(cap) is not int or cap < record.reservation_micro_usd):
        raise ValueError("Bound Guide allocation scope and cap required")
    require(settings.get("variant"), name)
    require(settings.get("deployment"), record.deployment)
    require(settings.get("provider"), {"maximum_input_bytes": record.wire_bytes,
        "maximum_input_tokens": record.input_tokens, "maximum_output_tokens": record.output_tokens})
    require(settings.get("budget"), {key: allocation[key] for key in
        ("scope", "maximum_calls", "hard_cap_micro_usd", "concurrent_requests")})
    prices = settings.get("prices")
    if (type(prices) is not dict or set(prices) != {
            "input_micro_usd_per_million", "output_micro_usd_per_million", "schedule_ref"}
            or not isinstance(prices["schedule_ref"], str) or not prices["schedule_ref"].strip()):
        raise ValueError("Bound Guide safety schedule required")
    require(prices["input_micro_usd_per_million"], record.input_micro_usd_per_million)
    require(prices["output_micro_usd_per_million"], record.output_micro_usd_per_million)
    return record


@dataclass(frozen=True)
class AIRequest:
    request_id: str
    product: str
    purpose: Purpose
    audience: Audience
    subject_key: str
    question: str = field(repr=False)
    context_key: str | None = None

    def __post_init__(self) -> None:
        _bounded_identifier("request_id", self.request_id)
        _bounded_identifier("product", self.product, maximum=100)
        _bounded_identifier("subject_key", self.subject_key)
        _required_text("question", self.question)
        if not isinstance(self.purpose, Purpose):
            raise ValueError("purpose must be a Purpose")
        if not isinstance(self.audience, Audience):
            raise ValueError("audience must be an Audience")
        if self.context_key is not None:
            _bounded_identifier("context_key", self.context_key, maximum=300)


@dataclass(frozen=True)
class SourceVersion:
    """One immutable source version already retrieved under authorization."""

    source_version_key: str
    source_key: str
    version: int
    subject_key: str
    title: str
    content: str = field(repr=False)
    content_sha256: str
    allowed_audiences: frozenset[Audience]
    allowed_purposes: frozenset[Purpose]

    def __post_init__(self) -> None:
        _bounded_identifier("source_version_key", self.source_version_key)
        _bounded_identifier("source_key", self.source_key)
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise ValueError("source version must be positive")
        _bounded_identifier("subject_key", self.subject_key)
        _required_text("title", self.title)
        _required_text("content", self.content)
        _required_text("content_sha256", self.content_sha256)
        if len(self.content_sha256) != 64 or any(
            character not in "0123456789abcdefABCDEF"
            for character in self.content_sha256
        ):
            raise ValueError("content digest must be a SHA-256 hex value")
        if not isinstance(self.allowed_audiences, frozenset) or any(
            not isinstance(value, Audience) for value in self.allowed_audiences
        ):
            raise ValueError("allowed audiences must be Audience values")
        if not isinstance(self.allowed_purposes, frozenset) or any(
            not isinstance(value, Purpose) for value in self.allowed_purposes
        ):
            raise ValueError("allowed purposes must be Purpose values")
        if not self.allowed_audiences or not self.allowed_purposes:
            raise ValueError("every source version needs an explicit use scope")

    @classmethod
    def approved(
        cls,
        *,
        source_version_key: str,
        source_key: str,
        version: int,
        subject_key: str,
        title: str,
        content: str,
        allowed_audiences: frozenset[Audience],
        allowed_purposes: frozenset[Purpose],
    ) -> "SourceVersion":
        return cls(
            source_version_key=source_version_key,
            source_key=source_key,
            version=version,
            subject_key=subject_key,
            title=title,
            content=content,
            content_sha256=sha256(content.encode("utf-8")).hexdigest(),
            allowed_audiences=allowed_audiences,
            allowed_purposes=allowed_purposes,
        )

    def digest_is_current(self) -> bool:
        return sha256(self.content.encode("utf-8")).hexdigest() == self.content_sha256

    def permits(self, request: AIRequest) -> bool:
        return (
            self.subject_key == request.subject_key
            and request.audience in self.allowed_audiences
            and request.purpose in self.allowed_purposes
        )


@dataclass(frozen=True)
class Citation:
    claim_id: str
    source_version_key: str
    start: int
    end: int
    excerpt: str = field(repr=False)


@dataclass(frozen=True)
class AnswerClaim:
    claim_id: str
    text: str
    kind: AnswerKind
    state: AnswerState
    citations: tuple[Citation, ...] = ()
    limitation: str | None = None


@dataclass(frozen=True)
class HandoffProposal:
    reason: HandoffReason
    question: str = field(repr=False)
    private: bool = True


@dataclass(frozen=True)
class GroundedAnswer:
    answer_id: str
    state: AnswerState
    summary: str
    claims: tuple[AnswerClaim, ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    handoff: HandoffProposal | None = None
    model_name: str | None = None
    prompt_contract_version: str | None = None

    @classmethod
    def unavailable(cls, *, answer_id: str, question: str) -> "GroundedAnswer":
        return cls(
            answer_id=answer_id,
            state=AnswerState.UNAVAILABLE,
            summary=(
                "Ask Pete is temporarily unavailable. The public resume and "
                "its evidence remain available to review."
            ),
            handoff=HandoffProposal(
                reason=HandoffReason.PROVIDER_UNAVAILABLE,
                question=question,
            ),
        )


@dataclass(frozen=True)
class StructuredRequest:
    """One strict structured-output extraction or matching call.

    ``instructions`` carry the closed extraction contract and ``input_text``
    carries member material as data. ``schema_name`` selects the exact JSON
    schema the provider must satisfy. The default is Luna xhigh; explicit
    extraction efforts stay owner-scoped. Sol6.1 low/medium is limited to owner
    extraction or career interview, and Sol6.1 synthesis remains high-only.
    Matching inherits none of these choices.
    """

    request_id: str
    product: str
    purpose: ExtractionPurpose
    audience: Audience
    subject_key: str
    instructions: str = field(repr=False)
    input_text: str = field(repr=False)
    schema_name: str
    reasoning_effort: str = REASONING_EFFORT_XHIGH
    model_name: str = STRUCTURED_MODEL_LUNA

    def __post_init__(self) -> None:
        _bounded_identifier("request_id", self.request_id)
        _bounded_identifier("product", self.product, maximum=100)
        _bounded_identifier("subject_key", self.subject_key)
        _required_text("instructions", self.instructions)
        _required_text("input_text", self.input_text)
        _bounded_identifier("schema_name", self.schema_name, maximum=100)
        if not isinstance(self.purpose, ExtractionPurpose):
            raise ValueError("purpose must be an ExtractionPurpose")
        if not isinstance(self.audience, Audience):
            raise ValueError("audience must be an Audience")
        owner_extraction = (self.product == "my_data_intake"
                            and self.purpose == ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION
                            and self.audience == Audience.OWNER)
        selected_private = (self.product == "resume_private_assistance"
                            and self.audience == Audience.OWNER)
        if self.model_name == STRUCTURED_MODEL_NATIVE_LUNA:
            if not owner_extraction or self.reasoning_effort != REASONING_EFFORT_LOW:
                raise ValueError("Native Luna Low requires owner My Data extraction")
        elif self.model_name == STRUCTURED_MODEL_SOL61:
            synthesis = (selected_private and self.purpose == ExtractionPurpose.RESUME_PRIVATE_SYNTHESIS
                         and self.reasoning_effort == REASONING_EFFORT_HIGH)
            guide = ((owner_extraction or (selected_private and self.purpose == ExtractionPurpose.RESUME_CAREER_INTERVIEW))
                     and self.reasoning_effort in (REASONING_EFFORT_LOW, REASONING_EFFORT_MEDIUM))
            if not (synthesis or guide):
                raise ValueError("Sol6.1 requires its closed private owner purpose and effort")
        elif (self.model_name == STRUCTURED_MODEL_SOL and selected_private
              and self.purpose == ExtractionPurpose.RESUME_CAREER_INTERVIEW):
            if self.reasoning_effort != REASONING_EFFORT_LOW:
                raise ValueError("Career interview requires Sol6 Low")
        else:
            if self.model_name not in (STRUCTURED_MODEL_LUNA, STRUCTURED_MODEL_SOL):
                raise ValueError("structured model is not the accepted contract value")
            efforts = (SOL_EXTRACTION_REASONING_EFFORTS
                       if self.model_name == STRUCTURED_MODEL_SOL else ALLOWED_REASONING_EFFORTS)
            if not isinstance(self.reasoning_effort, str) or self.reasoning_effort not in efforts:
                raise ValueError("reasoning effort is not the accepted contract value")
            if self.purpose in {ExtractionPurpose.RESUME_PRIVATE_SYNTHESIS,
                                ExtractionPurpose.RESUME_CAREER_INTERVIEW}:
                raise ValueError("Private Resume purposes require their selected model")
            if (self.model_name == STRUCTURED_MODEL_SOL
                    or self.reasoning_effort != REASONING_EFFORT_XHIGH) and not owner_extraction:
                raise ValueError(f"{self.reasoning_effort} reasoning requires owner My Data extraction")


@dataclass(frozen=True)
class StructuredResult:
    """Validated payload and usage, with configured and reported identity separate.

    ``model_name`` identifies the configured product model. A returned deployment
    alias is retained in ``response_model_name`` and labeled by its identity
    source; ``response_model_version`` stays unknown unless separately reported.
    """

    request_id: str
    schema_name: str
    model_name: str | None
    payload: object
    input_tokens: int
    output_tokens: int
    deployment_name: str | None = None
    configured_model_version: str | None = None
    response_model_name: str | None = None
    response_model_version: str | None = None
    response_identity_source: str | None = None

    def __post_init__(self) -> None:
        _bounded_identifier("request_id", self.request_id)
        _bounded_identifier("schema_name", self.schema_name, maximum=100)
        if self.model_name is not None:
            _bounded_identifier("model_name", self.model_name, maximum=100)
        for label, value in (("input_tokens", self.input_tokens),
                             ("output_tokens", self.output_tokens)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")
