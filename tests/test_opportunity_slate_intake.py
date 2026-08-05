"""Document upload and public-link import contract tests — PS-OPPSLATE-001,
slice OS-6.

This is the Protected-risk slice: parsing untrusted files and making an
outbound fetch on a member's behalf (SSRF). Coverage here is deliberately
adversarial rather than merely functional:

* declared-type spoofing (a PDF/DOCX/TXT declaration paired with ELF, ZIP,
  EXE, or HTML magic bytes) is rejected before any parser sees the bytes;
* an oversize upload body is rejected by the bounded MAX+1 read, never
  buffered in full;
* a corrupt PDF, a corrupt/mistyped DOCX (including an XML-entity-expansion
  attempt), and invalid-UTF-8 TXT are all rejected as unreadable, never
  partially extracted;
* extraction that exceeds the storable cap truncates cleanly and reports the
  fact, rather than silently losing text or hard-failing;
* the SSRF guard: non-https scheme, a private/loopback/link-local/metadata
  IP literal, a hostname that resolves to a private address, a redirect
  onto a private address, more than three redirects, an oversize response,
  and a slow response are all refused — every one of them mocked, per this
  slice's own instruction not to make a live network call from tests;
* both new routes are signed-in only (neutral 404 signed out, matching every
  other owner-only route in this room);
* both new routes are registered in app.py's rate-limit table (the
  enumeration guard walks the blueprint's real POST routes, so a future
  unregistered route fails this test even before app.py's hardcoded tuple
  would need updating);
* no failure path — upload or import — ever calls
  ``opportunity_slate_service.save_source_for_owner``, so no partial source
  can ever be persisted;
* ``GET .../source/original`` is deliberately NOT implemented in this slice
  (documented, not silently dropped) — see
  ``OriginalRouteDeliberatelyUnimplementedTests`` for why.

Everything below is mocked at the network/filesystem boundary the security
contract itself names: DNS resolution, the pinned HTTPS connection, and the
database service. No test in this file opens a real socket.
"""

import io
import ipaddress
import re
import struct
import time
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import app, limiter
from services.database_service import DatabaseServiceError
from services.opportunity_slate_service import OpportunitySlateServiceError
import services.opportunity_source_intake_service as intake
from services.opportunity_source_intake_service import (
    MAX_EXTRACTED_TEXT_UNITS,
    MAX_UPLOAD_BYTES,
    OpportunitySourceIntakeError,
    extract_imported_link,
    extract_uploaded_document,
    guarded_fetch_html,
    html_to_text,
    utf16_length,
    validate_upload,
)


SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}
UPLOAD_PATH = "/opportunity-slate/source/upload"
IMPORT_PATH = "/opportunity-slate/source/import"

_DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_CONTENT_TYPES_XML = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    b'<Override PartName="/word/document.xml" '
    b'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml'
    b'.document.main+xml"/></Types>'
)

_WORDPROCESSINGML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_bytes(paragraphs):
    body = "".join(
        f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>' for text in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_WORDPROCESSINGML_NS}"><w:body>{body}</w:body>'
        "</w:document>"
    ).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        archive.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def _lying_header_docx(*, member, real_uncompressed_size, declared_uncompressed_size):
    """Build a real DOCX-shaped zip whose ``member`` entry decompresses to
    ``real_uncompressed_size`` genuine zero bytes, then patches BOTH the
    local file header and the central directory record's 4-byte
    uncompressed-size field (raw zip format, RFC — offset 22 in a local
    header, offset 24 in a central directory record, both little-endian
    ``uint32``) to declare ``declared_uncompressed_size`` instead.

    The compressed data stream itself, and ``compress_size`` (the field
    the read actually depends on to locate the compressed bytes) are left
    completely untouched — only the numbers this module's PRE-FILTER
    trusts are forged, exactly modelling the reviewer's "lying header"
    archive. Zero bytes are used for the real payload because they are
    trivially, extremely compressible, so the on-disk archive stays small
    even at multi-megabyte real sizes (matching the reviewer's own
    "299KB archive" shape).
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        if member != "word/document.xml":
            archive.writestr("word/document.xml", b"<x/>")
        archive.writestr(member, b"\x00" * real_uncompressed_size)
    data = bytearray(buf.getvalue())

    name_bytes = member.encode("utf-8")
    declared = struct.pack("<I", declared_uncompressed_size)

    # Local file header: signature PK\x03\x04, filename length at +26:28,
    # uncompressed size at +22:26.
    local_sig = b"PK\x03\x04"
    search_from = 0
    patched_local = False
    while True:
        idx = data.find(local_sig, search_from)
        if idx == -1:
            break
        name_len = struct.unpack_from("<H", data, idx + 26)[0]
        candidate = bytes(data[idx + 30 : idx + 30 + name_len])
        if candidate == name_bytes:
            data[idx + 22 : idx + 26] = declared
            patched_local = True
            break
        search_from = idx + 4
    assert patched_local, "test setup: could not find the local file header"

    # Central directory record: signature PK\x01\x02, filename length at
    # +28:30, uncompressed size at +24:28, filename starts at +46.
    central_sig = b"PK\x01\x02"
    search_from = 0
    patched_central = False
    while True:
        idx = data.find(central_sig, search_from)
        if idx == -1:
            break
        name_len = struct.unpack_from("<H", data, idx + 28)[0]
        candidate = bytes(data[idx + 46 : idx + 46 + name_len])
        if candidate == name_bytes:
            data[idx + 24 : idx + 28] = declared
            patched_central = True
            break
        search_from = idx + 4
    assert patched_central, "test setup: could not find the central directory record"

    return bytes(data)


def _pdf_bytes(text="Employer role text sample."):
    content = f"BT /F1 24 Tf 72 712 Td ({text}) Tj ET".encode("latin-1")
    objs = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj",
        b"4 0 obj<</Length " + str(len(content)).encode() + b">>stream\n"
        + content + b"\nendstream endobj",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out += obj + b"\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n"
        "%%EOF"
    ).encode()
    return bytes(out)


def _pdf_bomb_bytes(decoded_content_bytes, *, text_operators=True):
    """A single-page PDF whose content stream is genuinely, honestly
    FlateDecode-compressed (no lying central-directory-style header tricks
    needed here — DEFLATE's own compression ratio on repetitive PDF
    operator text is sufficient) and decodes to roughly
    ``decoded_content_bytes`` bytes.

    ``text_operators=True`` repeats a real ``Tj`` text-showing operator
    (the shape that actually stresses pypdf's tokenizer, per independent
    review F4 — a repeated non-text operator was tried first during this
    fix's own investigation and returned near-instantly, so this is
    deliberately the operator shape that reproduces the measured cost).
    """
    import zlib

    unit = b"BT /F1 12 Tf 10 10 Td (word) Tj ET\n" if text_operators else b"0 0 0 rg 1 1 1 1 re f\n"
    repeats = max(1, decoded_content_bytes // len(unit))
    raw_content = unit * repeats
    compressed = zlib.compress(raw_content, 6)
    objs = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj",
        b"4 0 obj<</Length " + str(len(compressed)).encode()
        + b"/Filter/FlateDecode>>stream\n" + compressed + b"\nendstream endobj",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out += obj + b"\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n"
        "%%EOF"
    ).encode()
    return bytes(out)


class FakeUpload:
    """Mirrors werkzeug's FileStorage just enough for validate_upload."""

    def __init__(self, data, mimetype):
        self.stream = io.BytesIO(data)
        self.mimetype = mimetype


# ---------------------------------------------------------------------------
# Declared-type spoofing / magic-byte verification
# ---------------------------------------------------------------------------


