"""Owner-scoped upload, scan, normalization, and authorized attachment reads."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import logging
import posixpath
import re
import stat
from threading import Lock
import time
from urllib.parse import urlsplit
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import BadZipFile, LargeZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile

from services.community_contracts import (
    ATTACHMENT_CONTENT_TYPES,
    MAX_ATTACHMENT_BYTES,
    XLSX_CONTENT_TYPE,
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
    opaque_key,
    safe_display_name,
)
from services.community_media_storage import (
    CommunityMediaStorageError,
    community_media_storage,
)
from services.database_service import DatabaseServiceError, database_service
from services.photo_capture_service import PhotoCaptureError, normalize_photo


LOGGER = logging.getLogger(__name__)

XLSX_MAX_ENTRIES = 2_000
XLSX_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
XLSX_MAX_ENTRY_BYTES = 10 * 1024 * 1024
XLSX_MAX_XML_BYTES = 1024 * 1024
XLSX_MAX_COMPRESSION_RATIO = 100
XLSX_WORKBOOK_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
XLSX_WORKSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
)
XLSX_OFFICE_DOCUMENT_RELATIONSHIP_TYPES = frozenset(
    {
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
        "officeDocument",
        "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
    }
)
XLSX_WORKSHEET_RELATIONSHIP_TYPES = frozenset(
    {
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
        "http://purl.oclc.org/ooxml/officeDocument/relationships/worksheet",
    }
)
_XLSX_BLOCKED_PATH_PREFIXES = (
    "customxml/",
    "xl/activex/",
    "xl/embeddings/",
    "xl/externallinks/",
)
_XLSX_BLOCKED_PATHS = frozenset(
    {
        "xl/connections.xml",
        "xl/vbaproject.bin",
    }
)
_XLSX_BLOCKED_EXTENSIONS = frozenset(
    {
        ".bat",
        ".bin",
        ".class",
        ".cmd",
        ".com",
        ".dll",
        ".exe",
        ".jar",
        ".js",
        ".msi",
        ".ps1",
        ".scr",
        ".vbs",
    }
)
_XLSX_BLOCKED_CONTENT_TYPE_MARKERS = (
    "activex",
    "connections",
    "external",
    "macroenabled",
    "macrosheet",
    "oleobject",
    "vba",
)
_XLSX_BLOCKED_RELATIONSHIP_TYPE_TOKENS = frozenset(
    {
        "activexcontrol",
        "activexcontrolbinary",
        "connections",
        "control",
        "ctrlprop",
        "customxml",
        "embeddedpackage",
        "externallink",
        "externallinkpath",
        "oleobject",
        "package",
        "querytable",
        "vbaproject",
        "vbaprojectsignature",
        "xlintlmacrosheet",
        "xlmacrosheet",
    }
)


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    content_type: str
    extension: str
    display_name: str
    sha256_digest: bytes


def _xlsx_error():
    return CommunityValidationError(
        "The XLSX workbook contains unsupported or unsafe package content."
    )


def _xml_local_name(tag):
    return str(tag or "").rsplit("}", 1)[-1]


def _normalized_xlsx_entry_name(info):
    name = info.filename
    if (
        not isinstance(name, str)
        or not name
        or "\x00" in name
        or "\\" in name
        or name.startswith("/")
    ):
        raise _xlsx_error()
    normalized = name[:-1] if name.endswith("/") else name
    parts = normalized.split("/")
    if (
        not normalized
        or any(part in {"", ".", ".."} for part in parts)
        or ":" in parts[0]
        or posixpath.normpath(normalized) != normalized
    ):
        raise _xlsx_error()
    unix_mode = (int(info.external_attr or 0) >> 16) & 0o170000
    if unix_mode == stat.S_IFLNK:
        raise _xlsx_error()
    return normalized


def _read_xlsx_xml(archive, entries, name):
    info = entries.get(name)
    if info is None or info.is_dir() or info.file_size > XLSX_MAX_XML_BYTES:
        raise _xlsx_error()
    try:
        payload = archive.read(info)
    except (BadZipFile, RuntimeError, NotImplementedError, EOFError) as error:
        raise _xlsx_error() from error
    if (
        len(payload) != info.file_size
        or b"<!doctype" in payload.lower()
        or b"<!entity" in payload.lower()
    ):
        raise _xlsx_error()
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise _xlsx_error() from error


def _xlsx_relationships(archive, entries, name):
    root = _read_xlsx_xml(archive, entries, name)
    if _xml_local_name(root.tag) != "Relationships":
        raise _xlsx_error()
    relationships = []
    relationship_ids = set()
    for node in root:
        if _xml_local_name(node.tag) != "Relationship":
            continue
        relationship = dict(node.attrib)
        relationship_id = str(relationship.get("Id") or "").strip()
        relationship_type = str(relationship.get("Type") or "").strip()
        folded_relationship_type = relationship_type.casefold()
        relationship_type_token = folded_relationship_type.rsplit(
            "/relationships/", 1
        )[-1]
        target = str(relationship.get("Target") or "").strip()
        target_mode = str(relationship.get("TargetMode") or "").strip().casefold()
        parsed_target = urlsplit(target)
        path_parts = parsed_target.path.split("/")
        if (
            not relationship_id
            or relationship_id in relationship_ids
            or not relationship_type
            or relationship_type_token in _XLSX_BLOCKED_RELATIONSHIP_TYPE_TOKENS
            or not target
            or "\\" in target
            or target_mode not in {"", "internal"}
            or parsed_target.scheme
            or parsed_target.netloc
            or not parsed_target.path
            or parsed_target.query
            or parsed_target.fragment
            or target.startswith("//")
            or "%" in target
            or any(part in {".", ".."} for part in path_parts)
        ):
            raise _xlsx_error()
        relationship_ids.add(relationship_id)
        relationships.append(relationship)
    return relationships


def validate_xlsx_package(data):
    """Validate a bounded OOXML workbook without parsing or evaluating cell data."""
    if (
        not isinstance(data, bytes)
        or len(data) < 22
        or not data.startswith(b"PK\x03\x04")
        or data[-22:-18] != b"PK\x05\x06"
        or data[-2:] != b"\x00\x00"
    ):
        raise _xlsx_error()
    try:
        with ZipFile(BytesIO(data), mode="r", allowZip64=False) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > XLSX_MAX_ENTRIES:
                raise _xlsx_error()
            entries = {}
            names_casefolded = set()
            total_uncompressed = 0
            for info in infos:
                name = _normalized_xlsx_entry_name(info)
                folded = name.casefold()
                if folded in names_casefolded:
                    raise _xlsx_error()
                names_casefolded.add(folded)
                entries[name] = info
                if info.flag_bits & 0x1:
                    raise _xlsx_error()
                if info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
                    raise _xlsx_error()
                if info.is_dir():
                    continue
                if (
                    info.file_size < 0
                    or info.compress_size < 0
                    or info.file_size > XLSX_MAX_ENTRY_BYTES
                    or (info.file_size and not info.compress_size)
                    or (
                        info.compress_size
                        and info.file_size
                        > info.compress_size * XLSX_MAX_COMPRESSION_RATIO
                    )
                ):
                    raise _xlsx_error()
                total_uncompressed += info.file_size
                if total_uncompressed > XLSX_MAX_UNCOMPRESSED_BYTES:
                    raise _xlsx_error()
                lower_name = folded
                if (
                    lower_name in _XLSX_BLOCKED_PATHS
                    or lower_name.startswith(_XLSX_BLOCKED_PATH_PREFIXES)
                    or any(
                        lower_name.endswith(extension)
                        for extension in _XLSX_BLOCKED_EXTENSIONS
                    )
                ):
                    raise _xlsx_error()

            required_parts = {
                "[Content_Types].xml",
                "_rels/.rels",
                "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels",
            }
            if not required_parts.issubset(entries):
                raise _xlsx_error()

            content_types = _read_xlsx_xml(
                archive, entries, "[Content_Types].xml"
            )
            if _xml_local_name(content_types.tag) != "Types":
                raise _xlsx_error()
            overrides = {}
            override_names = set()
            defaults = {}
            declared_types = []
            for node in content_types:
                content_type = str(node.attrib.get("ContentType") or "").strip()
                if content_type:
                    declared_types.append(content_type.casefold())
                node_name = _xml_local_name(node.tag)
                if node_name == "Override":
                    part_name = str(node.attrib.get("PartName") or "").strip()
                    normalized_part = part_name.lstrip("/")
                    folded_part = normalized_part.casefold()
                    if (
                        not part_name.startswith("/")
                        or not content_type
                        or folded_part in override_names
                        or normalized_part not in entries
                    ):
                        raise _xlsx_error()
                    override_names.add(folded_part)
                    overrides[part_name] = content_type
                elif node_name == "Default":
                    extension = str(node.attrib.get("Extension") or "").strip()
                    folded_extension = extension.casefold()
                    if (
                        not re.fullmatch(r"[A-Za-z0-9]+", extension)
                        or not content_type
                        or folded_extension in defaults
                    ):
                        raise _xlsx_error()
                    defaults[folded_extension] = content_type

            def declared_content_type(part_name):
                override = overrides.get(f"/{part_name}")
                if override is not None:
                    return override
                extension = part_name.rsplit(".", 1)[-1].casefold()
                return defaults.get(extension)

            if (
                declared_content_type("xl/workbook.xml")
                != XLSX_WORKBOOK_CONTENT_TYPE
                or not any(
                    part.startswith("xl/worksheets/")
                    and declared_content_type(part) == XLSX_WORKSHEET_CONTENT_TYPE
                    for part in entries
                )
                or any(
                    marker in content_type
                    for content_type in declared_types
                    for marker in _XLSX_BLOCKED_CONTENT_TYPE_MARKERS
                )
            ):
                raise _xlsx_error()

            package_relationships = _xlsx_relationships(
                archive, entries, "_rels/.rels"
            )
            office_documents = [
                relationship
                for relationship in package_relationships
                if str(relationship.get("Type") or "")
                in XLSX_OFFICE_DOCUMENT_RELATIONSHIP_TYPES
            ]
            if (
                len(office_documents) != 1
                or str(office_documents[0].get("Target") or "").lstrip("/")
                != "xl/workbook.xml"
            ):
                raise _xlsx_error()

            workbook_relationships = _xlsx_relationships(
                archive, entries, "xl/_rels/workbook.xml.rels"
            )
            worksheet_relationships = []
            for relationship in workbook_relationships:
                if (
                    str(relationship.get("Type") or "")
                    not in XLSX_WORKSHEET_RELATIONSHIP_TYPES
                ):
                    continue
                target = str(relationship.get("Target") or "")
                resolved = (
                    target.lstrip("/")
                    if target.startswith("/")
                    else posixpath.normpath(posixpath.join("xl", target))
                )
                if (
                    resolved.startswith("../")
                    or resolved not in entries
                    or declared_content_type(resolved)
                    != XLSX_WORKSHEET_CONTENT_TYPE
                ):
                    raise _xlsx_error()
                worksheet_relationships.append(relationship)
            if not worksheet_relationships:
                raise _xlsx_error()

            workbook = _read_xlsx_xml(archive, entries, "xl/workbook.xml")
            if (
                _xml_local_name(workbook.tag) != "workbook"
                or not any(
                    _xml_local_name(node.tag) == "sheet"
                    for node in workbook.iter()
                )
            ):
                raise _xlsx_error()

            for name in entries:
                if name.casefold().endswith(".rels"):
                    _xlsx_relationships(archive, entries, name)
            if archive.testzip() is not None:
                raise _xlsx_error()
    except CommunityValidationError:
        raise
    except (
        BadZipFile,
        LargeZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        ValueError,
    ) as error:
        raise _xlsx_error() from error


def stored_sha256(value):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes) and len(value) == 32:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return bytes.fromhex(value)
    raise CommunityUnavailableError("Attachment integrity metadata is unavailable.")


def validate_upload(upload):
    if upload is None or not getattr(upload, "stream", None):
        raise CommunityValidationError("Choose a file to attach.")
    content_type = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0]
    if content_type not in ATTACHMENT_CONTENT_TYPES:
        raise CommunityValidationError("Attach a JPEG, PNG, PDF, or XLSX file.")
    data = upload.stream.read(MAX_ATTACHMENT_BYTES + 1)
    if not data:
        raise CommunityValidationError("The attachment is empty.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise CommunityValidationError("Attachments are limited to 10 MiB.")
    if content_type == "image/jpeg":
        valid = data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
        extension = "jpg"
    elif content_type == "image/png":
        valid = data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(
            b"\x00\x00\x00\x00IEND\xaeB\x60\x82"
        )
        extension = "png"
    elif content_type == "application/pdf":
        valid = data.startswith(b"%PDF-") and b"%%EOF" in data[-1024:]
        extension = "pdf"
    else:
        validate_xlsx_package(data)
        valid = True
        extension = "xlsx"
    if not valid:
        raise CommunityValidationError(
            "The attachment contents do not match its file type."
        )
    return ValidatedUpload(
        data=data,
        content_type=content_type,
        extension=extension,
        display_name=safe_display_name(
            getattr(upload, "filename", ""), content_type=content_type
        ),
        sha256_digest=hashlib.sha256(data).digest(),
    )


class CommunityMediaService:
    def __init__(self, database=None, storage=None):
        self.database = database or database_service
        self.storage = storage or community_media_storage

    def reserve_and_upload(self, user_key, upload):
        self.sweep_best_effort(limit=4)
        item = validate_upload(upload)
        opaque = uuid4().hex
        original = f"community/v1/{opaque[:2]}/{opaque}.{item.extension}"
        safe = f"community/v1/{opaque[:2]}/{opaque}-safe.{item.extension}"
        row = None
        try:
            row = self.database.last_row(
                "usp_ReservePublicCommunityMedia",
                [
                    ("@UserKey", user_key),
                    ("@DisplayName", item.display_name),
                    ("@ContentType", item.content_type),
                    ("@ByteLength", len(item.data)),
                    ("@Sha256", item.sha256_digest),
                    ("@OriginalBlobName", original),
                    (
                        "@SafeBlobName",
                        safe if item.content_type.startswith("image/") else original,
                    ),
                ],
            )
            if not row or row.get("outcome") != "reserved":
                raise CommunityUnavailableError("Attachment upload unavailable.")
            self.storage.upload(original, item.data, item.content_type)
            marked = self.database.last_row(
                "usp_MarkPublicCommunityMediaUploaded",
                [("@UserKey", user_key), ("@MediaKey", row["media_key"])],
            )
            if not marked or marked.get("outcome") != "uploaded":
                raise CommunityUnavailableError("Attachment upload unavailable.")
            return {
                "key": str(row["media_key"]),
                "state": "processing",
                "display_name": item.display_name,
            }
        except (
            DatabaseServiceError,
            CommunityMediaStorageError,
            CommunityUnavailableError,
        ) as error:
            if row and row.get("media_key"):
                try:
                    self.storage.delete(original)
                except CommunityMediaStorageError:
                    pass
                try:
                    self.database.last_row(
                        "usp_RejectPublicCommunityMedia",
                        [
                            ("@UserKey", user_key),
                            ("@MediaKey", row["media_key"]),
                            ("@TerminalState", "failed"),
                        ],
                    )
                except DatabaseServiceError:
                    pass
                self.sweep_best_effort(limit=4, media_key=row["media_key"])
            raise CommunityUnavailableError("Attachment upload unavailable.") from error

    def reconcile(self, user_key, media_key):
        media_key = opaque_key(media_key, field="attachment key")
        try:
            row = self.database.first_row(
                "usp_GetPublicCommunityMediaForOwner",
                [("@UserKey", user_key), ("@MediaKey", media_key)],
            )
            if not row:
                raise CommunityNotFoundError("Attachment not found.")
            if row.get("media_state") in {"ready", "rejected", "removed", "failed"}:
                if row.get("media_state") != "ready":
                    self.sweep_best_effort(limit=1, media_key=media_key)
                return self._safe_state(row)
            scan = self.storage.scan_result(row["original_blob_name"])
            if scan["result"] == "malicious":
                return self._reject(user_key, media_key, "rejected")
            if scan["result"] == "error":
                return self._reject(user_key, media_key, "failed")
            if scan["result"] != "clean":
                return {"key": media_key, "state": "processing"}
            if scan.get("scan_time_utc") is None:
                return self._reject(user_key, media_key, "failed")
            width = height = None
            safe_byte_length = int(row["byte_length"])
            safe_sha256 = stored_sha256(row["sha256"])
            derivative_available = False
            source = self.storage.download(row["original_blob_name"])
            if (
                int(source.get("byte_length") or 0) != int(row["byte_length"])
                or len(source.get("data") or b"") != int(row["byte_length"])
                or hashlib.sha256(source["data"]).digest()
                != stored_sha256(row["sha256"])
                or source.get("content_type") not in {None, row["content_type"]}
            ):
                self._reject(user_key, media_key, "failed")
                raise CommunityValidationError(
                    "The image failed its integrity check."
                    if str(row["content_type"]).startswith("image/")
                    else "The attachment failed its integrity check."
                )
            if row["content_type"] == XLSX_CONTENT_TYPE:
                try:
                    validate_xlsx_package(source["data"])
                except CommunityValidationError:
                    self._reject(user_key, media_key, "failed")
                    raise
            if str(row["content_type"]).startswith("image/"):
                try:
                    derivative = normalize_photo(source["data"], row["content_type"])
                except PhotoCaptureError as error:
                    self._reject(user_key, media_key, "failed")
                    raise CommunityValidationError("The image could not be safely processed.") from error
                if (
                    not isinstance(derivative.data, bytes)
                    or derivative.byte_length != len(derivative.data)
                    or not 1 <= derivative.byte_length <= MAX_ATTACHMENT_BYTES
                    or hashlib.sha256(derivative.data).digest()
                    != derivative.sha256_digest
                ):
                    self._reject(user_key, media_key, "failed")
                    raise CommunityValidationError(
                        "The image could not be safely processed."
                    )
                try:
                    self.storage.upload(
                        row["safe_blob_name"], derivative.data, derivative.content_type
                    )
                except CommunityMediaStorageError as error:
                    if error.code != "storage_conflict":
                        raise
                    existing = self.storage.download(row["safe_blob_name"])
                    if (
                        int(existing.get("byte_length") or 0) != derivative.byte_length
                        or len(existing.get("data") or b"") != derivative.byte_length
                        or hashlib.sha256(existing["data"]).digest()
                        != derivative.sha256_digest
                        or existing.get("content_type")
                        not in {None, derivative.content_type}
                    ):
                        self._reject(user_key, media_key, "failed")
                        raise CommunityValidationError(
                            "The image failed its integrity check."
                        ) from error
                derivative_available = True
                width, height = derivative.width, derivative.height
                safe_byte_length = derivative.byte_length
                safe_sha256 = derivative.sha256_digest
            completion_parameters = [
                ("@UserKey", user_key),
                ("@MediaKey", media_key),
                ("@SafeByteLength", safe_byte_length),
                ("@SafeSha256", safe_sha256),
                ("@PixelWidth", width),
                ("@PixelHeight", height),
                ("@ScanTimeUtc", scan["scan_time_utc"]),
            ]
            completion_error = None
            try:
                completed = self.database.last_row(
                    "usp_CompletePublicCommunityMedia", completion_parameters
                )
            except DatabaseServiceError as error:
                completed = None
                completion_error = error
            if completed and completed.get("outcome") == "ready":
                return self._safe_state(completed)
            if derivative_available:
                compensated = self._compensate_derivative_completion(
                    user_key,
                    media_key,
                    safe_byte_length,
                    safe_sha256,
                    width,
                    height,
                )
                if compensated:
                    return compensated
            unavailable = CommunityUnavailableError(
                "Attachment processing unavailable."
            )
            if completion_error is not None:
                raise unavailable from completion_error
            raise unavailable
        except (DatabaseServiceError, CommunityMediaStorageError) as error:
            raise CommunityUnavailableError("Attachment processing unavailable.") from error

    def _reject(self, user_key, media_key, state):
        row = self.database.last_row(
            "usp_RejectPublicCommunityMedia",
            [("@UserKey", user_key), ("@MediaKey", media_key), ("@TerminalState", state)],
        )
        if not row or row.get("outcome") not in {"rejected", "failed", "existing"}:
            raise CommunityUnavailableError("Attachment processing unavailable.")
        self.sweep_best_effort(limit=4, media_key=media_key)
        return {"key": media_key, "state": row.get("media_state") or state}

    @staticmethod
    def _safe_state(row):
        return {
            "key": str(row.get("media_key")),
            "state": row.get("media_state"),
            "display_name": row.get("display_name"),
            "content_type": row.get("content_type"),
        }

    def _compensate_derivative_completion(
        self,
        user_key,
        media_key,
        safe_byte_length,
        safe_sha256,
        width,
        height,
    ):
        row = self.database.last_row(
            "usp_CompensatePublicCommunityMediaCompletion",
            [
                ("@UserKey", user_key),
                ("@MediaKey", media_key),
                ("@SafeByteLength", safe_byte_length),
                ("@SafeSha256", safe_sha256),
                ("@PixelWidth", width),
                ("@PixelHeight", height),
            ],
        )
        outcome = row.get("outcome") if row else None
        if outcome == "ready":
            return self._safe_state(row)
        if outcome == "cleanup_reopened":
            LOGGER.warning(
                "Community media derivative completion lost a terminal race; "
                "cleanup was reopened."
            )
            self.sweep_best_effort(limit=1, media_key=media_key)
        return None

    def sweep(
        self,
        limit=4,
        media_key=None,
        post_key=None,
        contribution_key=None,
        uploader_user_key=None,
    ):
        """Delete blobs claimed by SQL, completing only fully successful claims.

        `uploader_user_key` scopes a targeted claim to one member's uploads in
        SQL rather than relying only on the route having checked ownership
        first (independent review, 2026-08-04, F14). Server-initiated lifecycle
        sweeps pass none and stay unscoped, which is correct for a janitor.
        """
        selectors = [media_key, post_key, contribution_key]
        if sum(value is not None for value in selectors) > 1:
            raise CommunityValidationError("The cleanup target is invalid.")
        parameters = [("@Take", limit)]
        if uploader_user_key is not None:
            parameters.append(("@UploaderUserKey", uploader_user_key))
        if media_key is not None:
            parameters.append(
                ("@MediaKey", opaque_key(media_key, field="attachment key"))
            )
        if post_key is not None:
            parameters.append(("@PostKey", opaque_key(post_key, field="post key")))
        if contribution_key is not None:
            parameters.append(
                (
                    "@ContributionKey",
                    opaque_key(contribution_key, field="contribution key"),
                )
            )
        claims = self.database.first_result(
            "usp_ClaimPublicCommunityMediaCleanup", parameters
        )
        completed = 0
        storage_failures = 0
        for claim in claims:
            try:
                self.storage.delete(claim.get("original_blob_name"))
                if claim.get("safe_blob_name") != claim.get("original_blob_name"):
                    self.storage.delete(claim.get("safe_blob_name"))
            except CommunityMediaStorageError:
                # The SQL lease expires after ten minutes, making this retryable
                # without declaring physical deletion complete prematurely.
                storage_failures += 1
                continue
            result = self.database.last_row(
                "usp_CompletePublicCommunityMediaCleanup",
                [
                    ("@MediaKey", claim.get("media_key")),
                    ("@ClaimToken", claim.get("cleanup_claim_token")),
                ],
            )
            if not result or result.get("outcome") != "completed":
                raise DatabaseServiceError("Community attachment cleanup completion failed.")
            completed += 1
        log = LOGGER.warning if storage_failures else LOGGER.info
        log(
            "Community media cleanup batch finished: claimed=%d completed=%d "
            "storage_failures=%d.",
            len(claims),
            completed,
            storage_failures,
        )
        return completed

    def sweep_best_effort(
        self,
        limit=4,
        media_key=None,
        post_key=None,
        contribution_key=None,
        uploader_user_key=None,
    ):
        try:
            return self.sweep(
                limit=limit,
                media_key=media_key,
                post_key=post_key,
                contribution_key=contribution_key,
                uploader_user_key=uploader_user_key,
            )
        except (DatabaseServiceError, CommunityMediaStorageError) as error:
            LOGGER.error(
                "Community media cleanup dependency failure: error_type=%s.",
                type(error).__name__,
                exc_info=True,
            )
            return 0

    def public_file(self, media_key, *, preview):
        media_key = opaque_key(media_key, field="attachment key")
        try:
            row = self.database.first_row(
                "usp_GetPublicCommunityMedia", [("@MediaKey", media_key)]
            )
            if not row:
                raise CommunityNotFoundError("Attachment not found.")
            is_image = str(row["content_type"]).startswith("image/")
            if preview and not is_image:
                raise CommunityNotFoundError("Attachment not found.")
            blob_name = row["safe_blob_name"] if is_image else row["original_blob_name"]
            stored = self.storage.download(blob_name)
            expected_length = int(row["safe_byte_length"])
            expected_digest = stored_sha256(row["safe_sha256"])
            if (
                int(stored.get("byte_length") or 0) != expected_length
                or len(stored.get("data") or b"") != expected_length
                or hashlib.sha256(stored["data"]).digest() != expected_digest
                or stored.get("content_type") not in {None, row["content_type"]}
            ):
                raise CommunityMediaStorageError("storage_integrity_failed")
            return {
                "data": stored["data"],
                "content_type": row["content_type"],
                "display_name": row["display_name"],
                "inline": bool(preview and is_image),
            }
        except (DatabaseServiceError, CommunityMediaStorageError) as error:
            raise CommunityUnavailableError("Attachment unavailable.") from error

    def remove(self, user_key, media_key):
        media_key = opaque_key(media_key, field="attachment key")
        try:
            row = self.database.last_row(
                "usp_DeletePublicCommunityMedia",
                [("@UserKey", user_key), ("@MediaKey", media_key)],
            )
            if not row or row.get("outcome") not in {"removed", "existing"}:
                raise CommunityNotFoundError("Attachment not found.")
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Attachment removal unavailable.") from error
        self.sweep_best_effort(limit=1, media_key=media_key)


class CommunityMediaMaintenance:
    """Run one bounded cleanup batch on the Always On request cadence."""

    def __init__(self, service=None, interval_seconds=3600):
        self.service = service or community_media_service
        self.interval_seconds = interval_seconds
        self._next_run = 0.0
        self._lock = Lock()

    def maybe_run(self):
        now = time.monotonic()
        if now < self._next_run or not self._lock.acquire(blocking=False):
            return 0
        try:
            now = time.monotonic()
            if now < self._next_run:
                return 0
            self._next_run = now + self.interval_seconds
            return self.service.sweep_best_effort(limit=20)
        finally:
            self._lock.release()


community_media_service = CommunityMediaService()
community_media_maintenance = CommunityMediaMaintenance(community_media_service)
