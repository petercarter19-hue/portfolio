# Codex Completion Handoff — PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001

**Written 2026-08-12 by the Claude Fable architect session at Pete's direction
("I can have codex finish everything"). This document is self-contained: it is
everything a fresh Codex session needs to finish this package to the stop
line. Pete's stop line, verbatim across this lane: go all the way up to right
before it goes live — merge and deploy DARK, then STOP; setting the flag
`PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED=true` anywhere is Pete's personal,
separately recorded act and is NOT part of this handoff.**

## 1. What this package is

Puts the real `/interview-studio` behind sign-in and recomposes it to the 19
hash-locked warm-material visuals. One flag (`PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED`,
default off) gates both HTML routes and all four interview APIs as a unit;
identity is server-derived; each account gets an opaque browser-storage
namespace (v3); flag-off anonymous pages are byte-comparable to base. Full
architecture: `Interview Studio Claude Architecture Deliverable 2026-08-11` in
`C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\` (accepted
by Pete; see OWNER_ACCEPTANCE_2026-08-11.md there). Locked visuals:
`...\Interview Studio Claude Architecture Handoff 2026-08-11\02_VISUAL_AUTHORITY\FINAL\`.

## 2. Exact current state

- Worktree: `C:\Users\peter\Documents\portfolio-interview-studio-auth-20260811`
- Branch: `work/2026-08-11-interview-studio-authenticated-experience-001`,
  **pushed to origin at handoff SHA `92741795c26c89b4d64425b07dfabaad8b6bae7f`**
  (no PR yet for the lane itself). Base: main `24f0acb`; rebased onto `65651b4`
  (the Opportunity Slate lane activation — part of main's history, NOT part of
  this candidate's diff; an earlier reviewer note flagging it is a non-issue).
- Lane record: `docs/governance/CURRENT_LANES.json`, package
  `PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001` (writable surfaces,
  exclusions, owner decisions, model routing — read it in full).
- All 6 slices delivered; the Fable visual rebuild (passes 1-9) brought all 19
  locks to a measured pass; the header-warmth fix landed (cold band killed).
- **First independent review (Opus, on SHA `81d8f21`): REJECT** — findings in
  §4. **The findings-closure run then COMPLETED** and is fully committed at
  `9274179`: every P1/P2/P3 in §4 closed and live-verified by its writer, 391
  focused tests green, flag-off byte-comparability green, full discover showing
  only the inherited failures, worktree clean. §4 therefore reads as a
  verification checklist for the final reviewer, not an open work list. One
  disclosed judgment call awaits reviewer confirmation: whether lock 08's
  "Practice This Answer" disabled-toggle reading is correct (recorded in
  SLICE_NOTES rather than guessed silently).

### Writer seat status (updated at close)

The Claude lane was formally closed through the new governed
`--intent transfer` flow (added to main on 2026-08-12 by the parallel
Opportunity Slate session). Control branch
`work/2026-08-12-interview-studio-writer-transfer`, PR 378, changes only
`docs/governance/CURRENT_LANES.json`: the lane's `writer` field now reads OPEN
with the relinquishment recorded at the pushed handoff SHA, plus one owner
decision quoting Pete's direction and the full handoff state. The lane stays
active with its surfaces, capacity, and `writes_allowed_for` intact, so the
incoming writer inherits authority without a fresh activation.

**Expected merge conflict, by design:** the lane branch also carries its own
`CURRENT_LANES.json` edits (the recorded surface note for
tests/test_navigation.py and the routing-history entries). When the lane PR is
prepared, `CURRENT_LANES.json` will conflict with the merged transfer commit.
Resolve by keeping BOTH: the transfer's writer/owner-decision changes and the
lane's surface/routing records. Then set the `writer` field to the actual
incoming writer's identity as part of the merge-grant commit in §5 step 4.

### FIRST ACTION for the incoming writer — reconcile the closure run

1. `git -C <worktree> status` and `git log --oneline -15`.
2. Commits after `81d8f21` = the closure writer's completed work. Uncommitted
   changes = it died mid-edit: read the diff, keep what is correct and
   complete per §4's specs, discard half-done fragments deliberately (record
   what you discarded in SLICE_NOTES).
3. Read `docs/initiatives/PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001/SLICE_NOTES.md`
   end to end — it is the running truth record of every change and disclosed
   deviation.

## 3. How to run and verify (all proven this session)

- Tests: `C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest
  tests.test_interview_studio tests.test_auth tests.test_search_visibility
  tests.test_navigation tests.test_governance_pointers tests.test_delivery_preflight`
  with env `ANTHROPIC_API_KEY=test-placeholder-key`. Expected: ~372+, 1 skip, 0 fail.
- Full sweep: `-m unittest discover -s tests -p "test_*.py"` — the ONLY
  acceptable failures are the five inherited items listed in SLICE_NOTES
  (ScheduledRunnerTests trio, POSIX-permission test on Windows, one
  journal-frontend contention flake).
- Byte-comparability (non-negotiable): the flag-off anonymous pages must stay
  byte-identical; the dedicated test class covers it.
- Local flag-on server: env `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED=true
  PEERSLATE_ALLOW_DEV_IDENTITY=true PEERSLATE_DEV_USER_KEY=x
  PEERSLATE_OWNER_USER_KEYS=x PORT=5019` then `python app.py` from the
  worktree. Owner-grounded AI states need the OWNER_USER_KEYS=dev key pairing.
- State captures/measurement: `tooling/` in this package folder —
  `capture_states.py` (fixture-intercepted real-flow captures; canvas-stream
  getUserMedia shim for media states; storage-sabotage script for lock 17),
  `capture_measure.py` (region color measurement vs locks),
  `build_comparison_sheet.py` (the 19-pair sheet Pete reviews),
  `MEASURED_TARGETS.md` (the measured palette — canvas #fdf9f6, rail #fcf7f3,
  forest #114a2b, ink #061e47, gold #a5762f/#c9a566), and
  `FABLE_REVIEW_BRIEF.md` (the full review checklist incl. pass K closure
  verification). Edit the two path constants at the top of each script (they
  point at this worktree and the iCloud locks folder).

## 4. The Opus findings the closure run must land (verify each, then re-verify live)

P1-1 `clearLocalData()` crash: interview-studio.js ~:4685-4686 unguarded
`levelSelect.value`/`familySelect.value`; `[data-is-family]` absent in the
authenticated DOM → clear destroys data, page still shows records, no truthful
announcement. Fix: null-guard both + committed regression test. Live repro:
seed a record, click Clear local History — no page error, rows disappear,
truthful announcement.

P1-2 lock divergences: (a) cool/green `.is__card` gradient (css ~3460) bleeds
into authenticated Complete/History cards → override to warm flat surface in
auth scope; (b) lock 08: result renders in its card container, question stays
at the ~1.5-1.85rem tier, dominant action = ENABLED green "Use best practice"
(selects the best_practice radio + generates), "Practice This Answer" visible
but disabled; (c) lock 09 order: frame → media-truth line → controls, plus
"Local camera preview" caption and chip icon/status dots; (d) lock 11: warm
cards + circular icon badges + gold rule + arrow icons on actions + a
"Completed questions" rail group during the complete view (checkmark + title,
removed on new session); (e) lock 12: filter selects styled as the locked
pills.

P2-1/P2-2 marker gate: server must reject bracket markers ONLY for revisions —
authenticated client sends `attempt` (bounded int, default 1) in the review
payload; server applies `_IMPROVEMENT_MARKER_PATTERN` only when attempt >= 2.
Test: first-attempt answer "I built the pipeline. [I can share the
architecture diagram if useful.]" → 200 (mocked provider). Client must consume
the improve payload's `confirmations[]` as the canonical marker list (literal
containment count gates "Review Revised Answer"; regex fallback only if the
array is absent) and a confirmations-listed `[TBD]`-style placeholder must
keep the gate locked.

P2-3: the line "Video Practice does not analyze eye contact, appearance,
confidence, emotion, personality, pace, or delivery." renders persistently
under CONTENT COACHING (authenticated branch), and the word "public" comes out
of the authenticated delivery-analysis sentence.

P3: legacy redirects (/interview-me, /petec/interview-me,
/petec/interview-studio) get the same X-Robots-Tag/no-store treatment when the
flag is on.

## 5. Remaining sequence to the stop line

1. Land/complete the §4 closures; suites + byte-comparability green.
2. Recapture affected states (tooling), re-generate `comparison_sheet.html`,
   commit the refreshed captures into
   `artifacts/2026-08-11-interview-studio-authenticated/` and give Pete the
   sheet.
3. **Final independent review** (Pete's routing: Opus did the first review; a
   reviewer that did not write the closures does the final one) using
   `tooling/FABLE_REVIEW_BRIEF.md` — pass K (closure verification with the
   exact live repros) is mandatory and first. Zero unresolved P0/P1 to
   proceed.
4. **Record the merge grant before merging** (house recorded-scope pattern):
   add this package to `merge_allowed_for` (and `release_allowed_for` if the
   validator asks) in `docs/governance/CURRENT_LANES.json`'s operating_mode
   with an owner_decisions entry quoting Pete's standing grant for this lane
   ("Go all the way up to right before it goes live" / "I can have codex
   finish everything"), committed on this branch. The activation validator
   forbade recording it at activation; recording it at merge time with the
   quote is the established pattern (see PS-OPPORTUNITY-SLATE-001 and
   PS-ASK-PETE-* precedents in the same file).
5. Push the branch, open the Azure PR (title WITHOUT [skip ci] — this is a
   runtime change and MUST deploy), let the required build pass, squash-merge.
   CLI that works here: `az repos pr create --organization
   https://dev.azure.com/peerslate19 --project portfolio-site --repository
   portfolio-site ...`; complete with `az repos pr update --id <id> --status
   completed --squash true`.
6. Deployment: merges auto-deploy (three-stage pipeline; no human checkpoint
   for schemaAction=none). KNOWN FLAKE: the automatic trigger sometimes does
   not fire — if no run starts for the exact merged SHA, use the governed
   manual override (queue the pipeline with forceProductionDeploy=true and
   manualProductionSourceVersion=<full 40-char merged SHA>) — never a same-SHA
   fallback while an automatic run exists.
7. Verify: `/healthz` release identity matches the merged SHA's derived
   identity; live anonymous smoke — `/interview-studio` still public 200 with
   unchanged content (flag is off), all four APIs behave exactly as before for
   anonymous callers; robots.txt shows the new Disallow; sitemap omits the
   studio.
8. Write the completion record (docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md
   proportional form): base/final SHA, changed paths, verification, release
   state ("merged and deployed DARK; flag off; enablement awaiting Pete"),
   honest limitations (include: SESSION_COOKIE_SECURE note Q-D, deferrals
   D1-D4 from the architecture's 06 file, the inherited test failures, and
   that Pete's browser acceptance of the flag-ON experience happens at
   enablement time on a local/candidate run — NOT by flipping production).
9. **STOP.** Do not set the flag anywhere. Report to Pete.

## 6. Hard rules carried from the lane record (read the record itself too)

- Writable surfaces only (the ledger lists them; tests/test_navigation.py was
  added narrowly by recorded surface note). No base.html, no dictation.js, no
  schema/SQL, no pipeline YAML, no provider config.
- Never weaken a failing test; the public flag-off contract is sacred.
- A merge is not enablement; nothing is called live without the exact-release
  /healthz match and smoke.
- Preserve every unrelated worktree/branch/artifact; the parallel
  PS-PROFILE-EXPERIENCE-001 and Opportunity Slate lanes are other writers'.
- Cleanup of this lane's branches/worktrees happens only after the completion
  record, behind archive tags, task-local only.

## 7. Quick reference

| Thing | Value |
|---|---|
| Candidate reviewed by Opus | `81d8f21` (closures land after it) |
| Flag | `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED` (default off) |
| Storage scope | `member-<sha256(user_key)[:20]>`, keys `peerslate:interview-studio:<scope>:v3:*` |
| Inherited discover failures | 5, listed in SLICE_NOTES |
| Review brief | `tooling/FABLE_REVIEW_BRIEF.md` (run pass K first) |
| Comparison sheet generator | `tooling/build_comparison_sheet.py` |
| Architecture + acceptance | iCloud `PeerSlate Architect Handoffs\2026-08-11\` |
| Governance ledger | `docs/governance/CURRENT_LANES.json` (this lane + routing history) |
