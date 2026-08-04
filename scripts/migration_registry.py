"""The PeerSlate schema migration registry: ordering, gate proofs, and state.

This module is deliberately pure. It reads files, hashes bytes, and computes
sets. It never opens a database connection and never reads a credential, so the
whole of it is unit-testable offline and runs in CI on every build.

`scripts/govern_sql_migrations.py` is the operational entry point that pairs
this logic with a connection.

Three ideas carry the whole design:

1. `SQL FIles/Migrations/registry.json` is the ordered inventory of every
   migration this repository knows about. It records identity, file location,
   rollback file, prerequisites, and a gate proof. It deliberately does NOT
   record whether a migration is applied anywhere. Applied-ness is a property
   of a database, so it is read from `dbo.schema_migrations` at run time and
   never asserted by a file that can drift.

2. A migration may be applied only when its registry entry carries a gate proof
   whose `executable_sha256` still matches the file on disk. The hash covers the
   executable body -- everything after the leading block comment -- so header
   prose may be corrected without invalidating the proof, while a single changed
   character of T-SQL invalidates it and the applier fails closed.

3. The repository's record of what a database carries is rendered by
   `render_state`, byte-for-byte deterministically, from a live ledger read. It
   is regenerated rather than edited, and `--check-state` re-renders and
   compares, so a hand edit is detected instead of believed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "SQL FIles" / "Migrations"
REGISTRY_PATH = MIGRATION_DIR / "registry.json"
STATE_PATH = ROOT / "docs" / "governance" / "PRODUCTION_SCHEMA_STATE.md"

REGISTRY_VERSION = 1

STATE_BANNER = (
    "<!-- GENERATED FILE. Do not edit by hand. Regenerate with: "
    "python scripts/govern_sql_migrations.py report "
    "--expect-database <name> --write-state -->"
)

#: Databases a gate run must never target. A gate exists to rehearse a
#: migration somewhere disposable; pointing it at the real database would
#: defeat the entire control.
FORBIDDEN_GATE_DATABASES = frozenset(
    {
        "peerslate-database",
        "peerslate-staging",
    }
)


class RegistryError(RuntimeError):
    """The registry is malformed, inconsistent, or contradicts the files."""


@dataclass(frozen=True)
class GateProof:
    """Evidence that this exact T-SQL ran successfully somewhere disposable."""

    executable_sha256: str
    gated_at_utc: str
    gate_database: str
    gate_server: str
    prerequisites: tuple[str, ...]
    objects: tuple[str, ...]
    verification: str
    operator: str
    notes: str = ""

    @classmethod
    def from_json(cls, migration_id: str, payload: dict) -> "GateProof":
        required = (
            "executable_sha256",
            "gated_at_utc",
            "gate_database",
            "gate_server",
            "prerequisites",
            "objects",
            "verification",
            "operator",
        )
        missing = [key for key in required if key not in payload]
        if missing:
            raise RegistryError(
                f"{migration_id}: gate proof is missing "
                + ", ".join(sorted(missing))
                + "."
            )
        digest = str(payload["executable_sha256"])
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RegistryError(
                f"{migration_id}: gate proof executable_sha256 is not a "
                "lowercase 64-character SHA-256 digest."
            )
        gate_database = str(payload["gate_database"])
        if gate_database in FORBIDDEN_GATE_DATABASES:
            raise RegistryError(
                f"{migration_id}: gate proof names {gate_database}, which is "
                "not a throwaway database. A gate proof recorded against a "
                "real database proves nothing."
            )
        return cls(
            executable_sha256=digest,
            gated_at_utc=str(payload["gated_at_utc"]),
            gate_database=gate_database,
            gate_server=str(payload["gate_server"]),
            prerequisites=tuple(str(item) for item in payload["prerequisites"]),
            objects=tuple(str(item) for item in payload["objects"]),
            verification=str(payload["verification"]),
            operator=str(payload["operator"]),
            notes=str(payload.get("notes", "")),
        )

    def to_json(self) -> dict:
        payload = {
            "executable_sha256": self.executable_sha256,
            "gated_at_utc": self.gated_at_utc,
            "gate_database": self.gate_database,
            "gate_server": self.gate_server,
            "prerequisites": list(self.prerequisites),
            "objects": list(self.objects),
            "verification": self.verification,
            "operator": self.operator,
        }
        if self.notes:
            payload["notes"] = self.notes
        return payload


@dataclass(frozen=True)
class Migration:
    """One registered migration and the order it occupies."""

    migration_id: str
    position: int
    forward: str
    rollback: str
    requires: tuple[str, ...]
    summary: str
    gate: GateProof | None

    @property
    def is_gated(self) -> bool:
        return self.gate is not None

    def forward_path(self, root: Path = ROOT) -> Path:
        return root / self.forward

    def rollback_path(self, root: Path = ROOT) -> Path:
        return root / self.rollback

    def to_json(self) -> dict:
        return {
            "id": self.migration_id,
            "forward": self.forward,
            "rollback": self.rollback,
            "requires": list(self.requires),
            "summary": self.summary,
            "gate": self.gate.to_json() if self.gate else None,
        }


def executable_body(text: str) -> str:
    """Return the part of a migration a database actually executes.

    Leading block comments are stripped. Everything else -- including any
    comment that appears after the first statement -- is retained, so the digest
    changes whenever the T-SQL changes.

    Line endings are normalized to LF and surrounding whitespace removed so a
    checkout that rewrites CRLF cannot invalidate a gate proof.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    while True:
        stripped = normalized.lstrip()
        if not stripped.startswith("/*"):
            break
        close = stripped.find("*/")
        if close == -1:
            # An unterminated leading comment is not a header; treat the whole
            # remaining text as executable rather than silently dropping it.
            break
        normalized = stripped[close + 2 :]
    return normalized.strip()


