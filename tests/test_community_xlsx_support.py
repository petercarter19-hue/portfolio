"""Focused security and delivery contracts for Community XLSX attachments."""

from __future__ import annotations

from datetime import datetime
import hashlib
from io import BytesIO
import struct
import unittest
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Flask
from werkzeug.datastructures import FileStorage

from community_api import community_api
from services.community_contracts import (
    MAX_ATTACHMENT_BYTES,
    XLSX_CONTENT_TYPE,
    CommunityNotFoundError,
    CommunityValidationError,
)
from services.community_media_service import (
    CommunityMediaService,
    validate_upload,
    validate_xlsx_package,
)


OWNER_KEY = str(uuid4())
MEDIA_KEY = str(uuid4())
ORIGINAL_BLOB = "community/v1/aa/" + "a" * 32 + ".xlsx"

WORKBOOK_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
WORKSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
)
OFFICE_DOCUMENT_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    "officeDocument"
)
WORKSHEET_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
)


def workbook_bytes(
    *,
    workbook_as_default=False,
    extra_content_type="",
    extra_package_relationship="",
    extra_relationship="",
    extra_entries=(),
):
    if workbook_as_default:
        workbook_declaration = (
            f'<Default Extension="xml" ContentType="{WORKBOOK_CONTENT_TYPE}"/>'
        )
    else:
        workbook_declaration = (
            f'<Override PartName="/xl/workbook.xml" '
            f'ContentType="{WORKBOOK_CONTENT_TYPE}"/>'
        )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        f"{workbook_declaration}"
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        f'ContentType="{WORKSHEET_CONTENT_TYPE}"/>'
        f"{extra_content_type}"
        "</Types>"
    )
    package_relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships '
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{OFFICE_DOCUMENT_RELATIONSHIP}" '
        'Target="/xl/workbook.xml"/>'
        f"{extra_package_relationship}"
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook '
        'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Gate Tracker" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships '
        'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{WORKSHEET_RELATIONSHIP}" '
        'Target="/xl/worksheets/sheet1.xml"/>'
        f"{extra_relationship}"
        "</Relationships>"
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet '
        'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Gate</t></is>'
        "</c></row></sheetData></worksheet>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_relationships)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
        for name, payload in extra_entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


def mark_first_entry_encrypted(data):
    encrypted = bytearray(data)
    local_header = encrypted.find(b"PK\x03\x04")
    central_header = encrypted.find(b"PK\x01\x02")
    if local_header < 0 or central_header < 0:
        raise AssertionError("Fixture is not a ZIP archive")
    local_flags = struct.unpack_from("<H", encrypted, local_header + 6)[0] | 0x1
    central_flags = struct.unpack_from("<H", encrypted, central_header + 8)[0] | 0x1
    struct.pack_into("<H", encrypted, local_header + 6, local_flags)
    struct.pack_into("<H", encrypted, central_header + 8, central_flags)
    return bytes(encrypted)


