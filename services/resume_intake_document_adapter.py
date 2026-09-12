"""Bounded document-only intake adapter for MVP1 increment C.

This deliberately reuses the *document-only* seam in
``services/my_opportunities/member_import_service.py`` -- its declared-MIME
allowlist, magic-byte sniff, hostile-character refusal and isolated
decode/parse/extract pipeline -- and excludes that module's URL fetching and
opportunity records entirely. The adapter owns no canonical fact and calls no
network: bytes in, bounded text out.

The pipeline is injectable so a test can install a deterministic parser that
records exactly which bytes it received. Nothing is retained: the adapter
hashes the admitted bytes for provenance and drops them.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone

from services.my_opportunities.member_import_service import (
    OUTCOME_EMPTY,
    OUTCOME_EXTRACTED,
    OUTCOME_PARTIAL,
    MemberImportServiceError,
    _run_pipeline,
    validate_upload,
)


_OUTCOME_MESSAGES = {
    "unsupported_type": "That file type is not supported. Use a PDF, Word document, or plain text file.",
    "too_large": "That file is larger than this entrance allows.",
    "upload_required": "Choose a file to upload.",
    "could_not_decode": "That file could not be read. It may be encrypted or damaged.",
    "parser_failure": "That file could not be parsed. Try exporting it again or use the text.",
    "parser_resource_bounds": "That file was too complex to read safely.",
    "archive_bomb_suspected": "That file was too complex to read safely.",
    "hostile_characters": "That text could not be read safely.",
    "output_truncated": "Only part of that document could be read.",
    "extraction_deadline": "Reading that file took too long.",
    "empty": "No selectable text was found in that file. If it is a scan, the text cannot be read yet.",
}


class DocumentIntakeError(RuntimeError):
    """A pre-admission refusal. No bytes were admitted as member material."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.member_message = message or _OUTCOME_MESSAGES.get(
            code, "That file could not be read."
        )
        super().__init__(code)


@dataclass(frozen=True)
class DocumentParseResult:
    admitted: bool
    ok: bool
    outcome: str
    reason: str | None
    text: str | None
    truncated: bool
    content_type: str
    byte_length: int
    sha256: str
    member_message: str

    def as_receipt(self) -> dict:
        return {
            "kind": "document",
            "content_type": self.content_type,
            "byte_length": self.byte_length,
            "sha256": self.sha256,
            "outcome": self.outcome,
            "reason": self.reason,
            "truncated": self.truncated,
            "readable_text": bool(self.text),
            "message": self.member_message,
        }


class _BytesUpload:
    """Minimal upload shape the shared validator expects."""

    def __init__(self, content_type: str, data: bytes) -> None:
        self.mimetype = content_type
        self.stream = io.BytesIO(data)


class ResumeDocumentAdapter:
    """Owner-neutral, Windows/Linux-safe bounded document reader."""

    def __init__(self, pipeline=None) -> None:
        # ``pipeline`` is the deterministic recording seam used in tests.
        self._pipeline = pipeline

    @staticmethod
    def read_bounded(upload, policy) -> bytes:
        """Read at most ``policy.max_document_bytes`` bytes plus one sentinel."""

        stream = getattr(upload, "stream", None)
        if stream is None:
            raise DocumentIntakeError("upload_required")
        data = stream.read(policy.max_document_bytes + 1)
        if len(data) > policy.max_document_bytes:
            raise DocumentIntakeError("too_large")
        if not data:
            raise DocumentIntakeError("upload_required")
        return data

    def admit(self, upload, policy) -> tuple[str, bytes]:
        """Declared-type allowlist plus magic-byte sniff via the shared seam."""

        data = self.read_bounded(upload, policy)
        declared = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0].strip()
        if declared not in policy.allowed_document_types:
            raise DocumentIntakeError("unsupported_type")
        limits = policy.import_limits()
        try:
            validate_upload(_BytesUpload(declared, data), limits)
        except MemberImportServiceError as error:
            raise DocumentIntakeError(error.failure_code, error.member_message) from error
        return declared, data

    def parse(
        self,
        content_type: str,
        data: bytes,
        policy,
        *,
        pipeline=None,
        now: datetime | None = None,
    ) -> DocumentParseResult:
        """Run the bounded decode/parse/extract pipeline over admitted bytes."""

        limits = policy.import_limits()
        runner = pipeline or self._pipeline or _run_pipeline
        moment = now or datetime.now(timezone.utc)
        digest = hashlib.sha256(data).hexdigest()
        try:
            text, outcome, reason, truncated, _trail = runner(
                "resume-intake", "resume-intake-source", content_type, data,
                limits=limits, now=moment,
            )
        except Exception:  # noqa: BLE001 - provider-neutral boundary
            # The shared pipeline reports post-admission outcomes as values.
            # Anything raised here is an environment failure, never a
            # malformed-document claim, so it stays retryable.
            return DocumentParseResult(
                admitted=True, ok=False, outcome="failed", reason="parser_unavailable",
                text=None, truncated=False, content_type=content_type,
                byte_length=len(data), sha256=digest,
                member_message="That file could not be read right now. Try again, or keep typing.",
            )
        if outcome in {OUTCOME_EXTRACTED, OUTCOME_PARTIAL} and text:
            return DocumentParseResult(
                admitted=True, ok=True, outcome=outcome, reason=reason, text=text,
                truncated=bool(truncated), content_type=content_type,
                byte_length=len(data), sha256=digest,
                member_message=(
                    _OUTCOME_MESSAGES["output_truncated"] if truncated else "Read."
                ),
            )
        message = _OUTCOME_MESSAGES.get(reason or "", None)
        if message is None:
            message = (
                _OUTCOME_MESSAGES["empty"]
                if outcome == OUTCOME_EMPTY
                else _OUTCOME_MESSAGES["parser_failure"]
            )
        return DocumentParseResult(
            admitted=True, ok=False, outcome=outcome, reason=reason, text=None,
            truncated=bool(truncated), content_type=content_type,
            byte_length=len(data), sha256=digest, member_message=message,
        )


resume_document_adapter = ResumeDocumentAdapter()
