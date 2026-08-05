"""Opportunity Slate document upload and public-link import — PS-OPPSLATE-001,
slice OS-6.

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001. Controlling contract:
01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md section 11 (security contract,
reproduced below as literally as Python allows) and section 7 (failure
truth). This module owns the two highest-risk operations this package adds:
turning an untrusted uploaded file into plain text, and fetching an
employer's public page over the network on the member's behalf.

**Nothing here talks to the AI provider and nothing here persists anything.**
It returns plain validated text (or raises a stable, owner-safe error code);
``opportunity_slate_routes.py`` is the only caller, and it hands the returned
text to the SAME ``opportunity_slate_service.save_source_for_owner`` call the
paste path already uses, with ``capture_method="uploaded"`` or
``"imported"``. Every byte this module reads from a file or a network
response is untrusted DATA — it is walked for text, never executed,
evaluated, or treated as a command.

Upload contract (handoff section 11, "Upload intake")
-------------------------------------------------------
Declared-MIME allowlist (PDF/DOCX/TXT); bounded read (the ``MAX + 1``
idiom that :func:`services.photo_capture_service.validate_photo_upload`
already uses); magic-byte verification independent of the declared type;
structure-only parsing (no macro or script evaluation — PDF text extraction
never touches ``/OpenAction``/``/AA``/JavaScript names, and DOCX extraction
never evaluates a field, a macro, or an OOXML relationship, it only walks
``w:t`` runs); a hard output cap on extracted text (below, tied to the
already-shipped ``MAX_SOURCE_TEXT_UNITS`` — see the module docstring note by
:data:`MAX_EXTRACTED_TEXT_UNITS`).

Import contract (handoff section 11, "Public-link import" — the highest-risk
surface, SSRF)
-------------------------------------------------------
``https`` only; the target hostname is resolved and **every** resolved
address is required to be public unicast (reject private, loopback,
link-local, multicast, reserved, and unspecified ranges — this closes the
cloud-metadata address off too, since ``169.254.169.254`` is link-local); the
validated address is then **pinned** for the actual TCP connection
(:class:`_PinnedHTTPSConnection` connects to the numeric IP directly and
presents the original hostname only as the TLS SNI / ``Host`` header), which
defeats a DNS-rebinding attack that would otherwise re-resolve to a different
address between the check and the connect. Redirects are re-validated at
every hop with the same DNS-then-pin sequence, capped at
:data:`MAX_IMPORT_REDIRECTS`. Response size and total wall-clock time are
both capped. Extraction is HTML-to-text only (:class:`_VisibleTextExtractor`
is a pure tokenizer over already-fetched bytes; it never evaluates
``<script>``, never fetches an image, stylesheet, or any other referenced
asset, and never follows a link other than a same-request redirect).

No bare ``requests.get``/``urllib.request.urlopen`` on a member-supplied URL
exists anywhere in this module or its caller — :func:`guarded_fetch_html` is
the only path an imported URL can reach the network through.
"""

from __future__ import annotations

import http.client
import ipaddress
import os
import re
import socket
import ssl
import time
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from services.opportunity_slate_service import MAX_SOURCE_TEXT_UNITS


class OpportunitySourceIntakeError(RuntimeError):
    """A stable, member-safe outcome code.

    Every code below maps, at the route layer, to one of the handoff's two
    truthful failure cards ("We couldn't read this document." for upload,
    "Nothing was saved or analyzed." for import) — never to a raw exception
    message, and never to a hint about *why* in a way that would help an
    attacker calibrate a probe (the same reasoning
    ``services/photo_capture_service.py`` already applies to its own codes).
    """

    def __init__(self, code):
        self.code = code
        super().__init__(code)


# ---------------------------------------------------------------------------
# Shared bounds
#
# The extracted text this module returns is handed to
# ``opportunity_slate_service.save_source_for_owner``, which runs it through
# ``validate_source_text`` — the SAME ``MAX_SOURCE_TEXT_UNITS`` (20,000 UTF-16
# code units) the paste path enforces, and the migration's
# CK_opportunity_source_versions_original_length CHECK enforces identically in
# the database. The handoff's section 11 text proposes a "60k units" output
# cap for upload extraction specifically; that number predates (or was never
# reconciled with) the single, capture-method-uniform 20,000-unit column
# constraint the OS-1 migration actually shipped, and nothing this module
# does can persist more than the column accepts regardless of what number is
# chosen here. Extracting to 60k and then failing the save with a generic
# "too long" error would contradict the failure-truth contract's own test
# requirement ("output-cap truncation labeled truthfully") — a truncation
# labeled to the member, not a same-shape rejection reusing the paste path's
# unrelated field error. This module therefore caps extraction at the
# constraint that is actually enforceable end to end, truncates cleanly at a
# UTF-16 boundary, and reports the fact via the returned ``truncated`` flag
# so the route can render an honest notice. See the OS-6 completion report
# for this reconciliation.
# ---------------------------------------------------------------------------
MAX_EXTRACTED_TEXT_UNITS = MAX_SOURCE_TEXT_UNITS