class CommunityXlsxPackageTests(unittest.TestCase):
    def test_exact_mime_validates_package_and_forces_safe_xlsx_name(self):
        data = workbook_bytes(workbook_as_default=True)
        upload = FileStorage(
            stream=BytesIO(data),
            filename="../gate-tracker.xlsm",
            content_type=XLSX_CONTENT_TYPE,
        )

        item = validate_upload(upload)

        self.assertEqual(item.data, data)
        self.assertEqual(item.content_type, XLSX_CONTENT_TYPE)
        self.assertEqual(item.extension, "xlsx")
        self.assertEqual(item.display_name, "gate-tracker.xlsx")
        self.assertEqual(item.sha256_digest, hashlib.sha256(data).digest())

    def test_valid_package_with_non_xlsx_mime_is_rejected(self):
        upload = FileStorage(
            stream=BytesIO(workbook_bytes()),
            filename="gate-tracker.xlsx",
            content_type="application/octet-stream",
        )
        with self.assertRaisesRegex(
            CommunityValidationError, "JPEG, PNG, PDF, or XLSX"
        ):
            validate_upload(upload)

    def test_malformed_and_oversized_uploads_are_rejected(self):
        malformed = FileStorage(
            stream=BytesIO(b"not an OOXML ZIP"),
            filename="gate-tracker.xlsx",
            content_type=XLSX_CONTENT_TYPE,
        )
        with self.assertRaises(CommunityValidationError):
            validate_upload(malformed)

        oversized = FileStorage(
            stream=BytesIO(b"A" * (MAX_ATTACHMENT_BYTES + 1)),
            filename="gate-tracker.xlsx",
            content_type=XLSX_CONTENT_TYPE,
        )
        with self.assertRaisesRegex(CommunityValidationError, "10 MiB"):
            validate_upload(oversized)

    def test_rejects_macro_activex_ole_and_custom_xml_parts(self):
        unsafe_parts = (
            ("xl/vbaProject.bin", b"macro"),
            ("xl/activeX/activeX1.xml", b"control"),
            ("xl/embeddings/oleObject1.bin", b"ole"),
            ("customXml/item1.xml", b"custom"),
        )
        for unsafe_part in unsafe_parts:
            with self.subTest(part=unsafe_part[0]), self.assertRaises(
                CommunityValidationError
            ):
                validate_xlsx_package(
                    workbook_bytes(extra_entries=(unsafe_part,))
                )

    def test_rejects_xlm_macro_sheet_content_and_relationships_at_any_path(self):
        cases = (
            workbook_bytes(
                extra_content_type=(
                    '<Override PartName="/xl/custom/legacy-sheet.xml" '
                    'ContentType="application/vnd.ms-excel.macrosheet+xml"/>'
                ),
                extra_entries=(("xl/custom/legacy-sheet.xml", b"<macrosheet/>"),),
            ),
            workbook_bytes(
                extra_relationship=(
                    '<Relationship Id="rId2" '
                    'Type="http://schemas.microsoft.com/office/2006/'
                    'relationships/xlMacrosheet" '
                    'Target="/xl/custom/legacy-sheet.xml"/>'
                ),
                extra_entries=(("xl/custom/legacy-sheet.xml", b"<macrosheet/>"),),
            ),
        )
        for data in cases:
            with self.subTest(
                case=hashlib.sha256(data).hexdigest()
            ), self.assertRaises(CommunityValidationError):
                validate_xlsx_package(data)

    def test_rejects_external_connection_content_and_relationships_at_any_path(self):
        cases = (
            workbook_bytes(
                extra_content_type=(
                    '<Override PartName="/xl/custom/data-source.xml" '
                    'ContentType="application/vnd.ms-excel.connections+xml"/>'
                ),
                extra_entries=(("xl/custom/data-source.xml", b"<connections/>"),),
            ),
            workbook_bytes(
                extra_relationship=(
                    '<Relationship Id="rId2" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                    'relationships/connections" '
                    'Target="/xl/custom/data-source.xml"/>'
                ),
                extra_entries=(("xl/custom/data-source.xml", b"<connections/>"),),
            ),
        )
        for data in cases:
            with self.subTest(
                case=hashlib.sha256(data).hexdigest()
            ), self.assertRaises(CommunityValidationError):
                validate_xlsx_package(data)

    def test_rejects_active_relationship_types_at_noncanonical_paths(self):
        relationship_types = (
            "package",
            "oleObject",
            "control",
            "vbaProject",
            "xlIntlMacrosheet",
            "externalLink",
            "queryTable",
        )
        for relationship_type in relationship_types:
            relationship = (
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                f'relationships/{relationship_type}" '
                'Target="/xl/custom/payload.dat"/>'
            )
            with self.subTest(relationship_type=relationship_type), self.assertRaises(
                CommunityValidationError
            ):
                validate_xlsx_package(
                    workbook_bytes(
                        extra_relationship=relationship,
                        extra_entries=(("xl/custom/payload.dat", b"payload"),),
                    )
                )

    def test_accepts_standard_core_and_extended_document_properties(self):
        core_relationship = (
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/'
            'relationships/metadata/core-properties" '
            'Target="/docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/extended-properties" '
            'Target="/docProps/app.xml"/>'
        )
        document_property_types = (
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.'
            'core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'extended-properties+xml"/>'
        )
        data = workbook_bytes(
            extra_content_type=document_property_types,
            extra_package_relationship=core_relationship,
            extra_entries=(
                ("docProps/core.xml", b"<coreProperties/>"),
                ("docProps/app.xml", b"<Properties/>"),
            ),
        )

        validate_xlsx_package(data)

    def test_rejects_external_and_traversing_relationships(self):
        relationships = (
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/hyperlink" Target="https://example.com" '
            'TargetMode="External"/>',
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/styles" Target="../outside.xml"/>',
        )
        for relationship in relationships:
            with self.subTest(relationship=relationship), self.assertRaises(
                CommunityValidationError
            ):
                validate_xlsx_package(
                    workbook_bytes(extra_relationship=relationship)
                )

    def test_rejects_entry_traversal_encryption_and_duplicate_names(self):
        traversal = workbook_bytes(extra_entries=(("../outside.xml", b"unsafe"),))
        duplicate = workbook_bytes(
            extra_entries=(("[content_types].XML", b"duplicate"),)
        )
        encrypted = mark_first_entry_encrypted(workbook_bytes())
        for label, data in (
            ("traversal", traversal),
            ("duplicate", duplicate),
            ("encrypted", encrypted),
        ):
            with self.subTest(case=label), self.assertRaises(
                CommunityValidationError
            ):
                validate_xlsx_package(data)

    def test_rejects_high_ratio_zip_bomb_and_trailing_payload(self):
        compressed_bomb = workbook_bytes(
            extra_entries=(("xl/media/repeated.txt", b"A" * 2_000_000),)
        )
        trailing_payload = workbook_bytes() + b"untrusted-trailer"
        for label, data in (
            ("compression-ratio", compressed_bomb),
            ("trailing-payload", trailing_payload),
        ):
            with self.subTest(case=label), self.assertRaises(
                CommunityValidationError
            ):
                validate_xlsx_package(data)


