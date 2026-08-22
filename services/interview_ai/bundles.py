"""Immutable bundle catalog loading for Interview AI.

A released bundle directory holds the four §2 identity files plus a
manifest. Loading re-verifies the recorded full content hash against the
committed bytes; a mismatch is a hard failure, never a fallback.
"""

import json
import re

from services.interview_ai.identity import (
    BUNDLE_FILE_ORDER,
    bundle_content_sha256,
)

_SEGMENT_OPEN = re.compile(rb"<<<SEGMENT ([a-z_]+)>>>\n")

REQUIRED_SEGMENTS = {
    "coach": ("system_template", "user_template"),
    "revision": ("system_template", "user_template"),
    "planning_hints": ("system_template", "user_template"),
    "grounded_example": (
        "system_template",
        "user_template",
        "followup_suffix_template",
    ),
    "generic_example": (
        "system_template",
        "user_template",
        "followup_suffix_template",
        "followup_prior_best_practice_template",
        "followup_prior_compare_template",
    ),
}


class BundleError(ValueError):
    """A bundle directory is malformed or fails identity verification."""


def parse_instruction_segments(instruction_bytes):
    """Extract named segments as exact bytes per instruction-format@1.

    A segment's content is the bytes between the byte after the open
    marker's newline and the byte immediately before the newline that
    precedes its END marker. No normalization occurs.
    """
    segments = {}
    for match in _SEGMENT_OPEN.finditer(instruction_bytes):
        name = match.group(1).decode("ascii")
        if name in segments:
            raise BundleError("duplicate instruction segment: %s" % name)
        end_marker = b"\n<<<END " + match.group(1) + b">>>"
        end = instruction_bytes.find(end_marker, match.end())
        if end == -1:
            raise BundleError("unterminated instruction segment: %s" % name)
        segments[name] = instruction_bytes[match.end():end].decode("utf-8")
    return segments


class Bundle:
    """One verified, immutable bundle."""

    def __init__(self, specialist, semver, bundle_label, content_sha256,
                 segments, provider, path):
        self.specialist = specialist
        self.semver = semver
        self.bundle_label = bundle_label
        self.content_sha256 = content_sha256
        self.segments = segments
        self.provider = provider
        self.path = path

    @property
    def model(self):
        return self.provider["model"]

    @property
    def max_tokens(self):
        return self.provider["max_tokens"]


def load_bundle(directory, expected_specialist=None):
    """Load and verify one bundle directory."""
    files = {}
    for name in BUNDLE_FILE_ORDER:
        file_path = directory / name
        if not file_path.is_file():
            raise BundleError("bundle file missing: %s" % file_path)
        files[name] = file_path.read_bytes()

    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise BundleError("bundle manifest missing: %s" % manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    computed = bundle_content_sha256(files)
    if manifest.get("bundle_content_sha256") != computed:
        raise BundleError(
            "bundle content hash does not recompute for %s" % directory
        )
    specialist = manifest.get("specialist")
    if expected_specialist is not None and specialist != expected_specialist:
        raise BundleError("bundle specialist mismatch in %s" % directory)
    if specialist not in REQUIRED_SEGMENTS:
        raise BundleError("unknown bundle specialist in %s" % directory)

    expected_label = "%s+%s" % (manifest.get("semver"), computed[:8])
    if manifest.get("bundle_label") != expected_label:
        raise BundleError("bundle label mismatch in %s" % directory)
    if directory.name != expected_label:
        raise BundleError("bundle directory name mismatch in %s" % directory)

    if files["constitution.md"] != b"":
        raise BundleError(
            "slice-1 constitution must be zero bytes in %s" % directory
        )

    segments = parse_instruction_segments(files["instruction.md"])
    required = REQUIRED_SEGMENTS[specialist]
    if set(segments) != set(required):
        raise BundleError(
            "bundle %s segments are %s, expected %s"
            % (directory, sorted(segments), sorted(required))
        )

    provider = json.loads(files["provider.json"].decode("utf-8"))
    if provider.get("provider") != "anthropic-messages":
        raise BundleError("unsupported provider in %s" % directory)
    if provider.get("explicit_parameters") != [
        "model", "max_tokens", "system", "messages",
    ]:
        raise BundleError("provider explicit-parameter set drifted in %s" % directory)
    if not isinstance(provider.get("model"), str) or not isinstance(
        provider.get("max_tokens"), int
    ):
        raise BundleError("provider configuration invalid in %s" % directory)

    return Bundle(
        specialist=specialist,
        semver=manifest.get("semver"),
        bundle_label=manifest.get("bundle_label"),
        content_sha256=computed,
        segments=segments,
        provider=provider,
        path=directory,
    )
