"""Resume-only literal document reading in a bounded, local child process.

The shared opportunity reader keeps its own contract. This reader retains
literal resume text, accounts for every PDF page, and optionally reads printed
English scans using an explicitly pinned local runtime. OCR is evidence for
member review, never proof that a character or assertion is correct.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import zlib


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
OCR_KEYS = {"schema_version", "runtime_root", "tesseract", "tessdata", "renderer",
            "renderer_version", "files_sha256"}
OCR_MAX_PAGES = 10
OCR_PAGE_SECONDS = 20
OCR_TOTAL_SECONDS = 180
OCR_PAGE_PIXELS = 12_000_000
OCR_TOTAL_PIXELS = 100_000_000
TEMP_BYTES = 32 * 1024 * 1024
_WORKERS = threading.BoundedSemaphore(2)
_BIDI = frozenset(chr(n) for n in (*range(0x202A, 0x202F), *range(0x2066, 0x206A)))


class ResumeDocumentReadError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _ordinary_path(value, *, directory=False):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ResumeDocumentReadError("ocr_configuration_invalid")
    path = Path(value)
    # A resolved symlink/reparse path must not silently become an allowed file.
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ResumeDocumentReadError("ocr_configuration_invalid")
    if directory and not path.is_dir() or not directory and not path.is_file():
        raise ResumeDocumentReadError("ocr_configuration_invalid")
    return path.resolve()


def _closed_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ResumeDocumentReadError("ocr_configuration_invalid")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)


def load_ocr_configuration(configuration):
    """Validate the seven-key ordinary-file manifest and every pinned file.

    The manifest path is supplied by reviewed private runtime wiring. There is
    no PATH lookup, download, package installation, or fallback engine.
    """
    try:
        manifest = _ordinary_path(configuration)
        if manifest.stat().st_size > 512_000:
            raise ResumeDocumentReadError("ocr_configuration_invalid")
        raw = manifest.read_bytes()
        settings = _closed_json(raw)
        if (not isinstance(settings, dict) or set(settings) != OCR_KEYS
                or type(settings["schema_version"]) is not int
                or settings["schema_version"] != 1
                or settings["renderer"] != "pypdfium2"
                or not re.fullmatch(r"\d+\.\d+\.\d+", str(settings["renderer_version"]))):
            raise ResumeDocumentReadError("ocr_configuration_invalid")
        root = _ordinary_path(settings["runtime_root"], directory=True)
        tessdata = _ordinary_path(settings["tessdata"], directory=True)
        executable = _ordinary_path(settings["tesseract"])
        files = settings["files_sha256"]
        if not isinstance(files, dict) or not 4 <= len(files) <= 2000:
            raise ResumeDocumentReadError("ocr_configuration_invalid")
        admitted = set()
        for filename, expected in files.items():
            path = _ordinary_path(filename)
            if not path.is_relative_to(root) or not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
                raise ResumeDocumentReadError("ocr_configuration_invalid")
            if path.stat().st_size > 100 * 1024 * 1024:
                raise ResumeDocumentReadError("ocr_configuration_invalid")
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                raise ResumeDocumentReadError("ocr_dependency_changed")
            admitted.add(path)
        required = {executable, tessdata / "eng.traineddata", tessdata / "osd.traineddata"}
        package_root = root / "python-packages"
        if not required <= admitted or not tessdata.is_relative_to(root):
            raise ResumeDocumentReadError("ocr_configuration_invalid")
        # Entire import and executable dependency directories are pinned, not
        # just their entrypoints. Ignored bytecode may never supply an import.
        for directory in (executable.parent, package_root):
            _ordinary_path(str(directory), directory=True)
            for path in directory.rglob("*"):
                if path.is_dir():
                    _ordinary_path(str(path), directory=True)
                elif _ordinary_path(str(path)) not in admitted:
                    raise ResumeDocumentReadError("ocr_dependency_unpinned")
        for package in ("pypdfium2", "pypdfium2_raw"):
            if package_root / package / "__init__.py" not in admitted:
                raise ResumeDocumentReadError("ocr_configuration_invalid")
        return {"settings": settings, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "package_root": str(package_root)}
    except ResumeDocumentReadError:
        raise
    except (OSError, ValueError, TypeError):
        raise ResumeDocumentReadError("ocr_configuration_invalid") from None


def _literal_text(text):
    if any(ch in _BIDI or unicodedata.category(ch) == "Cc" and ch not in "\n\r\t" for ch in text):
        raise ResumeDocumentReadError("hostile_characters")
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


_SECTION_NAMES = {
    "experience": "Experience", "work experience": "Experience", "employment": "Experience",
    "professional experience": "Experience", "education": "Education", "qualifications": "Qualifications",
    "credentials": "Credentials", "certifications": "Credentials", "licenses": "Credentials",
    "technical strengths": "Skills", "technical skills": "Skills", "skills": "Skills", "strengths": "Skills",
    "awards": "Awards", "awards and recognition": "Awards", "my story": "My Story",
    "personal story": "My Story", "professional summary": "Professional summary", "summary": "Professional summary",
    "professional qualifications": "Qualifications", "key qualifications": "Qualifications",
    "contact details": "Contact details", "contact": "Contact details",
    "independent project": "Independent Project", "independent projects": "Independent Project",
}


def inventory_source(text, *, pages=None, document=False):
    """Account for every nonblank source span; infer no biographical assertion.

    IDs bind offsets and exact text. Repeated wording has separate identities.
    Headings remain structural evidence. Wrapped paragraphs retain their exact
    original span rather than inventing a new source quote.
    """
    rows, offset, section = [], 0, None
    has_resume_heading = any(line.strip().strip(":").casefold() in _SECTION_NAMES for line in text.splitlines()[:10])
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        start = offset + len(line) - len(line.lstrip())
        end = offset + len(line.rstrip())
        offset += len(line)
        if not stripped:
            continue
        heading = _SECTION_NAMES.get(stripped.strip(":").casefold())
        if heading:
            section = heading
        # Continuations are only joined within one paragraph. A line that
        # begins a bullet, date/header, or heading remains independently bound.
        continuation = (rows and not heading and rows[-1]["kind"] == "content"
                        and rows[-1]["section"] == section
                        and start - rows[-1]["span_end"] <= 2
                        and not re.match(r"[•*\-]|\d+[.)]", stripped)
                        and not rows[-1]["text"].rstrip().endswith((".", ";", ":", "!", "?")))
        if continuation:
            row = rows[-1]
            row["span_end"] = end
            row["text"] = text[row["span_start"]:end]
        else:
            instruction = bool(re.search(r"(?:ignore (?:all |the |previous )?(?:instructions|rules)|^system:|^assistant:|^publish (?:everything|this)|send (?:all |the )?(?:password|credentials))", stripped, re.I))
            kind = ("heading" if heading else "untrusted_instruction" if instruction else
                    "presentation" if document and not rows and has_resume_heading else "content")
            row = {"kind": kind, "section": section,
                   "span_start": start, "span_end": end, "text": text[start:end]}
            rows.append(row)
    for row in rows:
        identity = f'{row["span_start"]}:{row["span_end"]}:{row["text"]}'
        row["unit_id"] = "unit-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        row["disposition"] = "structural" if row["kind"] in {"heading", "presentation"} else "unresolved"
        row["page"] = next((p["page"] for p in pages or []
                            if p.get("span_start", -1) <= row["span_start"] < p.get("span_end", -1)), None)
    return rows


class ResumeOnboardingDocumentReader:
    def __init__(self, configuration=None):
        # Capture once, after reviewed runtime wiring has supplied the env.
        self.configuration = configuration if configuration is not None else os.environ.get("PEERSLATE_RESUME_OCR_CONFIGURATION")
        self.ocr = load_ocr_configuration(self.configuration) if self.configuration else None

    def read(self, content_type, data, *, limits):
        if content_type not in {"application/pdf", DOCX, "text/plain"}:
            raise ResumeDocumentReadError("unsupported_type")
        if not isinstance(data, bytes) or not data or len(data) > limits.max_upload_bytes:
            raise ResumeDocumentReadError("too_large")
        if not _WORKERS.acquire(blocking=False):
            raise ResumeDocumentReadError("parser_busy")
        try:
            # Reverify pins for every invocation; a changed file must not use
            # the previously captured manifest to gain permission to execute.
            ocr = load_ocr_configuration(self.configuration) if self.ocr else None
            if ocr and ocr["manifest_sha256"] != self.ocr["manifest_sha256"]:
                raise ResumeDocumentReadError("ocr_dependency_changed")
            with tempfile.TemporaryDirectory(prefix="peerslate-resume-read-") as temporary:
                root = Path(temporary)
                (root / "source.bin").write_bytes(data)
                names = ("max_extracted_units", "max_pdf_pages", "max_subprocess_memory_ceiling_bytes",
                         "max_docx_entries", "max_docx_entry_uncompressed_bytes", "max_docx_document_xml_bytes",
                         "max_docx_total_uncompressed_bytes", "max_docx_entry_compression_ratio")
                command = {"content_type": content_type, "limits": {name: getattr(limits, name) for name in names},
                           "ocr": ocr, "root": str(root)}
                (root / "request.json").write_text(json.dumps(command), encoding="utf-8")
                timeout = OCR_TOTAL_SECONDS if ocr and content_type == "application/pdf" else (
                    limits.pdf_extraction_timeout_seconds + limits.subprocess_timeout_margin_seconds)
                _run_bounded_child([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                                    "--child", str(root / "request.json")], root, timeout)
                result_path = root / "result.json"
                if not result_path.is_file() or result_path.stat().st_size > TEMP_BYTES:
                    raise ResumeDocumentReadError("parser_resource_bounds")
                result = json.loads(result_path.read_text(encoding="utf-8"))
                if result.get("error"):
                    raise ResumeDocumentReadError(result["error"])
                text = result.get("text")
                if not isinstance(text, str):
                    raise ResumeDocumentReadError("parser_failure")
                result["units"] = inventory_source(text, pages=result["pages"], document=True)
                result["ocr_configuration_sha256"] = self.ocr["manifest_sha256"] if self.ocr else None
                return result
        finally:
            _WORKERS.release()


def _run_bounded_child(arguments, root, timeout):
    # Logs are private bounded files, never PIPE buffers holding arbitrary
    # provider/document output in the request worker's memory.
    with (root / "worker.log").open("wb") as log:
        process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=log, shell=False, cwd=root,
                                   start_new_session=os.name != "nt")
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    _kill_reader(process)
                    raise ResumeDocumentReadError("extraction_deadline")
                output_size = sum(p.stat().st_size for p in root.iterdir()
                                  if p.is_file() and p.name not in {"source.bin", "request.json"})
                if output_size > TEMP_BYTES:
                    _kill_reader(process)
                    raise ResumeDocumentReadError("parser_resource_bounds")
                try:
                    process.wait(timeout=min(.1, max(.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
        finally:
            # On Windows the child's own kill-on-close job terminates its OCR
            # descendants when Python exits or is killed. POSIX needs the
            # process group cleaned even when the leader already exited.
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                _kill_reader(process)
        if (root / "worker.log").stat().st_size > TEMP_BYTES:
            raise ResumeDocumentReadError("parser_resource_bounds")
        if process.returncode != 0:
            raise ResumeDocumentReadError("parser_resource_bounds" if process.returncode < 0 else "parser_failure")


def _kill_reader(process):
    if os.name == "nt":
        process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def _child_memory_boundary(maximum):
    """Set process/tree lifetime and memory bounds before untrusted parsing."""
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
        resource.setrlimit(resource.RLIMIT_FSIZE, (TEMP_BYTES, TEMP_BYTES))
        return None
    import ctypes
    from ctypes import wintypes
    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", wintypes.DWORD), ("minimum", ctypes.c_size_t), ("maximum", ctypes.c_size_t),
                    ("active", wintypes.DWORD), ("affinity", ctypes.c_size_t),
                    ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    bounds = Extended()
    # PROCESS_MEMORY, JOB_MEMORY and KILL_ON_JOB_CLOSE. Assignment occurs
    # before PDFium imports or subprocess creation, eliminating the child race.
    bounds.basic.flags = 0x100 | 0x200 | 0x2000
    bounds.process_memory = maximum
    bounds.job_memory = maximum
    if (not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(bounds), ctypes.sizeof(bounds))
            or not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess())):
        if handle:
            kernel.CloseHandle(handle)
        raise ResumeDocumentReadError("parser_resource_bounds")
    # Keep this handle alive through process exit. Closing it while Python is
    # still returning would terminate Python as another job member.
    return handle


def _png_rgb(bitmap):
    width, height, stride = bitmap.width, bitmap.height, bitmap.stride
    if bitmap.n_channels != 3 or width * height > OCR_PAGE_PIXELS:
        raise ResumeDocumentReadError("ocr_resource_bounds")
    raw = bytes(bitmap.buffer)
    rows = b"".join(b"\0" + raw[y * stride:y * stride + width * 3] for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def _tesseract(executable, tessdata, image, *, mode, timeout):
    arguments = [executable, str(image), "stdout", "--tessdata-dir", tessdata,
                 "-l", "osd" if mode == "orientation" else "eng", "--psm", "0" if mode == "orientation" else "3"]
    if mode != "orientation":
        arguments.append("tsv")
    process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, shell=False)
    output, errors = bytearray(), []
    def drain():
        try:
            while chunk := process.stdout.read(65536):
                if len(output) + len(chunk) > TEMP_BYTES:
                    errors.append("ocr_resource_bounds")
                    process.kill()
                    return
                output.extend(chunk)
        except OSError:
            errors.append("ocr_unreadable")
    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        errors.append("ocr_deadline")
    finally:
        process.wait(timeout=10)
        thread.join(timeout=5)
        process.stdout.close()
    if thread.is_alive():
        raise ResumeDocumentReadError("ocr_deadline")
    if errors:
        raise ResumeDocumentReadError(errors[0])
    if process.returncode or not output:
        if mode == "orientation":
            return None  # Sparse text may lack orientation evidence; no guess.
        raise ResumeDocumentReadError("ocr_unreadable")
    return output.decode("utf-8", errors="strict")


def _ocr_page(pdfium, page, number, settings, root, total_pixels):
    deadline = time.monotonic() + OCR_PAGE_SECONDS
    rotation = 0
    def render(rotation):
        width, height = page.get_size()
        pixels = math.ceil(width * 300 / 72) * math.ceil(height * 300 / 72)
        if pixels > OCR_PAGE_PIXELS or total_pixels + pixels > OCR_TOTAL_PIXELS:
            raise ResumeDocumentReadError("ocr_resource_bounds")
        return page.render(scale=300 / 72, rotation=rotation,
                           force_bitmap_format=pdfium.raw.FPDFBitmap_BGR, rev_byteorder=True), pixels
    bitmap, pixels = render(0)
    try:
        image = root / "page.png"
        encoded = _png_rgb(bitmap)
        if len(encoded) > TEMP_BYTES:
            raise ResumeDocumentReadError("ocr_resource_bounds")
        image.write_bytes(encoded)
    finally:
        bitmap.close()
    orientation = _tesseract(settings["tesseract"], settings["tessdata"], image,
                            mode="orientation", timeout=max(.1, deadline - time.monotonic()))
    if orientation:
        match = re.search(r"Rotate: (0|90|180|270)\b", orientation)
        rotation = int(match.group(1)) if match else 0
    if rotation:
        bitmap, _ = render(rotation)
        try:
            image.write_bytes(_png_rgb(bitmap))
        finally:
            bitmap.close()
    tsv = _tesseract(settings["tesseract"], settings["tessdata"], image,
                    mode="text", timeout=max(.1, deadline - time.monotonic()))
    tokens, lines = [], {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if row.get("level") != "5" or not row.get("text", "").strip():
            continue
        confidence = float(row["conf"])
        token = {"text": row["text"], "confidence": confidence,
                 "box": [int(row[k]) for k in ("left", "top", "width", "height")]}
        tokens.append(token)
        key = tuple(int(row[k]) for k in ("block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(token["text"])
    if not tokens:
        raise ResumeDocumentReadError("ocr_unreadable")
    text = "\n".join(" ".join(words) for words in lines.values())
    for filename in ("page.png", "orientation.osd", "text.tsv"):
        path = root / filename
        if path.exists():
            path.unlink()
    return text, {"method": "ocr", "rotation": rotation, "tokens": tokens,
                  "review_required": True, "low_confidence": any(t["confidence"] < 85 for t in tokens)}, pixels


_DATE_RUN = re.compile(r"(?:19|20)\d\d|present|current", re.I)


def _is_column_layout(fragments, width):
    """True only for a real second column, not for right-aligned dates.

    A column's lines all start at one x. A right-aligned date shares its row with the
    left text and starts wherever its width puts it, so dates and the continuation runs
    of long lines never line up. Short date-like runs are ignored; at least three
    right-hand rows must then start at one x for the page to count as two columns.
    """
    rows = {}
    for x, y, text in fragments:
        rows.setdefault(round(y / 3), []).append((x, text))
    starts = []
    for row in rows.values():
        right = [x for x, text in row
                 if x > width * .52 and not (len(text.strip()) <= 30 and _DATE_RUN.search(text))]
        if right:
            starts.append(min(right))
    if len([f for f in fragments if f[0] < width * .45]) < 3 or len(starts) < 3:
        return False
    ordered = sorted(starts)
    anchor = ordered[len(ordered) // 2]
    return sum(1 for x in starts if abs(x - anchor) <= width * .02) >= .6 * len(starts)


def _pdf_text_page(page):
    # pypdf's content-stream reading preserves whole columns when authored in
    # that order. Visitor positions let common two-column layouts authored
    # row-first keep their complete records together; a single column with
    # right-aligned dates keeps every date on the line of its title.
    fragments = []
    def visitor(text, cm, tm, font, size):
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            fragments.append((x, y, text))
    original = page.extract_text(visitor_text=visitor) or ""
    width = float(page.mediabox.width)
    if _is_column_layout(fragments, width):
        groups = ([f for f in fragments if f[0] <= width * .5],
                  [f for f in fragments if f[0] > width * .5])
        return "\n".join(f[2].rstrip() for group in groups for f in sorted(group, key=lambda f: -f[1]))
    return original


def _read_pdf(data, limits, ocr, root):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ResumeDocumentReadError("encrypted_document")
    if not 0 < len(reader.pages) <= limits["max_pdf_pages"]:
        raise ResumeDocumentReadError("parser_resource_bounds")
    pdfium_document, pdfium, total_pixels, scan_pages = None, None, 0, 0
    chunks, metadata, offset = [], [], 0
    try:
        for number, page in enumerate(reader.pages, 1):
            text = _literal_text(_pdf_text_page(page))
            details = {"method": "selectable", "review_required": False}
            # An image-only page in a hybrid document must not be silently
            # omitted because a different page contains selectable text.
            meaningful_image = any(float(image.get("/Width", 0)) * float(image.get("/Height", 0)) > 100_000
                                   for image in (page.get("/Resources", {}).get("/XObject", {}) or {}).values()
                                   if hasattr(image.get_object(), "get")
                                   for image in [image.get_object()])
            if not text or meaningful_image and len(text) < 100:
                scan_pages += 1
                if ocr is None:
                    details = {"method": "unreadable", "reason": "ocr_unavailable", "review_required": True}
                else:
                    if scan_pages > OCR_MAX_PAGES:
                        raise ResumeDocumentReadError("ocr_resource_bounds")
                    if pdfium is None:
                        sys.path.insert(0, ocr["package_root"])
                        import pypdfium2 as pdfium
                        if str(pdfium.PYPDFIUM_INFO.version) != ocr["settings"]["renderer_version"]:
                            raise ResumeDocumentReadError("ocr_dependency_changed")
                        pdfium_document = pdfium.PdfDocument(data)
                    pdfium_page = pdfium_document[number - 1]
                    try:
                        text, details, pixels = _ocr_page(pdfium, pdfium_page, number, ocr["settings"], root, total_pixels)
                        total_pixels += pixels
                    finally:
                        pdfium_page.close()
            elif meaningful_image:
                # Selectable text on a page does not establish that a separate
                # embedded image contains no further resume content. Preserve
                # the literal text and expose the unresolved image for review.
                details.update({"complete": False, "reason": "embedded_content_unreadable", "review_required": True})
            text = _literal_text(text)
            start = offset
            if chunks:
                offset += 2
                start = offset
            chunks.append(text)
            offset += len(text)
            metadata.append({"page": number, "span_start": start, "span_end": offset, **details})
        return "\n\n".join(chunks), metadata
    finally:
        if pdfium_document is not None:
            pdfium_document.close()


def _read_docx(data, limits):
    import zipfile
    from xml.etree import ElementTree
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len({entry.filename for entry in entries}) != len(entries):
            raise ResumeDocumentReadError("parser_failure")
        if len(entries) > limits["max_docx_entries"] or sum(e.file_size for e in entries) > limits["max_docx_total_uncompressed_bytes"]:
            raise ResumeDocumentReadError("archive_bomb_suspected")
        for entry in entries:
            if (entry.file_size > limits["max_docx_entry_uncompressed_bytes"]
                    or entry.file_size / max(1, entry.compress_size) > limits["max_docx_entry_compression_ratio"]
                    or entry.flag_bits & 1):
                raise ResumeDocumentReadError("archive_bomb_suspected")
        names = ["word/document.xml"] + sorted(entry.filename for entry in entries
                 if re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml", entry.filename))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        lines, unreadable = [], False
        for name in names:
            info = archive.getinfo(name)
            if info.file_size > limits["max_docx_document_xml_bytes"]:
                raise ResumeDocumentReadError("archive_bomb_suspected")
            document = archive.read(info)
            if re.search(br"<!\s*(DOCTYPE|ENTITY)", document, re.I):
                raise ResumeDocumentReadError("parser_failure")
            root = ElementTree.fromstring(document)
            unreadable = unreadable or any(item.tag in {ns + "altChunk", ns + "drawing", ns + "pict"} for item in root.iter())
            for paragraph in root.iter(ns + "p"):
                parts = []
                for item in paragraph.iter():
                    if item.tag == ns + "t":
                        parts.append(item.text or "")
                    elif item.tag in {ns + "br", ns + "cr"}:
                        parts.append("\n")
                    elif item.tag == ns + "tab":
                        parts.append("\t")
                lines.append("".join(parts))
    return "\n".join(lines), unreadable


def _child(request_path):
    command = json.loads(Path(request_path).read_text(encoding="utf-8"))
    root, limits = Path(command["root"]), command["limits"]
    _job_handle = _child_memory_boundary(limits["max_subprocess_memory_ceiling_bytes"])
    try:
        reason = None
        data = (root / "source.bin").read_bytes()
        if command["content_type"] == "application/pdf":
            text, pages = _read_pdf(data, limits, command["ocr"], root)
        else:
            if command["content_type"] == DOCX:
                text, unreadable = _read_docx(data, limits)
                reason = "embedded_content_unreadable" if unreadable else None
            else:
                text = data.decode("utf-8-sig", errors="strict")
            text = _literal_text(text)
            pages = [{"page": None, "part": "document-text", "span_start": 0, "span_end": len(text), "method": "literal", "review_required": False}]
        text = _literal_text(text)
        if len(text.encode("utf-16-le")) // 2 > limits["max_extracted_units"]:
            raise ResumeDocumentReadError("output_truncated")
        reason = reason or next((p.get("reason") for p in pages if p.get("complete") is False), None)
        complete = bool(text) and not reason and all(p["method"] != "unreadable" for p in pages)
        result = {"text": text, "pages": pages, "complete": complete,
                  "outcome": "extracted" if complete else "partial" if text else "empty",
                  "reason": None if complete else reason or ("ocr_unavailable" if any(p["method"] == "unreadable" for p in pages) else "empty")}
    except ResumeDocumentReadError as error:
        result = {"error": error.code}
    except (MemoryError, OSError):
        result = {"error": "parser_resource_bounds"}
    except Exception:
        result = {"error": "parser_failure"}
    (root / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    # _job_handle is intentionally held until operating-system process exit.


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--child":
    _child(sys.argv[2])
