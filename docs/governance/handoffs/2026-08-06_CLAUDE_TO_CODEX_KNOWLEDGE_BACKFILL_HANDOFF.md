# Writer handoff: Claude Code (cloud) → ChatGPT Codex (Pete's machine)

Date: 2026-08-06, ~11:45 UTC. Owner-ordered transfer. Per
`MANAGER_SESSION_HANDOFF.md`: this records the pushed state, the exact
remaining work, and explicit relinquishment. The departing session's write
authority ends at this document; its scheduled check-ins and watchers are
cancelled. One writer per surface — the lane is yours.

## Why this transfer

Everything is done except one step that requires Azure SQL credentials,
which exist only on Pete's machine by design. The cloud session could not
run the disposable-database gate; two owner paste attempts failed
(first: the local checkout was parked on `work/os4-gate-proof` by the
previous gate script, so `git pull` failed and the new script was never
downloaded; second: most likely an unattended `az login` browser prompt —
no push ever arrived). Codex runs where the credentials live, so the gate
is a routine local run.

## Production state (verify, don't trust)

- Azure DevOps is the release authority:
  `https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site`.
  GitHub `petercarter19-hue/portfolio` is a mirror, currently synced only
  through main `225a1c0` — behind; sync after closeout.
- `main` = `896fd056b3c43248b9474e37bf6b9d253dc856b0`.
- Deployed: automatic run **560** for exactly that SHA; live
  `/healthz` release `668080a833260b3aeed84104` verified against
  `scripts/release_identity.py`.
- Live and verified: the complete Opportunity Slate page (OS-1..OS-6
  including the OS-4 save lifecycle, applied as PS-OPPSLATE-003 by run
  551), the nav link, and the leg-8 rule that member-authored Workshop
  saves confirm at save time.
- Production schema ledger: 23 applied rows
  (`docs/governance/PRODUCTION_SCHEMA_STATE.md` is the generated record).
- **PS-WORKSHOP-002** (the in-place knowledge backlog confirmation) is
  registered as a draft (`"gate": null`) and merged to main, with its
  app wiring already deployed in run 560 and structurally inert until the
  procedure exists (DatabaseServiceError degrades to skip; verified).

## The one remaining task

Run the gate, then the governed apply. All the machinery exists.

1. From the repo root on Pete's machine (or your own session there):
   `git checkout main && git pull`, then run
   `powershell -ExecutionPolicy Bypass -File scripts\gate_workshop_002.ps1`
   (needs `az login`). It creates a disposable DB
   `ps-workshop-002-gate-<stamp>`, proves apply / no-op reapply / verifier
   / rollback / reapply, deletes the DB, and pushes the registry proof on
   `work/workshop-002-gate-proof`.
2. **Known trap:** `tests/test_workshop_confirmation_migration.py` pins
   the draft shape ("gate key present and null"). The proof PR's
   validation will fail on that test until you flip it to assert the
   recorded gate (operator Pete, database `^ps-workshop-002-gate-\d{12}$`,
   server `peerslate`, digest equal to
   `govern_sql_migrations.executable_sha256(<forward file>)`,
   verifier sentence). Exact precedent: the OS-4 flip of
   `test_registry_entry_has_no_gate_proof_yet` → the gated-state test in
   `tests/test_opportunity_slate_migration.py` (main history, commit
   `2e65aead`, "Flip the OS-4 draft pin...").
3. Merge the proof PR to main with `[skip ci]` in the squash message
   (registry+test only; documentation-only closeout rules in
   `docs/AI_WORKFLOW.md`).
4. Queue pipeline 1 manually on the exact merged SHA with
   `schemaAction=apply`, `schemaMigrationId=PS-WORKSHOP-002` (everything
   else default). No automatic run will exist for a `[skip ci]` SHA, so
   the overlap guard is clean.
5. The run pauses at the `peerslate-database-schema` environment approval
   at stage entry (the plan prints only after; the in-run preflight
   refuses drift fail-closed). Approve after checking the run's
   parameters. Owner delegations recorded in `CURRENT_LANES.json`
   `owner_decisions` cover queueing and approval release for this lane.
