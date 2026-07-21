# PeerSlate Completion & Handoff Report - Photo Proof Readiness

## A. Status

- Package: `PS-CAPTURE-PHOTO-LIFECYCLE-001`, proof-readiness continuation
- Status: Complete for the two assigned gaps; the production proof window
  itself remains unrun
- Branch and commit: `work/2026-07-20-photo-proof-readiness-001`; the exact
  pushed commit is supplied in the handoff because a commit cannot contain its
  own SHA
- Exact base: Azure DevOps `origin/main` at
  `ed3409a902f38e9437f6fbf70d3f2f61625037f4`, verified after
  `git fetch origin --prune`
- PR / pipeline / environment: none. No PR opened, no merge, no push to `main`,
  no pipeline run, no deployment, no Azure, Defender, SQL, or setting action
- Production state: unchanged. `CAPTURE_PHOTO_ENABLED=false` and
  `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`. Photo remains unavailable to
  ordinary members and is not claimed live
- Visual authority and status: Not Applicable. No user-facing surface changed;
  no template, CSS, or JavaScript was touched
- Homepage product projection: Not Applicable to this change; the existing
  downstream requirement `PS-HOME-CAPTURE-PHOTO-PARITY-001` is unchanged and
  still blocks ordinary enablement
- Pete / designated session manager visual acceptance: not required for this
  server-and-document diff
- Designated session manager: the existing ChatGPT Work/Codex owner-delegated
  Capture Media manager role, via the Claude Code manager session that assigned
  this continuation
- Manager handoff status and next receiver: returned to the assigning manager
  after push; no further writer assigned
- Lane owner and self-managed authority: current Claude Code session, sole
  writer on the branch above
- Self-certification: **Pass** for the two assigned gaps; **Conditional** for
  overall lifecycle readiness and enablement, unchanged
- Complete-diff review: Passed
- Acceptance requested: technical report

## B. What changed technically

### Change 1 - the proof-mode admission audit record

`services/photo_lifecycle_access_service.py`:

- `PhotoLifecycleAccessService.allows_identity` changed from a static method to
  an instance method. Both existing call sites in `owner_routes.py` and all
  existing test call sites already invoked it on the module singleton or a test
  instance, so no call site changed.
- Added `_announce_proof_window`, which emits one warning-level record the
  first time a given proof window actually admits a cohort request:

  ```text
  PeerSlate Photo lifecycle proof admission. access_mode=proof run_id=<run id>
  ```

  The format lives in the module constant `PROOF_ADMISSION_LOG_FORMAT`; an
  unconfigured run id is labelled by `PROOF_ADMISSION_UNSET_RUN_ID`, `unset`.
- Dedupe fingerprint is `(mode, run_id, expires_at_utc)`, held in instance
  memory behind a lock. It deliberately excludes the cohort keys, so the audit
  path retains no identity material.
- Added `reset_audit_state()` so a process, or a test, can forget which windows
  it has announced.
- The `PhotoLifecycleConfiguration` docstring now enumerates the single narrow
  exception to its never-serialize rule, naming the two safe fields, so the
  exception cannot widen silently in a later edit.

No access decision changed. Exactly the same identities are admitted and denied
as before, in the same order, with the same fail-closed behaviour. The audit
call sits after the cohort membership test and cannot affect its result.

Granularity, level, and the rejected alternatives are documented in
[`06_PROOF_ADMISSION_AUDIT_RECORD.md`](06_PROOF_ADMISSION_AUDIT_RECORD.md).

`tests/test_photo_lifecycle_access.py`: twelve added tests across two new
classes, covering emission, non-emission in `off`/`invalid`/`ordinary`/
non-cohort cases, the absence of any identity value, spam bounding, second-window
attribution, the `unset` label, reset, and two end-to-end assertions through a
real direct Photo route.

### Change 2 - Defender decision converted from choice B to choice A

Documents updated to record choice A as the owner decision of 2026-07-20:

- `README.md` - new proof-readiness section, decision line, recommendation
  text, alternatives table, document index, writable-scope record.
- `01_THREAT_MODEL_AND_AUTHORIZATION_BOUNDARY.md` - Synthetic Owner A role, and
  the closing Fail/Conditional paragraph, which now states explicitly that the
  expected Defender verdict for the approved inert fixture is the planned
  outcome and not a stop signal.
- `02_PROOF_MECHANISM_AND_ROLLOUT.md` - decision paragraph, entry-gate item 7,
  execution-sequence item 6, the owner-decision section, both choice headings,
  and a narrow, explicitly bounded exception in the incident stop conditions.
