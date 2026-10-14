"""Live, read-only eligibility and currentness over E's authoritative records."""
from __future__ import annotations

from typing import Protocol
import copy
import hashlib
import re
from services.member_visitor_ai_sources import (
    EligibleSources, PreviewBinding, SourcesUnavailable, build_sources, issue_preview, strict_json, fingerprint,
)
from services.resume_publication_contracts import ReadState, text, decode_canonical_source

VISITOR_AI_PROCEDURES = frozenset({'usp_GetMemberVisitorAiBySlug', 'usp_GetMemberVisitorAiPreviewForOwner'})


class AuthenticatedOwnerPort(Protocol):
    def current_owner_key(self) -> str: ...


class SqlMemberVisitorAiRepository:
    def __init__(self, database, *, identity: AuthenticatedOwnerPort | None = None, draft_service=None):
        self.database = database
        self.identity = identity
        self.draft_service = draft_service

    def _owner(self) -> str:
        if self.identity is None:
            raise SourcesUnavailable('Owner authorization is unavailable.')
        owner = self.identity.current_owner_key()
        text(owner)
        return owner

    def _read(self, *, slug=None, owner=None):
        try:
            if owner is None:
                text(slug)
                procedure, parameters = 'usp_GetMemberVisitorAiBySlug', [('@ProfileSlug', slug)]
            else:
                procedure, parameters = 'usp_GetMemberVisitorAiPreviewForOwner', [('@UserKey', owner)]
            row = self.database.first_row(procedure, parameters)
            if type(row) is not dict or set(row) != {'snapshot_json'}:
                raise ValueError('missing coherent snapshot')
            document = strict_json(row['snapshot_json'])
            if owner is not None and self.draft_service is not None:
                workspace = self.draft_service.get_workspace(owner)
                # Bracket the separate draft read with coherent authority reads.
                # Provider and citation release repeat this check.
                after = self.database.first_row(procedure, parameters)
                if (type(after) is not dict or set(after) != {'snapshot_json'}
                        or strict_json(after['snapshot_json']) != document):
                    raise ValueError('preview authority changed during draft read')
                document = _with_private_draft(document, workspace)
            return document
        except Exception as error:
            raise SourcesUnavailable('AI source authority is unavailable.') from error

    def load_guest(self, slug: str) -> EligibleSources:
        try:
            return build_sources(self._read(slug=slug), slug=slug)
        except Exception as error:
            raise SourcesUnavailable('AI source authority is unavailable.') from error

    def prepare_preview(self, *, expected_draft_revision: int,
                        choices: tuple[tuple[str, bool], ...]) -> PreviewBinding:
        """Server composition supplies identity; choices are explicit proposed AI use.

        A binding is process-local and never returned as a public/guest token.
        Later route integration must inject the real authenticated identity port.
        """
        try:
            owner = self._owner()
            return issue_preview(self._read(owner=owner), owner, expected_draft_revision, choices)
        except Exception as error:
            raise SourcesUnavailable('Preview authority is unavailable.') from error

    def preview_choices(self) -> dict:
        """Private saved draft choices; neither a permission grant nor a guest token."""
        try:
            owner = self._owner()
            document = self._read(owner=owner)
            choices = tuple((row['entry_key'], row['visitor_ai']) for row in document['entries'])
            binding = issue_preview(document, owner, document['draft_revision'], choices)
            items = []
            for row in document['entries']:
                values = decode_canonical_source(bytes.fromhex(row['content_hex']))
                label = next((values.get(key) for key in ('role_title', 'title', 'name',
                              'credential_name', 'institution_name', 'summary', 'wording')
                              if type(values.get(key)) is str and values[key].strip()), 'Saved information')
                items.append({'entry_key': row['entry_key'], 'label': label[:160],
                              'selected': row['visitor_ai']})
            bundle = build_sources(document, owner=owner, preview=binding)
            if self.recheck(bundle) is not ReadState.CURRENT:
                raise SourcesUnavailable('Preview changed.')
            return {'draft_revision': binding.draft_revision, 'choices': items}
        except Exception as error:
            raise SourcesUnavailable('Preview choices are unavailable.') from error

    def load_preview(self, binding: PreviewBinding) -> EligibleSources:
        try:
            if type(binding) is not PreviewBinding:
                raise ValueError('server preview binding required')
            owner = self._owner()
            if owner != binding.subject_key:
                raise ValueError('foreign preview')
            return build_sources(self._read(owner=owner), owner=owner, preview=binding)
        except Exception as error:
            raise SourcesUnavailable('Preview authority is unavailable.') from error

    def recheck(self, sources: EligibleSources) -> ReadState:
        """Fresh SQL read after provider and support validation, with no cached authority."""
        try:
            if type(sources) is not EligibleSources:
                return ReadState.DENIED
            current = (self.load_preview(sources.preview) if sources.preview is not None
                       else self.load_guest(sources.slug))
            if (current.context != sources.context or current.versions != sources.versions
                    or current.authority_digest != sources.authority_digest
                    or current.sources != sources.sources):
                return ReadState.STALE
            return ReadState.CURRENT
        except SourcesUnavailable:
            return ReadState.UNAVAILABLE


def _same_rowversion(left, right):
    """Compare SQL style-2 and Python hex only as exact binary(8) tokens."""
    if not all(type(value) is str and re.fullmatch(r'[0-9a-fA-F]{16}', value)
               for value in (left, right)):
        return False
    return bytes.fromhex(left) == bytes.fromhex(right)


def _with_private_draft(document, workspace):
    """Project owner-saved draft wording without writing canonical/public state."""
    from services.resume_publication_projection import committed_source_bytes
    from services.resume_publication_service import _codec_values, conversion_publication_blocker

    if (workspace['capabilities']['canonical_read'] != 'ok'
            or workspace['draft_version'] != document['draft_revision']):
        raise ValueError('draft authority unavailable or changed')
    result = copy.deepcopy(document)
    rows = {row['entry_key']: row for row in result['entries']}
    seen = set()
    for item in workspace['items']:
        key = item['record_key']
        if key in seen:
            raise ValueError('duplicate draft entry')
        seen.add(key)
        conversion = conversion_publication_blocker(item)
        if conversion is not None:
            # D6a: a B3 move's destination values never reach the old-type codec.
            raise ValueError(conversion)
        if not item['has_draft']:
            continue
        row = rows.get(key)
        kind = 'achievement' if item['record_type'] == 'accomplishment' else item['record_type']
        if (row is None or item['orphaned'] or item['draft_is_stale']
                or kind != row['canonical_type']
                or not _same_rowversion(item['content_token'], row['canonical_revision'])
                or item['access_revision'] != row['access_revision']
                or not _same_rowversion(item['draft_base_content_token'], row['canonical_revision'])
                or item['draft_base_access_revision'] != row['access_revision']):
            raise ValueError('private draft base changed')
        raw = bytes.fromhex(row['content_hex'])
        if (hashlib.sha256(raw).hexdigest() != row['content_sha256']
                or row['current_content_sha256'] != row['content_sha256']):
            raise ValueError('canonical evidence changed')
        proposed = committed_source_bytes(kind, _codec_values(item['proposed_values'], kind))
        digest = hashlib.sha256(proposed).hexdigest()
        row.update(content_hex=proposed.hex(), content_sha256=digest, current_content_sha256=digest,
                   evidence_version_key='draft:' + key + ':' + str(workspace['draft_version']) + ':' + digest)
    result['draft_digest'] = fingerprint([document['draft_digest'], workspace])
    return result
