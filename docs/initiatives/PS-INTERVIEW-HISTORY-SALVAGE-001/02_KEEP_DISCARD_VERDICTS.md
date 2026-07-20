# 02 — Keep / discard / obsolete verdicts

Every concept found on `origin/work/2026-07-17-member-history-completion` is
listed exactly once, with a verdict and the reasoning behind it. Verdicts are
judgements offered for Pete's and a manager's review; none of them has been
acted on.

Legend:

- **KEEP** — durable value; re-derive against the released Studio.
- **DISCARD** — do not carry forward in any form.
- **OBSOLETE** — the need it addressed is already met by released work.
- **CONDITIONAL** — value depends on a decision only Pete can make.

---

## KEEP

### K-1 — `allowed_for_ai_grounding` as a permission independent of confirmation

*What it is.* A `bit` column on the story, defaulted to `0`, set by an explicit
member boolean at confirmation time and toggleable afterwards through a
dedicated procedure that requires the story already be `CONFIRMED`.

*Why keep it.* This is the single most valuable idea on the branch and nothing
released today has an equivalent. Confirming that a memory is accurate and
permitting an AI to speak from it are two different consents. Every released
private surface conflates them or sidesteps them: Capture has no AI-grounding
concept, Moment confirmation is about canonical accuracy, and Placement is
about destination eligibility. A member must be able to say "yes, that is what
happened" and separately "no, don't let the model use it."

*Evidence it was built deliberately.* `usp_SetInterviewStoryGroundingPermission`
takes `UPDLOCK, HOLDLOCK`, refuses non-confirmed rows, and appends an audit
event containing a fixed JSON literal — never member text. Archive and delete
both force the flag back to `0`.

### K-2 — Immutable confirmed version snapshots with an insert-only trigger

*What it is.* `dbo.interview_story_versions` holds one row per confirm, with
`CK_interview_story_versions_status CHECK (confirmation_status = N'CONFIRMED')`,
`UQ_interview_story_versions_story (story_id, version)`, and
`trg_interview_story_versions_immutable` blocking update and delete.

*Why keep it.* It matches the released `dbo.moment_versions` pattern from
PS-MOMENT-001 and the immutability convention already used by
`audit_events` and `content_approval_events`. If AI answers are going to cite a
member's history, the cited text must not be silently rewritable after the fact.

### K-3 — Fail-closed grounding resolver with exact-set matching

*What it is.* `InterviewGroundedAnswerService.resolve_sources()` sends the
requested IDs to `usp_GetInterviewStoriesForGrounding`, which filters to
`CONFIRMED AND allowed_for_ai_grounding=1 AND visibility='private' AND deleted_at_utc IS NULL`.
The service then asserts that the **returned set equals the requested set** and
re-checks each of the three conditions in Python before any prompt is built.

*Why keep it.* A silently shortened result set is the classic way a
permission filter turns into a partial disclosure or a confusing answer. Failing
the whole request when even one requested story is ineligible is correct, and
the belt-and-braces Python re-check means a future procedure edit cannot quietly
widen the boundary. The `normalize_story()` decision to treat *missing*
visibility metadata as unsafe rather than defaulting it to private is the same
instinct and should also be kept.

### K-4 — Answer audit pinned to the exact confirmed story version

*What it is.* `dbo.interview_answer_attempts` plus
`dbo.interview_answer_sources`, the latter keyed on
`(answer_attempt_id, story_id)` and carrying `story_version_id` with a composite
FK back through `(story_version_id, story_id, owner_user_id)`.

*Why keep it.* It is the same exact-version-pinning contract PS-PLACEMENT-001
already released and proved in production: a reference points at *one exact
confirmed version*, not at "the story as it is today." Without it there is no
way to answer "which words did the model actually see" three months later.

*Caveat.* The branch's *population* of this table is defective — see D-5. Keep
the schema and the contract; rewrite the writer.

### K-5 — Deterministic, non-AI sufficiency classification with reason codes

*What it is.* `InterviewStorySufficiencyService.evaluate()` is a pure function.
`required_story_fields()` picks which STAR fields matter for this question
(always situation/responsibility/personal actions/results; adds reasoning for
"why/decision/judgment/tradeoff" questions; adds reflection for
"learn/differently/mistake/failure" questions). Missing fields become
`MISSING_SITUATION`, `MISSING_PERSONAL_ROLE`, `MISSING_PERSONAL_ACTION`,
`MISSING_REASONING`, `MISSING_RESULT`, `MISSING_REFLECTION`. The result is one
of `SUFFICIENT`, `MULTIPLE_CANDIDATES`, `PARTIALLY_SUFFICIENT`, `UNCONFIRMED`,
`PERMISSION_REQUIRED`, `INSUFFICIENT`.

