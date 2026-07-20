# PeerSlate Next-Task Board

_Prepared 2026-07-20 by a Claude Code review session at Azure `origin/main`
`531013dd8c1a05e2443becd881a226755f27ca14`. This board is a dispatch aid, not an
authority record. `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and
`ACTIVE_INITIATIVES.md` remain the controlling pointers. Fetch `origin` and
re-read them before starting any task below._

## How to use this board

Each task is written to be handed to a fresh session with no prior context. Give
the session the task's **Brief** verbatim, plus the standing instruction to open
`START_HERE.md` first. One writer per branch. Every branch starts from the exact
then-current `origin/main`, never from this recorded SHA if `origin` has moved.

Status vocabulary: **Assigned** means a named lane already owns it — do not
start a competing session. **Open** means no writer is assigned and it is
available. **Owner decision** means it is blocked on Pete, not on capacity.

## Already assigned — do not start these

| Package | Lane owner | Current state |
|---|---|---|
| `PS-CAPTURE-MEDIA-001` | ChatGPT Work/Codex manager | Released flag-off; enablement gates open; enablement writer unassigned |
| `PS-HOME-INTERVIEW-PARITY-001` | ChatGPT Work/Codex manager; **Claude Code sole writer** | Architecture checkpoint merged; manager review pending; implementation not started |
| `PS-HOME-FRONTEND-001` | ChatGPT Work/Codex manager; separate Codex task sole writer | Activated; writer branch pending |

`PS-HOME-INTERVIEW-PARITY-001` is the one already-assigned lane that belongs to
a Claude session. If Pete wants a Claude session working product code right now,
that is the correct one to staff, as its sole writer.

---

## Task 1 — Photo dark-launch implementation (Open)

**Why it is open.** `PS-CAPTURE-PHOTO-LIFECYCLE-001` merged through Azure PR 107
at `531013dd8c1a05e2443becd881a226755f27ca14`. It is architecture and evidence
planning only; its README records the later implementation writer as
unassigned. Codex has confirmed the owner approved the architecture and selected
Defender Option B: no production EICAR or malware test, retain the
isolated-account proof, and keep the production malicious path Conditional.

**Brief.** You are the sole implementation writer for the Photo dark-launch
slice. Open `START_HERE.md`, fetch `origin`, and create
`work/YYYY-MM-DD-capture-photo-dark-launch-001` from the exact current
`origin/main`. Read `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/` in full —
all five files — before writing code. Implement a server-only dark launch:
fail-closed synthetic identity gating, route coverage, tests, proof tooling, and
package evidence. `CAPTURE_PHOTO_ENABLED` stays `false` and no ordinary member
gains Photo access. Do not perform a production EICAR or malware test; the
production malicious path stays Conditional by owner decision. Dark-launch proof
does not depend on homepage parity. Self-review the complete diff, run the full
suite plus the two guardrail suites, report `Pass`, `Conditional`, or `Fail`,
and stop for manager and Pete acceptance before opening the PR.

**Explicitly out of scope.** Enabling Photo, homepage Photo parity, any change
to Voice, and any schema change beyond what the lifecycle package already
authorizes.

---

## Task 2 — Connected-system Bible v2.7 authority (Open, needs manager named)

**Why it is open.** Pete supplied the Connected-System and Hooks handoff on
2026-07-20. It is now staged in-repo at
`docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/` with the source Markdown, PDF,
and architecture diagram preserved. No candidate Bible v2.7 exists;
`docs/governance/` still tops out at v2.6.

**Brief.** You are the sole writer for `PS-GOV-CONNECTED-SYSTEM-001`. Read
`docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/README.md` and then the complete
source handoff in that package's `source/` directory. Section 12 of the handoff
is your execution procedure and Section 13 is your deliverable list; follow them
literally. Create branch `docs/connected-system-return-value-authority` from the
exact current `origin/main`. Produce a candidate Bible v2.7 marked `PROPOSED`,
leaving v2.6 unchanged as historical authority. This is documentation only: no
flag, route, schema, deployment, or production setting may change, and you may
not touch `CURRENT_BASELINE.yaml` or `CURRENT_STATE.md` to claim v2.7 is
current. Activation is a separate step after Pete approves.

**Blocked on.** Pete naming the designated session manager, because this package
edits shared governance artifacts while three Codex-managed lanes are active.
Serialize against them.

---

## Task 3 — Resolve the Bible v1.5.1 authority question (Owner decision)

**Why it is open.** `PeerSlate_Company_and_Product_Bible_v1.5.1.pages` and
`PeerSlate Career Platform Vision.pages` sit untracked in the repository root.
v1.5.1 is dated July 17, 2026, presents itself as an implementation baseline
superseding v1.3 and v1.4, and locks an Appendix K "Member Intelligence and
Activation System" with its own traceability, testing, and release-gate regime.
`DOCUMENT_CONTROL.md` lists supersessions only through v1.4 and never mentions
it, so it reads as a parallel numbering line rather than settled history. It
carries at least two positions that collide with current authority: "the Journal
is the member profile" while Journal UI is held, and the retired Iris Foundry
color direction.

**What is needed from Pete.** One decision: is v1.5.1 (a) superseded history to
be archived, (b) a live authority whose unique content must be reconciled into
the v2.x line, or (c) a draft that never took effect. This should be settled
before candidate v2.7 is approved, so the new Bible supersedes a known set.

**Follow-on task once decided.** Record the disposition in
`DOCUMENT_CONTROL.md`, decide whether the two `.pages` files are committed,
converted, or left local, and note that `.pages` is a binary format that does
not diff.

---

## Task 4 — Member-history salvage (Open, newly unblocked)

**Why it is newly open.** The previous audit deferred this until the new
Interview Studio became authoritative. That condition is now met: the accepted
5A/5C Studio released through Azure PR 101 at
`39002f5130a1766d2090007c16582e0dbe07226c`, pipeline 149 passed, and live
`/interview-studio` now serves `Interview Me` and `ps-theme` with `Video Me`
gone.

**Current branch facts.** `origin/work/2026-07-17-member-history-completion` is
at `b439afb`, 54 commits behind `main` and 1 ahead. It contains useful private
Interview Story grounding, owner-isolated services, migrations, APIs, and
confirmation/versioning work. Its SQL migration was never applied.

**Brief.** Do **not** merge or rebase that branch. Its UI layer modifies the
Interview template, CSS, JavaScript, and tests that the released 5A/5C
implementation has since replaced, so a merge would regress the live Studio.
Read the branch read-only, extract the backend, service, and migration concepts
worth keeping, and write a fresh proposal package describing how they would
integrate against the released Studio. Assume nothing about the current schema
without inspecting it. Produce a written package, not an implementation.

---

## Task 5 — Interview coaching provider reliability (Open)

**Why it is open.** Flagged during the Interview review and never given a lane.
Coaching responses intermittently return validated 502 failures when the AI
provider produces incomplete output. The client handles this honestly, so this
is a backend reliability task rather than a correctness bug, and it was
deliberately kept out of the Studio acceptance.

**Brief.** Investigate the incomplete-output failure mode behind the public
Interview coaching path. Characterize it before changing anything: how often,
which inputs, which provider condition. Then propose bounded handling —
retry, partial-response detection, or a clearer degraded state. Preserve the
current honest client behavior; do not fabricate coaching content when the
provider fails. Add focused tests for the failure path.

---

## Task 6 — GitHub mirror sync (Owner decision)

**Why it is open.** `github/main` is at `d5dd7bd`, now **49 commits behind**
Azure. The baseline records the mirror push as on hold pending explicit owner
approval, and the current `next_gate` repeats that hold. This is a deliberate
hold, not a defect.

**What is needed from Pete.** Approval to run `git push github main
--follow-tags`. It is a backup-only mirror; GitHub Actions deployment stays
disabled either way.

---

## Task 7 — Branch, worktree, and stash disposition (Open, low priority, do last)

**Why it is open.** Housekeeping was correctly sequenced behind the
reconciliation. Nothing should be deleted until each item has a recorded
disposition.

**Current inventory.** Six stale remote branches, each ahead of `main` by the
count shown: `work/2026-07-18-voice-001` (5),
`work/2026-07-19-control-room-deploy-evidence` (1),
`work/2026-07-19-interview-gate-24-review` (1),
`work/2026-07-19-owner-home-viewer-architecture` (4),
`work/2026-07-19-voice-visual-parity-001` (6), and
`work/2026-07-17-member-history-completion` (1, see Task 4). Locally there is an
orphaned locked `/tmp/wt-dn` worktree record pointing at a missing directory,
three older worktrees under `~/Documents/Website/`, and a preserved CSS stash
touching 11 stylesheets.

**Brief.** Produce a disposition record for every item — preserve, archive-tag,
or delete — before any deletion. Follow the destructive-operation rules in
`docs/AI_WORKFLOW.md`: recovery reference first, then scope confirmation, then
the operation. `work/2026-07-16-adopt-product-bible-v13` remains
**do-not-merge**; its committed change deletes roughly 9,699 lines and
represents a retired product direction.

---

## Local environment note (not a repository task)

The primary Mac checkout's virtualenv is missing `azure-storage-blob` and
`Pillow`, both pinned in `requirements.txt`. Local runs therefore show import
errors and a lower test count than a clean clone. `pip install -r
requirements.txt` fixes it. `pytest` is also absent — the suites are `unittest`,
so the correct local command is:

```bash
venv/bin/python -m unittest discover -s tests -t .
```

Running `python -m pytest` silently does nothing in that venv, which has
previously produced false green signals.