# Upload bounds (mirrors services/photo_capture_service.py's
# os.getenv(..., default) idiom for every operator-tunable bound).
MAX_UPLOAD_BYTES = int(os.getenv("OPPSLATE_UPLOAD_MAX_BYTES", str(15 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("OPPSLATE_UPLOAD_MAX_PDF_PAGES", "400"))
# Independent review finding F4: a single 80KB PDF whose one page's content
# stream decoded to ~40MB (an ordinary, non-malformed FlateDecode stream —
# no zip-bomb-style header lie is even needed here, DEFLATE alone gives
# this ratio on repetitive operator text) burned 79s of CPU and ~2GB RSS
# inside pypdf's own text-extraction tokenizer, which has no size or time
# bound of its own. Two independent measurements calibrate the fix below:
#   * decompressing a content stream (``get_data()``) is CHEAP regardless of
#     its decoded size — 42MB decoded in ~0.1s in testing — so checking the
#     DECODED length before tokenizing it is itself a fast operation, not
#     something that reintroduces the same cost it is guarding against.
#   * ``extract_text()`` (the actual slow step, the per-operator Python
#     tokenizer) measured at roughly 0.4-0.5s per decoded megabyte on this
#     hardware; a naive adoption of the "8MB, far above any real job
#     posting" figure floated as illustrative during review was tested
#     directly and found to cost ~18s of tokenization time on its own for
#     ONE page — clearly not an acceptable per-request bound for a
#     synchronous upload route. 2MB is used instead (roughly 2-3s worst
#     case per page on this hardware), which is still enormously more
#     content-stream text than any real single-page job posting or resume
#     would ever legitimately contain.
MAX_PDF_PAGE_CONTENT_BYTES = int(
    os.getenv("OPPSLATE_UPLOAD_MAX_PDF_PAGE_CONTENT_BYTES", str(2 * 1024 * 1024))
)
# The wall-clock backstop across the WHOLE multi-page extraction loop —
# independent of the per-page pre-screen above, and the only thing that
# bounds a legitimately-shaped document whose page count times per-page
# tokenization time still adds up to too long. Checked between pages, not
# used to interrupt a single already-in-flight extract_text() call (Python
# cannot safely preempt a pure-CPU call from outside without a
# signal/subprocess mechanism this codebase does not use elsewhere — see
# the OS-6 completion report for why that trade-off was accepted); the
# per-page content-size pre-screen above is what actually prevents a
# single call from ever running long enough for this to matter.
PDF_EXTRACTION_TIMEOUT_SECONDS = float(
    os.getenv("OPPSLATE_UPLOAD_PDF_TIMEOUT_SECONDS", "20")
)
MAX_DOCX_ENTRIES = 2000
MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES = 60 * 1024 * 1024
# A conservative zip-bomb heuristic: reject any single entry whose declared
# uncompressed size is more than this multiple of its compressed size. Real
# OOXML XML parts compress at roughly 5-12x; 200x is generous headroom that
# still catches a pathological single-entry bomb.
MAX_DOCX_ENTRY_COMPRESSION_RATIO = 200

ALLOWED_UPLOAD_CONTENT_TYPES = frozenset(
    {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}
)

_DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Import bounds.
MAX_IMPORT_URL_LENGTH = 2048
MAX_IMPORT_REDIRECTS = 3
MAX_IMPORT_RESPONSE_BYTES = int(
    os.getenv("OPPSLATE_IMPORT_MAX_BYTES", str(5 * 1024 * 1024))
)
IMPORT_CONNECT_TIMEOUT_SECONDS = float(
    os.getenv("OPPSLATE_IMPORT_CONNECT_TIMEOUT_SECONDS", "5")
)
IMPORT_TOTAL_TIMEOUT_SECONDS = float(
    os.getenv("OPPSLATE_IMPORT_TOTAL_TIMEOUT_SECONDS", "10")
)
IMPORT_READ_CHUNK_BYTES = 65536
# v1 restricts import to the standard HTTPS port. A "public employer or ATS
# page" (handoff section 11) is served on 443; accepting an arbitrary port
# would only widen the surface a validated-but-malicious host could expose
# internal services on, for no real member benefit.
IMPORT_ALLOWED_PORT = 443
_IMPORT_USER_AGENT = "PeerSlateOpportunitySlateImporter/1.0 (+https://peerslate.com)"


def utf16_length(value):
    return len(value.encode("utf-16-le")) // 2


def _truncate_to_units(text, max_units):
    """Cut ``text`` to at most ``max_units`` UTF-16 code units.

    Never splits a surrogate pair: a trailing lone high surrogate produced by
    the byte-level cut is dropped rather than emitted, which is what
    ``errors="ignore"`` does for an incomplete UTF-16 code unit on decode.
    Returns ``(text, truncated)``.
    """
    encoded = text.encode("utf-16-le")
    limit_bytes = max_units * 2
    if len(encoded) <= limit_bytes:
        return text, False
    return encoded[:limit_bytes].decode("utf-16-le", errors="ignore"), True


# Independent review: applied uniformly, as the last step, by every
# extraction path below (PDF, DOCX, TXT, and imported HTML) — never only
# the upload/TXT path. C0 controls (excluding the three legitimate
# whitespace characters) and DEL have no place in an employer's role
# wording; Unicode bidirectional override/isolate characters are the
# "Trojan Source" character class that can make displayed text read in a
# different order (or hide characters) than what is actually stored.
# Refused rather than silently stripped, for the same reason a truncation
# is labeled rather than silently applied: a member's captured source
# should never be quietly altered by this module, including to remove
# something hostile — an honest "we couldn't read this document" is the
# truthful outcome, not a silently sanitized document.
_HOSTILE_CONTROL_CHARS = frozenset(
    chr(codepoint) for codepoint in range(0x00, 0x20) if chr(codepoint) not in "\t\n\r"
) | {"\x7f"}
# Built from numeric code points ONLY — deliberately never typed as literal
# characters in this source file, so a diff or an editor never renders (or
# silently reorders/hides) the very characters this guard exists to catch.
# LRE, RLE, PDF, LRO, RLO (0x202A-0x202E) and LRI, RLI, FSI, PDI
# (0x2066-0x2069): the Unicode bidirectional-formatting "Trojan Source" set.
_BIDI_OVERRIDE_CODEPOINTS = (
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
)
_BIDI_OVERRIDE_CHARS = frozenset(chr(codepoint) for codepoint in _BIDI_OVERRIDE_CODEPOINTS)
_HOSTILE_CHARS = _HOSTILE_CONTROL_CHARS | _BIDI_OVERRIDE_CHARS


def _reject_hostile_characters(text):
    """Refuse text carrying a NUL/C0 control character, DEL, or a Unicode
    bidirectional-override/isolate character. Checked on the final,
    already-truncated text — the text that would actually be saved."""
    if any(character in _HOSTILE_CHARS for character in text):
        raise OpportunitySourceIntakeError("corrupt")
    return text


# ---------------------------------------------------------------------------
# Upload: declared-MIME allowlist, bounded read, magic-byte verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    declared_content_type: str
    byte_length: int


def _sniff_binary_kind(data):
    """Best-effort identification of what ``data`` actually is, from bytes
    alone — never from the caller's declared type. Used to catch a spoofed
    declaration (declared PDF, magic bytes ELF/ZIP/HTML/...) before any
    parser ever sees the bytes."""
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


def validate_upload(upload):
    """Validate declared type, bounded size, and true (sniffed) type.

    Mirrors ``photo_capture_service.validate_photo_upload`` exactly: read at
    most ``MAX_UPLOAD_BYTES + 1`` bytes so an oversized body is detected
    without ever buffering more than one byte past the limit, then confirm
    the bytes actually are what the caller declared before any structural
    parser runs.
    """
    if upload is None or not getattr(upload, "stream", None):
        raise OpportunitySourceIntakeError("required")
    declared = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0].strip()
    if declared not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise OpportunitySourceIntakeError("unsupported_type")

    data = upload.stream.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise OpportunitySourceIntakeError("too_large")
    if not data:
        raise OpportunitySourceIntakeError("required")

    sniffed = _sniff_binary_kind(data)
    if declared == "application/pdf" and sniffed != "pdf":
        raise OpportunitySourceIntakeError("unsupported_type")
    if declared == _DOCX_CONTENT_TYPE and sniffed != "zip":
        raise OpportunitySourceIntakeError("unsupported_type")
    if declared == "text/plain" and sniffed in {"pdf", "zip", "elf", "exe", "html", "binary"}:
        raise OpportunitySourceIntakeError("unsupported_type")

    return ValidatedUpload(
        data=data, declared_content_type=declared, byte_length=len(data)
    )


# ---------------------------------------------------------------------------
# PDF extraction (pypdf — pure Python, no macro/script evaluation; the
# library has no rendering or JavaScript engine, so a call to
# ``page.extract_text()`` cannot execute anything a malicious PDF embeds)
# ---------------------------------------------------------------------------


def _extract_pdf_text(data):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as error:  # pragma: no cover - dependency always pinned
        raise OpportunitySourceIntakeError("extraction_unavailable") from error

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            # Only the common "no real password, an empty owner password
            # locks editing" case is handled. Anything still encrypted after
            # that is honestly unreadable, never brute-forced.
            try:
                if reader.decrypt("") == 0:
                    raise OpportunitySourceIntakeError("corrupt")
            except OpportunitySourceIntakeError:
                raise
            except Exception as error:
                raise OpportunitySourceIntakeError("corrupt") from error

        pages = reader.pages
        if len(pages) == 0:
            raise OpportunitySourceIntakeError("corrupt")
        if len(pages) > MAX_PDF_PAGES:
            raise OpportunitySourceIntakeError("too_large")

        deadline = time.monotonic() + PDF_EXTRACTION_TIMEOUT_SECONDS
        chunks = []
        units = 0
        truncated = False
        for page in pages:
            if units >= MAX_EXTRACTED_TEXT_UNITS:
                truncated = True
                break
            if time.monotonic() >= deadline:
                # A legitimately-shaped document whose cumulative page
                # count made tokenization run long. Whatever text has
                # already been extracted from earlier pages is kept and
                # labeled truncated, rather than discarding real work —
                # the same truthful-truncation contract every other
                # extraction path in this module already follows.
                truncated = True
                break
            # Independent review F4: decode (cheap, ~0.1s even for tens of
            # MB) BEFORE tokenizing (the actually expensive step) so an
            # oversized page's real cost is never paid. A pre-screen
            # failure (an unexpected pypdf internal shape) is treated as
            # "cannot safely size this page" and refused the same as an
            # oversized one, never silently skipped past the guard.
            try:
                raw_content = page._get_contents_as_bytes()
            except Exception as error:
                raise OpportunitySourceIntakeError("too_large") from error
            if raw_content is not None and len(raw_content) > MAX_PDF_PAGE_CONTENT_BYTES:
                raise OpportunitySourceIntakeError("too_large")
            text = page.extract_text() or ""
            chunks.append(text)
            units += utf16_length(text) + 2  # +2 for the join separator
        joined = "\n\n".join(chunks)
    except OpportunitySourceIntakeError:
        raise
    except PyPdfError as error:
        raise OpportunitySourceIntakeError("corrupt") from error
    except Exception as error:
        # Untrusted, adversarial input: any other parser failure (a
        # malformed object graph pypdf's own error types do not cover) is
        # still an honest "we couldn't read this document", never a 500.
        raise OpportunitySourceIntakeError("corrupt") from error

    cleaned = joined.strip()
    if not cleaned:
        raise OpportunitySourceIntakeError("empty")
    text, cut = _truncate_to_units(cleaned, MAX_EXTRACTED_TEXT_UNITS)
    text = _reject_hostile_characters(text)
    return text, (truncated or cut)


# ---------------------------------------------------------------------------
# DOCX extraction (stdlib zipfile + xml.etree only)
#
# DOCX is a zip of XML. The only content this function ever reads is
# ``word/document.xml``'s ``w:t`` text runs — it never opens
# ``word/vbaProject.bin`` (a macro would live there), never resolves an
# OOXML relationship, and never evaluates a field code. defusedxml is not
# pinned in this repository (requirements.txt / requirements-sql.txt), so
# hardening is done without it: a legitimate Word-produced document.xml
# never carries a DOCTYPE declaration, so any that does is refused before
# xml.etree ever parses it — closing the entity-expansion (XXE / billion
# laughs) route without adding a dependency. Bounded zip-bomb guards (entry
# count, per-entry and total uncompressed size, compression-ratio heuristic)
# run before a single byte is decompressed.
# ---------------------------------------------------------------------------
_WORDPROCESSINGML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W_T = f"{{{_WORDPROCESSINGML_NS}}}t"
_W_TAB = f"{{{_WORDPROCESSINGML_NS}}}tab"
_W_BR = f"{{{_WORDPROCESSINGML_NS}}}br"
_W_P = f"{{{_WORDPROCESSINGML_NS}}}p"


def _safe_zip_member_names(archive):
    """A fast PRE-FILTER only — never the safety boundary.

    Independent review finding F3: every number this function reads
    (``file_size``, ``compress_size``) comes straight out of the zip
    central directory, which the archive's own bytes control. A crafted
    archive can declare whatever ``file_size`` it likes independent of what
    actually decompresses — measured: a 299KB archive with lying headers
    that this function's old, size-check-only version accepted allocated
    301MB when read. Central-directory numbers are still checked here
    because they let an obviously-oversized or -unreasonable claim be
    rejected before touching the archive at all (cheap, no decompression
    started yet), but nothing downstream may depend on them being honest.
    The actual bound is enforced separately, by :func:`_bounded_zip_read`,
    on the real bytes each open() + read(LIMIT + 1) call produces.
    """
    names = archive.namelist()
    if len(names) > MAX_DOCX_ENTRIES:
        raise OpportunitySourceIntakeError("too_large")
    total_declared = 0
    for info in archive.infolist():
        name = info.filename
        if name.startswith("/") or ".." in name.split("/"):
            raise OpportunitySourceIntakeError("corrupt")
        if info.file_size > MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES:
            raise OpportunitySourceIntakeError("too_large")
        if (
            info.compress_size > 0
            and info.file_size / max(info.compress_size, 1)
            > MAX_DOCX_ENTRY_COMPRESSION_RATIO
        ):
            raise OpportunitySourceIntakeError("corrupt")
        total_declared += info.file_size
        if total_declared > MAX_DOCX_TOTAL_UNCOMPRESSED_BYTES:
            raise OpportunitySourceIntakeError("too_large")
    return names


def _bounded_zip_read(archive, name, limit):
    """Read at most ``limit`` ACTUAL decompressed bytes of ``name``,
    regardless of what the archive's central directory claims about it.

    ``ZipExtFile.read(n)`` is an incrementally-decompressing stream read:
    passing a bounded ``n`` genuinely stops decompression once ``n`` bytes
    have been produced — verified directly (a ~2MB-on-disk archive
    declaring a 2GB member; ``.read(LIMIT + 1)`` returned in well under a
    second, producing only ``LIMIT + 1`` bytes, never approaching the
    declared size). ``archive.read(name)`` (no bound, what this module used
    before this fix) and any call passing ``-1`` or no argument instead
    decompress the entire member up front regardless of caller-side
    declared-size checks — this function exists so nothing in this module
    can do that by accident again.
    """
    with archive.open(name) as member:
        data = member.read(limit + 1)
    if len(data) > limit:
        raise OpportunitySourceIntakeError("too_large")
    return data


def _reject_doctype(xml_bytes):
    """Real OOXML document parts never declare a DOCTYPE; refuse any that
    do, before ``xml.etree`` ever parses them (closes XXE/billion-laughs
    without a defusedxml dependency).

    Independent review: an earlier version of this function scanned only
    the first 4KB on the theory that a DOCTYPE always precedes the
    document body — true for a well-formed document, but a crafted XML
    prolog can carry an oversized comment or processing instruction ahead
    of the DOCTYPE declaration, pushing it past a fixed window. The
    byte string handed in here is already bounded (by
    :func:`_bounded_zip_read`'s ``limit``, currently
    ``MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES``) before this function ever runs,
    so scanning the whole thing is itself a bounded, cheap operation — a
    single C-level substring search — not an unbounded one.
    """
    if b"<!doctype" in xml_bytes.lower():
        raise OpportunitySourceIntakeError("corrupt")


def _paragraph_text(paragraph_element):
    parts = []
    for node in paragraph_element.iter():
        if node.tag == _W_T:
            parts.append(node.text or "")
        elif node.tag == _W_TAB:
            parts.append("\t")
        elif node.tag == _W_BR:
            parts.append("\n")
    return "".join(parts)


def _extract_docx_text(data):
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = _safe_zip_member_names(archive)
            if "word/document.xml" not in names:
                raise OpportunitySourceIntakeError("unsupported_type")
            if "[Content_Types].xml" not in names:
                raise OpportunitySourceIntakeError("unsupported_type")
            content_types = _bounded_zip_read(
                archive, "[Content_Types].xml", MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES
            )
            _reject_doctype(content_types)
            if b"wordprocessingml" not in content_types.lower():
                raise OpportunitySourceIntakeError("unsupported_type")
            document_xml = _bounded_zip_read(
                archive, "word/document.xml", MAX_DOCX_ENTRY_UNCOMPRESSED_BYTES
            )
    except OpportunitySourceIntakeError:
        raise
    except zipfile.BadZipFile as error:
        raise OpportunitySourceIntakeError("corrupt") from error
    except Exception as error:
        raise OpportunitySourceIntakeError("corrupt") from error

    _reject_doctype(document_xml)

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as error:
        raise OpportunitySourceIntakeError("corrupt") from error

    body = root.find(f"{{{_WORDPROCESSINGML_NS}}}body")
    if body is None:
        raise OpportunitySourceIntakeError("corrupt")

    lines = []
    units = 0
    truncated = False
    for paragraph in body.iter(_W_P):
        if units >= MAX_EXTRACTED_TEXT_UNITS:
            truncated = True
            break
        line = _paragraph_text(paragraph)
        lines.append(line)
        units += utf16_length(line) + 1

    joined = "\n".join(lines).strip()
    if not joined:
        raise OpportunitySourceIntakeError("empty")
    text, cut = _truncate_to_units(joined, MAX_EXTRACTED_TEXT_UNITS)
    text = _reject_hostile_characters(text)
    return text, (truncated or cut)


# ---------------------------------------------------------------------------
# TXT extraction
# ---------------------------------------------------------------------------


def _extract_txt_text(data):
    if b"\x00" in data:
        raise OpportunitySourceIntakeError("unsupported_type")
    body = data
    if body.startswith(b"\xef\xbb\xbf"):
        body = body[3:]
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise OpportunitySourceIntakeError("corrupt") from error
    cleaned = text.strip()
    if not cleaned:
        raise OpportunitySourceIntakeError("empty")
    truncated_text, cut = _truncate_to_units(cleaned, MAX_EXTRACTED_TEXT_UNITS)
    truncated_text = _reject_hostile_characters(truncated_text)
    return truncated_text, cut


def extract_uploaded_document(upload):
    """Validate and extract text from a signed-in member's uploaded file.

    Returns ``(text, truncated)``. Raises :class:`OpportunitySourceIntakeError`
    for every failure reason — required, unsupported_type, too_large,
    corrupt, empty, extraction_unavailable — so the route can map every one
    of them to the single "We couldn't read this document." failure card
    (handoff section 7 / 14-M13-f) without branching member-facing copy on
    the internal reason.
    """
    validated = validate_upload(upload)
    if validated.declared_content_type == "application/pdf":
        return _extract_pdf_text(validated.data)
    if validated.declared_content_type == _DOCX_CONTENT_TYPE:
        return _extract_docx_text(validated.data)
    return _extract_txt_text(validated.data)


# ---------------------------------------------------------------------------
# Public-link import — the SSRF-guarded fetch
# ---------------------------------------------------------------------------


# RFC 7343 ORCHIDv2 (2001:20::/28) has been observed to mis-classify as
# ``ip.is_global`` True on some Python versions, with none of the named
# ``is_private``/``is_loopback``/``is_link_local``/``is_multicast``/
# ``is_reserved``/``is_unspecified`` properties catching it either —
# reproduced directly on this environment's Python (3.11.15): a
# ``2001:20::1`` address passes every one of those checks. Rather than
# special-case ORCHIDv2 alone, this excludes the whole IANA IPv6 Special-
# Purpose Address Registry "IETF Protocol Assignments" block that contains
# it (2001::/23) — none of its other sub-ranges (Teredo, benchmarking, AMT,
# AS112-v6, etc.) are addresses a public web server would legitimately hold
# either, so the wider exclusion costs nothing real.
_IETF_PROTOCOL_ASSIGNMENTS_V6 = ipaddress.ip_network("2001::/23")


def _is_public_unicast(ip):
    """``True`` only for an address a public web server could legitimately
    hold.

    Belt and suspenders, deliberately: ``ip.is_global`` is the
    IANA-special-registry-aware check (it alone correctly rejects
    Carrier-Grade NAT space, 100.64.0.0/10, which ``is_private`` does not).
    It is still not blanket-trusted here: every named exclusion in handoff
    section 11 is ALSO checked as its own named property, AND the
    ``2001::/23`` IETF-protocol-assignments block (which contains RFC 7343
    ORCHIDv2, 2001:20::/28 — verified to slip past both ``is_global`` and
    every named property on this environment's Python) is excluded
    explicitly, so no single check alone has to be perfect.
    """
    if not ip.is_global:
        return False
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip in _IETF_PROTOCOL_ASSIGNMENTS_V6
    ):
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return _is_public_unicast(mapped)
    sixtofour = getattr(ip, "sixtofour", None)
    if sixtofour is not None:
        return _is_public_unicast(sixtofour)
    teredo = getattr(ip, "teredo", None)
    if teredo is not None:
        # ``teredo`` is a (server, client) tuple of embedded IPv4 addresses.
        return all(_is_public_unicast(addr) for addr in teredo)
    return True


