"""Create the immutable manifest for one PeerSlate candidate artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    from scripts.release_identity import (
        BUILD_ID_PATTERN,
        SOURCE_VERSION_PATTERN,
        release_id_for_build,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from release_identity import (
        BUILD_ID_PATTERN,
        SOURCE_VERSION_PATTERN,
        release_id_for_build,
    )


SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$')
SOURCE_BRANCH_PATTERN = re.compile(r'^refs/heads/[A-Za-z0-9._/-]{1,240}$')
PYTHON_VERSION_PATTERN = re.compile(r'^[0-9]+(?:\.[0-9]+){1,2}$')


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    archive: Path,
    *,
    source_version: str,
    source_branch: str,
    build_id: str,
    python_version: str,
) -> dict[str, object]:
    normalized_source = source_version.strip().lower()
    normalized_branch = source_branch.strip()
    normalized_build = build_id.strip()
    normalized_python = python_version.strip()

    if not archive.is_file():
        raise ValueError(f'artifact does not exist: {archive}')
    if not SOURCE_VERSION_PATTERN.fullmatch(normalized_source):
        raise ValueError('source version must be a full 40-character Git SHA')
    if not SOURCE_BRANCH_PATTERN.fullmatch(normalized_branch):
        raise ValueError('source branch must be a refs/heads branch')
    if not BUILD_ID_PATTERN.fullmatch(normalized_build):
        raise ValueError('build ID contains unsupported characters')
    if not PYTHON_VERSION_PATTERN.fullmatch(normalized_python):
        raise ValueError('Python version must contain only numeric components')

    artifact_hash = sha256_file(archive)
    if not SHA256_PATTERN.fullmatch(artifact_hash):
        raise ValueError('artifact hash generation failed')

    return {
        'schema_version': 1,
        'source_version': normalized_source,
        'source_branch': normalized_branch,
        'build_id': normalized_build,
        'release': release_id_for_build(normalized_source, normalized_build),
        'artifact_name': archive.name,
        'artifact_sha256': artifact_hash,
        'python_version': normalized_python,
    }


def write_manifest(
    archive: Path,
    output: Path,
    *,
    source_version: str,
    source_branch: str,
    build_id: str,
    python_version: str,
) -> dict[str, object]:
    manifest = build_manifest(
        archive,
        source_version=source_version,
        source_branch=source_branch,
        build_id=build_id,
        python_version=python_version,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    checksum_path = output.with_suffix(output.suffix + '.sha256')
    checksum_path.write_text(
        f"{manifest['artifact_sha256']}  {manifest['artifact_name']}\n",
        encoding='ascii',
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Create an immutable PeerSlate candidate manifest.',
    )
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-version', required=True)
    parser.add_argument('--source-branch', required=True)
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--python-version', required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = write_manifest(
            args.archive,
            args.output,
            source_version=args.source_version,
            source_branch=args.source_branch,
            build_id=args.build_id,
            python_version=args.python_version,
        )
    except (OSError, ValueError) as error:
        print(f'Candidate manifest generation failed: {error}', file=sys.stderr)
        return 1

    print(
        'Candidate artifact manifest generated: '
        f"{manifest['artifact_name']} sha256={manifest['artifact_sha256']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
