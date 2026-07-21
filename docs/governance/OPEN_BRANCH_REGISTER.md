# PeerSlate Open Branch Register

_Created 2026-07-21 by `PS-GOV-TRUTH-RECONCILIATION-001`, from authoritative
Azure `origin/main` at `0717e03c9f1d4e6b67f355fd1556651086ddc351`._

## What this register is for

`BRANCH_DISPOSITION_RECORD.md` inventories **stale** branches, worktrees, and
stashes and proposes preserve/archive/delete dispositions for them. This
register covers a different and more urgent case: branches that were **pushed to
`origin` and are not merged, not abandoned, and not named in any lane record**.

Work in this state is invisible to the governance pointers. A manager
dispatching from `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, or
`ACTIVE_INITIATIVES.md` cannot see it, which risks two failures: the work is
silently lost, or a fresh writer is assigned to re-do something that already
exists.

**This register authorizes nothing.** It records what exists and what decision
each item needs. No branch here may be merged, reworked, or deleted without an
explicit owner decision and a normal Azure pull request.

## Verification commands

Re-run these before acting on any row; `origin` moves.

```bash
git fetch origin --prune
git rev-list --left-right --count origin/main...origin/work/<branch>
git log origin/main..origin/work/<branch> --format='%h %ad %s' --date=short
git diff --stat origin/main...origin/work/<branch>
```

---

## Row 1 — `work/2026-07-20-interview-me-microphone-001`

| Field | Value |
|---|---|
| Tip | `cb7ad20` |
| Position | 2 ahead of `main`, 4 behind |
| Package | `PS-INTERVIEW-MIC-001` (exists only on this branch) |
| Lane record | **None** |
| Decision needed | Merge, rework, or archive |

**What it contains.** Continuous speak-your-answer dictation for Interview Me,
plus a package with an architecture decision, an implementation/evidence
record, and six committed screenshots covering listening state in desktop
5A-light and 5C-dark, mobile 390px in both themes, permission-denied, and the
composer row.

Changes `static/js/interview-studio.js` (+247), `templates/interview_studio.html`,
`static/css/interview-studio.css`, and `tests/test_interview_studio.py` (+252).
1,056 insertions across 13 files.

**Why it matters.** This is real, evidenced product work against the released
Interview Studio, and it touches the exact files the accepted 5A/5C release
owns. It cannot merge without a visual-integrity comparison against the
released Studio authority and Pete's acceptance.

**Risk if left.** `main` has moved 4 commits and will keep moving. The longer
this sits, the more likely another Interview change conflicts with it.

---

## Row 2 — `work/2026-07-20-interview-validator-truthfulness-001`

| Field | Value |
|---|---|
| Tip | `56a3232` |
| Position | 4 ahead of `main`, 4 behind |
| Package | Recorded inside `PS-INTERVIEW-PUBLIC-GATE-001` evidence on the branch |
| Lane record | **None** |
| Decision needed | Merge, rework, or archive |

**What it contains.** A fix for two Interview validators that rejected
legitimately empty output — the case where a candidate answer honestly has zero
strengths to report. Later commits restore the requirement for improvements
while keeping empty strengths allowed, and set owner-chosen wording for the
empty-strengths state. Four committed screenshots cover the zero-strengths
review state in desktop 5A-light, 5C-dark, mobile 390px, and a with-strengths
comparison.

Changes `app.py` (+51), `static/js/interview-studio.js`,
`static/css/interview-studio.css`, `templates/interview_studio.html`, and
`tests/test_interview_studio.py` (+314).

**Why it matters.** This is a truthfulness fix: without it the product can
refuse to display an honest empty result. It also carries an owner wording
decision that exists nowhere on `main`.

**Interaction.** Overlaps Row 1 in `interview-studio.js`,
`interview-studio.css`, `interview_studio.html`, and `test_interview_studio.py`.
The two branches must be sequenced, not merged in parallel.

---

## Row 3 — `work/2026-07-20-photo-proof-readiness-001`

| Field | Value |
|---|---|
| Tip | `0db8a2a` |
| Position | 1 ahead of `main`, 4 behind |
| Package | `PS-CAPTURE-PHOTO-LIFECYCLE-001` (merged and closed on `main`) |
| Lane record | **None** |
| Decision needed | Owner decision on Defender path, then merge or archive |

**What it contains.** Proof-window readiness extending the closed Photo
lifecycle package: a Defender Choice A operational plan, a proof-window run
checklist, a proof-admission audit record, an updated threat model and evidence
matrix, plus `services/photo_lifecycle_access_service.py` (+70) and
`tests/test_photo_lifecycle_access.py` (+284). 1,646 insertions across 13 files.

**⚠ Contains an owner decision that contradicts `main`.**

- `main` records **Defender choice B**: no production EICAR or malware test, the
  production malicious path stays Conditional. See
  `PS-CAPTURE-PHOTO-LIFECYCLE-001/COMPLETION_REPORT.md:5` and
  `02_PROOF_MECHANISM_AND_ROLLOUT.md:12`.
- This branch records that the owner **replaced B with A** — a coordinated inert
  production test — and builds the operational plan for it. See the branch's
  `README.md:27` and `README.md:160`.

Only one of these can be current. Until Pete confirms which, `main` is the
controlling record and Defender choice B stands. **No production Defender test
may be planned or run against the strength of this unmerged branch alone.**

---

## Row 4 — `work/2026-07-20-bible-v27-activation`

| Field | Value |
|---|---|
| Tip | `4fa0a36` |
| Position | 1 ahead of `main`, 4 behind |
| Package | `PS-GOV-CONNECTED-SYSTEM-001` |
| Lane record | **None** |
| Decision needed | Archive (recommended) |

**What it contains.** The original attempt to activate Bible v2.7 and Roadmap
v2.6 as controlling authority.

**Status: superseded twice.** Its pull request, **Azure PR 115, was abandoned**.
PR 117 (`efd3433`, pipeline 169) activated v2.7/v2.6 instead, and PR 118
(`3d7c9e1`, pipeline 171) then superseded those with Bible v2.8 and Roadmap
v2.7, which are current.

**Recommendation.** Archive-tag and delete. It edits `CURRENT_BASELINE.yaml`,
`CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`, `DOCUMENT_CONTROL.md`, and both
guardrail suites against a two-versions-old authority. Merging it now would
actively regress the current baseline. Follow the five-step destructive-operation
procedure in `docs/AI_WORKFLOW.md` and create the recovery tag first:

```bash
git tag archive/2026-07-21/bible-v27-activation 4fa0a3670dcf1d117381df56b83f8ea57a86830d
git push origin archive/2026-07-21/bible-v27-activation
```

---

## Owner decisions, 2026-07-21

Pete reviewed this register on 2026-07-21 and delegated the remaining calls to
the designated session manager ("yes to what is best, you decide"). The
manager's decisions and the evidence behind them are recorded here.

**All four rows are closed as of 2026-07-21. This register is now history.**

| Row | Branch | Decision | Outcome |
|---|---|---|---|
| 2 | `interview-validator-truthfulness-001` | Merge first; repairs two live production defects | **Released.** PR 123, merge `f3749d8`, pipeline 177; verified live |
| 1 | `interview-me-microphone-001` | Merge second; manager visual acceptance granted | **Released.** PR 124, merge `6d36bd4`, pipeline 178; live signature `studio-5a5c-4` |
| 3 | `photo-proof-readiness-001` | Merge third; Defender B controls, A prepared-and-deferred | **Released.** PR 125, merge `74a7427`, pipeline 179; Photo still flag-off |
| 4 | `bible-v27-activation` | Archive | **Archived.** Tag `archive/2026-07-21/bible-v27-activation`; remote branch deleted |

Every remote source branch was deleted by Azure on completion. No branch in this
register remains open.

**The asset-signature correction proved itself.** When PR 124 was merged after
PR 123, Git raised a real conflict on the two signature lines — precisely because
the numbers had been made to differ. Had both branches stayed on `studio-5a5c-3`
as originally written, the identical textual change would have merged silently
and the second release would have shipped different bytes under an
already-cached URL. The conflict was resolved in favour of `studio-5a5c-4`, and
the live JavaScript was then confirmed to carry both releases' changes.

The test that pinned the literal `studio-5a5c-3` was rewritten during that merge
to assert the invariant instead — two signatures, identical to each other, ahead
of the last released one — because pinning a literal is what let the collision
form unnoticed.

**Merge order is not cosmetic.** Row 2 first because it ends a live outage and
carries no visual gate. Row 1 second because of the asset-signature dependency
below. Row 3 third; it is documentation plus a flag-off service and is
independent of the other two.

### Asset-signature collision — found and corrected 2026-07-21

Rows 1 and 2 each independently bumped the Interview Studio asset signature from
`studio-5a5c-2` to `studio-5a5c-3`. Because both sides make the **identical**
textual change, Git merges it silently — no conflict, no warning, nothing in the
pipeline would have caught it.

`app.py` leaves versioned static assets cacheable by design and marks only
`text/html` as `no-cache`, so the `?v=` string is the Studio's only cache-busting
mechanism. Shipping both rows as `-3` would have published **different bytes
under a URL already cached from the first release**: a returning visitor would
receive Row 1's new markup while still running Row 2's JavaScript, so the
dictation controls would render and do nothing — reproducing the exact "there is
no microphone" failure Row 1 exists to fix.

Row 1 now publishes `studio-5a5c-4`, with its asset-signature test updated. Row 2
keeps `-3`.

**Standing rule for any later Interview branch:** check the signature actually on
`origin/main` before merging and bump beyond it. Do not trust the number recorded
in your own branch.

### Row 2 finding — a live production failure

Reviewing this branch surfaced a defect on live `main` that no record mentioned.
`validate_interview_model_answer` rejects an empty `evidenceIds` list, but the
best-practice system prompt instructs the model to return exactly
`"evidenceIds":[]`, and the call passes an empty evidence map. Both possible
model outputs are therefore rejected:

| Model output | Result on `main` |
|---|---|
| `evidenceIds: []`, as its own prompt demands | `model answer has no approved evidence references` |
| any cited id, against an empty evidence map | `model answer referenced unauthorized evidence` |

Verified by calling the validator directly on `main` at
`0717e03c9f1d4e6b67f355fd1556651086ddc351`. **Interview Studio "Get Answer" in
best-practice and compare modes cannot succeed in production; every request
returns 502.** This is a closed trap, not an intermittent provider issue.

The branch's fix adds `require_evidence=False` for illustrative answers only.
Both security properties were re-verified against the branch and still hold: an
illustrative answer that cites any id is still rejected, and a grounded answer
with no citation is still rejected.

Row 2 should merge before Row 1 because it is a repair, is independent of the
visual gate, and its files are a subset of Row 1's.

### Row 1 — manager visual acceptance, with evidence

The branch was run locally at its exact pushed tip `cb7ad20` and inspected in
both themes rather than accepted from its documentation.

- **Deviation D-1, listening colour red to gold: accepted.** Light theme renders
  `#8A5A00` on `#F6E9C9`, a contrast ratio of **4.92:1**; dark renders `#D99A2B`
  on the composited dark surface at **6.14:1**. Both pass WCAG 2.2 AA for normal
  text. `#8A5A00` is the approved Marigold text-safe token and `#F6E9C9` the
  Marigold soft token, so the state uses the Deep Navy Gold system rather than a
  new colour. Reserving red for genuine errors is correct; a listening indicator
  is a current-state cue.
