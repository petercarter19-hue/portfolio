"""Private My Data presentation facade for MVP1 first slice.

Reads the member's canonical facts through the accepted entry-policy
commands and the composer's intake workspace, then shapes one inventory:
category groups in member-facing order, a cross-view Activity timeline,
search/filter selection, and truthful unavailable states.

This module performs no writes, owns no store, derives identity from its
caller (the route layer passes the server-derived user key), and never
accepts owner identifiers, table names, or permission bypass flags. Every
saved fact starts private; this layer only reports the stored flags.

Feature gate ``PEERSLATE_MY_DATA_ENABLED`` is enforced by the route layer.
Missing configuration behaves as disabled.
"""

from __future__ import annotations

from datetime import datetime


DISPLAY_CATEGORIES = (
    ("experience", "Work history"),
    ("education", "Education"),
    ("skill", "Skills"),
    ("achievement", "Achievements"),
    ("credential", "Credentials"),
    ("project", "Project experience"),
    ("personal", "About me"),
)

DISPLAY_TITLES = dict(DISPLAY_CATEGORIES)

PERMISSION_FILTERS = frozenset(
    {"all", "private", "resume", "visitor_ai", "excluded", "recently_deleted"}
)


def _parse_moment(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment


def _entry_search_text(entry):
    values = entry.get("values") or {}
    parts = [entry.get("category") or "", entry.get("canonical_type") or ""]
    for value in values.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, bool):
            continue
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).casefold()


def _is_deleted(entry):
    return entry.get("lifecycle") == "deleted"


def _shares_resume(entry):
    return bool(entry.get("resume_display"))


def _shares_visitor_ai(entry):
    return bool(entry.get("visitor_ai"))


def _assistance_excluded(entry):
    return bool(entry.get("private_assistance_excluded"))


def _permission_match(entry, permission):
    """Match one permission filter against the entry's actual flags.

    Permissions are independent: an entry permitted for both résumé and
    visitor AI matches both filters. Private means neither résumé nor
    visitor AI sharing is permitted; assistance exclusion is a separate
    setting that may coexist with any of these states.
    """
    deleted = _is_deleted(entry)
    if permission == "recently_deleted":
        return deleted
    if deleted:
        return False
    if permission == "all":
        return True
    if permission == "private":
        return not _shares_resume(entry) and not _shares_visitor_ai(entry)
    if permission == "resume":
        return _shares_resume(entry)
    if permission == "visitor_ai":
        return _shares_visitor_ai(entry)
    if permission == "excluded":
        return _assistance_excluded(entry)
    return False


class MyDataUnavailableError(RuntimeError):
    """Raised when no backing source could be read at all."""


