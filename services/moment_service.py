"""Deterministic validation for private Capture-to-Moment proposals."""

from __future__ import annotations

from datetime import date


MOMENT_KINDS = (
    ("achievement", "Achievement"),
    ("decision", "Decision"),
    ("lesson", "Lesson"),
    ("progress", "Progress"),
    ("challenge", "Challenge"),
    ("question", "Question"),
    ("update", "Update"),
    ("other", "Other"),
)
MOMENT_KIND_VALUES = frozenset(value for value, _label in MOMENT_KINDS)
OCCURRED_PRECISIONS = (
    ("exact", "Exact date"),
    ("month", "Month"),
    ("year", "Year"),
    ("unknown", "Date not set"),
)
OCCURRED_PRECISION_VALUES = frozenset(
    value for value, _label in OCCURRED_PRECISIONS
)

MAX_MOMENT_TITLE_LENGTH = 160
MAX_MOMENT_NARRATIVE_LENGTH = 8000
MAX_MOMENT_WHY_LENGTH = 2000


def utf16_length(value: str) -> int:
    """Match SQL Server nvarchar and browser maxlength code-unit counting."""
    return len(value.encode("utf-16-le")) // 2


def validate_moment_proposal(form) -> tuple[dict | None, str | None]:
    """Return normalized proposal fields or a fixed member-safe error key."""
    moment_kind = form.get("moment_kind", "").strip().lower()
    title = form.get("title", "").strip()
    narrative = form.get("narrative", "").strip()
    why_it_matters = form.get("why_it_matters", "").strip() or None
    occurred_precision = form.get("occurred_precision", "").strip().lower()
    occurred_on_value = form.get("occurred_on", "").strip()

    if (
        moment_kind not in MOMENT_KIND_VALUES
        or not title
        or not narrative
        or occurred_precision not in OCCURRED_PRECISION_VALUES
    ):
        return None, "required"

    if (
        utf16_length(title) > MAX_MOMENT_TITLE_LENGTH
        or utf16_length(narrative) > MAX_MOMENT_NARRATIVE_LENGTH
        or (
            why_it_matters is not None
            and utf16_length(why_it_matters) > MAX_MOMENT_WHY_LENGTH
        )
    ):
        return None, "too-long"

    occurred_on = None
    if occurred_precision != "unknown":
        if not occurred_on_value:
            return None, "date"
        try:
            occurred_on = date.fromisoformat(occurred_on_value)
        except ValueError:
            return None, "date"

    return (
        {
            "moment_kind": moment_kind,
            "title": title,
            "occurred_on": occurred_on,
            "occurred_precision": occurred_precision,
            "narrative": narrative,
            "why_it_matters": why_it_matters,
        },
        None,
    )