def _validate_import_url(url):
    if not isinstance(url, str) or not url.strip():
        raise OpportunitySourceIntakeError("required")
    candidate = url.strip()
    if len(candidate) > MAX_IMPORT_URL_LENGTH:
        raise OpportunitySourceIntakeError("too_long")
    try:
        parts = urlsplit(candidate)
        # Accessing .port explicitly triggers urllib's own numeric-port
        # validation (it raises ValueError for a non-numeric port such as
        # "https://example.com:abc/"); forcing that check here, inside the
        # try, keeps every malformed-URL shape behind one honest
        # "invalid_url" outcome instead of an uncaught exception.
        raw_port = parts.port
        hostname = parts.hostname
    except ValueError as error:
        raise OpportunitySourceIntakeError("invalid_url") from error
    if parts.scheme.lower() != "https":
        raise OpportunitySourceIntakeError("invalid_url")
    if parts.username or parts.password:
        # Userinfo in a URL is never needed for a public page and is a
        # known SSRF/URL-confusion vector (a parser and a browser can
        # disagree about which host it names).
        raise OpportunitySourceIntakeError("invalid_url")
    if not hostname:
        raise OpportunitySourceIntakeError("invalid_url")
    port = raw_port or IMPORT_ALLOWED_PORT
    if port != IMPORT_ALLOWED_PORT:
        raise OpportunitySourceIntakeError("invalid_url")
    path_qs = parts.path or "/"
    if parts.query:
        path_qs = f"{path_qs}?{parts.query}"
    return hostname, port, path_qs


