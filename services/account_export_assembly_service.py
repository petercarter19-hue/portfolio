"""Deterministic ZIP assembly for the account export archive.

Implements C0's archive and consistency contract
(docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md,
"Archive and consistency contract") against an injected iterable of
already-shaped domain files. This service is, and remains, completely
agnostic to where those files came from: it never imports a database or
storage module, performs no I/O of its own, and holds no state. Every
domain file it has ever been exercised against in this package's own
tests (tests/test_account_export_assembly.py) is a hand-built, obvious
fixture; PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001 separately
wired scripts/run_account_export_worker.py's real content source
(services/account_export_domain_readers.py's DOMAINS registry) as one
possible caller of this exact, unchanged assemble() contract -- this
module itself did not need to start reading a live table to support
that; it only needed to accept one legitimate shape its caller now also
produces: an "included" file whose content is empty bytes, for a real
domain a real member genuinely has zero rows in (see
_validate_domain_file's own comment below).

Determinism: two calls with identical input always produce a
byte-identical archive. That requires pinning everything a naive ZIP
write would otherwise let vary between runs or hosts -- entry order
(manifest.json first, then every included domain file in ascending
path order), each entry's ZipInfo (a fixed 1980-01-01 DOS timestamp
instead of wall-clock time, a fixed create_system instead of the
build host's platform, a pinned external_attr), a fixed compression
method, and manifest.json's own JSON encoding (fixed key order, no
extra whitespace, UTF-8).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile


MAX_COMPRESSED_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024

MANIFEST_FORMAT = "peerslate.account.export"
MANIFEST_SCHEMA_VERSION = 1
MANIFEST_PATH = "manifest.json"

_DISPOSITIONS = ("included", "excluded", "unavailable")

# The ZIP format's own epoch, used in place of wall-clock time so the
# archive never encodes when it happened to be built.
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
_FIXED_CREATE_SYSTEM = 0  # MS-DOS/FAT, regardless of the build host's platform


class AccountExportAssemblyError(RuntimeError):
    """A stable assembly outcome. Never carries member content."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require_non_empty_str(value, code):
    if not isinstance(value, str) or not value.strip():
        raise AccountExportAssemblyError(code)
    return value


def _require_optional_str(value, code):
    if value is not None and not isinstance(value, str):
        raise AccountExportAssemblyError(code)
    return value


def _validate_domain_file(entry):
    """Enforce the same disposition-shape discipline C1's
    CK_account_export_job_domains_shape enforces at the schema level:
    included carries every read fact and no reason; excluded carries
    only omission_reason; unavailable carries exactly one of
    omission_reason or failure_reason, never both.
    """

    if not isinstance(entry, dict):
        raise AccountExportAssemblyError("invalid_domain_input")

    path = entry.get("path")
    domain_code = entry.get("domain_code")
    schema_id = entry.get("schema_id")
    schema_version = entry.get("schema_version")
    disposition = entry.get("disposition")

    _require_non_empty_str(path, "invalid_domain_input")
    _require_non_empty_str(domain_code, "invalid_domain_input")
    _require_non_empty_str(schema_id, "invalid_domain_input")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version <= 0
    ):
        raise AccountExportAssemblyError("invalid_domain_input")
    if disposition not in _DISPOSITIONS:
        raise AccountExportAssemblyError("invalid_domain_input")
    if path.startswith("/") or ".." in path.split("/") or path == MANIFEST_PATH:
        raise AccountExportAssemblyError("invalid_domain_input")

    content = entry.get("content")
    record_count = entry.get("record_count")
    omission_reason = entry.get("omission_reason")
    failure_reason = entry.get("failure_reason")

    if disposition == "included":
        # Empty bytes ARE valid: a real domain reader can truthfully
        # find zero rows for a genuine member (e.g. a member who never
        # created a Capture) -- that is an honest "included, 0 records"
        # fact, not an error. services/account_export_domain_readers.py's
        # own module docstring already anticipates this exact case (its
        # "genuinely empty domain for a real owner" read-window
        # fallback). Only the TYPE is enforced here; emptiness is not.
        # PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001 relaxed this
        # from an earlier `or not content` check, which rejected exactly
        # this legitimate, now-reachable case.
        if not isinstance(content, bytes):
            raise AccountExportAssemblyError("invalid_domain_input")
        if (
            not isinstance(record_count, int)
            or isinstance(record_count, bool)
            or record_count < 0
        ):
            raise AccountExportAssemblyError("invalid_domain_input")
        if omission_reason is not None or failure_reason is not None:
            raise AccountExportAssemblyError("invalid_domain_input")
    elif disposition == "excluded":
        if content is not None or record_count is not None or failure_reason is not None:
            raise AccountExportAssemblyError("invalid_domain_input")
        _require_non_empty_str(omission_reason, "invalid_domain_input")
    else:  # unavailable
        if content is not None or record_count is not None:
            raise AccountExportAssemblyError("invalid_domain_input")
        has_omission = bool(omission_reason)
        has_failure = bool(failure_reason)
        if has_omission == has_failure:  # neither, or both: exactly one is required
            raise AccountExportAssemblyError("invalid_domain_input")

    _require_optional_str(omission_reason, "invalid_domain_input")
    _require_optional_str(failure_reason, "invalid_domain_input")

    provenance = entry.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise AccountExportAssemblyError("invalid_domain_input")

    read_window = entry.get("read_window")
    if read_window is not None:
        if (
            not isinstance(read_window, dict)
            or not isinstance(read_window.get("started_at_utc"), str)
            or not isinstance(read_window.get("ended_at_utc"), str)
        ):
            raise AccountExportAssemblyError("invalid_domain_input")
    if disposition != "included" and read_window is not None:
        raise AccountExportAssemblyError("invalid_domain_input")

    return entry


