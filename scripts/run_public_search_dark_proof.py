"""Fail-closed Search 3F reference tooling.

The default command is a zero-network plan.  This module does not provision,
publish, query, or rerun the historical proof.  Its only live mutation path is
an explicitly confirmed, manifest-bound teardown of the temporary proof
resources.  Tests inject transports and never contact Azure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence
from urllib.parse import urlparse


PACKAGE_ID = "PS-SEARCH-DARK-PROOF-001"
HISTORICAL_EXECUTION_API_VERSION = "2024-07-01"
FUTURE_CONTRACT_API_VERSION = "2026-04-01"
PRIMARY_INDEX = "peerslate-public-content-v1"
REHEARSAL_INDEX = "peerslate-public-content-v999"
EXPECTED_RESOURCE_GROUP = "peerslate"
EXPECTED_SEARCH_SERVICE = "proj-default-srch-f0z1"
EXPECTED_SEARCH_ENDPOINT = "https://proj-default-srch-f0z1.search.windows.net"
EXPECTED_CREATED_AT = "2026-08-16T19:05:00-05:00"
EXPECTED_TEARDOWN_AT = "2026-08-23T23:59:00-05:00"
# SHA-256 of lower-cased, high-entropy private identifiers from the pre-authorized
# historical cleanup record. The identifiers themselves remain outside Git.
EXPECTED_APPLICATION_ID_SHA256 = (
    "289329014732b65feb7333388cfcf9917f9fe7949c0e047d34536eb91b69fa9a",
    "cb05d97a79734f0268c03c7d81b2f4696e25113df02aca937a5aac06578c3524",
)
EXPECTED_ROLE_ASSIGNMENT_ID_SHA256 = (
    "dc16fb4c65b8fd809a0dc175dcaf85a3cae8413fcd38f0ca085ff44c2c2f0ac0",
    "b08d0dc51bd523dac0f7a59106dcc7507235288b905b5b07c795645612f269bb",
)
EXPECTED_ROLE_DEFINITION_IDS = (
    "8ebe5a00-799e-43f5-93ac-243d3dce84a7",  # Search Index Data Contributor
    "1407120a-92aa-4202-b7e9-c0e197c71c8f",  # Search Index Data Reader
)
INDEX_ALLOW_PATTERN = re.compile(r"^peerslate-public-content-v[0-9]{1,3}$")
INDEX_DENY_PATTERN = re.compile(r"^ask-pete", re.IGNORECASE)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(r"^<[^<>]+>$")

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "docs" / "initiatives" / PACKAGE_ID
DEFAULT_FIXTURE_MANIFEST = PACKAGE_ROOT / "fixtures" / "public-content-proof-manifest.json"
DEFAULT_CLEANUP_TEMPLATE = PACKAGE_ROOT / "fixtures" / "cleanup-manifest.template.json"

RESULT_TYPES = frozenset(
    {"profile", "experience", "impact", "skill", "credential", "story_chapter"}
)
INDEX_FIELDS = (
    "document_id",
    "profile_key",
    "profile_slug",
    "member_display_name",
    "audience",
    "publication_revision_key",
    "projection_version_key",
    "projection_key",
    "projection_digest",
    "result_type",
    "destination",
    "title",
    "summary",
    "search_text",
    "aliases",
    "period_label",
    "locale",
    "title_sort",
    "schema_version",
    "indexed_at",
)
SEARCH_FIELDS = (
    "title",
    "summary",
    "search_text",
    "aliases",
    "member_display_name",
)
DIGEST_FIELDS = (
    "aliases",
    "destination",
    "locale",
    "member_display_name",
    "period_label",
    "profile_slug",
    "result_type",
    "search_text",
    "summary",
    "title",
    "title_sort",
)
PUBLIC_OUTPUT_FIELDS = (
    "destination",
    "member_display_name",
    "period_label",
    "profile_slug",
    "result_type",
    "summary",
    "title",
)
CANONICAL_MATCH_FIELDS = tuple(
    field_name for field_name in INDEX_FIELDS if field_name != "projection_digest"
)
FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "answers",
        "captions",
        "semanticconfiguration",
        "semanticquery",
        "vectorfiltermode",
        "vectorqueries",
        "vectors",
    }
)

QUERY_PAGE_SIZE = 20
MAX_QUERY_CANDIDATES = 200
PUBLIC_RESULT_LIMIT = 6


class ContractError(ValueError):
    """The local manifest, query, result, or cleanup contract is invalid."""


class CeilingError(RuntimeError):
    """A request was refused before dispatch because a persistent ceiling was reached."""


class ExecutionRefused(RuntimeError):
    """A live operation was not explicitly and validly authorized."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    for attempt in range(5):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.01 * (attempt + 1))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    return sha256_text(_canonical_json(manifest))