- `03_PRODUCTION_EVIDENCE_MATRIX.md` - the `A-defender-malicious` fixture row
  and the Defender-malicious lifecycle row are now in-scope production rows
  rather than Choice-B-excluded Conditionals; Defender decision evidence,
  screenshot item 5, the Pass criteria, and the current-recommendation section
  updated; the admission audit line added to the allowed evidence list.
- `IMPLEMENTATION_COMPLETION_REPORT.md`, `CLAUDE_HANDOFF.md`,
  `COMPLETION_REPORT.md` - superseding notes added and forward-looking
  choice-B instructions corrected. Their historical release, pipeline, and
  verification facts are preserved rather than rewritten.

Documents added:

- `04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md` - the plan choice A requires:
  what EICAR is and why the alert is expected, fixture custody, the advance
  notification table, the expected `rejected` state transition, eleven required
  negative proofs, remediation and cleanup, active-absence checks, the honest
  seven-day retention treatment, row-specific stop conditions, and the evidence
  the row produces.
- `05_PROOF_WINDOW_RUN_CHECKLIST.md` - the runnable day-of document.
- `06_PROOF_ADMISSION_AUDIT_RECORD.md` - the audit record specification.
- this report.

Nothing outside `services/photo_lifecycle_access_service.py`,
`tests/test_photo_lifecycle_access.py`, and
`docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/` changed. `app.py`,
`static/js/interview-studio.js`, `owner_routes.py`, `.env.example`,
`tests/test_owner_photo_capture.py`, templates, CSS, SQL, migrations, Azure
scripts, homepage files, and shared governance were not touched.

## C. What this means in plain English

Two things were blocking Pete from booking the day where the private photo
feature gets tested against the real live site.

**First, the test would have left no trace on the server.** The code already
accepted a "run label" for the test session, but nothing ever used it. Every
other message the photo code writes to the log is an error message. So if the
test had gone perfectly, the server would have recorded nothing at all - no
proof the special test mode was switched on, no proof it let the right test
accounts in. The only evidence would have been screenshots of a browser, which
show what a screen displayed, not what the server decided. The code now writes
one short line the first time the test mode actually lets someone in. That line
contains two things only: the words "proof mode", and the run label. No account,
no email, no file name, no expiry time.

**Second, Pete changed his mind about the virus test.** Earlier he had decided
to skip testing that a genuinely malicious upload gets blocked in production,
which left that one check permanently marked unproven. He has now decided to run
it, using EICAR - a harmless, standard test file that antivirus makers publish
specifically so companies can check their scanner is working. It is not a virus
and does nothing. Microsoft Defender will report it as dangerous and quarantine
it, which is exactly the desired result. The main risk is human: if nobody warns
the security team, a real person will see a real malware alert and reasonably
assume the site has been attacked. So the new plan spells out exactly who must
be told beforehand, what they must be told, how the test file is handled so it
never ends up in the codebase, and when to stop.

Alongside that, there is now a single day-of checklist Pete or an operator can
follow from the first check to the final "everything is switched back off"
confirmation.

## D. What the website or member can do now

Nothing new, and nothing changed for anyone. Members still have the released
Type and Voice Capture paths. Photo remains unavailable because both flags are
false. No route, page, screen, or response changed. The one new server log line
only ever appears during an approved proof window that has not been scheduled or
run.

## E. How this connects to PeerSlate

The change preserves the Bible v2.6 and Roadmap v2.5 position: authorization
before retrieval, server-derived ownership, private media, deterministic
lifecycle, and the chain

`private Photo source -> known-clean safe derivative -> member-authored note -> explicit private Capture -> optional later exact-version Moment`

The audit record strengthens the evidence discipline the governance documents
already require, without weakening the privacy rules they impose: it adds a
positive server record while explicitly enumerating and bounding what may be
written. Choice A closes a permanent hole in the production evidence matrix -
the malicious-upload path was going to stay unproven forever under choice B.

## F. Verification and validation

### Authority review

- Followed `START_HERE.md`; read `AGENTS.md`, `CLAUDE.md`, and
  `docs/AI_WORKFLOW.md` in full.
- Read `docs/governance/CURRENT_BASELINE.yaml` and confirmed Bible v2.6 /
  Roadmap v2.5 as the current authority.
- Read all seven pre-existing documents in this package.
- `git fetch origin --prune`; confirmed `origin/main` is exactly
  `ed3409a902f38e9437f6fbf70d3f2f61625037f4`, matching the assignment.
