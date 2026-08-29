# PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001 review evidence

Runtime-inert review-tail record for replacement package 1 of the accepted
2026-08-29 reader topology (after PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-READERS-001
failed independent pre-activation review and was paused, never to resume).
Paired receipt: `docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001.json`.

- **Boundary:** Protected, independent review required, repository authority
  through merge, production authority withheld. This record grants no schema
  apply outside the deleted disposable gate databases, no grant, worker,
  route, UI, schedule, deployment, or enablement. No reader is wired to
  anything; account-wide export remains unavailable today.
- **Delivered candidate:** `bc8dd2db1aedcd04228ceded0ff0643bbd5e8089` on
  `work/2026-08-29-settings-account-export-core-readers-001`, activation
  base main `7cc57899` (worktree created at `81afdbef`). Ten read-only
  owner-scoped reader procedures (own account row, active profile, eight
  Living Resume tables), rollback, sealed registry gate proof, isolation
  verification, adapter DOMAINS registry (3 included + 26 non-included
  dispositions incl. career_skill_links deferred to the evidence decision
  package), tests, two CR1 records.
- **Custody:** three writer commits (agent:claude-code/settings-core-readers-writer,
  Sonnet; final writer SHA `54bd2d14`), then manager commits: `b80f4f21`
  (ledger self-description fit to nvarchar(500) after gate truncation),
  `8b9453b3` (requires widened to ["PS-PLAT-006","PS-AUTH-001"] for the
  verification's usp_UpsertAppUserFromAuth dependency, pinned test updated
  in lockstep), `53d767c7` (sealed gate block), then review-round commits
  `ee505bda`, `f64e3ee1`, `bc8dd2db`.
- **Gate proof:** digest `28678016f02b4a0abb072504e7f1fe6f3ed16f11ac7d1de3ad758fbc9f326b2e`
  (normalized executable content), third run passed in full and the
  post-header-fix re-proof passed again on `ps-migration-path-20260829-cr2`:
  prerequisites replayed, ten objects, idempotent re-apply,
  `verified = 1` from the isolation script, rollback rehearsed, forward
  re-applied. Throwaway databases deleted. `check`: 25 gated and matching.
- **Independent review (fresh Opus reviewer, read-only, zero mutations across
  all rounds):** `53d767c7` → CONDITIONAL (1 CRITICAL: the manager's gate
  commit broke the then-pinned gate-null test — the frozen candidate was red;
  1 HIGH stale validation claim; 1 MEDIUM missing parent-owner-predicate pin;
  1 LOW header fragment; six privacy mutation probes, five caught).
  `ee505bda` → **PASS** (all four fixed and re-probed; the reviewer also
  corrected its own earlier probe's false negative on the digest pin) with
  two non-blocking fold-ins: the computed-digest assertion (proven necessary
  by an un-regated-edit probe) and a heading move. `f64e3ee1` and
  `bc8dd2db` → records-only deltas verified and **CONFIRMED**: gate-round
  record added, every stale gate-null/requires claim corrected to the sealed
  truth, `git diff ee505bda..bc8dd2db -- "SQL FIles/" services/` empty.
  Suites at the final candidate: 133 passed / 664 subtests, pytest exit 0;
  unittest OK.
- **Standing exclusions and next steps:** career_skill_links and all
  sensitive-tier domains await their own packages per the accepted topology;
  reader-worker integration is package 6; grants are paper-only until C4;
  the C3 experience remains gated on the reader packages and the revised
  visual direction. One zero-severity cosmetic note (an orphaned source line
  in one report bullet; renders identically) transfers to the next touch.
