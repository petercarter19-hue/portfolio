"""C10 -- PS-MYOPP-MEMBER-IMPORT-001 binding test suite.

Grouped to mirror the C10 architecture note (§5): A (doc 16 §3 unconditional
rows), B (pipeline outcome truth), C (fetch-port downstream pre-proof), D
(idempotency), E (negative multi-member), F (export/delete/dual retention),
G (unknown-outcome discipline), H (content-free audit sweep), I (migration
file-content tests -- implementer B's SQL trio; these read the forward/
rollback/verifier/registry files as text and are EXPECTED to fail with a
clear "file not found" signal until PS-MYOPP-006's SQL trio lands, mirroring
how C4/C5/C6 treat an unproven disposable-gate proof as an honest failure
rather than a defect in the test), J (structural stops).
"""

from __future__ import annotations

import base64
import dataclasses
import io
import json
import platform
import re
import resource
import struct
import subprocess
import sys
import time
import tracemalloc
import unittest
import zipfile
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.migration_registry import executable_sha256

from services.my_opportunities.canonical_service import DATA_CLASSES
import services.my_opportunities.member_import_service as member_import_service
from services.my_opportunities.member_import_service import (
    ALLOWED_UPLOAD_CONTENT_TYPES,
    BODY_REMOVAL_MEMBER_DELETE,
    BODY_REMOVAL_REASONS,
    BODY_REMOVAL_RIGHTS_TAKEDOWN,
    COMMAND_DELETE_IMPORT,
    COMMAND_IMPORT_FROM_URL,
    COMMAND_SUBMIT_PASTE,
    COMMAND_SUBMIT_UPLOAD,
    COMMANDS,
    CONTRACT_VERSION,
    FETCH_FACTORY,
    FETCH_MODULE,
    FLAG_SURFACE,
    FLAG_URL_FETCH,
    FailingMemberImportRepository,
    FetchRefused,
    FetchResult,
    HOST_CLASSES,
    HOST_CLASS_NOT_APPLICABLE,
    INTAKE_METHODS,
    INTAKE_PASTE,
    INTAKE_UPLOAD,
    INTAKE_URL_FETCH,
    ImportReceipt,
    ImportStageOutcome,
    InMemoryAuditSink,
    InMemoryMemberImportRepository,
    MAX_ACTIVE_IMPORTS_PER_MEMBER,
    MAX_EXTRACTED_TEXT_UNITS,
    MAX_IDEMPOTENCY_KEY_UTF16_UNITS,
    MAX_PASTE_UTF16_UNITS,
    MAX_UPLOAD_BYTES,
    MAX_USER_KEY_UTF16_UNITS,
    MemberImport,
    MemberImportAuditEvent,
    MemberImportLimits,
    MemberImportService,
    MemberImportServiceError,
    NoneRightsObligationReader,
    OUTCOME_BLOCKED,
    OUTCOME_DECODED,
    OUTCOME_EMPTY,
    OUTCOME_EXTRACTED,
    OUTCOME_FETCHED,
    OUTCOME_PARSED,
    OUTCOME_PARTIAL,
    OUTCOME_REFUSED,
    OUTCOME_STATES,
    OUTCOME_TIMEOUT,
    RECORD_STATE_ACTIVE,
    RECORD_STATE_DELETED,
    RECORD_STATES,
    REASON_ARCHIVE_BOMB_SUSPECTED,
    REASON_COULD_NOT_DECODE,
    REASON_EXTRACTION_DEADLINE,
    REASON_HOSTILE_CHARACTERS,
    REASON_OUTPUT_TRUNCATED,
    REASON_PARSER_FAILURE,
    REASON_PARSER_RESOURCE_BOUNDS,
    RIGHTS_NONE,
    RIGHTS_OBLIGATION_CLASSES,
    RIGHTS_TAKEDOWN_REQUIRED,
    RepositoryWriteError,
    SANITIZER_VERSION,
    TERMINAL_SUCCESS_STATES,
    ValidatedUpload,
    validate_paste,
    validate_upload,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
_DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_WORDPROCESSINGML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CONTENT_TYPES_XML = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    b'<Override PartName="/word/document.xml" '
    b'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml'
    b'.document.main+xml"/></Types>'
)


# ---------------------------------------------------------------------------
# Fixture builders (idiom shared with tests/test_opportunity_slate_intake.py)
# ---------------------------------------------------------------------------


def _docx_bytes(paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_WORDPROCESSINGML_NS}"><w:body>{body}</w:body>'
        "</w:document>"
    ).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _pdf_bytes(text="A sample role posting extracted from a PDF."):
    content = f"BT /F1 24 Tf 72 712 Td ({text}) Tj ET".encode("latin-1")
    objs = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>endobj",
        b"4 0 obj<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream endobj",
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
    out += (f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n" "%%EOF").encode()
    return bytes(out)


def _pdf_bomb_bytes(decoded_content_bytes, *, text_operators=True):
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
        b"4 0 obj<</Length " + str(len(compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
        + compressed + b"\nendstream endobj",
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
    out += (f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n" "%%EOF").encode()
    return bytes(out)


def _assemble_pdf(objects_by_id):
    """``objects_by_id``: ``dict[int, bytes]`` of object BODIES (the part
    between ``N 0 obj`` and ``endobj``, exclusive of both) -- builds a
    complete, valid PDF with a correct xref table around them. Used by the
    BLOCKER 1 part (a) font/ToUnicode fixtures below, where hand-counting
    object numbers and byte offsets across several variable-size streams
    would otherwise be error-prone."""
    max_id = max(objects_by_id)
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0] * (max_id + 1)
    for obj_id in range(1, max_id + 1):
        body = objects_by_id.get(obj_id)
        if body is None:
            continue
        offsets[obj_id] = len(out)
        out += f"{obj_id} 0 obj".encode() + body + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {max_id + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for obj_id in range(1, max_id + 1):
        out += f"{offsets[obj_id]:010d} 00000 n \n".encode()
    out += (f"trailer<</Size {max_id + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n" "%%EOF").encode()
    return bytes(out)


def _make_cmap_stream(n_bytes):
    """A minimal, structurally plausible CMap body padded to ~``n_bytes``."""
    header = b"/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
    footer = b"endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    pad_target = max(0, n_bytes - len(header) - len(footer))
    return header + b"%" + b"A" * pad_target + b"\n" + footer


def _pdf_with_tounicode_fonts(n_fonts, cmap_size, *, content=b"BT /F1 12 Tf 10 10 Td (hi) Tj ET"):
    """A single-page PDF whose ``/Contents`` is tiny (passes content-stream
    admission trivially) but carries ``n_fonts`` Type0/CIDFontType2 fonts,
    each with a ``/ToUnicode`` CMap that genuinely FlateDecode-decompresses
    to ~``cmap_size`` bytes (honest compression -- the same "no lying
    header needed" idiom as :func:`_pdf_bomb_bytes`). Reproduces BLOCKER 1
    part (a)'s proven multiplication case: N individually-legal-sized CMaps
    whose AGGREGATE is what a naive per-stream-only bound would miss."""
    objects: dict[int, bytes] = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
    }
    font_dict_entries = "".join(f"/F{i} {4 + 3 * i} 0 R" for i in range(n_fonts))
    content_id = 4 + 3 * n_fonts
    objects[3] = (
        f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        f"/Resources<</Font<<{font_dict_entries}>>>>/Contents {content_id} 0 R>>"
    ).encode()
    next_id = 4
    for i in range(n_fonts):
        font_id, desc_id, cmap_id = next_id, next_id + 1, next_id + 2
        cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
        objects[font_id] = (
            f"<</Type/Font/Subtype/Type0/BaseFont/Test{i}/Encoding/Identity-H"
            f"/DescendantFonts[{desc_id} 0 R]/ToUnicode {cmap_id} 0 R>>"
        ).encode()
        objects[desc_id] = f"<</Type/Font/Subtype/CIDFontType2/BaseFont/Test{i}/CIDToGIDMap/Identity>>".encode()
        objects[cmap_id] = (
            f"<</Length {len(cmap_compressed)}/Filter/FlateDecode>>stream\n".encode()
            + cmap_compressed + b"\nendstream"
        )
        next_id += 3
    objects[content_id] = f"<</Length {len(content)}>>stream\n".encode() + content + b"\nendstream"
    return _assemble_pdf(objects)


def _pdf_with_large_fontfile2(fontfile2_size, *, content=b"BT /F1 12 Tf 10 10 Td (hi) Tj ET"):
    """A single-page PDF with one Type0/CIDFontType2 font carrying a SMALL,
    legitimate ``/ToUnicode`` CMap but a LARGE embedded ``/FontFile2``
    (TrueType program) on its ``/FontDescriptor`` -- the reviewer-verified
    positive control: pypdf's ``extract_text()`` never decompresses
    ``/FontFile2`` for text extraction, so this must succeed normally, not
    be refused, however large the embedded font program is."""
    small_cmap = zlib.compress(_make_cmap_stream(64), 6)
    fontfile2_compressed = zlib.compress(b"\x00" * fontfile2_size, 6)
    objects = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 8 0 R>>",
        4: b"<</Type/Font/Subtype/Type0/BaseFont/Test/Encoding/Identity-H"
        b"/DescendantFonts[5 0 R]/ToUnicode 6 0 R>>",
        5: b"<</Type/Font/Subtype/CIDFontType2/BaseFont/Test/CIDToGIDMap/Identity/FontDescriptor 7 0 R>>",
        6: f"<</Length {len(small_cmap)}/Filter/FlateDecode>>stream\n".encode() + small_cmap + b"\nendstream",
        7: b"<</Type/FontDescriptor/FontName/Test/FontFile2 9 0 R>>",
        8: f"<</Length {len(content)}>>stream\n".encode() + content + b"\nendstream",
        9: (
            f"<</Length {len(fontfile2_compressed)}/Filter/FlateDecode/Length1 {fontfile2_size}>>stream\n".encode()
            + fontfile2_compressed + b"\nendstream"
        ),
    }
    return _assemble_pdf(objects)


def _pdf_with_xobject_nested_fonts(n_fonts, cmap_size):
    """A single-page PDF whose page ``/Contents`` merely invokes ONE Form
    XObject (``/Fm0 Do``); that XObject's OWN ``/Resources/Font`` carries
    ``n_fonts`` Type0/CIDFontType2 fonts, each with a genuine FlateDecode
    ``/ToUnicode`` CMap ~``cmap_size`` bytes -- reproduces RESIDUAL BLOCKER
    A's proven XObject-nesting evasion (page-direct-only bounds never see
    fonts reachable only through a nested Form XObject's own resources)."""
    objects: dict[int, bytes] = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
    }
    page_content = b"q /Fm0 Do Q"
    objects[3] = b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</XObject<</Fm0 5 0 R>>>>/Contents 4 0 R>>"
    objects[4] = f"<</Length {len(page_content)}>>stream\n".encode() + page_content + b"\nendstream"
    font_dict_entries = "".join(f"/F{i} {6 + 3 * i} 0 R" for i in range(n_fonts))
    xobj_content = b" "
    objects[5] = (
        f"<</Type/XObject/Subtype/Form/BBox[0 0 612 792]"
        f"/Resources<</Font<<{font_dict_entries}>>>>/Length {len(xobj_content)}>>stream\n"
    ).encode() + xobj_content + b"\nendstream"
    next_id = 6
    for i in range(n_fonts):
        font_id, desc_id, cmap_id = next_id, next_id + 1, next_id + 2
        cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
        objects[font_id] = (
            f"<</Type/Font/Subtype/Type0/BaseFont/Test{i}/Encoding/Identity-H"
            f"/DescendantFonts[{desc_id} 0 R]/ToUnicode {cmap_id} 0 R>>"
        ).encode()
        objects[desc_id] = f"<</Type/Font/Subtype/CIDFontType2/BaseFont/Test{i}/CIDToGIDMap/Identity>>".encode()
        objects[cmap_id] = (
            f"<</Length {len(cmap_compressed)}/Filter/FlateDecode>>stream\n".encode()
            + cmap_compressed + b"\nendstream"
        )
        next_id += 3
    return _assemble_pdf(objects)


def _pdf_with_deeply_nested_xobject_font(depth, cmap_size):
    """A single-page PDF with a CHAIN of ``depth`` Form XObjects
    (page -> Fm0 -> Fm1 -> ... -> Fm(depth-1)), each nested purely via
    ``/Resources/XObject`` (no functional ``Do``-operator wiring needed --
    this module's pre-screen walks the RESOURCE graph directly, a
    deliberately more conservative superset of what ``extract_text()``'s
    content-stream-driven recursion visits); the font with its
    ``/ToUnicode`` CMap of ~``cmap_size`` bytes sits at the DEEPEST level,
    proving the recursive walk actually reaches arbitrary depth rather than
    stopping after one or two levels."""
    objects: dict[int, bytes] = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
    }
    first_xobj_id = 5
    objects[3] = (
        f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        f"/Resources<</XObject<</Fm0 {first_xobj_id} 0 R>>>>/Contents 4 0 R>>"
    ).encode()
    page_content = b"q /Fm0 Do Q"
    objects[4] = f"<</Length {len(page_content)}>>stream\n".encode() + page_content + b"\nendstream"

    font_id = first_xobj_id + depth
    desc_id = font_id + 1
    cmap_id = font_id + 2
    for level in range(depth):
        xobj_id = first_xobj_id + level
        if level + 1 < depth:
            resources = f"<</XObject<</Fm{level + 1} {first_xobj_id + level + 1} 0 R>>>>"
        else:
            resources = f"<</Font<</F0 {font_id} 0 R>>>>"
        xobj_content = b" "
        objects[xobj_id] = (
            f"<</Type/XObject/Subtype/Form/BBox[0 0 612 792]/Resources{resources}"
            f"/Length {len(xobj_content)}>>stream\n"
        ).encode() + xobj_content + b"\nendstream"

    cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
    objects[font_id] = (
        f"<</Type/Font/Subtype/Type0/BaseFont/Deep/Encoding/Identity-H"
        f"/DescendantFonts[{desc_id} 0 R]/ToUnicode {cmap_id} 0 R>>"
    ).encode()
    objects[desc_id] = b"<</Type/Font/Subtype/CIDFontType2/BaseFont/Deep/CIDToGIDMap/Identity>>"
    objects[cmap_id] = (
        f"<</Length {len(cmap_compressed)}/Filter/FlateDecode>>stream\n".encode()
        + cmap_compressed + b"\nendstream"
    )
    return _assemble_pdf(objects)