def _write_fixed_entry(archive, path, data):
    """Write one ZIP member with every incidental, non-content field
    pinned so that identical input produces a byte-identical archive
    across runs and hosts."""

    info = zipfile.ZipInfo(filename=path, date_time=_FIXED_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = _FIXED_CREATE_SYSTEM
    # NOT zero: zipfile.ZipFile._open_to_write silently substitutes
    # 0o600 << 16 for a falsy external_attr (Unix rw------- encoded in
    # the high 16 bits), so writing 0 here does not pin anything -- it
    # is overwritten to this exact value regardless. Setting it
    # explicitly makes the archive's actual, already-deterministic
    # value visible in this file instead of depending on a reader's
    # knowledge of that stdlib substitution.
    info.external_attr = 0o600 << 16
    archive.writestr(info, data)


def _sum_uncompressed(archive_bytes):
    """Sum every archive member's uncompressed size EXCEPT manifest.json.

    This must match the definition the in-loop cap check above already
    uses (the running total of included domain file content only) so
    that the value returned to the caller is exactly the value that was
    checked against ``max_uncompressed_bytes``, not that plus
    manifest.json's own (small but nonzero, and input-size-dependent)
    overhead. services/account_export_storage_service.py's independent
    readback recomputation uses this identical exclusion.
    """

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            return sum(
                info.file_size
                for info in archive.infolist()
                if info.filename != MANIFEST_PATH
            )
    except zipfile.BadZipFile as error:
        raise AccountExportAssemblyError("corrupt_archive") from error


class AccountExportAssemblyService:
    """Build the deterministic v1 account-export archive from a caller-
    supplied domain_files iterable. Holds no state and performs no I/O."""

    def assemble(
        self,
        domain_files,
        *,
        job_key,
        requested_at_utc,
        assembly_started_at_utc,
        assembly_cutoff_at_utc,
        consistency_marker_start=None,
        consistency_marker_cutoff=None,
        max_compressed_bytes=MAX_COMPRESSED_BYTES,
        max_uncompressed_bytes=MAX_UNCOMPRESSED_BYTES,
    ):
        """Return ``{"archive_bytes", "manifest", "sha256",
        "compressed_size_bytes", "uncompressed_size_bytes"}`` for the
        given ``domain_files`` iterable, or raise
        ``AccountExportAssemblyError`` before any bytes are returned.

        SHA-256 and both size facts are always derived here from the
        actual archive bytes just produced -- never estimated or
        carried through from caller input.
        """

        _require_non_empty_str(job_key, "invalid_job_key")
        _require_non_empty_str(requested_at_utc, "invalid_timestamp")
        _require_non_empty_str(assembly_started_at_utc, "invalid_timestamp")
        _require_non_empty_str(assembly_cutoff_at_utc, "invalid_timestamp")
        _require_optional_str(consistency_marker_start, "invalid_consistency_marker")
        _require_optional_str(consistency_marker_cutoff, "invalid_consistency_marker")

        entries = []
        for entry in domain_files:
            if not isinstance(entry, dict):
                raise AccountExportAssemblyError("invalid_domain_input")
            entries.append(_validate_domain_file(dict(entry)))

        paths = [entry["path"] for entry in entries]
        if len(paths) != len(set(paths)):
            raise AccountExportAssemblyError("duplicate_domain_path")
        entries.sort(key=lambda entry: entry["path"])

        # Pass 1: derive every file's independently-recomputed facts
        # (hash, byte length) from its raw content before any archive
        # bytes are written, so manifest.json can be the archive's
        # first physical member instead of a trailing summary that
        # would require rewriting it after the fact.
        manifest_files = []
        uncompressed_running_total = 0
        for entry in entries:
            disposition = entry["disposition"]
            file_record = {
                "path": entry["path"],
                "domain_code": entry["domain_code"],
                "schema_id": entry["schema_id"],
                "schema_version": entry["schema_version"],
                "disposition": disposition,
                "byte_length": None,
                "record_count": None,
                "sha256": None,
                "provenance": entry.get("provenance"),
                "read_window": entry.get("read_window"),
                "omission_reason": entry.get("omission_reason"),
                "failure_reason": entry.get("failure_reason"),
            }
            if disposition == "included":
                content = entry["content"]
                uncompressed_running_total += len(content)
                if uncompressed_running_total > max_uncompressed_bytes:
                    raise AccountExportAssemblyError("oversize_uncompressed")
                file_record["byte_length"] = len(content)
                file_record["record_count"] = entry["record_count"]
                file_record["sha256"] = hashlib.sha256(content).hexdigest()
            manifest_files.append(file_record)

        manifest = {
            "format": MANIFEST_FORMAT,
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "job_key": job_key,
            "requested_at_utc": requested_at_utc,
            "assembly_started_at_utc": assembly_started_at_utc,
            "assembly_cutoff_at_utc": assembly_cutoff_at_utc,
            "consistency_marker_start": consistency_marker_start,
            "consistency_marker_cutoff": consistency_marker_cutoff,
            "files": manifest_files,
        }
        manifest_bytes = json.dumps(
            manifest, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

        # Pass 2: write the archive -- manifest.json first, then every
        # included domain file in the exact lexical order manifest.json
        # already committed to. The compressed cap is checked against
        # the real underlying buffer length after every write, so a
        # run that would exceed it fails before any archive bytes are
        # ever returned.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_fixed_entry(archive, MANIFEST_PATH, manifest_bytes)
            if buffer.tell() > max_compressed_bytes:
                raise AccountExportAssemblyError("oversize_compressed")
            for entry in entries:
                if entry["disposition"] != "included":
                    continue
                _write_fixed_entry(archive, entry["path"], entry["content"])
                if buffer.tell() > max_compressed_bytes:
                    raise AccountExportAssemblyError("oversize_compressed")

        archive_bytes = buffer.getvalue()
        # The in-loop checks above see buffer.tell() before the ZipFile
        # context manager's own __exit__ appends the central directory
        # and end-of-central-directory record on close, so they alone
        # could let a result that is over the cap by that overhead
        # through. This final check against the true, complete archive
        # is the authoritative gate.
        if len(archive_bytes) > max_compressed_bytes:
            raise AccountExportAssemblyError("oversize_compressed")
        uncompressed_size_bytes = _sum_uncompressed(archive_bytes)

        return {
            "archive_bytes": archive_bytes,
            "manifest": manifest,
            "sha256": hashlib.sha256(archive_bytes).hexdigest(),
            "compressed_size_bytes": len(archive_bytes),
            "uncompressed_size_bytes": uncompressed_size_bytes,
        }


account_export_assembly_service = AccountExportAssemblyService()
