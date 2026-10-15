"""Pure rules for Guide same-key private conversions (B3b). No storage, provider or route here.

A conversion ("Move to") changes only the member's private draft view of one item until an
explicit Publish (ruling 41e46cf). These helpers decide which moves exist, build the D6a
descriptor the publisher reads, and bind tokens to exactly what a member reviewed.
"""
from __future__ import annotations

import hashlib
import json

# B3b scope (ruling B3b-design-answers Q4). The rest of the approved R6q set lands in a named
# follow-up round before package 10; until then these are the only destinations offered.
SUPPORTED_CONVERSIONS = frozenset({
    ("skill", "accomplishment"),
    ("skill", "project"),
    ("accomplishment", "skill"),
    ("project", "skill"),
})

CONVERSION_DESCRIPTOR_KEYS = ("state", "base_record_type", "destination_record_type", "destination_parent_ref",
                              "base_content_token", "base_access_revision", "conversion_op_ref")


def _digest(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def conversion_supported(base_record_type, destination_record_type) -> bool:
    return (base_record_type, destination_record_type) in SUPPORTED_CONVERSIONS


def destination_needs_parent(destination_record_type) -> bool:
    """A role bullet lives under an eligible saved role; every other B3b destination has no parent."""
    return destination_record_type == "accomplishment"


def conversion_descriptor(*, base_record_type, destination_record_type, destination_parent_ref,
                          base_content_token, base_access_revision, operation_ref) -> dict:
    """The exact D6a object for a confirmed private move of a saved item."""
    return {
        "state": "confirmed_private",
        "base_record_type": base_record_type,
        "destination_record_type": destination_record_type,
        "destination_parent_ref": destination_parent_ref,
        "base_content_token": str(base_content_token),
        "base_access_revision": int(base_access_revision),
        "conversion_op_ref": operation_ref,
    }


def reference_digest(references) -> str:
    return _digest(list(references or []))


def conversion_token(owner, conversion_key, item_ref, base, destination, affected) -> str:
    """Binds a staged move to what was reviewed; it is not permission."""
    return _digest({"type": "guide_conversion", "owner": owner, "conversion_key": conversion_key,
                    "item_ref": item_ref, "base": base, "destination": destination,
                    "affected": [{"kind": row["kind"], "container_ref": row["container_ref"],
                                  "before_digest": row["before_digest"]} for row in affected]})


def undo_token(owner, operation_ref, resulting) -> str:
    return _digest({"type": "guide_conversion_undo", "owner": owner, "operation_ref": operation_ref,
                    "resulting": resulting})


def reconcile_references(affected, reconciliation, *, invalid_refs):
    """Return {(kind, container_ref): final list} or raise ValueError(code).

    Every affected container needs exactly one reviewed entry whose before_digest is current.
    The final list keeps the current order, may only drop references, and must drop every
    reference the move makes invalid. Nothing is added, copied or silently lost.
    """
    if not isinstance(reconciliation, list):
        raise ValueError("invalid")
    wanted = {(row["kind"], row["container_ref"]): row for row in affected}
    given = {}
    for entry in reconciliation:
        if (not isinstance(entry, dict) or set(entry) != {"kind", "container_ref", "before_digest", "references"}
                or not isinstance(entry["references"], list)):
            raise ValueError("invalid")
        key = (entry["kind"], entry["container_ref"])
        if key in given or key not in wanted:
            raise ValueError("reconciliation_required")
        given[key] = entry
    if set(given) != set(wanted):
        raise ValueError("reconciliation_required")
    final = {}
    for key, row in wanted.items():
        entry = given[key]
        if entry["before_digest"] != row["before_digest"]:
            raise ValueError("changed")
        current = list(row["references"])
        chosen = list(entry["references"])
        positions = []
        for ref in chosen:
            if ref not in current or ref in invalid_refs.get(key, ()) or chosen.count(ref) > 1:
                raise ValueError("reconciliation_required")
            positions.append(current.index(ref))
        if positions != sorted(positions):
            raise ValueError("reconciliation_required")
        final[key] = chosen
    return final
