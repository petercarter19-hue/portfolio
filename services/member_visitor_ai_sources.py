"""Immutable member AI inputs. These objects are not bearer credentials.

Only the repository builds a bundle from a coherent SQL read. Preview choices
select saved canonical evidence; proposed wording, uploads and artwork never
become evidence here. The seal prevents accidental dictionary construction,
not malicious code running inside the server process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Protocol

from services.ai_foundation.contracts import Audience, Purpose, SourceVersion
from services.resume_publication_contracts import (
    ContractError, EntryRef, ManifestEntry, MediaVersion, PublicationEvidenceVersion,
    ReadState, SourceRef, TrustedUseContext, UseAudience, UsePurpose, VersionTuple,
    VisitorAIManifest, Wording, _context_from_authorized_server,
    decode_canonical_source, digest, revision, text,
)

_SEAL = object()
CANONICAL_TYPES = frozenset({'role', 'education', 'credential', 'skill', 'achievement', 'project', 'knowledge'})


class SourcesUnavailable(RuntimeError):
    """No reliable authority was obtained. Never fall back to private data."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('duplicate JSON key')
        result[key] = value
    return result


def strict_json(raw: str):
    if type(raw) is not str:
        raise ContractError('JSON text required')
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ContractError('nonfinite JSON')))


def fingerprint(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _boolean(value):
    if type(value) is not bool:
        raise ContractError('explicit boolean required')
    return value


def _positive(value):
    revision(value)
    if value == 0:
        raise ContractError('positive version required')
    return value


@dataclass(frozen=True)
class PreviewBinding:
    subject_key: str
    draft_revision: int
    choices: tuple[tuple[str, bool], ...]
    authority_digest: str
    candidate_digest: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self):
        if self._seal is not _SEAL:
            raise ContractError('server-issued preview required')
        text(self.subject_key)
        revision(self.draft_revision)
        digest(self.authority_digest)
        digest(self.candidate_digest)
        if type(self.choices) is not tuple or any(type(x) is not tuple or len(x) != 2 for x in self.choices):
            raise ContractError('immutable choices required')
        for key, allowed in self.choices:
            text(key)
            _boolean(allowed)
        if len({x[0] for x in self.choices}) != len(self.choices):
            raise ContractError('duplicate choice')
        expected = fingerprint([self.subject_key, self.draft_revision, self.choices, self.authority_digest])
        if expected != self.candidate_digest:
            raise ContractError('candidate digest mismatch')


@dataclass(frozen=True)
class EligibleSources:
    context: TrustedUseContext
    versions: VersionTuple
    manifest: VisitorAIManifest
    evidence: tuple[PublicationEvidenceVersion, ...]
    sources: tuple[SourceVersion, ...]
    authority_digest: str
    slug: str | None
    preview: PreviewBinding | None
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self):
        if self._seal is not _SEAL:
            raise ContractError('repository-issued sources required')
        digest(self.authority_digest)


class EligibleSourcesPort(Protocol):
    def load_guest(self, slug: str) -> EligibleSources: ...
    def load_preview(self, binding: PreviewBinding) -> EligibleSources: ...


class CurrentnessPort(Protocol):
    def recheck(self, sources: EligibleSources) -> ReadState: ...


def _validate_header(document: dict, *, owner: str | None):
    if type(document) is not dict or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ContractError('unsupported SQL snapshot')
    text(document['subject_key'])
    text(document['profile_revision'])
    digest(document['placement_digest'])
    if document['resume_key'] != 'resume:' + document['subject_key']:
        raise ContractError('foreign Resume')
    if owner is not None and owner != document['subject_key']:
        raise ContractError('foreign owner')
    if document['mode'] != ('owner_preview' if owner is not None else 'guest'):
        raise ContractError('wrong use mode')
    for key in ('draft_revision', 'publication_revision', 'sharing_epoch'):
        revision(document[key])
    _boolean(document['sharing_enabled'])
    if owner is None:
        if not document['sharing_enabled'] or document['current_revision'] != document['publication_revision']:
            raise ContractError('sharing unavailable')
        _positive(document['current_revision'])
        digest(document['reviewed_digest'])
    elif document['current_revision'] is not None:
        _positive(document['current_revision'])
    for key in ('entries', 'media'):
        if type(document[key]) is not list:
            raise ContractError('explicit version collection required')
    if type(document['publication_media']) is not dict:
        raise ContractError('explicit publication media required')
    digest(document['draft_digest'])


def issue_preview(document: dict, owner: str, draft_revision: int,
                  choices: tuple[tuple[str, bool], ...]) -> PreviewBinding:
    _validate_header(document, owner=owner)
    revision(draft_revision)
    if document['draft_revision'] != draft_revision:
        raise ContractError('draft changed')
    if type(choices) is not tuple or any(type(x) is not tuple or len(x) != 2 for x in choices):
        raise ContractError('explicit immutable choices required')
    choices = tuple(sorted(choices))
    authority = fingerprint(document)
    binding = PreviewBinding(owner, draft_revision, choices, authority,
                             fingerprint([owner, draft_revision, choices, authority]), _SEAL)
    # Validate every selected source before issuing the candidate binding.
    build_sources(document, owner=owner, preview=binding)
    return binding


