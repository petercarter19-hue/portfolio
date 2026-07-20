# PeerSlate Branch, Worktree, and Stash Disposition Record

_Prepared 2026-07-20 by a Claude Code session on branch
`work/2026-07-20-branch-disposition-record`, based from authoritative Azure
`origin/main` at `531013dd8c1a05e2443becd881a226755f27ca14`. This answers
Task 7 of `docs/governance/NEXT_TASK_BOARD.md`._

---

## 0. This document authorizes nothing

**No deletion is authorized by this document.** It is a written disposition
proposal so that Pete can approve, reject, or defer each item individually.

Producing this record involved **no deletions of any kind**. No branch,
worktree, stash, tag, or file was removed; no `git reset --hard`,
`git clean`, `git branch -D`, `git prune`, or force-push was run; and none of
the inventoried branches or worktrees was checked out or modified. Every
observation below came from read-only inspection.

Before any item here is deleted, `docs/AI_WORKFLOW.md` §"Destructive operations
and recovery" requires all five steps, in order:

1. explain why the deletion is necessary;
2. identify exactly what would be removed or rewritten;
3. create **and verify** the recovery reference (tag, bundle, or archive);
4. confirm the operation is limited to the intended scope;
5. report the recovery reference afterward.

Each row below supplies steps 1, 2, and the exact recovery reference for
step 3. Pete supplies the approval. The writer who executes supplies steps 4
and 5.

## 0.1 Snapshot caveat

This repository currently has multiple concurrent sessions and worktrees. The
local branch set changed between two commands during this inventory (a new
`docs/connected-system-return-value-authority` branch appeared mid-pass).
**Re-run `git fetch origin --prune`, `git branch -vv`, `git worktree list`, and
`git stash list` immediately before acting on any row.** Treat the SHAs here as
the state at 2026-07-20 11:27 CDT, not as a live guarantee.

## 0.2 How "already on main" was determined

Azure completes every pull request with a **squash merge**. A squashed branch
tip is therefore never an ancestor of `main`, and `git branch --merged` /
`git merge-base --is-ancestor` will always report "not merged" even when every
line of the work is live. All 17 task-branch commits inventoried here return
"not an ancestor of main" — that fact carries no information.

The test actually used was **content presence**: for every file each branch
touched relative to its merge base, compare the branch's blob with `origin/main`
and classify it `IDENTICAL_ON_MAIN`, `DIFFERS_ON_MAIN`, or `ABSENT_FROM_MAIN`.
Every `DIFFERS` case was then read to decide which side is newer — main having
moved past a branch is preservation, not loss; a branch holding lines main never
received is loss.

---

## A. Remote task branches on `origin` (Azure DevOps)

`origin` currently carries seven `work/*` branches besides `main`.

### A1. `work/2026-07-18-voice-001` — archive-tag-then-delete

| Field | Value |
|---|---|
| Tip SHA | `705161d418539bbde5550f57d5ecdafdc3fd4bb5` |
| Ahead / behind `origin/main` | 5 ahead, 33 behind |
| Merge base | `fd27b2147b6a34019353d038331f4bde4f97d3b5` |
| Local copy | none (remote-tracking only) |

**Contains.** The original PS-VOICE-001 private Voice Capture delivery: 32 files,
+5,380/−37 — `services/voice_capture_service.py`,
`services/media_storage_service.py`,
`services/speech_transcription_service.py`, the voice capture SQL migration,
rollback and isolation-verification scripts, the Azure provisioning PowerShell,
`static/js/owner-capture-voice.js`, eight evidence screenshots, and seven test
modules. Five commits: `7fed189`, `bcd12c7`, `d868fda` (merge from main),
`25d4bf2`, `705161d`.

**Already on main?** Yes, fully and then some. PS-VOICE-001 landed on `main` at
`eede856` and was refined again by PR 80/81
(`864a79d`, `5cc5b69`). Of the 32 touched files, 17 are byte-identical on main.
Every one of the 15 `DIFFERS` files was inspected: in each case main is the
**newer superset**. Examples — the branch's `PS-VOICE-001/COMPLETION_REPORT.md`
is a strict subset (main has 27 additional lines); the branch's
`owner_routes.py` still has `schema_version = 2 if capture.get("capture_type")
== "voice" else 1` where main has the superseding
`schema_version = {"voice": 2, "photo": 3}.get(...)`; the remaining deltas are
main's later Photo Capture additions that the branch simply predates.

**Would anything be lost?** No unique content was found.

**Recommended disposition.** Archive-tag, then delete the remote branch.

**Required recovery reference (must exist and be verified first):**

```bash
git tag -a archive/2026-07-20/voice-001 705161d418539bbde5550f57d5ecdafdc3fd4bb5 \
  -m "PS-VOICE-001 original Voice Capture writer branch; superseded by main eede856 + PR 80/81"
git push origin archive/2026-07-20/voice-001
git rev-parse archive/2026-07-20/voice-001^{commit}   # must print 705161d4...
```

---

### A2. `work/2026-07-19-control-room-deploy-evidence` — safe-to-delete

| Field | Value |
|---|---|
| Tip SHA | `43cc3ad02ac33154dc0c21e25fb3b730129b04c0` |
| Ahead / behind `origin/main` | 1 ahead, 20 behind |
| Merge base | `6cb49f135cc3a2749dd4539f8261d176b43dad9a` |
| Local copy | none |

**Contains.** One commit, two documentation files:
`docs/control-room/COMPLETION_REPORT.md` and
`docs/control-room/HANDOFF_FOR_REVIEW.md` (+117/−80).