def _resolve_public_ip(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError) as error:
        # OSError covers socket.gaierror (the ordinary "name does not
        # resolve" case); UnicodeError covers a hostname that fails IDNA
        # encoding. Both are an honest "we could not import that link",
        # never a raw exception reaching the route layer.
        raise OpportunitySourceIntakeError("dns_failed") from error
    if not infos:
        raise OpportunitySourceIntakeError("dns_failed")
    resolved = []
    for family, _socktype, _proto, _canon, sockaddr in infos:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        resolved.append((family, ip))
    if not resolved:
        raise OpportunitySourceIntakeError("dns_failed")
    for _family, ip in resolved:
        if not _is_public_unicast(ip):
            # Reject the whole resolution rather than merely skipping the
            # bad record: a resolver returning a mix of public and private
            # addresses for one name is itself the shape of a rebinding
            # setup, and which record gets used next is not this module's
            # to gamble on.
            raise OpportunitySourceIntakeError("private_address")
    return resolved[0]


class _DeadlineExceeded(OSError):
    """Raised by :class:`_DeadlineSSLSocket` once the shared fetch deadline
    has passed. An ``OSError`` subclass so it is caught by the same
    transport-failure handling ``guarded_fetch_html`` already applies to
    every other socket-level error — but listed ahead of the general
    ``OSError`` clause there so it maps to the honest ``"timeout"`` code,
    not the generic ``"fetch_failed"`` one.
    """


