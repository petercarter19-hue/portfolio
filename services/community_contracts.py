"""Finite, reusable contracts for the owner-authored Community public pilot."""

from __future__ import annotations

import re
from uuid import UUID


POST_BODY_MAX = 4000
CONTRIBUTION_BODY_MAX = 2000
SEARCH_QUERY_MAX = 120
PAGE_SIZE_DEFAULT = 12
PAGE_SIZE_MAX = 20
FEED_WINDOW_MAX = 120
CONTRIBUTION_PAGE_SIZE = 20
CONTRIBUTION_WINDOW_MAX = 100
MAX_ATTACHMENTS = 4
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

POST_INTENTS = frozenset({"post", "question", "small_win"})
RESPONSE_POSTURES = frozenset(
    {"open_feedback", "questions_welcome", "sharing_only", "help_welcome"}
)
CONTRIBUTION_KINDS = frozenset({"comment", "reply", "author_update"})
RESPONSE_INTENTIONS = frozenset(
    {"celebrate", "support", "i_relate", "ask", "offer_help"}
)
ATTACHMENT_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "application/pdf", XLSX_CONTENT_TYPE}
)

IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
REVISION_TOKEN = re.compile(r"^[1-9][0-9]{0,9}$")


class CommunityValidationError(ValueError):
    """Safe member-facing input failure."""


class CommunityNotFoundError(LookupError):
    """Neutral missing/inaccessible source outcome."""


class CommunityConflictError(RuntimeError):
    """Authorized stale revision or idempotency conflict."""


class CommunityUnavailableError(RuntimeError):
    """Retryable database or storage dependency failure."""


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def bounded_text(value, *, field, maximum, required=True):
    if not isinstance(value, str):
        raise CommunityValidationError(f"{field} must be text.")
    cleaned = value.strip()
    if required and not cleaned:
        raise CommunityValidationError(f"{field} is required.")
    if utf16_length(cleaned) > maximum:
        raise CommunityValidationError(
            f"{field} is limited to {maximum:,} characters."
        )
    return cleaned


def enum_value(value, *, field, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise CommunityValidationError(f"{field} has an unsupported value.")
    return value


def opaque_key(value, *, field="key"):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise CommunityValidationError(f"{field} is invalid.") from error


def optional_opaque_key(value, *, field="key"):
    if value in (None, ""):
        return None
    return opaque_key(value, field=field)


def idempotency_key(value):
    if not isinstance(value, str) or not IDEMPOTENCY_KEY.fullmatch(value):
        raise CommunityValidationError("A valid idempotency key is required.")
    return value


def revision_number(value):
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 1 <= value <= 2_147_483_647
    ):
        return value
    if isinstance(value, str) and REVISION_TOKEN.fullmatch(value):
        return int(value)
    raise CommunityValidationError("A valid revision precondition is required.")


def attachment_keys(values):
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > MAX_ATTACHMENTS:
        raise CommunityValidationError(
            f"Up to {MAX_ATTACHMENTS} attachments are allowed."
        )
    normalized = [opaque_key(value, field="attachment key") for value in values]
    if len(set(normalized)) != len(normalized):
        raise CommunityValidationError("An attachment cannot be added twice.")
    return normalized


def safe_display_name(value, content_type=None):
    if not isinstance(value, str):
        raise CommunityValidationError("The attachment filename is invalid.")
    basename = value.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = re.sub(
        r"[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]",
        "",
        basename,
    ).strip(" .")
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "application/pdf": "pdf",
        XLSX_CONTENT_TYPE: "xlsx",
    }.get(content_type)
    if extension:
        stem = cleaned.rsplit(".", 1)[0].strip(" .") if "." in cleaned else cleaned
        stem = stem or "attachment"
        available_units = 180 - utf16_length(f".{extension}")
        kept = []
        used_units = 0
        for character in stem:
            character_units = utf16_length(character)
            if used_units + character_units > available_units:
                break
            kept.append(character)
            used_units += character_units
        cleaned = f"{''.join(kept) or 'attachment'}.{extension}"
    if not cleaned or utf16_length(cleaned) > 180:
        raise CommunityValidationError("The attachment filename is invalid.")
    return cleaned


def safe_search_query(value):
    cleaned = bounded_text(
        value, field="Search", maximum=SEARCH_QUERY_MAX, required=True
    )
    if len(cleaned) < 2:
        raise CommunityValidationError("Enter at least two characters.")
    return cleaned