**Already on main?** Yes, byte-identical. Both files match `origin/main`
exactly. `main` records the completed merge at `730c37d`
("Merge pull request 88 from work/2026-07-19-control-room-deploy-evidence into
main").

**Would anything be lost?** Nothing. This is the cleanest case in the inventory.

**Recommended disposition.** Safe-to-delete. Because both blobs are proven
identical on `main` and the Azure PR is recorded, an archive tag is optional
rather than required; the record below is still the cheapest insurance and
costs one tag object.

**Recovery reference (optional but recommended):**

```bash
git tag -a archive/2026-07-20/control-room-deploy-evidence 43cc3ad02ac33154dc0c21e25fb3b730129b04c0 \
  -m "PS-CONTROL-ROOM-001 deploy evidence; content identical on main via Azure PR 88"
git push origin archive/2026-07-20/control-room-deploy-evidence
```

---

### A3. `work/2026-07-19-interview-gate-24-review` — **PRESERVE (do not delete)**

| Field | Value |
|---|---|
| Tip SHA | `ca4af35117a4e3bb8bef0c8e98a26756677fc6cc` |
| Ahead / behind `origin/main` | 1 ahead, 28 behind |
| Merge base | `31864e43287d7cefb5a0d1c0441e94bec0bd6b1f` |
| Local copy | none |

**Contains.** One commit, four files, +429/−15:

- `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/08_GATE_24_REVIEW_REPORT.md`
  — a manager review whose recorded decision is **"Result: Fail"**, with the
  reasoning that the submitted archive was a homepage-walkthrough package for
  `PS-HOME-INTERVIEW-DEMO-001` rather than the nine-screen current-public
  Interview Studio package Gate 2.4 required.
- `artifacts/ps-interview-public-gate-001/gate-2.4-received/ATTACHED_ASSET_INDEX.md`
  — the received-asset index, including the archive's SHA-256
  `968BFD9723A216939AB078C77D9725102A47746DB10D35D5DE07AEF6EEC082E3`.
- `artifacts/ps-interview-public-gate-001/gate-2.4-received/PS-HOME-INTERVIEW-DEMO-001_Design_Authority_Package.zip`
  — the 4,444,154-byte submitted archive, preserved unchanged as the exact
  evidence reviewed.
- an updated `PS-INTERVIEW-PUBLIC-GATE-001/COMPLETION_REPORT.md` carrying
  `Self-certification: Fail`.

**Already on main?** **No.** Three of the four files are `ABSENT_FROM_MAIN` and
the fourth `DIFFERS`. `main` instead carries
`08_GATE_24_FINAL_VISUAL_REVIEW.md`, which is a **different, later, Conditional**
review produced on the separate branch
`work/2026-07-19-interview-gate-24-final-review` and merged as PR 90
(`6d5ef46`). Main has no `gate-2.4-received/` directory and no copy of this
ZIP anywhere in any ref — the only `.zip` under
`artifacts/ps-interview-public-gate-001/` on main is
`gate-24-final-visual-review/PeerSlate_Interview_Studio_PUBLIC-03-V02_Final_Visual_System.zip`,
a different artifact. The unpacked homepage screenshots under
`artifacts/ps-home-interview-demo-001/` on main are implementation evidence, not
this received design-authority package.

**Would anything be lost?** **Yes — permanently.** Deleting this branch destroys
(a) the only record that Gate 2.4 was first **failed** and why, and (b) the only
copy of the reviewed 4.4 MB design-authority archive with its verified hash.
Losing the Fail record leaves only the later Conditional record, which reads as
if the gate never failed.

**Recommended disposition.** **Preserve.** Do not delete this branch. The
correct resolution is a governance decision, not a cleanup action: either merge
the review record into `main` through a normal Azure PR so the gate history is
complete, or, if Pete decides the failed-gate record should not live on `main`,
archive-tag it and record that decision in
`docs/governance/DOCUMENT_CONTROL.md`. Either way the branch stays until that
decision is made and written down.

**Recovery reference required before any future deletion:**

```bash
git tag -a archive/2026-07-20/interview-gate-24-review ca4af35117a4e3bb8bef0c8e98a26756677fc6cc \
  -m "PS-INTERVIEW-PUBLIC-GATE-001 Gate 2.4 FAILED review + received 4.4MB design-authority archive; unique, not on main"
git push origin archive/2026-07-20/interview-gate-24-review
git rev-parse archive/2026-07-20/interview-gate-24-review^{commit}   # must print ca4af351...
```

---

### A4. `work/2026-07-19-owner-home-viewer-architecture` — archive-tag-then-delete

| Field | Value |
|---|---|
| Tip SHA | `6ef7bf74e363e6e6d8cbc23f7e0a9150fdbd53f6` |
| Ahead / behind `origin/main` | 4 ahead, 26 behind |
| Merge base | `5cc5b69346ee354bcc36248f7ee5724ce13c9d08` |
| Local copy | none |

**Contains.** Four commits (`f6d2a33`, two merges from main, `6ef7bf7`) creating
the ten-file `PS-OWNER-HOME-VIEWER-GATE-001` Gate B planning package (+1,579
lines): architecture, authorization/projection matrix, current-state inventory,
accessibility requirements, finite-home contract, implementation decomposition,
test/release plan, visual-truth handoff, README, completion report.

**Already on main?** Yes, and main is substantially ahead. Six of the ten files
are byte-identical on main. The four `DIFFERS` files were read: main is the newer
side in every case. Main's copy of the package has since gained fifteen further
documents (`01_FABLE_AUTHORITY_MANIFEST.md` through
`11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md`, the Codex and Sonnet implementation
briefs, `FABLE_COMPLETION_REPORT.md`) via PR 94 (`79a0ced`). The branch's
"unique" lines are older status text — its README still says
`Bible v2.5 and Roadmap v2.4` and `Status: architecture package complete with a
Conditional implementation gate`, both superseded on main by `Bible v2.6 and
Roadmap v2.5` and `architecture accepted by the designated manager`. The owner
direction added by the branch's final commit (`docs: keep future home
capabilities visible`) is present verbatim on main.

**Would anything be lost?** Only superseded, and now-inaccurate, status wording.

**Recommended disposition.** Archive-tag, then delete the remote branch.

**Required recovery reference:**

```bash
git tag -a archive/2026-07-20/owner-home-viewer-architecture 6ef7bf74e363e6e6d8cbc23f7e0a9150fdbd53f6 \
  -m "PS-OWNER-HOME-VIEWER-GATE-001 architecture writer branch; superseded by main via PR 94"
git push origin archive/2026-07-20/owner-home-viewer-architecture
git rev-parse archive/2026-07-20/owner-home-viewer-architecture^{commit}   # must print 6ef7bf74...
```

---

### A5. `work/2026-07-19-voice-visual-parity-001` — archive-tag-then-delete

| Field | Value |
|---|---|
| Tip SHA | `e32b31d7c351ac2f8601a4467bcd1c9450f52c3b` |
| Ahead / behind `origin/main` | 6 ahead, 28 behind |
| Merge base | `31864e43287d7cefb5a0d1c0441e94bec0bd6b1f` |
| Local copy | none |

**Contains.** Six commits rebuilding the Voice Capture UI against the approved
walkthrough (+2,342/−258 across 34 files): design instructions, parity matrix,
completion report, 26 named evidence screenshots, four approved visual-authority
images, and reworked `owner-app.css`, `owner-capture-voice.js`,
`owner_capture.html`, `tests/test_owner_voice_ui.py`.

**Already on main?** Yes. All 30 image files and `owner-capture-voice.js` are
byte-identical on main; the work merged through PR 80 and PR 81
(`864a79d`, `5cc5b69`). The four `DIFFERS` files were read and main is newer in
each: the branch's `COMPLETION_REPORT.md` still asserts
"**Not merged, not deployed** — awaiting Pete and ChatGPT Work real-visual
acceptance", which is exactly the pre-acceptance status that merging resolved,
and its `owner-app.css` and `owner_capture.html` predate main's later Photo
Capture and Owner Home additions (main is +1,015 and +232 lines respectively).

**Would anything be lost?** No unique content. The only branch-only lines are
stale "not merged" status claims that would be actively misleading if restored.

**Recommended disposition.** Archive-tag, then delete the remote branch.

**Required recovery reference:**

```bash
git tag -a archive/2026-07-20/voice-visual-parity-001 e32b31d7c351ac2f8601a4467bcd1c9450f52c3b \
  -m "PS-VOICE-VISUAL-PARITY-001 writer branch; superseded by main via PR 80/81"
git push origin archive/2026-07-20/voice-visual-parity-001
git rev-parse archive/2026-07-20/voice-visual-parity-001^{commit}   # must print e32b31d7...
```

---

### A6. `work/2026-07-17-member-history-completion` — **RESERVED (active lane)**

| Field | Value |
|---|---|
| Tip SHA | `b439afb2c94b527f68d6d31ba7a9e34e3f49387d` |
| Ahead / behind `origin/main` | 1 ahead, 54 behind |
| Merge base | `75ff29af80be856767f5687f5117144f040b2f08` |
| Local copy | `work/2026-07-17-member-history-completion`, same SHA |
| Worktree | `/Users/petercarter/Documents/Website/ps-interview-002c1-member-history` (**dirty**) |

**Status.** A separate salvage-analysis lane
(`work/2026-07-20-member-history-salvage-analysis`, Task 4 of the next-task
board) is **currently active** against this branch. Its contents were therefore
deliberately **not** analyzed in depth here; the identity facts above are
recorded and nothing further.

**Shallow facts only, for completeness.** One commit, 20 files, +2,961/−63.
Nine files are `ABSENT_FROM_MAIN`, including `interview_story_api.py`,
`services/interview_stories.py`, `tests/test_interview_stories.py`, and the
`PS-INTERVIEW-001_member_history_completion` SQL migration and rollback, which
the next-task board records as never applied.

**Would anything be lost?** Yes — this branch holds substantial content that is
not on `main`. It is also the subject of an in-flight analysis.

**Recommended disposition.** **Reserved-active. Do not delete, do not
archive-tag, do not merge, do not rebase, and do not touch the worktree** until
the Task 4 salvage lane returns its proposal and Pete rules on it. Revisit this
row only after that lane closes. The next-task board's standing instruction that
merging this branch would regress the released 5A/5C Studio remains in force.

**If a disposition is ever approved,** the recovery reference must be created
first:

```bash
git tag -a archive/2026-07-20/member-history-completion b439afb2c94b527f68d6d31ba7a9e34e3f49387d \
  -m "PS-INTERVIEW-002C1 member history; unique backend/migration content; see salvage analysis"
git push origin archive/2026-07-20/member-history-completion
```

---

### A7. `work/2026-07-20-next-task-board` — reserved-active

| Field | Value |
|---|---|
| Tip SHA | `34156b3eaa97beda303a5cc1f1b870bb39f97a9d` |
| Ahead / behind `origin/main` | 1 ahead, 0 behind |
| Local copy | checked out in the primary checkout `/Users/petercarter/portfolio` |

**Contains.** `docs/governance/NEXT_TASK_BOARD.md` (the board this record answers)
and the staged `PS-GOV-CONNECTED-SYSTEM-001` package: README, the source
handoff Markdown and PDF, and the architecture diagram (+1,064 lines).

**Already on main?** No — none of the five files exists on `main`.

**Recommended disposition.** **Reserved-active.** It is the current session's
open governance branch, not stale housekeeping. It exits this inventory through
a normal Azure PR, not through cleanup. No archive tag needed while it is live.

---

## B. Known standing ruling carried forward

### B1. `work/2026-07-16-adopt-product-bible-v13` — **PRESERVE, DO-NOT-MERGE**

| Field | Value |
|---|---|
| Tip SHA | `d21df223b0b1351fa48cdf583513803bf42f0c9d` |
| Ahead / behind `origin/main` | 1 ahead, 62 behind |
| Scope | local branch only — **not present on `origin`** |
| Worktree | `/Users/petercarter/Documents/Website/peerslate-v13` (**dirty**) |

**Ruling (carried forward unchanged).** This branch is **DO-NOT-MERGE**. Its
single commit `d21df22` ("feat: consolidate Community and Slate Board") is
44 files, **+755 / −9,699**, deleting `the_slate_daily.html`,
`the_slate_feed.html`, `the_slate_my.html`, `the_slate_people_interests.html`,
`slate_break.html`, `slate_pulse.html`, and their supporting partials and
tests. It represents a **retired product direction**. Verified this session: the
deletion count is exactly 9,699 lines as recorded.

**Recommended disposition.** **Preserve via archive tag; never merge.** Because
the branch exists only locally, it is one `git branch -D` away from
disappearing with no remote copy. The archive tag should be created **now**,
independent of any deletion decision, and pushed to `origin`.

**Recovery reference to create now:**

```bash
git tag -a archive/2026-07-20/adopt-product-bible-v13 d21df223b0b1351fa48cdf583513803bf42f0c9d \
  -m "DO-NOT-MERGE: retired v1.3 Community/Slate Board consolidation, -9699 lines; preserved for history only"
git push origin archive/2026-07-20/adopt-product-bible-v13
git rev-parse archive/2026-07-20/adopt-product-bible-v13^{commit}   # must print d21df223...
```

Only after that tag is pushed **and verified on `origin`** may the local branch
and its worktree be considered for removal — and see §D1 first, because that
worktree holds an untracked file that exists in no git ref.

---

## C. Local-only branch state

Twenty-five local branches exist. Eight of them have an **upstream configured
that no longer resolves** (`[gone]`) because Azure deleted the remote branch on
squash merge; that alone is not evidence of anything.

### C1. Squash-merged, content verified on `main` — archive-tag-then-delete

For each of these, every file the branch touched was compared against
`origin/main`. Where a file `DIFFERS`, the difference was read and confirmed to
be **main having moved forward** (later PRs editing the same governance or
application files), not branch-unique content.

| Local branch | Tip SHA | Ahead | Azure PR on main | Verification result |
|---|---|---:|---|---|
| `work/2026-07-17-display-name` | `d624ae99e58e849058d08e035b4d35cb8b18c19b` | 1 | PR 54 `e043705` | 2/2 files identical on main |
| `work/2026-07-17-owner-settings` | `fc835993e07458485c9f148ee59598e330aa4dc1` | 1 | PR 55 `086753f` | 2/5 identical; `app.py`, `owner_routes.py`, `owner_workspace.html` differ only because main is 53 commits newer |
| `work/2026-07-20-capture-photo-lifecycle-001` | `c6c06fad2c2067827157eda1841e98ab2af403e1` | 1 | PR 107 `531013d` | 5/5 files identical on main |
| `work/2026-07-20-home-frontend-manager` | `95af77a84dc4354874f7dd90b1d9ba69e231662d` | 1 | PR 104 `5217247` | 7/7 files identical on main |
| `work/2026-07-20-home-interview-parity-001` | `6625b52ca4620b503ec56dcc15567470b6ef2499` | 4 | PR 105 `4deb0a0` | 28/29 identical; `EVIDENCE_INDEX.md` differs because the PR 106 closeout amended it |
| `work/2026-07-20-home-interview-parity-closeout` | `83567a5f5baa8ebc42c4d26bd0fe5b0de270fa5b` | 1 | PR 106 `8fb501d` | 5/5 files identical on main |
| `work/2026-07-20-home-interview-parity-manager` | `44761d47ea7d1cb0e0f21db4a6dae630f597d927` | 1 | PR 103 `b7b6744` | 4/8 identical; the four governance files differ only because PRs 105–107 updated them afterwards |

**Recommended disposition.** Archive-tag-then-delete, **but** each must first
clear the verified-squash-merge gate in §F, and four of the seven are still
attached to worktrees (§D) that must be dealt with first. A single grouped tag
is acceptable per branch tip:

```bash
git tag -a archive/2026-07-20/<short-name> <full-sha> -m "squash-merged via Azure PR <id>; archived before local cleanup"
git push origin archive/2026-07-20/<short-name>
```

### C2. Already an ancestor of `main` — safe-to-delete, no tag needed

These point at commits that are literally reachable from `origin/main`. Deleting
the ref removes a name, never an object.

| Local branch | Tip SHA | Note |
|---|---|---|
| `codex/ps-auth-001-display-name` | `d8627eef80f64601ab080b8973a1ce7d8bf6d9cb` | 56 behind, 0 ahead; commit is on main |
| `work/2026-07-20-interview-release-closeout` | `39002f5130a1766d2090007c16582e0dbe07226c` | 6 behind, 0 ahead; commit is on main. **Worktree is dirty — see §D4** |
| `work/2026-07-20-capture-photo-lifecycle-implementation-001` | `531013dd8c1a05e2443becd881a226755f27ca14` | equals `origin/main`. **Worktree is dirty with active work — see §D3** |

**Recommended disposition.** Safe-to-delete **once the associated worktree is
resolved**, not before. Deleting a branch does not delete the worktree's
uncommitted files, but it removes the only convenient handle on them.

### C3. Never merged, unique content — **PRESERVE**

#### `work/2026-07-15-interview-concept1`

| Field | Value |
|---|---|
| Tip SHA | `b4046cd184a08a14409b1b2ee36794ee04f07940` |
| Ahead / behind `origin/main` | 2 ahead, 77 behind |
| Scope | **local only** — not on `origin`, not covered by any existing archive tag |

**This branch is not listed in Task 7 of the next-task board.** It surfaced
during this inventory.

**Contains.** Two commits (`436b0ea` "Interview Workspace Concept 1: focused
coaching loop behind a flag", `b4046cd` "Interview Studio: make Concept 1 the
default page") and seven files. Five are `ABSENT_FROM_MAIN`:
`static/css/interview-concept1.css`, `static/js/interview-concept1.js`,
`templates/interview_concept1.html`, `templates/interview_me.html`, and
`tests/test_interview_concept1.py`. `app.py` and
`templates/partials/interview_question_bank.html` also differ.

**Already on main?** No. Zero of the seven files match. Reachability was checked
against **all fourteen existing archive tags** — `b4046cd` is reachable from
none of them.

**Would anything be lost?** Yes, permanently and with no remote copy. This is a
retired Interview Studio design concept that the released 5A/5C Studio replaced,
so it has no forward product value — but it is unrecoverable design history that
currently survives on exactly one disk.

**Recommended disposition.** **Preserve via archive tag, pushed to `origin`,
before any consideration of deletion.**

```bash
git tag -a archive/2026-07-20/interview-concept1 b4046cd184a08a14409b1b2ee36794ee04f07940 \
  -m "Retired Interview Workspace Concept 1 prototype; local-only, superseded by released 5A/5C Studio"
git push origin archive/2026-07-20/interview-concept1
git rev-parse archive/2026-07-20/interview-concept1^{commit}   # must print b4046cd1...
```

### C4. Live session branches — reserved-active, do not touch

| Local branch | Tip SHA | Owner |
|---|---|---|
| `work/2026-07-20-next-task-board` | `34156b3eaa97beda303a5cc1f1b870bb39f97a9d` | governance session, primary checkout |
| `work/2026-07-20-branch-disposition-record` | this branch | this session |
| `work/2026-07-20-capture-photo-dark-launch-001` | `531013dd8c1a05e2443becd881a226755f27ca14` | agent worktree `agent-a873985a470bd2f25` |
| `work/2026-07-20-interview-coaching-reliability-001` | `531013dd8c1a05e2443becd881a226755f27ca14` | agent worktree `agent-ad5168398146e4e87` |
| `work/2026-07-20-member-history-salvage-analysis` | `531013dd8c1a05e2443becd881a226755f27ca14` | agent worktree `agent-a1a0989c08c1e3803` |
| `docs/connected-system-return-value-authority` | `531013dd8c1a05e2443becd881a226755f27ca14` | appeared mid-inventory; Task 2 lane |
| `worktree-agent-a1a0989c08c1e3803` | `531013dd8c1a05e2443becd881a226755f27ca14` | harness-managed |
| `worktree-agent-a219a07d32deac35b` | `531013dd8c1a05e2443becd881a226755f27ca14` | harness-managed |
| `worktree-agent-a873985a470bd2f25` | `531013dd8c1a05e2443becd881a226755f27ca14` | harness-managed |
| `worktree-agent-ad5168398146e4e87` | `531013dd8c1a05e2443becd881a226755f27ca14` | harness-managed |
| `worktree-agent-afeaeb6782c7b90ba` | `531013dd8c1a05e2443becd881a226755f27ca14` | harness-managed |

**Recommended disposition.** Reserved-active. The five `worktree-agent-*`
branches are created and reclaimed by the Claude Code harness and are not
PeerSlate task branches; leave them to the harness. None of them is stale
housekeeping and none belongs in a cleanup pass.

---

## D. Worktrees

`git worktree list` reports **sixteen** worktrees. Five are harness-managed
agent worktrees under `/Users/petercarter/portfolio/.claude/worktrees/` and are
out of scope. The rest:

### D1. `/tmp/wt-dn` — orphaned, locked, directory missing — safe-to-prune

```
worktree /tmp/wt-dn
HEAD d624ae99e58e849058d08e035b4d35cb8b18c19b
detached
locked initializing
```

**Verified.** `/tmp/wt-dn` **does not exist on disk** (`ls` returns
"No such file or directory"). The record is an orphan left behind by a worktree
creation that never finished — its lock reason is literally `initializing`.

**Would anything be lost?** Nothing. Its detached HEAD `d624ae9` is the tip of
`work/2026-07-17-display-name`, whose content is byte-identical on `main`
(§C1). There is no working directory, so there are no uncommitted files.

**Recommended disposition.** Safe-to-delete. The removal is administrative and
touches no commits:

```bash
git worktree unlock /tmp/wt-dn
git worktree prune --dry-run     # confirm scope first
git worktree prune
```

No recovery reference is required because no object and no file is removed.
`git worktree prune --dry-run` is the scope confirmation step.

### D2. `/Users/petercarter/Documents/Website/peerslate-v13` — **PRESERVE (holds an untracked file that exists in no git ref)**

Branch `work/2026-07-16-adopt-product-bible-v13` at `d21df223b` (§B1). The
worktree is **dirty**: modified `AGENTS.md`, `CLAUDE.md`,
`docs/INITIATIVE_CHECKLIST.md`, `docs/PEERSLATE_SITE_RULES.md`,
`docs/PEERSLATE_V12_IMPLEMENTATION_INSTRUCTIONS.md`,
`docs/initiatives/PS-RULES-001/README.md`, `tests/test_site_rules.py`; deleted
Bible v1.1 and v1.2 `.docx`; plus two untracked files.

Both untracked files were checked:

- `PeerSlate_Company_and_Product_Bible_v1.3.docx` — **safe.** MD5
  `35bd2959a0dc029e372420d1e9d09011`, byte-identical to the copy tracked at
  `origin/main:PeerSlate_Company_and_Product_Bible_v1.3.docx`.
- `docs/PEERSLATE_V13_IMPLEMENTATION_INSTRUCTIONS.md` (15,303 bytes) —
  **at risk.** `git log --all -- <path>` returns **nothing**. This file exists
  in **no commit, no branch, and no tag** anywhere in the repository. `main`
  carries only the v1.2 instructions. Removing this worktree destroys it.

**Recommended disposition.** **Preserve until the untracked file is dealt with.**
Do not remove this worktree. Sequence, in order:

1. create and push the §B1 archive tag for `d21df223b`;
2. have Pete rule on `docs/PEERSLATE_V13_IMPLEMENTATION_INSTRUCTIONS.md` —
   commit it somewhere, archive it outside git, or explicitly discard it. Note
   that it is v1.3-era material, so it interacts with the Task 3 Bible v1.5.1
   authority question;
3. only then consider the worktree for removal.

**Recovery reference for the untracked file (required before any removal):**

```bash
cp "/Users/petercarter/Documents/Website/peerslate-v13/docs/PEERSLATE_V13_IMPLEMENTATION_INSTRUCTIONS.md" \
   "$HOME/peerslate-recovery-2026-07-20/"
shasum -a 256 "$HOME/peerslate-recovery-2026-07-20/PEERSLATE_V13_IMPLEMENTATION_INSTRUCTIONS.md"
```

A git-native alternative is a bundle of the branch plus a commit of the
untracked file on a throwaway ref — but the branch is DO-NOT-MERGE, so a plain
file copy plus a recorded hash is the lower-risk option.

### D3. `/Users/petercarter/Documents/Website/ps-capture-photo-lifecycle-implementation-001` — **RESERVED (active, uncommitted implementation)**

Branch `work/2026-07-20-capture-photo-lifecycle-implementation-001` at
`531013dd8` (= `origin/main`). The worktree contains **uncommitted
implementation work**: modified `.env.example`, `owner_routes.py`,
`tests/test_owner_photo_capture.py` and four package documents, plus untracked
`services/photo_lifecycle_access_service.py`,
`tests/test_photo_lifecycle_access.py`,
`docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/CLAUDE_HANDOFF.md`, and
`docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/IMPLEMENTATION_COMPLETION_REPORT.md`.

**This is live, unpushed, unique work.** It also appears to overlap the Task 1
Photo dark-launch lane running in agent worktree `agent-a873985a470bd2f25` on
`work/2026-07-20-capture-photo-dark-launch-001`. Two lanes on the same package
is a coordination question for the designated manager, flagged in §G.

**Recommended disposition.** **Reserved-active. Do not remove, do not clean, do
not delete the branch.** The owning writer must commit and push before this
worktree is even discussed.

### D4. `/Users/petercarter/Documents/Website/ps-interview-release-closeout` — preserve pending review

Branch `work/2026-07-20-interview-release-closeout` at `39002f513` (an ancestor
of `main`, 6 behind). The worktree is **dirty**: six modified tracked files
(all three governance pointers, `tests/test_governance_pointers.py`, and two
`PS-INTERVIEW-PUBLIC-GATE-001` documents — all six now differ from `main`), plus
untracked `docs/initiatives/PS-INTERVIEW-PUBLIC-GATE-001/17_RELEASE_CLOSEOUT.md`
(4,899 bytes) and an older draft of
`docs/initiatives/PS-HOME-INTERVIEW-PARITY-001/README.md`.

`17_RELEASE_CLOSEOUT.md` is **`ABSENT_FROM_MAIN`** — main's package stops at
`16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md`. It is uncommitted and in no ref.

**Recommended disposition.** Preserve pending a short review. The likely reading
is that this closeout was superseded by PRs 105–107, in which case the residue
is discardable — but that is a judgement for whoever owned the lane, not a
cleanup default. Copy `17_RELEASE_CLOSEOUT.md` to the recovery directory before
anything else happens to this worktree.

### D5. Merged-lane worktrees — remove after their branches clear §F

| Path | Branch | Worktree state |
|---|---|---|
| `/Users/petercarter/Documents/Website/ps-auth-001-display-name` | `work/2026-07-17-owner-settings` | clean |
| `/Users/petercarter/Documents/Website/ps-capture-photo-lifecycle-001` | `work/2026-07-20-capture-photo-lifecycle-001` | clean |
| `/Users/petercarter/Documents/Website/ps-home-frontend-manager` | `work/2026-07-20-home-frontend-manager` | clean |
| `/Users/petercarter/Documents/Website/ps-home-interview-parity-001` | `work/2026-07-20-home-interview-parity-closeout` | clean |
| `/Users/petercarter/Documents/Website/ps-home-interview-parity-manager` | `work/2026-07-20-home-interview-parity-manager` | untracked `Remote_ChatGPT_Context_Pack/` (16 MB) + `build_remote_chatgpt_context_pack.js` |
| `/Users/petercarter/Documents/Website/ps-interview-002c1-member-history` | `work/2026-07-17-member-history-completion` | **dirty — RESERVED, see §A6** |

The four clean worktrees are safe to remove with `git worktree remove <path>`
**after** their branches clear the §F gate and are archive-tagged.
`docs/AI_WORKFLOW.md` requires worktrees to be removed promptly once merged, so
these are overdue rather than risky.

`ps-home-interview-parity-manager` needs one decision first: neither
`build_remote_chatgpt_context_pack.js` nor `Remote_ChatGPT_Context_Pack/` exists
in any ref. The pack's `.docx` files are copies of governance documents already
tracked on `main`, so the pack itself is regenerable output — but the **build
script is not**. Copy the script to the recovery directory, or commit it, before
removing that worktree.

The `ps-interview-002c1-member-history` worktree is reserved and must not be
touched while the Task 4 salvage lane is open.

---

## E. Stashes

There is exactly **one** stash in the repository. (`git stash list` reports it
from every worktree because `refs/stash` lives in the common git directory; it
is one stash, not one per worktree.)

| Field | Value |
|---|---|
| Ref | `stash@{0}` |
| Stash commit | `c3de3d507210090a0f9695ac4c84aa78f74f8f4c` |
| Message | `On main: scrapped-gray-navy-dark-2026-07-17` |
| Created | 2026-07-17 15:35:11 −0400 |
| Base commit | `75ff29af80be856767f5687f5117144f040b2f08` (PR 53) |
| Scope | 11 stylesheets, +381/−336 |

**Contains.** `editorial-glass.css`, `homepage-scenes.css`,
`interview-studio.css`, `living-resume-v2.css`, `people-interests.css`,
`resume2.css`, `skills-cinematic.css`, `sky-glass.css`, `slate-board.css`,
`story-acts.css`, `style.css`.

**Already on main?** No — and it should not be. The name records it as
**scrapped**. It is a rejected gray-navy dark-theme experiment from
2026-07-17, superseded the same week by the approved PS-THEME-002 Layered Ink
dark theme and the Deep Navy Gold light system (PS-BRAND-NAV-002, PR 58).

**Would anything be lost?** Yes — the stash is the only copy of that
exploration. Its value is historical, not forward-looking.

**Recommended disposition.** Archive-tag, then drop. A stash is a real commit
object, so tagging it preserves it exactly.

```bash
git tag -a archive/2026-07-20/scrapped-gray-navy-dark c3de3d507210090a0f9695ac4c84aa78f74f8f4c \
  -m "Scrapped gray-navy dark theme exploration, 11 stylesheets, stashed 2026-07-17; superseded by PS-THEME-002 + Deep Navy Gold"
git push origin archive/2026-07-20/scrapped-gray-navy-dark
git show --stat archive/2026-07-20/scrapped-gray-navy-dark   # must show the 11 stylesheets
```

Only after the tag is pushed **and** the `show --stat` output verified may
`git stash drop stash@{0}` be considered. Note that dropping a stash is
explicitly listed in `docs/AI_WORKFLOW.md` as a destructive operation requiring
a recovery reference. Precedent exists — `archive/2026-07-14/claude-notes-stash`
and `archive/2026-07-14/vscode-tutorial-stash` were preserved the same way.

---

## F. The correct verified-squash-merge cleanup procedure

From `docs/AI_WORKFLOW.md` §"Finishing a task". This is the **only** routine
exception to the rule against `git branch -D`, and it exists precisely because
Azure's squash merge makes `git branch -d` refuse a branch whose work is fully
live.

Normal path first:

```bash
git switch main
git fetch origin --prune
git pull --ff-only
git branch -d work/YYYY-MM-DD-task-name
git fetch origin --prune
```

If `git branch -d` refuses, **do not reach for `-D`.** Gather evidence:

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git rev-parse work/YYYY-MM-DD-task-name
az repos pr show --id <PR_ID> \
  --query '{status:status,mergeStatus:mergeStatus,sourceCommit:lastMergeSourceCommit.commitId,mergeCommit:lastMergeCommit.commitId}' \
  --output json
git ls-remote --heads origin refs/heads/work/YYYY-MM-DD-task-name
```

All five conditions must hold:

1. PR status is `completed`;
2. PR merge status is `succeeded`;
3. the PR's `sourceCommit` **exactly** matches `git rev-parse` for the local
   branch tip;
4. the PR records a non-empty `mergeCommit`;
5. `ls-remote` returns nothing, because Azure deleted the remote branch on merge.

Only then:

```bash
git branch -D work/YYYY-MM-DD-task-name
```

If **any** condition fails, preserve the branch and investigate. **Do not
substitute a comparison against current `main`** — later merges legitimately
change `main` after a task PR completes, so "it looks like it's on main" is not
the test. The content comparisons in §A and §C of this record are diagnostic
evidence for writing dispositions; they are **not** a substitute for the Azure
PR record required by conditions 1–5.

Every branch in §C1 is a candidate for this procedure. None of them has been
run through it yet: this session did not query Azure PR status, so condition 3
in particular is unverified for all seven.

---

## G. Findings that need an owner decision

1. **A failed gate record exists only on one branch.**
   `work/2026-07-19-interview-gate-24-review` holds the only record that
   Interview Gate 2.4 was **failed**, plus the only copy of the reviewed 4.4 MB
   design-authority archive and its SHA-256. `main` carries only the later
   **Conditional** review from a differently-named branch. Decide whether the
   Fail record merges to `main` or is archived with a `DOCUMENT_CONTROL.md`
   note. Until then the branch stays.

2. **A file exists that is in no git ref at all.**
   `docs/PEERSLATE_V13_IMPLEMENTATION_INSTRUCTIONS.md` (15,303 bytes) lives only
   as an untracked file in the `peerslate-v13` worktree. It would be destroyed
   silently by a routine worktree cleanup. Related to the Task 3 Bible v1.5.1
   authority question.

3. **An unlisted local-only branch holds unique retired design work.**
   `work/2026-07-15-interview-concept1` is not in the Task 7 inventory, is not
   on `origin`, is not covered by any of the fourteen archive tags, and none of
   its seven files exists on `main`. One disk, no copy.

4. **Two lanes appear to be working the same Photo package.**
   `~/Documents/Website/ps-capture-photo-lifecycle-implementation-001` holds
   uncommitted Photo lifecycle implementation (including a new
   `services/photo_lifecycle_access_service.py`), while agent worktree
   `agent-a873985a470bd2f25` holds
   `work/2026-07-20-capture-photo-dark-launch-001` for what the next-task board
   describes as the same Task 1 slice. `docs/AI_WORKFLOW.md` allows exactly one
   active writer per package. The manager should reconcile these before either
   lane pushes.

5. **Uncommitted governance work sits in the release-closeout worktree.**
   `17_RELEASE_CLOSEOUT.md` and six modified tracked files that now diverge from
   `main`. Probably superseded by PRs 105–107, but that needs confirming rather
   than assuming.

6. **The GitHub mirror is far behind and this record does not change that.**
   `github/main` is at `d5dd7bd`. Archive tags pushed to `origin` will not reach
   the mirror until the Task 6 owner decision is made. Every recovery reference
   in this document therefore depends on `origin` alone.

---

## H. Recommended execution order, once approved

Nothing below may run without Pete's explicit approval of the specific item.

1. **Create and push all archive tags first.** In particular
   `archive/2026-07-20/adopt-product-bible-v13` and
   `archive/2026-07-20/interview-concept1`, which currently protect local-only
   history. Verify each with `git rev-parse <tag>^{commit}` and
   `git ls-remote --tags origin`.
2. **Copy the at-risk untracked files** to a recovery directory and record their
   SHA-256 hashes: the v1.3 implementation instructions (§D2),
   `17_RELEASE_CLOSEOUT.md` (§D4), and
   `build_remote_chatgpt_context_pack.js` (§D5).
3. **Prune the orphaned `/tmp/wt-dn` record** (§D1) — the one genuinely
   consequence-free item.
4. **Run the §F verified-squash-merge gate** against each §C1 branch,
   individually, with the real Azure PR IDs.
5. **Remove the four clean merged worktrees** (§D5), then delete their branches.
6. **Archive-tag and then delete the three superseded remote branches** — A1,
   A4, A5 — and optionally A2.
7. **Archive-tag the stash, verify with `git show --stat`, then drop it** (§E).
8. **Leave alone**: A3, A6, A7, B1, C3, C4, D2, D3, D4, and the
   `ps-interview-002c1-member-history` worktree.

---

## I. Disposition summary

| Item | Type | Disposition |
|---|---|---|
| `work/2026-07-18-voice-001` | remote branch | archive-tag-then-delete |
| `work/2026-07-19-control-room-deploy-evidence` | remote branch | safe-to-delete (tag optional) |
| `work/2026-07-19-interview-gate-24-review` | remote branch | **preserve — unique failed-gate record** |
| `work/2026-07-19-owner-home-viewer-architecture` | remote branch | archive-tag-then-delete |
| `work/2026-07-19-voice-visual-parity-001` | remote branch | archive-tag-then-delete |
| `work/2026-07-17-member-history-completion` | remote + local | **reserved-active** (Task 4 salvage lane) |
| `work/2026-07-20-next-task-board` | remote + local | reserved-active |
| `work/2026-07-16-adopt-product-bible-v13` | local only | **preserve, DO-NOT-MERGE**, tag now |
| `work/2026-07-15-interview-concept1` | local only | **preserve — unique, unlisted, untagged** |
| 7 squash-merged local branches (§C1) | local | archive-tag-then-delete after §F gate |
| 3 ancestor-of-main local branches (§C2) | local | safe-to-delete after worktrees resolve |
| 6 live session branches + 5 `worktree-agent-*` (§C4) | local | reserved-active |
| `/tmp/wt-dn` | worktree record | safe-to-delete (prune) |
| `peerslate-v13` worktree | worktree | **preserve — holds a file in no git ref** |
| `ps-capture-photo-lifecycle-implementation-001` worktree | worktree | **reserved-active — uncommitted work** |
| `ps-interview-release-closeout` worktree | worktree | preserve pending review |
| `ps-interview-002c1-member-history` worktree | worktree | **reserved-active** |
| 4 clean merged worktrees (§D5) | worktree | remove after §F gate |
| `ps-home-interview-parity-manager` worktree | worktree | remove after saving build script |
| `stash@{0}` gray-navy dark | stash | archive-tag-then-drop |

**Approval required per row. This document deletes nothing.**
