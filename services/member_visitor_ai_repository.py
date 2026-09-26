"""Live, read-only eligibility and currentness over E's authoritative records."""
from __future__ import annotations

from typing import Protocol
from services.member_visitor_ai_sources import (
    EligibleSources, PreviewBinding, SourcesUnavailable, build_sources, issue_preview, strict_json,
)
from services.resume_publication_contracts import ReadState, text

VISITOR_AI_PROCEDURES = frozenset({'usp_GetMemberVisitorAiBySlug', 'usp_GetMemberVisitorAiPreviewForOwner'})


class AuthenticatedOwnerPort(Protocol):
    def current_owner_key(self) -> str: ...


class SqlMemberVisitorAiRepository:
    def __init__(self, database, *, identity: AuthenticatedOwnerPort | None = None):
        self.database = database
        self.identity = identity

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
            return strict_json(row['snapshot_json'])
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