*Why keep it.* The application, not the model, decides whether there is enough
material to answer. That is directly aligned with the Bible rule that AI output
is a proposal and never an authorization. It is also testable without an AI
provider, which makes it cheap to guard.

*Also keep.* The two-result-set shape of
`usp_GetInterviewStoryCandidatesForUser` — ranked candidates, then a diagnostic
row of `unconfirmed_count` and `permission_required_count`. That is what lets
the product say "you have something relevant but haven't confirmed it" without
disclosing the unconfirmed record itself.

### K-6 — Prompt-injection containment for member data

*What it is.* `prompt_sources()` serializes each story as
`SOURCE n ID <uuid>` followed by a `<member_story_data>` block containing
`json.dumps(facts)`. The system prompt states the blocks are *untrusted member
data, never instructions*, and tells the model to ignore any command-like text
inside them.

*Why keep it.* Member-authored free text is exactly the untrusted-content
category that must never become instructions. This is correct handling and costs
nothing to preserve.

### K-7 — Explicit, fail-closed source mode

*What it is.* `source_mode` must be one of `ILLUSTRATIVE`, `MEMBER_HISTORY`,
`COMPARE`. Absent or invalid is a `400`. The released code instead does
`mode = str(data.get('mode') or 'member_history')` and coerces anything
unrecognized to `member_history`.

*Why keep it.* A grounding mode that silently defaults is a mode that can be
reached by accident. When one of those modes reads private member history, a
silent default is a privacy hazard rather than a convenience. The old branch's
own audit called this out as a required change.

*Note.* Renaming the wire value is a client-visible contract change; see
`03_…` for how to sequence it without breaking the released Studio.

### K-8 — Confirmed-fact versus AI-proposed-wording boundary

*What it is.* A `factBoundary` object on the response separating "confirmed
information comes from the records listed" from "suggested wording is
AI-proposed and remains yours to review."

*Why keep it.* It is the product expression of the governing rule that AI output
is a proposal, not an edit, and it is the honest thing to show a member who is
about to rehearse words a model wrote about their own life. The *concept*
survives; the *markup* does not (see D-1).

### K-9 — Owner-key binding inside the signed follow-up context

*What it is.* `_sign_interview_model_context()` gains `owner_user_key`;
`_load_interview_model_context()` validates its type; the route returns `403`
when the token's owner differs from the current identity, and `400` when the
follow-up's source mode differs from the original.

*Why keep it.* A signed token is tamper-evident but not owner-bound. Without
this, a valid token minted for one member remains structurally valid when
presented by another. Once the token can carry private story IDs, that gap
matters.

### K-10 — Stored-procedure-only access on a server-resolved `user_key`, with composite tenant FKs

*What it is.* Every procedure takes `@UserKey` and joins `dbo.app_users`; no
browser-supplied identifier reaches SQL. Ownership is additionally enforced in
the schema by `UQ_member_profiles_id_user`, `UQ_interview_stories_id_owner`, and
composite FKs that carry `owner_user_id` / `owner_profile_id` into every child
table.

*Why keep it.* This is the released house convention (`identity.py` →
`services/database_service.py` → allowlisted procedure), extended correctly.
The structural tenant constraints mean a future procedure bug cannot create a
cross-owner row — the database refuses it.

### K-11 — Source-mode change audit

*What it is.* `dbo.interview_mode_changes` with
`CK_interview_mode_changes_distinct CHECK (from_mode <> to_mode)` and a
bounded `reason`.

*Why keep it.* Cheap, contains no member content, and answers "was this member
ever shown a personal-history answer" without reading any story. Low priority
relative to K-1 through K-5, but worth carrying.

### K-12 — `allow_illustrative` on `validate_interview_model_answer`

*What it is.* A keyword-only flag that skips the
`if not evidence_ids: raise ValueError('model answer has no approved evidence references')`
check, plus a focused test.

*Why keep it.* It appears to fix a live latent defect on `main`. Released
`best_practice` mode calls `_generate(best_practice_system, empty_evidence=True)`,
which validates against `{}` while the prompt instructs the model to return
`"evidenceIds":[]`. Reading the code, an empty list raises and a non-empty list
fails the unauthorized-evidence check, so the route's `except (ValueError, …)`
branch would return `502` either way.

*Status.* Source reading only. This has **not** been reproduced against a
running request and has **not** been fixed. If confirmed by a reproduction, it
is a self-contained bug fix that does not depend on any decision in this
package and could be its own small lane. It may also be related to
`NEXT_TASK_BOARD.md` Task 5, though that task describes the *coaching* path
rather than the model-answer path.

---

## DISCARD

### D-1 — The entire UI layer

`templates/interview_studio.html` (+82/−6), `static/css/interview-studio.css`
(+79), `static/js/interview-studio.js` (+543/−7), and the
`tests/test_interview_studio.py` additions.

