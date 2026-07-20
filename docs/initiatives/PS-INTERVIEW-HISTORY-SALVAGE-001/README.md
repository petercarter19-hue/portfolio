# PS-INTERVIEW-HISTORY-SALVAGE-001 — Private Interview Story salvage analysis

**This is a written proposal. It is not an implementation, and no writer is
assigned.** Nothing in this package has been built, migrated, merged,
deployed, enabled, or made available to any member. No schema exists. No route
exists. No production behavior changed. Every statement about the released
Interview Studio in this package describes code already on `origin/main`, not
anything proposed here.

## Package identity

| Field | Value |
|---|---|
| Package ID | `PS-INTERVIEW-HISTORY-SALVAGE-001` |
| Type | Salvage analysis and integration proposal — documentation only |
| Status | **Proposal. Not activated. No manager. No implementation writer.** |
| Analysis branch | `work/2026-07-20-member-history-salvage-analysis` |
| Base | `origin/main` at `531013dd8c1a05e2443becd881a226755f27ca14` |
| Subject branch (read-only) | `origin/work/2026-07-17-member-history-completion` at `b439afb2c94b527f68d6d31ba7a9e34e3f49387d` |
| Task board entry | `docs/governance/NEXT_TASK_BOARD.md` Task 4 — Member-history salvage |
| Roadmap relationship | Would extend the released public Interview Studio with an authenticated private layer; touches Phase 10/11 boundaries |

## Why this package exists

`origin/work/2026-07-17-member-history-completion` is a single commit
(`b439afb`, "feat: add confirmed interview story grounding") that is 54 commits
behind and 1 ahead of `main`. It contains a complete, coherent, private
member-history design: a SQL migration with six tables and fourteen stored
procedures, an owner-isolated service layer, an authenticated JSON API, a
deterministic sufficiency classifier, prompt-injection containment for member
data, and a grounded-answer audit trail. Its SQL migration was never applied to
any database.

It also contains a UI layer — template, CSS, JavaScript, and Studio tests —
built against the *pre-release* Interview Studio. The accepted 5A-light/5C-dark
Studio has since replaced all four of those files through Azure PR 101 at
`39002f5130a1766d2090007c16582e0dbe07226c` (pipeline 149, live and verified).

## Hard constraint carried into this package

**The subject branch must not be merged, rebased, cherry-picked, or deleted.**
Merging it would regress the live Studio. This package treats the branch as a
read-only design artifact and a source of concepts, never as a source of
mergeable code. Any future implementation writes fresh code against the
released Studio and re-derives the keepers deliberately.

## What is in this package

| File | Contents |
|---|---|
| `README.md` | This file — identity, verdict summary, boundaries, next gate |
| `01_BRANCH_INVENTORY.md` | Exact inventory of what the old branch contains, file by file |
| `02_KEEP_DISCARD_VERDICTS.md` | Per-concept keep / discard / obsolete verdict with reasoning |
| `03_INTEGRATION_AGAINST_RELEASED_STUDIO.md` | How the keepers would attach to the *released* Studio, not the replaced one |
| `04_SCHEMA_AND_MIGRATION_PLAN.md` | Schema and migration work that would actually be required today |
| `05_AUTHORIZATION_AND_ISOLATION.md` | Authentication, authorization, and two-owner isolation implications |
| `06_OPEN_QUESTIONS_FOR_PETE.md` | Decisions that must be made before any writer is assigned |

## Verdict summary

Eleven backend concepts are worth keeping. Six things must be discarded
outright. Four are obsoleted by work released since. Three are conditional on
an architecture decision only Pete can make. Full reasoning is in
`02_KEEP_DISCARD_VERDICTS.md`.

**Keep — the durable value**