class UploadMimeSpoofTests(unittest.TestCase):
    def test_declared_pdf_with_elf_bytes_is_rejected(self):
        upload = FakeUpload(b"\x7fELF" + b"\x00" * 64, "application/pdf")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_pdf_with_zip_bytes_is_rejected(self):
        upload = FakeUpload(b"PK\x03\x04" + b"\x00" * 64, "application/pdf")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_pdf_with_html_bytes_is_rejected(self):
        upload = FakeUpload(
            b"<!DOCTYPE html><html><body>hi</body></html>", "application/pdf"
        )
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_docx_with_pdf_bytes_is_rejected(self):
        upload = FakeUpload(_pdf_bytes(), _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_docx_with_exe_bytes_is_rejected(self):
        upload = FakeUpload(b"MZ" + b"\x90" * 64, _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_txt_with_html_bytes_is_rejected(self):
        upload = FakeUpload(
            b"<!DOCTYPE html><html><body>hi</body></html>", "text/plain"
        )
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_txt_with_pdf_bytes_is_rejected(self):
        upload = FakeUpload(_pdf_bytes(), "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_declared_txt_with_zip_bytes_is_rejected(self):
        upload = FakeUpload(b"PK\x03\x04" + b"\x00" * 64, "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_an_undeclared_content_type_is_rejected_before_any_read(self):
        upload = FakeUpload(_pdf_bytes(), "application/octet-stream")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            validate_upload(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_a_genuine_pdf_is_accepted(self):
        upload = FakeUpload(_pdf_bytes(), "application/pdf")
        text, truncated = extract_uploaded_document(upload)
        self.assertIn("Employer role text sample.", text)
        self.assertFalse(truncated)

    def test_a_genuine_docx_is_accepted(self):
        upload = FakeUpload(_docx_bytes(["Hello employer wording."]), _DOCX_TYPE)
        text, truncated = extract_uploaded_document(upload)
        self.assertEqual(text, "Hello employer wording.")
        self.assertFalse(truncated)

    def test_a_genuine_txt_is_accepted(self):
        upload = FakeUpload(b"Plain role description text.", "text/plain")
        text, truncated = extract_uploaded_document(upload)
        self.assertEqual(text, "Plain role description text.")
        self.assertFalse(truncated)


# ---------------------------------------------------------------------------
# Bounded read / oversize body
# ---------------------------------------------------------------------------


class UploadSizeTests(unittest.TestCase):
    def test_an_oversize_body_is_rejected_by_the_bounded_read(self):
        upload = FakeUpload(b"A" * (MAX_UPLOAD_BYTES + 1), "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "too_large")

    def test_the_bounded_read_never_buffers_more_than_one_byte_past_the_cap(self):
        """MAX + 1 idiom: the stream is asked for exactly one byte more than
        the cap, never the whole (potentially enormous) body."""
        upload = FakeUpload(b"A" * (MAX_UPLOAD_BYTES + 1), "text/plain")
        upload.stream = MagicMock(wraps=upload.stream)
        with self.assertRaises(OpportunitySourceIntakeError):
            validate_upload(upload)
        upload.stream.read.assert_called_once_with(MAX_UPLOAD_BYTES + 1)

    def test_an_exactly_at_cap_body_is_accepted(self):
        upload = FakeUpload(b"A" * MAX_UPLOAD_BYTES, "text/plain")
        validated = validate_upload(upload)
        self.assertEqual(validated.byte_length, MAX_UPLOAD_BYTES)

    def test_an_empty_upload_is_required_not_corrupt(self):
        upload = FakeUpload(b"", "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "required")

    def test_no_file_at_all_is_required(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(None)
        self.assertEqual(error.exception.code, "required")


# ---------------------------------------------------------------------------
# Corrupt / unreadable documents
# ---------------------------------------------------------------------------


class CorruptDocumentTests(unittest.TestCase):
    def test_a_truncated_pdf_is_unreadable(self):
        upload = FakeUpload(b"%PDF-1.4\ngarbage garbage garbage" + b"X" * 100, "application/pdf")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "corrupt")

    def test_a_zero_page_pdf_is_unreadable(self):
        pdf = _pdf_bytes()
        # A minimal, still-parseable PDF with zero pages is contrived to
        # build directly; instead assert on the guard via a monkeypatched
        # reader whose .pages is empty, which is the documented behavior.
        upload = FakeUpload(pdf, "application/pdf")
        with patch("pypdf.PdfReader") as reader_cls:
            reader = MagicMock()
            reader.is_encrypted = False
            reader.pages = []
            reader_cls.return_value = reader
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "corrupt")

    def test_a_non_zip_docx_is_unreadable(self):
        upload = FakeUpload(b"PK\x03\x04" + b"not a real zip" * 4, _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "corrupt")

    def test_a_zip_missing_document_xml_is_unsupported(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
            archive.writestr("word/other.xml", b"<x/>")
        upload = FakeUpload(buf.getvalue(), _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_a_docx_missing_content_types_is_unsupported(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("word/document.xml", b"<x/>")
        upload = FakeUpload(buf.getvalue(), _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_a_non_wordprocessingml_zip_spoofed_as_docx_is_unsupported(self):
        """An .xlsx (or any other OOXML package) renamed to .docx: the zip
        signature and even a plausible word/document.xml path can be faked,
        but [Content_Types].xml naming a non-wordprocessingml part cannot be
        satisfied by accident."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr(
                "[Content_Types].xml",
                b'<?xml version="1.0"?><Types xmlns="x"><Override '
                b'PartName="/word/document.xml" '
                b'ContentType="application/vnd.openxmlformats-officedocument'
                b'.spreadsheetml.sheet.main+xml"/></Types>',
            )
            archive.writestr("word/document.xml", b"<not-word-xml/>")
        upload = FakeUpload(buf.getvalue(), _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_a_docx_entity_expansion_attempt_is_rejected_before_parsing(self):
        """XXE / billion-laughs defence: a document.xml carrying a DOCTYPE
        is refused outright — a real Word document never has one — so
        xml.etree never sees the entity declaration at all."""
        malicious_document_xml = (
            '<?xml version="1.0"?><!DOCTYPE w:document [<!ENTITY lol "lol">]>'
            f'<w:document xmlns:w="{_WORDPROCESSINGML_NS}"><w:body><w:p><w:r>'
            "<w:t>&lol;</w:t></w:r></w:p></w:body></w:document>"
        ).encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
            archive.writestr("word/document.xml", malicious_document_xml)
        upload = FakeUpload(buf.getvalue(), _DOCX_TYPE)
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "corrupt")

    def test_a_docx_zip_bomb_style_entry_is_rejected_before_decompression(self):
        """Independent review F3/F5: replaces the earlier version of this
        test, which only asserted a declared-size field was non-zero and
        never actually forged a lying header — so it proved nothing about
        the vulnerability it was named for. This one builds a REAL lying
        central directory: the declared (central-directory) uncompressed
        size is patched to a small, innocent-looking value while the
        compressed data is left untouched and genuinely decompresses to far
        more than that (real payload is 8MB of zeros; declared size is 64
        bytes) — the exact shape the reviewer measured (a small archive
        with a lying header that a declared-size-only guard accepts).

        Investigating this construction empirically (documented here rather
        than left implicit, since it changes what this test can honestly
        claim) surfaced that CPython's own ``zipfile.ZipExtFile`` ALSO uses
        the central directory's declared ``file_size`` as its own internal
        output-truncation bound (``self._left = zipinfo.file_size``,
        ``zipfile.py``), and raises ``BadZipFile("Bad CRC-32 ...")`` once
        truncated output stops matching the (honest, untouched) stored
        CRC-32 — meaning a pure "shrink the declared size" lie is ALSO
        caught by the stdlib itself for this exact archive shape, before
        this module's own bound even has to act. That is a real, verified
        finding, not an assumption, and it does not weaken the case for
        :func:`_bounded_zip_read`: this module must not depend on an
        interpreter implementation detail as its safety boundary either
        (a ``ZIP_STORED`` entry, a future Python version, or a different
        zip-reading library would not necessarily share it). The
        observable, tool-independent property this test actually asserts
        is the one that matters regardless of WHICH safe mechanism fires:
        no more than ``limit + 1`` real bytes are ever produced, and the
        refusal happens fast — never anything resembling the reviewer's
        301MB/79s measurement.
        """
        real_uncompressed_size = 8 * 1024 * 1024  # 8MB of real zeros
        data = _lying_header_docx(
            member="word/document.xml",
            real_uncompressed_size=real_uncompressed_size,
            declared_uncompressed_size=64,
        )
        # The lie fooled the declared-size PRE-FILTER: infolist() reports
        # the small forged size, and the compression-ratio heuristic sees
        # nothing alarming (64 declared bytes over a genuinely small
        # compressed size looks like ordinary text, not a bomb) — proving
        # the pre-filter alone is not a safety boundary.
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")
            self.assertEqual(info.file_size, 64, "the forged header did not take")
            self.assertLess(
                info.file_size / max(info.compress_size, 1),
                intake.MAX_DOCX_ENTRY_COMPRESSION_RATIO,
                "the declared-size ratio guard alone would have missed this",
            )

        limit = 1024
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            start = time.monotonic()
            try:
                result = intake._bounded_zip_read(archive, "word/document.xml", limit)
                observed_bytes = len(result)
                error_code = None
            except OpportunitySourceIntakeError as error:
                observed_bytes = 0
                error_code = error.code
            except zipfile.BadZipFile:
                # zipfile's own CRC safety net (documented above) — also a
                # safe, bounded, non-amplifying outcome for this archive.
                observed_bytes = 0
                error_code = "stdlib-crc-guard"
            elapsed = time.monotonic() - start

        self.assertIsNotNone(error_code, "a lying-header archive must never be accepted")
        self.assertLessEqual(observed_bytes, limit + 1)
        self.assertLess(
            elapsed, 5.0, "must not spend real time decompressing the 8MB payload"
        )

    def test_bounded_zip_read_never_returns_more_than_the_limit_plus_one(self):
        """Direct unit proof of the F3 mechanism, independent of the DOCX
        pipeline around it: a genuine zip bomb (2MB on disk declaring —
        truthfully, this time — a 2GB member) is read through
        ``_bounded_zip_read`` and the returned bytes are asserted to never
        exceed ``limit + 1``, no matter how large the archive claims (or
        actually contains)."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("bomb.bin", b"\x00" * (200 * 1024 * 1024))
        data = buf.getvalue()
        self.assertLess(len(data), 300 * 1024, "test setup: bomb should compress tiny")

        limit = 1024
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("bomb.bin")
            self.assertGreater(info.file_size, limit * 100)  # the honest declared size
            start = time.monotonic()
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                intake._bounded_zip_read(archive, "bomb.bin", limit)
            elapsed = time.monotonic() - start
        self.assertEqual(error.exception.code, "too_large")
        self.assertLess(elapsed, 2.0, "must not decompress the full bomb to detect it")

    def test_bounded_zip_read_never_issues_an_unbounded_read_call(self):
        """Independent review finding N2: the timing bound above
        (``elapsed < 2.0``) sits inside measurement noise — the reviewer
        measured an ``archive.read(name)`` (unbounded) mutant of
        ``_bounded_zip_read`` completing in 1.978s on their hardware, which
        would pass that assertion despite being the exact regression the
        test exists to catch. A wall-clock bound can never be tightened
        enough to be reliable across machines and load; this test instead
        instruments the real call boundary directly, so the mutation is
        caught by what happened, not by how long it took.

        ``_bounded_zip_read`` must call ``ZipExtFile.read`` with a small,
        finite ``n`` (``limit + 1``) — never with ``None``, ``-1``, or no
        argument at all (all three mean "decompress everything" to
        ``zipfile``). This wraps the real method to record every ``n`` it
        was called with, so an ``archive.read(name)``-style regression
        (which passes no bound) fails this assertion regardless of how
        fast the underlying decompression happens to run on this machine.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("bomb.bin", b"\x00" * (200 * 1024 * 1024))
        data = buf.getvalue()

        limit = 1024
        real_read = zipfile.ZipExtFile.read
        recorded_n = []

        def spying_read(self, n=-1):
            recorded_n.append(n)
            return real_read(self, n)

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            with patch.object(zipfile.ZipExtFile, "read", spying_read):
                with self.assertRaises(OpportunitySourceIntakeError) as error:
                    intake._bounded_zip_read(archive, "bomb.bin", limit)

        self.assertEqual(error.exception.code, "too_large")
        self.assertTrue(recorded_n, "the spy never observed a ZipExtFile.read call")
        for n in recorded_n:
            self.assertIsNotNone(
                n, "ZipExtFile.read(None) decompresses the entire member — unbounded"
            )
            self.assertNotEqual(
                n, -1, "ZipExtFile.read(-1) decompresses the entire member — unbounded"
            )
            self.assertLessEqual(
                n,
                limit + 1,
                f"ZipExtFile.read({n}) is not bounded by the caller's limit ({limit})",
            )

    def test_invalid_utf8_txt_is_unreadable(self):
        # No NUL byte here on purpose — that is its own, earlier
        # "unsupported_type" (binary) guard, exercised separately below.
        # \x80\x81 alone is a lone UTF-8 continuation byte sequence with no
        # valid lead byte: invalid UTF-8, not a null-byte binary signal.
        upload = FakeUpload(b"not valid utf-8 \x80\x81 more text", "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "corrupt")

    def test_a_null_byte_txt_is_rejected_as_binary(self):
        upload = FakeUpload(b"role text\x00hidden", "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "unsupported_type")

    def test_whitespace_only_content_is_empty_not_a_silent_success(self):
        upload = FakeUpload(b"   \n\n   ", "text/plain")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "empty")


# ---------------------------------------------------------------------------
# F4 — PDF extraction time/memory bound
# ---------------------------------------------------------------------------


class PdfExtractionBoundTests(unittest.TestCase):
    """Independent review F4: a single 80KB PDF whose one page's content
    stream decoded to ~40MB burned 79s CPU and ~2GB RSS inside pypdf's own
    (unbounded) text-extraction tokenizer. No zip-bomb-style header lie is
    needed to build one — ordinary FlateDecode compression on repetitive
    operator text gives this ratio honestly, so these reproductions do not
    forge any metadata."""

    def test_a_small_on_disk_pdf_with_a_huge_decoded_content_stream_is_refused_fast(self):
        """Direct reproduction of the reviewer's measurement: builds an
        on-disk file of well under 200KB whose single page decodes to
        roughly 40MB of real (non-forged) content, and asserts refusal
        completes in a small bounded time — nothing resembling 79s."""
        data = _pdf_bomb_bytes(40 * 1024 * 1024)
        self.assertLess(len(data), 200 * 1024, "test setup: should compress small")
        upload = FakeUpload(data, "application/pdf")
        start = time.monotonic()
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        elapsed = time.monotonic() - start
        self.assertEqual(error.exception.code, "too_large")
        self.assertLess(elapsed, 5.0, "must not spend real time tokenizing the bomb")

    def test_the_pre_screen_checks_decoded_not_declared_size(self):
        """The dangerous case is exactly a SMALL on-disk (compressed) size
        with a huge DECODED size — proving the guard checks the real
        decoded byte count via ``_get_contents_as_bytes()``, not a
        declared/compressed-size proxy that a bomb is specifically shaped
        to be small in."""
        data = _pdf_bomb_bytes(10 * 1024 * 1024)
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        page = reader.pages[0]
        raw_ref = page.raw_get("/Contents").get_object()
        self.assertLess(
            len(raw_ref._data),
            intake.MAX_PDF_PAGE_CONTENT_BYTES,
            "test setup: the on-disk/compressed size must look small",
        )
        self.assertGreater(
            len(page._get_contents_as_bytes()),
            intake.MAX_PDF_PAGE_CONTENT_BYTES,
            "test setup: the DECODED size must exceed the cap",
        )
        upload = FakeUpload(data, "application/pdf")
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            extract_uploaded_document(upload)
        self.assertEqual(error.exception.code, "too_large")

    def test_content_just_under_the_cap_is_accepted(self):
        data = _pdf_bomb_bytes(int(intake.MAX_PDF_PAGE_CONTENT_BYTES * 0.5))
        upload = FakeUpload(data, "application/pdf")
        text, truncated = extract_uploaded_document(upload)
        self.assertIn("word", text)

    def test_decompression_alone_is_cheap_the_guard_targets_tokenization(self):
        """Documents the calibration finding this fix's bound is based on:
        decoding a huge content stream is fast; tokenizing it for text is
        what is slow. If this ever stops being true (a pypdf internals
        change), the whole design of checking decoded-length-before-
        tokenizing needs to be revisited — this test pins the assumption
        so that change would be caught here, not silently."""
        data = _pdf_bomb_bytes(20 * 1024 * 1024)
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        page = reader.pages[0]
        start = time.monotonic()
        decoded = page._get_contents_as_bytes()
        decode_elapsed = time.monotonic() - start
        self.assertGreater(len(decoded), 15 * 1024 * 1024)
        self.assertLess(decode_elapsed, 2.0, "decode itself must stay cheap")

    def test_pypdf_still_exposes_the_private_prescreen_method(self):
        """Independent review finding N3: ``_get_contents_as_bytes`` is a
        PRIVATE pypdf method (leading underscore, no compatibility
        guarantee). ``_extract_pdf_text`` already wraps the call in a
        ``try/except Exception`` that treats its disappearance as
        "too_large" (fail closed, never a silent bypass of the guard) — but
        that fail-closed behavior means a future pypdf release that
        renames or removes this method would refuse EVERY PDF upload in
        production, discovered only by a wave of user reports, not by a
        red test. This sentinel pins the assumption at the class level so
        a pypdf version bump that breaks it fails CI instead."""
        from pypdf._page import PageObject

        self.assertTrue(
            hasattr(PageObject, "_get_contents_as_bytes"),
            "pypdf's PageObject no longer exposes _get_contents_as_bytes — "
            "the F4 pre-screen in _extract_pdf_text will fail closed "
            "(refusing every PDF) until this module is updated for the "
            "new pypdf internals",
        )


# ---------------------------------------------------------------------------
# Output-cap truncation, labeled truthfully
# ---------------------------------------------------------------------------


class TruncationTests(unittest.TestCase):
    def test_a_long_txt_upload_truncates_cleanly_and_reports_it(self):
        long_text = "Employer wording. " * 3000  # far past the cap
        upload = FakeUpload(long_text.encode("utf-8"), "text/plain")
        text, truncated = extract_uploaded_document(upload)
        self.assertTrue(truncated)
        self.assertLessEqual(utf16_length(text), MAX_EXTRACTED_TEXT_UNITS)

    def test_a_long_docx_upload_truncates_cleanly_and_reports_it(self):
        paragraphs = ["Requirement number {}.".format(i) for i in range(4000)]
        upload = FakeUpload(_docx_bytes(paragraphs), _DOCX_TYPE)
        text, truncated = extract_uploaded_document(upload)
        self.assertTrue(truncated)
        self.assertLessEqual(utf16_length(text), MAX_EXTRACTED_TEXT_UNITS)

    def test_a_short_document_is_never_marked_truncated(self):
        upload = FakeUpload(b"Short role text.", "text/plain")
        _text, truncated = extract_uploaded_document(upload)
        self.assertFalse(truncated)

    def test_truncation_never_splits_a_surrogate_pair(self):
        text = "a" * 10 + "\U0001F600" + "b" * 10
        out, cut = intake._truncate_to_units(text, 11)
        self.assertTrue(cut)
        # A clean decode (no stray surrogate) proves the pair was not split.
        out.encode("utf-16-le").decode("utf-16-le")
        self.assertEqual(out, "a" * 10)

    def test_html_import_text_truncates_and_reports_it(self):
        long_html = b"<html><body>" + (b"<p>Requirement text here.</p>" * 3000) + b"</body></html>"
        text, truncated = html_to_text(long_html, max_units=200)
        self.assertTrue(truncated)
        self.assertLessEqual(utf16_length(text), 200)


# ---------------------------------------------------------------------------
# HTML-to-text extraction never executes script/style content
# ---------------------------------------------------------------------------


class HtmlExtractionTests(unittest.TestCase):
    def test_script_and_style_content_never_appears_in_extracted_text(self):
        html = (
            b"<html><head><script>alert(document.cookie)</script>"
            b"<style>.x{color:red}</style></head><body>"
            b"<h1>Senior Engineer</h1><p>We build things.</p>"
            b"<script>fetch('https://evil.example/steal')</script>"
            b"</body></html>"
        )
        text, _truncated = html_to_text(html)
        self.assertIn("Senior Engineer", text)
        self.assertIn("We build things.", text)
        self.assertNotIn("alert", text)
        self.assertNotIn("evil.example", text)
        self.assertNotIn("color:red", text)

    def test_empty_html_is_empty_not_a_silent_success(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            html_to_text(b"<html><head><script>x()</script></head><body></body></html>")
        self.assertEqual(error.exception.code, "empty")


# ---------------------------------------------------------------------------
# SSRF guard — every case mocked, no live network call
# ---------------------------------------------------------------------------


class PublicUnicastClassificationTests(unittest.TestCase):
    def _assert_public(self, literal, expected):
        ip = ipaddress.ip_address(literal)
        self.assertEqual(
            intake._is_public_unicast(ip), expected, f"{literal} misclassified"
        )

    def test_loopback_is_rejected(self):
        self._assert_public("127.0.0.1", False)
        self._assert_public("::1", False)

    def test_rfc1918_private_ranges_are_rejected(self):
        for literal in ("10.0.0.1", "172.16.0.1", "192.168.1.1"):
            self._assert_public(literal, False)

    def test_link_local_and_cloud_metadata_are_rejected(self):
        self._assert_public("169.254.169.254", False)
        self._assert_public("169.254.1.1", False)

    def test_carrier_grade_nat_is_rejected(self):
        # 100.64.0.0/10 is NOT covered by ipaddress.is_private, only by
        # is_global — regression guard for that specific gap.
        self._assert_public("100.64.0.1", False)

    def test_multicast_and_unspecified_are_rejected(self):
        self._assert_public("224.0.0.1", False)
        self._assert_public("0.0.0.0", False)
        self._assert_public("ff02::1", False)

    def test_ipv6_unique_local_is_rejected(self):
        self._assert_public("fc00::1", False)
        self._assert_public("fe80::1", False)

    def test_ipv4_mapped_ipv6_inherits_the_v4_classification(self):
        self._assert_public("::ffff:127.0.0.1", False)
        self._assert_public("::ffff:8.8.8.8", True)

    def test_ordinary_public_addresses_are_accepted(self):
        self._assert_public("8.8.8.8", True)
        self._assert_public("2001:4860:4860::8888", True)

    def test_orchidv2_and_the_wider_ietf_protocol_assignments_block_are_rejected(self):
        """Regression guard for the ORCHIDv2 residual: on this environment's
        Python, ``ipaddress`` classifies a 2001:20::/28 address as
        ``is_global`` True with none of the named properties
        (``is_private``/``is_loopback``/etc.) catching it either — the
        exact gap the guard's belt-and-suspenders design otherwise
        depends on. Also checks the wider 2001::/23 block the fix actually
        excludes, and a neighboring address just outside it that must
        still be classified purely on its own (unrelated) merits."""
        self.assertTrue(
            ipaddress.ip_address("2001:20::1").is_global,
            "test setup: this Python's ipaddress must still consider "
            "ORCHIDv2 addresses is_global for this regression test to be "
            "meaningful",
        )
        self._assert_public("2001:20::1", False)  # ORCHIDv2
        self._assert_public("2001:0:1234::1", False)  # Teredo, inside 2001::/23
        self._assert_public("2001:1ff:ffff::1", False)  # last address in 2001::/23
        # 2001:200::1 has second hextet 0x0200 — one past the /23 boundary
        # (0x0000-0x01ff) — must be classified on its own merits, not swept
        # in by an over-wide block.
        self._assert_public("2001:200::1", True)


class ImportUrlValidationTests(unittest.TestCase):
    def test_http_scheme_is_rejected(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("http://example.com/job")
        self.assertEqual(error.exception.code, "invalid_url")

    def test_non_standard_port_is_rejected(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("https://example.com:8443/job")
        self.assertEqual(error.exception.code, "invalid_url")

    def test_userinfo_in_the_url_is_rejected(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("https://user:pass@example.com/job")
        self.assertEqual(error.exception.code, "invalid_url")

    def test_a_private_ip_literal_in_the_url_passes_validation_but_fails_resolution(self):
        # The literal itself is a syntactically valid https URL; it is
        # _resolve_public_ip (exercised via guarded_fetch_html below) that
        # must catch it, because socket.getaddrinfo on a literal IP still
        # returns that same address.
        hostname, port, _path = intake._validate_import_url("https://127.0.0.1/job")
        self.assertEqual(hostname, "127.0.0.1")
        self.assertEqual(port, 443)

    def test_a_malformed_port_does_not_raise_a_bare_valueerror(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("https://example.com:notaport/job")
        self.assertEqual(error.exception.code, "invalid_url")

    def test_an_overlong_url_is_rejected(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("https://example.com/" + "a" * 3000)
        self.assertEqual(error.exception.code, "too_long")

    def test_an_empty_url_is_required(self):
        with self.assertRaises(OpportunitySourceIntakeError) as error:
            intake._validate_import_url("")
        self.assertEqual(error.exception.code, "required")


class _FakeResponse:
    def __init__(self, status, headers, body=b""):
        self.status = status
        self._headers = headers
        self._body = body
        self._pos = 0

    def getheader(self, name):
        return self._headers.get(name)

    def read(self, n):
        chunk = self._body[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    # The real fix (F1/F2) reads via response.read1(), not response.read().
    # These fakes model "here is all the available data in one call", which
    # is a valid (if simplified) read1() semantics for a canned response —
    # the byte-by-byte/one-syscall distinction that matters for the real
    # bug is exercised for real in test_opportunity_slate_intake_tls.py
    # against an actual socket, not here.
    def read1(self, n):
        return self.read(n)


class _FakeConnection:
    """Stands in for _PinnedHTTPSConnection. Subclass and override
    ``respond`` per test to control what each hop returns."""

    instances = []

    def __init__(self, ip, host, port, timeout, ssl_context=None, deadline=None):
        self.ip = ip
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ssl_context = ssl_context
        self.deadline = deadline
        self.sock = MagicMock()
        _FakeConnection.instances.append(self)

    def connect(self):
        pass

    def putrequest(self, *args, **kwargs):
        pass

    def putheader(self, *args, **kwargs):
        pass

    def endheaders(self):
        pass

    def getresponse(self):
        return self.respond()

    def respond(self):
        raise NotImplementedError

    def close(self):
        pass


class GuardedFetchSSRFTests(unittest.TestCase):
    def setUp(self):
        _FakeConnection.instances = []

    def _public_ip(self):
        return (2, ipaddress.ip_address("93.184.216.34"))

    def test_private_ip_resolution_is_refused_before_any_connection(self):
        with patch.object(
            intake,
            "_resolve_public_ip",
            side_effect=OpportunitySourceIntakeError("private_address"),
        ), patch.object(intake, "_PinnedHTTPSConnection") as conn_cls:
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://internal.example/careers")
            self.assertEqual(error.exception.code, "private_address")
            conn_cls.assert_not_called()

    def test_a_hostname_resolving_to_a_private_address_is_refused(self):
        with patch.object(intake.socket, "getaddrinfo") as getaddrinfo:
            getaddrinfo.return_value = [
                (2, 1, 6, "", ("10.0.0.5", 0)),
            ]
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://internal.example/careers")
        self.assertEqual(error.exception.code, "private_address")

    def test_a_mixed_public_and_private_resolution_is_refused_entirely(self):
        """A resolver returning both a public and a private record for one
        name is itself the shape of a rebinding setup; the whole resolution
        is refused rather than gambling on which record gets used."""
        with patch.object(intake.socket, "getaddrinfo") as getaddrinfo:
            getaddrinfo.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
                (2, 1, 6, "", ("169.254.169.254", 0)),
            ]
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://mixed.example/careers")
        self.assertEqual(error.exception.code, "private_address")

    def test_dns_failure_is_refused(self):
        import socket as socket_module

        with patch.object(
            intake.socket, "getaddrinfo", side_effect=socket_module.gaierror()
        ):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://nowhere.invalid/careers")
        self.assertEqual(error.exception.code, "dns_failed")

    def test_a_redirect_to_a_private_address_is_refused(self):
        class RedirectThenPrivate(_FakeConnection):
            def respond(self):
                if self.host == "public.example":
                    return _FakeResponse(
                        302, {"Location": "https://internal.example/x"}
                    )
                raise AssertionError("must not connect past the private hop")

        def resolve(hostname):
            if hostname == "internal.example":
                raise OpportunitySourceIntakeError("private_address")
            return self._public_ip()

        with patch.object(intake, "_resolve_public_ip", side_effect=resolve), \
             patch.object(intake, "_PinnedHTTPSConnection", RedirectThenPrivate):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://public.example/start")
        self.assertEqual(error.exception.code, "private_address")

    def test_more_than_three_redirects_is_refused(self):
        class InfiniteRedirect(_FakeConnection):
            hop = 0

            def respond(self):
                InfiniteRedirect.hop += 1
                return _FakeResponse(
                    302, {"Location": f"https://hop{InfiniteRedirect.hop}.example/"}
                )

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", InfiniteRedirect):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://start.example/")
        self.assertEqual(error.exception.code, "redirect_blocked")
        # Exactly MAX_IMPORT_REDIRECTS + 1 requests were attempted: the
        # initial fetch plus three redirect hops, never a fourth.
        self.assertEqual(len(_FakeConnection.instances), intake.MAX_IMPORT_REDIRECTS + 1)

    def test_exactly_three_redirects_then_success_is_allowed(self):
        class ThreeThenOk(_FakeConnection):
            def respond(self):
                if self.host == "start.example":
                    return _FakeResponse(302, {"Location": "https://hop1.example/"})
                if self.host == "hop1.example":
                    return _FakeResponse(302, {"Location": "https://hop2.example/"})
                if self.host == "hop2.example":
                    return _FakeResponse(302, {"Location": "https://final.example/"})
                return _FakeResponse(
                    200, {"Content-Type": "text/html"}, b"<html><body>Role text here.</body></html>"
                )

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", ThreeThenOk):
            page = guarded_fetch_html("https://start.example/")
        self.assertIn(b"Role text here.", page.data)
        self.assertEqual(page.final_url, "https://final.example/")

    def test_an_oversize_declared_content_length_is_refused(self):
        class Oversize(_FakeConnection):
            def respond(self):
                return _FakeResponse(
                    200,
                    {
                        "Content-Type": "text/html",
                        "Content-Length": str(intake.MAX_IMPORT_RESPONSE_BYTES + 1),
                    },
                    b"x",
                )

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", Oversize):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://big.example/")
        self.assertEqual(error.exception.code, "response_too_large")

    def test_an_oversize_streamed_body_with_no_content_length_is_refused(self):
        class StreamedOversize(_FakeConnection):
            def respond(self):
                body = b"A" * (intake.MAX_IMPORT_RESPONSE_BYTES + 1024)
                return _FakeResponse(200, {"Content-Type": "text/html"}, body)

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", StreamedOversize):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://big.example/")
        self.assertEqual(error.exception.code, "response_too_large")

    def test_a_non_text_content_type_is_refused(self):
        class BinaryResponse(_FakeConnection):
            def respond(self):
                return _FakeResponse(200, {"Content-Type": "application/pdf"}, b"%PDF-1.4")

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", BinaryResponse):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://binary.example/")
        self.assertEqual(error.exception.code, "unsupported_content_type")

    def test_a_non_200_status_is_refused(self):
        class NotFound(_FakeConnection):
            def respond(self):
                return _FakeResponse(404, {"Content-Type": "text/html"}, b"missing")

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", NotFound):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://gone.example/")
        self.assertEqual(error.exception.code, "fetch_failed")

    def test_a_slow_multi_hop_redirect_chain_times_out_between_hops(self):
        """Independent review R2's fix moved the fine-grained, per-read
        deadline enforcement (status line / headers / body) INSIDE the
        socket layer itself (:class:`_DeadlineSSLSocket`, armed once after
        the TLS handshake) — see ``guarded_fetch_html``'s docstring. A
        ``_FakeConnection``-based unit test cannot exercise that anymore:
        it never constructs a real socket for the wrapper to enforce
        anything through. That per-read enforcement is instead proven, for
        real, against an actual local TLS server and a real socket, by
        ``test_header_dribbling_server_aborts_within_the_deadline`` and
        ``test_chunked_slowloris_aborts_within_the_deadline`` in
        ``test_opportunity_slate_intake_tls.py``.

        What DOES remain, and is still real and observable at this mock
        boundary, is the coarser BETWEEN-HOP check at the top of
        ``guarded_fetch_html``'s redirect loop (``remaining = deadline -
        time.monotonic(); if remaining <= 0: raise "timeout"``) — a chain
        of individually-fast redirects can still cumulatively exceed the
        total budget. This test exercises exactly that surviving check."""

        class SlowRedirectChain(_FakeConnection):
            def respond(self):
                if self.host == "start.example":
                    return _FakeResponse(302, {"Location": "https://hop1.example/"})
                if self.host == "hop1.example":
                    return _FakeResponse(302, {"Location": "https://hop2.example/"})
                return _FakeResponse(
                    200, {"Content-Type": "text/html"}, b"<html><body>never reached</body></html>"
                )

        class FakeClock:
            """Advances a large, fixed step on every call. Deterministic
            regardless of exactly how many times anything checks the
            deadline — a couple of hops' worth of calls exceeds the 10s
            budget, so this cannot flake on call-count details."""

            def __init__(self):
                self.now = 0.0

            def __call__(self):
                value = self.now
                self.now += 6.0
                return value

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", SlowRedirectChain), \
             patch.object(intake.time, "monotonic", FakeClock()):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://start.example/")
        self.assertEqual(error.exception.code, "timeout")
        # The chain must have been cut off partway through, not allowed to
        # exhaust MAX_IMPORT_REDIRECTS worth of hops first.
        self.assertLess(len(_FakeConnection.instances), intake.MAX_IMPORT_REDIRECTS + 1)

    def test_a_connection_reset_becomes_an_honest_fetch_failure(self):
        class Reset(_FakeConnection):
            def getresponse(self):
                raise ConnectionResetError()

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", Reset):
            with self.assertRaises(OpportunitySourceIntakeError) as error:
                guarded_fetch_html("https://flaky.example/")
        self.assertEqual(error.exception.code, "fetch_failed")

    def test_full_import_pipeline_end_to_end(self):
        class OkPage(_FakeConnection):
            def respond(self):
                return _FakeResponse(
                    200,
                    {"Content-Type": "text/html; charset=utf-8"},
                    b"<html><body><h1>Staff Engineer</h1>"
                    b"<p>5+ years experience required.</p></body></html>",
                )

        with patch.object(intake, "_resolve_public_ip", return_value=self._public_ip()), \
             patch.object(intake, "_PinnedHTTPSConnection", OkPage):
            text, truncated, final_url = extract_imported_link(
                "https://careers.example.com/roles/1"
            )
        self.assertIn("Staff Engineer", text)
        self.assertIn("5+ years experience required.", text)
        self.assertFalse(truncated)
        self.assertEqual(final_url, "https://careers.example.com/roles/1")


# ---------------------------------------------------------------------------
# Route-level boundary and no-partial-source guarantees (Flask test client)
# ---------------------------------------------------------------------------


class OppslateRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_OPPORTUNITY_SLATE_ENABLED")
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = True
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = self.original_flag

    def signed_in(self):
        return patch(
            "opportunity_slate_routes.get_optional_identity",
            return_value=SimpleNamespace(
                display_name="Test Member", user_key="member-oppslate-intake"
            ),
        )


class UploadRouteBoundaryTests(OppslateRouteTestCase):
    def test_anonymous_upload_is_a_neutral_404(self):
        with patch("opportunity_slate_routes.get_optional_identity", return_value=None):
            response = self.client.post(
                UPLOAD_PATH, headers=SAME_ORIGIN_HEADERS, data={}
            )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_import_is_a_neutral_404(self):
        with patch("opportunity_slate_routes.get_optional_identity", return_value=None):
            response = self.client.post(
                IMPORT_PATH, headers=SAME_ORIGIN_HEADERS, data={"source_url": "https://example.com/"}
            )
        self.assertEqual(response.status_code, 404)

    def test_flag_off_is_404_before_identity_resolution(self):
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        with patch("opportunity_slate_routes.get_optional_identity") as resolve:
            response = self.client.post(UPLOAD_PATH, headers=SAME_ORIGIN_HEADERS, data={})
            self.assertEqual(response.status_code, 404)
            response2 = self.client.post(
                IMPORT_PATH, headers=SAME_ORIGIN_HEADERS, data={"source_url": "https://example.com/"}
            )
            self.assertEqual(response2.status_code, 404)
        resolve.assert_not_called()

    def test_cross_site_upload_is_refused(self):
        with self.signed_in():
            response = self.client.post(UPLOAD_PATH, data={})
        self.assertEqual(response.status_code, 403)

    def test_cross_site_import_is_refused(self):
        with self.signed_in():
            response = self.client.post(
                IMPORT_PATH, data={"source_url": "https://example.com/"}
            )
        self.assertEqual(response.status_code, 403)

    def test_a_signed_out_upload_never_reaches_the_intake_service(self):
        with patch("opportunity_slate_routes.get_optional_identity", return_value=None), \
             patch("opportunity_slate_routes.extract_uploaded_document") as extract:
            self.client.post(UPLOAD_PATH, headers=SAME_ORIGIN_HEADERS, data={})
        extract.assert_not_called()

    def test_upload_success_renders_the_upload_failure_card_on_missing_file(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            response = self.client.post(UPLOAD_PATH, headers=SAME_ORIGIN_HEADERS, data={})
        self.assertEqual(response.status_code, 400)
        body = response.data.decode("utf-8")
        self.assertIn("We couldn&#39;t read this document.", body)
        self.assertIn("Nothing was saved or analyzed", body)
        service.save_source_for_owner.assert_not_called()

    def test_upload_spoofed_mime_never_reaches_save(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            data = {
                "document": (io.BytesIO(b"\x7fELF" + b"\x00" * 40), "resume.pdf", "application/pdf"),
            }
            response = self.client.post(
                UPLOAD_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data=data,
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 400)
        service.save_source_for_owner.assert_not_called()

    def test_upload_corrupt_pdf_never_reaches_save(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            data = {
                "document": (
                    io.BytesIO(b"%PDF-1.4 corrupt" + b"z" * 80),
                    "resume.pdf",
                    "application/pdf",
                ),
            }
            response = self.client.post(
                UPLOAD_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data=data,
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 400)
        body = response.data.decode("utf-8")
        self.assertIn("We couldn&#39;t read this document.", body)
        service.save_source_for_owner.assert_not_called()

    def test_upload_success_calls_save_with_capture_method_uploaded(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.save_source_for_owner.return_value = {"saved": True}
            data = {
                "document": (
                    io.BytesIO(_pdf_bytes("Full stack engineer role.")),
                    "resume.pdf",
                    "application/pdf",
                ),
            }
            response = self.client.post(
                UPLOAD_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data=data,
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/opportunity-slate")
        _args, kwargs = service.save_source_for_owner.call_args
        self.assertEqual(kwargs.get("capture_method"), "uploaded")

    def test_upload_database_failure_never_reaches_save_confirmation_and_is_truthful(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.save_source_for_owner.side_effect = DatabaseServiceError("down")
            data = {
                "document": (
                    io.BytesIO(_pdf_bytes()),
                    "resume.pdf",
                    "application/pdf",
                ),
            }
            response = self.client.post(
                UPLOAD_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data=data,
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 503)

    def test_import_success_calls_save_with_capture_method_imported(self):
        class OkPage(_FakeConnection):
            def respond(self):
                return _FakeResponse(
                    200,
                    {"Content-Type": "text/html"},
                    b"<html><body><p>Backend engineer role text.</p></body></html>",
                )

        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service, \
             patch.object(intake, "_resolve_public_ip", return_value=(2, ipaddress.ip_address("93.184.216.34"))), \
             patch.object(intake, "_PinnedHTTPSConnection", OkPage):
            service.save_source_for_owner.return_value = {"saved": True}
            response = self.client.post(
                IMPORT_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data={"source_url": "https://careers.example.com/roles/1"},
            )
        self.assertEqual(response.status_code, 302)
        _args, kwargs = service.save_source_for_owner.call_args
        self.assertEqual(kwargs.get("capture_method"), "imported")

    def test_import_http_url_never_reaches_save(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            response = self.client.post(
                IMPORT_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data={"source_url": "http://careers.example.com/roles/1"},
            )
        self.assertEqual(response.status_code, 400)
        body = response.data.decode("utf-8")
        self.assertIn("We couldn&#39;t import that link.", body)
        self.assertIn("Nothing was saved or analyzed", body)
        service.save_source_for_owner.assert_not_called()

    def test_import_private_ip_literal_never_reaches_save(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            response = self.client.post(
                IMPORT_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data={"source_url": "https://169.254.169.254/latest/meta-data/"},
            )
        self.assertEqual(response.status_code, 400)
        service.save_source_for_owner.assert_not_called()

    def test_import_hostname_resolving_private_never_reaches_save(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service, \
             patch.object(intake.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("10.1.2.3", 0))]):
            response = self.client.post(
                IMPORT_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data={"source_url": "https://internal-portal.example/roles"},
            )
        self.assertEqual(response.status_code, 400)
        service.save_source_for_owner.assert_not_called()

    def test_import_database_failure_is_truthful_and_503(self):
        class OkPage(_FakeConnection):
            def respond(self):
                return _FakeResponse(
                    200, {"Content-Type": "text/html"}, b"<html><body>Role text.</body></html>"
                )

        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service, \
             patch.object(intake, "_resolve_public_ip", return_value=(2, ipaddress.ip_address("93.184.216.34"))), \
             patch.object(intake, "_PinnedHTTPSConnection", OkPage):
            service.save_source_for_owner.side_effect = DatabaseServiceError("down")
            response = self.client.post(
                IMPORT_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data={"source_url": "https://careers.example.com/roles/1"},
            )
        self.assertEqual(response.status_code, 503)

    def test_upload_truncated_extraction_redirects_with_a_notice_and_still_saves(self):
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.save_source_for_owner.return_value = {"saved": True}
            data = {
                "document": (
                    io.BytesIO(("Employer wording. " * 3000).encode("utf-8")),
                    "resume.txt",
                    "text/plain",
                ),
            }
            response = self.client.post(
                UPLOAD_PATH,
                headers=SAME_ORIGIN_HEADERS,
                data=data,
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 302)
        location = response.headers["Location"]
        self.assertTrue(location.startswith("/opportunity-slate?notice="))
        token = location.split("notice=", 1)[1]
        import opportunity_slate_routes as routes

        with app.app_context():
            self.assertEqual(routes._read_notice_token(token), "upload_truncated")
        service.save_source_for_owner.assert_called_once()

    def test_the_truncation_notice_renders_truthfully_on_the_next_get(self):
        from services.opportunity_slate_service import WorkingSourceView
        from datetime import datetime, timedelta, timezone

        working = WorkingSourceView(
            working_session_key="11111111-1111-1111-1111-111111111111",
            session_version_token="0000000000000001",
            workbench_state="review_source",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            source_key="22222222-2222-2222-2222-222222222222",
            source_version_token="0000000000000002",
            version_number=1,
            confirmed_version_number=None,
            confirmed_at=None,
            capture_method="uploaded",
            original_text="A" * 20000,
            member_corrected_text=None,
            corrected_at=None,
            captured_at=datetime.now(timezone.utc),
        )
        import opportunity_slate_routes as routes

        with app.app_context():
            token = routes._mint_notice_token("upload_truncated")
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.get_working_session_for_owner.return_value = working
            service.get_source_review_for_owner.return_value = None
            service.purge_expired_working_data_for_owner.return_value = None
            response = self.client.get(f"/opportunity-slate?notice={token}")
        body = response.data.decode("utf-8")
        self.assertIn("longer than PeerSlate reviews", body)

    def _working_view_for_notice_test(self):
        from services.opportunity_slate_service import WorkingSourceView
        from datetime import datetime, timedelta, timezone

        return WorkingSourceView(
            working_session_key="11111111-1111-1111-1111-111111111111",
            session_version_token="0000000000000001",
            workbench_state="review_source",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            source_key="22222222-2222-2222-2222-222222222222",
            source_version_token="0000000000000002",
            version_number=1,
            confirmed_version_number=None,
            confirmed_at=None,
            capture_method="uploaded",
            original_text="A" * 20000,
            member_corrected_text=None,
            corrected_at=None,
            captured_at=datetime.now(timezone.utc),
        )

    def test_a_bare_unsigned_notice_value_is_ignored(self):
        """Independent review (non-blocking, fixed now): the notice must be
        a signed, short-lived token, not a bare replayable string — a
        bookmarked or history-replayed URL must not resurface a stale
        truncation claim."""
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.get_working_session_for_owner.return_value = self._working_view_for_notice_test()
            service.get_source_review_for_owner.return_value = None
            service.purge_expired_working_data_for_owner.return_value = None
            response = self.client.get("/opportunity-slate?notice=upload_truncated")
        body = response.data.decode("utf-8")
        self.assertNotIn("longer than PeerSlate reviews", body)

    def test_a_tampered_notice_token_is_ignored(self):
        import opportunity_slate_routes as routes

        with app.app_context():
            token = routes._mint_notice_token("upload_truncated")
        # Independent review: flipping the token's LAST character (the
        # final character of its base64url-encoded HMAC signature) is
        # unreliable, not merely probabilistic-but-fine. A base64url
        # string's final character encodes fewer than 6 REAL bits whenever
        # the digest's bit length is not a multiple of 6 (true of every
        # common hash size) — the remaining low bits are padding that
        # Python's base64 decoder silently discards rather than validates.
        # The old fallback ("A" if last != "A" else "B") stayed inside that
        # same discarded-bits equivalence class whenever the real token's
        # last character was already A/B/C/D, so the "tampered" token
        # decoded to the IDENTICAL real signature bytes and still verified
        # — a false pass, measured at ~5.9% of minted tokens, not a flake
        # in the test runner. A MIDDLE signature character always encodes
        # a full 6 real bits (the discarded-bits effect is specific to the
        # final character of the whole base64url string), so flipping one
        # there is a mathematically guaranteed byte-level change, not a
        # probabilistic one — measured 0/4000 false-passes.
        prefix, signature = token.rsplit(".", 1)
        middle = len(signature) // 2
        flipped_char = "A" if signature[middle] != "A" else "B"
        tampered_signature = signature[:middle] + flipped_char + signature[middle + 1 :]
        tampered = f"{prefix}.{tampered_signature}"
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.get_working_session_for_owner.return_value = self._working_view_for_notice_test()
            service.get_source_review_for_owner.return_value = None
            service.purge_expired_working_data_for_owner.return_value = None
            response = self.client.get(f"/opportunity-slate?notice={tampered}")
        body = response.data.decode("utf-8")
        self.assertNotIn("longer than PeerSlate reviews", body)

    def test_an_expired_notice_token_is_ignored(self):
        import opportunity_slate_routes as routes

        with app.app_context():
            token = routes._mint_notice_token("upload_truncated")
        with self.signed_in(), \
             patch("opportunity_slate_routes.opportunity_slate_service") as service, \
             patch.object(routes, "NOTICE_TOKEN_MAX_AGE_SECONDS", -1):
            service.get_working_session_for_owner.return_value = self._working_view_for_notice_test()
            service.get_source_review_for_owner.return_value = None
            service.purge_expired_working_data_for_owner.return_value = None
            response = self.client.get(f"/opportunity-slate?notice={token}")
        body = response.data.decode("utf-8")
        self.assertNotIn("longer than PeerSlate reviews", body)


# ---------------------------------------------------------------------------
# Rate-limit registration — the enumeration guard
# ---------------------------------------------------------------------------


class RateLimitEnumerationTests(unittest.TestCase):
    def test_every_post_route_on_the_blueprint_is_registered_in_app_py(self):
        """Walks the blueprint's REAL registered routes (not a hand-kept
        list), so a future POST route added to opportunity_slate_routes.py
        without a matching app.py rate-limit entry fails this test."""
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(
            encoding="utf-8"
        )
        missing = []
        for rule in app.url_map.iter_rules():
            if not rule.endpoint.startswith("opportunity_slate."):
                continue
            if "POST" not in rule.methods:
                continue
            if f"'{rule.endpoint}'" not in app_source:
                missing.append(rule.endpoint)
        self.assertEqual(missing, [], f"unregistered rate limit(s): {missing}")

    def test_upload_and_import_are_specifically_registered(self):
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("'opportunity_slate.upload_source'", app_source)
        self.assertIn("'opportunity_slate.import_source'", app_source)


# ---------------------------------------------------------------------------
# Dependency pin sanity (companion to tests/test_site_rules.py's
# DependencyPinTests, which asserts cross-file consistency; this asserts the
# pin exists at all and matches the module's documented choice).
# ---------------------------------------------------------------------------


class ExtractionDependencyTests(unittest.TestCase):
    def test_pypdf_is_pinned_in_requirements(self):
        root = Path(__file__).resolve().parents[1]
        requirements = (root / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("pypdf==", requirements)

    def test_docx_extraction_uses_only_the_standard_library(self):
        """No new dependency for DOCX: stdlib zipfile + xml.etree only,
        hardened by the DOCTYPE refusal instead of a defusedxml pin that is
        not otherwise used anywhere in this repository. The module's own
        docstring names "defusedxml" in prose to explain that choice, so
        this checks for an actual import, not the bare substring."""
        source = (
            Path(__file__).resolve().parents[1]
            / "services"
            / "opportunity_source_intake_service.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import defusedxml", source)
        self.assertNotIn("from defusedxml", source)
        requirements = (
            Path(__file__).resolve().parents[1] / "requirements.txt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("defusedxml", requirements)
        self.assertIn("import zipfile", source)
        self.assertIn("from xml.etree import ElementTree", source)


class ProductionCallerNeverPassesSslContextTests(unittest.TestCase):
    """Independent review finding N7: ``ssl_context`` on
    ``guarded_fetch_html``/``_PinnedHTTPSConnection`` is documented as a
    test-only seam (it lets tests swap in an untrusting context to prove
    verification is genuinely on, and a trusting one to talk to a
    self-signed local test server) — but a docstring promise is not a
    guarantee. If any real production caller ever passed a non-default
    ``ssl_context`` (accidentally or otherwise) it could silently weaken or
    disable certificate verification for a live member-supplied URL. This
    walks every ``.py`` file in the repository, excluding the tests
    directory and the intake service module's own definition site, and
    fails if any of them passes ``ssl_context=`` at a call site — the same
    grep-idiom guardrail style used in ``tests/test_site_rules.py``.
    """

    def test_no_production_caller_passes_ssl_context(self):
        root = Path(__file__).resolve().parents[1]
        pattern = re.compile(r"ssl_context\s*=")
        excluded_dirs = {"tests", ".git", "node_modules", "__pycache__"}
        excluded_files = {"opportunity_source_intake_service.py"}
        offenders = []
        for path in root.rglob("*.py"):
            relative_parts = path.relative_to(root).parts
            if any(part in excluded_dirs for part in relative_parts[:-1]):
                continue
            if path.name in excluded_files:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(root)}:{lineno}")
        self.assertEqual(
            offenders,
            [],
            "a production caller passes ssl_context= — this is a test-only "
            "seam and must never be used outside tests: " + ", ".join(offenders),
        )

    def test_extract_imported_link_itself_accepts_no_ssl_context_parameter(self):
        """Belt-and-suspenders: even if some future caller tried to pass
        ``ssl_context`` through the one function production code actually
        calls, it could not reach ``guarded_fetch_html`` — ``extract_imported_link``
        takes only ``url``."""
        import inspect

        signature = inspect.signature(extract_imported_link)
        self.assertEqual(list(signature.parameters), ["url"])


class BodyReadMechanismSourcePinTests(unittest.TestCase):
    def test_body_loop_reads_via_read1_not_read(self):
        """Source-pinning regression guard for the ``read1``-vs-``read``
        mutation named in review.

        This is deliberately NOT a behavioral/timing test. Empirically
        re-run during this pass: after the R2 redesign moved deadline
        enforcement down into ``_DeadlineSSLSocket`` (armed once, checked
        on every real ``recv``/``recv_into``/``read`` at the raw socket
        layer — see that class and ``guarded_fetch_html``'s docstring), a
        ``response.read1(n)`` -> ``response.read(n)`` mutation in the body
        loop was found to leave every existing behavioral test (the full
        real-TLS suite, including the slowloris and header-dribbling
        deadline tests) passing unchanged — because ``read(n)``'s internal
        multi-raw-read loop still runs through the very same wrapped
        socket, so it is still deadline-bounded either way. ``read1`` is
        still the prescribed, correct call (one real network operation per
        Python-level call, versus ``read(n)``'s internal looping to fill a
        requested size), so this pins the actual source text directly,
        rather than relying on a behavioral test that can no longer tell
        the two apart."""
        source = (
            Path(__file__).resolve().parents[1]
            / "services"
            / "opportunity_source_intake_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "response.read1(IMPORT_READ_CHUNK_BYTES)",
            source,
            "the import body-read loop must call response.read1(...), not "
            "response.read(...) — see this test's docstring for why a "
            "behavioral test can no longer catch this regression",
        )


# ---------------------------------------------------------------------------
# GET .../source/original — deliberately unimplemented in this slice
# ---------------------------------------------------------------------------


class OriginalRouteDeliberatelyUnimplementedTests(unittest.TestCase):
    """Documents, rather than silently omits, a real schema gap.

    The OS-1 migration's ``opportunity_source_versions`` table has exactly
    the columns slice OS-6's TEXT pipeline needs (``capture_method``
    already includes 'uploaded'/'imported', ``original_text``,
    ``original_sha256``) and nothing more: no column for a blob storage
    locator, no original filename, and no original source URL. The
    established pattern for retaining a private original
    (``dbo.capture_media_sources`` / PS-CAPTURE-MEDIA-001) is a dedicated
    table carrying exactly those fields, which this migration does not
    have. Adding one is a schema change — a separate Protected path, not an
    inline addition a route-and-service slice may make for itself — so
    ``GET .../source/original`` is not implemented, and no blob is written
    for an uploaded file's original bytes. This test locks that decision in
    as a visible, intentional fact rather than a route nobody remembered to
    add.
    """

    def test_the_route_does_not_exist(self):
        found = any(
            rule.rule.endswith("/source/original")
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith("opportunity_slate.")
        )
        self.assertFalse(
            found,
            "source/original exists but the schema still lacks a blob "
            "locator/filename/URL column — if this now passes, the schema "
            "gap this test documents has been closed and the test (and its "
            "docstring) should be updated or removed, not just the assertion.",
        )


if __name__ == "__main__":
    unittest.main()
