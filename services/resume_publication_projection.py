"""Build committed canonical-source bytes from actual resulting values.

SQL is the transaction producer. Python implements the same codec for
conformance and reader validation only.
"""

from __future__ import annotations

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


def canonical_fields_from_values(canonical_type: str, values: dict[str, object]) -> dict[str, object]:
    if canonical_type not in TYPE_FIELD_MAP:
        raise ContractError("unsupported canonical type")
    if type(values) is not dict:
        raise ContractError("typed canonical values required")
    mapped = dict(values)
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
