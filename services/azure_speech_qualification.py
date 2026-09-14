"""Privacy-safe scoring and progress state for the Azure Speech daily suite."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping, Sequence

TARGET_AUDIO_SECONDS = 36_900  # 10.25 hours at $0.10/hour = $1.025.
MAX_AUDIO_SECONDS = 37_800  # 10.5-hour fail-closed ceiling.
PRICE_USD_PER_AUDIO_HOUR = Decimal("0.10")
MAX_PRICE_USD_PER_AUDIO_HOUR = Decimal("0.36")
MAX_REQUESTS = 8
SAMPLE_WORD_LIMIT = 400
PROGRESS_SCHEMA_VERSION = 2

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
_ALLOWED_PROFILES = {
    "clean",
    "fast",
    "slow",
    "light_noise",
    "low_gain",
    "phone_band",
    "high_pitch",
    "low_pitch",
}


class SpeechQualificationError(ValueError):
    """The suite input or progress state is unsafe or ambiguous."""


@dataclass(frozen=True)
class SpeechEvaluationCase:
    key: str
    product: str
    capability: str
    benchmark_ref: str
    profile: str
    text: str
    required_terms: tuple[str, ...]
    speed_wpm: int
    pitch: int


@dataclass(frozen=True)
class SpeechProfileResult:
    key: str
    product: str
    capability: str
    benchmark_ref: str
    profile: str
    audio_seconds: int
    latency_milliseconds: int
    sample_word_error_rate_milli: int
    required_term_recall_milli: int
    token_count_ratio_milli: int
    punctuation_coverage_milli: int
    quality_passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpeechProgress:
    day: date
    fixture_digest: str
    attempts: Mapping[str, int]
    results: Mapping[str, SpeechProfileResult]

    @property
    def audio_seconds(self) -> int:
        return sum(item.audio_seconds for item in self.results.values())

    @property
    def attempted_audio_seconds(self) -> int:
        """Upper bound for audio that might have reached paid processing."""

        return sum(self.attempts.values())

    @property
    def all_quality_passed(self) -> bool:
        return bool(self.results) and all(
            item.quality_passed for item in self.results.values()
        )


def _bounded_text(value: object, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or value != value.strip() or not value:
        raise SpeechQualificationError(f"{label} must be nonempty and trimmed")
    if "\n" in value or "\r" in value or len(value) > maximum:
        raise SpeechQualificationError(f"{label} is outside its safe bound")
    return value


def load_cases(path: Path) -> tuple[SpeechEvaluationCase, ...]:
    """Load a fixed synthetic corpus definition without accepting commands."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpeechQualificationError("speech fixture is unavailable") from error
    if not isinstance(payload, list) or len(payload) != MAX_REQUESTS:
        raise SpeechQualificationError(f"speech fixture must contain {MAX_REQUESTS} cases")

    cases: list[SpeechEvaluationCase] = []
    for raw in payload:
        if not isinstance(raw, dict):
            raise SpeechQualificationError("speech case is malformed")
        if set(raw) != {
            "key",
            "product",
            "capability",
            "benchmark_ref",
            "profile",
            "text",
            "required_terms",
            "speed_wpm",
            "pitch",
        }:
            raise SpeechQualificationError("speech case fields are not exact")
        key = _bounded_text(raw["key"], "key", maximum=64)
        if not _IDENTIFIER.fullmatch(key):
            raise SpeechQualificationError("speech case key is invalid")
        profile = _bounded_text(raw["profile"], "profile", maximum=32)
        if profile not in _ALLOWED_PROFILES:
            raise SpeechQualificationError("speech case profile is not allowlisted")
        terms = raw["required_terms"]
        if (
            not isinstance(terms, list)
            or not 2 <= len(terms) <= 12
            or any(not isinstance(term, str) for term in terms)
        ):
            raise SpeechQualificationError("required terms are malformed")
        normalized_terms = tuple(
            _bounded_text(
                " ".join(normalized_words(term)), "required term", maximum=48
            )
            for term in terms
        )
        if len(normalized_terms) != len(set(normalized_terms)):
            raise SpeechQualificationError("required terms must be unique")
        speed = raw["speed_wpm"]
        pitch = raw["pitch"]
        if isinstance(speed, bool) or not isinstance(speed, int) or not 105 <= speed <= 210:
            raise SpeechQualificationError("speech speed is outside its safe bound")
        if isinstance(pitch, bool) or not isinstance(pitch, int) or not 25 <= pitch <= 75:
            raise SpeechQualificationError("speech pitch is outside its safe bound")
        cases.append(
            SpeechEvaluationCase(
                key=key,
                product=_bounded_text(raw["product"], "product", maximum=64),
                capability=_bounded_text(raw["capability"], "capability", maximum=96),
                benchmark_ref=_bounded_text(
                    raw["benchmark_ref"], "benchmark reference", maximum=120
                ),
                profile=profile,
                text=_bounded_text(raw["text"], "synthetic text", maximum=1800),
                required_terms=normalized_terms,
                speed_wpm=speed,
                pitch=pitch,
            )
        )
    keys = [item.key for item in cases]
    if len(keys) != len(set(keys)):
        raise SpeechQualificationError("speech case keys must be unique")
    return tuple(cases)


