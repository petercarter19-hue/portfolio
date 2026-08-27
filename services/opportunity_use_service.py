"""Owner-scoped Opportunity Slate use disclosure — PS-WORKSHOP-USE-DISCLOSURE-001.

Workshop D's one read: does any version of the member's own explicitly saved
Opportunity Slate cite one knowledge item? The durable authority is
``dbo.opportunity_saved_evidence`` (rows a member created with Save
privately); transient analysis citations are working data and are never
consulted here. The read returns counts, a version number, and a timestamp
only — no bodies, excerpts, employer text, or any other Opportunity Slate
content ever passes through this module.

The identity rule matches services/knowledge_service.py exactly: the given
``user_key`` string is passed straight through to the procedure's ``@UserKey``
parameter (never a cached, global, or substituted value), and
``usp_GetOpportunitySlateUseForOwner`` is solely responsible for resolving
``@UserKey`` -> ``@ProfileId`` and re-asserting ``owner_profile_id`` on every
predicate. A forged or unresolvable ``user_key`` is carried through unchanged
and yields zero rows at the database layer, exactly as
PS-OPPSLATE-USE-001_owner_isolation_verify.sql proves.

No provider or AI call exists anywhere in this module.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from services.database_service import database_service


class OpportunityUseServiceError(RuntimeError):
    """Raised for invalid input or an unexpected database result shape."""

    def __init__(self, message, *, code):
        super().__init__(message)
        self.code = code


# The exact-and-only fields usp_GetOpportunitySlateUseForOwner returns per
# cited item. Enforced with set equality (the knowledge_service
# ``_require_exact_fields`` discipline): a widened or narrowed result is an
# error, never silently accepted.
USE_ROW_FIELDS = frozenset(
    {
        "citing_version_count",
        "latest_saved_at_utc",
        "latest_save_version_number",
        "cites_latest_saved_version",
    }
)


@dataclass(frozen=True)
class SlateUse:
    """One item's citation state across every saved slate version."""

    citing_version_count: int
    latest_saved_at_utc: datetime
    latest_save_version_number: int
    cites_latest_saved_version: bool


def _require_user_key(user_key):
    if not isinstance(user_key, str) or not user_key.strip():
        raise OpportunityUseServiceError(
            "A resolved owner identity is required.", code="no_identity"
        )


def _require_item_key(item_key):
    try:
        return str(UUID(str(item_key)))
    except (ValueError, TypeError, AttributeError) as error:
        raise OpportunityUseServiceError(
            "A valid knowledge item key is required.", code="invalid"
        ) from error


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OpportunityUseServiceError(f"Invalid {label}.", code="invalid")
    return value


def _sql_bit(value, label):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise OpportunityUseServiceError(f"Invalid {label}.", code="invalid")


def _utc_datetime(value, label):
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str) and value == value.strip() and "T" in value:
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError as error:
            raise OpportunityUseServiceError(
                f"Invalid {label}.", code="invalid"
            ) from error
    else:
        raise OpportunityUseServiceError(f"Invalid {label}.", code="invalid")

    try:
        if timestamp.utcoffset() is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)
    except (OverflowError, ValueError) as error:
        raise OpportunityUseServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error


class OpportunityUseService:
    """The single Workshop D disclosure read.

    ``database`` defaults to the shared ``database_service`` singleton; the
    one public method calls exactly one procedure through it.
    """

    def __init__(self, database=None):
        self.database = database or database_service

    def get_slate_use_for_owner(self, user_key, item_key):
        """Return a ``SlateUse`` when the member's saved slate cites the
        item, or ``None`` when it does not.

        ``None`` covers every zero-row shape identically — no slate saved
        yet, item never cited, a foreign or unknown key, an unresolvable
        ``user_key`` — so the caller can never distinguish "not mine" from
        "does not exist" through this read.
        """
        _require_user_key(user_key)
        clean_item_key = _require_item_key(item_key)

        result_sets = self.database.execute_procedure(
            "usp_GetOpportunitySlateUseForOwner",
            [("@UserKey", user_key), ("@KnowledgeItemKey", clean_item_key)],
        )
        if len(result_sets) > 1:
            raise OpportunityUseServiceError(
                "Unexpected slate use result.", code="invalid"
            )
        rows = result_sets[0] if result_sets else []
        if not rows:
            return None
        if len(rows) != 1:
            raise OpportunityUseServiceError(
                "Unexpected slate use result.", code="invalid"
            )

        row = rows[0]
        if not isinstance(row, dict) or set(row) != USE_ROW_FIELDS:
            raise OpportunityUseServiceError(
                "Unexpected slate use result shape.", code="invalid"
            )
        return SlateUse(
            citing_version_count=_positive_int(
                row["citing_version_count"], "citing version count"
            ),
            latest_saved_at_utc=_utc_datetime(
                row["latest_saved_at_utc"], "latest saved timestamp"
            ),
            latest_save_version_number=_positive_int(
                row["latest_save_version_number"], "latest save version"
            ),
            cites_latest_saved_version=_sql_bit(
                row["cites_latest_saved_version"], "latest-save citation bit"
            ),
        )


opportunity_use_service = OpportunityUseService()
