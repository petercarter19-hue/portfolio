"""Owner-scoped C10 member document/paste import for My Opportunities.

Route-free, Flask-free, provider-neutral, AI-free -- mirrors C3/C4/C5/C6
exactly: no Flask, no identity, no provider credentials, no network access of
its own.  A member's ``user_key`` is always the first, server-derived
argument on every member-facing method (:func:`_require_user_key`).

Two refusal layers are kept structurally distinct throughout this module
(doc 09 §4):

* **Pre-admission refusals** -- the submission is refused before any byte is
  accepted as member material.  No :class:`MemberImport` row is ever
  created; :func:`validate_paste`/:func:`validate_upload` raise
  :class:`MemberImportServiceError` directly and the calling command emits
  one content-free ``import_refused`` audit event (reason code only).
* **Post-admission pipeline outcomes** -- bytes were admitted; a
  :class:`MemberImport` row is persisted recording the truthful doc 06 §2
  outcome state.  The record can never appear complete; retry is always a
  NEW submission (retry-as-new, the C4 idiom), never an in-place re-run.

The deterministic decode/parse/extract pipeline (`§3.5`) never calls the AI
provider and never opens a network connection; the only network-capable
surface this module can ever reach is the C13-era :class:`FetchAdapter`,
resolved through a guarded dynamic import that is DISABLED unless both
feature flags are true and the (deliberately absent, at C10) adapter module
resolves (doc 14 design B, REC-08).
"""

from __future__ import annotations

import base64
import hashlib
import html
import importlib
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
import zlib
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Protocol, Sequence
from uuid import uuid4
from xml.etree import ElementTree

from .canonical_service import DATA_CLASSES

CONTRACT_VERSION = "1.0"
SANITIZER_VERSION = "c10-1"  # stamped on every record (doc 06 §3)

# ---------------------------------------------------------------------------
# Closed vocabularies (module constants; verbatim from doc 06/doc 02 -- the
# PS-MYOPP-006 SQL CHECK constraints must admit every literal below.  As
# C6's own header notes, what a file-content test can prove is
# literal-PRESENCE (each string appears as an ``N'...'`` substring in the
# forward migration DDL), not a full byte-equal reconstruction of every
# CHECK's value list; real catalog-shape verification is the disposable
# gate proof (outstanding; "gate": null in the registry entry until run).
# ---------------------------------------------------------------------------

# -- doc 02 §1 / doc 06 intake methods (url_fetch reserved for C13; schema
#    carries it now so C13 needs no migration) ------------------------------
INTAKE_PASTE = "paste"
INTAKE_UPLOAD = "upload"
INTAKE_URL_FETCH = "url_fetch"
INTAKE_METHODS = frozenset({INTAKE_PASTE, INTAKE_UPLOAD, INTAKE_URL_FETCH})

# -- doc 06 §2 outcome states, verbatim, closed (fetched/blocked are C13's
#    fetch-stage states; C10's paste/upload paths never emit them, but the
#    schema and this vocabulary carry them now) -----------------------------
OUTCOME_FETCHED = "fetched"
OUTCOME_DECODED = "decoded"
OUTCOME_PARSED = "parsed"
OUTCOME_EXTRACTED = "extracted"
OUTCOME_EMPTY = "empty"
OUTCOME_PARTIAL = "partial"
OUTCOME_BLOCKED = "blocked"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_REFUSED = "refused"
OUTCOME_STATES = frozenset(
    {
        OUTCOME_FETCHED, OUTCOME_DECODED, OUTCOME_PARSED, OUTCOME_EXTRACTED,
        OUTCOME_EMPTY, OUTCOME_PARTIAL, OUTCOME_BLOCKED, OUTCOME_TIMEOUT, OUTCOME_REFUSED,
    }
)
# A row's CURRENT/terminal outcome is one of these three when the pipeline
# reached a completed (not refused/timed out/blocked) end -- "empty" groups
# here because the pipeline itself completed cleanly, even though (per the
# text-pairing rule below) an empty outcome stores no text, same as a
# refusal.  See MemberImport.__post_init__.
TERMINAL_SUCCESS_STATES = frozenset({OUTCOME_EXTRACTED, OUTCOME_PARTIAL, OUTCOME_EMPTY})

# -- closed reason codes, paired to states (SQL CK byte-equal) -------------
REASON_COULD_NOT_DECODE = "could_not_decode"
REASON_PARSER_FAILURE = "parser_failure"
REASON_PARSER_RESOURCE_BOUNDS = "parser_resource_bounds"
REASON_ARCHIVE_BOMB_SUSPECTED = "archive_bomb_suspected"
REASON_HOSTILE_CHARACTERS = "hostile_characters"
REASON_OUTPUT_TRUNCATED = "output_truncated"
REASON_EXTRACTION_DEADLINE = "extraction_deadline"
# C13-reserved (schema-complete now; C10's own pipeline never emits these,
# but the CK carries them so C13 needs no migration -- doc 14 design B).
REASON_DENIED_ADDRESS = "denied_address"
REASON_SCHEME_REFUSED = "scheme_refused"
REASON_REDIRECT_REFUSED = "redirect_refused"
REASON_CONTENT_MISMATCH = "content_mismatch"
REASON_FETCH_DEADLINE = "fetch_deadline"
REASON_FETCH_TOO_LARGE = "fetch_too_large"

REASONS_BY_STATE = {
    OUTCOME_REFUSED: frozenset(
        {
            REASON_COULD_NOT_DECODE, REASON_PARSER_FAILURE, REASON_PARSER_RESOURCE_BOUNDS,
            REASON_ARCHIVE_BOMB_SUSPECTED, REASON_HOSTILE_CHARACTERS, REASON_FETCH_TOO_LARGE,
        }
    ),
    OUTCOME_PARTIAL: frozenset({REASON_OUTPUT_TRUNCATED}),
    OUTCOME_TIMEOUT: frozenset({REASON_EXTRACTION_DEADLINE, REASON_FETCH_DEADLINE}),
    OUTCOME_BLOCKED: frozenset(
        {REASON_DENIED_ADDRESS, REASON_SCHEME_REFUSED, REASON_REDIRECT_REFUSED, REASON_CONTENT_MISMATCH}
    ),
    # fetched/decoded/parsed/extracted/empty carry no reason code.
}

RECORD_STATE_ACTIVE = "active"
RECORD_STATE_DELETED = "deleted"
RECORD_STATES = frozenset({RECORD_STATE_ACTIVE, RECORD_STATE_DELETED})

BODY_REMOVAL_MEMBER_DELETE = "member_delete"
BODY_REMOVAL_RIGHTS_TAKEDOWN = "rights_takedown"
BODY_REMOVAL_REASONS = frozenset({BODY_REMOVAL_MEMBER_DELETE, BODY_REMOVAL_RIGHTS_TAKEDOWN})

RIGHTS_NONE = "none"
RIGHTS_TAKEDOWN_REQUIRED = "takedown_required"
RIGHTS_OBLIGATION_CLASSES = frozenset({RIGHTS_NONE, RIGHTS_TAKEDOWN_REQUIRED})

# Non-identifying host/address classes (doc 08 §4 / doc 12 §5) -- defined NOW
# so C13's audit reuses this closed set; C10's paste/upload paths always
# emit HOST_CLASS_NOT_APPLICABLE.
HOST_CLASS_NOT_APPLICABLE = "not_applicable"
HOST_CLASSES = frozenset(
    {
        "not_applicable", "public", "denied_loopback", "denied_private", "denied_link_local",
        "denied_cgnat", "denied_ula", "denied_metadata", "denied_other",
    }
)

# -- the prebuilt DISABLED fetch port (doc 14 design B; REC-08) ------------
FLAG_SURFACE = "PEERSLATE_MY_OPPORTUNITIES_ENABLED"
FLAG_URL_FETCH = "PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED"
FETCH_MODULE = "services.my_opportunities.member_url_fetch_service"
FETCH_FACTORY = "create_fetch_adapter"

# -- command vocabulary (ImportReceipt.command; closed, SQL CK byte-equal) -
COMMAND_SUBMIT_PASTE = "submit_paste"
COMMAND_SUBMIT_UPLOAD = "submit_upload"
COMMAND_IMPORT_FROM_URL = "import_from_url"
COMMAND_DELETE_IMPORT = "delete_import"
COMMANDS = frozenset(
    {COMMAND_SUBMIT_PASTE, COMMAND_SUBMIT_UPLOAD, COMMAND_IMPORT_FROM_URL, COMMAND_DELETE_IMPORT}
)

# -- closed audit event kinds (content-free; doc 08 §4, doc 12 §5) ---------
_AUDIT_EVENT_KINDS = frozenset(
    {
        "import_stored", "import_refused", "import_empty", "import_partial", "import_deleted",
        "import_body_removed_rights", "import_exported", "url_fetch_unavailable", "persistence_failure",
    }
)

_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_UPLOAD_CONTENT_TYPES = frozenset({"application/pdf", _DOCX_CONTENT_TYPE, "text/plain"})

# ---------------------------------------------------------------------------
# Bounds (v2 bounded-intake discipline, env-tunable idiom; C3/C5/C6 values
# reused verbatim for the shared fields).
# ---------------------------------------------------------------------------
MAX_USER_KEY_UTF16_UNITS = 300
MAX_IDEMPOTENCY_KEY_UTF16_UNITS = 200
MAX_IMPORT_KEY_UTF16_UNITS = 200
MAX_URL_UTF16_UNITS = 2048  # matches the submitted_url nvarchar(2048) column
MAX_PASTE_UTF16_UNITS = 20_000  # = v2 MAX_SOURCE_TEXT_UNITS discipline
MAX_EXTRACTED_TEXT_UNITS = 20_000  # single enforceable end-to-end cap