def case_contract_digest(cases: Sequence[SpeechEvaluationCase]) -> str:
    """Bind progress to every material, ordered fixture input."""

    canonical = [
        {
            "key": case.key,
            "product": case.product,
            "capability": case.capability,
            "benchmark_ref": case.benchmark_ref,
            "profile": case.profile,
            "text": case.text,
            "required_terms": list(case.required_terms),
            "speed_wpm": case.speed_wpm,
            "pitch": case.pitch,
        }
        for case in cases
    ]
    encoded = json.dumps(
        canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalized_words(value: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(value.casefold()))


def rounded_audio_seconds(value: float) -> int:
    seconds = int(
        Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    if not 1 <= seconds <= MAX_AUDIO_SECONDS:
        raise SpeechQualificationError("speech audio duration is outside its bound")
    return seconds


def _edit_distance(left: Sequence[str], right: Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_value != right_value),
                )
            )
        previous = current
    return previous[-1]


def score_transcript(
    case: SpeechEvaluationCase,
    *,
    expected_text: str,
    transcript: str,
    audio_seconds: float,
    latency_seconds: float,
) -> SpeechProfileResult:
    """Reduce an ephemeral transcript to bounded structural quality metrics."""

    expected = normalized_words(expected_text)
    observed = normalized_words(transcript)
    if not expected or not observed:
        raise SpeechQualificationError("speech transcript cannot be scored")
    sample_expected = expected[:SAMPLE_WORD_LIMIT]
    sample_observed = observed[: max(SAMPLE_WORD_LIMIT, len(sample_expected))]
    edit_distance = _edit_distance(sample_expected, sample_observed)
    word_error_rate = min(2.0, edit_distance / len(sample_expected))
    observed_text = " ".join(observed)
    recalled = sum(term in observed_text for term in case.required_terms)
    term_recall = recalled / len(case.required_terms)
    token_ratio = min(2.0, len(observed) / len(expected))
    expected_punctuation = {mark for mark in "?.!," if mark in expected_text}
    punctuation_coverage = (
        sum(mark in transcript for mark in expected_punctuation)
        / len(expected_punctuation)
        if expected_punctuation
        else 1.0
    )
    quality_passed = (
        word_error_rate <= 0.55
        and term_recall >= 0.70
        and 0.55 <= token_ratio <= 1.45
        and punctuation_coverage >= 0.50
    )
    return SpeechProfileResult(
        key=case.key,
        product=case.product,
        capability=case.capability,
        benchmark_ref=case.benchmark_ref,
        profile=case.profile,
        audio_seconds=rounded_audio_seconds(audio_seconds),
        latency_milliseconds=int(
            (Decimal(str(latency_seconds)) * 1000).quantize(Decimal("1"))
        ),
        sample_word_error_rate_milli=int(
            (Decimal(str(word_error_rate)) * 1000).quantize(Decimal("1"))
        ),
        required_term_recall_milli=int(
            (Decimal(str(term_recall)) * 1000).quantize(Decimal("1"))
        ),
        token_count_ratio_milli=int(
            (Decimal(str(token_ratio)) * 1000).quantize(Decimal("1"))
        ),
        punctuation_coverage_milli=int(
            (Decimal(str(punctuation_coverage)) * 1000).quantize(Decimal("1"))
        ),
        quality_passed=quality_passed,
    )