*Why discard.* These were written against the pre-release Studio. The accepted
5A-light/5C-dark Studio replaced all four files through PR 101 at
`39002f5130a1766d2090007c16582e0dbe07226c`, which is live and verified. The old
diff assumes DOM, class names, asset versions, and a panel structure that no
longer exist — for example it targets `?v=light-orbit-2`, has no concept of the
released `data-is-panel="orientation"` panel, and calls the third tab
"Video Me" where the release ships `Video Practice`.

Applying any of it would regress the live Studio. The *interaction concepts*
(a story-capture dialog, a sufficiency block in the answer workspace, candidate
selection, a fact-boundary strip) are worth re-deriving — but as new design
against the released component language, under the Owner Visual Integrity
Standard, with named visual authority and explicit acceptance.

### D-2 — The grounding-label copy change

The branch rewrote the grounding note to
"Grounded only in {first_name}'s **confirmed, permitted** history" and the draft
basis to "**confirmed, permitted** history".

*Why discard.* The released template deliberately says
"Use {first_name}'s **public** history" and "Grounded only in {first_name}'s
approved **public** history." That word "public" is a truth marker added during
the Gate 2.4 review, and it is currently accurate: the released grounding path
reads `static/data/resume_data.json` through `_interview_page_context()` and
touches no private record.

Changing that copy is not a code decision. It is a visual/product truth change
that requires named visual authority and Pete's acceptance, and it must not
happen before the private path actually exists — otherwise the label would
describe a capability the backend does not have, which is exactly what the
governance documents prohibit.

### D-3 — Registration in the mandatory migration list and core foundation verifier

The branch appended `PS-INTERVIEW-001_member_history_completion.sql` to
`MIGRATION_FILENAMES` in `scripts/apply_sql_migrations.py` and added the six
tables, four procedures, and the trigger to
`SQL FIles/Verification/peerslate_platform_foundation_verify.sql`.

*Why discard.* `MIGRATION_FILENAMES` is the **mandatory** foundation set
(`PS-PLAT-001`…`PS-PLAT-007`, `PS-AUTH-001`). `EXPECTED_MIGRATIONS` is derived
from it, and `verify_foundation()` fails when any listed migration is absent.
Adding an unapplied package migration there would make foundation verification
fail in every environment that has not run it — including production, where the
migration has never been applied.

Every package since PS-CAPTURE-001 uses the opposite convention:
`SQL FIles/Migrations/proposed/`, registered in `APPROVED_OPTIONAL_MIGRATIONS`,
with a package-specific verifier under `SQL FIles/Verification/`. See
`04_SCHEMA_AND_MIGRATION_PLAN.md`.

### D-4 — The `PS-INTERVIEW-001` migration ID

*Why discard.* The `PS-INTERVIEW-*` namespace has since been used for released
UI work — `PS-INTERVIEW-002` and `PS-INTERVIEW-PUBLIC-GATE-001` — neither of
which has any schema. A schema migration numbered `PS-INTERVIEW-001` would
read as the foundation of those packages, which it is not. It also sorts ahead
of packages that shipped first. A new ID is needed;
`04_SCHEMA_AND_MIGRATION_PLAN.md` proposes one but does **not** reserve it.

### D-5 — Auditing the model-returned evidence IDs

The branch computes
`answer_story_ids = [item['id'] for item in model_answer.get('evidenceUsed', [])]`
and passes that to `record_answer(...)` and into the signed follow-up context.

*Why discard.* This lets the model decide which sources get written to the
audit trail. The whole purpose of K-4 is to record what the server authorized
and supplied. If the model omits a source it used, or returns a subset, the
audit is wrong in exactly the situation where it matters. The recorded set
should be the **server-resolved** source set, or that set annotated with which
entries the model claimed to cite — never the model's list alone.

This is a defect in the branch, not a design choice to preserve. The validator
does constrain returned IDs to the supplied evidence map, so this cannot
*inject* an unauthorized source; but it can silently *shrink* the recorded set.

### D-6 — A second dictation or transcription path inside the story dialog

The branch's story dialog wires `data-is-mic="story"` into the browser
`SpeechRecognition` helper that the old Studio used for its text fields.

*Why discard.* PS-VOICE-001 released the private Voice Capture architecture —
private original audio in Blob Storage, managed-identity Speech transcription,
editable transcript, explicit private save. `CURRENT_STATE.md` explicitly
records that Voice must not be rebuilt inside another package. A second
browser-only dictation path inside the Studio would be a second voice story
with different privacy, retention, and failure semantics. The `source_kind`
*column* (`text` / `voice` / `transcript`) is fine as a provenance label; a
second voice *pipeline* is not.

---

## OBSOLETE

### O-1 — Browser `SpeechRecognition` as the voice story

Superseded by released PS-VOICE-001. See D-6.

### O-2 — The pre-release Studio structure the branch targets