- **Deviation D-2, control relocated: accepted.** Confirmed in the DOM that the
  control now shares the composer action row with Submit answer, which is the
  fix for the reported absence.
- **Status and interim regions render correctly.** The interim label is
  `display: block` and sits on its own line above the transcript preview.
- **Truth copy is accurate**: it states the browser performs transcription and
  that PeerSlate does not receive or keep the audio, without overclaiming that
  audio never leaves the device.

**Not verified, and it cannot be from here:** real microphone permission and
real vendor transcription. No browser in this environment can grant them
non-interactively. Pete should exercise one real dictation after release.

### Row 3 — Defender choice B now, choice A at enablement

Both branches record contradictory owner decisions dated the same day. The
manager decision that supersedes both:

**Choice B stands as the current recorded decision. Choice A is not cancelled;
it is deferred to the Photo enablement window.**

Reasoning:

1. EICAR is an inert test string with no payload or exploit, so choice A is not
   dangerous in itself, and the operational plan is careful.
2. Choice A's plan requires a six-party written acknowledgement including a
   security responder on duty, an on-call rotation holder, and a SIEM/MDR
   provider, and states the security contact "must be a real second person".
   Those parties do not currently exist for PeerSlate, and the plan's own
   completion report confirms none of the acknowledgements has been obtained.
3. A production Defender proof has a shelf life. It evidences production
   configuration at the moment it runs, not at enablement. Photo enablement is
   gated behind universal-composer / Save Moment / derived-Journal integration
   and is a substantial future package, so a proof run now would very likely
   need repeating.
4. Choice B costs nothing today, retains the existing isolated-account proof,
   and leaves exactly one row honestly marked `Conditional`.

**No production Defender test is authorized by this decision.** When Photo
enablement is scheduled, choice A should be run inside that window with the
coordination in place, and this record replaced.

**Made a gate, not a plan.** Today's reconciliation existed because plans without
gates get lost. This deferral is therefore recorded as blocking **Gate 3** in
`docs/initiatives/PS-CAPTURE-MEDIA-001/README.md`, which requires either the
executed choice-A plan or a fresh explicit owner decision to enable with the row
left `Conditional`. The choice-A operational plan is merged in a
prepared-and-deferred state, with every "choice A is selected" assertion in that
package corrected, so a future session cannot read the merged plan as
authorization.
