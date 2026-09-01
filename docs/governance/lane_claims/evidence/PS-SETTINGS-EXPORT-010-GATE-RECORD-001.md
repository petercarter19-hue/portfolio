# PS-SETTINGS-EXPORT-010-GATE-RECORD-001 review evidence

Routine, self-reviewed: the disposable-gate proof for EXPORT-010, run
under the owner's explicit authorization
(pete-chat-2026-09-01/yes-to-the-gate-proof) and recorded in the
registry. The throwaway database and temporary firewall rule were
created for each attempt and deleted after it, success or failure.

## What the passing run proved on a real engine

Ten prerequisite migrations, the forward apply, idempotent re-apply,
rollback rehearsal, and the full two-owner verification returning
verified = 1: refusal numbers 57272/57273/57275/57279/57280/57281 all
fired exactly; a refused completion left zero ledger rows and the job
running (both-or-neither); replay-after-ready refused with the original
thirty rows untouched; owner deactivation between claim and completion
refused under the lock; the successful completion wrote exactly thirty
rows, all the completing owner's, with the stable per-domain schema
identifier and the job cutoff marker, the other owner untouched.

## The three failed attempts, kept honest

a1: shell-sourcing truncated the dotenv connection string at its first
semicolon -- the tool refused cleanly ('names no database'). a2: the
verify's cleanup section hit the platform's immutable-audit trigger;
the house answer (per C1's own verify) is no cleanup at all, adopted
via a governed extend-surfaces. a3: an unescaped apostrophe introduced
in the a2 fix. Each attempt cost only its retry; nothing was stranded
and nothing committed.

## Gate run output (verbatim tail)

```
Gate database: ps-export-c4-gate-20260901-a4 on peerslate
Gating PS-SETTINGS-EXPORT-010 (SQL FIles/Migrations/PS-SETTINGS-EXPORT-010_domain_ledger_writer.sql)
Executable SHA-256: fb76306665fa6b3d3dbf7b24f98725b189081f6b6967df6971f4b60d311fa308

  [1] prerequisites - PS-PLAT-000, PS-PLAT-001, PS-PLAT-002, PS-PLAT-003, PS-PLAT-004, PS-PLAT-005, PS-PLAT-006, PS-PLAT-007, PS-AUTH-001, PS-SETTINGS-EXPORT-001
  [2] forward apply - 1 object(s) created
  [3] re-apply is a no-op - objects and ledger unchanged
  [4] verification - PS-SETTINGS-EXPORT-010_domain_ledger_isolation_verify.sql returned verified = 1
  [5] rollback rehearsal - 1 object(s) reversed
  [6] forward apply after rollback - ledger row restored

GATE PASSED for PS-SETTINGS-EXPORT-010.
Registry entry gate proof:
{
  "executable_sha256": "fb76306665fa6b3d3dbf7b24f98725b189081f6b6967df6971f4b60d311fa308",
  "gated_at_utc": "2026-09-01T10:29:04Z",
  "gate_database": "ps-export-c4-gate-20260901-a4",
  "gate_server": "peerslate",
  "prerequisites": [
    "PS-PLAT-000",
    "PS-PLAT-001",
    "PS-PLAT-002",
    "PS-PLAT-003",
    "PS-PLAT-004",
    "PS-PLAT-005",
    "PS-PLAT-006",
    "PS-PLAT-007",
    "PS-AUTH-001",
    "PS-SETTINGS-EXPORT-001"
  ],
  "objects": [
    "SQL_STORED_PROCEDURE:dbo.usp_CompleteAccountExportWithDomains"
  ],
  "verification": "PS-SETTINGS-EXPORT-010_domain_ledger_isolation_verify.sql returned verified = 1",
  "operator": "agent:claude-code/settings-export-gate-record-writer",
  "notes": "Owner-authorized C4 gate proof (pete-chat-2026-09-01/yes-to-the-gate-proof), attempt a4"
}
Registry updated: /Users/petercarter/Documents/PeerSlateWorktrees/PS-SETTINGS-EXPORT-010-GATE-RECORD-001/SQL FIles/Migrations/registry.json

```

EXPORT-010 remains NOT applied to production; the apply is gate 5b,
separately authorized and next.