MAX_UPLOAD_BYTES = int(os.environ.get("MYOPP_IMPORT_UPLOAD_MAX_BYTES", str(15 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.environ.get("MYOPP_IMPORT_MAX_PDF_PAGES", "400"))
PDF_EXTRACTION_TIMEOUT_SECONDS = float(os.environ.get("MYOPP_IMPORT_PDF_TIMEOUT_SECONDS", "20"))
# Independent review, FOURTH round (2026-09-02) -- ARCHITECTURAL conclusion,
# not another patch. Three straight rounds tried to bound pypdf's PDF
# decompression from the OUTSIDE, in-process: a per-stream cap (round 1,
# missed the AGGREGATE across a page's fonts), a document-wide object-model
# walk (round 2, missed fonts nested in Form XObjects and multiplication
# across pages), a raw-byte-structure pre-scan plus a tracemalloc-polling
# watchdog (round 3, missed ObjStm/XRef streams reachable only via object
# resolution). Round 4 FALSIFIED both round-3 defenses directly, decisively:
# the raw scan is not a real PDF tokenizer -- an indirect ``/Filter N 0 R``
# (a filter name reached through ANOTHER indirect object, which the scan's
# own regex-based dictionary reader never resolves) makes a stream look
# unfiltered and skip decode-verification entirely (peaked 151 MiB), and a
# ``(...)`` string literal containing a stray ``>>`` inside a stream
# dictionary throws off the scan's own bracket-depth dictionary-end search,
# silently skipping the WHOLE object it belongs to (peaked 559 MiB); and the
# watchdog's coarse, Python-level polling cannot bound a C-level burst
# allocation or steady LINEAR accumulation across pypdf's own
# un-checkpointed internal resolution before the next poll even runs (over
# 1 GiB reached before a refusal -- memory that was genuinely, physically
# allocated in this process; an OOM risk, not a graceful in-process
# refusal). The conclusion: a regex/byte-scanner cannot re-derive the exact
# structure a real PDF parser interprets, and Python-level polling cannot
# preempt a C-level allocation burst. No amount of additional in-process
# pattern-matching converges -- this is not a bug in the round-3 code, it is
# a category error in the STRATEGY.
#
# The guarantee is now OS-ENFORCED PROCESS ISOLATION, not any in-process
# analysis: every PDF or DOCX parse+extract runs inside a short-lived,
# freshly-started CHILD PROCESS (see :func:`_run_isolated_parse_and_extract`
# / :func:`_subprocess_worker_main`), spawned via ``subprocess.run`` (a
# clean new interpreter -- never ``os.fork()`` from the live request
# worker, which would inherit Gunicorn/gevent state, open file descriptors,
# and database connections; that risk was correctly identified and rejected
# in round 3 and remains rejected here). The child attempts a best-effort
# hard memory ceiling on ITSELF via ``resource.setrlimit`` (RLIMIT_AS, or
# RLIMIT_DATA if that alone fails to even set) the INSTANT it starts, before
# touching any untrusted byte -- verified directly that a FRESH subprocess
# can attempt this even though the already-running, already-large parent
# process could not lower its own limit; also verified directly (this
# development environment is macOS/Darwin) that macOS itself does not
# actually enforce RLIMIT_AS/RLIMIT_DATA regardless of process freshness (a
# well-documented Darwin platform limitation, distinct from the earlier
# "process already too large" finding) -- the rlimit attempt is silently
# best-effort and NOT the load-bearing guarantee for that reason. The
# load-bearing guarantee is that the child's entire address space --
# whatever pypdf/zipfile/ElementTree allocate inside it, bounded or not --
# is reclaimed the instant the child exits, is killed, or the parent's wall-
# clock ``subprocess.run(..., timeout=...)`` fires; NONE of that memory is
# ever the request-serving worker process's own memory. A nonzero exit, a
# signal kill (OOM/SIGKILL/SIGSEGV), or a timeout are ALL mapped uniformly
# to the truthful, persisted ``refused · parser_resource_bounds`` outcome --
# never an uncaught crash out of ``submit_upload``.
#
# The round 1-3 in-process bounding this comment used to describe --
# _bounded_inflate, the per-page /Contents walk, the document-wide font-aux/
# XObject walk, the raw-structure byte scanner, and the tracemalloc
# watchdog -- has been REMOVED, not merely demoted: each was PROVEN
# insufficient in turn, and carrying disproven defenses forward would only
# cost complexity while implying a precision none of them actually have.
# One isolation boundary is the guarantee. The DOCX zip-bomb bounds
# (_safe_zip_member_names / _bounded_zip_read) are KEPT -- unlike pypdf's
# opaque internals, this module fully controls that zip read
# (``ZipExtFile.read(n)`` genuinely, verifiably stops decompression at
# ``n`` bytes, proven directly in round 1) -- as a cheap admission-time
# pre-filter, on top of, never instead of, the same subprocess isolation
# DOCX parsing now also runs inside.
MAX_SUBPROCESS_MEMORY_CEILING_BYTES = int(
    os.environ.get("MYOPP_IMPORT_MAX_SUBPROCESS_MEMORY_CEILING_BYTES", str(256 * 1024 * 1024))
)
SUBPROCESS_TIMEOUT_MARGIN_SECONDS = float(
    os.environ.get("MYOPP_IMPORT_SUBPROCESS_TIMEOUT_MARGIN_SECONDS", "10")
)
MAX_DOCX_ENTRIES = 2000
MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES = 60 * 1024 * 1024
MAX_DOCX_ENTRY_COMPRESSION_RATIO = 200
# MINOR 1 (2026-09-02 independent review): the 25 MiB general entry cap
# bounds the RAW bytes read, but ``word/document.xml`` is the one entry
# this module hands to ``ElementTree.fromstring`` for a full DOM parse, and
# that amplifies -- a legal 20 MiB document.xml measured to peak ~214 MiB
# building the tree (roughly the same order of amplification independent
# review also measured against the on-disk archive size). No other zip
# entry in this module's parse path is ever DOM-parsed, so only
# ``word/document.xml`` needs a tighter bound; ``[Content_Types].xml``
# keeps the general 25 MiB cap (only ever substring-scanned, never
# ElementTree-parsed). 5 MiB of raw OOXML markup is already an extreme
# amount of document text -- the downstream 20,000-UTF-16-unit extraction
# cap this module enforces regardless makes anything beyond a few hundred
# KiB of real body text moot.
MAX_DOCX_DOCUMENT_XML_BYTES = int(
    os.environ.get("MYOPP_IMPORT_MAX_DOCX_DOCUMENT_XML_BYTES", str(5 * 1024 * 1024))
)
MAX_ACTIVE_IMPORTS_PER_MEMBER = int(os.environ.get("MYOPP_IMPORT_MAX_ACTIVE_PER_MEMBER", "200"))
IDEMPOTENCY_TTL = timedelta(hours=24)  # C3 value

# C0 controls (minus \t\n\r) + DEL + the Unicode bidirectional-override/
# isolate "Trojan Source" set -- built from numeric code points only
# (v2 idiom, verbatim) so this source file never itself renders (or a diff
# never silently reorders/hides) the very characters this guard exists to
# catch.
_HOSTILE_CONTROL_CHARS = frozenset(
    chr(codepoint) for codepoint in range(0x00, 0x20) if chr(codepoint) not in "\t\n\r"
) | {"\x7f"}
_BIDI_OVERRIDE_CODEPOINTS = (0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069)
_BIDI_OVERRIDE_CHARS = frozenset(chr(codepoint) for codepoint in _BIDI_OVERRIDE_CODEPOINTS)
_HOSTILE_CHARS = _HOSTILE_CONTROL_CHARS | _BIDI_OVERRIDE_CHARS


# ---------------------------------------------------------------------------
# Helpers (copied verbatim in semantics from C6)
# ---------------------------------------------------------------------------


def _utc(value: datetime | None = None) -> datetime:
    resolved = value or datetime.now(timezone.utc)
    if resolved.tzinfo is None:
        raise ValueError("now_requires_timezone")
    return resolved.astimezone(timezone.utc)


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _opaque_key() -> str:
    return uuid4().hex


def _bounded_string(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemberImportServiceError(f"{label}_required")
    normalized = value.strip()
    if _utf16_units(normalized) > maximum:
        raise MemberImportServiceError(f"{label}_too_long")
    return normalized


def _require_user_key(value: object) -> str:
    return _bounded_string(value, "user_key", MAX_USER_KEY_UTF16_UNITS)


def _owner_key_or_not_found(value: object, maximum: int) -> str:
    """Opaque import_key guard (conservative resolution -- mirrors C6's
    README note: the closed failure-code list has no dedicated
    ``import_key_required`` bounds code, so a non-string, empty, or
    over-length opaque key refuses ``not_found`` rather than inventing a new
    code or silently truncating.  Every :func:`_opaque_key` this service
    generates is a 32-character ``uuid4().hex``, well inside ``maximum``, so
    a genuinely issued key never trips the length guard; this only ever
    catches malformed input -- doc 08 §7's identical not-found isolation."""
    if not isinstance(value, str) or not value.strip() or _utf16_units(value.strip()) > maximum:
        raise MemberImportServiceError("not_found")
    return value.strip()


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (frozenset, set)):
        items = [_canonical_value(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, sort_keys=True, default=str))
        return items
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise MemberImportServiceError("canonical_input_invalid")


def _canonical_hash(command: str, value: object) -> str:
    encoded = json.dumps(
        {"command": command, "input": _canonical_value(value)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _content_hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _expect(value: object, expected_type: type) -> object:
    if not isinstance(value, expected_type):
        raise MemberImportServiceError("idempotency_result_invalid")
    return value


def _truncate_to_units(text: str, max_units: int) -> tuple[str, bool]:
    """Cut ``text`` to at most ``max_units`` UTF-16 code units, never
    splitting a surrogate pair (a trailing lone high surrogate produced by
    the byte-level cut is dropped, matching ``errors="ignore"``).  Returns
    ``(text, truncated)``."""
    encoded = text.encode("utf-16-le")
    limit_bytes = max_units * 2
    if len(encoded) <= limit_bytes:
        return text, False
    return encoded[:limit_bytes].decode("utf-16-le", errors="ignore"), True


def _reject_hostile_characters(text: str) -> str:
    if any(character in _HOSTILE_CHARS for character in text):
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_HOSTILE_CHARACTERS)
    return text


# ---------------------------------------------------------------------------
# Failure codes (closed; doc 09 §4 shape)
# ---------------------------------------------------------------------------


def _failure_message(code: str) -> str:
    return {
        "paste_required": "Paste the role details you'd like to import.",
        "paste_too_long": "That pasted text is too long.",
        "hostile_characters": "That text couldn't be read safely. Try plain text instead.",
        "upload_required": "Choose a file to upload.",
        "unsupported_type": "That file type isn't supported. Upload a PDF, Word document, or plain text file.",
        "too_large": "That file is too large.",
        "user_key_required": "A member identity is required.",
        "user_key_too_long": "That member identity is too long.",
        "idempotency_key_required": "A request key is required.",
        "idempotency_key_too_long": "That request key is too long.",
        "idempotency_mismatch": "That request key was already used for a different action.",
        "idempotency_result_invalid": "That request could not be replayed safely.",
        "url_required": "A link is required.",
        "url_too_long": "That link is too long.",
        "not_found": "That item is not available.",
        "data_class_invalid": "That data class is not valid.",
        "filter_invalid": "That filter is not valid.",
        "already_deleted": "That import was already removed.",
        "import_outcome_unknown": "We couldn't confirm that action went through. Reload and try again.",
        "retry_locked_state_reload_required": "Reload before trying that again.",
        "url_fetch_unavailable": "Importing from a link isn't available right now. Paste the text or upload the file instead.",
        "import_limit_reached": "You've reached the limit of saved imports. Remove one before adding another.",
    }.get(code, "That request could not be completed.")


class MemberImportServiceError(RuntimeError):
    """C3-C6 pattern: ``.failure_code``, ``.recoverable``,
    ``.member_message``, plus ``.current_state`` (the doc 09 §4
    ``current_state?`` slot) carrying the live record on state-refusals so
    the caller re-renders truth."""

    def __init__(
        self, failure_code: str, *, recoverable: bool | None = None, current_state: object | None = None
    ) -> None:
        self.failure_code = failure_code
        self.recoverable = bool(recoverable) if recoverable is not None else False
        self.current_state = current_state
        self.member_message = _failure_message(failure_code)
        super().__init__(failure_code)


class RepositoryWriteError(RuntimeError):
    """Raised by a repository write when storage fails.  NEVER converted
    into any stored outcome; the service converts this into
    ``import_outcome_unknown`` plus a blind-retry lock and fabricates no
    record (doc 09 §4)."""


class _PipelineHalt(Exception):
    """Internal-only pipeline control-flow signal: a decode/parse/extract
    stage function raises this to report the terminal (outcome, reason)
    the service should record for the row.  Never escapes this module --
    every command that runs the pipeline catches it and converts it into a
    stored :class:`MemberImport` row plus an :class:`ImportStageOutcome`,
    never into a raised :class:`MemberImportServiceError` (post-admission
    pipeline failures are NOT command failures; the command succeeds and
    truthfully reports the refusal on the row -- doc 09 §4's two-layer
    distinction)."""

    def __init__(self, outcome: str, reason: str | None = None) -> None:
        self.outcome = outcome
        self.reason = reason
        super().__init__(outcome)


# ---------------------------------------------------------------------------
# Bounds container (frozen; every pure pipeline function takes this
# explicitly rather than reading module globals, so tests can drive every
# bound -- including the PDF wall-clock deadline and the DOCX bomb
# thresholds -- deterministically without real multi-second sleeps or
# multi-megabyte fixtures).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemberImportLimits:
    max_paste_units: int = MAX_PASTE_UTF16_UNITS
    max_extracted_units: int = MAX_EXTRACTED_TEXT_UNITS
    max_upload_bytes: int = MAX_UPLOAD_BYTES
    max_pdf_pages: int = MAX_PDF_PAGES
    pdf_extraction_timeout_seconds: float = PDF_EXTRACTION_TIMEOUT_SECONDS
    # Independent review, fourth round (2026-09-02): the ONLY memory
    # guarantee left in this module -- see the extended comment at
    # MAX_SUBPROCESS_MEMORY_CEILING_BYTES above for why every round 1-3
    # in-process bound (per-page /Contents, document-wide font-aux/XObject
    # walk, raw-byte-structure scan, tracemalloc watchdog) was removed
    # rather than kept alongside this. ``max_subprocess_memory_ceiling_bytes``
    # is the child's own best-effort ``resource.setrlimit`` target;
    # ``subprocess_timeout_margin_seconds`` is added on top of
    # ``pdf_extraction_timeout_seconds`` for the PARENT's
    # ``subprocess.run(..., timeout=...)`` wall clock, to give the child's
    # own cold interpreter start and the parent-child JSON round trip real
    # headroom beyond the extraction deadline alone.
    max_subprocess_memory_ceiling_bytes: int = MAX_SUBPROCESS_MEMORY_CEILING_BYTES
    subprocess_timeout_margin_seconds: float = SUBPROCESS_TIMEOUT_MARGIN_SECONDS
    max_docx_entries: int = MAX_DOCX_ENTRIES
    max_docx_entry_uncompressed_bytes: int = MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES
    # MINOR 1 (2026-09-02 independent review): the dedicated, tighter cap
    # for word/document.xml specifically -- see MAX_DOCX_DOCUMENT_XML_BYTES.
    # Kept: this module fully controls the DOCX zip read (round 1), unlike
    # pypdf's opaque internals -- see the extended comment at
    # MAX_SUBPROCESS_MEMORY_CEILING_BYTES above.
    max_docx_document_xml_bytes: int = MAX_DOCX_DOCUMENT_XML_BYTES
    max_docx_total_uncompressed_bytes: int = MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES
    max_docx_entry_compression_ratio: int = MAX_DOCX_ENTRY_COMPRESSION_RATIO
    max_active_imports_per_member: int = MAX_ACTIVE_IMPORTS_PER_MEMBER

    def __post_init__(self) -> None:
        for name in (
            "max_paste_units", "max_extracted_units", "max_upload_bytes", "max_pdf_pages",
            "pdf_extraction_timeout_seconds", "max_subprocess_memory_ceiling_bytes",
            "subprocess_timeout_margin_seconds", "max_docx_entries",
            "max_docx_entry_uncompressed_bytes", "max_docx_document_xml_bytes",
            "max_docx_total_uncompressed_bytes",
            "max_docx_entry_compression_ratio", "max_active_imports_per_member",
        ):
            if getattr(self, name) <= 0:
                raise ValueError("member_import_limits_invalid")


# ---------------------------------------------------------------------------
# Record shapes (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemberImport:
    import_key: str
    user_key: str
    data_class: str  # fixture | production (C2 DATA_CLASSES)
    intake_method: str  # INTAKE_METHODS
    record_state: str  # active | deleted
    declared_content_type: str | None  # uploads/fetch only
    byte_count: int | None  # admitted bytes (uploads/fetch)
    # -- fetch provenance (doc 06 §3 / doc 02 §1); ALWAYS None in C10 use,
    #    populated only by the C13-era url path; lives ONLY in this record --
    submitted_url: str | None
    final_url: str | None
    resolved_address: str | None
    fetched_at: datetime | None
    # -- content + pipeline truth --
    content_hash: str | None  # sha256 hex of admitted bytes/paste text; in-record only
    sanitizer_version: str
    sanitized_text: str | None  # None <=> body removed OR non-success outcome
    extracted_units: int | None
    truncated: bool
    outcome: str  # OUTCOME_STATES (current/terminal)
    outcome_reason: str | None  # closed pairing
    # -- dual retention (doc 02 §4) --
    rights_obligation_class: str  # RIGHTS_OBLIGATION_CLASSES
    body_removed_at: datetime | None
    body_removal_reason: str | None  # BODY_REMOVAL_REASONS
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.record_state not in RECORD_STATES:
            raise ValueError("invalid_record_state")
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        if self.intake_method not in INTAKE_METHODS:
            raise ValueError("invalid_intake_method")
        if self.outcome not in OUTCOME_STATES:
            raise ValueError("invalid_outcome")
        if self.rights_obligation_class not in RIGHTS_OBLIGATION_CLASSES:
            raise ValueError("invalid_rights_obligation_class")

        allowed_reasons = REASONS_BY_STATE.get(self.outcome, frozenset())
        if allowed_reasons:
            if self.outcome_reason not in allowed_reasons:
                raise ValueError("invalid_outcome_reason_pairing")
        elif self.outcome_reason is not None:
            raise ValueError("invalid_outcome_reason_pairing")

        fetch_fields = (self.submitted_url, self.final_url, self.resolved_address, self.fetched_at)
        if self.intake_method != INTAKE_URL_FETCH and any(field is not None for field in fetch_fields):
            raise ValueError("fetch_provenance_requires_url_fetch")

        if (self.body_removed_at is None) != (self.body_removal_reason is None):
            raise ValueError("invalid_body_removal_pairing")
        if self.body_removal_reason is not None and self.body_removal_reason not in BODY_REMOVAL_REASONS:
            raise ValueError("invalid_body_removal_reason")
        if self.body_removed_at is not None and self.sanitized_text is not None:
            raise ValueError("body_removed_requires_no_text")

        if self.record_state == RECORD_STATE_DELETED:
            if self.body_removal_reason != BODY_REMOVAL_MEMBER_DELETE:
                raise ValueError("deleted_requires_member_delete_removal")
        elif self.body_removal_reason == BODY_REMOVAL_MEMBER_DELETE:
            raise ValueError("member_delete_requires_deleted_state")

        if self.outcome in (OUTCOME_EXTRACTED, OUTCOME_PARTIAL):
            if self.body_removed_at is None and self.sanitized_text is None:
                raise ValueError("success_outcome_requires_text_or_removal")
        elif self.sanitized_text is not None:
            raise ValueError("non_success_outcome_forbids_text")

        if self.truncated != (self.outcome == OUTCOME_PARTIAL):
            raise ValueError("truncated_requires_partial_outcome")

        if self.byte_count is not None and self.byte_count < 0:
            raise ValueError("byte_count_negative")
        if self.extracted_units is not None and self.extracted_units < 0:
            raise ValueError("extracted_units_negative")
        if self.updated_at < self.created_at:
            raise ValueError("invalid_timestamp_pairing")
        if self.body_removed_at is not None and self.body_removed_at < self.created_at:
            raise ValueError("invalid_timestamp_pairing")


@dataclass(frozen=True)
class ImportStageOutcome:  # append-only pipeline truth trail
    # MINOR 5 (2026-09-01 self-review): this in-memory shape carries no
    # sequence_number, because the InMemoryMemberImportRepository preserves
    # trail order structurally (an append-only Python list). The
    # PS-MYOPP-006 schema's stage_outcomes table requires
    # UQ(myopp_member_import_id, sequence_number), so a future SQL-backed
    # MemberImportRepository must synthesize sequence_number itself when
    # persisting a trail (e.g. a per-import monotonic counter, or simply
    # enumerate(trail, start=1) at append_stage_outcome time) -- it is a
    # storage-layer concern, not part of this module's own record shape.
    import_key: str
    user_key: str
    outcome: str  # OUTCOME_STATES
    reason_code: str | None
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOME_STATES:
            raise ValueError("invalid_outcome")
        allowed_reasons = REASONS_BY_STATE.get(self.outcome, frozenset())
        if allowed_reasons:
            if self.reason_code not in allowed_reasons:
                raise ValueError("invalid_outcome_reason_pairing")
        elif self.reason_code is not None:
            raise ValueError("invalid_outcome_reason_pairing")


# A receipt's ``outcome`` is either a pipeline OUTCOME_STATES value
# (submit_paste/submit_upload/import_from_url) or the terminal RECORD_STATES
# value ``"deleted"`` (delete_import has no pipeline outcome of its own --
# conservative resolution: the blueprint's ImportReceipt sketch does not
# separately type this field, so the union of the two closed vocabularies
# already in scope is used rather than inventing a third).
_RECEIPT_OUTCOME_VALUES = OUTCOME_STATES | RECORD_STATES


@dataclass(frozen=True)
class ImportReceipt:  # terminal command receipt (idempotent replay unit)
    import_key: str | None
    command: str  # submit_paste | submit_upload | import_from_url | delete_import
    outcome: str
    outcome_reason: str | None
    truncated: bool
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.command not in COMMANDS:
            raise ValueError("invalid_command")
        if self.outcome not in _RECEIPT_OUTCOME_VALUES:
            raise ValueError("invalid_receipt_outcome")


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    declared_content_type: str
    byte_length: int


@dataclass(frozen=True)
class FetchResult:  # the port-side contract C13 must satisfy
    data: bytes
    declared_content_type: str
    submitted_url: str
    final_url: str
    resolved_address: str
    fetched_at: datetime
    host_class: str  # HOST_CLASSES member ("public" on success)

    def __post_init__(self) -> None:
        if self.host_class not in HOST_CLASSES:
            raise ValueError("invalid_host_class")


class FetchRefused(RuntimeError):
    """Raised by a :class:`FetchAdapter` (C13-era) to report a guarded-fetch
    refusal.  ``reason`` is one of the C13-reserved reason codes; mapped by
    :func:`_map_fetch_refusal` onto the closed ``blocked``/``timeout``/
    ``refused`` outcome states this module already carries."""

    def __init__(self, reason: str, host_class: str) -> None:
        self.reason = reason
        self.host_class = host_class
        super().__init__(reason)


_FETCH_REFUSAL_OUTCOME = {
    REASON_DENIED_ADDRESS: OUTCOME_BLOCKED,
    REASON_SCHEME_REFUSED: OUTCOME_BLOCKED,
    REASON_REDIRECT_REFUSED: OUTCOME_BLOCKED,
    REASON_CONTENT_MISMATCH: OUTCOME_BLOCKED,
    REASON_FETCH_DEADLINE: OUTCOME_TIMEOUT,
    REASON_FETCH_TOO_LARGE: OUTCOME_REFUSED,
}


def _map_fetch_refusal(refusal: "FetchRefused") -> tuple[str, str]:
    outcome = _FETCH_REFUSAL_OUTCOME.get(refusal.reason)
    if outcome is None:
        raise MemberImportServiceError("fetch_refusal_reason_invalid")
    return outcome, refusal.reason


@dataclass(frozen=True)
class MemberImportAuditEvent:  # content-free (doc 08 §4 / doc 12 §5)
    event_kind: str  # closed: see _AUDIT_EVENT_KINDS
    user_key: str
    keys: tuple[str, ...]  # opaque keys only
    reason_code: str | None
    host_class: str  # HOST_CLASSES; not_applicable for paste/upload
    actor: str  # "member" | "system:rights_point_of_use"
    at: datetime
    # NEVER: url, hostname, path, query, body, content hash, filename, content
    # -- structurally guaranteed: this dataclass has no such field.

    def __post_init__(self) -> None:
        if self.event_kind not in _AUDIT_EVENT_KINDS:
            raise ValueError("invalid_event_kind")
        if self.host_class not in HOST_CLASSES:
            raise ValueError("invalid_host_class")
        object.__setattr__(self, "keys", tuple(self.keys))


# ---------------------------------------------------------------------------
# Protocols (dependency seams; all injected)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _IdempotencyRecord:  # C3 shape, verbatim fields
    command: str
    canonical_input_hash: str
    result: object
    expires_at: datetime


class MemberImportRepository(Protocol):
    def import_for_owner(self, user_key: str, import_key: str) -> MemberImport | None: ...

    def imports_for_owner(self, user_key: str) -> tuple[MemberImport, ...]: ...

    def active_import_count(self, user_key: str) -> int: ...

    def persist_import(self, record: MemberImport) -> None: ...  # insert only

    def update_import(self, record: MemberImport) -> None: ...  # legal transitions only:
    # active->active(body_removed rights_takedown) | active->deleted(member_delete)

    def append_stage_outcome(self, outcome: ImportStageOutcome) -> None: ...

    def stage_outcomes_for_owner(self, user_key: str, import_key: str) -> tuple[ImportStageOutcome, ...]: ...

    def _idempotency_record(self, user_key: str, key: str, now: datetime) -> _IdempotencyRecord | None: ...

    def _record_idempotency(self, user_key: str, key: str, record: _IdempotencyRecord) -> None: ...

    def purge_expired_idempotency(self, *, now: datetime) -> int: ...  # content-blind TTL


class RightsObligationReader(Protocol):
    """Point-of-use seam (doc 02 §4): the obligation class for one import
    record.  C10 ships a none-reader; real obligation sources arrive with
    future rights packages -- the ENFORCEMENT POINT is C10's, the sources
    are not (README known limitation)."""

    def obligation_for(self, record: MemberImport) -> str: ...


class FetchAdapter(Protocol):  # what C13's create_fetch_adapter() returns
    def fetch(self, url: str) -> FetchResult: ...
    # raises FetchRefused(reason, host_class) on a guarded refusal.


class AuditSink(Protocol):
    def emit(self, event: MemberImportAuditEvent) -> None: ...


class NoneRightsObligationReader:
    def obligation_for(self, record: MemberImport) -> str:  # noqa: ARG002
        return RIGHTS_NONE


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[MemberImportAuditEvent] = []

    def emit(self, event: MemberImportAuditEvent) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# In-memory reference repository (P-1 truth)
# ---------------------------------------------------------------------------

_IMPORT_IDENTITY_FIELDS = (
    "import_key", "user_key", "data_class", "intake_method", "declared_content_type", "byte_count",
    "submitted_url", "final_url", "resolved_address", "fetched_at", "content_hash", "sanitizer_version",
    "extracted_units", "truncated", "outcome", "outcome_reason", "created_at",
)


def _validate_import_transition(prior: MemberImport, new: MemberImport) -> None:
    if prior.record_state == RECORD_STATE_DELETED:
        raise RepositoryWriteError("import_terminal")
    for field_name in _IMPORT_IDENTITY_FIELDS:
        if getattr(prior, field_name) != getattr(new, field_name):
            raise RepositoryWriteError("import_identity_changed")
    if prior.record_state == RECORD_STATE_ACTIVE and new.record_state == RECORD_STATE_ACTIVE:
        # The only legal active->active move: a live rights-takedown removal
        # on a row that has not already been removed.
        if prior.body_removed_at is not None:
            raise RepositoryWriteError("illegal_import_field_change")
        if new.body_removal_reason != BODY_REMOVAL_RIGHTS_TAKEDOWN or new.body_removed_at is None:
            raise RepositoryWriteError("illegal_import_transition")
        if new.sanitized_text is not None:
            raise RepositoryWriteError("illegal_import_field_change")
    elif prior.record_state == RECORD_STATE_ACTIVE and new.record_state == RECORD_STATE_DELETED:
        if new.body_removal_reason != BODY_REMOVAL_MEMBER_DELETE:
            raise RepositoryWriteError("illegal_import_transition")
        if new.sanitized_text is not None:
            raise RepositoryWriteError("illegal_import_field_change")
    else:
        raise RepositoryWriteError("illegal_import_transition")


class InMemoryMemberImportRepository:
    """C3-C6 idiom: dict stores keyed by ``import_key``, an owner-scoped
    active-count index, a reentrant lock, owner re-check inside every
    ``*_for_owner`` read, a TTL-aware idempotency map, and a content-safe
    ``state_digest()``.  ``update_import`` re-validates the legal-transition
    table and refuses illegal writes with :class:`RepositoryWriteError` even
    if a service bug asked -- the in-memory reference enforces what the SQL
    triggers enforce, one behavior contract in two stores."""

    def __init__(self) -> None:
        self._imports: dict[str, MemberImport] = {}
        self._active_index: dict[str, set[str]] = {}  # user_key -> active import_keys
        self._stage_outcomes: dict[str, list[ImportStageOutcome]] = {}
        self._idempotency: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._lock = threading.RLock()

    def import_for_owner(self, user_key: str, import_key: str) -> MemberImport | None:
        record = self._imports.get(import_key)
        return record if record is not None and record.user_key == user_key else None

    def imports_for_owner(self, user_key: str) -> tuple[MemberImport, ...]:
        return tuple(record for record in self._imports.values() if record.user_key == user_key)

    def active_import_count(self, user_key: str) -> int:
        return len(self._active_index.get(user_key, ()))

    def persist_import(self, record: MemberImport) -> None:
        with self._lock:
            if record.import_key in self._imports:
                raise RepositoryWriteError("import_exists")
            self._imports[record.import_key] = record
            if record.record_state == RECORD_STATE_ACTIVE:
                self._active_index.setdefault(record.user_key, set()).add(record.import_key)
            self._stage_outcomes.setdefault(record.import_key, [])

    def update_import(self, record: MemberImport) -> None:
        with self._lock:
            prior = self._imports.get(record.import_key)
            if prior is None or prior.user_key != record.user_key:
                raise RepositoryWriteError("import_not_found")
            _validate_import_transition(prior, record)
            self._imports[record.import_key] = record
            active_set = self._active_index.setdefault(record.user_key, set())
            if record.record_state == RECORD_STATE_ACTIVE:
                active_set.add(record.import_key)
            else:
                active_set.discard(record.import_key)

    def append_stage_outcome(self, outcome: ImportStageOutcome) -> None:
        with self._lock:
            if outcome.import_key not in self._imports:
                raise RepositoryWriteError("import_not_found")
            self._stage_outcomes.setdefault(outcome.import_key, []).append(outcome)

    def stage_outcomes_for_owner(self, user_key: str, import_key: str) -> tuple[ImportStageOutcome, ...]:
        record = self._imports.get(import_key)
        if record is None or record.user_key != user_key:
            return ()
        return tuple(self._stage_outcomes.get(import_key, ()))

    def _idempotency_record(self, user_key: str, idempotency_key: str, now: datetime) -> _IdempotencyRecord | None:
        record = self._idempotency.get((user_key, idempotency_key))
        if record is not None and record.expires_at <= now:
            del self._idempotency[(user_key, idempotency_key)]
            return None
        return record

    def _record_idempotency(self, user_key: str, idempotency_key: str, record: _IdempotencyRecord) -> None:
        self._idempotency[(user_key, idempotency_key)] = record

    def purge_expired_idempotency(self, *, now: datetime) -> int:
        with self._lock:
            expired = [key for key, row in self._idempotency.items() if row.expires_at <= now]
            for key in expired:
                del self._idempotency[key]
            return len(expired)

    def state_digest(self) -> str:
        """Content-safe test aid proving refusals never mutate repository
        state."""
        with self._lock:
            value = {
                "imports": self._imports,
                "stage_outcomes": {key: tuple(rows) for key, rows in self._stage_outcomes.items()},
                "idempotency_keys": sorted(f"{owner}:{key}" for owner, key in self._idempotency),
            }
            return hashlib.sha256(
                json.dumps(_canonical_value(value), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()


class FailingMemberImportRepository(InMemoryMemberImportRepository):
    """Test double: raises :class:`RepositoryWriteError` from the named
    write methods, starting at the ``fail_after_calls``'th call to that
    specific method (default 1, i.e. every call) -- used by the doc 09 §4
    unknown-outcome suite (Group G).

    ``fail_mode`` selects WHEN the simulated failure fires relative to the
    underlying write (mirrors C6's own ``FailingRelationshipsRepository``):
    ``"pre"`` (default) raises before the write is attempted at all (the
    did-not-land branch); ``"post"`` lets the write complete durably against
    the underlying store and then raises (the landed branch, simulating a
    connection drop after commit)."""

    _WRITE_METHODS = ("persist_import", "update_import", "append_stage_outcome")
    _FAIL_MODES = frozenset({"pre", "post"})

    def __init__(self, *, fail_on: object = (), fail_after_calls: int = 1, fail_mode: str = "pre") -> None:
        super().__init__()
        self._fail_on = set(fail_on)
        self._fail_after_calls = fail_after_calls
        if fail_mode not in self._FAIL_MODES:
            raise ValueError("fail_mode_invalid")
        self._fail_mode = fail_mode
        self._call_counts = {name: 0 for name in self._WRITE_METHODS}

    def _should_fail(self, method_name: str) -> bool:
        self._call_counts[method_name] += 1
        return method_name in self._fail_on and self._call_counts[method_name] >= self._fail_after_calls

    def persist_import(self, record: MemberImport) -> None:
        fail = self._should_fail("persist_import")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().persist_import(record)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")

    def update_import(self, record: MemberImport) -> None:
        fail = self._should_fail("update_import")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().update_import(record)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")

    def append_stage_outcome(self, outcome: ImportStageOutcome) -> None:
        fail = self._should_fail("append_stage_outcome")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().append_stage_outcome(outcome)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")


# ---------------------------------------------------------------------------
# Deterministic sanitize/extract pipeline (pure functions; no AI, no
# network; every bound is passed explicitly via MemberImportLimits).
# ---------------------------------------------------------------------------


def validate_paste(text: object, limits: MemberImportLimits) -> str:
    """Pre-admission: bounds + hostile-character refusal (matrix rows 1-3).
    Never silently strips a hostile character -- refuses instead."""
    if not isinstance(text, str) or not text.strip():
        raise MemberImportServiceError("paste_required")
    normalized = text.strip()
    if _utf16_units(normalized) > limits.max_paste_units:
        raise MemberImportServiceError("paste_too_long")
    if any(character in _HOSTILE_CHARS for character in normalized):
        raise MemberImportServiceError("hostile_characters")
    return normalized


def _sniff_binary_kind(data: bytes) -> str:
    """Best-effort identification of what ``data`` actually is, from bytes
    alone -- never from the caller's declared type.  Catches a spoofed
    declaration before any parser sees the bytes (v2 idiom, verbatim)."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return "zip"
    if data.startswith(b"\x7fELF"):
        return "elf"
    if data[:2] == b"MZ":
        return "exe"
    stripped = data.lstrip(b"\xef\xbb\xbf \t\r\n\x0c").lower()
    if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
        return "html"
    if b"\x00" in data[:4096]:
        return "binary"
    return "text"


def validate_upload(upload: object, limits: MemberImportLimits) -> ValidatedUpload:
    """Declared-MIME allowlist, bounded ``MAX + 1`` read (never buffers past
    the limit), magic-byte sniff independent of the declared type (matrix
    rows 4-7)."""
    if upload is None or not getattr(upload, "stream", None):
        raise MemberImportServiceError("upload_required")
    declared = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0].strip()
    if declared not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise MemberImportServiceError("unsupported_type")

    data = upload.stream.read(limits.max_upload_bytes + 1)
    if len(data) > limits.max_upload_bytes:
        raise MemberImportServiceError("too_large")
    if not data:
        raise MemberImportServiceError("upload_required")

    sniffed = _sniff_binary_kind(data)
    if declared == "application/pdf" and sniffed != "pdf":
        raise MemberImportServiceError("unsupported_type")
    if declared == _DOCX_CONTENT_TYPE and sniffed != "zip":
        raise MemberImportServiceError("unsupported_type")
    if declared == "text/plain" and sniffed in {"pdf", "zip", "elf", "exe", "html", "binary"}:
        raise MemberImportServiceError("unsupported_type")

    return ValidatedUpload(data=data, declared_content_type=declared, byte_length=len(data))


# -- hardened deterministic markup sanitizer (doc 06 §3) --------------------
# A pure tag-stripping tokenizer: script/style/handler content is never
# emitted (attributes -- where any event-handler value would live -- are
# never read at all), block tags become newline separators, everything else
# becomes plain text.  Row 13: this is NOT a refusal -- markup is silently
# reduced to "text + minimal safe structure," which is the truthful,
# intended behavior; only hostile CONTROL/bidi characters are ever refused,
# never silently stripped.
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "head", "iframe", "object", "embed"})
_BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header", "footer"}
)


class _MarkupSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:  # noqa: ARG002
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag, attrs) -> None:  # noqa: ARG002
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data) -> None:
        if self._skip_depth:
            return
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def _sanitize_markup(text: str) -> str:
    parser = _MarkupSanitizer()
    try:
        parser.feed(text)
        parser.close()
    except MemoryError as error:
        # A memory exhaustion, never evidence the document is malformed.
        # NOTE: this function also runs in the PARENT for paste/text-plain,
        # where no isolation ceiling exists -- so the justification here is
        # simply that blaming the member's content for a machine condition
        # would be false, not that a ceiling fired (independent review F4).
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
    except Exception as error:  # untrusted, adversarial input
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
    return parser.text()


# -- PDF (pypdf -- pure Python, no macro/script evaluation) ----------------
#
# Independent review, fourth round (2026-09-02): this module no longer
# attempts to bound pypdf's own decompression from the outside at all -- see
# the extended comment at MAX_SUBPROCESS_MEMORY_CEILING_BYTES above for why
# three straight rounds of in-process bounding were each proven insufficient
# in turn, and why the guarantee is now OS-enforced subprocess isolation
# instead (:func:`_run_isolated_parse_and_extract`). ``_parse_pdf`` and
# ``_extract_pdf`` below are UNCHANGED in their core parsing/extraction
# logic from before that history began; they are simply never called
# directly in the request-serving parent process anymore -- only from
# inside the isolated child process this module's own worker entry point
# (:func:`_subprocess_worker_main`) spawns itself into.


def _parse_pdf(data: bytes, limits: MemberImportLimits):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as error:  # pragma: no cover - dependency always pinned
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            # Only the common "empty owner password" case is handled;
            # anything still encrypted is honestly unreadable, never
            # brute-forced.
            try:
                decrypted = reader.decrypt("")
            except MemoryError as error:
                # Reachable: PdfReader() above already inflates FlateDecode
                # /XRef streams, so a crafted document can leave the child
                # just under its ceiling and ANY later allocation -- even a
                # small one in here -- raises. Without this clause the halt
                # becomes a _PipelineHalt(parser_failure) that the outer
                # MemoryError guard can never see (independent review F1).
                raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
            except Exception as error:
                raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
            if decrypted == 0:
                raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)

        pages = reader.pages
        if len(pages) == 0:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)
        if len(pages) > limits.max_pdf_pages:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS)

        return pages
    except _PipelineHalt:
        raise
    except PyPdfError as error:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
    except MemoryError as error:
        # A MemoryError here is the isolation ceiling doing its job
        # (RLIMIT_AS/RLIMIT_DATA enforces on Linux), not a malformed
        # document: report it as a resource bound, never a parse
        # failure (independent review / CI on Linux, 2026-09-01).
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
    except Exception as error:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error


def _extract_pdf(pages, limits: MemberImportLimits) -> tuple[str, bool]:
    from pypdf.errors import LimitReachedError, PyPdfError

    deadline = time.monotonic() + limits.pdf_extraction_timeout_seconds
    chunks: list[str] = []
    units = 0
    truncated = False
    for page in pages:
        if units >= limits.max_extracted_units:
            truncated = True
            break
        if time.monotonic() >= deadline:
            # Matrix row 11: the whole extraction is refused as `timeout` --
            # whatever text has already been tokenized is discarded, never
            # stored as a fabricated partial result under a timeout label
            # (distinct from the `partial` truncation state, which DOES
            # keep and label its text).
            raise _PipelineHalt(OUTCOME_TIMEOUT, REASON_EXTRACTION_DEADLINE)
        try:
            text = page.extract_text() or ""
        except LimitReachedError as error:
            # pypdf's own internal ~75 MiB decompression safety net; this
            # code now only ever runs inside the isolated child (round 4
            # onward), so this is simply a truthful, more SPECIFIC reason
            # than the generic subprocess-boundary mapping would give --
            # never a load-bearing bound in its own right.
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
        except PyPdfError as error:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
        except MemoryError as error:
            # The isolation ceiling doing its job (RLIMIT_AS enforces on
            # Linux), not a malformed document: a resource bound.
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
        except Exception as error:
            # Untrusted, adversarial input: any other exception this call
            # can raise is still an honest, persisted refusal, never an
            # uncaught crash out of submit_upload (doc 09 §4).
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
        chunks.append(text)
        units += _utf16_units(text) + 2
    return "\n\n".join(chunks).strip(), truncated


# -- DOCX (stdlib zipfile + xml.etree only) ---------------------------------
_WORDPROCESSINGML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W_T = f"{{{_WORDPROCESSINGML_NS}}}t"
_W_TAB = f"{{{_WORDPROCESSINGML_NS}}}tab"
_W_BR = f"{{{_WORDPROCESSINGML_NS}}}br"
_W_P = f"{{{_WORDPROCESSINGML_NS}}}p"


def _safe_zip_member_names(archive: zipfile.ZipFile, limits: MemberImportLimits) -> list[str]:
    """A fast PRE-FILTER only -- never the safety boundary (the central
    directory's declared sizes are attacker-controlled); the actual bound is
    :func:`_bounded_zip_read`, on the real decompressed bytes."""
    names = archive.namelist()
    if len(names) > limits.max_docx_entries:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_ARCHIVE_BOMB_SUSPECTED)
    total_declared = 0
    for info in archive.infolist():
        name = info.filename
        if name.startswith("/") or ".." in name.split("/"):
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)
        if info.file_size > limits.max_docx_entry_uncompressed_bytes:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_ARCHIVE_BOMB_SUSPECTED)
        if (
            info.compress_size > 0
            and info.file_size / max(info.compress_size, 1) > limits.max_docx_entry_compression_ratio
        ):
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_ARCHIVE_BOMB_SUSPECTED)
        total_declared += info.file_size
        if total_declared > limits.max_docx_total_uncompressed_bytes:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_ARCHIVE_BOMB_SUSPECTED)
    return names


def _bounded_zip_read(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """Read at most ``limit`` ACTUAL decompressed bytes of ``name``,
    regardless of what the archive's central directory claims about it."""
    with archive.open(name) as member:
        data = member.read(limit + 1)
    if len(data) > limit:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_ARCHIVE_BOMB_SUSPECTED)
    return data


def _reject_doctype(xml_bytes: bytes) -> None:
    """Real OOXML document parts never declare a DOCTYPE; refuse any that do
    before ``xml.etree`` ever parses them (closes XXE/billion-laughs without
    a defusedxml dependency)."""
    if b"<!doctype" in xml_bytes.lower():
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)


def _parse_docx(data: bytes, limits: MemberImportLimits):
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = _safe_zip_member_names(archive, limits)
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)
            content_types = _bounded_zip_read(
                archive, "[Content_Types].xml", limits.max_docx_entry_uncompressed_bytes
            )
            _reject_doctype(content_types)
            if b"wordprocessingml" not in content_types.lower():
                raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)
            # MINOR 1: word/document.xml alone gets the tighter,
            # DOM-amplification-aware cap -- it is the only entry this
            # module hands to ElementTree.fromstring for a full parse.
            document_xml = _bounded_zip_read(
                archive, "word/document.xml", limits.max_docx_document_xml_bytes
            )
    except _PipelineHalt:
        raise
    except zipfile.BadZipFile as error:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error
    except MemoryError as error:
        # A MemoryError here is the isolation ceiling doing its job
        # (RLIMIT_AS/RLIMIT_DATA enforces on Linux), not a malformed
        # document: report it as a resource bound, never a parse
        # failure (independent review / CI on Linux, 2026-09-01).
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS) from error
    except Exception as error:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error

    _reject_doctype(document_xml)
    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as error:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE) from error

    body = root.find(f"{{{_WORDPROCESSINGML_NS}}}body")
    if body is None:
        raise _PipelineHalt(OUTCOME_REFUSED, REASON_PARSER_FAILURE)
    return body


