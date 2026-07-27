"""Pure fixture validation and projection for the internal Member Overview.

PS-OVERVIEW-SLICE-1-001 deliberately stops at a serializable read model.  It
does not retrieve member data, persist drafts, publish content, or change the
public résumé.  The fixture catalog exercises the same ownership, block,
destination, media, and count-aware boundaries that later services must keep.
"""

from __future__ import annotations

import copy
import json
import os
from collections import Counter
from typing import Any


FIXTURE_SCHEMA_VERSION = "overview-fixtures.v1"
PROJECTION_SCHEMA_VERSION = "member-overview-projection.v1"

STYLE_MANIFESTS = {
    "story-career": {
        "id": "story-career",
        "version": 1,
        "label": "Story & Career",
        "css_class": "member-overview--story",
    },
    "work-impact": {
        "id": "work-impact",
        "version": 1,
        "label": "Work & Impact",
        "css_class": "member-overview--work",
    },
}

BLOCK_DEFINITIONS = {
    "identity_hero": {"version": 1, "limit": 1, "emphasis": {"hero"}},
    "proof_band": {"version": 1, "limit": 4, "emphasis": {"feature", "standard"}},
    "story_spotlight": {"version": 1, "limit": 1, "emphasis": {"feature", "standard"}},
    "career": {"version": 1, "limit": 6, "emphasis": {"feature", "standard"}},
    "impact": {"version": 1, "limit": 4, "emphasis": {"feature", "standard"}},
    "skills": {"version": 1, "limit": 12, "emphasis": {"feature", "standard"}},
    "education": {"version": 1, "limit": 4, "emphasis": {"standard", "quiet"}},
    "certifications": {"version": 1, "limit": 6, "emphasis": {"standard", "quiet"}},
    "awards": {"version": 1, "limit": 6, "emphasis": {"standard", "quiet"}},
    "story_chapters": {"version": 1, "limit": 5, "emphasis": {"feature", "standard"}},
    "quote": {"version": 1, "limit": 1, "emphasis": {"feature", "standard"}},
    "philosophy": {"version": 1, "limit": 1, "emphasis": {"feature", "standard"}},
    "future_direction": {"version": 1, "limit": 1, "emphasis": {"feature", "standard"}},
    "resume_transition": {"version": 1, "limit": 1, "emphasis": {"standard"}},
}

BLOCK_MODES = {"record_linked", "authored", "hybrid"}
DENSITIES = {"sparse", "standard", "rich", "text-only"}
ALLOWED_ANCHORS = {
    "#overview",
    "#story",
    "#experience",
    "#impact",
    "#skills",
    "#credentials",
    "#connect",
    "#resume-start",
}
PROOF_ALLOWED_FIELDS = {
    "value",
    "label",
    "icon",
    "destination",
    "order",
    "visible",
}
PROOF_FORBIDDEN_FIELDS = {
    "source",
    "source_id",
    "source_ids",
    "evidence",
    "evidence_id",
    "evidence_ids",
    "verification",
    "verified",
    "confidence",
    "provenance",
    "provenance_state",
}