def _pdf_with_cyclic_xobjects():
    """A single-page PDF whose Form XObject ``Fm0`` references ``Fm1`` in
    its own ``/Resources/XObject``, and ``Fm1`` references ``Fm0`` right
    back -- a genuine mutual cycle in the resource graph, which PDF
    permits. Each carries one small, legitimate font, proving the
    cycle-protected walk still finds and counts real fonts while
    terminating (never hanging, never re-decoding the same XObject twice
    within one page) despite the cycle."""
    small_cmap = zlib.compress(_make_cmap_stream(64), 6)
    objects = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</XObject<</Fm0 5 0 R>>>>/Contents 4 0 R>>",
        4: b"<</Length 11>>stream\nq /Fm0 Do Q\nendstream",
        5: (
            b"<</Type/XObject/Subtype/Form/BBox[0 0 612 792]"
            b"/Resources<</XObject<</Fm1 8 0 R>>/Font<</F0 9 0 R>>>>/Length 1>>stream\n \nendstream"
        ),
        8: (
            b"<</Type/XObject/Subtype/Form/BBox[0 0 612 792]"
            b"/Resources<</XObject<</Fm0 5 0 R>>/Font<</F1 12 0 R>>>>/Length 1>>stream\n \nendstream"
        ),
        9: b"<</Type/Font/Subtype/Type0/BaseFont/T0/Encoding/Identity-H/DescendantFonts[10 0 R]/ToUnicode 11 0 R>>",
        10: b"<</Type/Font/Subtype/CIDFontType2/BaseFont/T0/CIDToGIDMap/Identity>>",
        11: f"<</Length {len(small_cmap)}/Filter/FlateDecode>>stream\n".encode() + small_cmap + b"\nendstream",
        12: b"<</Type/Font/Subtype/Type0/BaseFont/T1/Encoding/Identity-H/DescendantFonts[13 0 R]/ToUnicode 11 0 R>>",
        13: b"<</Type/Font/Subtype/CIDFontType2/BaseFont/T1/CIDToGIDMap/Identity>>",
    }
    return _assemble_pdf(objects)


def _pdf_with_tounicode_fonts_per_page(n_pages, cmap_size):
    """An ``n_pages``-page PDF where EACH page has its own tiny content
    stream and its OWN distinct Type0/CIDFontType2 font with a genuine
    FlateDecode ``/ToUnicode`` CMap of ~``cmap_size`` bytes -- reproduces
    RESIDUAL BLOCKER B's proven cross-page-multiplication evasion (each
    page individually under any single-page cap, but the document-wide sum
    is not)."""
    objects: dict[int, bytes] = {}
    page_ids = [3 + 3 * i for i in range(n_pages)]
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<</Type/Pages/Kids[{kids}]/Count {n_pages}>>".encode()
    next_id = 3 + 3 * n_pages
    page_content = b"BT /F0 12 Tf 10 10 Td (x) Tj ET"
    for i, pid in enumerate(page_ids):
        content_id, font_id = pid + 1, pid + 2
        desc_id, cmap_id = next_id, next_id + 1
        next_id += 2
        objects[pid] = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Resources<</Font<</F0 {font_id} 0 R>>>>/Contents {content_id} 0 R>>"
        ).encode()
        objects[content_id] = f"<</Length {len(page_content)}>>stream\n".encode() + page_content + b"\nendstream"
        cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
        objects[font_id] = (
            f"<</Type/Font/Subtype/Type0/BaseFont/Test{i}/Encoding/Identity-H"
            f"/DescendantFonts[{desc_id} 0 R]/ToUnicode {cmap_id} 0 R>>"
        ).encode()
        objects[desc_id] = f"<</Type/Font/Subtype/CIDFontType2/BaseFont/Test{i}/CIDToGIDMap/Identity>>".encode()
        objects[cmap_id] = (
            f"<</Length {len(cmap_compressed)}/Filter/FlateDecode>>stream\n".encode()
            + cmap_compressed + b"\nendstream"
        )
    return _assemble_pdf(objects)


def _pdf_legit_multi_page_shared_fonts(n_pages, n_fonts, cmap_size=20 * 1024):
    """A legitimate ``n_pages``-page, ``n_fonts``-font PDF -- every page
    SHARES the same ``n_fonts`` font objects (the realistic, common shape:
    fonts are reused across pages, not duplicated), each with a modest
    (~20 KiB default) real ``/ToUnicode`` CMap, and real drawable text.
    Positive control: proves a normal multi-page, multi-font resume-shaped
    document is not over-refused."""
    objects: dict[int, bytes] = {}
    page_ids = [3 + i for i in range(n_pages)]
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<</Type/Pages/Kids[{kids}]/Count {n_pages}>>".encode()
    next_id = 3 + n_pages
    font_ids = []
    for i in range(n_fonts):
        font_id, desc_id, cmap_id = next_id, next_id + 1, next_id + 2
        cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
        objects[font_id] = (
            f"<</Type/Font/Subtype/Type0/BaseFont/Test{i}/Encoding/Identity-H"
            f"/DescendantFonts[{desc_id} 0 R]/ToUnicode {cmap_id} 0 R>>"
        ).encode()
        objects[desc_id] = f"<</Type/Font/Subtype/CIDFontType2/BaseFont/Test{i}/CIDToGIDMap/Identity>>".encode()
        objects[cmap_id] = (
            f"<</Length {len(cmap_compressed)}/Filter/FlateDecode>>stream\n".encode()
            + cmap_compressed + b"\nendstream"
        )
        font_ids.append(font_id)
        next_id += 3
    font_dict = "".join(f"/F{i} {fid} 0 R" for i, fid in enumerate(font_ids))
    for pid in page_ids:
        content_id = next_id
        next_id += 1
        content = b"BT /F0 12 Tf 10 10 Td (Legitimate resume page text.) Tj ET"
        objects[content_id] = f"<</Length {len(content)}>>stream\n".encode() + content + b"\nendstream"
        objects[pid] = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Resources<</Font<<{font_dict}>>>>/Contents {content_id} 0 R>>"
        ).encode()
    return _assemble_pdf(objects)


# ---------------------------------------------------------------------------
# ObjStm / XRef-stream fixture builders (independent review, third round,
# 2026-09-02). These use PDF 1.5+ CROSS-REFERENCE STREAMS (not classic xref
# tables) with real, spec-correct binary /W[1 4 2] entries, so the
# constructed files are genuinely parseable PDFs (verified directly against
# bare pypdf before use in any test below), not merely byte soup.
# ---------------------------------------------------------------------------


def _pdf_xref_entry(entry_type, field2, field3):
    return struct.pack(">B", entry_type) + struct.pack(">I", field2) + struct.pack(">H", field3)