def _paragraph_text(paragraph_element) -> str:
    parts = []
    for node in paragraph_element.iter():
        if node.tag == _W_T:
            parts.append(node.text or "")
        elif node.tag == _W_TAB:
            parts.append("\t")
        elif node.tag == _W_BR:
            parts.append("\n")
    return "".join(parts)


def _extract_docx(body, limits: MemberImportLimits) -> tuple[str, bool]:
    lines: list[str] = []
    units = 0
    truncated = False
    for paragraph in body.iter(_W_P):
        if units >= limits.max_extracted_units:
            truncated = True
            break
        line = _paragraph_text(paragraph)
        lines.append(line)
        units += _utf16_units(line) + 1
    return "\n".join(lines).strip(), truncated


# -- stage dispatchers --------------------------------------------------


def _decode(admitted: object, content_type: str):
    """[decoded] -- text (paste) is already decoded and passes straight
    through; a text/plain upload is decoded as UTF-8 with BOM handling;
    binary containers (pdf/docx) are a structural pass-through (their own
    decode failures surface as parser_failure at the PARSE stage, matching
    matrix row 9's "corrupt PDF xref" wording)."""
    if isinstance(admitted, str):
        return admitted
    if content_type == "text/plain":
        body = admitted
        if body.startswith(b"\xef\xbb\xbf"):
            body = body[3:]
        try:
            return body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise _PipelineHalt(OUTCOME_REFUSED, REASON_COULD_NOT_DECODE) from error
    return admitted