class OverviewProjectionError(ValueError):
    """A deterministic, externally testable projection contract failure."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise OverviewProjectionError(code, message)


def default_fixture_path() -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "static",
        "data",
        "overview_fixtures.json",
    )


def load_fixture_catalog(path: str | None = None) -> dict[str, Any]:
    """Load fixture JSON without importing Flask or mutating application state."""

    with open(path or default_fixture_path(), "r", encoding="utf-8") as fixture_file:
        catalog = json.load(fixture_file)
    if not isinstance(catalog, dict):
        _fail("invalid_catalog", "fixture catalog must be an object")
    if catalog.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        _fail(
            "unsupported_fixture_version",
            f"expected {FIXTURE_SCHEMA_VERSION}",
        )
    if not isinstance(catalog.get("fixtures"), list):
        _fail("invalid_catalog", "fixtures must be a list")
    return catalog


def list_fixture_options(catalog: dict[str, Any]) -> list[dict[str, str]]:
    """Return the bounded review-menu fields, never fixture owner identifiers."""

    options = []
    seen = set()
    for fixture in catalog.get("fixtures", []):
        fixture_id = fixture.get("fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id or fixture_id in seen:
            _fail("invalid_fixture_id", "fixture IDs must be unique non-empty strings")
        seen.add(fixture_id)
        options.append(
            {
                "id": fixture_id,
                "label": _required_text(fixture, "label", "fixture"),
                "density": fixture.get("density", "standard"),
            }
        )
    return options


def build_overview_projection(
    catalog: dict[str, Any],
    fixture_id: str,
    style_id: str,
) -> dict[str, Any]:
    """Validate one fixture and return a deterministic style-aware read model."""

    manifest = STYLE_MANIFESTS.get(style_id)
    if manifest is None:
        _fail("unsupported_style", f"style {style_id!r} is not supported")

    matches = [
        fixture
        for fixture in catalog.get("fixtures", [])
        if fixture.get("fixture_id") == fixture_id
    ]
    if len(matches) != 1:
        _fail("unknown_fixture", f"fixture {fixture_id!r} does not exist")
    fixture = matches[0]

    owner_key = _required_text(fixture, "owner_key", "fixture")
    density = fixture.get("density", "standard")
    if density not in DENSITIES:
        _fail("unsupported_density", f"density {density!r} is not supported")

    profile = _validate_profile(fixture.get("profile"))
    records = _index_owned_items(fixture.get("records", []), owner_key, "record")
    media = _index_owned_items(fixture.get("media", []), owner_key, "media")
    blocks = _validate_and_resolve_blocks(
        fixture.get("blocks"),
        owner_key=owner_key,
        records=records,
        media=media,
    )

    counts = Counter(block["definition_id"] for block in blocks)
    if counts["identity_hero"] != 1:
        _fail("identity_hero_count", "exactly one visible identity hero is required")
    if counts["resume_transition"] != 1:
        _fail(
            "resume_transition_count",
            "exactly one visible résumé transition is required",
        )

    block_by_definition = {
        block["definition_id"]: block
        for block in blocks
    }
    proof_count = len(
        block_by_definition.get("proof_band", {}).get("content", {}).get("claims", [])
    )
    career_count = len(
        block_by_definition.get("career", {}).get("records", [])
    )
    education_count = len(
        block_by_definition.get("education", {}).get("records", [])
    )

    projection = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "fixture": {
            "id": fixture_id,
            "label": _required_text(fixture, "label", "fixture"),
            "notice": "Illustrative renderer fixture — not a member profile",
        },
        "style": copy.deepcopy(manifest),
        "density": density,
        "profile": profile,
        "blocks": blocks,
        "block_by_definition": block_by_definition,
        "semantic_block_ids": [block["definition_id"] for block in blocks],
        "layout": {
            "proof_count": proof_count,
            "proof_variant": _proof_variant(proof_count),
            "career_count": career_count,
            "career_heading": "Career Focus" if career_count == 1 else "Experience",
            "education_count": education_count,
            "has_credentials": any(
                name in block_by_definition
                for name in ("education", "certifications", "awards")
            ),
            "has_media": any(block.get("media") for block in blocks),
        },
        "navigation": _build_navigation(block_by_definition),
        "readiness": {"state": "ready", "errors": []},
    }
    return projection


def _validate_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        _fail("invalid_profile", "profile must be an object")
    result = {
        "display_name": _required_text(profile, "display_name", "profile"),
        "first_name": _required_text(profile, "first_name", "profile"),
        "headline": _required_text(profile, "headline", "profile"),
        "intro": _required_text(profile, "intro", "profile"),
        "location": _optional_text(profile.get("location")),
        "contact_label": _optional_text(profile.get("contact_label")) or "Connect",
        "initials": _optional_text(profile.get("initials")),
    }
    if not result["initials"]:
        result["initials"] = "".join(
            part[0].upper()
            for part in result["display_name"].split()
            if part
        )[:2]
    destination = profile.get("contact_destination")
    if destination is not None:
        result["contact_destination"] = _validate_destination(destination)
    else:
        result["contact_destination"] = {"kind": "anchor", "value": "#connect"}

    return result


def _index_owned_items(
    items: Any,
    owner_key: str,
    item_kind: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        _fail(f"invalid_{item_kind}_collection", f"{item_kind}s must be a list")
    indexed = {}
    for item in items:
        if not isinstance(item, dict):
            _fail(f"invalid_{item_kind}", f"each {item_kind} must be an object")
        item_id = _required_text(item, "id", item_kind)
        if item_id in indexed:
            _fail(f"duplicate_{item_kind}_id", f"duplicate {item_kind} ID {item_id!r}")
        if item.get("owner_key") != owner_key:
            _fail(
                "cross_owner_reference",
                f"{item_kind} {item_id!r} is not owned by the fixture owner",
            )
        indexed[item_id] = copy.deepcopy(item)
    return indexed


def _validate_and_resolve_blocks(
    raw_blocks: Any,
    *,
    owner_key: str,
    records: dict[str, dict[str, Any]],
    media: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(raw_blocks, list):
        _fail("invalid_blocks", "blocks must be a list")
    if len(raw_blocks) > 18:
        _fail("block_budget_exceeded", "an Overview may contain at most 18 placements")

    resolved = []
    placement_ids = set()
    previous_order = -1
    for raw_block in raw_blocks:
        if not isinstance(raw_block, dict):
            _fail("invalid_block", "each block must be an object")
        placement_id = _required_text(raw_block, "placement_id", "block")
        if placement_id in placement_ids:
            _fail("duplicate_placement_id", f"duplicate placement {placement_id!r}")
        placement_ids.add(placement_id)

        order = raw_block.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            _fail("invalid_order", f"placement {placement_id!r} has invalid order")
        if order <= previous_order:
            _fail("invalid_order", "block orders must be strictly increasing")
        previous_order = order

        definition_id = _required_text(raw_block, "definition_id", "block")
        definition = BLOCK_DEFINITIONS.get(definition_id)
        if definition is None:
            _fail("unsupported_block", f"block {definition_id!r} is not supported")
        if raw_block.get("definition_version") != definition["version"]:
            _fail(
                "unsupported_block_version",
                f"{definition_id!r} requires version {definition['version']}",
            )

        mode = raw_block.get("mode")
        if mode not in BLOCK_MODES:
            _fail("unsupported_block_mode", f"mode {mode!r} is not supported")
        emphasis = raw_block.get("emphasis", "standard")
        if emphasis not in definition["emphasis"]:
            _fail(
                "unsupported_emphasis",
                f"{definition_id!r} does not support emphasis {emphasis!r}",
            )
        visible = raw_block.get("visible", True)
        if not isinstance(visible, bool):
            _fail("invalid_visibility", "block visibility must be boolean")
        if not visible:
            continue

        record_ids = raw_block.get("record_ids", [])
        if not isinstance(record_ids, list) or not all(
            isinstance(item_id, str) for item_id in record_ids
        ):
            _fail("invalid_record_reference", "record_ids must be a string list")
        if mode == "record_linked" and not record_ids:
            _fail("missing_record_reference", f"{definition_id!r} needs records")
        if mode == "authored" and record_ids:
            _fail("unexpected_record_reference", "authored blocks cannot pin records")
        resolved_records = []
        for record_id in record_ids:
            record = records.get(record_id)
            if record is None:
                _fail("unknown_record", f"record {record_id!r} does not exist")
            if record.get("owner_key") != owner_key:
                _fail("cross_owner_reference", f"record {record_id!r} is cross-owner")
            resolved_records.append(_public_record(record))
        if len(resolved_records) > definition["limit"]:
            _fail(
                "collection_budget_exceeded",
                f"{definition_id} supports at most {definition['limit']} records",
            )

        content = raw_block.get("content", {})
        if not isinstance(content, dict):
            _fail("invalid_block_content", f"{definition_id!r} content must be an object")
        content = copy.deepcopy(content)
        _validate_block_content(definition_id, content, definition["limit"])
        if definition_id in {"proof_band", "impact", "skills", "story_chapters"}:
            collection_name = {
                "proof_band": "claims",
                "impact": "items",
                "skills": "items",
                "story_chapters": "items",
            }[definition_id]
            if not content.get(collection_name):
                continue

        destination = raw_block.get("destination")
        if destination is not None:
            destination = _validate_destination(destination)

        media_ids = raw_block.get("media_ids", [])
        if not isinstance(media_ids, list) or not all(
            isinstance(item_id, str) for item_id in media_ids
        ):
            _fail("invalid_media_reference", "media_ids must be a string list")
        resolved_media = []
        for media_id in media_ids:
            media_item = media.get(media_id)
            if media_item is None:
                _fail("unknown_media", f"media {media_id!r} does not exist")
            if media_item.get("owner_key") != owner_key:
                _fail("cross_owner_reference", f"media {media_id!r} is cross-owner")
            if media_item.get("public_eligible") is not True:
                _fail("ineligible_media", f"media {media_id!r} is not public-eligible")
            resolved_media.append(_public_media(media_item))

        resolved.append(
            {
                "placement_id": placement_id,
                "definition_id": definition_id,
                "definition_version": definition["version"],
                "mode": mode,
                "order": order,
                "emphasis": emphasis,
                "content": content,
                "records": resolved_records,
                "media": resolved_media,
                "destination": destination,
            }
        )

    _validate_cross_block_order(resolved)
    return resolved


def _validate_block_content(
    definition_id: str,
    content: dict[str, Any],
    limit: int,
) -> None:
    collection_name = {
        "proof_band": "claims",
        "impact": "items",
        "skills": "items",
        "story_chapters": "items",
    }.get(definition_id)
    if collection_name:
        collection = content.get(collection_name, [])
        if not isinstance(collection, list):
            _fail("invalid_collection", f"{definition_id}.{collection_name} must be a list")
        if len(collection) > limit:
            _fail(
                "collection_budget_exceeded",
                f"{definition_id} supports at most {limit} items",
            )
    if definition_id == "proof_band":
        previous_order = -1
        visible_claims = []
        for index, claim in enumerate(content.get("claims", [])):
            if not isinstance(claim, dict):
                _fail("invalid_proof_claim", f"proof claim {index} must be an object")
            forbidden = PROOF_FORBIDDEN_FIELDS.intersection(claim)
            unknown = set(claim).difference(PROOF_ALLOWED_FIELDS)
            if forbidden:
                _fail(
                    "forbidden_proof_field",
                    f"proof claim contains {sorted(forbidden)[0]!r}",
                )
            if unknown:
                _fail(
                    "unsupported_proof_field",
                    f"proof claim contains unsupported field {sorted(unknown)[0]!r}",
                )
            _required_text(claim, "value", "proof claim")
            _required_text(claim, "label", "proof claim")
            order = claim.get("order")
            if not isinstance(order, int) or isinstance(order, bool) or order <= previous_order:
                _fail(
                    "invalid_order",
                    "proof claim orders must be strictly increasing integers",
                )
            previous_order = order
            visible = claim.get("visible", True)
            if not isinstance(visible, bool):
                _fail("invalid_visibility", "proof visibility must be boolean")
            if "destination" in claim:
                claim["destination"] = _validate_destination(claim["destination"])
            if visible:
                visible_claims.append(claim)
        content["claims"] = visible_claims


def _validate_destination(destination: Any) -> dict[str, str]:
    if not isinstance(destination, dict):
        _fail("invalid_destination", "destination must be an object")
    kind = destination.get("kind")
    value = destination.get("value")
    if kind == "anchor" and value in ALLOWED_ANCHORS:
        return {"kind": kind, "value": value}
    if (
        kind == "email"
        and isinstance(value, str)
        and value.startswith("mailto:")
        and "\n" not in value
        and "\r" not in value
    ):
        return {"kind": kind, "value": value}
    if (
        kind == "public_url"
        and isinstance(value, str)
        and value.startswith("https://")
    ):
        return {"kind": kind, "value": value}
    _fail("unknown_destination", f"destination {kind!r}:{value!r} is not supported")


def _validate_cross_block_order(blocks: list[dict[str, Any]]) -> None:
    positions = {
        block["definition_id"]: index
        for index, block in enumerate(blocks)
    }
    skills_position = positions.get("skills")
    if skills_position is not None:
        for credential in ("education", "certifications", "awards"):
            if credential in positions and positions[credential] < skills_position:
                _fail(
                    "invalid_semantic_order",
                    "Skills must precede Education, Certifications, and Awards",
                )
    if positions.get("resume_transition") != len(blocks) - 1:
        _fail("invalid_semantic_order", "Résumé transition must be the final block")


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in record.items()
        if key not in {"owner_key", "private_notes"}
    }


def _public_media(media: dict[str, Any]) -> dict[str, Any]:
    alt = media.get("alt")
    decorative = media.get("decorative", False)
    if not decorative and (not isinstance(alt, str) or not alt.strip()):
        _fail("missing_media_alt", f"media {media.get('id')!r} needs alt text")
    return {
        "src": _required_text(media, "src", "media"),
        "alt": "" if decorative else alt.strip(),
        "decorative": bool(decorative),
        "focal": _optional_text(media.get("focal")) or "50% 50%",
        "truth_label": _required_text(media, "truth_label", "media"),
    }


def _proof_variant(count: int) -> str:
    return {
        0: "omitted",
        1: "feature",
        2: "pair",
        3: "equal-three",
        4: "equal-four",
    }.get(count, "invalid")


def _build_navigation(
    block_by_definition: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    navigation = [{"label": "Overview", "destination": "#overview"}]
    for definition_id, label, destination in (
        ("impact", "Impact", "#impact"),
        ("skills", "Skills", "#skills"),
        ("career", "Experience", "#experience"),
    ):
        if definition_id in block_by_definition:
            navigation.append({"label": label, "destination": destination})
    if any(
        definition_id in block_by_definition
        for definition_id in ("education", "certifications", "awards")
    ):
        navigation.append({"label": "Credentials", "destination": "#credentials"})
    return navigation


def _required_text(container: dict[str, Any], key: str, context: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        _fail("missing_text", f"{context}.{key} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail("invalid_text", "optional text values must be strings")
    value = value.strip()
    return value or None
