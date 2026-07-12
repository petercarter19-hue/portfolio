"""Plan or apply PeerSlate SQL migrations using the configured secure connection."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from mssql_python import connect

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "SQL FIles" / "Migrations"
load_dotenv(ROOT / ".env")


def get_connection():
    connection_string = os.getenv("AZURE_SQL_CONNECTIONSTRING")
    if not connection_string:
        raise RuntimeError("AZURE_SQL_CONNECTIONSTRING is not configured.")
    connection_string = connection_string.replace(
        ".database.windows.net.database.windows.net",
        ".database.windows.net",
    )
    supported_parts = []
    for part in connection_string.split(";"):
        if part.partition("=")[0].strip().lower() != "connection timeout":
            supported_parts.append(part)
    last_error = None
    for attempt in range(1, 4):
        try:
            connection = connect(";".join(supported_parts), timeout=60)
            connection.setautocommit(True)
            return connection
        except Exception as error:
            last_error = error
            if attempt < 3:
                time.sleep(5)
    raise RuntimeError("Azure SQL did not accept a connection after three attempts.") from last_error


def forward_migrations() -> list[Path]:
    return sorted(
        path
        for path in MIGRATION_DIR.glob("PS-PLAT-*.sql")
        if not path.name.endswith("_rollback.sql")
    )


def apply_migrations(paths: list[Path]) -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        for path in paths:
            print(f"Applying {path.name}...")
            cursor.execute(path.read_text(encoding="utf-8"))
            while cursor.nextset():
                pass
            print(f"Applied {path.name}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the forward migrations. Without this flag, only print the plan.",
    )
    args = parser.parse_args()
    paths = forward_migrations()
    if not paths:
        raise SystemExit("No PeerSlate platform migrations were found.")

    print("PeerSlate migration order:")
    for path in paths:
        print(f"- {path.name}")

    if not args.apply:
        print("Plan only. No database changes were made.")
        return

    apply_migrations(paths)


if __name__ == "__main__":
    main()