6. Verify from the run's logs/artifacts: ledger 23 → 24, exactly
   PS-WORKSHOP-002 applied at its gate digest, prior rows untouched.
   Commit the regenerated `PRODUCTION_SCHEMA_STATE.md` from the
   SchemaMigrationEvidence artifact byte-for-byte (`[skip ci]` PR).
7. No further app deploy is needed: the wiring deployed in run 560
   activates by itself once the procedure exists. The member-visible
   result — Pete's existing knowledge items flipping to Confirmed —
   happens on his next signed-in visit to the Workshop library or the
   slate (bounded batches of 200 per page load). Verify with him, then
   record it; nothing was observable before the apply, and this handoff
   deliberately does not claim it.

## Review provenance (do not re-litigate, but read before touching)

- Candidate `c532505948e8d433c5b9ff3041574bee3c5d23d5` (merged via PR 308)
  was APPROVED by an independent Opus review after one REFUSE round.
  Fixed in that round: gate idempotency (the W1 drift guard excluded the
  procedure this migration revises), the verifier's bare-EXEC calling
  convention (T-SQL Msg 8164 — see the convention note in
  `PS-WORKSHOP-001_owner_isolation_verify.sql:19-34`), `@@ROWCOUNT`
  capture, `visibility = N'private'` predicates + constraint guard.
  11/11 mutations killed. Evidence in the session record; verdicts
  summarized in `docs/initiatives/PS-OPPORTUNITY-SLATE-001/evidence/`.
- **Two named carried risks** (recorded in the forward migration header,
  `SQL FIles/Migrations/proposed/PS-WORKSHOP-002_knowledge_confirmation.sql`):
  the archive-refuses-'suggested' closure is procedural, not structural —
  any future suggestion-queue migration must re-verify the boundary and
  must NOT route "dismiss suggestion" through Archive (the detail view
  offers `archive_url` on every row today); and a PS-WORKSHOP-002
  rollback re-opens that hole while prior confirmations legitimately
  remain (rollback never un-confirms; owner-ruling policy, reviewer
  re-affirmed).
- An earlier app-side reconciliation approach was REFUSED and fully
  excised (it silently rewrote `authored_via`, reset the
  `updated_at_utc` ordering of the TOP(24) evidence window, and wrote
  member-attributed audit rows). Do not resurrect it.

## Records that need closing (currently one release behind)

- `docs/governance/CURRENT_BASELINE.yaml` authority block and the
  lockstep pins in `tests/test_operational_readiness.py` still record run
  **557** / release `388372b3...`; actual deployed is run **560** /
  `896fd056` / release `668080a833260b3aeed84104`. Reconcile both
  together in the closeout (they must move in lockstep or CI fails).
- `docs/governance/CURRENT_LANES.json`: lane `PS-OPPORTUNITY-SLATE-001`,
  leg 9 `authorized_not_started` → update through the apply; leg 8 is
  live as recorded. The lane's `branch` field gates the write preflight
  (`python scripts/delivery_preflight.py --package PS-OPPORTUNITY-SLATE-001
  --intent write --fetch --require-clean`); the recorded pattern is to
  rotate the field to your working branch in the commit itself (see the
  open/close rotation pairs throughout today's history).
- Lane close requires the recorded Fable extra-high final review per the
  ledger's `exit_authority` — or Pete's explicit waiver, which he can
  give you directly.
- Cleanup pattern: archive-tag (`archive/<branch-name>`) then delete
  merged branches; then sync the GitHub mirror `main`. Branch
  `work/2026-08-06-oppslate-knowledge-backfill` (merged, kept) awaits
  that treatment after the apply; so will the proof branch.
- `work/2026-08-06-agent-permissions` (Pete's commit `3ab30e24`) is a
  parked, unmerged Claude-specific permission grant. Not yours to merge;
  Pete may delete it or keep it.

## Relinquishment

The Claude cloud session relinquishes the PS-OPPORTUNITY-SLATE-001 lane
and all write intent at this document's commit. Its pushed state: main
`896fd056`, all work branches merged or archive-tagged as recorded, no
dirty worktrees, no stashes, no pending schedulers. Production release
authority remains with Pete; the governed pipeline remains the only path
to the database.
