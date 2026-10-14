"""Build committed canonical-source bytes from actual resulting values.

SQL is the transaction producer. Python implements the same codec for
conformance and reader validation only.
"""

from __future__ import annotations

from datetime import date
from services.living_resume_editor_service import credential_date_text, LivingResumeEditorValidationError

from services.resume_publication_contracts import (
    CANONICAL_SOURCE_FIELDS,
    ContractError,
    PublicationEvidenceVersion,
    encode_canonical_source,
    hash_canonical_source,
)


TYPE_FIELD_MAP = {
    "role": (
        "role_title",
        "employer_name",
        "location_text",
        "summary",
        "start_date",
        "end_date",
        "date_precision",
        "employment_type",
        "current_role",
    ),
    "education": (
        "title",
        "institution_name",
        "degree_name",
        "field_of_study",
        "education_status",
        "grade_text",
        "location_text",
        "summary",
        "start_date",
        "end_date",
        "date_precision",
    ),
    "credential": (
        "credential_name",
        "issuer_name",
        "credential_identifier",
        "issue_date",
        "expiration_date",
        "summary",
    ),
    "skill": ("name", "skill_summary"),
    "achievement": (
        "wording",
        "metric_value",
        "metric_label",
        "accomplishment_to_achievement",
        "parent_canonical_type",
    ),
    "project": (
        "title",
        "summary",
        "start_date",
        "end_date",
        "current_role",
    ),
    "knowledge": ("title", "summary"),
}

RESUME_CORE_SECTIONS = (
    ("impact_statement", "Impact Statement"), ("skills", "Skills"), ("experience", "Experience"),
    ("projects", "Projects"), ("education", "Education"), ("certifications", "Certifications"), ("awards", "Awards"),
)
RESUME_BASE_SECTION_ORDER = tuple(key for key, _ in RESUME_CORE_SECTIONS)
RESUME_SECTION_LABELS = {**dict(RESUME_CORE_SECTIONS), "languages": "Languages", "publications": "Publications",
    "memberships": "Memberships", "story": "My Story", "contact": "Contact details", "looking_ahead": "Looking Ahead"}
_SECTION_ALIASES = {label: key for key, label in RESUME_SECTION_LABELS.items()}
_SECTION_ALIASES.update({"Professional summary": "impact_statement", "Credentials": "certifications",
                         "Independent Project": "projects"})


def resume_section_for(record_type, values=None, *, presentation_section=None, story_bound=False, proposed=False):
    """Classify actual stored types/approved placement; never infer a Story binding."""
    values = values or {}
    if record_type == "credential":
        kind = values.get("qualification_kind")
        if kind in {None, "certification", "license"}:
            return "certifications"
        return {"publication": "publications", "membership": "memberships"}.get(kind, "unplaced")
    direct = {"role": "experience", "skill": "skills", "education": "education", "project": "projects"}
    if record_type in direct:
        return direct[record_type]
    if record_type != "knowledge":
        return "unplaced"
    if story_bound:
        return "story" if values.get("classification") == "personal" else "unplaced"
    stated = _SECTION_ALIASES.get(presentation_section, presentation_section)
    if stated == "story":
        return "story" if proposed else "unplaced"
    if stated in {"awards", "impact_statement", "projects", "contact", "looking_ahead", "languages"}:
        return stated
    # These are the approved knowledge envelope labels, not arbitrary title
    # guesses. "My Story" alone deliberately remains unbound.
    if values.get("classification") in {"work", "both"}:
        return {"Contact details": "contact", "Professional summary": "impact_statement",
                "Independent Project": "projects", "Looking Ahead": "looking_ahead"}.get(values.get("title"), "unplaced")
    return "unplaced"


def resume_section_order(seen=()):
    extras = []
    for section in seen:
        if section in {"languages", "publications", "memberships"} and section not in extras:
            extras.append(section)
    if "languages" in extras:
        extras.remove("languages")
        extras.insert(0, "languages")
    return (*RESUME_BASE_SECTION_ORDER, *extras)