class MyDataService:
    """Presentation facade over entry-policy reads and intake workspace reads."""

    def __init__(self, entry_policy=None, intake=None):
        self._entry_policy = entry_policy
        self._intake = intake

    def _entry_service(self):
        if self._entry_policy is not None:
            return self._entry_policy
        from flask import current_app

        from services.entry_policy_service import entry_policy_service

        try:
            configured = current_app.config.get("ENTRY_POLICY_SERVICE")
        except RuntimeError:  # No application context in bare unit use.
            configured = None
        return configured or entry_policy_service

    def _intake_service(self):
        if self._intake is not None:
            return self._intake
        from flask import current_app

        from services.resume_intake_service import resume_intake_service

        try:
            configured = current_app.config.get("RESUME_INTAKE_SERVICE")
        except RuntimeError:  # No application context in bare unit use.
            configured = None
        return configured or resume_intake_service

    def overview(
        self,
        user_key,
        *,
        view="category",
        search="",
        category="",
        permission="all",
    ):
        """Return the grouped inventory plus the Activity timeline.

        ``view`` is ``category`` or ``activity`` and is echoed back so the
        interface can preserve the member's selected view and list position.
        Unknown views fall back to ``category``; unknown permission filters
        fall back to ``all``.
        """
        if view not in {"category", "activity"}:
            view = "category"
        if permission not in PERMISSION_FILTERS:
            permission = "all"
        needle = (search or "").strip().casefold()
        entries, entries_state = self._read_entries(user_key)
        activity_events, activity_state = self._read_activity(user_key, entries)
        visible = [
            entry
            for entry in entries
            if self._matches(entry, needle, category, permission)
        ]
        groups = self._group(visible)
        return {
            "view": view,
            "search": search or "",
            "category": category or "",
            "permission": permission,
            "entries_state": entries_state,
            "activity_state": activity_state,
            "total_count": len(entries),
            "visible_count": len(visible),
            "groups": groups,
            "activity": activity_events,
            "capabilities": {
                "views": ["category", "activity"],
                "categories": [
                    {"key": key, "title": title}
                    for key, title in DISPLAY_CATEGORIES
                ],
                "permission_filters": sorted(PERMISSION_FILTERS),
            },
        }

    def _read_entries(self, user_key):
        try:
            result = self._entry_service().list_entries(user_key)
        except Exception:  # noqa: BLE001 - fail-closed unavailable state
            return [], "unavailable"
        entries = [
            entry
            for entry in (result.get("entries") or [])
            if entry.get("lifecycle") != "permanently_deleted"
        ]
        return entries, "ready"

    def _read_activity(self, user_key, entries):
        events = []
        try:
            workspace = self._intake_service().get_workspace(user_key)
        except Exception:  # noqa: BLE001 - intake outage stays truthful
            workspace = None
        if workspace:
            for proposal in workspace.get("pending_proposals") or []:
                moment = _parse_moment(proposal.get("created_at"))
                if moment is None:
                    continue
                events.append(
                    {
                        "at": proposal.get("created_at"),
                        "kind": "proposal_needs_review",
                        "text": "An addition needs your review before it is saved.",
                        "entry_key": proposal.get("target_key"),
                    }
                )
            receipt = workspace.get("last_receipt") or {}
            if receipt.get("created_at"):
                events.append(
                    {
                        "at": receipt.get("created_at"),
                        "kind": "composer_add",
                        "text": "Information entered through the composer.",
                        "entry_key": None,
                    }
                )
        for entry in entries:
            updated = entry.get("updated_at")
            created = entry.get("created_at")
            if entry.get("lifecycle") == "deleted":
                # A deletion is a lifecycle event with its own timestamp.
                # Content timestamps must never stand in for it, and a
                # missing lifecycle timestamp means no dated event at all.
                moment_value = entry.get("deleted_at")
                if _parse_moment(moment_value) is None:
                    continue
                kind, text = "entry_deleted", "Information moved to Recently deleted."
            elif updated and updated != created:
                moment_value = updated
                kind, text = "entry_updated", "Information corrected."
            else:
                moment_value = updated or created
                if _parse_moment(moment_value) is None:
                    continue
                kind, text = "entry_added", "Information entered."
            events.append(
                {
                    "at": moment_value,
                    "kind": kind,
                    "text": text,
                    "entry_key": entry.get("entry_key"),
                }
            )
        events.sort(key=lambda item: item["at"] or "", reverse=True)
        state = "ready" if workspace is not None else "intake_unavailable"
        return events, state

    def _matches(self, entry, needle, category, permission):
        if category and entry.get("category") != category:
            return False
        # The default view shows active information only. Deleted
        # entries live under Recently deleted.
        if not _permission_match(entry, permission):
            return False
        if needle and needle not in _entry_search_text(entry):
            return False
        return True

    def _group(self, entries):
        groups = [
            {"key": key, "title": title, "entries": []}
            for key, title in DISPLAY_CATEGORIES
        ]
        by_key = {group["key"]: group for group in groups}
        for entry in entries:
            group = by_key.get(entry.get("category"))
            if group is None:
                continue
            group["entries"].append(entry)
        return [group for group in groups if group["entries"]]