- Confirmed `origin` is Azure DevOps and `github` is the mirror.
- Created `work/2026-07-20-photo-proof-readiness-001` from that exact commit in
  a dedicated worktree; no other branch or worktree was touched.

### Automated tests

Run with `unittest`, not pytest - pytest is not installed in this environment
and `python -m pytest` exits silently, producing a false green.

| Command | Result |
| --- | --- |
| `venv/bin/python -m unittest discover -s tests -t .` on the exact base, before any edit | **642 passed, 2 skipped** |
| `venv/bin/python -m unittest tests.test_photo_lifecycle_access tests.test_owner_photo_capture` after the change | **53 passed** |
| `venv/bin/python -m unittest discover -s tests -t .` after the change | **654 passed, 2 skipped** |

654 = the 642 baseline plus the 12 added tests. No pre-existing test changed,
and no regression appeared.

### Security and privacy checks

- The audit line's arguments are asserted to be exactly the mode literal and
  the run id - not merely that forbidden strings are absent, but positively
  that nothing else is present.
- Forbidden-fragment assertions cover both cohort user keys, the non-cohort
  key, the test email domain, and expiry-shaped text, against both the rendered
  message and the raw log arguments.
- Non-emission is asserted for `off`, four distinct `invalid` configurations,
  `ordinary` release, and non-cohort denial, including end-to-end through a
  real route.
- No real environment value, key, secret, identity, or setting was read, set,
  printed, or invented.
- No EICAR string, fragment, encoded form, or generator was written to any file.
  Verified by scanning the full branch diff.

### Evidence limits, stated honestly

- No production proof window was run. Every row in
  `03_PRODUCTION_EVIDENCE_MATRIX.md` remains unrun.
- The audit record is proven by unit and route-level tests against the released
  code path. It has **not** been observed in production, because doing so would
  require enabling proof mode.
- No Azure, Defender, SQL, storage, or setting state was inspected or changed.
- No production screenshot, synthetic identity, or production record was
  created.
- Choice A's operational plan is a plan. Its notification acknowledgements,
  fixture approval, and alert coordination have not been obtained; they are
  preconditions for a window that is not yet scheduled.

## G. Known gaps, risks, and exclusions

- The optional production evidence and both-Blob active-absence verifier still
  does not exist. It remains an attended, owner-scoped production operation
  needing separate approval, exactly as the prior lane recorded.
- The audit record is per-process. In a multi-worker deployment the number of
  lines reflects worker count, not admission count. This is intended and
  documented; do not read the line count as a request count.
- The two-hour server cap on a proof window is a real operational constraint. A
  run that overruns will be cut off mid-flight with no warning. Section 0 of
  the checklist budgets for it.
- Choice A introduces a genuine production Defender alert. The mitigation is
  advance notification, and the plan treats a missing acknowledgement as a
  reason to skip the row, not a reason to proceed quietly.
- Active absence is not permanent erasure. The seven-day soft-delete retention
  window is stated as retention in every place the row is described, and a
  permanent-absence claim is explicitly deferred to a separately approved
  post-retention check.
- Overall lifecycle readiness remains **Conditional**, unchanged. Ordinary
  Photo enablement remains blocked on the full matrix, teardown, accepted and
  live homepage parity, and a separate explicit owner and manager decision.
- No independent or deeper review is requested. The diff is small, additive,
  and fully covered by tests.

## H. Clear next step

The designated manager reviews this branch and, if accepted, opens the Azure
pull request. After a green pipeline with both Photo flags still false, the
proof window can be scheduled against
[`05_PROOF_WINDOW_RUN_CHECKLIST.md`](05_PROOF_WINDOW_RUN_CHECKLIST.md).

The single blocking item for scheduling is the choice A security coordination:
the fixture approval and the written acknowledgements in the notification table
of [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md).
That work can start immediately and in parallel with the PR.

Owner Home frontend and Interview homepage parity remain independent lanes and
may proceed unaffected; this branch touches none of their files.

## I. What Pete needs to do or decide

1. Confirm the recorded Defender choice A decision as it is now written in
   `02_PROOF_MECHANISM_AND_ROLLOUT.md`.
2. Nominate the security/operations alert owner and confirm who else appears on
   the notification list, so the acknowledgements can be obtained.
3. Choose a target date and a two-hour attended window.

No credential, portal, configuration, SQL, production, homepage, or
Photo-enable action is requested.