class _DeadlineSSLSocket(ssl.SSLSocket):
    """An ``ssl.SSLSocket`` whose ``recv``/``recv_into``/``read`` enforce a
    single shared deadline on every call.

    Independent review finding R2: a socket timeout set once (even
    generously) cannot bound ``http.client``'s internal ``readline()``/
    ``readinto()`` loops — each one can call the underlying ``recv``
    repeatedly, and every individual call can keep succeeding on a tiny
    amount of data forever, so the LOOP's total wall-clock time is
    unbounded even though no single ``recv`` ever times out. Measured
    directly: a header-dribbling server blocked ``getresponse()`` for
    300s+ against a supposed 10s deadline.

    The fix makes every actual socket read deadline-aware instead of
    timeout-once: immediately before delegating to the real ``recv``/
    ``recv_into``/``read``, this recomputes ``remaining = deadline - now``,
    raises :class:`_DeadlineExceeded` if it is already exhausted, and
    otherwise tightens the socket's own timeout to exactly that remaining
    amount for that one call. Installed via ``context.sslsocket_class``
    (set in :meth:`_PinnedHTTPSConnection.connect`, right after the TCP
    connect and before the TLS wrap) so the type survives ``wrap_socket()``
    — verified directly that subclassing plain ``socket.socket`` does NOT
    survive it (``wrap_socket`` constructs a fresh object of
    ``context.sslsocket_class``, discarding any unrelated subclass), and
    that ``recv``/``recv_into``/``read`` on the object ``sslsocket_class``
    produces genuinely are what ``http.client``'s status-line, header, and
    body reads all go through (confirmed with call-count instrumentation
    against a real connection).

    One honestly-documented limitation, also verified directly rather than
    assumed: the TLS **handshake** itself does not call these Python-level
    methods at all — CPython's ``_ssl`` extension drives the handshake via
    the raw socket file descriptor inside the C extension, bypassing
    Python method dispatch entirely (confirmed with the same call-count
    instrumentation: zero calls recorded during ``wrap_socket()``, several
    recorded on the very next ordinary read). The handshake is therefore
    still bounded the earlier way — the plain per-connection socket
    timeout already set via ``socket.create_connection(..., timeout=...)``
    before ``wrap_socket()`` runs — which is adequate for a handshake's
    fixed, short message exchange; this wrapper is what makes the
    variable-length, attacker-shaped status-line/header/body phases safe.
    """

    _os6_deadline = None

    def _os6_arm(self):
        if self._os6_deadline is None:
            return
        remaining = self._os6_deadline - time.monotonic()
        if remaining <= 0:
            raise _DeadlineExceeded("the import fetch deadline was exceeded")
        self.settimeout(remaining)

    def recv(self, *args, **kwargs):
        self._os6_arm()
        return super().recv(*args, **kwargs)

    def recv_into(self, *args, **kwargs):
        self._os6_arm()
        return super().recv_into(*args, **kwargs)

    def read(self, *args, **kwargs):
        self._os6_arm()
        return super().read(*args, **kwargs)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """An ``HTTPSConnection`` whose TCP connect target and TLS/Host identity
    are deliberately different values.

    ``self.host`` (set by the base class) stays the ORIGINAL hostname, so
    ``putrequest`` sends the correct ``Host`` header and certificate
    validation checks the correct name. ``connect()`` is overridden to open
    the socket against the already-validated, already-pinned numeric
    address instead of re-resolving ``self.host`` — the resolve-then-connect
    gap a DNS-rebinding attack needs never exists.
    """

    def __init__(self, pinned_ip, hostname, port, timeout, ssl_context=None, deadline=None):
        super().__init__(hostname, port, timeout=timeout)
        self._pinned_ip = pinned_ip
        # Test seam ONLY. Production code never passes this — every caller
        # in this module leaves it ``None`` and gets a real
        # ``ssl.create_default_context()`` (full certificate + hostname
        # verification). The integration test module
        # (tests/test_opportunity_slate_intake_tls.py) is the only caller
        # that supplies a context, and it does so to add a throwaway
        # self-signed test CA to an otherwise-default context — it never
        # disables verification. Reviewed here because a test seam next to
        # a security-critical connect() is exactly where a shortcut could
        # hide; there is none.
        self._ssl_context = ssl_context
        # The shared, absolute (time.monotonic()-based) deadline for the
        # WHOLE fetch (all hops combined), armed onto the resulting socket
        # once the handshake completes — see _DeadlineSSLSocket.
        self._deadline = deadline

    def connect(self):
        sock = socket.create_connection(
            (self._pinned_ip, self.port), timeout=self.timeout
        )
        context = self._ssl_context or ssl.create_default_context()
        # Idempotent: always the same class, safe to set on a context this
        # call created fresh or on a shared test context reused across
        # calls.
        context.sslsocket_class = _DeadlineSSLSocket
        self.sock = context.wrap_socket(sock, server_hostname=self.host)
        self.sock._os6_deadline = self._deadline