def _normalize_string(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _canonical_value(field_name: str, value: Any) -> Any:
    if field_name == "aliases" and isinstance(value, list):
        return sorted(_normalize_string(item) for item in value)
    if isinstance(value, str):
        return _normalize_string(value)
    return value


def canonical_digest(document: Mapping[str, Any]) -> str:
    """Return canonical content digest cv1.

    Optional ``None`` fields are absent, aliases are NFC-normalized and sorted,
    all other strings are NFC-normalized, and compact sorted-key JSON is hashed.
    """

    canonical: dict[str, Any] = {}
    for field_name in DIGEST_FIELDS:
        value = document.get(field_name)
        if value is None:
            continue
        if field_name == "aliases":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ContractError("aliases must be a list of strings")
            value = sorted(_normalize_string(item) for item in value)
        elif isinstance(value, str):
            value = _normalize_string(value)
        canonical[field_name] = value
    return "cv1:" + sha256_text(_canonical_json(canonical))


def _require_exact_keys(
    value: Mapping[str, Any], expected: Iterable[str], label: str
) -> None:
    actual = set(value)
    expected_set = set(expected)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        extra = sorted(actual - expected_set)
        raise ContractError(f"{label} keys differ; missing={missing}, extra={extra}")


def validate_fixture_manifest(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    required_top = {
        "manifest",
        "canonicalization",
        "member_count",
        "document_count",
        "content_digest_root",
        "slot_owners",
        "documents",
    }
    _require_exact_keys(manifest, required_top, "fixture manifest")
    if "SYNTHETIC" not in str(manifest["manifest"]).upper():
        raise ContractError("fixture manifest must be labelled synthetic")
    documents = manifest["documents"]
    owners = manifest["slot_owners"]
    if not isinstance(documents, list) or not isinstance(owners, dict):
        raise ContractError("documents and slot_owners have invalid shapes")
    if manifest["document_count"] != len(documents) or len(documents) > 250:
        raise ContractError("document count is inconsistent or above the ceiling")
    document_ids: set[str] = set()
    projection_keys: set[str] = set()
    profile_keys: set[str] = set()
    digests: list[str] = []
    expected_document_keys = set(INDEX_FIELDS) | {"withdrawn"}
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ContractError(f"document {index} is not an object")
        _require_exact_keys(document, expected_document_keys, f"document {index}")
        if document["audience"] != "public" or document["schema_version"] != "1":
            raise ContractError(f"document {index} is outside the public schema boundary")
        if document["result_type"] not in RESULT_TYPES:
            raise ContractError(f"document {index} has an invalid result type")
        if not isinstance(document["withdrawn"], bool):
            raise ContractError(f"document {index} withdrawn state must be boolean")
        document_id = document["document_id"]
        projection_key = document["projection_key"]
        profile_key = document["profile_key"]
        if not isinstance(document_id, str) or not document_id.startswith("d1_"):
            raise ContractError(f"document {index} is outside the synthetic namespace")
        if document_id in document_ids or projection_key in projection_keys:
            raise ContractError("document_id and projection_key must be unique")
        if owners.get(projection_key) != profile_key:
            raise ContractError(f"slot owner mismatch for {projection_key}")
        expected_digest = canonical_digest(document)
        if document["projection_digest"] != expected_digest:
            raise ContractError(f"projection digest mismatch for {projection_key}")
        document_ids.add(document_id)
        projection_keys.add(projection_key)
        profile_keys.add(profile_key)
        digests.append(expected_digest)
    if set(owners) != projection_keys:
        raise ContractError("slot_owners must enumerate exactly the fixture projections")
    if manifest["member_count"] != len(profile_keys):
        raise ContractError("member_count is inconsistent")
    expected_root = sha256_text("".join(sorted(digests)))
    if manifest["content_digest_root"] != expected_root:
        raise ContractError("content_digest_root does not reproduce")
    return manifest


def load_fixture_manifest(path: Path = DEFAULT_FIXTURE_MANIFEST) -> Mapping[str, Any]:
    return validate_fixture_manifest(json.loads(path.read_text(encoding="utf-8")))


def schema_body(index_name: str = PRIMARY_INDEX) -> dict[str, Any]:
    guard_index_name(index_name)
    string = "Edm.String"

    def field_def(
        name: str,
        field_type: str = string,
        *,
        key: bool = False,
        searchable: bool = False,
        filterable: bool = False,
        sortable: bool = False,
        analyzer: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": name,
            "type": field_type,
            "key": key,
            "searchable": searchable,
            "filterable": filterable,
            "retrievable": True,
            "stored": True,
            "sortable": sortable,
            "facetable": False,
        }
        if analyzer:
            result["analyzer"] = analyzer
        return result

    return {
        "name": index_name,
        "fields": [
            field_def("document_id", key=True, filterable=True, sortable=True),
            field_def("profile_key", filterable=True),
            field_def("profile_slug", filterable=True),
            field_def("member_display_name", searchable=True, analyzer="en.microsoft"),
            field_def("audience", filterable=True),
            field_def("publication_revision_key", filterable=True),
            field_def("projection_version_key", filterable=True),
            field_def("projection_key", filterable=True),
            field_def("projection_digest", filterable=True),
            field_def("result_type", filterable=True),
            field_def("destination", filterable=True),
            field_def("title", searchable=True, analyzer="en.microsoft"),
            field_def("summary", searchable=True, analyzer="en.microsoft"),
            field_def("search_text", searchable=True, analyzer="en.microsoft"),
            field_def(
                "aliases",
                "Collection(Edm.String)",
                searchable=True,
                analyzer="en.microsoft",
            ),
            field_def("period_label"),
            field_def("locale", filterable=True),
            field_def("title_sort", sortable=True),
            field_def("schema_version", filterable=True),
            field_def("indexed_at", "Edm.DateTimeOffset", filterable=True, sortable=True),
        ],
        "semantic": None,
        "vectorSearch": None,
    }


def validate_index_schema(schema: Mapping[str, Any]) -> None:
    if schema.get("name") != PRIMARY_INDEX:
        raise ContractError("schema targets the wrong index")
    fields = schema.get("fields")
    if not isinstance(fields, list) or [item.get("name") for item in fields] != list(INDEX_FIELDS):
        raise ContractError("schema must contain the canonical 20 fields in order")
    if schema.get("semantic") is not None or schema.get("vectorSearch") is not None:
        raise ContractError("semantic and vector configuration are forbidden")
    by_name = {item["name"]: item for item in fields}
    if sum(bool(item.get("searchable")) for item in fields) != 5:
        raise ContractError("schema must have exactly five searchable fields")
    if sum(bool(item.get("filterable")) for item in fields) != 13:
        raise ContractError("schema must have exactly thirteen filterable fields")
    if sum(bool(item.get("sortable")) for item in fields) != 3:
        raise ContractError("schema must have exactly three sortable fields")
    if any(item.get("facetable") for item in fields):
        raise ContractError("faceting is forbidden")
    if not all(item.get("retrievable") is True and item.get("stored") is True for item in fields):
        raise ContractError("retrievable/stored truth must be explicit for all fields")
    if not by_name["document_id"].get("key"):
        raise ContractError("document_id must be the key")


def normalize_query(query: str) -> str:
    normalized = " ".join(_normalize_string(query).split())
    if not normalized or len(normalized) > 200:
        raise ContractError("query must contain 1-200 normalized characters")
    return normalized


def build_query_body(query: str, *, skip: int = 0, top: int = QUERY_PAGE_SIZE) -> dict[str, Any]:
    if skip < 0 or skip >= MAX_QUERY_CANDIDATES:
        raise ContractError("skip is outside the bounded paging window")
    if top < 1 or top > QUERY_PAGE_SIZE or skip + top > MAX_QUERY_CANDIDATES:
        raise ContractError("top is outside the bounded paging window")
    body = {
        "search": normalize_query(query),
        "queryType": "simple",
        "searchMode": "all",
        "searchFields": ",".join(SEARCH_FIELDS),
        "select": ",".join(INDEX_FIELDS),
        "filter": "audience eq 'public' and schema_version eq '1'",
        "orderby": "search.score() desc,document_id asc",
        "top": top,
        "skip": skip,
    }
    assert_request_contract(body)
    return body


def _walk_request(value: Any, keys: list[str], values: list[tuple[str, Any]]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            keys.append(key_text)
            values.append((key_text, child))
            _walk_request(child, keys, values)
    elif isinstance(value, list):
        for child in value:
            _walk_request(child, keys, values)


def _body_shape(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _body_shape(child) for key, child in sorted(value.items())}
    if isinstance(value, list):
        return ["list", len(value), *[_body_shape(child) for child in value[:3]]]
    if value is None:
        return "null"
    return type(value).__name__


def assert_request_contract(body: Mapping[str, Any]) -> None:
    keys: list[str] = []
    values: list[tuple[str, Any]] = []
    _walk_request(body, keys, values)
    folded = {key.casefold() for key in keys}
    forbidden = sorted(folded & FORBIDDEN_REQUEST_KEYS)
    if forbidden:
        raise ContractError(f"semantic/vector request keys are forbidden: {forbidden}")
    for key, value in values:
        if key.casefold() == "querytype" and value != "simple":
            raise ContractError("queryType must be pinned to simple")
    if body.get("queryType") != "simple" or body.get("searchMode") != "all":
        raise ContractError("lexical query pins are missing")
    if body.get("filter") != "audience eq 'public' and schema_version eq '1'":
        raise ContractError("public audience/schema filter is missing")
    if body.get("searchFields") != ",".join(SEARCH_FIELDS):
        raise ContractError("searchFields must be the explicit lexical field list")
    if body.get("select") != ",".join(INDEX_FIELDS):
        raise ContractError("select must be the explicit canonical field list")
    if body.get("orderby") != "search.score() desc,document_id asc":
        raise ContractError("deterministic orderby is missing")


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[float, str]:
    score = candidate.get("@search.score", 0.0)
    if not isinstance(score, (int, float)):
        score = 0.0
    return (-float(score), str(candidate.get("document_id", "")))


def fence_candidates(
    candidates: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """Apply the full local publication fence and return deterministic candidates."""

    validate_fixture_manifest(manifest)
    canonical = {item["projection_key"]: item for item in manifest["documents"]}
    owners = manifest["slot_owners"]
    accepted: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        projection_key = candidate.get("projection_key")
        source = canonical.get(projection_key)
        if source is None or owners.get(projection_key) != source["profile_key"]:
            continue
        if source["withdrawn"] is not False:
            continue
        if candidate.get("audience") != "public" or candidate.get("schema_version") != "1":
            continue
        if candidate.get("result_type") not in RESULT_TYPES:
            continue
        if candidate.get("profile_key") != owners[projection_key]:
            continue
        if any(
            _canonical_value(name, candidate.get(name))
            != _canonical_value(name, source.get(name))
            for name in CANONICAL_MATCH_FIELDS
        ):
            continue
        try:
            digest = canonical_digest(candidate)
        except ContractError:
            continue
        if digest != source["projection_digest"]:
            continue
        if candidate.get("projection_digest") != source["projection_digest"]:
            continue
        document_id = source["document_id"]
        existing = accepted.get(document_id)
        if existing is None or _candidate_sort_key(candidate) < _candidate_sort_key(existing):
            accepted[document_id] = candidate
    return sorted(accepted.values(), key=_candidate_sort_key)


def serialize_public_results(
    fenced: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Construct exact public output from local canonical projections only."""

    canonical = {item["projection_key"]: item for item in manifest["documents"]}
    output: list[dict[str, Any]] = []
    for candidate in fenced[:PUBLIC_RESULT_LIMIT]:
        source = canonical.get(candidate.get("projection_key"))
        if source is None or source.get("withdrawn") is not False:
            continue
        output.append({name: source.get(name) for name in PUBLIC_OUTPUT_FIELDS})
    return output


def collect_fenced_results(
    fetch_page: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]],
    query: str,
    manifest: Mapping[str, Any],
    *,
    page_size: int = QUERY_PAGE_SIZE,
    max_candidates: int = MAX_QUERY_CANDIDATES,
    result_limit: int = PUBLIC_RESULT_LIMIT,
) -> list[dict[str, Any]]:
    if page_size < 1 or page_size > QUERY_PAGE_SIZE:
        raise ContractError("page_size is outside the contract")
    if max_candidates < page_size or max_candidates > MAX_QUERY_CANDIDATES:
        raise ContractError("max_candidates is outside the contract")
    collected: list[Mapping[str, Any]] = []
    skip = 0
    while skip < max_candidates:
        top = min(page_size, max_candidates - skip)
        body = build_query_body(query, skip=skip, top=top)
        page = list(fetch_page(body))
        if len(page) > top:
            raise ContractError("fetch_page returned more candidates than requested")
        collected.extend(page)
        if len(fence_candidates(collected, manifest)) >= result_limit:
            break
        if len(page) < top:
            break
        skip += top
    fenced = fence_candidates(collected, manifest)[:result_limit]
    return serialize_public_results(fenced, manifest)


@dataclass
class RequestCensus:
    path: Path | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)

    def _persist(self) -> None:
        if self.path is None:
            return
        _atomic_write_text(self.path, json.dumps(self.rows, indent=2))

    def before_dispatch(
        self,
        *,
        transport: str,
        operation: str,
        method: str,
        target: str,
        api_version: str | None = None,
        body: Mapping[str, Any] | None = None,
        argv_shape: Sequence[str] | None = None,
    ) -> int:
        body = body or {}
        keys: list[str] = []
        values: list[tuple[str, Any]] = []
        _walk_request(body, keys, values)
        if body:
            assert_request_contract(body)
        row = {
            "sequence": len(self.rows) + 1,
            "dispatch": "authorized_pre_dispatch",
            "transport": transport,
            "operation": operation,
            "method": method,
            "target_sha256": sha256_text(target),
            "api_version": api_version,
            "body_keys": sorted(set(keys)),
            "body_bytes": len(_canonical_json(body).encode("utf-8")) if body else 0,
            "body_shape_sha256": sha256_text(_canonical_json(_body_shape(body))) if body else None,
            "query_type": body.get("queryType"),
            "semantic_or_vector": False,
            "argv_shape": list(argv_shape or []),
            "status": None,
        }
        self.rows.append(row)
        self._persist()
        return len(self.rows) - 1

    def finish(self, row_index: int, status: int | str) -> None:
        self.rows[row_index]["status"] = status
        self.rows[row_index]["dispatch"] = "completed"
        self._persist()


@dataclass
class PersistentBudget:
    manifest_sha256: str
    state_path: Path | None = None
    max_index_requests: int = 500
    max_query_requests: int = 500
    max_process_requests: int = 100
    max_request_bytes: int = 10 * 1024 * 1024
    max_documents: int = 250
    max_wall_seconds: int = 30 * 60
    now_monotonic: Callable[[], float] = time.monotonic
    started_monotonic: float = field(init=False)
    counts: MutableMapping[str, int] = field(init=False)

    def __post_init__(self) -> None:
        self.started_monotonic = self.now_monotonic()
        self.counts = {
            "index_requests": 0,
            "query_requests": 0,
            "process_requests": 0,
            "request_bytes": 0,
            "documents": 0,
        }
        if self.state_path and self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if state.get("manifest_sha256") != self.manifest_sha256:
                raise ContractError("budget state is bound to a different cleanup manifest")
            stored = state.get("counts")
            if not isinstance(stored, dict) or set(stored) != set(self.counts):
                raise ContractError("budget state has an invalid shape")
            if not all(isinstance(value, int) and value >= 0 for value in stored.values()):
                raise ContractError("budget state counters are invalid")
            self.counts.update(stored)

    def _persist(self) -> None:
        if self.state_path is None:
            return
        _atomic_write_text(
            self.state_path,
            json.dumps(
                {"manifest_sha256": self.manifest_sha256, "counts": self.counts},
                indent=2,
            ),
        )

    def authorize(self, kind: str, *, request_bytes: int = 0, documents: int = 0) -> None:
        if self.now_monotonic() - self.started_monotonic > self.max_wall_seconds:
            raise CeilingError("wall-clock ceiling reached before dispatch")
        projected = dict(self.counts)
        counter = {
            "index": "index_requests",
            "query": "query_requests",
            "process": "process_requests",
        }.get(kind)
        if counter is None:
            raise ContractError(f"unknown budget kind: {kind}")
        projected[counter] += 1
        projected["request_bytes"] += request_bytes
        projected["documents"] += documents
        limits = {
            "index_requests": self.max_index_requests,
            "query_requests": self.max_query_requests,
            "process_requests": self.max_process_requests,
            "request_bytes": self.max_request_bytes,
            "documents": self.max_documents,
        }
        exceeded = [name for name, limit in limits.items() if projected[name] > limit]
        if exceeded:
            raise CeilingError(f"persistent ceiling reached before dispatch: {exceeded}")
        self.counts.update(projected)
        self._persist()


def guard_index_name(index_name: str) -> str:
    if INDEX_DENY_PATTERN.search(index_name) or not INDEX_ALLOW_PATTERN.fullmatch(index_name):
        raise ContractError(f"refused index name: {index_name!r}")
    return index_name


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER_PATTERN.fullmatch(value))


def _contains_placeholder(value: Any) -> bool:
    if _is_placeholder(value):
        return True
    if isinstance(value, Mapping):
        return any(_contains_placeholder(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(child) for child in value)
    return False


def _require_uuid(value: Any, label: str, *, allow_placeholders: bool) -> str:
    if allow_placeholders and _is_placeholder(value):
        return str(value)
    if not isinstance(value, str) or not UUID_PATTERN.fullmatch(value):
        raise ContractError(f"{label} must be a UUID")
    return value


def _parse_time(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be an ISO-8601 timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ContractError(f"{label} must include an offset")
    return parsed


def validate_cleanup_manifest(
    manifest: Mapping[str, Any], *, allow_placeholders: bool
) -> Mapping[str, Any]:
    required_top = {
        "schema_version",
        "package",
        "classification",
        "historical_execution_api_version",
        "future_contract_api_version",
        "created_at",
        "teardown_not_before",
        "expires_at",
        "authorization",
        "service",
        "targets",
        "confirmation_phrase_sha256",
        "never_delete",
    }
    _require_exact_keys(manifest, required_top, "cleanup manifest")
    if manifest["schema_version"] != 3 or manifest["package"] != PACKAGE_ID:
        raise ContractError("cleanup manifest identity is invalid")
    if manifest["classification"] != "PRIVATE_OPERATOR_ONLY_DO_NOT_COMMIT_FILLED_COPY":
        raise ContractError("cleanup manifest classification is invalid")
    if manifest["historical_execution_api_version"] != HISTORICAL_EXECUTION_API_VERSION:
        raise ContractError("historical API pin is incorrect")
    if manifest["future_contract_api_version"] != FUTURE_CONTRACT_API_VERSION:
        raise ContractError("future API pin is incorrect")
    created = _parse_time(manifest["created_at"], "created_at")
    not_before = _parse_time(manifest["teardown_not_before"], "teardown_not_before")
    expires = _parse_time(manifest["expires_at"], "expires_at")
    if not created < not_before <= expires:
        raise ContractError("cleanup timing must satisfy created < not_before <= expires")
    if (
        manifest["created_at"] != EXPECTED_CREATED_AT
        or manifest["teardown_not_before"] != EXPECTED_TEARDOWN_AT
        or manifest["expires_at"] != EXPECTED_TEARDOWN_AT
    ):
        raise ContractError("cleanup timing differs from the pre-authorized fixed dates")
    authorization = manifest["authorization"]
    _require_exact_keys(
        authorization,
        {"authorized_by", "decision_date", "action", "extension_allowed"},
        "cleanup authorization",
    )
    if (
        authorization["authorized_by"] != "Pete"
        or authorization["decision_date"] != "2026-08-16"
        or authorization["action"] != "teardown_exact_targets"
        or authorization["extension_allowed"] is not False
    ):
        raise ContractError("cleanup authorization must be teardown-only with no silent extension")
    service = manifest["service"]
    _require_exact_keys(
        service,
        {"subscription_id", "tenant_id", "resource_group", "name", "endpoint"},
        "service",
    )
    subscription_id = _require_uuid(
        service["subscription_id"], "subscription_id", allow_placeholders=allow_placeholders
    )
    _require_uuid(service["tenant_id"], "tenant_id", allow_placeholders=allow_placeholders)
    if service["resource_group"] != EXPECTED_RESOURCE_GROUP:
        raise ContractError("cleanup targets the wrong resource group")
    if service["name"] != EXPECTED_SEARCH_SERVICE:
        raise ContractError("cleanup targets the wrong Search service")
    if service["endpoint"] != EXPECTED_SEARCH_ENDPOINT:
        raise ContractError("cleanup targets the wrong Search endpoint")
    targets = manifest["targets"]
    _require_exact_keys(
        targets,
        {
            "index_name",
            "role_assignment_resource_ids",
            "service_principal_object_ids",
            "application_ids",
        },
        "cleanup targets",
    )
    index_name = guard_index_name(targets["index_name"])
    if index_name != PRIMARY_INDEX:
        raise ContractError("cleanup may target only the primary proof index")
    role_ids = targets["role_assignment_resource_ids"]
    sp_ids = targets["service_principal_object_ids"]
    app_ids = targets["application_ids"]
    if not isinstance(role_ids, list) or len(role_ids) != 2:
        raise ContractError("exactly two role assignments are required")
    if not isinstance(sp_ids, list) or len(sp_ids) != 2:
        raise ContractError("exactly two service principals are required")
    if not isinstance(app_ids, list) or len(app_ids) != 2:
        raise ContractError("exactly two application registrations are required")
    expected_scope = (
        f"/subscriptions/{subscription_id}/resourceGroups/{service['resource_group']}"
        f"/providers/Microsoft.Search/searchServices/{service['name']}/indexes/{index_name}"
        "/providers/Microsoft.Authorization/roleAssignments/"
    )
    for index, role_id in enumerate(role_ids):
        if allow_placeholders and _is_placeholder(role_id):
            continue
        if not isinstance(role_id, str) or not role_id.casefold().startswith(expected_scope.casefold()):
            raise ContractError(f"role assignment {index} is outside the exact index scope")
        _require_uuid(role_id.rsplit("/", 1)[-1], f"role assignment {index}", allow_placeholders=False)
        if sha256_text(role_id.casefold()) != EXPECTED_ROLE_ASSIGNMENT_ID_SHA256[index]:
            raise ContractError(f"role assignment {index} is not a pre-authorized target")
    for index, object_id in enumerate(sp_ids):
        _require_uuid(object_id, f"service principal {index}", allow_placeholders=allow_placeholders)
    for index, app_id in enumerate(app_ids):
        _require_uuid(app_id, f"application {index}", allow_placeholders=allow_placeholders)
        if not (allow_placeholders and _is_placeholder(app_id)):
            if sha256_text(app_id.casefold()) != EXPECTED_APPLICATION_ID_SHA256[index]:
                raise ContractError(f"application {index} is not a pre-authorized target")
    flattened = _canonical_json(manifest).casefold()
    if "ask-pete" in flattened or "ask_pete" in flattened:
        raise ContractError("cleanup manifest must not target or name Ask Pete")
    if len(set(role_ids)) != len(role_ids) or len(set(sp_ids)) != len(sp_ids) or len(set(app_ids)) != len(app_ids):
        raise ContractError("cleanup targets must be unique")
    phrase_hash = manifest["confirmation_phrase_sha256"]
    if allow_placeholders and _is_placeholder(phrase_hash):
        pass
    elif not isinstance(phrase_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", phrase_hash):
        raise ContractError("confirmation phrase hash is invalid")
    if manifest["never_delete"] != [
        "search_service",
        "resource_group",
        "pre_existing_role_assignments",
        "pre_existing_indexes",
    ]:
        raise ContractError("never_delete contract differs")
    if not allow_placeholders and _contains_placeholder(manifest):
        raise ContractError("filled cleanup manifest still contains placeholders")
    return manifest


def build_teardown_plan(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_cleanup_manifest(manifest, allow_placeholders=True)
    targets = manifest["targets"]
    return {
        "mode": "ZERO_NETWORK_PLAN",
        "package": PACKAGE_ID,
        "historical_execution_api_version": HISTORICAL_EXECUTION_API_VERSION,
        "future_contract_api_version": FUTURE_CONTRACT_API_VERSION,
        "manifest_sha256": manifest_fingerprint(manifest),
        "teardown_not_before": manifest["teardown_not_before"],
        "expires_at": manifest["expires_at"],
        "ordered_steps": [
            {"action": "preflight_exact_targets", "count": 7},
            {"action": "delete_role_assignment", "count": len(targets["role_assignment_resource_ids"])},
            {"action": "delete_index", "count": 1},
            {"action": "verify_index_absent", "count": 1},
            {"action": "delete_service_principal", "count": len(targets["service_principal_object_ids"])},
            {"action": "delete_application_registration", "count": len(targets["application_ids"])},
            {"action": "verify_identity_targets_absent", "count": len(targets["service_principal_object_ids"]) + len(targets["application_ids"])},
        ],
        "target_fingerprints": {
            "index": sha256_text(targets["index_name"]),
            "role_assignments": [sha256_text(value) for value in targets["role_assignment_resource_ids"]],
            "service_principals": [sha256_text(value) for value in targets["service_principal_object_ids"]],
            "applications": [sha256_text(value) for value in targets["application_ids"]],
        },
        "network_dispatched": False,
    }


class LiveTransport:
    """Explicit live transport used only by the teardown command."""

    def __init__(self, budget: PersistentBudget, census: RequestCensus) -> None:
        self.budget = budget
        self.census = census

    def process(
        self,
        argv: Sequence[str],
        *,
        operation: str,
        target: str,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.budget.authorize("process")
        row = self.census.before_dispatch(
            transport="azure_cli",
            operation=operation,
            method="EXEC",
            target=target,
            argv_shape=[argv[0], argv[1], argv[2] if len(argv) > 2 else ""],
        )
        completed = subprocess.run(argv, text=True, capture_output=True, check=False)
        self.census.finish(row, completed.returncode)
        if completed.returncode and not allow_failure:
            raise RuntimeError(f"{operation} failed with exit code {completed.returncode}")
        return completed

    def http(
        self,
        method: str,
        url: str,
        *,
        operation: str,
        target: str,
        token: str,
        body: Mapping[str, Any] | None = None,
        allowed_statuses: Sequence[int] = (200,),
    ) -> Any:
        import requests

        payload_bytes = len(_canonical_json(body).encode("utf-8")) if body else 0
        self.budget.authorize("index", request_bytes=payload_bytes)
        row = self.census.before_dispatch(
            transport="https",
            operation=operation,
            method=method,
            target=target,
            api_version=FUTURE_CONTRACT_API_VERSION,
            body=body,
        )
        response = requests.request(
            method,
            url,
            params={"api-version": FUTURE_CONTRACT_API_VERSION},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=(5, 30),
        )
        self.census.finish(row, response.status_code)
        if response.status_code not in allowed_statuses:
            raise RuntimeError(f"{operation} returned HTTP {response.status_code}")
        return response


def _ensure_teardown_time(manifest: Mapping[str, Any], now: dt.datetime) -> None:
    if now.tzinfo is None:
        raise ContractError("now must be timezone-aware")
    not_before = _parse_time(manifest["teardown_not_before"], "teardown_not_before")
    if now < not_before:
        raise ExecutionRefused("teardown is not authorized before teardown_not_before")
    # Deliberately no upper-bound refusal: cleanup remains executable after expiry.


def _json_list(
    completed: subprocess.CompletedProcess[str], *, label: str
) -> list[Any]:
    try:
        rows = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} check returned invalid JSON") from exc
    if not isinstance(rows, list):
        raise RuntimeError(f"{label} check returned a non-list result")
    return rows


def _listed_identifier_exists(
    completed: subprocess.CompletedProcess[str],
    *,
    identifier: str,
    fields: Sequence[str],
    label: str,
) -> bool:
    rows = _json_list(completed, label=label)
    expected = identifier.casefold()
    return any(
        isinstance(row, dict)
        and any(
            isinstance(row.get(field_name), str)
            and row[field_name].casefold() == expected
            for field_name in fields
        )
        for row in rows
    )


def _require_exact_target_row(
    rows: Sequence[Any],
    *,
    identifier: str,
    fields: Sequence[str],
    label: str,
) -> Mapping[str, Any]:
    expected = identifier.casefold()
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and any(
            isinstance(row.get(field_name), str)
            and row[field_name].casefold() == expected
            for field_name in fields
        )
    ]
    if len(matches) != 1:
        raise ExecutionRefused(
            f"{label} must resolve to exactly one pre-authorized target; "
            f"found {len(matches)}"
        )
    return matches[0]


def execute_teardown(
    manifest: Mapping[str, Any],
    *,
    confirmation: str,
    state_path: Path,
    census_path: Path,
    now: dt.datetime | None = None,
    transport_factory: Callable[[PersistentBudget, RequestCensus], Any] = LiveTransport,
) -> dict[str, Any]:
    validate_cleanup_manifest(manifest, allow_placeholders=False)
    now = now or dt.datetime.now(dt.timezone.utc)
    _ensure_teardown_time(manifest, now)
    if sha256_text(confirmation) != manifest["confirmation_phrase_sha256"]:
        raise ExecutionRefused("confirmation phrase does not match the private manifest")
    fingerprint = manifest_fingerprint(manifest)
    census = RequestCensus(census_path)
    budget = PersistentBudget(fingerprint, state_path=state_path)
    transport = transport_factory(budget, census)
    targets = manifest["targets"]
    service = manifest["service"]

    role_rows_by_id: dict[str, Mapping[str, Any]] = {}
    for role_id in targets["role_assignment_resource_ids"]:
        role_scope = role_id.rsplit(
            "/providers/Microsoft.Authorization/roleAssignments/", 1
        )[0]
        listed = transport.process(
            [
                "az",
                "role",
                "assignment",
                "list",
                "--scope",
                role_scope,
                "--fill-role-definition-name",
                "false",
                "--fill-principal-name",
                "false",
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="preflight_role_assignment",
            target=role_id,
        )
        role_rows_by_id[role_id] = _require_exact_target_row(
            _json_list(listed, label="role assignment preflight"),
            identifier=role_id,
            fields=("id",),
            label="role assignment preflight",
        )

    for index, (object_id, app_id) in enumerate(
        zip(
            targets["service_principal_object_ids"],
            targets["application_ids"],
            strict=True,
        )
    ):
        listed_sp = transport.process(
            [
                "az",
                "ad",
                "sp",
                "list",
                "--filter",
                f"id eq '{object_id}'",
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="preflight_service_principal",
            target=object_id,
        )
        sp_rows = _json_list(listed_sp, label="service principal preflight")
        sp_row = _require_exact_target_row(
            sp_rows,
            identifier=object_id,
            fields=("id",),
            label=f"service principal preflight {index}",
        )
        if (
            not isinstance(sp_row.get("appId"), str)
            or sp_row["appId"].casefold() != app_id.casefold()
        ):
            raise ExecutionRefused(
                f"service principal {index} is not linked to its pre-authorized application"
            )
        listed_app = transport.process(
            [
                "az",
                "ad",
                "app",
                "list",
                "--app-id",
                app_id,
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="preflight_application",
            target=app_id,
        )
        app_rows = _json_list(listed_app, label="application preflight")
        _require_exact_target_row(
            app_rows,
            identifier=app_id,
            fields=("appId",),
            label=f"application preflight {index}",
        )

    for index, (role_id, object_id, expected_role_definition_id) in enumerate(
        zip(
            targets["role_assignment_resource_ids"],
            targets["service_principal_object_ids"],
            EXPECTED_ROLE_DEFINITION_IDS,
            strict=True,
        )
    ):
        row = role_rows_by_id[role_id]
        principal_id = row.get("principalId")
        role_definition_id = row.get("roleDefinitionId")
        if (
            not isinstance(principal_id, str)
            or principal_id.casefold() != object_id.casefold()
            or not isinstance(role_definition_id, str)
            or role_definition_id.rsplit("/", 1)[-1].casefold()
            != expected_role_definition_id.casefold()
        ):
            raise ExecutionRefused(
                f"role assignment {index} does not match the pre-authorized principal and role"
            )

    token_result = transport.process(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://search.azure.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        operation="acquire_search_teardown_token",
        target=service["tenant_id"],
    )
    token = token_result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned no Search token")
    index_name = guard_index_name(targets["index_name"])
    index_url = f"{service['endpoint']}/indexes/{index_name}"
    transport.http(
        "GET",
        index_url,
        operation="preflight_proof_index",
        target=index_name,
        token=token,
        allowed_statuses=(200, 404),
    )

    for role_id in targets["role_assignment_resource_ids"]:
        transport.process(
            ["az", "role", "assignment", "delete", "--ids", role_id, "--only-show-errors"],
            operation="delete_role_assignment",
            target=role_id,
            allow_failure=True,
        )
        role_scope = role_id.rsplit(
            "/providers/Microsoft.Authorization/roleAssignments/", 1
        )[0]
        verification = transport.process(
            [
                "az",
                "role",
                "assignment",
                "list",
                "--scope",
                role_scope,
                "--fill-role-definition-name",
                "false",
                "--fill-principal-name",
                "false",
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="verify_role_assignment_absent",
            target=role_id,
        )
        if _listed_identifier_exists(
            verification,
            identifier=role_id,
            fields=("id",),
            label="role assignment",
        ):
            raise RuntimeError("role assignment still exists after deletion")

    transport.http(
        "DELETE",
        index_url,
        operation="delete_proof_index",
        target=index_name,
        token=token,
        allowed_statuses=(204, 404),
    )
    transport.http(
        "GET",
        index_url,
        operation="verify_proof_index_absent",
        target=index_name,
        token=token,
        allowed_statuses=(404,),
    )

    for object_id in targets["service_principal_object_ids"]:
        transport.process(
            ["az", "ad", "sp", "delete", "--id", object_id, "--only-show-errors"],
            operation="delete_service_principal",
            target=object_id,
            allow_failure=True,
        )
        verification = transport.process(
            [
                "az",
                "ad",
                "sp",
                "list",
                "--filter",
                f"id eq '{object_id}'",
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="verify_service_principal_absent",
            target=object_id,
        )
        if _listed_identifier_exists(
            verification,
            identifier=object_id,
            fields=("id",),
            label="service principal",
        ):
            raise RuntimeError("service principal still exists after deletion")

    for app_id in targets["application_ids"]:
        transport.process(
            ["az", "ad", "app", "delete", "--id", app_id, "--only-show-errors"],
            operation="delete_application_registration",
            target=app_id,
            allow_failure=True,
        )
        verification = transport.process(
            [
                "az",
                "ad",
                "app",
                "list",
                "--app-id",
                app_id,
                "--only-show-errors",
                "-o",
                "json",
            ],
            operation="verify_application_absent",
            target=app_id,
        )
        if _listed_identifier_exists(
            verification,
            identifier=app_id,
            fields=("appId",),
            label="application",
        ):
            raise RuntimeError("application registration still exists after deletion")

    return {
        "result": "teardown_converged",
        "manifest_sha256": fingerprint,
        "completed_at": now.isoformat(),
        "census_path": str(census_path),
        "state_path": str(state_path),
        "target_counts": {
            "index": 1,
            "role_assignments": len(targets["role_assignment_resource_ids"]),
            "service_principals": len(targets["service_principal_object_ids"]),
            "application_registrations": len(targets["application_ids"]),
        },
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def build_plan(
    cleanup_manifest: Mapping[str, Any], fixture_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    validate_cleanup_manifest(cleanup_manifest, allow_placeholders=True)
    validate_fixture_manifest(fixture_manifest)
    schema = schema_body()
    validate_index_schema(schema)
    query = build_query_body("synthetic plan query")
    return {
        "mode": "ZERO_NETWORK_PLAN",
        "package": PACKAGE_ID,
        "network_dispatched": False,
        "fixture_manifest_sha256": manifest_fingerprint(fixture_manifest),
        "schema_sha256": manifest_fingerprint(schema),
        "query_contract_sha256": manifest_fingerprint(query),
        "cleanup": build_teardown_plan(cleanup_manifest),
        "limitations": [
            "historical proof ran at 2024-07-01; this plan does not rerun it",
            "shared-service permissions are not isolation",
            "Ask Pete evidence supports three counters only; structural digest is unverified",
            "member-facing search remains a separate Gate L2 package",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("plan", "validate", "teardown"), default="plan")
    parser.add_argument("--fixture-manifest", type=Path, default=DEFAULT_FIXTURE_MANIFEST)
    parser.add_argument("--cleanup-manifest", type=Path, default=DEFAULT_CLEANUP_TEMPLATE)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--census-file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cleanup_manifest = _load_json(args.cleanup_manifest)
    if args.command in {"plan", "validate"}:
        fixture_manifest = load_fixture_manifest(args.fixture_manifest)
        print(json.dumps(build_plan(cleanup_manifest, fixture_manifest), indent=2))
        return 0
    if not args.execute:
        print(json.dumps(build_teardown_plan(cleanup_manifest), indent=2))
        return 0
    if not args.confirm or args.state_file is None or args.census_file is None:
        raise ExecutionRefused(
            "live teardown requires --execute, --confirm, --state-file, and --census-file"
        )
    result = execute_teardown(
        cleanup_manifest,
        confirmation=args.confirm,
        state_path=args.state_file,
        census_path=args.census_file,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
