"""Explicit public-AI source manifest and deterministic resume adapter.

The living resume may be public without every field being approved for AI use.
This adapter reads only records named in the server-side manifest, renders only
the fields defined by a versioned public renderer, and requires the rendered
content to match the manifest's approved SHA-256 digest.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from services.ai_foundation import Audience, Purpose, SourceVersion

from .errors import PublicSourceManifestError


MANIFEST_SCHEMA = "ask-pete-public-sources.v1"
EXPECTED_DATA_FILE = "static/data/resume_data.json"
PUBLIC_PURPOSES = frozenset(
    {
        Purpose.PUBLIC_PROFILE_ANSWER,
        Purpose.RECRUITER_BRIEF,
        Purpose.EVIDENCE_FINDER,
        Purpose.INTERVIEW_PREPARATION,
    }
)


@dataclass(frozen=True)
class SourceLocator:
    section: str
    anchor: str
    record_kind: str
    record_id: str
    highlight_key: str

    @property
    def context_key(self) -> str:
        return f"{self.record_kind}:{self.record_id}"


@dataclass(frozen=True)
class PublicSourceRecord:
    source: SourceVersion
    locator: SourceLocator
    renderer: str


@dataclass(frozen=True)
class PublicSourceCatalog:
    manifest_id: str
    subject_key: str
    subject_display_name: str
    profile_slug: str
    records: tuple[PublicSourceRecord, ...]

    def __post_init__(self) -> None:
        if not self.records:
            raise PublicSourceManifestError("public source manifest is empty")

    @property
    def sources(self) -> tuple[SourceVersion, ...]:
        return tuple(record.source for record in self.records)

    def record_for_version(self, source_version_key: str) -> PublicSourceRecord:
        for record in self.records:
            if record.source.source_version_key == source_version_key:
                return record
        raise PublicSourceManifestError("citation source is outside the manifest")

    def sources_for(
        self,
        purpose: Purpose,
        *,
        context_key: str | None = None,
    ) -> tuple[SourceVersion, ...]:
        permitted = [
            record
            for record in self.records
            if purpose in record.source.allowed_purposes
        ]
        if context_key:
            permitted.sort(
                key=lambda record: record.locator.context_key != context_key
            )
        return tuple(record.source for record in permitted)


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PublicSourceManifestError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PublicSourceManifestError(f"{label} must be an array")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    *,
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    if actual != expected:
        raise PublicSourceManifestError(f"{label} fields do not match the contract")


def _text(value: Any, label: str, *, maximum: int = 300) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
    ):
        raise PublicSourceManifestError(f"{label} must be bounded text")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PublicSourceManifestError(f"{label} must be a positive integer")
    return value


def _boolean_true(value: Any, label: str) -> None:
    if value is not True:
        raise PublicSourceManifestError(f"{label} must be explicitly true")


def _record_by_id(resume: Mapping[str, Any], collection: str, record_id: str):
    values = _array(resume.get(collection), f"resume.{collection}")
    matches = [
        _object(value, f"resume.{collection} item")
        for value in values
        if isinstance(value, Mapping) and value.get("id") == record_id
    ]
    if len(matches) != 1:
        raise PublicSourceManifestError("approved resume record is missing or duplicated")
    return matches[0]


def _string_list(value: Any, label: str) -> list[str]:
    values = _array(value or [], label)
    output: list[str] = []
    for item in values:
        output.append(_text(item, label, maximum=1_000))
    return output


def _append_list(lines: list[str], heading: str, values: Sequence[str]) -> None:
    if not values:
        return
    lines.append(f"{heading}:")
    lines.extend(f"- {value}" for value in values)


def _render_profile(resume: Mapping[str, Any], record_id: str) -> str:
    profile = _object(resume.get("profile"), "resume.profile")
    if profile.get("slug") != record_id:
        raise PublicSourceManifestError("approved profile record does not match")
    lines = [
        f"Name: {_text(profile.get('name'), 'profile.name')}",
        f"Positioning: {_text(profile.get('positioning'), 'profile.positioning', maximum=1_000)}",
        f"Professional summary: {_text(profile.get('summary'), 'profile.summary', maximum=2_000)}",
        f"Location: {_text(profile.get('location'), 'profile.location')}",
    ]
    credentials: list[str] = []
    for value in _array(profile.get("credentials") or [], "profile.credentials"):
        item = _object(value, "profile credential")
        label = _text(item.get("label"), "credential.label", maximum=1_000)
        status = _text(item.get("status"), "credential.status", maximum=300)
        credentials.append(f"{label} — {status}")
    _append_list(lines, "Public credentials", credentials)
    return "\n".join(lines)


def _render_career_role(resume: Mapping[str, Any], record_id: str) -> str:
    role = _record_by_id(resume, "career_roles", record_id)
    lines = [
        f"Employer: {_text(role.get('employer'), 'role.employer', maximum=500)}",
        f"Role: {_text(role.get('title'), 'role.title', maximum=500)}",
        f"Dates: {_text(role.get('dates'), 'role.dates')}",
        f"Summary: {_text(role.get('summary'), 'role.summary', maximum=3_000)}",
    ]
    public_note = role.get("current_role_public_note")
    if isinstance(public_note, str) and public_note.strip():
        lines.append(f"Public boundary: {_text(public_note, 'role.public_note', maximum=2_000)}")
    accomplishments: list[str] = []
    for value in _array(role.get("accomplishments") or [], "role.accomplishments"):
        item = _object(value, "role accomplishment")
        accomplishments.append(
            _text(item.get("text"), "accomplishment.text", maximum=2_000)
        )
    _append_list(lines, "Accomplishments", accomplishments)
    _append_list(
        lines,
        "Responsibilities",
        _string_list(role.get("responsibilities"), "role.responsibility"),
    )
    _append_list(
        lines,
        "Leadership scope",
        _string_list(role.get("leadership_scope"), "role.leadership_scope"),
    )
    _append_list(
        lines,
        "Methods",
        _string_list(role.get("methods"), "role.methods"),
    )
    _append_list(lines, "Tools", _string_list(role.get("tools"), "role.tools"))
    return "\n".join(lines)


def _render_skill(resume: Mapping[str, Any], record_id: str) -> str:
    skill = _record_by_id(resume, "skills", record_id)
    if skill.get("public_display") is not True:
        raise PublicSourceManifestError("approved skill is not publicly displayed")
    lines = [
        f"Skill: {_text(skill.get('display_name'), 'skill.display_name')}",
        f"Public summary: {_text(skill.get('front_summary'), 'skill.front_summary', maximum=2_000)}",
    ]
    evidence: list[str] = []
    for value in _array(skill.get("evidence_items") or [], "skill.evidence_items"):
        item = _object(value, "skill evidence")
        employer = _text(item.get("employer"), "skill evidence employer", maximum=500)
        date_range = _text(item.get("date_range"), "skill evidence date", maximum=100)
        text = _text(item.get("text"), "skill evidence text", maximum=2_000)
        evidence.append(f"{employer} ({date_range}): {text}")
    _append_list(lines, "Approved evidence", evidence)
    return "\n".join(lines)


def _render_achievement(resume: Mapping[str, Any], record_id: str) -> str:
    achievement = _record_by_id(resume, "achievements", record_id)
    return "\n".join(
        [
            f"Achievement: {_text(achievement.get('title'), 'achievement.title', maximum=500)}",
            f"Organization: {_text(achievement.get('org'), 'achievement.org', maximum=500)}",
            f"Year: {_text(achievement.get('year'), 'achievement.year', maximum=100)}",
            f"Public detail: {_text(achievement.get('detail'), 'achievement.detail', maximum=2_000)}",
        ]
    )


Renderer = Callable[[Mapping[str, Any], str], str]
RENDERERS: dict[str, tuple[str, Renderer]] = {
    "profile_public_v1": ("profile", _render_profile),
    "career_role_public_v1": ("career_role", _render_career_role),
    "skill_public_v1": ("skill", _render_skill),
    "achievement_public_v1": ("achievement", _render_achievement),
}


def render_source_content(
    resume: Mapping[str, Any],
    *,
    renderer: str,
    record_kind: str,
    record_id: str,
) -> str:
    renderer_contract = RENDERERS.get(renderer)
    if renderer_contract is None or renderer_contract[0] != record_kind:
        raise PublicSourceManifestError("source renderer does not match record kind")
    content = renderer_contract[1](resume, record_id)
    if not content.strip():
        raise PublicSourceManifestError("approved source rendered empty content")
    return content


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicSourceManifestError(f"{label} could not be read") from exc
    return _object(payload, label)


def load_public_source_catalog(
    *,
    manifest_path: Path,
    resume_path: Path,
) -> PublicSourceCatalog:
    manifest = _read_json(manifest_path, "public source manifest")
    _exact_keys(
        manifest,
        expected={
            "schema_version",
            "manifest_id",
            "subject_key",
            "subject_display_name",
            "profile_slug",
            "data_file",
            "records",
        },
        label="public source manifest",
    )
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise PublicSourceManifestError("public source manifest schema is unsupported")
    if manifest.get("data_file") != EXPECTED_DATA_FILE:
        raise PublicSourceManifestError("public source manifest data file is not allowed")

    manifest_id = _text(manifest.get("manifest_id"), "manifest_id")
    subject_key = _text(manifest.get("subject_key"), "subject_key")
    subject_display_name = _text(
        manifest.get("subject_display_name"),
        "subject_display_name",
    )
    profile_slug = _text(manifest.get("profile_slug"), "profile_slug")
    resume = _read_json(resume_path, "public resume data")
    profile = _object(resume.get("profile"), "resume.profile")
    if (
        profile.get("slug") != profile_slug
        or profile_slug != subject_key
        or profile.get("name") != subject_display_name
    ):
        raise PublicSourceManifestError("manifest subject does not match resume profile")

    records: list[PublicSourceRecord] = []
    seen_sources: set[str] = set()
    seen_versions: set[str] = set()
    seen_contexts: set[str] = set()
    for raw_record in _array(manifest.get("records"), "manifest.records"):
        item = _object(raw_record, "manifest record")
        _exact_keys(
            item,
            expected={
                "source_key",
                "source_version_key",
                "version",
                "title",
                "record_kind",
                "record_id",
                "renderer",
                "content_sha256",
                "public_visibility",
                "approved_for_ask_pete",
                "allowed_purposes",
                "locator",
            },
            label="manifest record",
        )
        _boolean_true(item.get("public_visibility"), "public_visibility")
        _boolean_true(item.get("approved_for_ask_pete"), "approved_for_ask_pete")
        source_key = _text(item.get("source_key"), "source_key")
        source_version_key = _text(
            item.get("source_version_key"),
            "source_version_key",
        )
        if source_key in seen_sources or source_version_key in seen_versions:
            raise PublicSourceManifestError("manifest source keys must be unique")
        seen_sources.add(source_key)
        seen_versions.add(source_version_key)

        record_kind = _text(item.get("record_kind"), "record_kind")
        record_id = _text(item.get("record_id"), "record_id")
        renderer = _text(item.get("renderer"), "renderer")
        content = render_source_content(
            resume,
            renderer=renderer,
            record_kind=record_kind,
            record_id=record_id,
        )
        expected_digest = _text(
            item.get("content_sha256"),
            "content_sha256",
            maximum=64,
        )
        actual_digest = sha256(content.encode("utf-8")).hexdigest()
        if expected_digest != actual_digest:
            raise PublicSourceManifestError("approved source content digest changed")

        purposes: set[Purpose] = set()
        for value in _array(item.get("allowed_purposes"), "allowed_purposes"):
            try:
                purpose = Purpose(_text(value, "allowed purpose"))
            except ValueError as exc:
                raise PublicSourceManifestError("manifest purpose is unsupported") from exc
            if purpose not in PUBLIC_PURPOSES:
                raise PublicSourceManifestError("manifest purpose is not public")
            purposes.add(purpose)
        if not purposes:
            raise PublicSourceManifestError("manifest record needs a public purpose")

        raw_locator = _object(item.get("locator"), "source locator")
        _exact_keys(
            raw_locator,
            expected={
                "section",
                "anchor",
                "record_kind",
                "record_id",
                "highlight_key",
            },
            label="source locator",
        )
        locator = SourceLocator(
            section=_text(raw_locator.get("section"), "locator.section"),
            anchor=_text(raw_locator.get("anchor"), "locator.anchor"),
            record_kind=_text(
                raw_locator.get("record_kind"),
                "locator.record_kind",
            ),
            record_id=_text(raw_locator.get("record_id"), "locator.record_id"),
            highlight_key=_text(
                raw_locator.get("highlight_key"),
                "locator.highlight_key",
            ),
        )
        if locator.record_kind != record_kind or locator.record_id != record_id:
            raise PublicSourceManifestError("source locator names a different record")
        if locator.context_key in seen_contexts:
            raise PublicSourceManifestError("source locator contexts must be unique")
        seen_contexts.add(locator.context_key)

        source = SourceVersion(
            source_version_key=source_version_key,
            source_key=source_key,
            version=_positive_integer(item.get("version"), "source version"),
            subject_key=subject_key,
            title=_text(item.get("title"), "source title", maximum=500),
            content=content,
            content_sha256=expected_digest,
            allowed_audiences=frozenset({Audience.PUBLIC}),
            allowed_purposes=frozenset(purposes),
        )
        records.append(
            PublicSourceRecord(
                source=source,
                locator=locator,
                renderer=renderer,
            )
        )

    return PublicSourceCatalog(
        manifest_id=manifest_id,
        subject_key=subject_key,
        subject_display_name=subject_display_name,
        profile_slug=profile_slug,
        records=tuple(records),
    )