def progress_from_json(
    value: str,
    *,
    expected_day: date,
    expected_fixture_digest: str,
) -> SpeechProgress:
    if not _SHA256.fullmatch(expected_fixture_digest):
        raise SpeechQualificationError("expected speech fixture digest is invalid")
    if not value:
        return SpeechProgress(
            day=expected_day,
            fixture_digest=expected_fixture_digest,
            attempts={},
            results={},
        )
    if len(value) > 12_000:
        raise SpeechQualificationError("speech progress marker is outside its bound")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise SpeechQualificationError("speech progress marker is malformed") from error
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "day",
        "fixture_digest",
        "attempts",
        "results",
    }:
        raise SpeechQualificationError("speech progress marker fields are not exact")
    if payload["schema_version"] != PROGRESS_SCHEMA_VERSION:
        raise SpeechQualificationError("speech progress marker version is unsupported")
    try:
        marker_day = date.fromisoformat(payload["day"])
    except (TypeError, ValueError) as error:
        raise SpeechQualificationError("speech progress marker day is invalid") from error
    if marker_day != expected_day:
        return SpeechProgress(
            day=expected_day,
            fixture_digest=expected_fixture_digest,
            attempts={},
            results={},
        )
    fixture_digest = payload["fixture_digest"]
    if (
        not isinstance(fixture_digest, str)
        or not _SHA256.fullmatch(fixture_digest)
        or fixture_digest != expected_fixture_digest
    ):
        raise SpeechQualificationError("speech progress fixture digest does not match")
    raw_attempts = payload["attempts"]
    if not isinstance(raw_attempts, dict) or len(raw_attempts) > MAX_REQUESTS:
        raise SpeechQualificationError("speech progress attempts are malformed")
    attempts: dict[str, int] = {}
    for key, seconds in raw_attempts.items():
        if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key):
            raise SpeechQualificationError("speech progress attempt key is invalid")
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not 1 <= seconds <= MAX_AUDIO_SECONDS
        ):
            raise SpeechQualificationError("speech progress attempt is outside its bound")
        attempts[key] = seconds
    if sum(attempts.values()) > MAX_AUDIO_SECONDS:
        raise SpeechQualificationError("speech progress attempts exceed the audio ceiling")
    raw_results = payload["results"]
    if not isinstance(raw_results, dict) or len(raw_results) > MAX_REQUESTS:
        raise SpeechQualificationError("speech progress results are malformed")
    results: dict[str, SpeechProfileResult] = {}
    exact_fields = set(SpeechProfileResult.__dataclass_fields__)
    for key, raw in raw_results.items():
        if not isinstance(raw, dict) or set(raw) != exact_fields or raw.get("key") != key:
            raise SpeechQualificationError("speech progress result is malformed")
        try:
            result = SpeechProfileResult(**raw)
        except TypeError as error:
            raise SpeechQualificationError("speech progress result is invalid") from error
        numeric_bounds = {
            "audio_seconds": (1, MAX_AUDIO_SECONDS),
            "latency_milliseconds": (0, 1_800_000),
            "sample_word_error_rate_milli": (0, 2_000),
            "required_term_recall_milli": (0, 1_000),
            "token_count_ratio_milli": (0, 2_000),
            "punctuation_coverage_milli": (0, 1_000),
        }
        for field, (minimum, maximum) in numeric_bounds.items():
            number = getattr(result, field)
            if isinstance(number, bool) or not isinstance(number, int):
                raise SpeechQualificationError("speech progress metric type is invalid")
            if not minimum <= number <= maximum:
                raise SpeechQualificationError("speech progress metric is outside its bound")
        if not isinstance(result.quality_passed, bool):
            raise SpeechQualificationError("speech progress quality result is invalid")
        if not _IDENTIFIER.fullmatch(key):
            raise SpeechQualificationError("speech progress result is outside its bounds")
        _bounded_text(result.product, "progress product", maximum=64)
        _bounded_text(result.capability, "progress capability", maximum=96)
        _bounded_text(result.benchmark_ref, "progress benchmark", maximum=120)
        if result.profile not in _ALLOWED_PROFILES:
            raise SpeechQualificationError("speech progress profile is invalid")
        if attempts.get(key) != result.audio_seconds:
            raise SpeechQualificationError(
                "speech progress result has no matching bounded attempt"
            )
        results[key] = result
    progress = SpeechProgress(
        day=marker_day,
        fixture_digest=fixture_digest,
        attempts=attempts,
        results=results,
    )
    if progress.audio_seconds > MAX_AUDIO_SECONDS:
        raise SpeechQualificationError("speech progress total exceeds its audio ceiling")
    return progress


