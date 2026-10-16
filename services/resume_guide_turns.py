"""Pure rules for Guide same-key private conversions (B3b). No storage, provider or route here.

A conversion ("Move to") changes only the member's private draft view of one item until an
explicit Publish (ruling 41e46cf). These helpers decide which moves exist, build the D6a
descriptor the publisher reads, and bind tokens to exactly what a member reviewed.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

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


# ---------------------------------------------------------------- B3t: highlight tiles
# Frozen contract (plan edff4959, coordination B3t frozen contract): a highlight_refs entry is a
# plain bullet key (metric index 0, no caption) or {item_ref, metric_index, metric_text?, caption?}.
# metric_text is the server-set fingerprint of the chosen number; it is never displayed copy.
TILE_CAPTION_LIMIT = 80
_NUMBER = re.compile(r"(?<![\w.,])[$\u20ac\u00a3\u00a5]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
                     r"(?:[bB][nN]|[KkMmBb])?[%+x]?(?![\w])")


def metric_numbers(wording) -> list:
    """Every number token in a bullet's own words, in order. Pure and deterministic; no AI."""
    if not isinstance(wording, str):
        return []
    return [match.group(0) for match in _NUMBER.finditer(wording)]


def nth_metric(wording, stored_metric, index):
    """Index 0 is the stored metric; n >= 1 counts the other tokens after skipping the first stored one."""
    if index == 0:
        return stored_metric if isinstance(stored_metric, str) and stored_metric.strip() else None
    tokens = metric_numbers(wording)
    if isinstance(stored_metric, str) and stored_metric in tokens:
        tokens.remove(stored_metric)
    return tokens[index - 1] if 0 < index <= len(tokens) else None


def _utf16_units(text):
    return len(text.encode("utf-16-le")) // 2


def highlight_entry(raw):
    """Normalize one client-chosen tile. Raises ValueError; never accepts a client fingerprint."""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict) or not {"item_ref", "metric_index"} <= set(raw) <= {"item_ref", "metric_index", "caption"}:
        raise ValueError("invalid")
    index = raw["metric_index"]
    if type(index) is not int or index < 0 or not isinstance(raw["item_ref"], str):
        raise ValueError("invalid")
    entry = {"item_ref": raw["item_ref"], "metric_index": index}
    if "caption" in raw:
        caption = raw["caption"]
        if not isinstance(caption, str):
            raise ValueError("invalid")
        caption = caption.strip()
        visible = [c for c in caption if not c.isspace() and unicodedata.category(c) not in {"Cc", "Cf"}]
        if (not visible or any(unicodedata.category(c) in {"Cc", "Cf"} for c in caption)
                or _utf16_units(caption) > TILE_CAPTION_LIMIT):
            raise ValueError("invalid")  # plain visible text only: no newline, no zero-width-only caption
        entry["caption"] = caption
    if index == 0 and "caption" not in entry:
        return entry["item_ref"]
    return entry


def tile_key(entry):
    """(item_ref, metric_index) for a stored or chosen entry."""
    if isinstance(entry, str):
        return entry, 0
    return entry.get("item_ref"), entry.get("metric_index")


def resolve_tile(entry, *, values, role_ref):
    """The frozen read-only tile for one eligible saved bullet, or None when index 0 has no metric."""
    item_ref, index = tile_key(entry)
    caption = entry.get("caption") if isinstance(entry, dict) else None
    stored = values.get("metric_value")
    tile = {"item_ref": item_ref, "metric_index": index, "value": None, "label": None, "role_ref": role_ref,
            "state": "shown", "publish": "as_today" if isinstance(entry, str) else "after_update"}
    if index == 0:
        value = nth_metric(values.get("wording"), stored, 0)
        if value is None:
            return None
        tile.update(value=value, label=caption or values.get("metric_label"))
        return tile
    value = nth_metric(values.get("wording"), stored, index)
    fingerprint = entry.get("metric_text") if isinstance(entry, dict) else None
    if value is None or (fingerprint is not None and value != fingerprint):
        tile["state"] = "needs_review"  # never show a different number
        return tile
    tile["value"] = value
    if not caption:
        tile["state"] = "needs_caption"
        return tile
    tile["label"] = caption
    return tile