def resume_presentation_key(record_type: str, values: dict, *, presentation_section=None, story_bound=False, section_order=None) -> tuple:
    """Presentation only: current roles, then known dates; stable unknown ties.

    Never infer a date/currentness from prose or change canonical/review bytes.
    Placeholder days in the existing year/month encoding carry no extra truth.
    """
    order = section_order or RESUME_BASE_SECTION_ORDER
    section_key = resume_section_for(record_type, values, presentation_section=presentation_section, story_bound=story_bound)
    section = order.index(section_key) if section_key in order else len(order)
    if section_order is None and section_key in {"languages", "publications", "memberships"}:
        return section, 0, 0  # Preserve first encounter across optional groups.
    current = record_type == "role" and values.get("current_role") is True
    precision = values.get("date_precision")
    raw = values.get("end_date") or values.get("start_date")
    if record_type == "credential":
        raw = values.get('issue_date')
        precision = values.get('issue_date_precision') or ({4: 'year', 7: 'month', 10: 'day'}.get(len(raw)) if isinstance(raw, str) else None)
    ordinal = 0
    if precision in {"year", "month", "day"} and isinstance(raw, str):
        try:
            known = date.fromisoformat(raw + ('-01-01' if len(raw) == 4 else '-01' if len(raw) == 7 else ''))
            if precision == "year": known = known.replace(month=1, day=1)
            elif precision == "month": known = known.replace(day=1)
            ordinal = known.toordinal()
        except ValueError:
            pass
    return section, -int(current), -ordinal


def ordered_resume_display(display: dict) -> dict:
    order = resume_section_order(resume_section_for(row.get("canonical_type"), row.get("wording") or {},
        presentation_section=row.get("presentation_section"), story_bound=row.get("presentation_section") == "story")
        for row in display.values())
    return dict(sorted(display.items(), key=lambda pair: resume_presentation_key(
        pair[1].get("canonical_type", ""), pair[1].get("wording") or {},
        presentation_section=pair[1].get("presentation_section"), story_bound=pair[1].get("presentation_section") == "story",
        section_order=order)))


def canonical_fields_from_values(canonical_type: str, values: dict[str, object]) -> dict[str, object]:
    if canonical_type not in TYPE_FIELD_MAP:
        raise ContractError("unsupported canonical type")
    if type(values) is not dict:
        raise ContractError("typed canonical values required")
    mapped = dict(values)
    if canonical_type == "project" and "project_name" in mapped:
        if mapped.get("title") not in {None, mapped["project_name"]}:
            raise ContractError("Project name and title disagree.")
        mapped["title"] = mapped["project_name"]
    if canonical_type == 'credential':
        # Local partial-date evidence uses the existing date string slots.
        # The fixed durable v1 codec and legacy full-ISO bytes stay unchanged.
        for name in ('issue_date', 'expiration_date'):
            try:
                mapped[name] = credential_date_text(mapped.get(name), mapped.get(name + '_precision'))
            except LivingResumeEditorValidationError as error:
                raise ContractError(str(error)) from error
    if canonical_type == "skill" and "summary" in mapped and "skill_summary" not in mapped:
        mapped["skill_summary"] = mapped.pop("summary")
    fields = {name: None for name in CANONICAL_SOURCE_FIELDS}
    fields["canonical_type"] = canonical_type
    for name in TYPE_FIELD_MAP[canonical_type]:
        if name not in mapped:
            continue
        fields[name] = mapped[name]
    return fields


def committed_source_bytes(canonical_type: str, values: dict[str, object]) -> bytes:
    return encode_canonical_source(canonical_fields_from_values(canonical_type, values))


def publication_evidence_version(
    *,
    owner_key: str,
    entry_key: str,
    evidence_key: str,
    evidence_version_key: str,
    version: int,
    canonical_token: str,
    policy_content_version: int,
    access_revision: int,
    canonical_type: str,
    values: dict[str, object],
    display_eligible: bool,
    visitor_ai_eligible: bool,
    dependency_versions: tuple[str, ...] = (),
) -> PublicationEvidenceVersion:
    payload = committed_source_bytes(canonical_type, values)
    return PublicationEvidenceVersion(
        owner_key=owner_key,
        entry_key=entry_key,
        evidence_key=evidence_key,
        evidence_version_key=evidence_version_key,
        version=version,
        codec="resume-canonical-source.v1",
        canonical_token=canonical_token,
        policy_content_version=policy_content_version,
        access_revision=access_revision,
        content=payload,
        content_sha256=hash_canonical_source(payload),
        display_eligible=display_eligible,
        visitor_ai_eligible=visitor_ai_eligible,
        dependency_versions=dependency_versions,
    )
