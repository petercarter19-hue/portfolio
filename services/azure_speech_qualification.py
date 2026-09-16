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
PROGRESS_SCHEMA_VERSION = 3
SCORING_CONTRACT_VERSION = "english_numeric_v1"

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EVALUATION_LEXEME = re.compile(
    r"[$€£]|[+-−]?(?:\d{1,3}(?:,\d{3})+|\d+(?:[.,]\d+)+|\d+)"
    r"(?:[a-z][a-z0-9]*)?|[a-z0-9]+(?:'[a-z0-9]+)?|[.,;:?!]"
)
_LITERAL_NUMBER = re.compile(
    r"[+-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
)
_LITERAL_ORDINAL = re.compile(
    r"([+]?(?:\d{1,3}(?:,\d{3})+|\d+))(st|nd|rd|th)"
)
_CARDINAL_UNITS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_CARDINAL_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_ORDINAL_UNITS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "thirtieth": 30,
}
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_CURRENCY_SYMBOLS = {"$": "usd-dollar", "€": "eur", "£": "gbp"}
_CURRENCY_UNITS = {
    "dollar": "usd-dollar",
    "dollars": "usd-dollar",
    "cent": "usd-cent",
    "cents": "usd-cent",
    "euro": "eur",
    "euros": "eur",
    "pound": "gbp",
    "pounds": "gbp",
}
_SIGN_WORDS = {"minus": "-", "negative": "-", "plus": "+", "positive": "+"}
_UNSUPPORTED_SCALES = {"hundred", "thousand", "million", "billion", "trillion"}
_NUMERIC_SPAN_WORDS = (
    set(_CARDINAL_UNITS)
    | set(_CARDINAL_TENS)
    | set(_ORDINAL_UNITS)
    | set(_SIGN_WORDS)
    | _UNSUPPORTED_SCALES
    | {"and", "point"}
)
_TOKEN_BOUNDARIES = {".", ",", ";", ":", "?", "!"}
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
        bounded_terms = tuple(
            _bounded_text(term, "required term", maximum=48) for term in terms
        )
        normalized_terms = tuple(normalized_words(term) for term in bounded_terms)
        if any(not term for term in normalized_terms):
            raise SpeechQualificationError("required terms are malformed")
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
                required_terms=bounded_terms,
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

    canonical = {
        "scoring_contract_version": SCORING_CONTRACT_VERSION,
        "cases": [
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
        ],
    }
    encoded = json.dumps(
        canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_number(value: str) -> str:
    value = value.replace("−", "-")
    sign = "-" if value.startswith("-") else ""
    unsigned = value.lstrip("+-").replace(",", "")
    if "." in unsigned:
        whole, fraction = unsigned.split(".", 1)
        fraction = fraction.rstrip("0")
        unsigned = f"{int(whole)}.{fraction}" if fraction else str(int(whole))
    else:
        unsigned = str(int(unsigned))
    return sign + unsigned


def _expected_ordinal_suffix(value: int) -> str:
    if 10 <= value % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")


def _parse_word_number(
    tokens: Sequence[str], index: int
) -> tuple[str, int, int] | None:
    if index >= len(tokens):
        return None
    token = tokens[index]
    if token in _CARDINAL_UNITS:
        return "cardinal", _CARDINAL_UNITS[token], 1
    if token in _ORDINAL_UNITS:
        return "ordinal", _ORDINAL_UNITS[token], 1
    if token in _CARDINAL_TENS:
        value = _CARDINAL_TENS[token]
        if index + 1 < len(tokens):
            next_token = tokens[index + 1]
            if next_token in _CARDINAL_UNITS and 1 <= _CARDINAL_UNITS[next_token] <= 9:
                return "cardinal", value + _CARDINAL_UNITS[next_token], 2
            if next_token in _ORDINAL_UNITS and 1 <= _ORDINAL_UNITS[next_token] <= 9:
                return "ordinal", value + _ORDINAL_UNITS[next_token], 2
        return "cardinal", value, 1
    return None


def _parse_supported_number(
    tokens: Sequence[str], index: int
) -> tuple[str, str, int] | None:
    if index >= len(tokens):
        return None
    start = index
    word_sign = ""
    if tokens[index] in _SIGN_WORDS:
        word_sign = _SIGN_WORDS[tokens[index]]
        index += 1
        if index >= len(tokens):
            return None

    token = tokens[index]
    ordinal = _LITERAL_ORDINAL.fullmatch(token)
    if ordinal:
        if word_sign == "-":
            return None
        value = int(ordinal.group(1).lstrip("+").replace(",", "") or "0")
        if ordinal.group(2) != _expected_ordinal_suffix(value):
            return None
        consumed = index - start + 1
        if (
            start + consumed < len(tokens)
            and tokens[start + consumed] in _NUMERIC_SPAN_WORDS
        ):
            return None
        return "ordinal", str(value), consumed
    if _LITERAL_NUMBER.fullmatch(token):
        if word_sign and token.startswith(("+", "-")):
            return None
        value = _canonical_number(word_sign + token)
        consumed = index - start + 1
        if (
            start + consumed < len(tokens)
            and tokens[start + consumed] in _NUMERIC_SPAN_WORDS
        ):
            return None
        return "cardinal", value, consumed

    integer = _parse_word_number(tokens, index)
    if integer and integer[0] == "cardinal":
        _, integer_value, integer_count = integer
        point_index = index + integer_count
        if point_index < len(tokens) and tokens[point_index] == "point":
            fraction_index = point_index + 1
            fraction: list[str] = []
            while (
                fraction_index < len(tokens)
                and tokens[fraction_index] in _CARDINAL_UNITS
                and 0 <= _CARDINAL_UNITS[tokens[fraction_index]] <= 9
            ):
                fraction.append(str(_CARDINAL_UNITS[tokens[fraction_index]]))
                fraction_index += 1
            if not fraction or (
                fraction_index < len(tokens)
                and tokens[fraction_index] in _NUMERIC_SPAN_WORDS
            ):
                return None
            value = _canonical_number(
                f"{word_sign}{integer_value}.{''.join(fraction)}"
            )
            return "cardinal", value, fraction_index - start

    year = _parse_supported_year(tokens, index)
    if year is not None:
        value, count = year
        return "cardinal", _canonical_number(word_sign + value), count + index - start

    if integer:
        kind, value, count = integer
        after_number = index + count
        if (
            after_number < len(tokens)
            and tokens[after_number] in _NUMERIC_SPAN_WORDS
        ):
            return None
        if word_sign and kind == "ordinal":
            return None
        canonical = (
            _canonical_number(word_sign + str(value))
            if kind == "cardinal"
            else str(value)
        )
        return kind, canonical, after_number - start
    return None


def _parse_supported_year(
    tokens: Sequence[str], index: int
) -> tuple[str, int] | None:
    if index >= len(tokens) or tokens[index] != "twenty":
        return None
    year_tail = _parse_word_number(tokens, index + 1)
    if (
        year_tail is None
        or year_tail[0] != "cardinal"
        or not 20 <= year_tail[1] <= 99
    ):
        return None
    after_year = index + 1 + year_tail[2]
    if after_year < len(tokens) and tokens[after_year] in _NUMERIC_SPAN_WORDS:
        return None
    return str(2000 + year_tail[1]), after_year - index


def _looks_like_numeric_start(token: str) -> bool:
    return bool(
        _LITERAL_NUMBER.fullmatch(token)
        or _LITERAL_ORDINAL.fullmatch(token)
        or token in _CARDINAL_UNITS
        or token in _CARDINAL_TENS
        or token in _ORDINAL_UNITS
        or token in _SIGN_WORDS
        or token[:1].isdigit()
        or token[:1] in {"+", "-", "−"}
    )


def _opaque_numeric_span(tokens: Sequence[str], index: int) -> tuple[str, int]:
    end = index
    while end < len(tokens) and (
        tokens[end] in _NUMERIC_SPAN_WORDS
        or _LITERAL_NUMBER.fullmatch(tokens[end])
        or _LITERAL_ORDINAL.fullmatch(tokens[end])
        or tokens[end][:1].isdigit()
    ):
        end += 1
    if end == index:
        end += 1
    return "numeric-unsupported:" + "-".join(tokens[index:end]), end - index


def _date_token(tokens: Sequence[str], index: int) -> tuple[str, int] | None:
    month = _MONTHS.get(tokens[index])
    if month is None:
        return None
    day_index = index + 1
    day = _parse_supported_number(tokens, day_index)
    if day is None:
        word_day = _parse_word_number(tokens, day_index)
        if word_day is not None:
            following = day_index + word_day[2]
            if _parse_supported_year(tokens, following) is not None:
                day = word_day[0], str(word_day[1]), word_day[2]
    if day is None or "." in day[1] or day[1].startswith("-"):
        return None
    day_value = int(day[1])
    if not 1 <= day_value <= 31:
        return None
    return f"date:{month:02d}-{day_value:02d}", day[2] + 1


def _money_from_symbol(
    tokens: Sequence[str], index: int
) -> tuple[str, int] | None:
    currency = _CURRENCY_SYMBOLS.get(tokens[index])
    if currency is None:
        return None
    number = _parse_supported_number(tokens, index + 1)
    if number is None or number[0] != "cardinal":
        return None
    consumed = number[2] + 1
    following = index + consumed
    if following < len(tokens) and tokens[following] in _CURRENCY_UNITS:
        unit = _CURRENCY_UNITS[tokens[following]]
        consumed += 1
        if unit != currency:
            return f"money-conflict:{currency}:{unit}:{number[1]}", consumed
    compound = _following_currency_amount(tokens, index + consumed)
    if compound is not None:
        unit, amount, extra = compound
        return (
            f"money-unsupported-compound:{currency}:{number[1]}:{unit}:{amount}",
            consumed + extra,
        )
    return f"money:{currency}:{number[1]}", consumed


def _following_currency_amount(
    tokens: Sequence[str], index: int
) -> tuple[str, str, int] | None:
    start = index
    if index < len(tokens) and tokens[index] == "and":
        index += 1
    number = _parse_supported_number(tokens, index)
    if number is None or number[0] != "cardinal":
        return None
    unit_index = index + number[2]
    if unit_index >= len(tokens):
        return None
    unit = _CURRENCY_UNITS.get(tokens[unit_index])
    if unit is None:
        return None
    return unit, number[1], unit_index - start + 1


def _money_from_unit(
    tokens: Sequence[str], index: int, number: tuple[str, str, int]
) -> tuple[str, int] | None:
    following = index + number[2]
    if number[0] != "cardinal" or following >= len(tokens):
        return None
    currency = _CURRENCY_UNITS.get(tokens[following])
    if currency is None:
        return None
    consumed = number[2] + 1
    compound = _following_currency_amount(tokens, index + consumed)
    if compound is not None:
        unit, amount, extra = compound
        return (
            f"money-unsupported-compound:{currency}:{number[1]}:{unit}:{amount}",
            consumed + extra,
        )
    return f"money:{currency}:{number[1]}", consumed


def normalized_words(value: str) -> tuple[str, ...]:
    """Return bounded evaluation tokens, not a general natural-language parse."""

    lexemes = tuple(_EVALUATION_LEXEME.findall(value.casefold()))
    normalized: list[str] = []
    index = 0
    while index < len(lexemes):
        if lexemes[index] in _TOKEN_BOUNDARIES:
            index += 1
            continue
        date_value = _date_token(lexemes, index)
        if date_value is not None:
            token, consumed = date_value
            normalized.append(token)
            index += consumed
            continue
        money_symbol = _money_from_symbol(lexemes, index)
        if money_symbol is not None:
            token, consumed = money_symbol
            normalized.append(token)
            index += consumed
            continue
        number = _parse_supported_number(lexemes, index)
        if number is not None:
            money_unit = _money_from_unit(lexemes, index, number)
            if money_unit is not None:
                token, consumed = money_unit
                normalized.append(token)
                index += consumed
                continue
            kind, canonical, consumed = number
            normalized.append(f"{kind}:{canonical}")
            index += consumed
            continue
        if _looks_like_numeric_start(lexemes[index]):
            token, consumed = _opaque_numeric_span(lexemes, index)
            normalized.append(token)
            index += consumed
            continue
        normalized.append(lexemes[index])
        index += 1
    return tuple(normalized)


def _contains_token_sequence(
    observed: Sequence[str], required: Sequence[str]
) -> bool:
    if not required or len(required) > len(observed):
        return False
    return any(
        tuple(observed[index : index + len(required)]) == tuple(required)
        for index in range(len(observed) - len(required) + 1)
    )


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
    required_terms = tuple(normalized_words(term) for term in case.required_terms)
    recalled = sum(
        _contains_token_sequence(observed, term) for term in required_terms
    )
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