def build_sources(document: dict, *, owner: str | None = None,
                  slug: str | None = None, preview: PreviewBinding | None = None) -> EligibleSources:
    _validate_header(document, owner=owner)
    authority = fingerprint(document)
    if owner is None:
        text(slug)
        if preview is not None:
            raise ContractError('preview is not a guest credential')
    elif (type(preview) is not PreviewBinding or preview.subject_key != owner
          or preview.authority_digest != authority or preview.draft_revision != document['draft_revision']):
        raise ContractError('preview candidate changed')
    subject = document['subject_key']
    context = _context_from_authorized_server(
        subject_key=subject, resume_key=document['resume_key'],
        audience=UseAudience.GUEST if owner is None else UseAudience.OWNER_PREVIEW,
        purpose=UsePurpose.VISITOR_AI if owner is None else UsePurpose.OWNER_VISITOR_AI_PREVIEW,
        authenticated_owner_key=owner,
    )
    audience = Audience.PUBLIC if owner is None else Audience.OWNER
    choices = dict(preview.choices) if preview is not None else None
    seen = set()
    evidence, refs, source_refs, sources, manifest = [], [], [], [], []
    for row in document['entries']:
        if type(row) is not dict or row['owner_key'] != subject or row['entry_key'] in seen:
            raise ContractError('foreign or duplicate source')
        seen.add(row['entry_key'])
        text(row['entry_key'])
        if row['canonical_type'] not in CANONICAL_TYPES or row['lifecycle'] != 'active':
            raise ContractError('ineligible canonical source')
        for key in ('resume_display', 'visitor_ai', 'evidence_display', 'evidence_ai'):
            _boolean(row[key])
        if owner is None and (not row['visitor_ai'] or not row['evidence_ai']):
            raise ContractError('independent AI permission required')
        _positive(row['content_version'])
        _positive(row['access_revision'])
        _positive(row['evidence_content_version'])
        _positive(row['evidence_access_revision'])
        text(row['canonical_revision'])
        if (row['evidence_content_version'] != row['content_version']
                or row['evidence_access_revision'] != row['access_revision']
                or row['canonical_token'] != str(row['content_version'])):
            raise ContractError('stale evidence policy')
        if type(row['dependency_versions']) is not list:
            raise ContractError('dependency versions required')
        for dep in row['dependency_versions']:
            text(dep)
        raw = bytes.fromhex(row['content_hex'])
        decoded = decode_canonical_source(raw)
        if decoded['canonical_type'] != row['canonical_type']:
            raise ContractError('wrong canonical type')
        item = PublicationEvidenceVersion(
            subject, row['entry_key'], 'saved:' + row['entry_key'], row['evidence_version_key'],
            _positive(row['evidence_version']), row['codec'], row['canonical_token'],
            row['content_version'], row['access_revision'], raw, row['content_sha256'],
            row['evidence_display'], row['evidence_ai'], tuple(row['dependency_versions']),
        )
        if item.content_sha256 != row['current_content_sha256']:
            raise ContractError('canonical content changed')
        if choices is not None and not choices.get(row['entry_key'], False):
            continue
        ref = EntryRef(subject, row['entry_key'], str(row['content_version']) + ':' + row['canonical_revision'], row['access_revision'])
        source_ref = SourceRef(ref, item.evidence_key, item.evidence_version_key, item.version, item.content_sha256)
        source = SourceVersion(
            item.evidence_version_key, item.evidence_key, item.version, subject,
            'Private saved draft preview' if owner is not None else 'Approved saved information',
            raw.decode('utf-8'), item.content_sha256,
            frozenset({audience}), frozenset({Purpose.PUBLIC_PROFILE_ANSWER}),
        )
        refs.append(ref)
        evidence.append(item)
        source_refs.append(source_ref)
        sources.append(source)
        manifest.append(ManifestEntry(ref, tuple(Wording(k, tuple(v) if type(v) is list else str(v)) for k, v in decoded.items() if v is not None), (source_ref,)))
    if choices is not None and set(choices) - seen:
        raise ContractError('candidate contains unavailable source')
    media = []
    for row in document['media']:
        if not _boolean(row['ready']) or not _boolean(row['active']):
            raise ContractError('media dependency unavailable')
        media.append(MediaVersion(subject, row['slot'], row['placement_version'], row['source_kind'],
                                  row['source_key'], row['source_revision'], row['asset_version'],
                                  row['catalog_revision'], row['content_sha256'], row['readiness_sha256']))
    versions = VersionTuple(subject, document['resume_key'], document['draft_revision'],
                            document['publication_revision'], document['sharing_epoch'],
                            tuple(refs), tuple(source_refs), tuple(media))
    return EligibleSources(context, versions, VisitorAIManifest(tuple(manifest)), tuple(evidence),
                           tuple(sources), authority, slug, preview, _SEAL)