def _parse(decoded: object, content_type: str, limits: MemberImportLimits):
    """[parsed] -- markup-ish text (paste or a text/plain upload) is run
    through the hardened sanitizer now; pdf/docx get their structural parse
    + bomb-bounds pass now (the actual per-page/per-paragraph tokenization
    happens at EXTRACT)."""
    if isinstance(decoded, str):
        return _sanitize_markup(decoded)
    if content_type == "application/pdf":
        return _parse_pdf(decoded, limits)
    if content_type == _DOCX_CONTENT_TYPE:
        return _parse_docx(decoded, limits)
    raise AssertionError("unreachable: content_type already validated")  # pragma: no cover


def _extract(parsed: object, content_type: str, limits: MemberImportLimits) -> tuple[str, bool]:
    """[extracted|partial|empty] -- HTML-escape, UTF-16-boundary truncation
    at the cap, hostile-character refusal on the FINAL text, empty
    detection.

    Conservative resolution (row 4's "canaries ... in extracted document
    text never appear in sanitized_text" requirement): the SAME markup
    sanitizer paste/text-plain content goes through at PARSE is applied
    here, defensively, to whatever pdf/docx tokenization produced, before
    the final truncation/hostile-character pass -- defense in depth even
    though pypdf/the w:t walk never interpret bytes as HTML themselves.

    IMPORTANT 2 (2026-09-01 self-review): ``_sanitize_markup`` strips
    STRUCTURAL tags only.  ``HTMLParser(convert_charrefs=True)`` decodes
    entity references while it walks -- exactly ONE pass -- so a payload
    that never contains a literal ``<`` byte can still leave a tag-shaped
    substring in the OUTPUT text: ``&lt;scr&lt;script&gt;ipt&gt;`` decodes,
    in one pass, to ``<scr<script>ipt>`` -- which contains the literal
    substring ``<script>`` -- and a payload like
    ``&amp;lt;script&amp;gt;...`` decodes to the still-entity-shaped
    ``&lt;script&gt;...``, which a BROWSER's own single decode pass would
    turn into a live tag if some future consumer ever inserted this field
    unescaped into an HTML page.  Neither case is caught by re-tokenizing
    (the decoded text was never fed back through the tag parser), so the
    only structural fix is output encoding: HTML-escaping the fully
    sanitized text guarantees no substring of the STORED field can ever
    again read as a tag delimiter, however many rounds of entity-nesting
    the original payload played.  Escaping runs BEFORE truncation so the
    UTF-16 cap can never split an entity reference in half, and BEFORE the
    hostile-character check (escaping never touches a control or bidi
    character, so the two checks are independent regardless of order).
    ``sanitized_text`` is therefore plain text that is ALREADY HTML-escaped
    -- see the README C8 seam-contract note: consumers must still apply
    their own render-time output-escaping discipline (never treat this
    field as pre-vetted "safe" markup to insert raw), escaping at write
    time is defense in depth, not a license to skip escaping at read time.
    """
    if isinstance(parsed, str):
        text, truncated = parsed, False
    elif content_type == "application/pdf":
        text, truncated = _extract_pdf(parsed, limits)
        text = _sanitize_markup(text)
    elif content_type == _DOCX_CONTENT_TYPE:
        text, truncated = _extract_docx(parsed, limits)
        text = _sanitize_markup(text)
    else:
        raise AssertionError("unreachable: content_type already validated")  # pragma: no cover

    cleaned = text.strip()
    if not cleaned:
        return "", False
    escaped = html.escape(cleaned)
    final_text, cut = _truncate_to_units(escaped, limits.max_extracted_units)
    truncated = truncated or cut
    final_text = _reject_hostile_characters(final_text)
    return final_text, truncated


