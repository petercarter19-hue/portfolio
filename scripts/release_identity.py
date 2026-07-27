"""Create and read the public-safe identity of a deployed PeerSlate build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IDENTITY_PATH = ROOT / 'release_identity.json'
SOURCE_VERSION_PATTERN = re.compile(r'^[0-9a-f]{40}$')
BUILD_ID_PATTERN = re.compile(r'^[A-Za-z0-9._-]{1,128}$')
RELEASE_ID_PATTERN = re.compile(r'^[0-9a-f]{24}$')


def release_id_for_build(source_version: str, build_id: str) -> str:
    """Return an opaque identifier tied to one source SHA and Azure build."""
    normalized_source = source_version.strip().lower()
    normalized_build = build_id.strip()
    if not SOURCE_VERSION_PATTERN.fullmatch(normalized_source):
        raise ValueError('source version must be a full 40-character Git SHA')
    if not BUILD_ID_PATTERN.fullmatch(normalized_build):
        raise ValueError('build ID contains unsupported characters')
    material = (
        f'peerslate-release-v1\0{normalized_source}\0{normalized_build}'
    ).encode('ascii')
    return hashlib.sha256(material).hexdigest()[:24]


def build_identity(source_version: str, build_id: str) -> dict[str, object]:
    normalized_source = source_version.strip().lower()
    normalized_build = build_id.strip()
    return {
        'schema_version': 1,
        'source_version': normalized_source,
        'build_id': normalized_build,
        'release': release_id_for_build(normalized_source, normalized_build),
    }


def write_identity(
    source_version: str,
    build_id: str,
    path: Path = DEFAULT_IDENTITY_PATH,
) -> dict[str, object]:
    identity = build_identity(source_version, build_id)
    path.write_text(
        json.dumps(identity, indent=2) + '\n',
        encoding='utf-8',
    )
    return identity


def load_release_id(path: Path = DEFAULT_IDENTITY_PATH) -> str:
    """Read the packaged release ID, or a fail-obvious local fallback."""
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 'unversioned'
    if not isinstance(payload, dict):
        return 'unversioned'
    release_id = payload.get('release')
    if not isinstance(release_id, str):
        return 'unversioned'
    if not RELEASE_ID_PATTERN.fullmatch(release_id):
        return 'unversioned'
    return release_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate the packaged PeerSlate release identity.',
    )
    parser.add_argument(
        '--source-version',
        default=os.environ.get('BUILD_SOURCEVERSION'),
    )
    parser.add_argument(
        '--build-id',
        default=os.environ.get('BUILD_BUILDID'),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=DEFAULT_IDENTITY_PATH,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.source_version is None:
            raise ValueError('source version is required')
        if args.build_id is None:
            raise ValueError('build ID is required')
        identity = write_identity(
            args.source_version,
            args.build_id,
            args.output,
        )
    except (OSError, ValueError) as error:
        print(f'Release identity generation failed: {error}', file=sys.stderr)
        return 1

    print(f"Release identity generated: {identity['release']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