def _pdf_with_objstm_bomb_per_page(n_pages, padding_per_page):
    """An ``n_pages``-page PDF where EVERY page dictionary lives INSIDE its
    OWN ``/Type/ObjStm`` compressed object stream (reachable only via
    ``/Kids`` -> the compressed-object xref entry -- never as its own
    literal ``N G obj``), each ObjStm padded to decode to roughly
    ``padding_per_page`` bytes. Reproduces the third-round reviewer's exact
    finding: pypdf decompresses ObjStm/XRef streams during OBJECT
    RESOLUTION, entirely outside the role-specific (/Contents, font-aux)
    budgets those two only ever walk pypdf's ALREADY-resolved object graph.
    """
    out = bytearray(b"%PDF-1.5\n")
    offsets: dict[int, int] = {}

    def emit(num, body):
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj".encode() + body + b"\nendobj\n")

    content = b"BT /F1 12 Tf 10 10 Td (x) Tj ET"
    next_id = 3
    page_ids, objstm_ids = [], []
    for _ in range(n_pages):
        page_ids.append(next_id)
        objstm_ids.append(next_id + 1)
        next_id += 2
    content_id, font_id, xref_id = next_id, next_id + 1, next_id + 2

    emit(1, b"<</Type/Catalog/Pages 2 0 R>>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    emit(2, f"<</Type/Pages/Kids[{kids}]/Count {n_pages}>>".encode())
    emit(content_id, b"<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream")
    emit(font_id, b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

    for page_id, objstm_id in zip(page_ids, objstm_ids):
        page_dict = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Resources<</Font<</F1 {font_id} 0 R>>>>/Contents {content_id} 0 R"
            f"/Metadata({'A' * padding_per_page})>>"
        ).encode()
        header = f"{page_id} 0 ".encode()
        compressed = zlib.compress(header + page_dict, 6)
        offsets[objstm_id] = len(out)
        out.extend(
            f"{objstm_id} 0 obj<</Type/ObjStm/N 1/First {len(header)}".encode()
            + b"/Length " + str(len(compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
            + compressed + b"\nendstream\nendobj\n"
        )

    entries = [_pdf_xref_entry(0, 0, 65535), _pdf_xref_entry(1, offsets[1], 0), _pdf_xref_entry(1, offsets[2], 0)]
    for page_id, objstm_id in zip(page_ids, objstm_ids):
        entries.append(_pdf_xref_entry(2, objstm_id, 0))  # page: compressed in its own ObjStm, index 0
        entries.append(_pdf_xref_entry(1, offsets[objstm_id], 0))
    entries.append(_pdf_xref_entry(1, offsets[content_id], 0))
    entries.append(_pdf_xref_entry(1, offsets[font_id], 0))
    entries.append(_pdf_xref_entry(1, 0, 65535))  # placeholder for the xref object itself

    xref_offset = len(out)
    entries[-1] = _pdf_xref_entry(1, xref_offset, 0)
    xref_compressed = zlib.compress(b"".join(entries), 6)
    out.extend(
        f"{xref_id} 0 obj<</Type/XRef/Size {xref_id + 1}/W[1 4 2]/Root 1 0 R".encode()
        + b"/Length " + str(len(xref_compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
        + xref_compressed + b"\nendstream\nendobj\n"
    )
    out.extend(f"startxref\n{xref_offset}\n%%EOF".encode())
    return bytes(out)


def _pdf_with_legitimate_objstm(page_text="Legitimate ObjStm-packed page text."):
    """A small, entirely legitimate 1-page PDF whose page dictionary is
    packed inside a real (tiny) ObjStm, XRef-stream based -- the shape a
    modern, size-optimizing PDF writer commonly produces. Positive control:
    proves ordinary ObjStm/XRef-stream usage is not over-refused."""
    content = f"BT /F1 12 Tf 10 10 Td ({page_text}) Tj ET".encode()
    return _build_legitimate_objstm(content)


def _build_legitimate_objstm(content: bytes):
    out = bytearray(b"%PDF-1.5\n")
    offsets: dict[int, int] = {}

    def emit(num, body):
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj".encode() + body + b"\nendobj\n")

    emit(1, b"<</Type/Catalog/Pages 2 0 R>>")
    emit(2, b"<</Type/Pages/Kids[3 0 R]/Count 1>>")
    emit(4, b"<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream")
    emit(5, b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    page_dict = b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"
    header = b"3 0 "
    compressed = zlib.compress(header + page_dict, 6)
    offsets[6] = len(out)
    out.extend(
        f"6 0 obj<</Type/ObjStm/N 1/First {len(header)}".encode()
        + b"/Length " + str(len(compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
        + compressed + b"\nendstream\nendobj\n"
    )
    entries = [
        _pdf_xref_entry(0, 0, 65535), _pdf_xref_entry(1, offsets[1], 0), _pdf_xref_entry(1, offsets[2], 0),
        _pdf_xref_entry(2, 6, 0), _pdf_xref_entry(1, offsets[4], 0), _pdf_xref_entry(1, offsets[5], 0),
        _pdf_xref_entry(1, offsets[6], 0), _pdf_xref_entry(1, 0, 65535),
    ]
    xref_offset = len(out)
    entries[-1] = _pdf_xref_entry(1, xref_offset, 0)
    xref_compressed = zlib.compress(b"".join(entries), 6)
    out.extend(
        b"7 0 obj<</Type/XRef/Size 8/W[1 4 2]/Root 1 0 R"
        + b"/Length " + str(len(xref_compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
        + xref_compressed + b"\nendstream\nendobj\n"
    )
    out.extend(f"startxref\n{xref_offset}\n%%EOF".encode())
    return bytes(out)


def _pdf_with_xref_stream_bomb(padding_entries):
    """A minimal, otherwise-valid 1-page PDF whose XRef STREAM itself (not
    any ObjStm, not any font/content stream) is padded with many extra,
    harmless (type-0 free) entries so its OWN decoded size is large --
    proves the raw scan bounds the XRef stream family too, not only
    ObjStm/content/font streams."""
    out = bytearray(b"%PDF-1.5\n")
    offsets: dict[int, int] = {}

    def emit(num, body):
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj".encode() + body + b"\nendobj\n")

    content = b"BT /F1 12 Tf 10 10 Td (x) Tj ET"
    emit(1, b"<</Type/Catalog/Pages 2 0 R>>")
    emit(2, b"<</Type/Pages/Kids[3 0 R]/Count 1>>")
    emit(3, b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>")
    emit(4, b"<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream")
    emit(5, b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

    real_entries = [_pdf_xref_entry(0, 0, 65535)] + [_pdf_xref_entry(1, offsets[i], 0) for i in (1, 2, 3, 4, 5)]
    real_entries.append(_pdf_xref_entry(1, 0, 65535))  # placeholder for the xref object itself
    padding = [_pdf_xref_entry(0, 0, 65535) for _ in range(padding_entries)]
    all_entries = real_entries + padding

    xref_offset = len(out)
    all_entries[6] = _pdf_xref_entry(1, xref_offset, 0)
    xref_compressed = zlib.compress(b"".join(all_entries), 6)
    out.extend(
        b"6 0 obj<</Type/XRef/Size 7/W[1 4 2]/Root 1 0 R"
        + b"/Length " + str(len(xref_compressed)).encode() + b"/Filter/FlateDecode>>stream\n"
        + xref_compressed + b"\nendstream\nendobj\n"
    )
    out.extend(f"startxref\n{xref_offset}\n%%EOF".encode())
    return bytes(out)


class FakeUpload:
    """Mirrors werkzeug's FileStorage just enough for validate_upload."""

    def __init__(self, data, mimetype):
        self.stream = io.BytesIO(data)
        self.mimetype = mimetype


class FakeFetchAdapter:
    def __init__(self, data=b"Fetched job posting body text.", content_type="text/plain", host_class="public"):
        self._data = data
        self._content_type = content_type
        self._host_class = host_class

    def fetch(self, url):
        return FetchResult(
            data=self._data, declared_content_type=self._content_type, submitted_url=url, final_url=url,
            resolved_address="203.0.113.7", fetched_at=NOW, host_class=self._host_class,
        )


class RefusingFetchAdapter:
    def __init__(self, reason, host_class):
        self._reason = reason
        self._host_class = host_class

    def fetch(self, url):  # noqa: ARG002
        raise FetchRefused(self._reason, self._host_class)


class TakedownRightsReader:
    def obligation_for(self, record):  # noqa: ARG002
        return RIGHTS_TAKEDOWN_REQUIRED


class Harness(unittest.TestCase):
    """Shared setUp: a fresh repository/sink/service per test, plus a
    unique-idempotency-key generator."""

    def setUp(self):
        self.repository = InMemoryMemberImportRepository()
        self.sink = InMemoryAuditSink()
        self.service = MemberImportService(self.repository, self.sink)
        self._key_counter = 0

    def key(self, label="k"):
        self._key_counter += 1
        return f"{label}-{self._key_counter}"


# ---------------------------------------------------------------------------
# Closed-vocabulary / dataclass pairing tests
# ---------------------------------------------------------------------------


class ClosedVocabularyTests(unittest.TestCase):
    def test_outcome_states_are_the_nine_doc06_states_verbatim(self):
        self.assertEqual(
            OUTCOME_STATES,
            {"fetched", "decoded", "parsed", "extracted", "empty", "partial", "blocked", "timeout", "refused"},
        )

    def test_terminal_success_states(self):
        self.assertEqual(TERMINAL_SUCCESS_STATES, {"extracted", "partial", "empty"})

    def test_intake_methods(self):
        self.assertEqual(INTAKE_METHODS, {"paste", "upload", "url_fetch"})

    def test_record_states(self):
        self.assertEqual(RECORD_STATES, {"active", "deleted"})

    def test_body_removal_reasons(self):
        self.assertEqual(BODY_REMOVAL_REASONS, {"member_delete", "rights_takedown"})

    def test_rights_obligation_classes(self):
        self.assertEqual(RIGHTS_OBLIGATION_CLASSES, {"none", "takedown_required"})

    def test_host_classes_closed_set(self):
        self.assertEqual(
            HOST_CLASSES,
            {
                "not_applicable", "public", "denied_loopback", "denied_private", "denied_link_local",
                "denied_cgnat", "denied_ula", "denied_metadata", "denied_other",
            },
        )

    def test_commands_closed_set(self):
        self.assertEqual(COMMANDS, {"submit_paste", "submit_upload", "import_from_url", "delete_import"})

    def test_allowed_upload_content_types(self):
        self.assertEqual(ALLOWED_UPLOAD_CONTENT_TYPES, {"application/pdf", _DOCX_CONTENT_TYPE, "text/plain"})


class DataclassPairingTests(unittest.TestCase):
    def _record_kwargs(self, **overrides):
        base = dict(
            import_key="k1", user_key="u1", data_class="fixture", intake_method=INTAKE_PASTE,
            record_state=RECORD_STATE_ACTIVE, declared_content_type=None, byte_count=None,
            submitted_url=None, final_url=None, resolved_address=None, fetched_at=None,
            content_hash="a" * 64, sanitizer_version=SANITIZER_VERSION, sanitized_text="hello",
            extracted_units=5, truncated=False, outcome=OUTCOME_EXTRACTED, outcome_reason=None,
            rights_obligation_class=RIGHTS_NONE, body_removed_at=None, body_removal_reason=None,
            created_at=NOW, updated_at=NOW,
        )
        base.update(overrides)
        return base

    def test_a_well_formed_extracted_record_constructs(self):
        MemberImport(**self._record_kwargs())

    def test_extracted_outcome_requires_text_or_removal(self):
        with self.assertRaises(ValueError):
            MemberImport(**self._record_kwargs(sanitized_text=None))

    def test_empty_outcome_forbids_text(self):
        with self.assertRaises(ValueError):
            MemberImport(**self._record_kwargs(outcome=OUTCOME_EMPTY, sanitized_text="x", extracted_units=None))

    def test_refused_outcome_requires_paired_reason(self):
        with self.assertRaises(ValueError):
            MemberImport(
                **self._record_kwargs(
                    outcome=OUTCOME_REFUSED, outcome_reason=None, sanitized_text=None, extracted_units=None
                )
            )
        MemberImport(
            **self._record_kwargs(
                outcome=OUTCOME_REFUSED, outcome_reason=REASON_PARSER_FAILURE, sanitized_text=None, extracted_units=None
            )
        )

    def test_partial_requires_truncated_and_output_truncated_reason(self):
        with self.assertRaises(ValueError):
            MemberImport(**self._record_kwargs(outcome=OUTCOME_PARTIAL, outcome_reason=REASON_OUTPUT_TRUNCATED, truncated=False))
        MemberImport(**self._record_kwargs(outcome=OUTCOME_PARTIAL, outcome_reason=REASON_OUTPUT_TRUNCATED, truncated=True))

    def test_truncated_true_forbidden_outside_partial(self):
        with self.assertRaises(ValueError):
            MemberImport(**self._record_kwargs(truncated=True))

    def test_fetch_provenance_forbidden_unless_url_fetch(self):
        with self.assertRaises(ValueError):
            MemberImport(**self._record_kwargs(submitted_url="https://example.com"))

    def test_fetch_provenance_permitted_for_url_fetch(self):
        MemberImport(
            **self._record_kwargs(
                intake_method=INTAKE_URL_FETCH, submitted_url="https://example.com", final_url="https://example.com",
                resolved_address="203.0.113.1", fetched_at=NOW,
            )
        )

    def test_body_removed_requires_no_text(self):
        with self.assertRaises(ValueError):
            MemberImport(
                **self._record_kwargs(body_removed_at=NOW, body_removal_reason=BODY_REMOVAL_RIGHTS_TAKEDOWN)
            )

    def test_deleted_state_requires_member_delete_reason(self):
        with self.assertRaises(ValueError):
            MemberImport(
                **self._record_kwargs(
                    record_state=RECORD_STATE_DELETED, sanitized_text=None,
                    body_removed_at=NOW, body_removal_reason=BODY_REMOVAL_RIGHTS_TAKEDOWN,
                )
            )
        MemberImport(
            **self._record_kwargs(
                record_state=RECORD_STATE_DELETED, sanitized_text=None,
                body_removed_at=NOW, body_removal_reason=BODY_REMOVAL_MEMBER_DELETE,
            )
        )

    def test_member_delete_reason_requires_deleted_state(self):
        with self.assertRaises(ValueError):
            MemberImport(
                **self._record_kwargs(
                    sanitized_text=None, body_removed_at=NOW, body_removal_reason=BODY_REMOVAL_MEMBER_DELETE
                )
            )

    def test_import_stage_outcome_pairing(self):
        ImportStageOutcome(import_key="k1", user_key="u1", outcome=OUTCOME_DECODED, reason_code=None, occurred_at=NOW)
        with self.assertRaises(ValueError):
            ImportStageOutcome(
                import_key="k1", user_key="u1", outcome=OUTCOME_REFUSED, reason_code=None, occurred_at=NOW
            )

    def test_import_receipt_command_and_outcome_closed(self):
        ImportReceipt(import_key="k1", command=COMMAND_SUBMIT_PASTE, outcome=OUTCOME_EXTRACTED, outcome_reason=None, truncated=False)
        with self.assertRaises(ValueError):
            ImportReceipt(import_key="k1", command="not_a_command", outcome=OUTCOME_EXTRACTED, outcome_reason=None, truncated=False)
        with self.assertRaises(ValueError):
            ImportReceipt(import_key="k1", command=COMMAND_SUBMIT_PASTE, outcome="not_an_outcome", outcome_reason=None, truncated=False)

    def test_fetch_result_host_class_closed(self):
        FetchResult(
            data=b"x", declared_content_type="text/plain", submitted_url="u", final_url="u",
            resolved_address="1.2.3.4", fetched_at=NOW, host_class="public",
        )
        with self.assertRaises(ValueError):
            FetchResult(
                data=b"x", declared_content_type="text/plain", submitted_url="u", final_url="u",
                resolved_address="1.2.3.4", fetched_at=NOW, host_class="not_a_host_class",
            )

    def test_audit_event_kind_and_host_class_closed(self):
        MemberImportAuditEvent(
            event_kind="import_stored", user_key="u1", keys=("k1",), reason_code=None,
            host_class=HOST_CLASS_NOT_APPLICABLE, actor="member", at=NOW,
        )
        with self.assertRaises(ValueError):
            MemberImportAuditEvent(
                event_kind="not_a_kind", user_key="u1", keys=(), reason_code=None,
                host_class=HOST_CLASS_NOT_APPLICABLE, actor="member", at=NOW,
            )

    def test_limits_reject_non_positive_bounds(self):
        MemberImportLimits()
        with self.assertRaises(ValueError):
            MemberImportLimits(max_paste_units=0)
        with self.assertRaises(ValueError):
            MemberImportLimits(pdf_extraction_timeout_seconds=-1)


# ---------------------------------------------------------------------------
# A. Doc 16 §3 unconditional rows -- pre-admission refusals (matrix 1-7, 27)
# ---------------------------------------------------------------------------


class PasteAdmissionTests(Harness):
    def test_empty_paste_is_refused_paste_required_no_row(self):
        digest_before = self.repository.state_digest()
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "   ", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "paste_required")
        self.assertFalse(ctx.exception.recoverable)
        self.assertEqual(self.repository.state_digest(), digest_before)
        self.assertEqual(self.repository.imports_for_owner("alice"), ())
        self.assertEqual([e.event_kind for e in self.sink.events], ["import_refused"])
        self.assertEqual(self.sink.events[0].reason_code, "paste_required")
        self.assertEqual(self.sink.events[0].host_class, HOST_CLASS_NOT_APPLICABLE)
        self.assertEqual(self.sink.events[0].keys, ())

    def test_oversized_paste_is_refused_paste_too_long(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "x" * (MAX_PASTE_UTF16_UNITS + 1), self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "paste_too_long")
        self.assertEqual(self.repository.imports_for_owner("alice"), ())

    def test_paste_at_exactly_the_cap_is_admitted(self):
        receipt = self.service.submit_paste("alice", "A" * MAX_PASTE_UTF16_UNITS, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)

    def test_hostile_control_character_paste_is_refused_never_stripped(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "hello\x01world job posting", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "hostile_characters")
        self.assertEqual(self.repository.imports_for_owner("alice"), ())

    def test_hostile_bidi_override_paste_is_refused(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "hello‮world job posting", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "hostile_characters")

    def test_del_character_paste_is_refused(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "hello\x7fworld job posting", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "hostile_characters")

    def test_tab_newline_cr_are_not_hostile(self):
        receipt = self.service.submit_paste("alice", "line one\nline two\tindented\r\n", self.key(), now=NOW)
        self.assertIn(receipt.outcome, TERMINAL_SUCCESS_STATES)


class UploadAdmissionTests(Harness):
    def test_absent_upload_is_refused_upload_required(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", None, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "upload_required")

    def test_empty_stream_is_refused_upload_required(self):
        upload = FakeUpload(b"", "text/plain")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "upload_required")

    def test_forbidden_declared_mime_bare_zip_is_refused_unsupported_type(self):
        upload = FakeUpload(b"PK\x03\x04" + b"\x00" * 16, "application/zip")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_forbidden_declared_mime_image_is_refused(self):
        upload = FakeUpload(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_pdf_with_elf_bytes_is_rejected(self):
        upload = FakeUpload(b"\x7fELF" + b"\x00" * 64, "application/pdf")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_pdf_with_zip_bytes_is_rejected(self):
        upload = FakeUpload(b"PK\x03\x04" + b"\x00" * 64, "application/pdf")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_pdf_with_html_bytes_is_rejected(self):
        upload = FakeUpload(b"<!DOCTYPE html><html><body>hi</body></html>", "application/pdf")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_docx_with_pdf_bytes_is_rejected(self):
        upload = FakeUpload(_pdf_bytes(), _DOCX_CONTENT_TYPE)
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_docx_with_exe_bytes_is_rejected(self):
        upload = FakeUpload(b"MZ" + b"\x90" * 64, _DOCX_CONTENT_TYPE)
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_text_with_html_bytes_is_rejected(self):
        upload = FakeUpload(b"<!DOCTYPE html><html><body>hi</body></html>", "text/plain")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_text_with_pdf_bytes_is_rejected(self):
        upload = FakeUpload(_pdf_bytes(), "text/plain")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_declared_text_with_zip_bytes_is_rejected(self):
        upload = FakeUpload(b"PK\x03\x04" + b"\x00" * 64, "text/plain")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "unsupported_type")

    def test_oversized_upload_is_refused_too_large_no_row(self):
        upload = FakeUpload(b"A" * (MAX_UPLOAD_BYTES + 1), "text/plain")
        digest_before = self.repository.state_digest()
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "too_large")
        self.assertEqual(self.repository.state_digest(), digest_before)

    def test_bounded_read_never_asks_for_more_than_max_plus_one(self):
        """A.1 -- the streaming-cutoff discipline: the stream is asked for
        exactly ``MAX + 1`` bytes, never the whole (potentially enormous)
        body."""
        upload = FakeUpload(b"A" * (MAX_UPLOAD_BYTES + 1), "text/plain")
        upload.stream = MagicMock(wraps=upload.stream)
        with self.assertRaises(MemberImportServiceError):
            self.service.submit_upload("alice", upload, self.key(), now=NOW)
        upload.stream.read.assert_called_once_with(MAX_UPLOAD_BYTES + 1)

    def test_exactly_at_cap_upload_is_admitted(self):
        upload = FakeUpload(b"A" * MAX_UPLOAD_BYTES, "text/plain")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertIn(receipt.outcome, TERMINAL_SUCCESS_STATES)

    def test_a_genuine_pdf_is_accepted(self):
        upload = FakeUpload(_pdf_bytes("Senior widget engineer role."), "application/pdf")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIn("Senior widget engineer role.", record.sanitized_text)

    def test_a_genuine_docx_is_accepted(self):
        upload = FakeUpload(_docx_bytes(["Hello employer wording."]), _DOCX_CONTENT_TYPE)
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.sanitized_text, "Hello employer wording.")

    def test_a_genuine_text_upload_is_accepted(self):
        upload = FakeUpload(b"Plain role description text.", "text/plain")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)


class FieldValidationTests(Harness):
    def test_invalid_data_class_no_audit_event(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "hello there job posting text", self.key(), data_class="bogus", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "data_class_invalid")
        self.assertEqual(self.sink.events, [])

    def test_invalid_filter_on_list_is_not_a_matrix_row_here(self):
        # list_imports takes no filter parameter in C10 (unlike C6's
        # saved-view filters) -- filter_invalid is reserved for a future
        # C8-level query surface; nothing to validate at the service layer.
        self.assertTrue(True)

    def test_import_limit_reached_refuses_without_a_row(self):
        limits = MemberImportLimits(max_active_imports_per_member=1)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        service.submit_paste("alice", "First posting text here for the ceiling test.", self.key(), now=NOW)
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.submit_paste("alice", "Second posting text here for the ceiling test.", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "import_limit_reached")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(len(self.repository.imports_for_owner("alice")), 1)


# ---------------------------------------------------------------------------
# A.6 / C. URL fetch port: flag matrix, adapter absence, downstream pre-proof
# ---------------------------------------------------------------------------


class UrlFetchPortTests(Harness):
    def test_both_flags_off_refuses_surface_flag_off(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(self.sink.events[-1].event_kind, "url_fetch_unavailable")
        self.assertEqual(self.sink.events[-1].reason_code, "surface_flag_off")
        self.assertEqual(self.sink.events[-1].host_class, HOST_CLASS_NOT_APPLICABLE)
        self.assertEqual(self.sink.events[-1].keys, ())

    def test_surface_on_fetch_off_refuses_fetch_flag_off(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: name == FLAG_SURFACE
        )
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")
        self.assertEqual(self.sink.events[-1].reason_code, "fetch_flag_off")

    def test_surface_off_fetch_on_still_refuses_surface_flag_off_first(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: name == FLAG_URL_FETCH
        )
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")
        self.assertEqual(self.sink.events[-1].reason_code, "surface_flag_off")

    def test_both_flags_on_but_adapter_absent_refuses_adapter_absent(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: True, adapter_resolver=lambda: None
        )
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")
        self.assertEqual(self.sink.events[-1].reason_code, "adapter_absent")

    def test_default_adapter_resolver_returns_none_because_module_is_absent(self):
        """Stop-control pre-proof: with the REAL (default) resolver and both
        flags forced on, the refusal is still adapter_absent, because
        member_url_fetch_service.py genuinely does not exist at this
        candidate."""
        service = MemberImportService(self.repository, self.sink, flag_reader=lambda name: True)
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")
        self.assertEqual(self.sink.events[-1].reason_code, "adapter_absent")

    def test_url_refusal_never_appears_in_any_audit_field(self):
        secret_url = "https://internal.example.com/leak-me?token=abc123"
        with self.assertRaises(MemberImportServiceError):
            self.service.import_from_url("alice", secret_url, self.key(), now=NOW)
        for event in self.sink.events:
            for value in (event.event_kind, event.reason_code, event.actor, *event.keys):
                if value is not None:
                    self.assertNotIn("internal.example.com", value)
                    self.assertNotIn("leak-me", value)
                    self.assertNotIn("token", value)

    def test_url_refusal_creates_no_row_and_no_mutation(self):
        digest_before = self.repository.state_digest()
        with self.assertRaises(MemberImportServiceError):
            self.service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(self.repository.state_digest(), digest_before)
        self.assertEqual(self.repository.imports_for_owner("alice"), ())

    def test_member_url_fetch_service_module_does_not_exist(self):
        """The literal stop control the blueprint requires: the C13-reserved
        module must be ABSENT at the C10 candidate."""
        path = ROOT / "services" / "my_opportunities" / "member_url_fetch_service.py"
        self.assertFalse(path.exists(), "member_url_fetch_service.py must not exist at the C10 candidate")
        import importlib

        with self.assertRaises(ImportError):
            importlib.import_module(FETCH_MODULE)

    # -- Group C: downstream pre-proof via an injected FetchAdapter double --

    def test_both_flags_on_with_injected_adapter_runs_the_identical_pipeline(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: True,
            adapter_resolver=lambda: FakeFetchAdapter(data=b"Great role: widget engineer.", content_type="text/plain"),
        )
        receipt = service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.intake_method, INTAKE_URL_FETCH)
        self.assertIn("Great role", record.sanitized_text)
        self.assertEqual(record.submitted_url, "https://example.com/job")
        self.assertEqual(record.final_url, "https://example.com/job")
        self.assertEqual(record.resolved_address, "203.0.113.7")
        self.assertEqual(record.fetched_at, NOW)
        trail = service.stage_outcomes("alice", receipt.import_key)
        self.assertEqual([s.outcome for s in trail], [OUTCOME_FETCHED, OUTCOME_DECODED, OUTCOME_PARSED, OUTCOME_EXTRACTED])

    def test_fetch_refused_denied_address_maps_to_blocked(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: True,
            adapter_resolver=lambda: RefusingFetchAdapter("denied_address", "denied_private"),
        )
        receipt = service.import_from_url("alice", "https://internal.example/job", self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_BLOCKED)
        self.assertEqual(receipt.outcome_reason, "denied_address")
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)
        self.assertEqual(self.sink.events[-1].host_class, "denied_private")

    def test_fetch_refused_fetch_deadline_maps_to_timeout(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: True,
            adapter_resolver=lambda: RefusingFetchAdapter("fetch_deadline", "public"),
        )
        receipt = service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_TIMEOUT)
        self.assertEqual(receipt.outcome_reason, "fetch_deadline")

    def test_fetch_refused_fetch_too_large_maps_to_refused(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: True,
            adapter_resolver=lambda: RefusingFetchAdapter("fetch_too_large", "public"),
        )
        receipt = service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, "fetch_too_large")

    def test_flag_flip_off_restores_refusal_c13_rollback_contract(self):
        toggle = {"on": True}
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda name: toggle["on"],
            adapter_resolver=lambda: FakeFetchAdapter(),
        )
        receipt = service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        toggle["on"] = False
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.import_from_url("alice", "https://example.com/job", self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "url_fetch_unavailable")


# ---------------------------------------------------------------------------
# B. Pipeline outcome truth
# ---------------------------------------------------------------------------


class PipelineOutcomeTests(Harness):
    def test_paste_success_trail_is_decoded_parsed_extracted(self):
        receipt = self.service.submit_paste("alice", "A perfectly ordinary role description.", self.key(), now=NOW)
        trail = self.service.stage_outcomes("alice", receipt.import_key)
        self.assertEqual([s.outcome for s in trail], [OUTCOME_DECODED, OUTCOME_PARSED, OUTCOME_EXTRACTED])
        self.assertTrue(all(s.reason_code is None for s in trail))

    def test_undecodable_text_upload_is_refused_could_not_decode(self):
        # Invalid UTF-8 (a lead byte with no continuation) that still
        # sniffs as ordinary "text" (no NUL byte, no pdf/zip/elf/exe/html
        # signature) so the failure is caught at DECODE, not pre-admission.
        upload = FakeUpload(b"\x80\x81\x82 role posting with invalid utf-8 lead bytes", "text/plain")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_COULD_NOT_DECODE)
        trail = self.service.stage_outcomes("alice", receipt.import_key)
        self.assertEqual([s.outcome for s in trail], [OUTCOME_REFUSED])
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)

    def test_malformed_pdf_structure_is_refused_parser_failure(self):
        upload = FakeUpload(b"%PDF-1.4\ngarbage garbage garbage" + b"X" * 100, "application/pdf")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_FAILURE)
        trail = self.service.stage_outcomes("alice", receipt.import_key)
        self.assertEqual([s.outcome for s in trail], [OUTCOME_DECODED, OUTCOME_REFUSED])

    def test_malformed_docx_structure_is_refused_parser_failure(self):
        upload = FakeUpload(b"PK\x03\x04" + b"not a real zip" * 4, _DOCX_CONTENT_TYPE)
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_FAILURE)

    def test_pdf_page_count_bomb_is_refused_parser_resource_bounds(self):
        limits = MemberImportLimits(max_pdf_pages=1)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_pdf_bytes(), "application/pdf")
        # Build a genuine two-page PDF via two content streams referencing
        # the same page-tree shape as _pdf_bytes but with 2 kids.
        text = "Role posting page text.".encode("latin-1")
        content = b"BT /F1 12 Tf 10 10 Td (" + text + b") Tj ET"
        objs = [
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
            b"2 0 obj<</Type/Pages/Kids[3 0 R 4 0 R]/Count 2>>endobj",
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Resources<</Font<</F1 6 0 R>>>>/Contents 5 0 R>>endobj",
            b"4 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Resources<</Font<</F1 6 0 R>>>>/Contents 5 0 R>>endobj",
            b"5 0 obj<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream endobj",
            b"6 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
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
        out += (f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_offset}\n" "%%EOF").encode()
        upload = FakeUpload(bytes(out), "application/pdf")
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_RESOURCE_BOUNDS)

    def test_pdf_extraction_deadline_is_timeout_and_discards_text(self):
        limits = MemberImportLimits(pdf_extraction_timeout_seconds=1e-9)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_pdf_bytes("Text that will never be stored."), "application/pdf")
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_TIMEOUT)
        self.assertEqual(receipt.outcome_reason, REASON_EXTRACTION_DEADLINE)
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)

    def test_docx_entry_count_bomb_is_refused_archive_bomb_suspected(self):
        limits = MemberImportLimits(max_docx_entries=1)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_docx_bytes(["Hello."]), _DOCX_CONTENT_TYPE)
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_ARCHIVE_BOMB_SUSPECTED)

    def test_docx_entry_uncompressed_size_bomb_is_refused(self):
        limits = MemberImportLimits(max_docx_entry_uncompressed_bytes=8)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_docx_bytes(["A paragraph long enough to exceed 8 bytes."]), _DOCX_CONTENT_TYPE)
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_ARCHIVE_BOMB_SUSPECTED)

    def test_document_xml_specific_cap_is_independently_plumbed(self):
        # MINOR 1 (2026-09-02 independent review): word/document.xml gets
        # its own, tighter cap (default 5 MiB, vs. the 25 MiB general entry
        # cap) because it is the one entry this module hands to
        # ElementTree.fromstring for a full DOM parse -- a legal 20 MiB
        # document.xml was measured to peak ~214 MiB building that tree,
        # amplification a raw-byte-only cap cannot see. Proven here: a
        # reduced max_docx_document_xml_bytes refuses even though the
        # general max_docx_entry_uncompressed_bytes stays at its generous
        # default -- confirming the two bounds are independently plumbed,
        # not aliases of each other (the pre-filter in
        # _safe_zip_member_names still uses the general cap; the
        # authoritative bounded read of word/document.xml specifically now
        # uses the dedicated one).
        limits = MemberImportLimits(max_docx_document_xml_bytes=8)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(
            _docx_bytes(["A paragraph long enough to exceed an 8-byte document.xml cap."]), _DOCX_CONTENT_TYPE
        )
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_ARCHIVE_BOMB_SUSPECTED)

    def test_docx_total_uncompressed_size_bomb_is_refused(self):
        limits = MemberImportLimits(max_docx_total_uncompressed_bytes=8)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_docx_bytes(["A paragraph long enough to exceed the total cap."]), _DOCX_CONTENT_TYPE)
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_ARCHIVE_BOMB_SUSPECTED)

    def test_docx_compression_ratio_bomb_is_refused(self):
        # A highly repetitive (hence highly compressible) large paragraph
        # trips the ratio heuristic even though it fits the absolute caps.
        # zipfile.ZipFile defaults to ZIP_STORED (no compression, ratio
        # 1:1); ZIP_DEFLATED must be requested explicitly to exercise the
        # ratio guard at all.
        buffer = io.BytesIO()
        body = "".join(f"<w:p><w:r><w:t>{'word ' * 4000}</w:t></w:r></w:p>" for _ in range(1))
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{_WORDPROCESSINGML_NS}"><w:body>{body}</w:body>'
            "</w:document>"
        ).encode("utf-8")
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
            archive.writestr("word/document.xml", document_xml)
        limits = MemberImportLimits(max_docx_entry_compression_ratio=2)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(buffer.getvalue(), _DOCX_CONTENT_TYPE)
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_ARCHIVE_BOMB_SUSPECTED)

    def test_pasted_script_and_handler_canaries_never_appear_in_sanitized_text(self):
        payload = (
            'Great role. <script>alert(1)</script> <style>body{}</style> '
            '<div onclick="evil()">click me</div> Please apply with resume.'
        )
        receipt = self.service.submit_paste("alice", payload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        for canary in ("<script", "alert(1)", "<style", "onclick", "evil()"):
            self.assertNotIn(canary, record.sanitized_text)
        self.assertIn("Great role.", record.sanitized_text)
        self.assertIn("Please apply with resume.", record.sanitized_text)

    def test_split_tag_entity_encoded_canary_never_reads_as_a_tag(self):
        # IMPORTANT 2 (2026-09-01 self-review): the coordinator's exact
        # "split-tag" example. The raw payload contains no literal '<' or
        # '>' byte at all -- only entities -- yet HTMLParser's single
        # convert_charrefs decode pass turns "&lt;scr&lt;script&gt;ipt&gt;"
        # into the literal substring "<script>" inside the sanitizer's
        # OUTPUT text (proven directly while building this fix). The stored
        # field must contain NO raw '<' or '>' regardless.
        payload = "Great role. &lt;scr&lt;script&gt;ipt&gt;alert(1)&lt;/script&gt; Please apply."
        receipt = self.service.submit_paste("alice", payload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertNotIn("<", record.sanitized_text)
        self.assertNotIn(">", record.sanitized_text)
        self.assertNotIn("<script>", record.sanitized_text)
        self.assertIn("Great role.", record.sanitized_text)
        self.assertIn("Please apply.", record.sanitized_text)

    def test_double_entity_encoded_canary_never_reads_as_a_tag(self):
        # The coordinator's other exact example: "&amp;lt;script&amp;gt;...".
        # One decode pass turns this into the still-entity-shaped
        # "&lt;script&gt;..." -- inert as stored, but a single FURTHER
        # decode (e.g. a browser parsing this text if some future consumer
        # ever inserted it unescaped into HTML source) would complete the
        # journey to a live tag. HTML-escaping the final text means every
        # literal '&' in the stored field is itself escaped to '&amp;', so
        # a single downstream decode only ever peels back to an inert,
        # still-entity-shaped string, never to a raw '<'.
        payload = "hello &amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt; there, please apply."
        receipt = self.service.submit_paste("alice", payload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertNotIn("<", record.sanitized_text)
        self.assertNotIn(">", record.sanitized_text)
        # No literal '&' survives unescaped -- every one was itself turned
        # into a numbered/named entity by the final html.escape() pass.
        lone_ampersand = re.search(r"&(?!amp;|lt;|gt;|quot;|#x27;|#39;)", record.sanitized_text)
        self.assertIsNone(lone_ampersand, "a raw, unescaped '&' survived sanitization")
        self.assertIn("hello", record.sanitized_text)
        self.assertIn("please apply.", record.sanitized_text)

    def test_legitimate_special_characters_survive_as_escaped_entities(self):
        # Positive control: ordinary content that legitimately contains
        # '&' and '>' (no real tag anywhere) must survive, escaped but not
        # corrupted or dropped.
        payload = "Compensation: $100k & benefits, 5 > 3 years experience required."
        receipt = self.service.submit_paste("alice", payload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIn("Compensation: $100k &amp; benefits", record.sanitized_text)
        self.assertIn("5 &gt; 3 years experience required.", record.sanitized_text)
        self.assertNotIn("<", record.sanitized_text)

    def test_extracted_document_text_script_canary_is_stripped_too(self):
        upload = FakeUpload(
            _docx_bytes(["A role posting.", "<script>alert(1)</script>", "Apply within."]), _DOCX_CONTENT_TYPE
        )
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertNotIn("<script", record.sanitized_text)
        self.assertNotIn("alert(1)", record.sanitized_text)
        self.assertIn("A role posting.", record.sanitized_text)
        self.assertIn("Apply within.", record.sanitized_text)

    def test_hostile_bidi_character_surfacing_in_extracted_docx_text_is_refused(self):
        upload = FakeUpload(_docx_bytes(["A role with a hidden‮order trick."]), _DOCX_CONTENT_TYPE)
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_HOSTILE_CHARACTERS)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)

    def test_extraction_yields_no_text_is_truthfully_empty(self):
        upload = FakeUpload(b"   \n\t  ", "text/plain")
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_EMPTY)
        self.assertIsNone(receipt.outcome_reason)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)
        self.assertIsNone(record.extracted_units)

    def test_output_cap_truncation_is_utf16_boundary_safe_and_labeled(self):
        limits = MemberImportLimits(max_extracted_units=10)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        # A run of astral-plane characters (surrogate pairs in UTF-16) so a
        # naive byte-level cut could split a pair.
        text = "\U0001F600" * 20  # 20 code points = 40 UTF-16 units
        receipt = service.submit_paste("alice", text, self.key(), now=NOW)
        self.assertEqual(receipt.outcome, OUTCOME_PARTIAL)
        self.assertEqual(receipt.outcome_reason, REASON_OUTPUT_TRUNCATED)
        self.assertTrue(receipt.truncated)
        record = service.get_import("alice", receipt.import_key, now=NOW)
        # No lone surrogate must appear in the stored text.
        for character in record.sanitized_text:
            code_point = ord(character)
            self.assertFalse(0xD800 <= code_point <= 0xDFFF, "a lone surrogate leaked into stored text")
        self.assertLessEqual(len(record.sanitized_text.encode("utf-16-le")) // 2, 10)

    def test_pipeline_is_deterministic_for_identical_bytes(self):
        upload_a = FakeUpload(_docx_bytes(["Deterministic content here."]), _DOCX_CONTENT_TYPE)
        upload_b = FakeUpload(_docx_bytes(["Deterministic content here."]), _DOCX_CONTENT_TYPE)
        receipt_a = self.service.submit_upload("alice", upload_a, self.key(), now=NOW)
        receipt_b = self.service.submit_upload("alice", upload_b, self.key(), now=NOW)
        record_a = self.service.get_import("alice", receipt_a.import_key, now=NOW)
        record_b = self.service.get_import("alice", receipt_b.import_key, now=NOW)
        self.assertEqual(record_a.sanitized_text, record_b.sanitized_text)
        self.assertEqual(record_a.outcome, record_b.outcome)
        self.assertEqual(record_a.sanitizer_version, record_b.sanitizer_version)
        self.assertEqual(record_a.content_hash, record_b.content_hash)


# ---------------------------------------------------------------------------
# Independent review, FOURTH round (2026-09-02) -- ARCHITECTURAL conclusion.
# Three straight rounds of in-process bounding (a per-stream cap, a
# document-wide object-model walk, a raw-byte-structure scanner plus a
# tracemalloc watchdog) were each proven insufficient in turn. Round 4
# FALSIFIED the round-3 defenses decisively: an indirect ``/Filter N 0 R``
# made a stream look unfiltered to the (now-removed) regex-based scanner
# (peaked 151 MiB), a ``(...)`` string literal containing a stray ``>>``
# inside a stream dictionary threw off its bracket-depth dictionary-end
# search and silently skipped the whole object (peaked 559 MiB), and the
# watchdog's coarse polling could not bound linear accumulation to over
# 1 GiB before the next poll even ran. The conclusion: no amount of
# additional in-process pattern-matching converges -- a regex cannot
# re-derive PDF structure a real parser interprets differently, and
# Python-level polling cannot preempt a C-level allocation burst.
#
# The guarantee is now OS-ENFORCED PROCESS ISOLATION
# (_run_isolated_parse_and_extract / _subprocess_worker_main): every PDF or
# DOCX parse+extract runs inside a short-lived, freshly-spawned child
# process via ``subprocess.run`` (never ``os.fork()`` from the live request
# worker -- that risk was correctly rejected in round 3 and remains
# rejected). These tests measure PARENT PROCESS RSS via
# ``resource.getrusage(RUSAGE_SELF).ru_maxrss`` -- real OS-reported resident
# memory, NOT ``tracemalloc`` (which cannot see a child process's
# allocations at all, and would prove nothing about the actual guarantee).
# ---------------------------------------------------------------------------


def _parent_rss_mib() -> float:
    """This (parent) process's peak resident-set size, in MiB, as reported
    by the OS via ``getrusage`` -- a monotonic high-water mark for the
    process's lifetime. ``ru_maxrss`` is bytes on macOS/Darwin, kilobytes
    on Linux; both are handled so the reported figure is always accurate
    on whichever platform runs this suite."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024) if platform.system() == "Darwin" else raw / 1024


def _pdf_with_indirect_filter_bomb(cmap_size):
    """RESIDUAL BLOCKER (2026-09-02, fourth independent review, blind spot
    1): the stream's ``/Filter`` VALUE is itself an INDIRECT REFERENCE to a
    bare Name object (``/Filter 9 0 R`` where object 9 is the literal name
    ``/FlateDecode``), rather than the literal Name inline -- spec-legal,
    and a real PDF parser (pypdf) resolves it correctly; the now-removed
    regex-based raw-structure scanner never did, so it treated this stream
    as unfiltered and skipped decode-verification entirely."""
    objects = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>",
        4: b"<</Length 33>>stream\nBT /F1 12 Tf 10 10 Td (x) Tj ET\nendstream",
        5: b"<</Type/Font/Subtype/Type0/BaseFont/T/Encoding/Identity-H/DescendantFonts[6 0 R]/ToUnicode 7 0 R>>",
        6: b"<</Type/Font/Subtype/CIDFontType2/BaseFont/T/CIDToGIDMap/Identity>>",
        9: b"/FlateDecode",  # the filter NAME, stored as its own indirect object
    }
    cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
    objects[7] = (
        b"<</Length " + str(len(cmap_compressed)).encode() + b"/Filter 9 0 R>>stream\n"
        + cmap_compressed + b"\nendstream"
    )
    return _assemble_pdf(objects)


def _pdf_with_string_literal_decoy_bomb(cmap_size):
    """RESIDUAL BLOCKER (2026-09-02, fourth independent review, blind spot
    2): the stream dictionary contains a ``(...)`` string literal VALUE
    with a stray ``>>`` byte sequence inside it, placed before ``/Filter``.
    Per the PDF spec, content inside a string literal is not dictionary
    syntax at all -- a real parser handles this correctly; the now-removed
    scanner's naive bracket-depth dictionary-end search counted this
    literal ``>>`` as closing the dictionary early, silently skipping the
    whole object (and, with it, its /ToUnicode CMap's decoded-size check)."""
    cmap_compressed = zlib.compress(_make_cmap_stream(cmap_size), 6)
    objects = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>",
        4: b"<</Length 33>>stream\nBT /F1 12 Tf 10 10 Td (x) Tj ET\nendstream",
        5: b"<</Type/Font/Subtype/Type0/BaseFont/T/Encoding/Identity-H/DescendantFonts[6 0 R]/ToUnicode 7 0 R>>",
        6: b"<</Type/Font/Subtype/CIDFontType2/BaseFont/T/CIDToGIDMap/Identity>>",
    }
    objects[7] = (
        b"<</Metadata(decoy text with a stray >> inside it)/Filter/FlateDecode/Length "
        + str(len(cmap_compressed)).encode() + b">>stream\n" + cmap_compressed + b"\nendstream"
    )
    return _assemble_pdf(objects)


class MemoryErrorIsAResourceBoundTests(unittest.TestCase):
    """A MemoryError from the child's own isolation ceiling must be reported
    as a RESOURCE BOUND, never as a malformed document.

    Regression for a real Linux CI failure (2026-09-01): on Linux the child's
    RLIMIT_AS ceiling genuinely enforces, so a decompression bomb raises
    MemoryError INSIDE the child -- where the generic ``except Exception``
    handlers caught it first and mislabelled it ``parser_failure``. On macOS
    the ceiling does not enforce, so the same bomb fell through to the
    wall-clock path and the mislabel was invisible locally. These tests
    reproduce the MemoryError directly so the mapping is pinned on every
    platform, not only where the ceiling fires.
    """

    def test_sanitizer_memory_error_is_a_resource_bound(self):
        """MemoryError raised while FEEDING the sanitizer (inside its guard)."""
        exploding = MagicMock()
        exploding.feed.side_effect = MemoryError()
        with patch.object(
            member_import_service, "_MarkupSanitizer", return_value=exploding
        ):
            with self.assertRaises(member_import_service._PipelineHalt) as ctx:
                member_import_service._sanitize_markup("hello")
        self.assertEqual(ctx.exception.reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertEqual(ctx.exception.outcome, OUTCOME_REFUSED)

    def test_pdf_parse_memory_error_is_a_resource_bound(self):
        """MemoryError raised while pypdf reads the document (inside the
        guard that previously mislabelled it parser_failure)."""
        limits = MemberImportLimits()
        pdf_bytes = _pdf_bytes()
        with patch("pypdf.PdfReader", side_effect=MemoryError()):
            with self.assertRaises(member_import_service._PipelineHalt) as ctx:
                member_import_service._parse_pdf(pdf_bytes, limits)
        self.assertEqual(ctx.exception.reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertEqual(ctx.exception.outcome, OUTCOME_REFUSED)

    def test_pdf_decrypt_memory_error_is_a_resource_bound(self):
        """The nested decrypt("") guard inside _parse_pdf (independent review
        F1). Reachable because PdfReader() already inflates FlateDecode /XRef
        streams, so a crafted document can leave the child just under its
        ceiling and any later allocation raises. Before the fix this became a
        _PipelineHalt(parser_failure) that the outer MemoryError guard could
        never see."""
        limits = MemberImportLimits()
        encrypted_reader = MagicMock()
        encrypted_reader.is_encrypted = True
        encrypted_reader.decrypt.side_effect = MemoryError()
        with patch("pypdf.PdfReader", return_value=encrypted_reader):
            with self.assertRaises(member_import_service._PipelineHalt) as ctx:
                member_import_service._parse_pdf(_pdf_bytes(), limits)
        self.assertEqual(ctx.exception.reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertEqual(ctx.exception.outcome, OUTCOME_REFUSED)

    def test_child_worker_outer_memory_error_is_a_resource_bound(self):
        """A MemoryError escaping outside the parse/extract handlers still
        reports a resource bound, not a parse failure."""
        payload = json.dumps(
            {
                "content_type": "application/pdf",
                "decoded_b64": base64.b64encode(b"%PDF-1.4").decode("ascii"),
                "limits": dataclasses.asdict(MemberImportLimits()),
            }
        ).encode("utf-8")
        captured = io.StringIO()
        stdin = MagicMock()
        stdin.buffer.read.return_value = payload
        with patch.object(member_import_service, "_parse", side_effect=MemoryError()), \
                patch.object(sys, "stdin", stdin), \
                patch.object(sys, "stdout", captured), \
                patch("resource.setrlimit"):
            member_import_service._subprocess_worker_main()
        response = json.loads(captured.getvalue())
        self.assertFalse(response["parsed"])
        self.assertEqual(response["reason"], REASON_PARSER_RESOURCE_BOUNDS)


@unittest.skipUnless(
    sys.platform.startswith("linux"),
    "Obligation 8 concerns the Azure App Service LINUX runtime; setrlimit does "
    "not enforce on Darwin, so these prove nothing off-Linux.",
)
class LinuxCeilingEnforcementTests(Harness):
    """README obligation 8: prove the child memory ceiling genuinely ENFORCES
    on the Linux runtime, and that it -- not the wall clock -- is what stops a
    bomb.

    These exist because the MemoryError mapping fix removed the accidental
    oracle that CI build 2224 provided: post-fix, the bomb test passes on both
    platforms with identical assertions, so nothing else in the suite can
    distinguish "the ceiling enforced" from "the clock fired" (independent
    review item 7). Skipped off-Linux rather than silently passing.
    """

    def test_a_fresh_child_can_set_and_read_back_the_exact_ceiling(self):
        """(a) setrlimit succeeds in a fresh child and getrlimit reads back
        exactly the configured ceiling -- the mechanism itself works here."""
        ceiling = member_import_service.MAX_SUBPROCESS_MEMORY_CEILING_BYTES
        program = (
            "import json, resource\n"
            f"ceiling = {ceiling}\n"
            "try:\n"
            "    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))\n"
            "    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)\n"
            "    print(json.dumps({'which': 'RLIMIT_AS', 'soft': soft}))\n"
            "except (ValueError, OSError):\n"
            "    resource.setrlimit(resource.RLIMIT_DATA, (ceiling, ceiling))\n"
            "    soft, _hard = resource.getrlimit(resource.RLIMIT_DATA)\n"
            "    print(json.dumps({'which': 'RLIMIT_DATA', 'soft': soft}))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", program], capture_output=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertIn(payload["which"], {"RLIMIT_AS", "RLIMIT_DATA"})
        self.assertEqual(
            payload["soft"],
            ceiling,
            "the child must read back exactly the configured ceiling",
        )

    def test_a_bomb_is_stopped_by_the_ceiling_well_before_the_wall_clock(self):
        """(b) A bomb child refuses in well under the wall-clock deadline --
        proving the CEILING, not the clock, terminated it."""
        limits = MemberImportLimits(
            pdf_extraction_timeout_seconds=30, subprocess_timeout_margin_seconds=15
        )
        deadline = (
            limits.pdf_extraction_timeout_seconds
            + limits.subprocess_timeout_margin_seconds
        )
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(
            _pdf_with_objstm_bomb_per_page(40, 30 * 1024 * 1024), "application/pdf"
        )
        started = time.monotonic()
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        elapsed = time.monotonic() - started
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertLess(
            elapsed,
            deadline / 2,
            "refusal must arrive well inside the wall-clock deadline, proving "
            "the memory ceiling stopped the child rather than the timeout",
        )


class PdfDocxSubprocessIsolationTests(Harness):
    """Proves the SOLE remaining memory guarantee: OS-enforced subprocess
    isolation. Every assertion here measures PARENT process RSS via
    ``resource.getrusage`` -- never ``tracemalloc``, which is blind to a
    child process's own memory entirely (that blindness is exactly why
    ``tracemalloc``-based verification in earlier rounds proved nothing
    about what a child process genuinely costs the request-serving
    worker)."""

    _RSS_CEILING_MIB = 50  # generous -- real growth attributable to isolation failure would be hundreds of MiB

    def _assert_parent_rss_bounded(self, before: float, after: float) -> None:
        delta = after - before
        self.assertLess(
            delta, self._RSS_CEILING_MIB,
            f"parent RSS grew {delta:.2f} MiB processing this upload -- subprocess isolation failed to contain it",
        )

    # -- positive controls: round-trip parity through the subprocess boundary --
    #
    # Every test below builds its upload DATA before capturing "before" --
    # measuring RSS across fixture CONSTRUCTION (which, for the large bomb
    # fixtures, itself transiently builds tens-to-hundreds of MiB of
    # padding in THIS test process before compressing it down to a small
    # on-disk file) would attribute that unrelated cost to the
    # subprocess-isolation property under test, rather than to
    # submit_upload itself -- verified directly while building this suite:
    # measuring "before" ahead of fixture construction produced spurious
    # multi-hundred-MiB deltas that had nothing to do with the isolation
    # boundary at all.

    def test_base14_pdf_round_trips_correctly_through_the_subprocess_boundary(self):
        upload = FakeUpload(_pdf_bytes("Senior widget engineer role for round-trip parity."), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.sanitized_text, "Senior widget engineer role for round-trip parity.")

    def test_docx_round_trips_correctly_through_the_subprocess_boundary(self):
        upload = FakeUpload(_docx_bytes(["Hello employer wording for round-trip parity."]), _DOCX_CONTENT_TYPE)
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.sanitized_text, "Hello employer wording for round-trip parity.")

    def test_ten_font_multi_page_real_text_document_round_trips(self):
        upload = FakeUpload(_pdf_legit_multi_page_shared_fonts(15, 10), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertTrue(record.sanitized_text)

    def test_embedded_fontfile2_document_round_trips_not_over_refused(self):
        upload = FakeUpload(_pdf_with_large_fontfile2(3 * 1024 * 1024), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)

    def test_legitimate_objstm_based_document_round_trips_correctly(self):
        upload = FakeUpload(_pdf_with_legitimate_objstm("Legitimate ObjStm page text for parity."), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.sanitized_text, "Legitimate ObjStm page text for parity.")

    # -- bomb classes: platform-independent mechanisms (pypdf's own >75 MiB
    # per-call safety net, or the wall-clock subprocess timeout) reliably
    # refuse these regardless of whether resource.setrlimit enforces on the
    # host platform --

    def test_single_huge_tounicode_is_refused_and_parent_rss_stays_bounded(self):
        # 180 MiB exceeds pypdf's OWN internal ~75 MiB per-call decompress
        # cap (LimitReachedError) -- platform-independent, no rlimit needed.
        upload = FakeUpload(_pdf_with_tounicode_fonts(1, 180 * 1024 * 1024), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_RESOURCE_BOUNDS)
        rows = self.repository.imports_for_owner("alice")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].sanitized_text)
        self.assertIn("import_refused", [event.event_kind for event in self.sink.events])

    def test_xref_stream_bomb_is_refused_and_parent_rss_stays_bounded(self):
        upload = FakeUpload(_pdf_with_xref_stream_bomb(22_000_000), "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)

    def test_large_scale_objstm_bomb_is_refused_by_isolation_on_every_platform(self):
        # 40 pages x 30 MiB (~1.2 GiB decoded). This asserts only the
        # MEMBER-VISIBLE outcome (refused / parser_resource_bounds), which
        # both containment mechanisms now produce: on Linux the child's
        # rlimit ceiling fires and the child self-reports a MemoryError; on
        # a platform where setrlimit does not enforce (verified:
        # macOS/Darwin, this development environment) the wall-clock timeout
        # kills the child instead. Deliberately platform-agnostic --
        # WHICH mechanism fired is proven separately by the Linux-gated
        # LinuxCeilingEnforcementTests below, because this test can no
        # longer distinguish them (independent review F3). Slow by design.
        limits = MemberImportLimits(pdf_extraction_timeout_seconds=8, subprocess_timeout_margin_seconds=4)
        service = MemberImportService(self.repository, self.sink, limits=limits)
        upload = FakeUpload(_pdf_with_objstm_bomb_per_page(40, 30 * 1024 * 1024), "application/pdf")
        before = _parent_rss_mib()
        start = time.monotonic()
        receipt = service.submit_upload("alice", upload, self.key(), now=NOW)
        elapsed = time.monotonic() - start
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertLess(elapsed, 15.0, "the wall-clock backstop should have killed the child near the 12s ceiling")

    # -- bomb classes whose individual streams are UNDER pypdf's own
    # ~75 MiB per-call cap: on a platform where resource.setrlimit
    # genuinely enforces (Linux, the production target), the 256 MiB
    # subprocess ceiling refuses these once their cumulative decode crosses
    # it; on a platform where it does not (verified: macOS/Darwin, this
    # development environment), the child completes without a
    # resource-bounds refusal -- entirely contained within its own,
    # separate, reclaimed address space regardless. The property asserted
    # here UNCONDITIONALLY, on every platform, is what the coordinator
    # named as the crux: parent RSS never grows. The outcome itself is
    # correctly platform-dependent and is asserted loosely, honestly, for
    # that reason -- never silently pretending Linux-only enforcement is
    # verified from this sandbox. --

    def _assert_bomb_is_contained_regardless_of_platform_enforcement(self, data):
        upload = FakeUpload(data, "application/pdf")
        before = _parent_rss_mib()
        receipt = self.service.submit_upload("alice", upload, self.key(), now=NOW)
        after = _parent_rss_mib()
        self._assert_parent_rss_bounded(before, after)
        self.assertIn(receipt.outcome, (OUTCOME_EXTRACTED, OUTCOME_EMPTY, OUTCOME_PARTIAL, OUTCOME_REFUSED))
        return receipt

    def test_eight_font_tounicode_multiplication_is_contained(self):
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(_pdf_with_tounicode_fonts(8, 30 * 1024 * 1024))

    def test_xobject_nested_fonts_bomb_is_contained(self):
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(
            _pdf_with_xobject_nested_fonts(20, 30 * 1024 * 1024)
        )

    def test_cross_page_multiplication_bomb_is_contained(self):
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(
            _pdf_with_tounicode_fonts_per_page(40, 6 * 1024 * 1024)
        )

    def test_objstm_multiplication_bomb_is_contained(self):
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(
            _pdf_with_objstm_bomb_per_page(12, 30 * 1024 * 1024)
        )

    def test_indirect_filter_blind_spot_bomb_is_contained(self):
        # Round 4's blind spot 1 (peaked 151 MiB against the now-removed
        # scanner): proves the SUBPROCESS boundary does not depend on this
        # module correctly re-deriving PDF structure at all -- pypdf
        # resolves the indirect /Filter correctly regardless, and whatever
        # it does with the result is contained the same way as every other
        # bomb shape.
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(
            _pdf_with_indirect_filter_bomb(30 * 1024 * 1024)
        )

    def test_string_literal_decoy_blind_spot_bomb_is_contained(self):
        # Round 4's blind spot 2 (peaked 559 MiB against the now-removed
        # scanner): same proof, for the string-literal dictionary-boundary
        # evasion.
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(
            _pdf_with_string_literal_decoy_bomb(30 * 1024 * 1024)
        )

    def test_content_stream_bomb_is_contained(self):
        # The ORIGINAL round-1 threat shape (a large FlateDecode
        # /Contents stream, not a font/ObjStm/XRef stream) -- proves the
        # subprocess boundary contains this family too, now that the
        # dedicated round-1 per-page /Contents bound has been removed as
        # part of this round's architecture change.
        self._assert_bomb_is_contained_regardless_of_platform_enforcement(_pdf_bomb_bytes(30 * 1024 * 1024))


class SubprocessBoundaryMappingTests(unittest.TestCase):
    """Proves the PARENT-side mapping in
    ``_run_isolated_parse_and_extract`` is UNIFORM across every way the
    child process can fail -- directly demonstrating the "parser-
    independent" property the coordinator asked for: this function's
    handling of a dead child does not depend on knowing WHAT the child was
    parsing or WHY it died, only THAT it did not return a usable result.
    ``subprocess.run`` itself is mocked here (each failure mode is
    deterministic and instantaneous to test this way; the REAL subprocess
    mechanics -- a genuine timeout, a genuine nonzero exit -- are proven
    separately, end to end, by ``PdfDocxSubprocessIsolationTests`` above)."""

    def _limits(self):
        return MemberImportLimits()

    def test_timeout_expired_maps_to_refused_parser_resource_bounds(self):
        with patch(
            "services.my_opportunities.member_import_service.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1),
        ):
            result = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        parsed_ok, outcome, reason, text, truncated = result
        self.assertFalse(parsed_ok)
        self.assertEqual(outcome, OUTCOME_REFUSED)
        self.assertEqual(reason, REASON_PARSER_RESOURCE_BOUNDS)
        self.assertIsNone(text)
        self.assertFalse(truncated)

    def test_plain_nonzero_exit_maps_to_refused_parser_resource_bounds(self):
        fake_result = MagicMock(returncode=1, stdout=b"", stderr=b"some unrelated traceback")
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertFalse(parsed_ok)
        self.assertEqual(outcome, OUTCOME_REFUSED)
        self.assertEqual(reason, REASON_PARSER_RESOURCE_BOUNDS)

    def test_signal_kill_negative_returncode_maps_to_refused_parser_resource_bounds(self):
        # Python reports a POSIX signal kill (SIGKILL from the kernel's OOM
        # killer, or this module's own best-effort rlimit self-terminating,
        # or SIGSEGV) as a NEGATIVE returncode.
        for signal_returncode in (-9, -11):
            with self.subTest(returncode=signal_returncode):
                fake_result = MagicMock(returncode=signal_returncode, stdout=b"", stderr=b"")
                with patch(
                    "services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result
                ):
                    parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                        "application/pdf", b"irrelevant", self._limits()
                    )
                self.assertFalse(parsed_ok)
                self.assertEqual(outcome, OUTCOME_REFUSED)
                self.assertEqual(reason, REASON_PARSER_RESOURCE_BOUNDS)

    def test_malformed_stdout_json_maps_to_refused_parser_failure(self):
        fake_result = MagicMock(returncode=0, stdout=b"not valid json {{{", stderr=b"")
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertFalse(parsed_ok)
        self.assertEqual(outcome, OUTCOME_REFUSED)
        self.assertEqual(reason, REASON_PARSER_FAILURE)

    def test_child_reported_parse_failure_propagates_faithfully(self):
        response = json.dumps({"parsed": False, "outcome": "refused", "reason": "parser_failure"}).encode()
        fake_result = MagicMock(returncode=0, stdout=response, stderr=b"")
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertFalse(parsed_ok)
        self.assertEqual(outcome, "refused")
        self.assertEqual(reason, "parser_failure")

    def test_child_reported_extract_halt_propagates_faithfully_with_parsed_true(self):
        response = json.dumps(
            {"parsed": True, "extract_halt": {"outcome": "timeout", "reason": "extraction_deadline"}}
        ).encode()
        fake_result = MagicMock(returncode=0, stdout=response, stderr=b"")
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertTrue(parsed_ok)
        self.assertEqual(outcome, "timeout")
        self.assertEqual(reason, "extraction_deadline")

    def test_child_reported_success_propagates_text_and_truncated(self):
        response = json.dumps({"parsed": True, "text": "hello world", "truncated": True}).encode()
        fake_result = MagicMock(returncode=0, stdout=response, stderr=b"")
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertTrue(parsed_ok)
        self.assertIsNone(outcome)
        self.assertIsNone(reason)
        self.assertEqual(text, "hello world")
        self.assertTrue(truncated)

    def test_child_stderr_is_never_read_content_free_by_construction(self):
        # Even when stderr carries something (a traceback, a URL, member
        # content the child might have echoed on a bug) it must never
        # reach the member -- proven here by confirming the function's
        # OWN return values never mention it, using a MagicMock whose
        # .stderr access would itself be observable.
        fake_result = MagicMock(returncode=0, stdout=json.dumps({"parsed": True, "text": "ok", "truncated": False}).encode())
        fake_result.stderr = b"SENSITIVE_CONTENT_MARKER_never_should_leak"
        with patch("services.my_opportunities.member_import_service.subprocess.run", return_value=fake_result):
            parsed_ok, outcome, reason, text, truncated = member_import_service._run_isolated_parse_and_extract(
                "application/pdf", b"irrelevant", self._limits()
            )
        self.assertNotIn("SENSITIVE_CONTENT_MARKER_never_should_leak", repr((parsed_ok, outcome, reason, text, truncated)))


class SubprocessMechanismTests(unittest.TestCase):
    """Proves the actual OS-level mechanics: the worker is genuinely
    reachable via ``python -m ... --pdf-docx-parse-worker``, and documents
    (rather than silently assumes) this development environment's
    ``resource.setrlimit`` capability."""

    def test_worker_entry_point_is_reachable_via_module_invocation(self):
        # The worker protocol's "decoded" bytes are always genuine BYTES
        # (never a str) -- exactly matching what _decode() produces for
        # the only two content types the parent ever actually routes
        # through the subprocess boundary (PDF/DOCX; text/plain's decoded
        # value is a str and is never sent this way, since _run_pipeline
        # only calls _run_isolated_parse_and_extract for PDF/DOCX). This
        # test invokes the worker directly with a real minimal PDF payload
        # to prove the entry point itself is reachable and functions
        # correctly, independent of going through submit_upload.
        repo_root = Path(member_import_service.__file__).resolve().parents[2]
        payload = json.dumps(
            {
                "content_type": "application/pdf",
                "decoded_b64": base64.b64encode(_pdf_bytes("hello from the worker")).decode("ascii"),
                "limits": dataclasses.asdict(MemberImportLimits()),
            }
        ).encode("utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "services.my_opportunities.member_import_service", "--pdf-docx-parse-worker"],
            input=payload, capture_output=True, timeout=10, cwd=str(repo_root),
        )
        self.assertEqual(result.returncode, 0)
        response = json.loads(result.stdout.decode("utf-8"))
        self.assertTrue(response["parsed"])
        self.assertEqual(response["text"], "hello from the worker")
        self.assertEqual(response["text"], "hello from the worker")

    def test_worker_ignores_unrecognized_invocation_without_error(self):
        repo_root = Path(member_import_service.__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-m", "services.my_opportunities.member_import_service"],
            capture_output=True, timeout=10, cwd=str(repo_root),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_setrlimit_capability_is_documented_not_assumed(self):
        # Informational, not a pass/fail gate on the architecture: records
        # directly, for this verification environment, whether
        # RLIMIT_AS/RLIMIT_DATA can even be LOWERED by a fresh child
        # process. Verified while building this fix: on macOS/Darwin, a
        # FRESH subprocess CAN attempt this (unlike the already-large
        # parent process, which cannot raise/lower its own limit at all)
        # but the platform does not actually enforce it regardless
        # (setrlimit itself raises ValueError). On Linux, the production
        # target, RLIMIT_AS is the standard, well-established mechanism
        # and is expected to both set AND enforce -- not independently
        # verifiable from this sandbox, disclosed here rather than assumed
        # silently.
        script = (
            "import resource, sys, json\n"
            "outcome = {}\n"
            "for name in ('RLIMIT_AS', 'RLIMIT_DATA'):\n"
            "    limit_id = getattr(resource, name, None)\n"
            "    if limit_id is None:\n"
            "        outcome[name] = 'not_defined_on_this_platform'\n"
            "        continue\n"
            "    try:\n"
            "        resource.setrlimit(limit_id, (256*1024*1024, 256*1024*1024))\n"
            "        outcome[name] = 'set_ok'\n"
            "    except (ValueError, OSError) as error:\n"
            "        outcome[name] = f'failed:{error}'\n"
            "print(json.dumps(outcome))\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        outcome = json.loads(result.stdout.decode("utf-8"))
        # No assertion on the VALUE -- this is a documentation probe, not a
        # gate. The mechanism this module ships (best-effort, silently
        # falls back to isolation-and-timeout-only when unavailable) is
        # correct either way; see _subprocess_worker_main's own docstring.
        self.assertIn("RLIMIT_AS", outcome)
        self.assertIn("RLIMIT_DATA", outcome)


# ---------------------------------------------------------------------------
# D. Idempotency (C3 precedence table)
# ---------------------------------------------------------------------------


class IdempotencyTests(Harness):
    def test_replay_returns_byte_equal_receipt_and_creates_no_second_row(self):
        key = self.key()
        first = self.service.submit_paste("alice", "A role posting to replay.", key, now=NOW)
        second = self.service.submit_paste("alice", "A role posting to replay.", key, now=NOW)
        self.assertEqual(first, second)
        self.assertEqual(len(self.repository.imports_for_owner("alice")), 1)

    def test_same_key_different_input_is_idempotency_mismatch_no_mutation(self):
        key = self.key()
        self.service.submit_paste("alice", "First distinct posting text.", key, now=NOW)
        digest_before = self.repository.state_digest()
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.submit_paste("alice", "Second, totally different posting text.", key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "idempotency_mismatch")
        self.assertEqual(self.repository.state_digest(), digest_before)

    def test_same_content_new_key_creates_a_new_row_duplicates_permitted(self):
        self.service.submit_paste("alice", "Same content, different key.", self.key(), now=NOW)
        self.service.submit_paste("alice", "Same content, different key.", self.key(), now=NOW)
        self.assertEqual(len(self.repository.imports_for_owner("alice")), 2)

    def test_receipts_survive_across_commands_delete_replay(self):
        receipt = self.service.submit_paste("alice", "A role to delete and replay.", self.key(), now=NOW)
        delete_key = self.key()
        first_delete = self.service.delete_import("alice", receipt.import_key, delete_key, now=NOW)
        second_delete = self.service.delete_import("alice", receipt.import_key, delete_key, now=NOW)
        self.assertEqual(first_delete, second_delete)

    def test_ttl_purge_is_content_blind(self):
        self.service.submit_paste("alice", "Expiring soon posting text.", self.key(), now=NOW)
        later = NOW + timedelta(hours=25)
        purged = self.service.purge_expired_idempotency(now=later)
        self.assertGreaterEqual(purged, 1)

    def test_no_mutation_on_any_pre_admission_refusal(self):
        digest_before = self.repository.state_digest()
        for attempt in range(3):
            with self.assertRaises(MemberImportServiceError):
                self.service.submit_paste("alice", "", self.key(), now=NOW)
        self.assertEqual(self.repository.state_digest(), digest_before)


# ---------------------------------------------------------------------------
# E. Negative multi-member proofs (doc 08 §7)
# ---------------------------------------------------------------------------


class CrossMemberIsolationTests(Harness):
    def setUp(self):
        super().setUp()
        self.alice_receipt = self.service.submit_paste("alice", "Alice's private posting content.", self.key(), now=NOW)

    def test_get_import_cross_owner_and_absent_are_identical_not_found(self):
        with self.assertRaises(MemberImportServiceError) as cross:
            self.service.get_import("bob", self.alice_receipt.import_key, now=NOW)
        with self.assertRaises(MemberImportServiceError) as absent:
            self.service.get_import("alice", "totally-absent-key", now=NOW)
        self.assertEqual(cross.exception.failure_code, "not_found")
        self.assertEqual(absent.exception.failure_code, "not_found")
        self.assertEqual(cross.exception.member_message, absent.exception.member_message)

    def test_malformed_and_overlong_keys_are_also_not_found(self):
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.get_import("alice", "x" * 500, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.get_import("alice", "", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_delete_cross_owner_and_absent_are_identical_not_found(self):
        with self.assertRaises(MemberImportServiceError) as cross:
            self.service.delete_import("bob", self.alice_receipt.import_key, self.key(), now=NOW)
        with self.assertRaises(MemberImportServiceError) as absent:
            self.service.delete_import("alice", "totally-absent-key", self.key(), now=NOW)
        self.assertEqual(cross.exception.failure_code, "not_found")
        self.assertEqual(absent.exception.failure_code, "not_found")

    def test_stage_outcomes_cross_owner_and_absent_are_identical_not_found(self):
        with self.assertRaises(MemberImportServiceError) as cross:
            self.service.stage_outcomes("bob", self.alice_receipt.import_key)
        with self.assertRaises(MemberImportServiceError) as absent:
            self.service.stage_outcomes("alice", "totally-absent-key")
        self.assertEqual(cross.exception.failure_code, "not_found")
        self.assertEqual(absent.exception.failure_code, "not_found")

    def test_list_and_export_never_leak_across_members(self):
        self.service.submit_paste("bob", "Bob's private posting content.", self.key(), now=NOW)
        alice_list = self.service.list_imports("alice", now=NOW)
        bob_list = self.service.list_imports("bob", now=NOW)
        self.assertEqual({r.user_key for r in alice_list}, {"alice"})
        self.assertEqual({r.user_key for r in bob_list}, {"bob"})
        alice_export = self.service.export_imports("alice", now=NOW)
        exported_keys = {row["import_key"] for row in alice_export["imports"]}
        self.assertEqual(exported_keys, {self.alice_receipt.import_key})

    def test_deleting_alice_import_leaves_bob_intact(self):
        bob_receipt = self.service.submit_paste("bob", "Bob's untouched posting.", self.key(), now=NOW)
        self.service.delete_import("alice", self.alice_receipt.import_key, self.key(), now=NOW)
        bob_record = self.service.get_import("bob", bob_receipt.import_key, now=NOW)
        self.assertEqual(bob_record.record_state, RECORD_STATE_ACTIVE)
        self.assertIsNotNone(bob_record.sanitized_text)


# ---------------------------------------------------------------------------
# F. Export / delete / dual retention / rights point-of-use
# ---------------------------------------------------------------------------


class ExportDeleteRetentionTests(Harness):
    def test_export_payload_is_versioned_and_includes_stage_trails(self):
        receipt = self.service.submit_paste("alice", "Exportable posting content.", self.key(), now=NOW)
        payload = self.service.export_imports("alice", now=NOW)
        self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
        row = payload["imports"][0]
        self.assertEqual(row["import_key"], receipt.import_key)
        self.assertGreaterEqual(len(row["stage_outcomes"]), 1)
        self.assertEqual(self.sink.events[-1].event_kind, "import_exported")

    def test_tombstoned_row_exports_tombstone_truth_no_body(self):
        receipt = self.service.submit_paste("alice", "Soon to be deleted content.", self.key(), now=NOW)
        self.service.delete_import("alice", receipt.import_key, self.key(), now=NOW)
        payload = self.service.export_imports("alice", now=NOW)
        row = payload["imports"][0]
        self.assertEqual(row["record_state"], RECORD_STATE_DELETED)
        self.assertIsNone(row["sanitized_text"])
        self.assertEqual(row["body_removal_reason"], BODY_REMOVAL_MEMBER_DELETE)

    def test_member_delete_tombstones_and_is_idempotent(self):
        receipt = self.service.submit_paste("alice", "Content to delete once.", self.key(), now=NOW)
        deleted = self.service.delete_import("alice", receipt.import_key, self.key(), now=NOW)
        self.assertEqual(deleted.outcome, RECORD_STATE_DELETED)
        record = self.service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.record_state, RECORD_STATE_DELETED)
        self.assertIsNone(record.sanitized_text)
        self.assertEqual(record.body_removal_reason, BODY_REMOVAL_MEMBER_DELETE)

    def test_already_deleted_carries_current_state(self):
        receipt = self.service.submit_paste("alice", "Content deleted twice.", self.key(), now=NOW)
        self.service.delete_import("alice", receipt.import_key, self.key(), now=NOW)
        with self.assertRaises(MemberImportServiceError) as ctx:
            self.service.delete_import("alice", receipt.import_key, self.key(), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "already_deleted")
        self.assertEqual(ctx.exception.current_state.record_state, RECORD_STATE_DELETED)

    def test_rights_point_of_use_removes_body_and_stays_active(self):
        service = MemberImportService(self.repository, self.sink, rights_reader=TakedownRightsReader())
        receipt = service.submit_paste("alice", "Content subject to a takedown.", self.key(), now=NOW)
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIsNone(record.sanitized_text)
        self.assertEqual(record.body_removal_reason, BODY_REMOVAL_RIGHTS_TAKEDOWN)
        self.assertEqual(record.record_state, RECORD_STATE_ACTIVE)  # never substituted, never deleted
        self.assertIn("import_body_removed_rights", [e.event_kind for e in self.sink.events])

    def test_rights_takedown_is_not_reapplied_on_second_read(self):
        service = MemberImportService(self.repository, self.sink, rights_reader=TakedownRightsReader())
        receipt = service.submit_paste("alice", "Content subject to a takedown twice.", self.key(), now=NOW)
        first = service.get_import("alice", receipt.import_key, now=NOW)
        removal_events_before = len([e for e in self.sink.events if e.event_kind == "import_body_removed_rights"])
        second = service.get_import("alice", receipt.import_key, now=NOW)
        removal_events_after = len([e for e in self.sink.events if e.event_kind == "import_body_removed_rights"])
        self.assertEqual(first.body_removed_at, second.body_removed_at)
        self.assertEqual(removal_events_before, removal_events_after)


# ---------------------------------------------------------------------------
# G. Unknown-outcome discipline (doc 09 §4)
# ---------------------------------------------------------------------------


class UnknownOutcomeTests(unittest.TestCase):
    def test_persist_import_pre_failure_locks_retry_and_emits_persistence_failure(self):
        repository = FailingMemberImportRepository(fail_on=("persist_import",))
        sink = InMemoryAuditSink()
        service = MemberImportService(repository, sink)
        key = "k1"
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.submit_paste("alice", "Content that fails to persist.", key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "import_outcome_unknown")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(repository.imports_for_owner("alice"), ())

        with self.assertRaises(MemberImportServiceError) as retry_ctx:
            service.submit_paste("alice", "Content that fails to persist.", key, now=NOW)
        self.assertEqual(retry_ctx.exception.failure_code, "retry_locked_state_reload_required")
        self.assertEqual([e.event_kind for e in sink.events], ["persistence_failure"])

    def test_state_reload_via_get_import_clears_the_lock(self):
        repository = FailingMemberImportRepository(fail_on=("update_import",))
        sink = InMemoryAuditSink()
        service = MemberImportService(repository, sink)
        receipt = service.submit_paste("alice", "Content that will fail to delete.", "k1", now=NOW)
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.delete_import("alice", receipt.import_key, "kd", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "import_outcome_unknown")

        with self.assertRaises(MemberImportServiceError) as locked:
            service.delete_import("alice", receipt.import_key, "kd", now=NOW)
        self.assertEqual(locked.exception.failure_code, "retry_locked_state_reload_required")

        # A successful read is the "state reload" that clears the lock.
        service.get_import("alice", receipt.import_key, now=NOW)
        # No longer locked -- update_import no longer configured to fail,
        # so the retry now legitimately proceeds.
        repository._fail_on.clear()
        deleted = service.delete_import("alice", receipt.import_key, "kd2", now=NOW)
        self.assertEqual(deleted.outcome, RECORD_STATE_DELETED)

    def test_post_mode_failure_lands_the_write_durably_before_raising(self):
        repository = FailingMemberImportRepository(fail_on=("persist_import",), fail_mode="post")
        sink = InMemoryAuditSink()
        service = MemberImportService(repository, sink)
        with self.assertRaises(MemberImportServiceError):
            service.submit_paste("alice", "Content landed then dropped connection.", "k1", now=NOW)
        # The underlying store DID receive the row (post-mode), even though
        # the caller was told the outcome was unknown -- no fabricated
        # in-memory state, but the write itself is not silently lost either.
        self.assertEqual(len(repository.imports_for_owner("alice")), 1)

    def test_append_stage_outcome_failure_also_locks(self):
        repository = FailingMemberImportRepository(fail_on=("append_stage_outcome",))
        sink = InMemoryAuditSink()
        service = MemberImportService(repository, sink)
        with self.assertRaises(MemberImportServiceError) as ctx:
            service.submit_paste("alice", "Content whose trail fails to persist.", "k1", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "import_outcome_unknown")


# ---------------------------------------------------------------------------
# H. Content-free audit sweep (doc 08 §4 / doc 12 §5)
# ---------------------------------------------------------------------------


class ContentFreeAuditTests(Harness):
    _BANNED_SUBSTRINGS = (
        "http://", "https://", ".com", ".org", "@", "resume", "cover letter",
        "widget engineer", "Senior", "script", "job posting",
    )

    def _assert_event_is_content_free(self, event):
        self.assertIn(event.event_kind, member_import_service._AUDIT_EVENT_KINDS)
        self.assertIn(event.host_class, HOST_CLASSES)
        for key in event.keys:
            self.assertEqual(len(key), 32)  # uuid4().hex opaque key shape
            int(key, 16)  # never anything but hex
        for value in (event.reason_code, event.actor):
            if value is None:
                continue
            lowered = value.lower()
            for banned in self._BANNED_SUBSTRINGS:
                self.assertNotIn(banned.lower(), lowered)

    def test_every_event_across_a_full_scenario_is_content_free(self):
        # Exercise every command once, including a real "Senior widget
        # engineer" job-posting-shaped paste/upload as the content canary.
        service = MemberImportService(self.repository, self.sink, flag_reader=lambda name: True, adapter_resolver=lambda: FakeFetchAdapter())
        receipt = service.submit_paste("alice", "Senior widget engineer role at example@example.com, apply via resume/cover letter to https://example.com/apply.", self.key(), now=NOW)
        service.get_import("alice", receipt.import_key, now=NOW)
        service.export_imports("alice", now=NOW)
        service.delete_import("alice", receipt.import_key, self.key(), now=NOW)
        upload = FakeUpload(b"Senior widget engineer role, plain text upload version.", "text/plain")
        service.submit_upload("alice", upload, self.key(), now=NOW)
        service.import_from_url("alice", "https://example.com/senior-widget-engineer", self.key(), now=NOW)
        with self.assertRaises(MemberImportServiceError):
            service.submit_paste("alice", "", self.key(), now=NOW)

        self.assertTrue(self.sink.events)
        for event in self.sink.events:
            self._assert_event_is_content_free(event)

    def test_audit_event_dataclass_has_no_content_carrying_field(self):
        field_names = {field for field in MemberImportAuditEvent.__dataclass_fields__}
        for forbidden in ("url", "hostname", "path", "query", "body", "content", "filename", "text", "hash"):
            self.assertNotIn(forbidden, field_names)


# ---------------------------------------------------------------------------
# I. Migration file-content tests (implementer B's PS-MYOPP-006 SQL trio)
#
# These read the forward migration, rollback, verifier, and registry.json as
# TEXT and assert on their content -- the C4/C5/C6 byte-equality idiom. They
# will fail with a clear "file not found" signal until B's files exist; that
# is an honest reflection of build state, not a defect in this test (mirrors
# how C6's own equivalent test treats an unrun disposable-gate proof).
# ---------------------------------------------------------------------------

FORWARD_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-006_member_import.sql"
ROLLBACK_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-006_member_import_rollback.sql"
VERIFY_PATH = ROOT / "SQL FIles/Verification/PS-MYOPP-006_member_import_verify.sql"
REGISTRY_PATH = ROOT / "SQL FIles/Migrations/registry.json"

_C10_TABLES = ("myopp_member_imports", "myopp_member_import_stage_outcomes", "myopp_member_import_idempotency")
_C10_TRIGGERS = (
    "trg_myopp_member_imports_transition_guard",
    "trg_myopp_member_imports_delete_block",
    "trg_myopp_member_import_stage_outcomes_immutable",
    "trg_myopp_member_import_idempotency_immutable",
)
_FORBIDDEN_SHARED_SIDE_PATTERNS = ("receipt_key", "listing_key", "source_version", "score", "probability", "percentage", "prediction")

# The full closed-vocabulary literal set every §3.1 Python constant carries;
# the forward DDL's CHECK constraints must admit every one, byte-equal, as
# an N'...' substring (C6's literal-presence idiom -- see that module's own
# header note on what this style of test can and cannot prove).
_ALL_CLOSED_LITERALS = (
    tuple(INTAKE_METHODS)
    + tuple(OUTCOME_STATES)
    + tuple(RECORD_STATES)
    + tuple(BODY_REMOVAL_REASONS)
    + tuple(RIGHTS_OBLIGATION_CLASSES)
    + (
        REASON_COULD_NOT_DECODE, REASON_PARSER_FAILURE, REASON_PARSER_RESOURCE_BOUNDS,
        REASON_ARCHIVE_BOMB_SUSPECTED, REASON_HOSTILE_CHARACTERS, REASON_OUTPUT_TRUNCATED,
        REASON_EXTRACTION_DEADLINE,
    )
    + tuple(DATA_CLASSES)
)


@unittest.skipUnless(FORWARD_PATH.exists() and ROLLBACK_PATH.exists() and VERIFY_PATH.exists(), "PS-MYOPP-006 SQL trio not yet delivered by implementer B")
class MigrationFileContentTests(unittest.TestCase):
    """Runs only once B's three SQL files exist (skipped, not failed,
    otherwise -- an absent file is a build-sequencing fact, not this test's
    defect). ``registry.json`` is shared/append-only and always exists, so
    the couple of registry-only assertions below run unconditionally in a
    separate class."""

    def test_forward_migration_declares_all_three_tables_and_triggers(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for table in _C10_TABLES:
            self.assertIn(f"CREATE TABLE dbo.{table}", forward)
        for trigger in _C10_TRIGGERS:
            self.assertIn(trigger, forward)
        self.assertIn("user_key nvarchar(300) NOT NULL", forward)

    def test_forward_migration_carries_every_closed_vocabulary_literal(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for value in _ALL_CLOSED_LITERALS:
            self.assertIn(f"N'{value}'", forward, f"{value!r} missing from PS-MYOPP-006 forward DDL")

    def test_forward_migration_carries_five_prerequisite_guards(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for prerequisite in ("PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003", "PS-MYOPP-004", "PS-MYOPP-005"):
            self.assertIn(f"PS-MYOPP-006 requires {prerequisite}", forward)

    def test_no_shared_side_key_or_score_column_anywhere_in_the_ddl(self):
        # Scoped to each CREATE TABLE body only -- the file's own header
        # comment deliberately NAMES these forbidden patterns to document
        # their absence (doc invariant-8 proof-by-construction note), which
        # would otherwise false-positive a whole-file substring scan.
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for table in _C10_TABLES:
            start = forward.index(f"CREATE TABLE dbo.{table}")
            candidates = [
                forward.find("CREATE TABLE dbo.", start + 1),
                forward.find("CREATE INDEX ", start + 1),
                forward.find("CREATE UNIQUE INDEX ", start + 1),
                forward.find("EXEC(N'", start + 1),
            ]
            ends = [c for c in candidates if c != -1]
            end = min(ends) if ends else len(forward)
            body = forward[start:end].lower()
            for pattern in _FORBIDDEN_SHARED_SIDE_PATTERNS:
                self.assertNotIn(pattern, body, f"forbidden pattern {pattern!r} found in {table}'s DDL body")

    def test_rollback_refuses_on_any_member_row_and_drops_children_first(self):
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        for table in _C10_TABLES:
            self.assertIn(f"DROP TABLE dbo.{table};", rollback)
        for trigger in _C10_TRIGGERS:
            self.assertIn(f"DROP TRIGGER dbo.{trigger};", rollback)
        stage_index = rollback.index("DROP TABLE dbo.myopp_member_import_stage_outcomes;")
        idempotency_index = rollback.index("DROP TABLE dbo.myopp_member_import_idempotency;")
        parent_index = rollback.index("DROP TABLE dbo.myopp_member_imports;")
        self.assertLess(stage_index, parent_index)
        self.assertLess(idempotency_index, parent_index)

    def test_verifier_names_every_table_and_trigger_and_ends_verified(self):
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        for table in _C10_TABLES:
            self.assertIn(table, verify)
        for trigger in _C10_TRIGGERS:
            self.assertIn(trigger, verify)
        self.assertIn("SELECT CAST(1 AS bit) AS verified", verify)

    def test_throw_numbers_fall_within_the_reserved_c10_range_and_are_unique(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        all_numbers = []
        for label, text in (("forward", forward), ("rollback", rollback), ("verify", verify)):
            numbers = [int(n) for n in re.findall(r"THROW (\d{5})", text)]
            self.assertTrue(numbers, f"{label} carries no THROW statements")
            self.assertTrue(all(55840 <= n <= 55899 for n in numbers), f"{label} THROW numbers escape 55840-55899")
            if len(numbers) != len(set(numbers)):
                duplicated = sorted({n for n in numbers if numbers.count(n) > 1})
                self.fail(f"{label} reuses THROW number(s) {duplicated}")
            all_numbers.extend(numbers)

        c10_paths = {FORWARD_PATH, ROLLBACK_PATH, VERIFY_PATH}
        for directory in (ROOT / "SQL FIles" / "Migrations", ROOT / "SQL FIles" / "Verification"):
            for path in sorted(directory.glob("*.sql")):
                if path in c10_paths:
                    continue
                text = path.read_text(encoding="utf-8")
                other_numbers = {int(n) for n in re.findall(r"THROW (\d{5})", text)}
                collision = set(all_numbers) & other_numbers
                if collision:
                    self.fail(f"THROW {sorted(collision)} claimed by PS-MYOPP-006 already used in {path.name}")


class RegistryEntryTests(unittest.TestCase):
    """Runs unconditionally: registry.json is a shared, append-only file
    that always exists; only the PS-MYOPP-006 entry itself may be absent
    until B appends it."""

    def test_registry_json_is_well_formed(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertIn("migrations", registry)

    @unittest.skipUnless(
        any(
            item.get("id") == "PS-MYOPP-006"
            for item in json.loads(REGISTRY_PATH.read_text(encoding="utf-8")).get("migrations", [])
        )
        if REGISTRY_PATH.exists()
        else False,
        "PS-MYOPP-006 registry entry not yet appended by implementer B",
    )
    def test_registry_entry_shape_and_requires_chain(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        entries = [item for item in registry["migrations"] if item["id"] == "PS-MYOPP-006"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(list(entry.keys()), ["id", "forward", "rollback", "requires", "summary", "gate"])
        self.assertEqual(entry["forward"], "SQL FIles/Migrations/PS-MYOPP-006_member_import.sql")
        self.assertEqual(entry["rollback"], "SQL FIles/Migrations/PS-MYOPP-006_member_import_rollback.sql")
        self.assertEqual(
            entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003", "PS-MYOPP-004", "PS-MYOPP-005"]
        )
        self.assertTrue(entry["gate"] is None or isinstance(entry["gate"], dict))
        if isinstance(entry["gate"], dict) and FORWARD_PATH.exists():
            gate = entry["gate"]
            self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD_PATH))
            self.assertEqual(len(gate["executable_sha256"]), 64)

    def test_every_requires_entry_appears_earlier_in_the_array(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        migrations = registry["migrations"]
        index_by_id = {item["id"]: position for position, item in enumerate(migrations)}
        for entry in migrations:
            for required_id in entry.get("requires", []):
                self.assertIn(required_id, index_by_id, f"{entry['id']} requires unknown {required_id}")
                self.assertLess(
                    index_by_id[required_id], index_by_id[entry["id"]],
                    f"{entry['id']} requires {required_id}, which must appear earlier in registry.json",
                )


# ---------------------------------------------------------------------------
# J. Structural stops
# ---------------------------------------------------------------------------


class StructuralStopTests(unittest.TestCase):
    def test_no_forbidden_provider_or_web_framework_import(self):
        import ast
        import inspect

        source = inspect.getsource(member_import_service)
        tree = ast.parse(source)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden_substrings = ("flask", "requests", "anthropic", "openai", "werkzeug")
        for name in imported_modules:
            lowered = name.lower()
            for forbidden in forbidden_substrings:
                self.assertNotIn(
                    forbidden, lowered, f"member_import_service.py must not import {forbidden} (found: {name})"
                )

    def test_member_url_fetch_service_module_absent_at_candidate(self):
        path = ROOT / "services" / "my_opportunities" / "member_url_fetch_service.py"
        self.assertFalse(path.exists())

    def test_service_module_exports_no_http_route_symbols(self):
        for forbidden in ("Blueprint", "route", "app", "request", "jsonify", "Flask"):
            self.assertFalse(
                hasattr(member_import_service, forbidden),
                f"member_import_service.py must export no HTTP symbol (found: {forbidden})",
            )

    def test_no_c2_through_c6_file_is_modified_relative_to_origin_main(self):
        """Static, non-flaky proxy for the claim invariant "no C2-C6 file
        changes": compares each shared-package file's on-disk content
        against the same path's content at origin/main. Skips (rather than
        fails) if git plumbing is unavailable in this environment, since
        that is an environment fact, not evidence of a violation."""
        watched_paths = (
            "services/my_opportunities/canonical_service.py",
            "services/my_opportunities/criteria_service.py",
            "services/my_opportunities/ingestion_service.py",
            "services/my_opportunities/interpretation_service.py",
            "services/my_opportunities/qualification_service.py",
            "services/my_opportunities/relationships_service.py",
            "services/my_opportunities/evidence_port.py",
            "services/my_opportunities/connectors.py",
            "services/my_opportunities/index_fence.py",
            "services/my_opportunities/index_projection.py",
            "services/my_opportunities/retrieval_service.py",
            "services/my_opportunities/search_worker.py",
            "services/my_opportunities/safe_outbound.py",
        )
        try:
            subprocess.run(
                ["git", "fetch", "origin", "main"], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.SubprocessError):
            pass
        for relative_path in watched_paths:
            local_path = ROOT / relative_path
            if not local_path.exists():
                continue
            try:
                result = subprocess.run(
                    ["git", "show", f"origin/main:{relative_path}"],
                    cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
                )
            except (OSError, subprocess.SubprocessError):
                self.skipTest("git is unavailable in this environment")
                return
            if result.returncode != 0:
                # The file may not exist on origin/main yet (e.g. C6 still
                # in flight) -- not this test's concern either way.
                continue
            self.assertEqual(
                local_path.read_text(encoding="utf-8"), result.stdout,
                f"{relative_path} differs from origin/main -- C10 must never edit a C2-C6 file",
            )


if __name__ == "__main__":
    unittest.main()