def executable_sha256(path: Path) -> str:
    body = executable_body(path.read_text(encoding="utf-8"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class Registry:
    """The ordered migration inventory."""

    def __init__(self, migrations: list[Migration], source: Path) -> None:
        self._migrations = migrations
        self._by_id = {item.migration_id: item for item in migrations}
        self.source = source

    def __iter__(self):
        return iter(self._migrations)

    def __len__(self) -> int:
        return len(self._migrations)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(item.migration_id for item in self._migrations)

    def get(self, migration_id: str) -> Migration:
        try:
            return self._by_id[migration_id]
        except KeyError:
            raise RegistryError(
                f"{migration_id} is not in {self.source.name}. Register a "
                "migration before it can be applied or rolled back."
            ) from None

    def contains(self, migration_id: str) -> bool:
        return migration_id in self._by_id

    def pending(self, applied_ids) -> list[Migration]:
        """Registered migrations the target database does not carry, in order.

        The answer comes from the live ledger, never from a hardcoded list.
        """

        applied = set(applied_ids)
        return [
            item for item in self._migrations if item.migration_id not in applied
        ]

    def unregistered(self, applied_ids) -> list[str]:
        """Ledger rows this repository cannot explain.

        A database carrying a migration the repository does not register is a
        real finding: something was applied out of band.
        """

        return sorted(
            str(item) for item in applied_ids if item not in self._by_id
        )


def _validate_entry(index: int, raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise RegistryError(f"Entry {index} is not an object.")
    for key in ("id", "forward", "rollback", "requires", "summary"):
        if key not in raw:
            raise RegistryError(f"Entry {index} is missing '{key}'.")
    if "gate" not in raw:
        raise RegistryError(
            f"Entry {index} ({raw['id']}) is missing 'gate'. Use null to "
            "register a migration that has not been gated yet; omitting the "
            "key hides the distinction."
        )
    return raw


def load_registry(
    path: Path | None = None,
    root: Path = ROOT,
    require_files: bool = True,
) -> Registry:
    """Load, validate, and return the registry.

    Every check here is fail-closed. A registry that cannot be fully validated
    raises rather than returning a partially trusted inventory.
    """

    registry_path = path or REGISTRY_PATH
    if not registry_path.exists():
        raise RegistryError(f"Migration registry is missing: {registry_path}")

    try:
        document = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RegistryError(
            f"{registry_path.name} is not valid JSON: {error}"
        ) from error

    if document.get("version") != REGISTRY_VERSION:
        raise RegistryError(
            f"{registry_path.name} declares version "
            f"{document.get('version')!r}; this tool understands "
            f"{REGISTRY_VERSION}."
        )

    entries = document.get("migrations")
    if not isinstance(entries, list) or not entries:
        raise RegistryError(f"{registry_path.name} lists no migrations.")

    migrations: list[Migration] = []
    seen: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw in enumerate(entries):
        raw = _validate_entry(index, raw)
        migration_id = str(raw["id"])
        if migration_id in seen:
            raise RegistryError(f"{migration_id} is registered more than once.")
        seen.add(migration_id)

        forward = str(raw["forward"])
        rollback = str(raw["rollback"])
        for candidate in (forward, rollback):
            if candidate in seen_paths:
                raise RegistryError(
                    f"{migration_id}: {candidate} is claimed by more than one "
                    "registry entry."
                )
            seen_paths.add(candidate)
            if "\\" in candidate:
                raise RegistryError(
                    f"{migration_id}: registry paths use forward slashes so "
                    f"they resolve on every platform; found {candidate!r}."
                )

        requires = tuple(str(item) for item in raw["requires"])
        unknown = [item for item in requires if item not in seen]
        if unknown:
            raise RegistryError(
                f"{migration_id} requires "
                + ", ".join(unknown)
                + ", which is not registered before it. The registry order is "
                "the apply order, so a prerequisite must appear earlier."
            )

        gate_payload = raw["gate"]
        gate = (
            GateProof.from_json(migration_id, gate_payload)
            if gate_payload is not None
            else None
        )

        migration = Migration(
            migration_id=migration_id,
            position=index,
            forward=forward,
            rollback=rollback,
            requires=requires,
            summary=str(raw["summary"]),
            gate=gate,
        )

        if require_files:
            for candidate in (
                migration.forward_path(root),
                migration.rollback_path(root),
            ):
                if not candidate.exists():
                    raise RegistryError(
                        f"{migration_id}: registered file is missing: "
                        f"{candidate}"
                    )

        migrations.append(migration)

    return Registry(migrations, registry_path)


def gate_status(migration: Migration, root: Path = ROOT) -> tuple[bool, str]:
    """Answer the only question that gates an apply.

    Returns (ok, reason). `ok` is True only when the migration carries a gate
    proof whose digest still matches the T-SQL on disk.
    """

    if migration.gate is None:
        return (
            False,
            f"{migration.migration_id} has no gate proof. It has not been "
            "proven against a throwaway database, so this path will not apply "
            "it. Run the gate first: python scripts/govern_sql_migrations.py "
            "gate --migration " + migration.migration_id,
        )

    path = migration.forward_path(root)
    if not path.exists():
        return False, f"{migration.migration_id}: {path} is missing."

    actual = executable_sha256(path)
    if actual != migration.gate.executable_sha256:
        return (
            False,
            f"{migration.migration_id}: the T-SQL on disk does not match the "
            "gated bytes. Gated "
            f"{migration.gate.executable_sha256}, found {actual}. The file "
            "changed after it was gated; re-gate it before applying.",
        )

    return True, f"{migration.migration_id}: gate proof matches the file."


def resolve_apply_plan(
    registry: Registry,
    applied_ids,
    only: tuple[str, ...] = (),
    root: Path = ROOT,
) -> tuple[list[Migration], list[str], list[Migration]]:
    """Return (plan, blockers, held) for a forward apply.

    `plan` is the ordered list of migrations that would run. `blockers` is every
    reason the run must not proceed at all; a non-empty `blockers` means fail
    closed, and the caller must not apply a partial plan. `held` is the pending
    migrations this run deliberately leaves alone because they carry no valid
    gate proof.

    An ungated pending migration is not an error on its own. The registry lists
    every migration this repository knows about, including ones that are merely
    drafted, so ungated entries are normal and permanent. They become an error
    only when the operator names one explicitly, or when a migration in the plan
    actually depends on one.
    """

    applied = set(applied_ids)
    pending = registry.pending(applied)
    blockers: list[str] = []
    held: list[Migration] = []

    if only:
        unknown = [item for item in only if not registry.contains(item)]
        if unknown:
            blockers.append(
                "Not registered: " + ", ".join(sorted(unknown)) + "."
            )
        already = [item for item in only if item in applied]
        if already:
            blockers.append(
                "Already recorded in the target ledger: "
                + ", ".join(sorted(already))
                + "."
            )
        candidates = [item for item in pending if item.migration_id in only]
        # An explicitly named migration must be gated. Silently dropping it
        # would turn a specific instruction into a surprise no-op.
        selected = []
        for migration in candidates:
            ok, reason = gate_status(migration, root)
            if ok:
                selected.append(migration)
            else:
                blockers.append(reason)
    else:
        selected = []
        for migration in pending:
            ok, _ = gate_status(migration, root)
            if ok:
                selected.append(migration)
            else:
                held.append(migration)

    # Prerequisites must already be present, or be applied earlier in this same
    # run. Each migration also guards itself with a THROW, but failing here
    # produces a plan the operator can read instead of a raw SQL error code.
    will_have = set(applied)
    for migration in selected:
        unmet = [item for item in migration.requires if item not in will_have]
        if unmet:
            blockers.append(
                f"{migration.migration_id} requires "
                + ", ".join(unmet)
                + ", which the target does not carry and this run cannot "
                "apply. A prerequisite that is pending and ungated blocks "
                "everything that depends on it."
            )
        will_have.add(migration.migration_id)

    return selected, blockers, held


def _json_block(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def render_state(
    registry: Registry,
    database: str,
    server: str,
    ledger_rows: list[dict],
    generated_at_utc: str,
    source_version: str = "",
    build_id: str = "",
    root: Path = ROOT,
) -> str:
    """Render the repository's record of what a database carries.

    Deterministic: the same inputs always produce the same bytes, so the file
    can be regenerated and byte-compared rather than reviewed by eye.
    """

    rows = sorted(ledger_rows, key=lambda row: str(row["migration_id"]))
    applied_ids = [str(row["migration_id"]) for row in rows]
    pending = registry.pending(applied_ids)
    unregistered = registry.unregistered(applied_ids)

    ordered_applied = [
        item.migration_id
        for item in registry
        if item.migration_id in set(applied_ids)
    ]

    document = {
        "database": database,
        "server": server,
        "generated_at_utc": generated_at_utc,
        "pipeline_source_version": source_version,
        "pipeline_build_id": build_id,
        "registry_version": REGISTRY_VERSION,
        "applied": [
            {
                "id": str(row["migration_id"]),
                "applied_at_utc": str(row["applied_at_utc"]),
                "registered": registry.contains(str(row["migration_id"])),
            }
            for row in rows
        ],
        "pending": [item.migration_id for item in pending],
        "unregistered_in_ledger": unregistered,
    }

    lines = [
        STATE_BANNER,
        "",
        f"# Production schema state: `{database}`",
        "",
        "This file is the repository's record of which schema migrations the "
        "named database carries. It is **generated from a live read of "
        "`dbo.schema_migrations`** by the governed migration path, never "
        "written by hand, and `--check-state` re-renders it and compares "
        "byte-for-byte. If you are reading a claim about database schema "
        "anywhere else in this repository -- a migration header, a completion "
        "report, a package README -- that claim is prose and this file is the "
        "record.",
        "",
        f"- Database: `{database}`",
        f"- Server: `{server}`",
        f"- Read at: `{generated_at_utc}` UTC",
    ]
    if source_version:
        lines.append(f"- Pipeline source version: `{source_version}`")
    if build_id:
        lines.append(f"- Pipeline build: `{build_id}`")
    lines.extend(
        [
            "",
            f"## Applied ({len(ordered_applied)})",
            "",
            "In registry order.",
            "",
            "| # | Migration | Applied (UTC) | Registered |",
            "| --- | --- | --- | --- |",
        ]
    )
    by_id = {str(row["migration_id"]): row for row in rows}
    for number, migration_id in enumerate(ordered_applied, start=1):
        row = by_id[migration_id]
        lines.append(
            f"| {number} | `{migration_id}` | "
            f"{row['applied_at_utc']} | yes |"
        )
    if unregistered:
        for migration_id in unregistered:
            row = by_id[migration_id]
            lines.append(
                f"| - | `{migration_id}` | {row['applied_at_utc']} | "
                "**NO - applied out of band** |"
            )

    lines.extend(["", f"## Registered but not applied ({len(pending)})", ""])
    if pending:
        lines.append("| Migration | Gate proof | Summary |")
        lines.append("| --- | --- | --- |")
        for item in pending:
            ok, _ = gate_status(item, root)
            gate_cell = "matches file" if ok else "**none or stale**"
            lines.append(
                f"| `{item.migration_id}` | {gate_cell} | {item.summary} |"
            )
    else:
        lines.append("None. The database carries every registered migration.")

    if unregistered:
        lines.extend(
            [
                "",
                "## Ledger rows this repository cannot explain",
                "",
                "These migration ids are recorded in the database but are not "
                "in `SQL FIles/Migrations/registry.json`. Something was "
                "applied outside this path. Investigate before the next apply.",
                "",
            ]
        )
        for migration_id in unregistered:
            lines.append(f"- `{migration_id}`")

    lines.extend(
        [
            "",
            "## Machine-readable record",
            "",
            "```json",
            _json_block(document),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_state(text: str) -> dict:
    """Extract the machine-readable record from a rendered state file."""

    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise RegistryError(
            "The state file has no machine-readable JSON block. It was hand "
            "edited or truncated; regenerate it."
        )
    return json.loads(match.group(1))
