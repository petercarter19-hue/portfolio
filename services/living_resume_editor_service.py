"""Private, owner-scoped Living Resume editor commands.

The browser supplies a closed command vocabulary and opaque record keys.  It
never supplies an owner, table name, visibility, approval, or publication
state.  SQL resolves the authenticated owner and performs the whole command
and receipt write atomically.

Published or history-bearing records stay blocked here
(``blocked_reason=published_or_history_bearing``). Overlay edits for those
records belong to ``ResumeDraftService`` and must not change already-shared
facts. Never-published private records may still use these commands where
the guards allow.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date
from calendar import monthrange
from urllib.parse import urlparse
from uuid import UUID

from services.database_service import DatabaseServiceError, database_service


EDITOR_SECTIONS = ("profile", "roles", "accomplishments", "skills", "credentials", "education")
SECTION_RECORD_TYPES = {
    "roles": "role",
    "accomplishments": "accomplishment",
    "skills": "skill",
    "credentials": "credential",
    "education": "education",
}


def save_mode_for_record(row: Mapping[str, object] | object) -> str:
    """Canonical commands vs draft overlay. Does not publish or grant access."""

    if not isinstance(row, Mapping):
        return "draft_overlay"
    if row.get("editable") is True:
        return "canonical"
    return "draft_overlay"


COMMAND_TYPES = frozenset(
    f"{operation}_{record_type}"
    for operation in ("create", "update", "remove")
    for record_type in ("role", "accomplishment", "skill", "credential", "education")
)
DATE_PRECISIONS = frozenset({"day", "month", "year", "unknown"})
EMPLOYMENT_TYPES = frozenset(
    {
        "full_time",
        "part_time",
        "contract",
        "freelance",
        "internship",
        "volunteer",
        "military",
        "other",
    }
)
CREDENTIAL_STATUSES = frozenset({"planned", "in_progress", "completed"})
CREDENTIAL_PRECISION_FIELDS = frozenset({'issue_date_precision', 'expiration_date_precision'})
CREDENTIAL_PRECISION_UNAVAILABLE = ('This storage does not support credential date precision yet. '
    'Your input is kept. Use the private local workspace or keep this suggestion for later; do not invent an exact day.')

# Education uses the existing canonical chapter precision/status vocabulary.
EDUCATION_DATE_PRECISIONS = DATE_PRECISIONS | {"approximate"}
EDUCATION_STATUSES = frozenset({"planned", "admitted", "in_progress", "completed", "paused", "withdrawn"})
_EDUCATION_FIELDS = frozenset({
    "title", "institution_name", "degree_name", "field_of_study", "education_status",
    "grade_text", "location_text", "summary", "start_date", "end_date", "date_precision",
})

_ENVELOPE_FIELDS = frozenset(
    {"command_id", "type", "record_key", "parent_key", "expected_version", "values"}
)
_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SUCCESS_FIELDS = frozenset(
    {
        "committed",
        "error_code",
        "command_id",
        "request_digest",
        "command_type",
        "record_key",
        "outcome",
        "record_version",
        "replayed",
    }
)

_ROLE_FIELDS = frozenset(
    {
        "role_title",
        "employer_name",
        "location_text",
        "summary",
        "start_date",
        "end_date",
        "date_precision",
        "employment_type",
        "current_role",
    }
)
_ACCOMPLISHMENT_FIELDS = frozenset({"wording", "metric_value", "metric_label"})
_SKILL_FIELDS = frozenset({"name", "summary"})
_CREDENTIAL_FIELDS = frozenset(
    {
        "name",
        "issuer",
        "identifier",
        "issue_date",
        "expiration_date",
        "issue_date_precision",
        "expiration_date_precision",
        "verification_url",
        "completion_status",
        "qualification_kind",
    }
)

QUALIFICATION_KINDS = frozenset({"certification", "license", "publication", "membership"})
PROJECT_CATEGORIES = frozenset({"software", "research", "community_volunteer", "business_product", "creative_design", "other"})
LOCAL_QUALIFICATION_UNAVAILABLE = "This storage does not support qualification kinds yet. Your input is kept."
_PROJECT_FIELDS = frozenset({"project_name", "summary", "project_category", "organization_name", "project_role",
    "project_status", "location_text", "start_date", "end_date", "date_precision", "project_url", "additional_project_urls"})
PROJECT_EDITOR_FIELDS = _PROJECT_FIELDS

_EDITOR_ROW_FIELDS = {
    "education": _EDUCATION_FIELDS | {"record_key", "row_version", "editable", "blocked_reason"},
    "profile": frozenset({"profile_key", "profile_slug", "display_name"}),
    "roles": frozenset(
        {
            "record_key",
            "role_title",
            "employer_name",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
            "employment_type",
            "current_role",
            "row_version",
            "editable",
            "blocked_reason",
        }
    ),
    "accomplishments": frozenset(
        {
            "record_key",
            "parent_key",
            "wording",
            "metric_value",
            "metric_label",
            "row_version",
            "editable",
            "blocked_reason",
        }
    ),
    "skills": frozenset(
        {
            "record_key",
            "name",
            "summary",
            "row_version",
            "editable",
            "blocked_reason",
        }
    ),
    "credentials": frozenset(
        {
            "record_key",
            "name",
            "issuer",
            "identifier",
            "issue_date",
            "expiration_date",
            "verification_url",
            "completion_status",
            "row_version",
            "editable",
            "blocked_reason",
        }
    ),
}


class LivingResumeEditorError(RuntimeError):
    """Stable error boundary for the private editor API."""

    def __init__(self, message: str, *, code: str, current: object = None) -> None:
        super().__init__(message)
        self.code = code
        self.current = current


class LivingResumeEditorValidationError(LivingResumeEditorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid")


class LivingResumeEditorNotFoundError(LivingResumeEditorError):
    def __init__(self, message: str = "Living Resume record not found.") -> None:
        super().__init__(message, code="not_found")


class LivingResumeEditorConflictError(LivingResumeEditorError):
    pass


class LivingResumeEditorUnavailableError(LivingResumeEditorError):
    def __init__(self) -> None:
        super().__init__("Living Resume editing is temporarily unavailable.", code="unavailable")


def utf16_length(value: str) -> int:
    """Count SQL Server nvarchar code units rather than Python code points."""

    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError as error:
        raise LivingResumeEditorValidationError(
            "Text contains unsupported Unicode."
        ) from error


def _exact_uuid(value: object, label: str, *, version: int | None = None) -> str:
    if not isinstance(value, str):
        raise LivingResumeEditorValidationError(f"{label} must be a canonical UUID.")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise LivingResumeEditorValidationError(f"{label} must be a canonical UUID.") from error
    if str(parsed) != value or (version is not None and parsed.version != version):
        raise LivingResumeEditorValidationError(f"{label} must be a canonical UUID.")
    return value


def _text(values: Mapping[str, object], name: str, maximum: int, *, required: bool = False):
    value = values.get(name)
    if value is None:
        if required:
            raise LivingResumeEditorValidationError(f"{name} is required.")
        return None
    if not isinstance(value, str):
        raise LivingResumeEditorValidationError(f"{name} must be text.")
    value = value.strip()
    if required and not value:
        raise LivingResumeEditorValidationError(f"{name} is required.")
    if utf16_length(value) > maximum:
        raise LivingResumeEditorValidationError(f"{name} is too long.")
    return value or None


def _choice(values: Mapping[str, object], name: str, choices: frozenset[str], *, required=False):
    value = _text(values, name, 30, required=required)
    if value is not None and value not in choices:
        raise LivingResumeEditorValidationError(f"{name} has an unsupported value.")
    return value


def _boolean(values: Mapping[str, object], name: str, *, default: bool = False) -> bool:
    value = values.get(name, default)
    if not isinstance(value, bool):
        raise LivingResumeEditorValidationError(f"{name} must be true or false.")
    return value


def _date_value(values: Mapping[str, object], name: str) -> date | None:
    value = values.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LivingResumeEditorValidationError(f"{name} must use YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise LivingResumeEditorValidationError(f"{name} must use YYYY-MM-DD.") from error
    if parsed.isoformat() != value:
        raise LivingResumeEditorValidationError(f"{name} must use YYYY-MM-DD.")
    return parsed


def _normalized_date(value: date | None, precision: str | None) -> str | None:
    if value is None:
        return None
    if precision == "year":
        value = value.replace(month=1, day=1)
    elif precision == "month":
        value = value.replace(day=1)
    return value.isoformat()


def _validate_exact_fields(values: object, expected: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(values, Mapping):
        raise LivingResumeEditorValidationError("values must be an object.")
    unknown = set(values) - expected
    if unknown:
        raise LivingResumeEditorValidationError("values contains unsupported fields.")
    return values


def _role_values(raw: object, *, require_employer: bool = True) -> dict[str, object]:
    values = _validate_exact_fields(raw, _ROLE_FIELDS)
    precision = _choice(values, "date_precision", DATE_PRECISIONS) or "unknown"
    start = _date_value(values, "start_date")
    end = _date_value(values, "end_date")
    current = _boolean(values, "current_role")
    if end is not None and start is None:
        raise LivingResumeEditorValidationError("start_date is required when end_date is set.")
    if start is not None and end is not None and start > end:
        raise LivingResumeEditorValidationError("end_date cannot be before start_date.")
    if current and end is not None:
        raise LivingResumeEditorValidationError("A current role cannot have an end_date.")
    return {
        "role_title": _text(values, "role_title", 300, required=True),
        "employer_name": _text(values, "employer_name", 300, required=require_employer),
        "location_text": _text(values, "location_text", 300),
        "summary": _text(values, "summary", 8000),
        "start_date": _normalized_date(start, precision),
        "end_date": _normalized_date(end, precision),
        "date_precision": precision,
        "employment_type": _choice(values, "employment_type", EMPLOYMENT_TYPES),
        "current_role": current,
    }


def _accomplishment_values(raw: object) -> dict[str, object]:
    values = _validate_exact_fields(raw, _ACCOMPLISHMENT_FIELDS)
    return {
        "wording": _text(values, "wording", 8000, required=True),
        "metric_value": _text(values, "metric_value", 100),
        "metric_label": _text(values, "metric_label", 300),
    }


def _skill_values(raw: object) -> dict[str, object]:
    values = _validate_exact_fields(raw, _SKILL_FIELDS)
    return {
        "name": _text(values, "name", 200, required=True),
        "summary": _text(values, "summary", 8000),
    }


def credential_date_text(value, precision=None):
    """Validate and project a copy to supplied precision; legacy ISO stays exact."""
    if value is None:
        return None
    if not isinstance(value, str) or len(value) not in {4, 7, 10}:
        raise LivingResumeEditorValidationError('Invalid credential date.')
    precision = precision or {4: 'year', 7: 'month', 10: 'day'}.get(len(value))
    if precision not in {'year', 'month', 'day'}:
        raise LivingResumeEditorValidationError('Invalid credential date detail.')
    if len(value) < 10 and {4: 'year', 7: 'month'}[len(value)] != precision:
        raise LivingResumeEditorValidationError('Credential date does not match its supplied detail.')
    # Partial strings occur only in the read-only local evidence projection.
    padded = value + ('-01-01' if len(value) == 4 else '-01' if len(value) == 7 else '')
    parsed = _date_value({'date': padded}, 'date')
    if parsed is None: raise LivingResumeEditorValidationError('Invalid credential date.')
    if (precision == 'year' and (parsed.month, parsed.day) != (1, 1)
            or precision == 'month' and parsed.day != 1):
        raise LivingResumeEditorValidationError('Credential date does not match its supplied detail.')
    return parsed.isoformat()[:{'year': 4, 'month': 7, 'day': 10}[precision]]


def _credential_upper(value, precision):
    if precision == 'year': return date(value.year, 12, 31)
    if precision == 'month': return date(value.year, value.month, monthrange(value.year, value.month)[1])
    return value


def _credential_values(raw: object) -> dict[str, object]:
    values = _validate_exact_fields(raw, _CREDENTIAL_FIELDS)
    kind = _choice(values, "qualification_kind", QUALIFICATION_KINDS)
    status = _choice(values, "completion_status", CREDENTIAL_STATUSES, required=True)
    issue = _date_value(values, "issue_date")
    expiration = _date_value(values, "expiration_date")
    precisions = {}
    for name, parsed in (('issue_date', issue), ('expiration_date', expiration)):
        precision = _choice(values, name + '_precision', {'year', 'month', 'day'})
        if precision and parsed is None:
            raise LivingResumeEditorValidationError('Credential date detail needs its date.')
        if parsed:
            credential_date_text(parsed.isoformat(), precision)
        if precision in {'year', 'month'}: precisions[name + '_precision'] = precision
    if status in {"planned", "in_progress"} and (issue is not None or expiration is not None):
        raise LivingResumeEditorValidationError(
            "planned and in_progress credentials cannot have issue or expiration dates."
        )
    if status == "completed" and issue is None:
        raise LivingResumeEditorValidationError("A completed credential requires issue_date.")
    if issue is not None and expiration is not None and _credential_upper(
            expiration, precisions.get('expiration_date_precision')) < issue:
        raise LivingResumeEditorValidationError("expiration_date cannot be before issue_date.")
    verification_url = _text(values, "verification_url", 1000)
    if verification_url is not None:
        try:
            parsed = urlparse(verification_url)
        except ValueError as error:
            raise LivingResumeEditorValidationError(
                "verification_url must use http or https."
            ) from error
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise LivingResumeEditorValidationError("verification_url must use http or https.")
    return {
        "name": _text(values, "name", 300, required=kind != "membership"),
        "issuer": _text(values, "issuer", 300, required=True),
        "identifier": _text(values, "identifier", 300),
        "issue_date": issue.isoformat() if issue else None,
        "expiration_date": expiration.isoformat() if expiration else None,
        "verification_url": verification_url,
        "completion_status": status,
        **precisions,
        **({"qualification_kind": kind} if "qualification_kind" in values else {}),
    }


def _education_values(raw: object, *, require_title: bool = True) -> dict[str, object]:
    values = _validate_exact_fields(raw, _EDUCATION_FIELDS)
    precision = _choice(values, "date_precision", EDUCATION_DATE_PRECISIONS) or "unknown"
    start = _date_value(values, "start_date")
    end = _date_value(values, "end_date")
    # Unlike role commands, the canonical education contract allows end-only dates.
    if start is not None and end is not None and start > end:
        raise LivingResumeEditorValidationError("end_date cannot be before start_date.")
    return {
        "title": _text(values, "title", 300, required=require_title),
        "institution_name": _text(values, "institution_name", 300, required=True),
        "degree_name": _text(values, "degree_name", 300),
        "field_of_study": _text(values, "field_of_study", 300),
        "education_status": _choice(values, "education_status", EDUCATION_STATUSES, required=True),
        "grade_text": _text(values, "grade_text", 100),
        "location_text": _text(values, "location_text", 300),
        "summary": _text(values, "summary", 8000),
        "start_date": _normalized_date(start, precision),
        "end_date": _normalized_date(end, precision),
        "date_precision": precision,
    }


def _project_links(values):
    first = _text(values, "project_url", 1000)
    supplied = values.get("additional_project_urls")
    if supplied is None:
        supplied = []
    if type(supplied) is not list:
        raise LivingResumeEditorValidationError("additional_project_urls must be a list of links.")
    extra = [_text({"link": value}, "link", 1000) for value in supplied]
    extra = [value for value in extra if value is not None]
    if len(extra) > 2:
        raise LivingResumeEditorValidationError("A project can have at most three links.")
    seen = set()
    for value in ([first] if first else []) + extra:
        try:
            parsed = urlparse(value)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                    or parsed.password is not None or re.search(r"[\s\x00-\x1f\x7f]", value)):
                raise ValueError("unsafe link")
            identity = (parsed.hostname.lower(), parsed.port or 443, parsed.path or "/", parsed.query, parsed.fragment)
        except ValueError as error:
            raise LivingResumeEditorValidationError("Project links must use HTTPS with a host and no sign-in details.") from error
        if identity in seen:
            raise LivingResumeEditorValidationError("Project links must be unique.")
        seen.add(identity)
    return first, extra


def _project_values(raw: object) -> dict[str, object]:
    values = _validate_exact_fields(raw, _PROJECT_FIELDS)
    name = _text(values, "project_name", 300, required=True)
    summary = _text(values, "summary", 8000, required=True)
    if len(summary.splitlines()) != 1:
        raise LivingResumeEditorValidationError("Use a one-line project description. Your wording is kept.")
    category = _choice(values, "project_category", PROJECT_CATEGORIES)
    precision = _choice(values, "date_precision", EDUCATION_DATE_PRECISIONS) or "unknown"
    start, end = _date_value(values, "start_date"), _date_value(values, "end_date")
    if start is not None and end is not None and start > end:
        raise LivingResumeEditorValidationError("end_date cannot be before start_date.")
    first, extra = _project_links(values)
    result = {"project_name": name, "summary": summary}
    if "project_category" in values:
        result["project_category"] = category
    for field in ("organization_name", "project_role", "project_status", "location_text"):
        if field in values:
            result[field] = _text(values, field, 300)
    for field, parsed in (("start_date", start), ("end_date", end)):
        if field in values:
            result[field] = _normalized_date(parsed, precision)
    if start is not None or end is not None:
        result["date_precision"] = precision
    elif "date_precision" in values:
        result["date_precision"] = "unknown"
    if "project_url" in values:
        result["project_url"] = first
    if "additional_project_urls" in values:
        result["additional_project_urls"] = extra
    return result


_VALUE_VALIDATORS = {
    "education": _education_values,
    "role": _role_values,
    "accomplishment": _accomplishment_values,
    "skill": _skill_values,
    "credential": _credential_values,
    "project": _project_values,
}


def normalize_editor_values(record_type: str, values: object, *, require_title: bool = True) -> dict[str, object]:
    """Validate closed editor field sets for draft overlay reuse."""

    validator = _VALUE_VALIDATORS.get(record_type)
    if validator is None:
        raise LivingResumeEditorValidationError("canonical_type has an unsupported value.")
    return validator(values, require_title=require_title) if record_type == "education" else validator(values)


class GuideRequiredFieldsError(LivingResumeEditorValidationError):
    code = "missing_required_fields"

    def __init__(self, fields):
        self.missing_required_fields = list(fields)
        super().__init__("Add the required details before saving. Your input is kept.")
        self.code = "missing_required_fields"


class GuideTextLimitError(LivingResumeEditorValidationError):
    def __init__(self, code, actual_count, limit):
        self.actual_count, self.limit = actual_count, limit
        super().__init__(f"This text has {actual_count}; the limit is {limit}. Your original words are kept.")
        self.code = code


def guide_required_fields(record_type, values, *, section=None):
    """One Guide essentials policy; generic private editor behavior stays separate."""
    if not isinstance(values, Mapping):
        raise LivingResumeEditorValidationError("values must be an object.")
    if record_type == "credential":
        kind = values.get("qualification_kind") or "certification"
        if kind not in QUALIFICATION_KINDS:
            raise LivingResumeEditorValidationError("qualification_kind has an unsupported value.")
        fields = ("issuer",) if kind == "membership" else ("name", "issuer")
        if values.get("completion_status") not in ("planned", "in_progress"):
            fields += ("issue_date",)
    else:
        fields = {"education": ("institution_name", "end_date"), "project": ("project_name", "summary"),
            "skill": ("name",), "role": ("role_title",), "accomplishment": ("wording",),
            "knowledge": ("title",)}.get(record_type)
        if fields is None:
            raise LivingResumeEditorValidationError("This entry type is not supported by the Guide.")
    if record_type == "knowledge":
        from services.resume_publication_projection import resume_section_for
        actual = resume_section_for("knowledge", values, presentation_section=section, proposed=True)
        if actual in {"impact_statement", "story", "looking_ahead", "contact"} or values.get("title") == "My Story":
            fields = ("title", "wording")
    return [field for field in fields if not isinstance(values.get(field), str) or not values[field].strip()]


def _guide_date_input(values, field, precision_field):
    raw = values.get(field)
    if raw is None or raw == "":
        return
    if not isinstance(raw, str):
        raise LivingResumeEditorValidationError(f"{field} must be a date or year.")
    raw = raw.strip()
    inferred = "year" if re.fullmatch(r"\d{4}", raw) else "month" if re.fullmatch(r"\d{4}-\d{2}", raw) else None
    if inferred:
        supplied = values.get(precision_field)
        if supplied not in {None, inferred}:
            raise LivingResumeEditorValidationError("The date and its detail do not agree. Your input is kept.")
        raw += "-01-01" if inferred == "year" else "-01"
        values[precision_field] = inferred
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as error:
        raise LivingResumeEditorValidationError(f"{field} is not a valid date or year.") from error
    values[field] = _normalized_date(parsed, values.get(precision_field))


def validate_guide_text_limits(values, *, section=None):
    """One non-mutating bound for named Resume text on every saving path."""
    from services.resume_publication_projection import resume_section_for
    words = values.get("wording")
    if not isinstance(words, str):
        return  # Required-field/type validation remains with its existing validator.
    actual = resume_section_for("knowledge", values)
    if (actual == "impact_statement" or section in {"impact_statement", "Professional summary"}) and len(words.split()) > 70:
        raise GuideTextLimitError("impact_statement_too_long", len(words.split()), 70)
    if (actual == "looking_ahead" or section in {"looking_ahead", "Looking Ahead"}) and utf16_length(words) > 120:
        raise GuideTextLimitError("looking_ahead_too_long", utf16_length(words), 120)


def normalize_guide_values(record_type, raw, *, section=None):
    """Validate an explicit Guide save; do not shorten, save or publish anything."""
    missing = guide_required_fields(record_type, raw, section=section)
    if missing:
        raise GuideRequiredFieldsError(missing)
    values = dict(raw)
    if record_type == "credential":
        for field in ("issue_date", "expiration_date"):
            _guide_date_input(values, field, field + "_precision")
        if values.get("completion_status") is None:
            values["completion_status"] = "completed"
    elif record_type in {"education", "project", "role"}:
        for field in ("start_date", "end_date"):
            _guide_date_input(values, field, "date_precision")
        if record_type == "education" and values.get("education_status") is None:
            values["education_status"] = "in_progress" if int(values["end_date"][:4]) > date.today().year else "completed"
    if record_type == "knowledge":
        from services.knowledge_service import (
            CLASSIFICATIONS, MAX_TITLE_UNITS, MAX_WORDING_UNITS,
            validate_knowledge_item_input, KnowledgeServiceError)
        values = _validate_exact_fields(values, frozenset({"title", "wording", "classification"}))
        title = _text(values, "title", MAX_TITLE_UNITS, required=True)
        wording = _text(values, "wording", MAX_WORDING_UNITS)
        classification = values.get("classification", "personal")
        if not isinstance(classification, str) or classification not in CLASSIFICATIONS:
            raise LivingResumeEditorValidationError("Classification is invalid.")
        validate_guide_text_limits(values, section=section)
        if wording is not None:
            try:
                title, wording, classification = validate_knowledge_item_input(title, wording, classification)
            except KnowledgeServiceError as error:
                raise LivingResumeEditorValidationError(str(error)) from error
        return {"title": title, "wording": wording, "classification": classification}
    if record_type == "role":
        return _role_values(values, require_employer=False)
    return normalize_editor_values(record_type, values, require_title=False)


def normalize_editor_intent(record_type: str, values: object) -> dict[str, object]:
    """Normalize only fields the member supplied, without inventing defaults.

    Intake matches a partial command before it knows whether the command will
    create a record or propose a change. Required and cross-field rules are
    enforced later against the complete create or merged-change payload. This
    helper still applies the canonical vocabulary, scalar types, lengths, date
    syntax, and enum choices to every supplied field.
    """

    expected = {
        "role": _ROLE_FIELDS,
        "education": _EDUCATION_FIELDS,
        "credential": _CREDENTIAL_FIELDS,
        "skill": _SKILL_FIELDS,
        "accomplishment": _ACCOMPLISHMENT_FIELDS,
        "project": _PROJECT_FIELDS,
    }.get(record_type)
    if expected is None:
        raise LivingResumeEditorValidationError("canonical_type has an unsupported value.")
    supplied = _validate_exact_fields(values, expected)
    text_limits = {
        "role_title": 300,
        "employer_name": 300,
        "location_text": 300,
        "summary": 8000,
        "degree_name": 300,
        "field_of_study": 300,
        "grade_text": 100,
        "title": 300,
        "institution_name": 300,
        "name": 300 if record_type == "credential" else 200,
        "issuer": 300,
        "identifier": 300,
        "verification_url": 1000,
        "wording": 8000,
        "metric_value": 100,
        "metric_label": 300,
        "project_name": 300,
        "project_role": 300,
        "project_status": 300,
        "organization_name": 300,
        "project_url": 1000,
    }
    normalized: dict[str, object] = {}
    for name in supplied:
        if name == "current_role":
            normalized[name] = _boolean(supplied, name)
        elif name in {"start_date", "end_date", "issue_date", "expiration_date"}:
            parsed = _date_value(supplied, name)
            normalized[name] = parsed.isoformat() if parsed else None
        elif name in CREDENTIAL_PRECISION_FIELDS:
            normalized[name] = _choice(supplied, name, {'year', 'month', 'day'})
        elif name == "date_precision":
            choices = EDUCATION_DATE_PRECISIONS if record_type == "education" else DATE_PRECISIONS
            normalized[name] = _choice(supplied, name, choices)
        elif name == "employment_type":
            normalized[name] = _choice(supplied, name, EMPLOYMENT_TYPES)
        elif name == "education_status":
            normalized[name] = _choice(supplied, name, EDUCATION_STATUSES, required=True)
        elif name == "completion_status":
            normalized[name] = _choice(supplied, name, CREDENTIAL_STATUSES, required=True)
        elif name == "qualification_kind":
            normalized[name] = _choice(supplied, name, QUALIFICATION_KINDS)
        elif name == "project_category":
            normalized[name] = _choice(supplied, name, PROJECT_CATEGORIES)
        elif name == "additional_project_urls":
            _, normalized[name] = _project_links({name: supplied[name]})
        elif name == "project_url":
            normalized[name], _ = _project_links({name: supplied[name]})
        else:
            normalized[name] = _text(supplied, name, text_limits[name])
    return normalized


def normalize_command(payload: object) -> tuple[dict[str, object], str, str]:
    if not isinstance(payload, Mapping) or set(payload) - _ENVELOPE_FIELDS:
        raise LivingResumeEditorValidationError("The command contains unsupported fields.")
    command_id = _exact_uuid(payload.get("command_id"), "command_id", version=4)
    command_type = payload.get("type")
    if not isinstance(command_type, str) or command_type not in COMMAND_TYPES:
        raise LivingResumeEditorValidationError("type has an unsupported value.")
    operation, record_type = command_type.split("_", 1)
    record_key = _exact_uuid(payload.get("record_key"), "record_key")

    parent_key = payload.get("parent_key")
    if operation == "create" and record_type == "accomplishment":
        parent_key = _exact_uuid(parent_key, "parent_key")
    elif parent_key is not None:
        raise LivingResumeEditorValidationError("parent_key is not allowed for this command.")

    expected_version = payload.get("expected_version")
    if operation == "create":
        if expected_version is not None:
            raise LivingResumeEditorValidationError("expected_version is not allowed for create.")
    elif not isinstance(expected_version, str) or not _VERSION_TOKEN.fullmatch(expected_version):
        raise LivingResumeEditorValidationError("expected_version must be a 16-character version token.")
    else:
        expected_version = expected_version.lower()

    raw_values = payload.get("values")
    if operation == "remove":
        if raw_values != {}:
            raise LivingResumeEditorValidationError("remove values must be an empty object.")
        values: dict[str, object] = {}
    else:
        values = _VALUE_VALIDATORS[record_type](raw_values)

    normalized = {
        "command_id": command_id,
        "type": command_type,
        "record_key": record_key,
        "parent_key": parent_key,
        "expected_version": expected_version,
        "values": values,
    }
    command_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(command_json.encode("utf-16-le")).hexdigest()
    return normalized, command_json, digest


def _bit(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    raise LivingResumeEditorUnavailableError()


def _version(value: object, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        value = value.hex()
    if not isinstance(value, str) or not _VERSION_TOKEN.fullmatch(value):
        raise LivingResumeEditorUnavailableError()
    return value.lower()


def _database_uuid(value: object) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise LivingResumeEditorUnavailableError() from error


class LivingResumeEditorService:
    def __init__(self, executor=database_service) -> None:
        self._executor = executor

    @staticmethod
    def _user_key(user_key: object) -> str:
        if not isinstance(user_key, str) or not user_key.strip() or utf16_length(user_key.strip()) > 300:
            raise LivingResumeEditorNotFoundError()
        return user_key.strip()

    @staticmethod
    def _translate_database_error(error: DatabaseServiceError):
        detail = str(error.__cause__ or "")
        if "RESUME_EDITOR_NOT_FOUND" in detail:
            raise LivingResumeEditorNotFoundError() from error
        if "RESUME_EDITOR_PROTECTED" in detail:
            raise LivingResumeEditorConflictError(
                "Published or history-bearing records cannot be changed here.", code="protected"
            ) from error
        if "RESUME_EDITOR_IDEMPOTENCY_CONFLICT" in detail:
            raise LivingResumeEditorConflictError(
                "That command_id was already used for different content.",
                code="idempotency_conflict",
            ) from error
        if "RESUME_EDITOR_VALIDATION" in detail:
            raise LivingResumeEditorValidationError("The command was rejected.") from error
        raise LivingResumeEditorUnavailableError() from error

    def get_editor(self, user_key: object) -> dict[str, object]:
        clean_user_key = self._user_key(user_key)
        try:
            result_sets = self._executor.execute_procedure(
                "usp_GetOwnerLivingResumeEditor", (("@UserKey", clean_user_key),)
            )
        except DatabaseServiceError as error:
            self._translate_database_error(error)
        if not isinstance(result_sets, list) or len(result_sets) != len(EDITOR_SECTIONS):
            raise LivingResumeEditorUnavailableError()
        editor: dict[str, object] = {}
        for index, section in enumerate(EDITOR_SECTIONS):
            rows = result_sets[index]
            if not isinstance(rows, list):
                raise LivingResumeEditorUnavailableError()
            if section == "profile" and len(rows) != 1:
                raise LivingResumeEditorUnavailableError()
            serialized = [self._serialize_editor_row(section, row) for row in rows]
            editor[section] = serialized[0] if section == "profile" else serialized
        editor["capabilities"] = {
            "commands": sorted(COMMAND_TYPES),
            "credential_completion_statuses": sorted(CREDENTIAL_STATUSES),
            "education_statuses": sorted(EDUCATION_STATUSES),
            "education_date_precisions": sorted(EDUCATION_DATE_PRECISIONS),
            "date_precisions": sorted(DATE_PRECISIONS),
            "employment_types": sorted(EMPLOYMENT_TYPES),
            "published_records_use_draft_overlay": True,
            "canonical_commands_do_not_publish": True,
        }
        return editor

    @staticmethod
    def _serialize_editor_row(section: str, row: object) -> dict[str, object]:
        if not isinstance(row, Mapping) or set(row) != _EDITOR_ROW_FIELDS[section]:
            raise LivingResumeEditorUnavailableError()
        output = dict(row)
        for key in ("profile_key", "record_key", "parent_key"):
            if key in output and output[key] is not None:
                output[key] = _database_uuid(output[key])
        if "row_version" in output:
            output["row_version"] = _version(output["row_version"])
            output["editable"] = _bit(output["editable"])
            if output["editable"] and output["blocked_reason"] is not None:
                raise LivingResumeEditorUnavailableError()
            if not output["editable"] and output["blocked_reason"] != "published_or_history_bearing":
                raise LivingResumeEditorUnavailableError()
            output["save_mode"] = save_mode_for_record(output)
        if "current_role" in output:
            output["current_role"] = _bit(output["current_role"])
        for key in ("start_date", "end_date", "issue_date", "expiration_date"):
            if key not in output or output[key] is None:
                continue
            if isinstance(output[key], date):
                output[key] = output[key].isoformat()
                continue
            if not isinstance(output[key], str):
                raise LivingResumeEditorUnavailableError()
            try:
                parsed = date.fromisoformat(output[key])
            except ValueError as error:
                raise LivingResumeEditorUnavailableError() from error
            if parsed.isoformat() != output[key]:
                raise LivingResumeEditorUnavailableError()
        if section == "credentials" and output["completion_status"] not in CREDENTIAL_STATUSES | {None}:
            raise LivingResumeEditorUnavailableError()
        if section == "education" and (
            not isinstance(output["education_status"], str)
            or output["education_status"] not in EDUCATION_STATUSES
            or not isinstance(output["date_precision"], str)
            or output["date_precision"] not in EDUCATION_DATE_PRECISIONS
        ):
            raise LivingResumeEditorUnavailableError()
        return output

    @staticmethod
    def _record_from_editor(editor: Mapping[str, object], command_type: str, record_key: str):
        record_type = command_type.split("_", 1)[1]
        section = {
            "role": "roles",
            "accomplishment": "accomplishments",
            "skill": "skills",
            "credential": "credentials",
            "education": "education",
        }[record_type]
        rows = editor.get(section)
        if not isinstance(rows, list):
            raise LivingResumeEditorUnavailableError()
        return next((row for row in rows if row.get("record_key") == record_key), None)

    def commit(self, user_key: object, payload: object) -> dict[str, object]:
        clean_user_key = self._user_key(user_key)
        normalized, command_json, expected_digest = normalize_command(payload)
        if "qualification_kind" in normalized["values"]:
            raise LivingResumeEditorValidationError(LOCAL_QUALIFICATION_UNAVAILABLE)
        if CREDENTIAL_PRECISION_FIELDS & set(normalized['values']):
            raise LivingResumeEditorValidationError(CREDENTIAL_PRECISION_UNAVAILABLE)
        try:
            result_sets = self._executor.execute_procedure(
                "usp_CommitLivingResumeCommandForOwner",
                (
                    ("@UserKey", clean_user_key),
                    ("@CommandId", normalized["command_id"]),
                    ("@CommandJson", command_json),
                ),
            )
        except DatabaseServiceError as error:
            self._translate_database_error(error)
        if (
            not isinstance(result_sets, list)
            or len(result_sets) != 1
            or not isinstance(result_sets[0], list)
            or len(result_sets[0]) != 1
        ):
            raise LivingResumeEditorUnavailableError()
        row = result_sets[0][0]
        if not isinstance(row, Mapping) or set(row) != _SUCCESS_FIELDS:
            raise LivingResumeEditorUnavailableError()
        committed = _bit(row["committed"])
        error_code = row["error_code"]
        if not committed:
            if error_code != "changed":
                raise LivingResumeEditorUnavailableError()
            editor = self.get_editor(clean_user_key)
            current = self._record_from_editor(
                editor, normalized["type"], normalized["record_key"]
            )
            raise LivingResumeEditorConflictError(
                "That record changed before this command.", code="changed", current=current
            )
        if error_code is not None:
            raise LivingResumeEditorUnavailableError()

        returned_digest = row["request_digest"]
        returned_command_id = _database_uuid(row["command_id"])
        returned_type = row["command_type"]
        returned_key = _database_uuid(row["record_key"])
        outcome = row["outcome"]
        if (
            returned_digest != expected_digest
            or returned_command_id != normalized["command_id"]
            or returned_type != normalized["type"]
            or returned_key != normalized["record_key"]
            or outcome not in {"created", "updated", "removed"}
        ):
            raise LivingResumeEditorUnavailableError()
        if outcome == "removed":
            if row["record_version"] is not None:
                raise LivingResumeEditorUnavailableError()
            version = None
        else:
            version = _version(row["record_version"])
        replayed = _bit(row["replayed"])
        editor = self.get_editor(clean_user_key)
        current = self._record_from_editor(editor, returned_type, returned_key)
        if outcome != "removed" and current is None and not replayed:
            raise LivingResumeEditorUnavailableError()
        return {
            "receipt": {
                "command_id": returned_command_id,
                "request_digest": returned_digest,
                "type": returned_type,
                "record_key": returned_key,
                "outcome": outcome,
                "record_version": version,
                "replayed": replayed,
            },
            "current": current,
        }


living_resume_editor_service = LivingResumeEditorService()