1. Independent `allowed_for_ai_grounding` permission, separate from confirmation.
2. Immutable confirmed story versions with an insert-only trigger.
3. Fail-closed grounding resolver: confirmed + permitted + private, exact-set match.
4. Grounded-answer audit pinning the exact confirmed story version.
5. Deterministic, non-AI sufficiency classification with explicit reason codes.
6. Prompt-injection containment — member facts as quoted data, never instructions.
7. Explicit fail-closed source mode; no silent default, no model inference.
8. Confirmed-fact versus AI-proposed-wording boundary surfaced to the member.
9. Owner-key binding inside the signed follow-up context token.
10. Stored-procedure-only, server-resolved `user_key` access with composite tenant FKs.
11. Source-mode change audit.

**Discard — do not carry forward**

1. The entire UI layer: `templates/interview_studio.html`, `static/css/interview-studio.css`, `static/js/interview-studio.js`, `tests/test_interview_studio.py` diffs.
2. The grounding-label copy change ("confirmed, permitted history") — it contradicts a deliberate released truth marker.
3. Registration in the mandatory `MIGRATION_FILENAMES` tuple and the core foundation verifier.
4. The `PS-INTERVIEW-001` migration ID.
5. `record_answer` pinning the *model-returned* evidence IDs rather than the server-resolved source set — this is a defect, not a design.
6. Any second dictation/transcription path inside the story dialog.

**Obsoleted by released work**

1. Browser-`SpeechRecognition` story dictation — private Voice Capture (PS-VOICE-001) is the released voice architecture.
2. The old Studio's three-tab structure and pre-orientation DOM assumptions.
3. The mandatory-migration registration convention — superseded by `proposed/` plus `APPROVED_OPTIONAL_MIGRATIONS`.
4. The audit document's claim that the third tab is "Video Me" — the released Studio ships `Video Practice` plus an `orientation` panel that did not exist then.

**Conditional on an architecture decision**

1. Whether `interview_stories` should exist as a parallel private aggregate at
   all, or whether an interview story is a *projection over canonical Moments*
   (PS-MOMENT-001) reached by a Placement-style reference (PS-PLACEMENT-001).
2. Whether story confirmation may write `content_approval_events` with an
   `approved` action and flip `slate_entities.approval_status`.
3. Whether a fully public, unauthenticated route may host an authenticated
   private-history mode at all, or whether that belongs under `/app`.

## Independent defect found on `main` while inspecting it

This is not part of the salvage, but it was found by reading the released code
and belongs on the record.

`app.py::validate_interview_model_answer` raises
`'model answer has no approved evidence references'` whenever `evidenceIds` is
empty. The released `best_practice` grounding mode calls it with an empty
evidence map and instructs the model to return `"evidenceIds":[]`. As written,
the illustrative path appears unable to validate: an empty list raises, and a
non-empty list fails the unauthorized-evidence check against `{}`. The route's
handler converts that to a `502`.

The old branch fixed exactly this with an `allow_illustrative=True` parameter
and a focused test. That fix is small, self-contained, and independent of every
schema question in this package. It may be worth its own tiny lane rather than
waiting behind the private-history decision. See
`02_KEEP_DISCARD_VERDICTS.md` §K-12. **This was read from source only. It has
not been reproduced against a running request, and it has not been fixed here.**

## Explicit boundaries of this package

- No service, route, template, migration, script, or test was changed.
- No branch was merged, rebased, cherry-picked, or deleted.
- No pull request was opened. Nothing was pushed to `main`.
- Nothing described here is live, enabled, scheduled, or authorized.
- No migration ID is reserved by this document. `04_SCHEMA_AND_MIGRATION_PLAN.md`
  proposes an ID; reserving it is a later decision.
- This package does not modify `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`,
  `ACTIVE_INITIATIVES.md`, or `DECISIONS.md`, and makes no claim to be an
  active initiative.

## Next gate

Pete answers the decisions in `06_OPEN_QUESTIONS_FOR_PETE.md` — principally
whether an interview story is its own aggregate or a Moment projection, and
whether private history belongs on the public Studio route or under `/app`.
Only after those answers does a designated manager decide whether to activate a
package, name a writer, and reserve files. Until then this remains analysis.
