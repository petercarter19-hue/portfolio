"""Bounded, owner-scoped read model for the finite PeerSlate Home."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import re
from types import MappingProxyType
from uuid import UUID

from services.database_service import database_service


SCHEMA_VERSION = "owner-home.v1"
MAX_REVIEW_ITEMS = 3
MAX_PRODUCT_OBJECTS = 9
MAX_PAYLOAD_BYTES = 64 * 1024
AVAILABILITY_REGISTRY_VERSION = "owner-home-capabilities.v1"

OWNER_ROW_FIELDS = frozenset(
    {"profile_key", "display_name", "profile_row_version"}
)
REVIEW_ROW_FIELDS = frozenset(
    {
        "item_key",
        "review_kind",
        "created_at_utc",
        "updated_at_utc",
        "version_token",
        "status",
    }
)
MOMENT_ROW_FIELDS = frozenset(
    {
        "moment_key",
        "confirmed_version",
        "title",
        "occurred_on",
        "updated_at_utc",
        "version_token",
        "status",
    }
)
REVIEW_KINDS = frozenset(
    {"voice_draft_failed", "moment_proposal_pending", "voice_draft_ready"}
)
REVIEW_SUMMARIES = MappingProxyType(
    {
        "voice_draft_failed": "A private voice draft needs attention.",
        "moment_proposal_pending": "A private Moment proposal is ready for review.",
        "voice_draft_ready": "A private voice draft is ready for review.",
    }
)
AVAILABILITY_REGISTRY = MappingProxyType(
    {
        "resurfaced_moment": MappingProxyType({"state": "coming_later"}),
        "noticed_item": MappingProxyType({"state": "coming_later"}),
        "connection_item": MappingProxyType({"state": "coming_later"}),
    }
)
_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")
TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "owner",
        "generated_at",
        "state_version",
        "capture_action",
        "review_items",
        "recent_moment",
        "resurfaced_moment",
        "noticed_item",
        "connection_item",
        "next_step",
        "availability",
    }
)
OWNER_FIELDS = frozenset({"profile_key", "display_name"})
ACTION_FIELDS = frozenset(
    {"action_kind", "destination", "availability", "label"}
)
REVIEW_FIELDS = frozenset(
    {
        "item_key",
        "review_kind",
        "summary",
        "created_at",
        "updated_at",
        "version_token",
        "destination",
        "status",
    }
)
RECENT_MOMENT_FIELDS = frozenset(
    {
        "moment_key",
        "confirmed_version",
        "title",
        "occurred_on",
        "updated_at",
        "version_token",
        "destination",
        "status",
    }
)
NEXT_STEP_FIELDS = frozenset(
    {"action_kind", "label", "reason", "destination", "availability"}
)


class OwnerHomeContractError(RuntimeError):
    """The private Home result did not satisfy its fail-closed contract."""


@dataclass(frozen=True)
class OwnerHomeViewModel:
    owner: dict
    generated_at: str
    state_version: str
    capture_action: dict
    review_items: tuple
    recent_moment: dict | None
    next_step: dict

    def to_dict(self):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "owner": dict(self.owner),
            "generated_at": self.generated_at,
            "state_version": self.state_version,
            "capture_action": dict(self.capture_action),
            "review_items": [dict(item) for item in self.review_items],
            "recent_moment": (
                dict(self.recent_moment) if self.recent_moment is not None else None
            ),
            "resurfaced_moment": None,
            "noticed_item": None,
            "connection_item": None,
            "next_step": dict(self.next_step),
            "availability": {
                name: dict(value) for name, value in AVAILABILITY_REGISTRY.items()
            },
        }
        _validate_serialized_payload(payload)
        return payload


def _require_exact_fields(row, expected, label):
    if not isinstance(row, dict) or set(row) != set(expected):
        raise OwnerHomeContractError(f"Unexpected {label} result shape.")


def _opaque_key(value, label):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise OwnerHomeContractError(f"Invalid {label}.") from error


def _bounded_text(value, label, max_length, *, required=True):
    if value is None:
        clean = ""
    else:
        clean = str(value).strip()
    if (required and not clean) or len(clean) > max_length:
        raise OwnerHomeContractError(f"Invalid {label}.")
    return clean or None


def _version_token(value, label):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        value = value.hex()
    if not isinstance(value, str) or not _VERSION_TOKEN.fullmatch(value):
        raise OwnerHomeContractError(f"Invalid {label}.")
    return value.lower()


def _utc_timestamp(value, label):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise OwnerHomeContractError(f"Invalid {label}.") from error
    else:
        raise OwnerHomeContractError(f"Invalid {label}.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _date_value(value, label):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise OwnerHomeContractError(f"Invalid {label}.") from error
    raise OwnerHomeContractError(f"Invalid {label}.")


def _review_destination(kind, item_key):
    if kind in {"voice_draft_failed", "voice_draft_ready"}:
        return f"/app/capture?voice={item_key}"
    return f"/app/moments/{item_key}/review"


def _prepare_owner(row):
    _require_exact_fields(row, OWNER_ROW_FIELDS, "owner")
    return (
        {
            "profile_key": _opaque_key(row["profile_key"], "profile key"),
            "display_name": _bounded_text(
                row["display_name"], "display name", 300
            ),
        },
        _version_token(row["profile_row_version"], "profile version"),
    )


def _prepare_review(row):
    _require_exact_fields(row, REVIEW_ROW_FIELDS, "review item")
    kind = str(row["review_kind"] or "")
    if kind not in REVIEW_KINDS:
        raise OwnerHomeContractError("Unexpected review kind.")
    item_key = _opaque_key(row["item_key"], "review item key")
    status = _bounded_text(row["status"], "review status", 30)
    expected_status = {
        "voice_draft_failed": "failed",
        "moment_proposal_pending": "proposal",
        "voice_draft_ready": "needs_review",
    }[kind]
    if status != expected_status:
        raise OwnerHomeContractError("Unexpected review status.")
    return {
        "item_key": item_key,
        "review_kind": kind,
        "summary": REVIEW_SUMMARIES[kind],
        "created_at": _utc_timestamp(row["created_at_utc"], "review created time"),
        "updated_at": _utc_timestamp(row["updated_at_utc"], "review updated time"),
        "version_token": _version_token(row["version_token"], "review version"),
        "destination": _review_destination(kind, item_key),
        "status": status,
    }


def _prepare_recent_moment(row):
    _require_exact_fields(row, MOMENT_ROW_FIELDS, "recent Moment")
    if row["status"] != "confirmed":
        raise OwnerHomeContractError("Unexpected recent Moment status.")
    try:
        confirmed_version = int(row["confirmed_version"])
    except (TypeError, ValueError) as error:
        raise OwnerHomeContractError("Invalid confirmed Moment version.") from error
    if confirmed_version < 1:
        raise OwnerHomeContractError("Invalid confirmed Moment version.")
    moment_key = _opaque_key(row["moment_key"], "Moment key")
    return {
        "moment_key": moment_key,
        "confirmed_version": confirmed_version,
        "title": _bounded_text(row["title"], "Moment title", 160),
        "occurred_on": _date_value(row["occurred_on"], "Moment date"),
        "updated_at": _utc_timestamp(row["updated_at_utc"], "Moment updated time"),
        "version_token": _version_token(row["version_token"], "Moment version"),
        "destination": f"/app/moments/{moment_key}/review",
        "status": "confirmed",
    }


def _state_version(owner, profile_version, reviews, recent_moment):
    selected_state = {
        "owner": {"profile_key": owner["profile_key"], "version": profile_version},
        "reviews": [
            {
                "item_key": item["item_key"],
                "kind": item["review_kind"],
                "version": item["version_token"],
            }
            for item in reviews
        ],
        "recent_moment": (
            {
                "moment_key": recent_moment["moment_key"],
                "version": recent_moment["version_token"],
                "confirmed_version": recent_moment["confirmed_version"],
            }
            if recent_moment is not None
            else None
        ),
        "availability_registry": AVAILABILITY_REGISTRY_VERSION,
    }
    encoded = json.dumps(
        selected_state, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _next_step(reviews, recent_moment):
    if reviews:
        first = reviews[0]
        return {
            "action_kind": "review_item",
            "label": "Review this item",
            "reason": "A private item is waiting for your review.",
            "destination": first["destination"],
            "availability": {"state": "available"},
        }
    if recent_moment is not None:
        return {
            "action_kind": "recent_moment",
            "label": "Return to your recent Moment",
            "reason": "Your most recently confirmed private Moment is available.",
            "destination": recent_moment["destination"],
            "availability": {"state": "available"},
        }
    return {
        "action_kind": "start_text_capture",
        "label": "Start a new Capture",
        "reason": "Capture something you want to remember.",
        "destination": "/app/capture",
        "availability": {"state": "available"},
    }


def _validate_serialized_payload(payload):
    if set(payload) != TOP_LEVEL_FIELDS or set(payload["owner"]) != OWNER_FIELDS:
        raise OwnerHomeContractError("Unexpected Owner Home payload shape.")
    if set(payload["capture_action"]) != ACTION_FIELDS:
        raise OwnerHomeContractError("Unexpected Capture action shape.")
    if payload["capture_action"].get("availability") != {"state": "available"}:
        raise OwnerHomeContractError("Unexpected Capture availability.")
    for item in payload["review_items"]:
        if set(item) != REVIEW_FIELDS:
            raise OwnerHomeContractError("Unexpected review item shape.")
    if payload["recent_moment"] is not None and set(
        payload["recent_moment"]
    ) != RECENT_MOMENT_FIELDS:
        raise OwnerHomeContractError("Unexpected recent Moment shape.")
    if set(payload["next_step"]) != NEXT_STEP_FIELDS:
        raise OwnerHomeContractError("Unexpected next-step shape.")
    if payload["next_step"].get("availability") != {"state": "available"}:
        raise OwnerHomeContractError("Unexpected next-step availability.")
    if set(payload["availability"]) != set(AVAILABILITY_REGISTRY):
        raise OwnerHomeContractError("Unexpected availability category.")
    if any(
        value != {"state": "coming_later"}
        for value in payload["availability"].values()
    ):
        raise OwnerHomeContractError("Unexpected capability availability.")

    if len(payload["review_items"]) > MAX_REVIEW_ITEMS:
        raise OwnerHomeContractError("Owner Home review limit exceeded.")

    object_count = 1 + len(payload["review_items"]) + 1
    if payload["recent_moment"] is not None:
        object_count += 1
    for category in ("resurfaced_moment", "noticed_item", "connection_item"):
        if payload[category] is not None or payload["availability"][category][
            "state"
        ] == "coming_later":
            object_count += 1
    if object_count > MAX_PRODUCT_OBJECTS:
        raise OwnerHomeContractError("Owner Home object limit exceeded.")

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise OwnerHomeContractError("Owner Home payload limit exceeded.")


class OwnerHomeService:
    """Perform one finite database read and serialize only approved fields."""

    def __init__(self, database=None, clock=None):
        self.database = database or database_service
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def get_home(self, owner_identity):
        user_key = getattr(owner_identity, "user_key", None)
        if not isinstance(user_key, str) or not user_key.strip():
            raise OwnerHomeContractError("A resolved owner identity is required.")

        result_sets = self.database.execute_procedure(
            "usp_GetOwnerHomeForOwner", [("@UserKey", user_key)]
        )
        if len(result_sets) != 3 or len(result_sets[0]) != 1:
            raise OwnerHomeContractError("Unexpected Owner Home result sets.")

        owner, profile_version = _prepare_owner(result_sets[0][0])
        if len(result_sets[1]) > MAX_REVIEW_ITEMS or len(result_sets[2]) > 1:
            raise OwnerHomeContractError("Owner Home database limit exceeded.")
        reviews = tuple(_prepare_review(row) for row in result_sets[1])
        recent_moment = (
            _prepare_recent_moment(result_sets[2][0]) if result_sets[2] else None
        )

        view_model = OwnerHomeViewModel(
            owner=owner,
            generated_at=_utc_timestamp(self.clock(), "generation time"),
            state_version=_state_version(
                owner, profile_version, reviews, recent_moment
            ),
            capture_action={
                "action_kind": "capture",
                "destination": "/app/capture",
                "availability": {"state": "available"},
                "label": "Capture something",
            },
            review_items=reviews,
            recent_moment=recent_moment,
            next_step=_next_step(reviews, recent_moment),
        )
        view_model.to_dict()
        return view_model


owner_home_service = OwnerHomeService()