def progress_to_json(progress: SpeechProgress) -> str:
    return json.dumps(
        {
            "schema_version": PROGRESS_SCHEMA_VERSION,
            "day": progress.day.isoformat(),
            "fixture_digest": progress.fixture_digest,
            "attempts": {
                key: progress.attempts[key] for key in sorted(progress.attempts)
            },
            "results": {
                key: progress.results[key].as_dict() for key in sorted(progress.results)
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def estimated_cost_usd(
    audio_seconds: int, *, price: Decimal = PRICE_USD_PER_AUDIO_HOUR
) -> Decimal:
    return (
        Decimal(audio_seconds) / Decimal(3600) * price
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def privacy_safe_report(
    cases: Sequence[SpeechEvaluationCase],
    progress: SpeechProgress,
    *,
    mode: str,
    stop_category: str | None = None,
) -> dict[str, Any]:
    expected_keys = {item.key for item in cases}
    expected_cases = {item.key: item for item in cases}
    if progress.fixture_digest != case_contract_digest(cases):
        raise SpeechQualificationError("progress fixture digest does not match the fixture")
    attempted_keys = set(progress.attempts)
    completed_keys = set(progress.results)
    if not attempted_keys <= expected_keys or not completed_keys <= attempted_keys:
        raise SpeechQualificationError("progress contains an unknown speech case")
    for key, result in progress.results.items():
        case = expected_cases[key]
        if (
            result.product,
            result.capability,
            result.benchmark_ref,
            result.profile,
        ) != (
            case.product,
            case.capability,
            case.benchmark_ref,
            case.profile,
        ):
            raise SpeechQualificationError("progress metadata does not match the fixture")
        if progress.attempts.get(key) != result.audio_seconds:
            raise SpeechQualificationError("progress result does not match its attempt")
    audio_seconds = progress.audio_seconds
    attempted_audio_seconds = progress.attempted_audio_seconds
    if attempted_audio_seconds > MAX_AUDIO_SECONDS:
        raise SpeechQualificationError("attempted speech total exceeds its audio ceiling")
    all_complete = completed_keys == expected_keys
    spend_target_reached = (
        all_complete and TARGET_AUDIO_SECONDS <= audio_seconds <= MAX_AUDIO_SECONDS
    )
    quality_passed = all_complete and progress.all_quality_passed
    return {
        "mode": mode,
        "day": progress.day.isoformat(),
        "planned_requests": len(cases),
        "attempted_requests": len(attempted_keys),
        "completed_requests": len(completed_keys),
        "unresolved_attempts": len(attempted_keys - completed_keys),
        "audio_seconds": audio_seconds,
        "audio_hours": round(audio_seconds / 3600, 4),
        "estimated_cost_usd": float(estimated_cost_usd(audio_seconds)),
        "possible_billed_audio_seconds": attempted_audio_seconds,
        "possible_billed_audio_hours": round(attempted_audio_seconds / 3600, 4),
        "maximum_possible_cost_usd": float(
            estimated_cost_usd(attempted_audio_seconds)
        ),
        "maximum_standard_rate_cost_usd": float(
            estimated_cost_usd(
                attempted_audio_seconds,
                price=MAX_PRICE_USD_PER_AUDIO_HOUR,
            )
        ),
        "possible_spend_target_reached": (
            TARGET_AUDIO_SECONDS <= attempted_audio_seconds <= MAX_AUDIO_SECONDS
        ),
        "spend_target_reached": spend_target_reached,
        "success_marker_eligible": spend_target_reached,
        "quality_checks_passed": quality_passed,
        "stop_category": stop_category,
        "profile_results": [
            progress.results[key].as_dict() for key in sorted(progress.results)
        ],
        "limitations": [
            "Synthetic speech is a regression signal, not a human-usability study.",
            "Cost is a retail-meter estimate; Cost Management and the Startups portal remain authoritative.",
            "Possible billed audio includes every pre-recorded attempt, including timeout or persistence ambiguity.",
            "Audio and transcripts are ephemeral and are not included in this report or marker.",
        ],
    }