@dataclass(frozen=True)
class FetchedPage:
    data: bytes
    content_type: str | None
    final_url: str


def guarded_fetch_html(url, *, ssl_context=None):
    """Fetch ``url`` under the full section 11 SSRF contract and return the
    raw response bytes, bounded by size and total time, with every redirect
    hop independently re-validated and re-pinned.

    This is the ONLY function in the codebase that may open a network
    connection to a member-supplied URL. It never falls back to an
    unguarded request on any failure.

    ``ssl_context`` is a test seam ONLY (see :class:`_PinnedHTTPSConnection`)
    — production code (``extract_imported_link``) never passes it.

    Independent-review finding R2 (and, as a consequence, F1/F2's original
    fix): the deadline that bounds this whole fetch is armed onto the
    connection's socket once, right after the TLS handshake completes (see
    :class:`_DeadlineSSLSocket`), and every actual socket read — status
    line, every header line, and every body chunk alike — is deadline-aware
    from that point on. This function therefore does not set or re-arm any
    socket timeout itself; the wrapper is the single, load-bearing bound,
    which is also what makes the body-read loop below simple: no manual
    ``settimeout()`` call is ever made against a connection that may
    already be closed (independent review finding F1's original, narrower
    fix — capturing the socket reference before ``getresponse()`` — is
    superseded by this: there is no reference to capture or re-arm
    anymore, so a ``Connection: close`` response with a ``Content-Length``
    that fully closes the connection the moment the last body byte is read
    has nothing left in this function to crash on).

    ``response.read1(n)`` (rather than ``response.read(n)``) is still used
    for the body: it issues at most one underlying raw read per call
    (verified correct for both a ``Content-Length`` body and a
    chunked-encoded one), so the wrapper's per-call deadline check actually
    runs once per real network operation, not once per however many
    internal reads a buffered ``read(n)`` might silently perform to fill a
    requested size.
    """
    deadline = time.monotonic() + IMPORT_TOTAL_TIMEOUT_SECONDS
    current_url = url
    for hop in range(MAX_IMPORT_REDIRECTS + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OpportunitySourceIntakeError("timeout")
        hostname, port, path_qs = _validate_import_url(current_url)
        _family, ip = _resolve_public_ip(hostname)
        connect_timeout = max(0.1, min(IMPORT_CONNECT_TIMEOUT_SECONDS, remaining))
        connection = _PinnedHTTPSConnection(
            str(ip), hostname, port,
            timeout=connect_timeout, ssl_context=ssl_context, deadline=deadline,
        )
        try:
            connection.connect()
            connection.putrequest("GET", path_qs, skip_host=True, skip_accept_encoding=True)
            connection.putheader("Host", hostname)
            connection.putheader("User-Agent", _IMPORT_USER_AGENT)
            connection.putheader("Accept", "text/html,text/plain;q=0.8,*/*;q=0.1")
            # Refusing any transport compression keeps the bytes this
            # function hands onward exactly what the wire sent — a gzipped
            # body would otherwise decode to mojibake wherever this text is
            # later treated as UTF-8/plain text (independent review).
            connection.putheader("Accept-Encoding", "identity")
            connection.putheader("Connection", "close")
            connection.endheaders()
            # getresponse() reads the status line and every header via the
            # armed socket above — its internal readline() loops (finding R2:
            # unbounded by any per-recv timeout on their own) are bounded by
            # _DeadlineSSLSocket on every individual call they make.
            response = connection.getresponse()

            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location or hop >= MAX_IMPORT_REDIRECTS:
                    raise OpportunitySourceIntakeError("redirect_blocked")
                current_url = urljoin(current_url, location)
                continue

            if response.status != 200:
                raise OpportunitySourceIntakeError("fetch_failed")

            content_encoding = response.getheader("Content-Encoding")
            if content_encoding and content_encoding.strip().lower() not in (
                "identity",
                "",
            ):
                # A server that ignored "Accept-Encoding: identity" anyway.
                # Decoding compressed transport content is out of scope —
                # refuse rather than hand compressed bytes to a text
                # extractor that would silently mangle them.
                raise OpportunitySourceIntakeError("unsupported_content_type")

            content_type = response.getheader("Content-Type")
            # An absent Content-Type is refused rather than assumed-text:
            # the extraction contract is "HTML-to-text only", and a server
            # that will not say what it sent gets no benefit of the doubt
            # (independent review — a missing header previously sailed
            # through the "no header -> skip the check" branch).
            if not content_type or not content_type.split(";", 1)[0].strip().lower().startswith(
                "text/"
            ):
                raise OpportunitySourceIntakeError("unsupported_content_type")

            declared_length = response.getheader("Content-Length")
            if declared_length is not None:
                try:
                    if int(declared_length) > MAX_IMPORT_RESPONSE_BYTES:
                        raise OpportunitySourceIntakeError("response_too_large")
                except ValueError:
                    pass

            # No manual deadline bookkeeping here: every real read1() call
            # below goes through the armed _DeadlineSSLSocket, which raises
            # _DeadlineExceeded the moment the shared deadline passes. The
            # size cap is the only thing this loop still enforces itself.
            body = bytearray()
            while True:
                chunk = response.read1(IMPORT_READ_CHUNK_BYTES)
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > MAX_IMPORT_RESPONSE_BYTES:
                    raise OpportunitySourceIntakeError("response_too_large")
            return FetchedPage(
                data=bytes(body), content_type=content_type, final_url=current_url
            )
        except OpportunitySourceIntakeError:
            raise
        except _DeadlineExceeded as error:
            raise OpportunitySourceIntakeError("timeout") from error
        except (TimeoutError, socket.timeout) as error:
            raise OpportunitySourceIntakeError("timeout") from error
        except (OSError, ssl.SSLError, http.client.HTTPException, AttributeError) as error:
            # AttributeError is defence in depth against any future stale/
            # None socket reference in this block becoming a raw 500
            # instead of an honest fetch failure.
            raise OpportunitySourceIntakeError("fetch_failed") from error
        finally:
            connection.close()

    raise OpportunitySourceIntakeError("redirect_blocked")


# ---------------------------------------------------------------------------
# HTML-to-text extraction — a pure tokenizer, no script/style evaluation, no
# sub-fetch of any referenced asset.
# ---------------------------------------------------------------------------
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "head", "iframe", "object", "embed"})
_BLOCK_TAGS = frozenset(
    {
        "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
        "section", "article", "header", "footer",
    }
)