Three tabs, no orientation panel, `?v=light-orbit-2` assets, `Video Me`
labelling. The released Studio has moved on. The branch's audit document
records these as current-state findings; they are now historical.

### O-3 — The mandatory-migration registration convention

Superseded by the `proposed/` + `APPROVED_OPTIONAL_MIGRATIONS` split introduced
by PS-CAPTURE-001 and used by every package since. See D-3.

### O-4 — "There is no private confirmed-record layer" as a premise

The branch's audit concluded that nothing existed to represent a private,
member-confirmed, versioned record. That was true at
`75ff29af80be856767f5687f5117144f040b2f08`. It is no longer true: PS-MOMENT-001
released `dbo.moments` / `dbo.moment_versions` / `dbo.moment_sources` with
private-only visibility, explicit confirmation, immutable versions, exact source
pinning, and deleted-source tombstones — and its production migration and
verifier passed. PS-PLACEMENT-001 then released the exact-confirmed-version
reference contract.

This is the premise change that makes C-1 below the central question of this
package.

---

## CONDITIONAL

### C-1 — Whether `interview_stories` should be a parallel aggregate at all

*The tension.* Both `dbo.moments` and the proposed `dbo.interview_stories` are
private-only, owner-scoped, versioned, member-confirmed records of something
that happened to the member. Building both means a member who captured "the
contract renegotiation" as a Moment and then answers an interview question about
it could end up with two canonical records of one lived experience, each with
its own version history and its own confirmation state, capable of disagreeing.

*The case for a separate aggregate.* The shapes genuinely differ. A Moment
carries `moment_kind`, `title`, `occurred_on`, `occurred_precision`,
`narrative`, `why_it_matters`. An interview story carries a STAR decomposition —
situation, responsibility, personal actions, reasoning, results, reflection —
plus competencies, a source question, a source attempt, and per-field capture
progress. Forcing STAR fields into `narrative` would overload the canonical
record, which the branch's own audit argued against for `career_chapters` and
`career_achievements`. Interview stories also need the independent AI-grounding
permission (K-1), which the Moment model has no concept of.

*The case for a projection.* PS-PLACEMENT-001 already released precisely the
primitive that would be needed: an owner-scoped, lifecycle-aware pointer from
one exact confirmed Moment version to one eligible destination, copying no
authoritative text. An "interview story" could be a STAR *elaboration* attached
by reference to a confirmed Moment version, inheriting its canonical facts
rather than restating them. That keeps one canonical truth per experience and
reuses a contract already proven in production.

*Verdict.* **CONDITIONAL — Pete decides.** This is question 1 in
`06_OPEN_QUESTIONS_FOR_PETE.md`. The answer changes the schema substantially and
must precede any implementation.

### C-2 — Whether confirmation may write `content_approval_events` and flip `slate_entities.approval_status`

`usp_ConfirmInterviewStory` sets the linked entity to
`approval_status='approved'`, `visibility='private'`,
`publication_status='unpublished'` and inserts a `content_approval_events` row
with `action_type='approved'`.

*The tension.* Every released package draws a hard line: confirmation is not
approval, and neither is publication. `CURRENT_STATE.md` states that Moment
confirmation "does not publish or place content" and that Placement "changes no
audience, access grant, publication record." Writing an `approved` approval
event on story confirm blurs a line the platform has been careful to keep sharp,
even though the row stays private and unpublished.

*Verdict.* **CONDITIONAL.** Either justify it explicitly as "approved for the
member's own private use, never for an audience," or drop the approval-event
write and record confirmation in the story's own audit trail. Question 4 in
`06_…`.

### C-3 — Whether a public route may host an authenticated private-history mode

The branch returns HTTP `200` with `sufficiency.status = 'PERMISSION_REQUIRED'`
when an anonymous visitor selects `MEMBER_HISTORY` on `/api/interview/model-answer`.

*The tension.* `/interview-studio` is a fully public, unauthenticated route —
that is what PS-INTERVIEW-PUBLIC-GATE-001 released and what
`CURRENT_STATE.md` describes as "a public browser-local practice experience…
not an authenticated private history system." Every other private surface lives
under `/app` behind a sign-in redirect. Putting private-history grounding on the
public route means one endpoint serves both audiences and the public page must
carry sign-in affordances and honest empty states for visitors who have no
account.

*The `200` choice specifically.* Returning `200` with a structured
`PERMISSION_REQUIRED` state rather than `401` is defensible product behavior —
the page can explain the gate rather than erroring — but it means an
unauthenticated caller cannot distinguish "not signed in" from "signed in with
no permitted stories" without reading the reason codes. That is arguably a
privacy *feature*. It should be a deliberate, documented decision rather than
an inherited one.

*Verdict.* **CONDITIONAL.** Question 2 in `06_…`.