class CommunityXlsxRuntimeTests(unittest.TestCase):
    def test_reservation_upload_uses_opaque_xlsx_blob_and_exact_mime(self):
        class Database:
            def __init__(self):
                self.calls = []

            def first_result(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return []

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_ReservePublicCommunityMedia":
                    return {"outcome": "reserved", "media_key": MEDIA_KEY}
                if procedure == "usp_MarkPublicCommunityMediaUploaded":
                    return {"outcome": "uploaded"}
                raise AssertionError(f"Unexpected procedure: {procedure}")

        class Storage:
            def __init__(self):
                self.uploaded = None

            def upload(self, blob_name, data, content_type):
                self.uploaded = (blob_name, data, content_type)
                return {"etag": "test"}

        database = Database()
        storage = Storage()
        upload = FileStorage(
            stream=BytesIO(workbook_bytes()),
            filename="gate-tracker.xlsx",
            content_type=XLSX_CONTENT_TYPE,
        )

        result = CommunityMediaService(database, storage).reserve_and_upload(
            OWNER_KEY, upload
        )

        self.assertEqual(result["state"], "processing")
        self.assertRegex(
            storage.uploaded[0],
            r"^community/v1/[0-9a-f]{2}/[0-9a-f]{32}\.xlsx$",
        )
        self.assertEqual(storage.uploaded[2], XLSX_CONTENT_TYPE)
        mark_calls = [
            call
            for call in database.calls
            if call[0] == "usp_MarkPublicCommunityMediaUploaded"
        ]
        self.assertEqual(len(mark_calls), 1)

    def test_clean_post_scan_document_is_downloaded_verified_and_revalidated(self):
        data = workbook_bytes()

        class Database:
            def __init__(self):
                self.calls = []

            def first_row(self, procedure, parameters):
                return {
                    "media_key": MEDIA_KEY,
                    "media_state": "uploaded",
                    "original_blob_name": ORIGINAL_BLOB,
                    "safe_blob_name": ORIGINAL_BLOB,
                    "content_type": XLSX_CONTENT_TYPE,
                    "display_name": "gate-tracker.xlsx",
                    "byte_length": len(data),
                    "sha256": hashlib.sha256(data).digest(),
                }

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_CompletePublicCommunityMedia":
                    return {
                        "outcome": "ready",
                        "media_key": MEDIA_KEY,
                        "media_state": "ready",
                        "display_name": "gate-tracker.xlsx",
                        "content_type": XLSX_CONTENT_TYPE,
                    }
                raise AssertionError(f"Unexpected procedure: {procedure}")

        class Storage:
            def __init__(self):
                self.downloads = []

            def scan_result(self, blob_name):
                return {
                    "result": "clean",
                    "scan_time_utc": datetime(2026, 8, 1, 12, 0),
                }

            def download(self, blob_name):
                self.downloads.append(blob_name)
                return {
                    "data": data,
                    "byte_length": len(data),
                    "content_type": XLSX_CONTENT_TYPE,
                }

        database = Database()
        storage = Storage()
        with patch(
            "services.community_media_service.validate_xlsx_package",
            wraps=validate_xlsx_package,
        ) as validator:
            result = CommunityMediaService(database, storage).reconcile(
                OWNER_KEY, MEDIA_KEY
            )

        self.assertEqual(result["state"], "ready")
        self.assertEqual(storage.downloads, [ORIGINAL_BLOB])
        validator.assert_called_once_with(data)
        completion = database.calls[0]
        self.assertEqual(completion[0], "usp_CompletePublicCommunityMedia")
        self.assertIn(("@SafeByteLength", len(data)), completion[1])
        self.assertIn(("@SafeSha256", hashlib.sha256(data).digest()), completion[1])
        self.assertIn(("@PixelWidth", None), completion[1])
        self.assertIn(("@PixelHeight", None), completion[1])

    def test_post_scan_package_failure_is_terminal(self):
        data = workbook_bytes(
            extra_relationship=(
                '<Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/hyperlink" Target="https://example.com" '
                'TargetMode="External"/>'
            )
        )

        class Database:
            def __init__(self):
                self.calls = []

            def first_row(self, procedure, parameters):
                return {
                    "media_key": MEDIA_KEY,
                    "media_state": "uploaded",
                    "original_blob_name": ORIGINAL_BLOB,
                    "safe_blob_name": ORIGINAL_BLOB,
                    "content_type": XLSX_CONTENT_TYPE,
                    "display_name": "gate-tracker.xlsx",
                    "byte_length": len(data),
                    "sha256": hashlib.sha256(data).digest(),
                }

            def first_result(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return []

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_RejectPublicCommunityMedia":
                    return {"outcome": "failed", "media_state": "failed"}
                raise AssertionError(f"Unexpected procedure: {procedure}")

        class Storage:
            def scan_result(self, blob_name):
                return {
                    "result": "clean",
                    "scan_time_utc": datetime(2026, 8, 1, 12, 0),
                }

            def download(self, blob_name):
                return {
                    "data": data,
                    "byte_length": len(data),
                    "content_type": XLSX_CONTENT_TYPE,
                }

        database = Database()
        with self.assertRaises(CommunityValidationError):
            CommunityMediaService(database, Storage()).reconcile(
                OWNER_KEY, MEDIA_KEY
            )
        self.assertTrue(
            any(
                procedure == "usp_RejectPublicCommunityMedia"
                for procedure, _ in database.calls
            )
        )

    def test_xlsx_is_download_only_and_response_headers_are_safe(self):
        data = workbook_bytes()

        class Database:
            def first_row(self, procedure, parameters):
                return {
                    "content_type": XLSX_CONTENT_TYPE,
                    "display_name": "gate-tracker.xlsx",
                    "original_blob_name": ORIGINAL_BLOB,
                    "safe_blob_name": ORIGINAL_BLOB,
                    "safe_byte_length": len(data),
                    "safe_sha256": hashlib.sha256(data).digest(),
                }

        class Storage:
            def download(self, blob_name):
                raise AssertionError("Preview rejection must precede Blob access")

        with self.assertRaises(CommunityNotFoundError):
            CommunityMediaService(Database(), Storage()).public_file(
                MEDIA_KEY, preview=True
            )

        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
        )
        app.register_blueprint(community_api)
        with patch(
            "community_api.community_media_service.public_file",
            return_value={
                "data": data,
                "content_type": XLSX_CONTENT_TYPE,
                "display_name": "資料.xlsx",
                "inline": False,
            },
        ):
            response = app.test_client().get(
                f"/api/v1/community/attachments/{MEDIA_KEY}/download"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, XLSX_CONTENT_TYPE)
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn(
            "filename=attachment.xlsx", response.headers["Content-Disposition"]
        )
        self.assertIn("filename*=UTF-8''", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