# ---------------------------------------------------------------------------
# OS-enforced process isolation (independent review, fourth round,
# 2026-09-02) -- the sole memory guarantee for PDF and DOCX parsing. See the
# extended comment at MAX_SUBPROCESS_MEMORY_CEILING_BYTES above for the full
# architectural rationale.
# ---------------------------------------------------------------------------

_SUBPROCESS_WORKER_FLAG = "--pdf-docx-parse-worker"
_ISOLATED_CONTENT_TYPES = frozenset({"application/pdf", _DOCX_CONTENT_TYPE})


def _run_isolated_parse_and_extract(
    content_type: str, decoded: bytes, limits: MemberImportLimits
) -> tuple[bool, str | None, str | None, str | None, bool]:
    """Runs :func:`_parse` then :func:`_extract` for a PDF or DOCX payload
    INSIDE a short-lived, freshly-spawned CHILD PROCESS -- never in this,
    request-serving, process. Returns ``(parsed_ok, halt_outcome,
    halt_reason, text, truncated)``:

    * ``parsed_ok`` is ``False`` when the PARSE stage itself never
      completed -- either the child's own :func:`_parse` raised, or the
      SUBPROCESS BOUNDARY ITSELF failed (timeout, nonzero exit, a signal
      kill, or unparseable stdout). This module cannot attribute a
      boundary failure to a specific internal stage, so it conservatively
      never claims "parsed" completed when it cannot prove it did.
    * ``halt_outcome``/``halt_reason`` are set whenever the pipeline did
      not reach a successful EXTRACT, whether or not parse completed.
    * ``text``/``truncated`` are populated only when both stages
      succeeded (``halt_outcome is None``).

    A nonzero return code covers three shapes uniformly, exactly as
    directed: a plain uncaught-exception exit, a signal kill (Python
    reports a POSIX signal kill as a NEGATIVE returncode -- e.g. -9 for
    SIGKILL from the kernel's OOM killer, or from this module's own
    best-effort ``resource.setrlimit`` self-terminating), and
    ``subprocess.TimeoutExpired`` (the wall-clock backstop). Every one of
    these means the child's address space is gone without a usable
    result -- the resource-bounds condition this whole architecture exists
    to convert into a truthful, persisted outcome, never a crash out of
    ``submit_upload``. The child's own stderr is never read or surfaced to
    the member (content-free by construction: this function never touches
    ``result.stderr`` at all).
    """
    repo_root = Path(__file__).resolve().parents[2]
    payload = json.dumps(
        {
            "content_type": content_type,
            "decoded_b64": base64.b64encode(decoded).decode("ascii"),
            "limits": asdict(limits),
        }
    ).encode("utf-8")
    timeout_seconds = limits.pdf_extraction_timeout_seconds + limits.subprocess_timeout_margin_seconds

    try:
        result = subprocess.run(
            [sys.executable, "-m", "services.my_opportunities.member_import_service", _SUBPROCESS_WORKER_FLAG],
            input=payload,
            stdout=subprocess.PIPE,
            # The child's stderr is never read (content could not safely be
            # surfaced anyway); discard it at the OS level rather than buffer
            # it in the parent (independent review round 5, hardening note 2).
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        return False, OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS, None, False
    except OSError:
        # Launching/communicating with the child itself failed (the
        # interpreter missing, a broken pipe, ...) -- an honest
        # environment failure, never surfaced as a crash.
        return False, OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS, None, False

    if result.returncode != 0:
        return False, OUTCOME_REFUSED, REASON_PARSER_RESOURCE_BOUNDS, None, False

    try:
        response = json.loads(result.stdout.decode("utf-8"))
    except Exception:
        return False, OUTCOME_REFUSED, REASON_PARSER_FAILURE, None, False

    if not response.get("parsed", False):
        return False, response.get("outcome"), response.get("reason"), None, False
    if "extract_halt" in response:
        halt = response["extract_halt"]
        return True, halt.get("outcome"), halt.get("reason"), None, False
    return True, None, None, response.get("text", ""), bool(response.get("truncated", False))


def _subprocess_worker_main() -> None:
    """Entry point for the isolated child process this module spawns
    ITSELF into (see :func:`_run_isolated_parse_and_extract`, and re-invoke
    this file with ``python -m services.my_opportunities.member_import_service
    --pdf-docx-parse-worker`` to run it directly). Reads exactly one JSON
    payload from stdin, runs :func:`_parse`/:func:`_extract` for the given
    ``content_type`` against the decoded bytes, and writes exactly one JSON
    result line to stdout, then returns (the caller exits 0). NO network,
    NO database, NO import or use of this module's repository/service/
    audit-sink classes -- pure bytes-in/JSON-out, using only the same
    deterministic decode/parse/extract/sanitize pipeline functions every
    in-process content type already goes through.

    At the very first opportunity -- before reading or touching a single
    byte of the untrusted payload -- attempts a best-effort hard memory
    ceiling on ITSELF via ``resource.setrlimit``: ``RLIMIT_AS`` first (the
    correct, standard choice on Linux), falling back to ``RLIMIT_DATA`` if
    that itself fails to even set. Both are silently skipped, never fatal,
    if the platform does not support them at all -- verified directly that
    macOS/Darwin does not (``setrlimit`` raises
    ``ValueError("current limit exceeds maximum limit")`` for both, for a
    FRESH child exactly as it does for an already-large process -- a
    platform limitation, not a "process already too large" one; verified
    separately, and just as directly, that a FRESH child process CAN
    attempt to lower its own limit at all, unlike the already-running,
    already-large parent process, which cannot). This rlimit attempt is a
    best-effort fast-fail nicety, not the guarantee: the load-bearing
    property is that this whole process's entire address space -- whatever
    pypdf/zipfile/ElementTree allocate inside it, rlimit-bounded or not --
    is reclaimed by the OS the instant this process exits, is killed, or
    the parent's wall-clock ``subprocess.run(..., timeout=...)`` fires.
    """
    try:
        import resource

        for limit_name in ("RLIMIT_AS", "RLIMIT_DATA"):
            limit_id = getattr(resource, limit_name, None)
            if limit_id is None:
                continue
            try:
                ceiling = MAX_SUBPROCESS_MEMORY_CEILING_BYTES
                resource.setrlimit(limit_id, (ceiling, ceiling))
                break
            except (ValueError, OSError):
                continue
    except ImportError:  # pragma: no cover - resource is POSIX-only; no Windows deployment target
        pass

    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8"))
        content_type = payload["content_type"]
        decoded = base64.b64decode(payload["decoded_b64"])
        limits = MemberImportLimits(**payload["limits"])

        try:
            parsed = _parse(decoded, content_type, limits)
        except _PipelineHalt as halt:
            response = {"parsed": False, "outcome": halt.outcome, "reason": halt.reason}
        else:
            try:
                text, truncated = _extract(parsed, content_type, limits)
            except _PipelineHalt as halt:
                response = {"parsed": True, "extract_halt": {"outcome": halt.outcome, "reason": halt.reason}}
            else:
                response = {"parsed": True, "text": text, "truncated": truncated}
    except MemoryError:
        # The child hit its own isolation ceiling (RLIMIT_AS/RLIMIT_DATA,
        # which DOES enforce on Linux) somewhere outside the parse/extract
        # handlers. That is a resource bound, never a malformed document --
        # reporting it as parser_failure would misattribute a resource
        # attack to a broken file (CI on Linux caught exactly this,
        # 2026-09-01).
        response = {
            "parsed": False,
            "outcome": OUTCOME_REFUSED,
            "reason": REASON_PARSER_RESOURCE_BOUNDS,
        }
    except Exception:
        # Any unexpected failure reading/decoding the payload itself
        # (never the untrusted document's own content -- that is entirely
        # _parse()/_extract()'s well-tested territory, already converted
        # to a _PipelineHalt above) is reported the same truthful way; the
        # parent's own generic nonzero-exit mapping is the fallback if
        # even this write cannot complete.
        response = {"parsed": False, "outcome": OUTCOME_REFUSED, "reason": REASON_PARSER_FAILURE}

    sys.stdout.write(json.dumps(response))
    sys.stdout.flush()


def _run_pipeline(
    user_key: str, import_key: str, content_type: str, admitted: object, *, limits: MemberImportLimits, now: datetime
) -> tuple[str | None, str, str | None, bool, tuple[ImportStageOutcome, ...]]:
    """Runs decode -> parse -> extract, appending exactly one
    :class:`ImportStageOutcome` per stage attempted (success name, or the
    terminal failure classification on the stage that halts the pipeline).
    Returns ``(text_or_none, outcome, reason, truncated, trail)``.

    Independent review, fourth round (2026-09-02): for PDF and DOCX
    specifically, the parse and extract stages together run INSIDE an
    isolated child process (:func:`_run_isolated_parse_and_extract`) rather
    than calling :func:`_parse`/:func:`_extract` directly in this process --
    see the extended comment at MAX_SUBPROCESS_MEMORY_CEILING_BYTES for why.
    Paste and plain-text uploads are pure Python string operations with no
    third-party decompression risk and continue to run in-process exactly
    as before.
    """
    trail: list[ImportStageOutcome] = []

    def _append(outcome: str, reason: str | None = None) -> None:
        trail.append(
            ImportStageOutcome(
                import_key=import_key, user_key=user_key, outcome=outcome, reason_code=reason, occurred_at=now
            )
        )

    try:
        decoded = _decode(admitted, content_type)
    except _PipelineHalt as halt:
        _append(halt.outcome, halt.reason)
        return None, halt.outcome, halt.reason, False, tuple(trail)
    _append(OUTCOME_DECODED)

    if content_type in _ISOLATED_CONTENT_TYPES:
        parsed_ok, halt_outcome, halt_reason, text, truncated = _run_isolated_parse_and_extract(
            content_type, decoded, limits
        )
        if not parsed_ok:
            _append(halt_outcome, halt_reason)
            return None, halt_outcome, halt_reason, False, tuple(trail)
        _append(OUTCOME_PARSED)
        if halt_outcome is not None:
            _append(halt_outcome, halt_reason)
            return None, halt_outcome, halt_reason, False, tuple(trail)
    else:
        try:
            parsed = _parse(decoded, content_type, limits)
        except _PipelineHalt as halt:
            _append(halt.outcome, halt.reason)
            return None, halt.outcome, halt.reason, False, tuple(trail)
        _append(OUTCOME_PARSED)

        try:
            text, truncated = _extract(parsed, content_type, limits)
        except _PipelineHalt as halt:
            _append(halt.outcome, halt.reason)
            return None, halt.outcome, halt.reason, False, tuple(trail)

    if not text:
        _append(OUTCOME_EMPTY)
        return None, OUTCOME_EMPTY, None, False, tuple(trail)
    if truncated:
        _append(OUTCOME_PARTIAL, REASON_OUTPUT_TRUNCATED)
        return text, OUTCOME_PARTIAL, REASON_OUTPUT_TRUNCATED, True, tuple(trail)
    _append(OUTCOME_EXTRACTED)
    return text, OUTCOME_EXTRACTED, None, False, tuple(trail)


def _default_flag_reader(name: str) -> bool:
    """The repo-wide boolean-env idiom (``app.py``'s
    ``PEERSLATE_*_ENABLED`` flags): ``os.environ.get(name, "false").lower()
    == "true"``."""
    return os.environ.get(name, "false").lower() == "true"


def _default_adapter_resolver() -> FetchAdapter | None:
    """Guarded dynamic import (doc 14 design B): resolves
    :data:`FETCH_MODULE`'s :data:`FETCH_FACTORY` only if the module exists,
    exposes a callable factory, and that factory can be constructed without
    raising.  Every other case returns ``None`` -- never an exception the
    caller has to specifically catch, and never a hint distinguishing
    "module absent" from "module broken" (both are the identical,
    content-free ``adapter_absent`` refusal)."""
    try:
        module = importlib.import_module(FETCH_MODULE)
    except ImportError:
        return None
    factory = getattr(module, FETCH_FACTORY, None)
    if not callable(factory):
        return None
    try:
        return factory()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MemberImportService:
    def __init__(
        self,
        repository: MemberImportRepository,
        audit_sink: AuditSink,
        *,
        limits: MemberImportLimits = MemberImportLimits(),
        rights_reader: RightsObligationReader = NoneRightsObligationReader(),
        flag_reader=_default_flag_reader,
        adapter_resolver=_default_adapter_resolver,
    ) -> None:
        self.repository = repository
        self._audit_sink = audit_sink
        self._limits = limits
        self._rights_reader = rights_reader
        self._flag_reader = flag_reader
        self._adapter_resolver = adapter_resolver
        self._lock = getattr(repository, "_lock", None) or threading.RLock()
        # doc 09 §4 blind-retry lockout: user_key -> the set of
        # idempotency_keys whose write outcome is unknown until a state
        # reload proves the truth.
        self._unknown_outcomes: dict[str, set[str]] = {}

    # -- idempotency plumbing (C3 pattern) -----------------------------

    def _begin(
        self, user_key: str, idempotency_key: str, command: str, canonical: object, now: datetime
    ) -> tuple[object | None, str, str]:
        key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        digest = _canonical_hash(command, canonical)
        record = self.repository._idempotency_record(user_key, key, now)
        if record is not None:
            if record.command == command and record.canonical_input_hash == digest:
                return record.result, key, digest
            raise MemberImportServiceError("idempotency_mismatch")
        return None, key, digest

    def _finish(self, user_key: str, idempotency_key: str, command: str, digest: str, result: object, now: datetime) -> None:
        record = _IdempotencyRecord(command=command, canonical_input_hash=digest, result=result, expires_at=now + IDEMPOTENCY_TTL)
        self.repository._record_idempotency(user_key, idempotency_key, record)

    def _emit(
        self, event_kind: str, user_key: str, keys: Sequence[str], reason_code: str | None,
        actor: str, host_class: str, at: datetime,
    ) -> None:
        self._audit_sink.emit(
            MemberImportAuditEvent(
                event_kind=event_kind, user_key=user_key, keys=tuple(keys), reason_code=reason_code,
                host_class=host_class, actor=actor, at=at,
            )
        )

    # -- doc 09 §4 unknown-outcome write discipline --------------------

    def _check_not_locked(self, user_key: str, idempotency_key: str) -> None:
        locked = self._unknown_outcomes.get(user_key)
        if locked and idempotency_key in locked:
            raise MemberImportServiceError("retry_locked_state_reload_required", recoverable=True)

    def _lock_unknown_outcome(self, user_key: str, idempotency_key: str) -> None:
        self._unknown_outcomes.setdefault(user_key, set()).add(idempotency_key)

    def _clear_unknown_outcomes(self, user_key: str) -> None:
        self._unknown_outcomes.pop(user_key, None)

    def _record_unknown_write_failure(self, user_key: str, idempotency_key: str, keys: Sequence[str], now: datetime) -> None:
        # No idempotency receipt is recorded (the command did not complete
        # -- a later legitimate retry must be able to run), no record is
        # fabricated, and the blind-retry lockout is armed before raising.
        self._lock_unknown_outcome(user_key, idempotency_key)
        self._emit("persistence_failure", user_key, keys, None, "member", HOST_CLASS_NOT_APPLICABLE, now)

    def _enforce_active_ceiling(self, user_key: str) -> None:
        if self.repository.active_import_count(user_key) >= self._limits.max_active_imports_per_member:
            raise MemberImportServiceError("import_limit_reached", recoverable=True)

    def _build_record(
        self, *, import_key: str, user_key: str, data_class: str, intake_method: str,
        declared_content_type: str | None, byte_count: int | None, content_hash: str | None,
        sanitized_text: str | None, extracted_units: int | None, truncated: bool,
        outcome: str, outcome_reason: str | None, now: datetime,
        submitted_url: str | None = None, final_url: str | None = None,
        resolved_address: str | None = None, fetched_at: datetime | None = None,
    ) -> MemberImport:
        return MemberImport(
            import_key=import_key, user_key=user_key, data_class=data_class, intake_method=intake_method,
            record_state=RECORD_STATE_ACTIVE, declared_content_type=declared_content_type, byte_count=byte_count,
            submitted_url=submitted_url, final_url=final_url, resolved_address=resolved_address, fetched_at=fetched_at,
            content_hash=content_hash, sanitizer_version=SANITIZER_VERSION, sanitized_text=sanitized_text,
            extracted_units=extracted_units, truncated=truncated, outcome=outcome, outcome_reason=outcome_reason,
            rights_obligation_class=RIGHTS_NONE, body_removed_at=None, body_removal_reason=None,
            created_at=now, updated_at=now,
        )

    def _persist_record_and_trail(
        self, record: MemberImport, trail: tuple[ImportStageOutcome, ...], key: str, digest: str, command: str, now: datetime  # noqa: ARG002
    ) -> None:
        try:
            self.repository.persist_import(record)
            for stage_outcome in trail:
                self.repository.append_stage_outcome(stage_outcome)
        except RepositoryWriteError:
            self._record_unknown_write_failure(record.user_key, key, (record.import_key,), now)
            raise MemberImportServiceError("import_outcome_unknown", recoverable=True)

    def _emit_pipeline_audit(self, user_key: str, record: MemberImport, now: datetime, *, host_class: str = HOST_CLASS_NOT_APPLICABLE) -> None:
        kind = {
            OUTCOME_EXTRACTED: "import_stored",
            OUTCOME_PARTIAL: "import_partial",
            OUTCOME_EMPTY: "import_empty",
        }.get(record.outcome, "import_refused")  # refused/timeout/blocked all group under import_refused
        self._emit(kind, user_key, (record.import_key,), record.outcome_reason, "member", host_class, now)

    # -- intake (unconditional, permanent) -----------------------------

    def submit_paste(
        self, user_key: str, text: object, idempotency_key: str, *, data_class: str = "production", now: datetime | None = None
    ) -> ImportReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if data_class not in DATA_CLASSES:
            raise MemberImportServiceError("data_class_invalid")
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = COMMAND_SUBMIT_PASTE
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            try:
                normalized_text = validate_paste(text, self._limits)
            except MemberImportServiceError as error:
                self._emit("import_refused", user_key, (), error.failure_code, "member", HOST_CLASS_NOT_APPLICABLE, now)
                raise

            canonical = {"data_class": data_class, "content_hash": _content_hash(normalized_text)}
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, ImportReceipt)

            self._enforce_active_ceiling(user_key)

            import_key = _opaque_key()
            text_out, outcome, reason, truncated, trail = _run_pipeline(
                user_key, import_key, "text/plain", normalized_text, limits=self._limits, now=now
            )
            record = self._build_record(
                import_key=import_key, user_key=user_key, data_class=data_class, intake_method=INTAKE_PASTE,
                declared_content_type=None, byte_count=None, content_hash=_content_hash(normalized_text),
                sanitized_text=(text_out if outcome in (OUTCOME_EXTRACTED, OUTCOME_PARTIAL) else None),
                extracted_units=(_utf16_units(text_out) if text_out else None),
                truncated=truncated, outcome=outcome, outcome_reason=reason, now=now,
            )
            self._persist_record_and_trail(record, trail, key, digest, command, now)
            self._emit_pipeline_audit(user_key, record, now)
            receipt = ImportReceipt(
                import_key=record.import_key, command=command, outcome=outcome, outcome_reason=reason, truncated=truncated
            )
            self._finish(user_key, key, command, digest, receipt, now)
            return receipt

    def submit_upload(
        self, user_key: str, upload: object, idempotency_key: str, *, data_class: str = "production", now: datetime | None = None
    ) -> ImportReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if data_class not in DATA_CLASSES:
            raise MemberImportServiceError("data_class_invalid")
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = COMMAND_SUBMIT_UPLOAD
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            try:
                validated = validate_upload(upload, self._limits)
            except MemberImportServiceError as error:
                self._emit("import_refused", user_key, (), error.failure_code, "member", HOST_CLASS_NOT_APPLICABLE, now)
                raise

            canonical = {
                "data_class": data_class,
                "declared_content_type": validated.declared_content_type,
                "content_hash": _content_hash(validated.data),
            }
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, ImportReceipt)

            self._enforce_active_ceiling(user_key)

            import_key = _opaque_key()
            text_out, outcome, reason, truncated, trail = _run_pipeline(
                user_key, import_key, validated.declared_content_type, validated.data, limits=self._limits, now=now
            )
            record = self._build_record(
                import_key=import_key, user_key=user_key, data_class=data_class, intake_method=INTAKE_UPLOAD,
                declared_content_type=validated.declared_content_type, byte_count=validated.byte_length,
                content_hash=_content_hash(validated.data),
                sanitized_text=(text_out if outcome in (OUTCOME_EXTRACTED, OUTCOME_PARTIAL) else None),
                extracted_units=(_utf16_units(text_out) if text_out else None),
                truncated=truncated, outcome=outcome, outcome_reason=reason, now=now,
            )
            self._persist_record_and_trail(record, trail, key, digest, command, now)
            self._emit_pipeline_audit(user_key, record, now)
            receipt = ImportReceipt(
                import_key=record.import_key, command=command, outcome=outcome, outcome_reason=reason, truncated=truncated
            )
            self._finish(user_key, key, command, digest, receipt, now)
            return receipt

    # -- the prebuilt DISABLED service-level fetch port (doc 14 design B) --

    def import_from_url(
        self, user_key: str, url: object, idempotency_key: str, *, data_class: str = "production", now: datetime | None = None
    ) -> ImportReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if data_class not in DATA_CLASSES:
            raise MemberImportServiceError("data_class_invalid")
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = COMMAND_IMPORT_FROM_URL
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)

            # Resolution rule (doc 14 design B, verbatim): the `url` value
            # is never inspected, bounded, canonicalized, hashed, or
            # referenced in ANY way until every availability gate has
            # passed -- guaranteeing the refusal path can never leak or
            # record anything about it.
            if not self._flag_reader(FLAG_SURFACE):
                self._emit("url_fetch_unavailable", user_key, (), "surface_flag_off", "member", HOST_CLASS_NOT_APPLICABLE, now)
                raise MemberImportServiceError("url_fetch_unavailable", recoverable=True)
            if not self._flag_reader(FLAG_URL_FETCH):
                self._emit("url_fetch_unavailable", user_key, (), "fetch_flag_off", "member", HOST_CLASS_NOT_APPLICABLE, now)
                raise MemberImportServiceError("url_fetch_unavailable", recoverable=True)
            adapter = self._adapter_resolver()
            if adapter is None:
                self._emit("url_fetch_unavailable", user_key, (), "adapter_absent", "member", HOST_CLASS_NOT_APPLICABLE, now)
                raise MemberImportServiceError("url_fetch_unavailable", recoverable=True)

            # -- C13-era downstream path; proven now via an injected test
            #    double (§5.C pre-proof); C10 implements this fully so C13
            #    is adapter-module-only. --
            validated_url = _bounded_string(url, "url", MAX_URL_UTF16_UNITS)
            canonical = {"data_class": data_class, "url": validated_url}
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, ImportReceipt)

            self._enforce_active_ceiling(user_key)
            import_key = _opaque_key()

            try:
                fetched = adapter.fetch(validated_url)
            except FetchRefused as refusal:
                outcome, reason = _map_fetch_refusal(refusal)
                trail = (
                    ImportStageOutcome(
                        import_key=import_key, user_key=user_key, outcome=outcome, reason_code=reason, occurred_at=now
                    ),
                )
                record = self._build_record(
                    import_key=import_key, user_key=user_key, data_class=data_class, intake_method=INTAKE_URL_FETCH,
                    declared_content_type=None, byte_count=None, content_hash=None,
                    sanitized_text=None, extracted_units=None, truncated=False,
                    outcome=outcome, outcome_reason=reason, now=now,
                )
                self._persist_record_and_trail(record, trail, key, digest, command, now)
                self._emit_pipeline_audit(user_key, record, now, host_class=refusal.host_class)
                receipt = ImportReceipt(
                    import_key=record.import_key, command=command, outcome=outcome, outcome_reason=reason, truncated=False
                )
                self._finish(user_key, key, command, digest, receipt, now)
                return receipt

            fetched_stage = ImportStageOutcome(
                import_key=import_key, user_key=user_key, outcome=OUTCOME_FETCHED, reason_code=None, occurred_at=now
            )
            text_out, outcome, reason, truncated, pipeline_trail = _run_pipeline(
                user_key, import_key, fetched.declared_content_type, fetched.data, limits=self._limits, now=now
            )
            full_trail = (fetched_stage,) + pipeline_trail
            record = self._build_record(
                import_key=import_key, user_key=user_key, data_class=data_class, intake_method=INTAKE_URL_FETCH,
                declared_content_type=fetched.declared_content_type, byte_count=len(fetched.data),
                content_hash=_content_hash(fetched.data),
                sanitized_text=(text_out if outcome in (OUTCOME_EXTRACTED, OUTCOME_PARTIAL) else None),
                extracted_units=(_utf16_units(text_out) if text_out else None),
                truncated=truncated, outcome=outcome, outcome_reason=reason, now=now,
                submitted_url=validated_url, final_url=fetched.final_url,
                resolved_address=fetched.resolved_address, fetched_at=fetched.fetched_at,
            )
            self._persist_record_and_trail(record, full_trail, key, digest, command, now)
            self._emit_pipeline_audit(user_key, record, now, host_class=fetched.host_class)
            receipt = ImportReceipt(
                import_key=record.import_key, command=command, outcome=outcome, outcome_reason=reason, truncated=truncated
            )
            self._finish(user_key, key, command, digest, receipt, now)
            return receipt

    # -- owner reads (authorization before retrieval; rights at point of use) --

    def get_import(self, user_key: str, import_key: str, *, now: datetime | None = None) -> MemberImport:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        import_key = _owner_key_or_not_found(import_key, MAX_IMPORT_KEY_UTF16_UNITS)
        with self._lock:
            record = self.repository.import_for_owner(user_key, import_key)
            if record is None:
                raise MemberImportServiceError("not_found")
            self._clear_unknown_outcomes(user_key)

            obligation = self._rights_reader.obligation_for(record)
            if obligation not in RIGHTS_OBLIGATION_CLASSES:
                raise ValueError("rights_obligation_invalid")

            if obligation == RIGHTS_TAKEDOWN_REQUIRED and record.body_removed_at is None:
                updated = replace(
                    record, sanitized_text=None, body_removed_at=now,
                    body_removal_reason=BODY_REMOVAL_RIGHTS_TAKEDOWN,
                    rights_obligation_class=RIGHTS_TAKEDOWN_REQUIRED, updated_at=now,
                )
                try:
                    self.repository.update_import(updated)
                except RepositoryWriteError:
                    # Best-effort against the repository -- "truth is
                    # derived, storage catches up" (C6's
                    # _finalize_if_elapsed idiom): a persistence hiccup here
                    # must never risk SHOWING removed content, so the
                    # truthfully-hidden projection is still what is
                    # returned even if the write itself could not be
                    # durably recorded this pass.
                    self._emit(
                        "persistence_failure", user_key, (import_key,), None,
                        "system:rights_point_of_use", HOST_CLASS_NOT_APPLICABLE, now,
                    )
                else:
                    self._emit(
                        "import_body_removed_rights", user_key, (import_key,), None,
                        "system:rights_point_of_use", HOST_CLASS_NOT_APPLICABLE, now,
                    )
                return updated
            return record

    def list_imports(self, user_key: str, *, now: datetime | None = None) -> tuple[MemberImport, ...]:  # noqa: ARG002
        user_key = _require_user_key(user_key)
        with self._lock:
            rows = self.repository.imports_for_owner(user_key)
            ordered = tuple(sorted(rows, key=lambda record: (record.created_at, record.import_key), reverse=False))
            ordered = tuple(sorted(ordered, key=lambda record: record.created_at, reverse=True))
            self._clear_unknown_outcomes(user_key)
            return ordered

    def stage_outcomes(self, user_key: str, import_key: str) -> tuple[ImportStageOutcome, ...]:
        user_key = _require_user_key(user_key)
        import_key = _owner_key_or_not_found(import_key, MAX_IMPORT_KEY_UTF16_UNITS)
        with self._lock:
            record = self.repository.import_for_owner(user_key, import_key)
            if record is None:
                raise MemberImportServiceError("not_found")
            return self.repository.stage_outcomes_for_owner(user_key, import_key)

    # -- member data rights (doc 08 §5, doc 02 §4) ----------------------

    def delete_import(
        self, user_key: str, import_key: str, idempotency_key: str, *, now: datetime | None = None
    ) -> ImportReceipt:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        import_key = _owner_key_or_not_found(import_key, MAX_IMPORT_KEY_UTF16_UNITS)
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = COMMAND_DELETE_IMPORT
        canonical = {"import_key": import_key}
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, ImportReceipt)

            record = self.repository.import_for_owner(user_key, import_key)
            if record is None:
                raise MemberImportServiceError("not_found")
            if record.record_state == RECORD_STATE_DELETED:
                raise MemberImportServiceError("already_deleted", current_state=record)

            updated = replace(
                record, sanitized_text=None, record_state=RECORD_STATE_DELETED,
                body_removed_at=now, body_removal_reason=BODY_REMOVAL_MEMBER_DELETE, updated_at=now,
            )
            try:
                self.repository.update_import(updated)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (import_key,), now)
                raise MemberImportServiceError("import_outcome_unknown", recoverable=True)

            receipt = ImportReceipt(
                import_key=import_key, command=command, outcome=RECORD_STATE_DELETED, outcome_reason=None, truncated=False
            )
            self._finish(user_key, key, command, digest, receipt, now)
            self._emit("import_deleted", user_key, (import_key,), None, "member", HOST_CLASS_NOT_APPLICABLE, now)
            return receipt

    def export_imports(self, user_key: str, *, now: datetime | None = None) -> dict:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        with self._lock:
            rows = self.repository.imports_for_owner(user_key)
            ordered = tuple(sorted(rows, key=lambda record: record.created_at))
            payload_records = []
            for record in ordered:
                trail = self.repository.stage_outcomes_for_owner(user_key, record.import_key)
                payload_records.append(
                    {
                        "import_key": record.import_key,
                        "data_class": record.data_class,
                        "intake_method": record.intake_method,
                        "record_state": record.record_state,
                        "declared_content_type": record.declared_content_type,
                        "byte_count": record.byte_count,
                        "submitted_url": record.submitted_url,
                        "final_url": record.final_url,
                        "resolved_address": record.resolved_address,
                        "fetched_at": record.fetched_at.isoformat() if record.fetched_at else None,
                        "content_hash": record.content_hash,
                        "sanitizer_version": record.sanitizer_version,
                        "sanitized_text": record.sanitized_text,
                        "extracted_units": record.extracted_units,
                        "truncated": record.truncated,
                        "outcome": record.outcome,
                        "outcome_reason": record.outcome_reason,
                        "rights_obligation_class": record.rights_obligation_class,
                        "body_removed_at": record.body_removed_at.isoformat() if record.body_removed_at else None,
                        "body_removal_reason": record.body_removal_reason,
                        "created_at": record.created_at.isoformat(),
                        "updated_at": record.updated_at.isoformat(),
                        "stage_outcomes": [
                            {
                                "outcome": stage.outcome,
                                "reason_code": stage.reason_code,
                                "occurred_at": stage.occurred_at.isoformat(),
                            }
                            for stage in trail
                        ],
                    }
                )
            self._emit(
                "import_exported", user_key, tuple(record.import_key for record in ordered), None,
                "member", HOST_CLASS_NOT_APPLICABLE, now,
            )
            return {"contract_version": CONTRACT_VERSION, "exported_at": now.isoformat(), "imports": payload_records}

    def purge_expired_idempotency(self, *, now: datetime) -> int:
        now = _utc(now)
        with self._lock:
            return self.repository.purge_expired_idempotency(now=now)


# ---------------------------------------------------------------------------
# Module-as-script entry point (independent review, fourth round,
# 2026-09-02): re-invoked as ``python -m
# services.my_opportunities.member_import_service --pdf-docx-parse-worker``
# by :func:`_run_isolated_parse_and_extract` to become the isolated child
# process. A plain ``import`` of this module (the normal Flask-app case)
# never executes this block. Every other CLI invocation shape (no args, an
# unrecognized flag) is a deliberate, silent no-op -- this file is not
# meant to be run directly for any other purpose.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == _SUBPROCESS_WORKER_FLAG:
        _subprocess_worker_main()
