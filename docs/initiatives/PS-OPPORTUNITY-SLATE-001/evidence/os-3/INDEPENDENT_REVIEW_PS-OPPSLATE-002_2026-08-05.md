# Independent review — PS-OPPSLATE-002 production apply candidate

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort, per
  Pete's 2026-08-05 model routing (Fable architect, Sonnet implementation,
  Opus 5 independent review, Fable extra-high final review).
- Candidate SHA: `07348e1146c97a415b7f18f728b6517c45a8c1f8` (main, squash of
  Azure PR 287). Later commits through `8ef97a2` verified governance-only.
- Verdict: **APPROVE** — no blocking finding.

## What was verified

1. **Byte restoration of PS-OPPSLATE-001** by three independent mechanisms:
   empty `git diff 98d1565 07348e1` across forward/rollback/verifier;
   identical git blob object IDs (`078d68a6`, `fbf1c1fa`, `adcbcbf4`) between
   `98d1565` and the candidate, distinct from the mutated `d3af479` blobs; and
   registry gate digest restored from `752812bd…` to
   `2406ff6eedd44939ee5148982462a66935f13dfea45fe46076cf5895883c7273`.
2. **Registry integrity** at the candidate: `govern_sql_migrations.py check`
   exits 0; PS-OPPSLATE-002 is a separate additive entry requiring
   PS-OPPSLATE-001 at digest
   `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0`, with a
   61-object inventory containing no OS-1/OS-2 object.
3. **Forward migration** (2,058 lines, read in full): all guards precede the
   first DDL (missing/older/partial baseline refusal); single XACT_ABORT
   transaction; the PS-OPPSLATE-001 ledger row is read-only throughout; all
   eight procedures derive identity server-side from `@UserKey`; all 43
   DELETE/UPDATE statements filter `owner_profile_id = @ProfileId`; no
   aggregate score, percentage, ranking, recommendation, fit verdict, or
   employer prediction exists in any column, computed value, or output;
   evidence is referenced by key + pinned version with bounded excerpts, and
   save re-derives evidence identity from the member's own confirmed,
   unarchived items so a caller cannot cite another owner's evidence.
4. **Delete-path completeness proved**: the only OS-1/OS-2 procedures that
   delete rows the new OS-3 tables reference are the three revised ones; no
   unrevised procedure can hit an FK violation after apply.
5. **Rollback** (757 lines): refuses member rows, later migrations, and
   procedure drift before any change; deletes only the PS-OPPSLATE-002 ledger
   row; restores all four revised procedures to their OS-2 definitions,
   proved byte-exact by SHA-256 of the extracted procedure bodies.
6. **Verifier** (1,437 lines): two synthetic owners plus a forged key; single
   outer transaction with rollback-only exit; structural assertions across all
   seventeen procedures; adversarial cross-owner and forged-owner negative
   paths.
7. **Adversarial sweep**: no injection vector (all dynamic SQL is static
   literals); digest binding recomputed from disk; wrong-database and
   forbidden-gate-database protections confirmed; simulated apply plan against
   a production-shaped ledger resolves to exactly `['PS-OPPSLATE-002']` with
   zero blockers and no possibility of re-executing PS-OPPSLATE-001.
8. **Tests**: 116 passed, 3 skipped (each skip inspected and immaterial),
   292 subtests.

## Non-blocking findings (follow-up work)

1. `SQL FIles/Verification/PS-OPPSLATE-002_owner_isolation_verify.sql:143-159`
   — the structural forbidden-column assertion enumerates only the eight
   OS-1/OS-2 tables and four fixed column names; the four new OS-3 tables are
   not covered by that particular check. Direct reading confirmed no scoring
   column exists; widen the table list and predicate in a follow-up.
2. `services/database_service.py:37-43` — PR 274's addition of the four OS-3
   procedure names to `ALLOWED_PROCEDURES` remains on main ahead of the apply.
   Verified inert: no route or service calls them yet.
3. Informational: the gate execution against the deleted throwaway database
   could not be re-run; that portion rests on the recorded evidence, which was
   cross-checked for internal consistency (125 and 61 objects, matching the
   registry inventories exactly).

The reviewer's full command-level verdict is preserved in the session record;
this file is the package evidence summary committed alongside the apply.