class _VisibleTextExtractor(HTMLParser):
    def __init__(self, max_units):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks = []
        self._units = 0
        self._max_units = max_units
        self.truncated = False

    def _append(self, text):
        if not text or self._units >= self._max_units:
            if text:
                self.truncated = True
            return
        piece, cut = _truncate_to_units(text, self._max_units - self._units)
        if piece:
            self._chunks.append(piece)
            self._units += utf16_length(piece)
        if cut:
            self.truncated = True

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        self._append(data)

    def text(self):
        joined = "".join(self._chunks)
        # Collapse the run of literal whitespace inside one text node
        # (tabs/newlines from the source markup) without touching wording.
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n[ \t]*\n[ \t]*(\n[ \t]*)+", "\n\n", joined)
        return joined.strip()


def html_to_text(html_bytes, max_units=MAX_EXTRACTED_TEXT_UNITS):
    try:
        decoded = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded = html_bytes.decode("utf-8", errors="replace")
    parser = _VisibleTextExtractor(max_units)
    try:
        parser.feed(decoded)
        parser.close()
    except Exception as error:
        raise OpportunitySourceIntakeError("corrupt") from error
    text = parser.text()
    if not text:
        raise OpportunitySourceIntakeError("empty")
    text = _reject_hostile_characters(text)
    return text, parser.truncated


def extract_imported_link(url):
    """Fetch and extract the visible text of a public page.

    Returns ``(text, truncated, final_url)``. Every failure — bad scheme,
    private address, redirect loop, oversize, timeout, unreadable markup —
    raises :class:`OpportunitySourceIntakeError`, and the route maps every
    one of them to the single "Nothing was saved or analyzed." import
    failure card (handoff section 7), never a reason-specific message that
    would help calibrate a probe against the guard.
    """
    page = guarded_fetch_html(url)
    text, truncated = html_to_text(page.data)
    return text, truncated, page.final_url
