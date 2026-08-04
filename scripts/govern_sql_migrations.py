"""The governed path for moving PeerSlate database schema.

Application code has had a reviewed, gated, auditable route to production for a
long time: PR, CI, Azure pipeline, release record. Database schema has not. Every
schema change until now was applied by hand, by an agent holding a credential it
read out of App Service settings, guided by prose. Each apply was careful. None
of them was controlled.

This script is that control. It is the only supported way to move PeerSlate
schema, and it runs from the Azure pipeline's `SchemaMigration` stage.

    check      Validate the registry against the files. No connection. Runs in CI.
    report     Read the ledger and write the repository's record. Changes nothing.
    gate       Prove a migration against a throwaway database and emit its proof.
    apply      Apply every pending, gated migration in registry order.
    rollback   Reverse the most recently applied migration, deliberately awkwardly.

Design rules this file enforces:

* Nothing applies automatically. `apply` runs only when a human queues it.
* Pending is computed from `dbo.schema_migrations`, never from a hardcoded list.
* A migration without a matching gate proof is refused, not warned about.
* Every failure stops the run and reports the ledger as it actually stands.
* A no-op is reported as a no-op, loudly, so it can never read as an apply.
* The connection string is read from the environment, never printed, and never
  written to disk. Errors are scrubbed before they are shown.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402

from apply_sql_migrations import get_connection  # noqa: E402  house connection
import migration_registry as registry_module  # noqa: E402
from migration_registry import (  # noqa: E402
    FORBIDDEN_GATE_DATABASES,
    GateProof,
    Migration,
    Registry,
    RegistryError,
    STATE_PATH,
    executable_sha256,
    gate_status,
    load_registry,
    parse_state,
    render_state,
    resolve_apply_plan,
)

ROOT = registry_module.ROOT
VERIFICATION_DIR = ROOT / "SQL FIles" / "Verification"

LEDGER_QUERY = (
    "IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL "
    "SELECT CONVERT(nvarchar(100), NULL) AS migration_id, "
    "CONVERT(nvarchar(50), NULL) AS applied_at_utc WHERE 1 = 0; "
    "ELSE SELECT migration_id, "
    "CONVERT(nvarchar(50), applied_at_utc, 126) AS applied_at_utc "
    "FROM dbo.schema_migrations ORDER BY migration_id;"
)

# sys.objects columns carry the catalog collation, which need not match the
# database collation. Force every component to the database default so the
# concatenation and the sort work on any server this ever runs against.
OBJECT_INVENTORY_QUERY = (
    "SELECT CONCAT("
    "o.type_desc COLLATE DATABASE_DEFAULT, N':', "
    "s.name COLLATE DATABASE_DEFAULT, N'.', "
    "o.name COLLATE DATABASE_DEFAULT) AS object_name "
    "FROM sys.objects AS o "
    "JOIN sys.schemas AS s ON s.schema_id = o.schema_id "
    "WHERE o.is_ms_shipped = 0 AND s.name = N'dbo' "
    "ORDER BY object_name;"
)


class GovernedMigrationError(RuntimeError):
    """A governed run must stop."""


# --------------------------------------------------------------------------
# Credential handling
# --------------------------------------------------------------------------


def _secret_values() -> list[str]:
    """Every value that must never reach stdout or an artifact."""

    raw = os.getenv("AZURE_SQL_CONNECTIONSTRING") or ""
    values = [raw] if raw else []
    for match in re.finditer(r"(?i)(?:pwd|password)\s*=\s*([^;]+)", raw):
        secret = match.group(1).strip()
        if secret:
            values.append(secret)
            values.append(secret.strip("{}"))
    return values


def scrub(text: str) -> str:
    """Remove anything credential-shaped from a string before printing it."""

    result = str(text)
    for secret in _secret_values():
        if secret and secret in result:
            result = result.replace(secret, "***")
    # Belt and braces: redact the keyword form even if the live value differs
    # from what this process happens to hold.
    return re.sub(
        r"(?i)\b(pwd|password|uid|user id)\s*=\s*[^;]*",
        r"\1=***",
        result,
    )


def _retarget_database(connection_string: str, database: str) -> str:
    """Point an existing connection string at a different database.

    Used only by `gate`, so a throwaway database can be reached with the same
    credential without ever writing a second connection string to disk. The
    substitution is never trusted on its own: every connection is confirmed
    against `DB_NAME()` immediately after it opens.
    """

    replaced, count = re.subn(
        r"(?i)(^|;)\s*(database|initial catalog)\s*=\s*[^;]*",
        lambda match: f"{match.group(1)}Database={database}",
        connection_string,
        count=1,
    )
    if count == 0:
        raise GovernedMigrationError(
            "The configured connection string names no database, so it cannot "
            "be retargeted at a throwaway database."
        )
    return replaced


def open_connection(env_file: Path | None, database: str | None = None):
    """Open a connection, optionally retargeted, using the house pattern.

    Retargeting rewrites the database name in memory. It never opens the
    original connection first -- an operator whose local environment file names
    production must be able to reach a throwaway database without this tool
    touching production on the way there.
    """

    if database is None:
        return get_connection(env_file)

    resolved = env_file or ROOT / ".env"
    if env_file is not None and not resolved.exists():
        raise GovernedMigrationError(
            f"Connection environment file is missing: {resolved}"
        )
    if resolved.exists():
        load_dotenv(resolved, override=env_file is not None)

    connection_string = os.getenv("AZURE_SQL_CONNECTIONSTRING")
    if not connection_string:
        raise GovernedMigrationError("AZURE_SQL_CONNECTIONSTRING is not configured.")

    original = os.environ.get("AZURE_SQL_CONNECTIONSTRING")
    os.environ["AZURE_SQL_CONNECTIONSTRING"] = _retarget_database(
        connection_string, database
    )
    try:
        return get_connection(None)
    finally:
        if original is None:
            os.environ.pop("AZURE_SQL_CONNECTIONSTRING", None)
        else:
            os.environ["AZURE_SQL_CONNECTIONSTRING"] = original


# --------------------------------------------------------------------------
# Database reads
# --------------------------------------------------------------------------


def connect_for(args):
    """Open the connection a command needs, refusing an ambiguous target.

    `--database` retargets the configured connection string. It exists so a gate
    can reach a throwaway database using the same credential, and so an operator
    whose local environment file names production can still run this tool safely.
    It must always agree with `--expect-database`, and the pipeline never passes
    it: there, the secret already names the database the stage is allowed to
    touch.
    """

    override = getattr(args, "database", None)
    expected = getattr(args, "expect_database", None)
    if override is not None and override != expected:
        raise GovernedMigrationError(
            "--database must repeat --expect-database exactly, so a run can "
            f"never be pointed somewhere by accident. Got --database "
            f"{override!r} and --expect-database {expected!r}."
        )
    return open_connection(args.env_file, database=override)


def registry_root(args) -> Path:
    return Path(args.registry_root) if args.registry_root else ROOT


def registry_path(args) -> Path:
    return Path(args.registry) if args.registry else registry_module.REGISTRY_PATH


def load(args) -> Registry:
    """Load the registry this run governs.

    The overrides exist so the focused test suite and a proposed-registry dry
    run can exercise the real code against scratch files. The pipeline passes
    neither, so a production run always governs the committed registry.
    """

    return load_registry(registry_path(args), root=registry_root(args))


def _rows(cursor) -> list[dict]:
    while cursor.description is None:
        if not cursor.nextset():
            return []
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _drain(cursor) -> None:
    while cursor.nextset():
        pass


def identify_target(cursor) -> tuple[str, str]:
    cursor.execute("SELECT DB_NAME() AS database_name, @@SERVERNAME AS server_name;")
    row = _rows(cursor)[0]
    _drain(cursor)
    return str(row["database_name"]), str(row["server_name"])


def confirm_target(cursor, expected_database: str) -> tuple[str, str]:
    """Fail closed unless the open connection is the database asked for.

    A retargeted connection string, a stale variable group, or a copy-paste
    error all end here rather than in the wrong database.
    """

    database, server = identify_target(cursor)
    if database != expected_database:
        raise GovernedMigrationError(
            f"Refusing to continue. This connection is attached to "
            f"{database!r}, but --expect-database is {expected_database!r}."
        )
    return database, server


def read_ledger(cursor) -> list[dict]:
    cursor.execute(LEDGER_QUERY)
    rows = _rows(cursor)
    _drain(cursor)
    return [
        {
            "migration_id": str(row["migration_id"]),
            "applied_at_utc": str(row["applied_at_utc"]),
        }
        for row in rows
        if row.get("migration_id") is not None
    ]


def read_objects(cursor) -> list[str]:
    cursor.execute(OBJECT_INVENTORY_QUERY)
    rows = _rows(cursor)
    _drain(cursor)
    return [str(row["object_name"]) for row in rows]


def execute_script(cursor, path: Path) -> None:
    cursor.execute(path.read_text(encoding="utf-8"))
    _drain(cursor)


# --------------------------------------------------------------------------
# Pipeline-visible reporting
# --------------------------------------------------------------------------


class Reporter:
    """Prints for humans and, in Azure, raises the run's visible result.

    The pipeline already learned once -- with `ProductionReleaseSkipped` -- that
    a run which does nothing must not report a plain success. The same rule
    applies here: a no-op schema run is a legitimate outcome and a surprising
    one, so it is downgraded and labelled rather than left looking like an
    apply.
    """

    def __init__(self, azure: bool) -> None:
        self.azure = azure
        self.warned = False

    def say(self, message: str) -> None:
        print(scrub(message))

    def warn(self, message: str) -> None:
        message = scrub(message)
        print(f"WARNING: {message}")
        if self.azure:
            print(f"##vso[task.logissue type=warning]{message}")
        self.warned = True

    def fail(self, message: str) -> None:
        message = scrub(message)
        print(f"FAILED: {message}")
        if self.azure:
            print(f"##vso[task.logissue type=error]{message}")

    def downgrade(self) -> None:
        if self.azure and self.warned:
            print("##vso[task.complete result=SucceededWithIssues;]")


def write_evidence(path: Path | None, payload: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        scrub(json.dumps(payload, indent=2, sort_keys=True)) + "\n",
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def command_check(args, reporter: Reporter) -> int:
    registry = load(args)
    reporter.say(f"Registry: {registry.source}")
    reporter.say(f"Registered migrations: {len(registry)}")

    problems: list[str] = []
    gated = 0
    for migration in registry:
        if migration.gate is None:
            reporter.say(f"  draft   {migration.migration_id}  (no gate proof)")
            continue
        ok, reason = gate_status(migration, registry_root(args))
        if ok:
            gated += 1
            reporter.say(
                f"  gated   {migration.migration_id}  "
                f"{migration.gate.executable_sha256[:12]}  "
                f"{migration.gate.gate_database}"
            )
        else:
            problems.append(reason)
            reporter.say(f"  STALE   {migration.migration_id}")

    reporter.say(f"Gated and matching the files on disk: {gated}")
    for problem in problems:
        reporter.fail(problem)
    if problems:
        return 1
    reporter.say("Registry is internally consistent and every gate proof matches.")
    return 0


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def _state_for(
    registry: Registry,
    database: str,
    server: str,
    ledger: list[dict],
    generated_at: str,
    root: Path = ROOT,
) -> str:
    return render_state(
        registry,
        database=database,
        server=server,
        ledger_rows=ledger,
        generated_at_utc=generated_at,
        source_version=os.getenv("BUILD_SOURCEVERSION", ""),
        build_id=os.getenv("BUILD_BUILDID", ""),
        root=root,
    )


def _describe_ledger(
    reporter: Reporter,
    registry: Registry,
    ledger: list[dict],
    root: Path = ROOT,
) -> list[Migration]:
    applied_ids = [row["migration_id"] for row in ledger]
    reporter.say(f"Ledger rows: {len(applied_ids)}")
    for row in sorted(ledger, key=lambda item: item["applied_at_utc"]):
        known = "" if registry.contains(row["migration_id"]) else "  UNREGISTERED"
        reporter.say(
            f"  {row['applied_at_utc']}  {row['migration_id']}{known}"
        )
    unregistered = registry.unregistered(applied_ids)
    if unregistered:
        reporter.warn(
            "The target carries migrations this repository does not register: "
            + ", ".join(unregistered)
            + ". Something was applied outside the governed path."
        )
    pending = registry.pending(applied_ids)
    if pending:
        reporter.say(f"Registered but not applied: {len(pending)}")
        for item in pending:
            ok, _ = gate_status(item, root)
            reporter.say(
                f"  {item.migration_id}  "
                + ("gated" if ok else "not gated - held back")
            )
    else:
        reporter.say("The target carries every registered migration.")
    return pending


def _handle_state(
    args,
    reporter: Reporter,
    rendered: str,
    compare_against: str | None = None,
) -> tuple[bool, str]:
    """Write and/or compare the repository's record. Returns (drifted, note).

    `rendered` is written. `compare_against` is what the committed file *should*
    have said when this run started; it defaults to `rendered`. An apply passes
    its pre-apply render here, because the meaningful question is whether the
    repository knew the truth before this run changed it. A record that lags by
    exactly the apply that just happened is expected, not a finding.
    """

    baseline = compare_against if compare_against is not None else rendered
    state_path = Path(args.state_path) if args.state_path else STATE_PATH
    existed = state_path.exists()
    drifted = False
    note = "unchanged"

    if existed:
        current = state_path.read_text(encoding="utf-8")
        try:
            previous = parse_state(current)
        except RegistryError as error:
            reporter.warn(f"{state_path.name}: {error}")
            previous = None
            drifted = True
        if previous is not None:
            live = parse_state(baseline)
            if previous.get("database") != live.get("database"):
                reporter.say(
                    f"{state_path.name} records "
                    f"{previous.get('database')!r}; this run read "
                    f"{live.get('database')!r}. Not comparing them."
                )
                note = "different database"
            elif [item["id"] for item in previous.get("applied", [])] != [
                item["id"] for item in live.get("applied", [])
            ]:
                drifted = True
                note = "stale"
                reporter.warn(
                    f"{state_path.name} disagrees with the live ledger. The "
                    "repository record is stale; commit the regenerated file. "
                    "Recorded: "
                    + ", ".join(
                        item["id"] for item in previous.get("applied", [])
                    )
                    + ". Live: "
                    + ", ".join(item["id"] for item in live.get("applied", []))
                    + "."
                )
    else:
        note = "created"
        reporter.say(
            f"{state_path} does not exist yet. This run renders it for the "
            "first time; commit it so the repository records what the "
            "database carries."
        )

    if args.write_state:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        if not existed or state_path.read_text(encoding="utf-8") != rendered:
            state_path.write_text(rendered, encoding="utf-8")
            note = "created" if not existed else "rewritten"
        reporter.say(f"State record written: {state_path}")
    else:
        reporter.say(
            "State record not written (pass --write-state). Rendered content "
            "follows the run summary."
        )

    return drifted, note


def command_report(args, reporter: Reporter) -> int:
    registry = load(args)
    with connect_for(args) as connection:
        cursor = connection.cursor()
        database, server = confirm_target(cursor, args.expect_database)
        reporter.say(f"Target: {database} on {server}")
        ledger = read_ledger(cursor)

    _describe_ledger(reporter, registry, ledger, registry_root(args))
    generated_at = _now()
    rendered = _state_for(
        registry, database, server, ledger, generated_at, registry_root(args)
    )
    drifted, note = _handle_state(args, reporter, rendered)

    write_evidence(
        Path(args.emit_evidence) if args.emit_evidence else None,
        {
            "action": "report",
            "database": database,
            "server": server,
            "generated_at_utc": generated_at,
            "ledger": ledger,
            "state_record": note,
            "state_record_stale": drifted,
        },
    )
    if args.print_state:
        print(rendered)
    reporter.downgrade()
    return 0


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------


def command_apply(args, reporter: Reporter) -> int:
    registry = load(args)
    only = tuple(args.migration or ())
    started = _now()

    with connect_for(args) as connection:
        cursor = connection.cursor()
        database, server = confirm_target(cursor, args.expect_database)
        reporter.say(f"Target: {database} on {server}")

        before = read_ledger(cursor)
        pending = _describe_ledger(
            reporter, registry, before, registry_root(args)
        )
        applied_ids = [row["migration_id"] for row in before]

        plan, blockers, held = resolve_apply_plan(
            registry, applied_ids, only, root=registry_root(args)
        )
        if held:
            reporter.say("")
            reporter.say(
                "Pending but held back -- registered without a valid gate "
                "proof, so this path will not apply them:"
            )
            for migration in held:
                reporter.say(f"  {migration.migration_id}")

        if args.expect:
            expected = tuple(args.expect)
            planned = tuple(item.migration_id for item in plan)
            if planned != expected:
                blockers.append(
                    "The operator expected to apply "
                    + (", ".join(expected) or "(nothing)")
                    + " but the target's ledger makes the plan "
                    + (", ".join(planned) or "(nothing)")
                    + ". Refusing to apply a plan the operator did not "
                    "predict."
                )

        if blockers:
            for blocker in blockers:
                reporter.fail(blocker)
            reporter.fail(
                "Nothing was applied. The governed path fails closed: it "
                "applies the whole reviewed plan or none of it."
            )
            write_evidence(
                Path(args.emit_evidence) if args.emit_evidence else None,
                {
                    "action": "apply",
                    "result": "refused",
                    "database": database,
                    "started_at_utc": started,
                    "blockers": blockers,
                    "ledger_before": before,
                    "ledger_after": before,
                },
            )
            return 1

        if not plan:
            reporter.warn(
                f"NO-OP. {database} already carries every registered, gated "
                "migration; nothing was applied and no schema changed. If you "
                "queued this run expecting a migration to move, it did not: "
                "check that the migration is registered and gated on this "
                "commit."
            )
            write_evidence(
                Path(args.emit_evidence) if args.emit_evidence else None,
                {
                    "action": "apply",
                    "result": "no-op",
                    "database": database,
                    "started_at_utc": started,
                    "applied": [],
                    "ledger_before": before,
                    "ledger_after": before,
                },
            )
            reporter.downgrade()
            return 0

        reporter.say("")
        reporter.say(f"Plan for {database}:")
        for index, migration in enumerate(plan, start=1):
            reporter.say(
                f"  {index}. {migration.migration_id}  "
                f"{migration.forward}  "
                f"gated {migration.gate.gated_at_utc} on "
                f"{migration.gate.gate_database}"
            )
        reporter.say("")

        completed: list[dict] = []
        failure: dict | None = None
        for migration in plan:
            reporter.say(f"Applying {migration.migration_id}...")
            try:
                execute_script(
                    cursor, migration.forward_path(registry_root(args))
                )
            except Exception as error:  # noqa: BLE001  reported, then re-raised
                failure = {
                    "migration_id": migration.migration_id,
                    "file": migration.forward,
                    "error": scrub(str(error)),
                }
                break
            objects = set(read_objects(cursor))
            missing = [
                name for name in migration.gate.objects if name not in objects
            ]
            if missing:
                failure = {
                    "migration_id": migration.migration_id,
                    "file": migration.forward,
                    "error": (
                        "The migration reported success but the objects its "
                        "gate recorded are not present: "
                        + ", ".join(sorted(missing))
                        + ". Either the gate proof does not describe this "
                        "migration or the apply did not do what it claimed."
                    ),
                }
                break
            completed.append(
                {
                    "migration_id": migration.migration_id,
                    "file": migration.forward,
                    "executable_sha256": migration.gate.executable_sha256,
                }
            )
            reporter.say(f"Applied {migration.migration_id}.")

        after = read_ledger(cursor)
        generated_at = _now()
        rendered = _state_for(
            registry, database, server, after, generated_at, registry_root(args)
        )
        # What the committed record should have said before this run ran.
        baseline = _state_for(
            registry, database, server, before, generated_at, registry_root(args)
        )

    if failure is not None:
        reporter.fail(
            f"{failure['migration_id']} failed: {failure['error']}"
        )
        reporter.say("")
        reporter.say("Database state after the failure:")
        reporter.say(
            "  Applied in this run before it stopped: "
            + (
                ", ".join(item["migration_id"] for item in completed)
                or "(none)"
            )
        )
        reporter.say(
            "  Not attempted: "
            + (
                ", ".join(
                    item.migration_id
                    for item in plan[len(completed) + 1 :]
                )
                or "(none)"
            )
        )
        reporter.say(
            "  Ledger now carries: "
            + ", ".join(row["migration_id"] for row in after)
        )
        reporter.fail(
            "Each migration runs inside its own transaction, so the failed "
            "migration left nothing behind; migrations that already succeeded "
            "in this run are committed and remain applied. Fix the migration, "
            "re-gate it, and queue the stage again -- the applier will resume "
            "from the ledger."
        )
        write_evidence(
            Path(args.emit_evidence) if args.emit_evidence else None,
            {
                "action": "apply",
                "result": "failed",
                "database": database,
                "started_at_utc": started,
                "applied": completed,
                "failed": failure,
                "ledger_before": before,
                "ledger_after": after,
            },
        )
        return 1

    reporter.say("")
    reporter.say(
        f"APPLIED {len(completed)} migration(s) to {database}: "
        + ", ".join(item["migration_id"] for item in completed)
    )
    drifted, note = _handle_state(args, reporter, rendered, baseline)
    if not args.write_state:
        reporter.warn(
            "The repository record was not regenerated by this run. Run "
            "`report --write-state` and commit the result, or the repository "
            "will not know what the database carries."
        )
    write_evidence(
        Path(args.emit_evidence) if args.emit_evidence else None,
        {
            "action": "apply",
            "result": "applied",
            "database": database,
            "started_at_utc": started,
            "finished_at_utc": generated_at,
            "applied": completed,
            "ledger_before": before,
            "ledger_after": after,
            "state_record": note,
            "state_record_stale": drifted,
        },
    )
    if args.print_state:
        print(rendered)
    reporter.downgrade()
    return 0


# --------------------------------------------------------------------------
# rollback
# --------------------------------------------------------------------------


def command_rollback(args, reporter: Reporter) -> int:
    registry = load(args)
    target_id = args.migration_id

    if args.confirm != target_id:
        reporter.fail(
            "Rollback requires --confirm to repeat the migration id exactly. "
            f"Expected --confirm {target_id}, received {args.confirm!r}. "
            "This is destructive on member data; it is meant to be awkward."
        )
        return 1

    migration = registry.get(target_id)
    started = _now()

    with connect_for(args) as connection:
        cursor = connection.cursor()
        database, server = confirm_target(cursor, args.expect_database)
        reporter.say(f"Target: {database} on {server}")

        before = read_ledger(cursor)
        applied_ids = [row["migration_id"] for row in before]
        if target_id not in applied_ids:
            reporter.fail(
                f"{target_id} is not in {database}'s ledger. There is nothing "
                "to roll back."
            )
            return 1

        # Only the newest applied migration may be reversed. Anything else
        # would leave a later migration standing on removed objects, and the
        # rollback scripts themselves refuse that case with THROW 53502 or its
        # equivalent. Refusing here first gives the operator a readable reason.
        applied_in_order = [
            item.migration_id
            for item in registry
            if item.migration_id in set(applied_ids)
        ]
        if applied_in_order and applied_in_order[-1] != target_id:
            reporter.fail(
                f"{target_id} is not the most recently applied registered "
                f"migration; {applied_in_order[-1]} is. Roll back in reverse "
                "registry order, or the reversal would remove objects a later "
                "migration depends on."
            )
            return 1

        objects_before = set(read_objects(cursor))
        reporter.say("")
        reporter.warn(
            f"ROLLING BACK {target_id} on {database} using "
            f"{migration.rollback}. This is a destructive schema operation. "
            "The rollback script refuses if member data is present; if it "
            "does not refuse, the objects and the ledger row are removed."
        )

        failure = None
        try:
            execute_script(
                cursor, migration.rollback_path(registry_root(args))
            )
        except Exception as error:  # noqa: BLE001  reported below
            failure = scrub(str(error))

        after = read_ledger(cursor)
        objects_after = set(read_objects(cursor))
        generated_at = _now()
        rendered = _state_for(
            registry, database, server, after, generated_at, registry_root(args)
        )

    removed = sorted(objects_before - objects_after)
    payload = {
        "action": "rollback",
        "database": database,
        "migration_id": target_id,
        "rollback_file": migration.rollback,
        "started_at_utc": started,
        "finished_at_utc": generated_at,
        "ledger_before": before,
        "ledger_after": after,
        "objects_removed": removed,
    }

    if failure is not None:
        reporter.fail(f"{target_id} rollback failed: {failure}")
        reporter.say(
            "  Ledger now carries: "
            + ", ".join(row["migration_id"] for row in after)
        )
        reporter.fail(
            "The rollback ran inside its own transaction and committed "
            "nothing. A refusal here is usually correct: the rollback scripts "
            "refuse when member data is present, when a later migration is "
            "recorded, or when a procedure definition has drifted."
        )
        payload["result"] = "refused"
        payload["error"] = failure
        write_evidence(
            Path(args.emit_evidence) if args.emit_evidence else None, payload
        )
        return 1

    if target_id in {row["migration_id"] for row in after}:
        reporter.fail(
            f"{target_id} rollback reported success but its ledger row is "
            "still present. Treat the database as being in an unknown state "
            "and investigate before anything else runs."
        )
        payload["result"] = "inconsistent"
        write_evidence(
            Path(args.emit_evidence) if args.emit_evidence else None, payload
        )
        return 1

    reporter.say("")
    reporter.say(f"ROLLED BACK {target_id} on {database}.")
    reporter.say(f"  Objects removed: {len(removed)}")
    for name in removed:
        reporter.say(f"    {name}")
    payload["result"] = "rolled-back"
    drifted, note = _handle_state(args, reporter, rendered)
    payload["state_record"] = note
    payload["state_record_stale"] = drifted
    write_evidence(
        Path(args.emit_evidence) if args.emit_evidence else None, payload
    )
    if args.print_state:
        print(rendered)
    reporter.downgrade()
    return 0


# --------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------


def _verification_path(migration_id: str) -> Path | None:
    for candidate in VERIFICATION_DIR.glob(f"{migration_id}_*.sql"):
        return candidate
    return None


def _prerequisite_chain(
    registry: Registry, migration: Migration
) -> list[Migration]:
    """Every migration the target needs, transitively, in registry order."""

    needed: set[str] = set()
    frontier = list(migration.requires)
    while frontier:
        current = frontier.pop()
        if current in needed:
            continue
        needed.add(current)
        frontier.extend(registry.get(current).requires)
    return [item for item in registry if item.migration_id in needed]


def command_gate(args, reporter: Reporter) -> int:
    registry = load(args)
    migration = registry.get(args.migration_id)
    database = args.database
    if not database:
        reporter.fail(
            "gate requires --database naming the throwaway database to "
            "rehearse against."
        )
        return 1

    if database in FORBIDDEN_GATE_DATABASES:
        reporter.fail(
            f"Refusing to gate against {database}. A gate exists to rehearse a "
            "migration somewhere disposable."
        )
        return 1
    if args.expect_database != database:
        reporter.fail(
            "--expect-database must repeat --database exactly so a gate "
            "cannot be pointed at a database by accident."
        )
        return 1

    digest = executable_sha256(migration.forward_path(registry_root(args)))
    started = _now()
    steps: list[dict] = []

    def step(name: str, detail: str = "") -> None:
        steps.append({"step": name, "detail": detail})
        reporter.say(f"  [{len(steps)}] {name}" + (f" - {detail}" if detail else ""))

    with connect_for(args) as connection:
        cursor = connection.cursor()
        actual_database, server = confirm_target(cursor, args.expect_database)
        reporter.say(f"Gate database: {actual_database} on {server}")
        reporter.say(f"Gating {migration.migration_id} ({migration.forward})")
        reporter.say(f"Executable SHA-256: {digest}")
        reporter.say("")

        chain = _prerequisite_chain(registry, migration)
        applied = {row["migration_id"] for row in read_ledger(cursor)}
        for prerequisite in chain:
            if prerequisite.migration_id in applied:
                continue
            execute_script(
                cursor, prerequisite.forward_path(registry_root(args))
            )
            applied.add(prerequisite.migration_id)
        step(
            "prerequisites",
            ", ".join(item.migration_id for item in chain) or "(none)",
        )

        if migration.migration_id in applied:
            reporter.fail(
                f"{migration.migration_id} is already recorded in "
                f"{actual_database}. A gate must start from a database that "
                "does not carry it, so the forward apply is genuinely proven."
            )
            return 1

        objects_before = set(read_objects(cursor))

        execute_script(cursor, migration.forward_path(registry_root(args)))
        objects_after = set(read_objects(cursor))
        created = sorted(objects_after - objects_before)
        ledger_after_first = read_ledger(cursor)
        if migration.migration_id not in {
            row["migration_id"] for row in ledger_after_first
        }:
            reporter.fail(
                f"{migration.migration_id} ran without recording a ledger row. "
                "A migration that does not register itself cannot be governed."
            )
            return 1
        step("forward apply", f"{len(created)} object(s) created")

        # Idempotency is a claim every migration header makes. Prove it.
        execute_script(cursor, migration.forward_path(registry_root(args)))
        if set(read_objects(cursor)) != objects_after:
            reporter.fail(
                f"{migration.migration_id} is not idempotent: a second apply "
                "changed the object inventory."
            )
            return 1
        ledger_after_second = read_ledger(cursor)
        if len(ledger_after_second) != len(ledger_after_first):
            reporter.fail(
                f"{migration.migration_id} is not idempotent: a second apply "
                "changed the number of ledger rows."
            )
            return 1
        step("re-apply is a no-op", "objects and ledger unchanged")

        verification = "none available"
        verify_path = _verification_path(migration.migration_id)
        if verify_path is not None:
            cursor.execute(verify_path.read_text(encoding="utf-8"))
            result_sets = []
            while True:
                if cursor.description is not None:
                    columns = [column[0] for column in cursor.description]
                    result_sets.append(
                        [dict(zip(columns, row)) for row in cursor.fetchall()]
                    )
                if not cursor.nextset():
                    break
            final = next((rows for rows in reversed(result_sets) if rows), [])
            verified = bool(final and final[0].get("verified"))
            if not verified:
                reporter.fail(
                    f"{verify_path.name} did not return verified = 1 against "
                    "the gate database."
                )
                return 1
            verification = f"{verify_path.name} returned verified = 1"
        step("verification", verification)

        if args.rehearse_rollback:
            execute_script(
                cursor, migration.rollback_path(registry_root(args))
            )
            after_rollback = {
                row["migration_id"] for row in read_ledger(cursor)
            }
            if migration.migration_id in after_rollback:
                reporter.fail(
                    "The rollback ran but left the ledger row in place."
                )
                return 1
            step("rollback rehearsal", f"{len(created)} object(s) reversed")

            execute_script(
                cursor, migration.forward_path(registry_root(args))
            )
            if migration.migration_id not in {
                row["migration_id"] for row in read_ledger(cursor)
            }:
                reporter.fail(
                    "Re-applying after rollback did not restore the ledger row."
                )
                return 1
            step("forward apply after rollback", "ledger row restored")

    proof = GateProof(
        executable_sha256=digest,
        gated_at_utc=started,
        gate_database=actual_database,
        gate_server=server,
        prerequisites=tuple(item.migration_id for item in chain),
        objects=tuple(created),
        verification=verification,
        operator=args.operator,
        notes=args.notes,
    )

    reporter.say("")
    reporter.say(f"GATE PASSED for {migration.migration_id}.")
    reporter.say("Registry entry gate proof:")
    payload = proof.to_json()
    print(json.dumps(payload, indent=2))

    if args.update_registry:
        _write_gate_into_registry(
            registry_path(args), migration.migration_id, payload
        )
        reporter.say(f"Registry updated: {registry_path(args)}")

    write_evidence(
        Path(args.emit_evidence) if args.emit_evidence else None,
        {
            "action": "gate",
            "migration_id": migration.migration_id,
            "database": actual_database,
            "steps": steps,
            "proof": payload,
        },
    )
    return 0


def _write_gate_into_registry(path: Path, migration_id: str, proof: dict) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    for entry in document["migrations"]:
        if entry["id"] == migration_id:
            entry["gate"] = proof
            break
    else:
        raise GovernedMigrationError(f"{migration_id} is not in the registry.")
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--azure-pipelines",
        action="store_true",
        help="Emit Azure DevOps logging commands so a no-op or a warning "
        "changes the visible run result.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Local environment file holding AZURE_SQL_CONNECTIONSTRING. In "
        "the pipeline the value comes from a secret variable instead.",
    )
    parser.add_argument(
        "--emit-evidence",
        help="Write a JSON evidence record for this run to the given path.",
    )
    parser.add_argument(
        "--print-state",
        action="store_true",
        help="Print the rendered repository state record to stdout.",
    )
    parser.add_argument(
        "--registry",
        help="Use a different registry file. Test and dry-run affordance; the "
        "pipeline never passes it.",
    )
    parser.add_argument(
        "--registry-root",
        help="Resolve registry paths against this directory instead of the "
        "repository root. Test affordance.",
    )
    parser.add_argument(
        "--database",
        help="Retarget the configured connection string at this database. "
        "Required by `gate`; otherwise reserved for a throwaway database. "
        "Must repeat --expect-database exactly. The pipeline never passes it.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "check",
        help="Validate the registry against the files on disk. No connection.",
    )

    for name, help_text in (
        ("report", "Read the ledger and render the repository record."),
        ("apply", "Apply every pending, gated migration in registry order."),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument(
            "--expect-database",
            required=True,
            help="The database this run must be attached to. Checked against "
            "DB_NAME() before anything else happens.",
        )
        sub.add_argument(
            "--write-state",
            action="store_true",
            help="Write the rendered record to the state file.",
        )
        sub.add_argument(
            "--state-path",
            help="Override the state file location (tests and gates).",
        )
        if name == "apply":
            sub.add_argument(
                "--migration",
                action="append",
                help="Restrict the run to the named migration id. Repeatable.",
            )
            sub.add_argument(
                "--expect",
                action="append",
                help="The migration ids the operator expects to apply. The "
                "run fails closed if the computed plan differs.",
            )

    rollback = subparsers.add_parser(
        "rollback",
        help="Reverse the most recently applied migration.",
    )
    rollback.add_argument("migration_id")
    rollback.add_argument(
        "--confirm",
        required=True,
        help="Repeat the migration id exactly. Rollback is destructive.",
    )
    rollback.add_argument("--expect-database", required=True)
    rollback.add_argument("--write-state", action="store_true")
    rollback.add_argument("--state-path")

    gate = subparsers.add_parser(
        "gate",
        help="Prove a migration against a throwaway database.",
    )
    gate.add_argument("migration_id")
    gate.add_argument("--expect-database", required=True)
    gate.add_argument("--operator", required=True)
    gate.add_argument("--notes", default="")
    gate.add_argument(
        "--update-registry",
        action="store_true",
        help="Write the resulting proof into registry.json.",
    )
    gate.add_argument(
        "--no-rehearse-rollback",
        dest="rehearse_rollback",
        action="store_false",
        help="Skip the rollback rehearsal. Recorded in the proof.",
    )
    gate.set_defaults(rehearse_rollback=True)

    return parser


COMMANDS = {
    "check": command_check,
    "report": command_report,
    "apply": command_apply,
    "rollback": command_rollback,
    "gate": command_gate,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    reporter = Reporter(azure=args.azure_pipelines)
    try:
        return COMMANDS[args.command](args, reporter)
    except (GovernedMigrationError, RegistryError) as error:
        reporter.fail(str(error))
        return 1
    except Exception as error:  # noqa: BLE001  scrubbed before it is shown
        reporter.fail(f"{type(error).__name__}: {scrub(str(error))}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
