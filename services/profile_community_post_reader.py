"""Durable exact Community Post reference reader for Profile.

The injected executor must expose only PS-PROFILE-002's owner-scoped exact
reference procedures.  No Community body, reply, count, or feed is retrieved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol, Sequence

from services.profile_posts_adapter import EligibleCommunityPostSource, ProfilePostsDependencyUnavailable


class CommunityReferenceProcedureExecutor(Protocol):
    def execute_procedure(self, name: str, parameters: Sequence[tuple[str, object]] | None = None) -> list[list[Mapping[str, object]]]: ...


class SqlProfileCommunityPostReader:
    def __init__(self, executor: CommunityReferenceProcedureExecutor):
        self._executor = executor

    def _row(self, name: str, parameters):
        try:
            result = self._executor.execute_procedure(name, parameters)
        except Exception as error:
            raise ProfilePostsDependencyUnavailable("Community reference unavailable.") from error
        if not isinstance(result, list) or not result or not isinstance(result[0], list) or not result[0]:
            return None
        return result[0][0] if isinstance(result[0][0], Mapping) else None

    def get_exact_profile_eligible_post(self, *, owner_key: str, source_key: str, source_revision: str):
        row = self._row("usp_GetProfileEligibleCommunityPostForOwner", [
            ("@OwnerKey", owner_key), ("@SourceKey", source_key), ("@SourceRevision", source_revision),
        ])
        if row is None:
            return None
        try:
            return EligibleCommunityPostSource(
                source_key=row["source_key"], owner_key=row["owner_key"],
                source_revision=row["source_revision"], canonical_path=row["canonical_path"],
                published_at=datetime.fromisoformat(row["published_at"]),
                profile_eligible=row.get("profile_eligible") is True or row.get("profile_eligible") == 1,
            )
        except (KeyError, TypeError, ValueError):
            raise ProfilePostsDependencyUnavailable("Community reference unavailable.") from None

    def get_current_profile_eligible_revision(self, *, owner_key: str, source_key: str):
        row = self._row("usp_GetCurrentProfileEligibleCommunityRevisionForOwner", [
            ("@OwnerKey", owner_key), ("@SourceKey", source_key),
        ])
        return None if row is None else row.get("source_revision")
