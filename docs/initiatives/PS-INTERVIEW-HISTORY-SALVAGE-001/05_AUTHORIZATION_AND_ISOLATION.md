# 05 — Authorization and two-owner isolation implications

The old branch's isolation design is one of its stronger parts. This file
records what it does, where it is weaker than the released platform, and what a
future implementation would have to prove. Nothing here has been implemented.

## The boundary being crossed

This is the first proposal to put **private member content inside an AI prompt
generated from a publicly reachable route**. Every released private surface —
Capture, Voice, Photo, Moment, Placement, Owner Home — lives behind `/app` and a
sign-in redirect. The Interview Studio is the opposite: fully public,
unauthenticated, browser-local, deliberately so.

That makes authorization the central risk of this package, not an implementation
detail. Three distinct failures must be impossible:

1. **Cross-owner disclosure.** Member B's story reaching member A's answer.
2. **Consent bypass.** A confirmed story being used for grounding when the
   member never granted AI-grounding permission.
3. **Public leakage.** Any private story text reaching an unauthenticated
   visitor, a public page, a cached response, a log line, or an error message.

## Layer 1 — Identity resolution

**Released convention.** `identity.get_current_identity()` resolves identity
only from the trusted authentication boundary. It decodes the Easy Auth
principal header, is length-bounded, caps claim count at 250, and raises
`AuthenticationRequired` on anything malformed. `get_optional_identity()` is the
non-raising variant. No route accepts a browser-supplied user ID, email, or
role.

**Old branch.** Follows this correctly. `require_interview_identity` returns
`401` when `get_current_identity()` raises. Every service call passes
`identity.user_key`, never a body value. There is no code path where a
client-supplied identifier selects an owner.

**Verdict.** Sound. Keep as-is.

## Layer 2 — Ownership enforcement in SQL

**Old branch.** Every one of the fourteen procedures takes
`@UserKey nvarchar(300)` first and resolves the owner by joining
`dbo.app_users ON app_user.user_key = @UserKey`. Reads and writes are filtered
by the resolved `owner_user_id`. A story key belonging to another member
produces no row, which the service turns into `InterviewStoryAccessError` and
the API turns into `404` — with an explicit comment that it must not reveal
whether another member owns that key.

That last point matters. Returning `403` for "exists but not yours" and `404`
for "does not exist" is an enumeration oracle. Returning `404` for both is
correct.

**Structural reinforcement.** Ownership is not only procedural:

- `UQ_member_profiles_id_user (profile_id, user_id)` on the foundation table.
- `UQ_interview_stories_id_owner (story_id, owner_user_id, owner_profile_id)`.
- `FK_interview_stories_profile_user (owner_profile_id, owner_user_id) → member_profiles(profile_id, user_id)`.
- `FK_interview_stories_entity_owner (entity_id, owner_profile_id) → slate_entities(entity_id, owner_profile_id)`.
- `FK_interview_story_versions_story_owner (story_id, owner_user_id, owner_profile_id)`.
- `FK_interview_answer_sources_version_story_owner (story_version_id, story_id, owner_user_id)`.

The effect is that a cross-owner row cannot be created even by a buggy
procedure — the database refuses the insert. This mirrors PS-PLAT-005 tenant
integrity and is the right instinct.

**Verdict.** Sound. Keep, and keep the structural constraints specifically —
they are what makes the isolation hold under future edits.

**Caveat on `UQ_member_profiles_id_user`.** It alters a foundation table. Its
rollback in the old branch drops the constraint unconditionally. If any later
package comes to depend on it, that rollback becomes destructive. A current
version should drop it only if this migration created it and nothing else
references it.

## Layer 3 — Consent enforcement

**Two independent gates.** A story is eligible for grounding only when
`confirmation_status = 'CONFIRMED'` **and** `allowed_for_ai_grounding = 1`
**and** `visibility = 'private'` **and** `deleted_at_utc IS NULL`. All four are
enforced in `usp_GetInterviewStoriesForGrounding` and re-checked in
`InterviewGroundedAnswerService.resolve_sources()`.

**The exact-set rule.** `resolve_sources()` compares the returned key set to the
requested key set and raises if they differ, rather than proceeding with
whatever came back. A silently shortened result cannot become a partial
grounding.

**Default deny.** `allowed_for_ai_grounding` defaults to `0`. Archive and delete
force it to `0`. `usp_SetInterviewStoryGroundingPermission` refuses non-confirmed
rows and takes `UPDLOCK, HOLDLOCK`.

**Missing metadata is unsafe.** `normalize_story()` sets `visibility` from the
row or to `""`, never to `"private"`, with a comment stating that grounding
callers must observe an explicit private value. A row that somehow lacks
visibility metadata fails the eligibility check rather than passing it.

**Verdict.** Sound, and the strongest part of the branch. Keep all of it.

## Layer 4 — The signed context token

**Released state.** `_sign_interview_model_context()` on `main` signs
`profile_slug`, `question`, `level`, `family`, `answer`, `evidence_ids`. It is
tamper-evident (itsdangerous, keyed on a salted API key, time-limited on load)
but **not owner-bound** — nothing in the payload identifies who it was minted
for. That is acceptable today because everything in it is public fixture data.

**The moment it stops being acceptable.** As soon as the token can carry
`story_ids` referencing private records, an unbound token is a real gap: a valid
token minted for member A remains structurally valid when presented by member B,
and the follow-up path would resolve A's story IDs.

**Old branch fix.** Adds `owner_user_key` to the signed payload and returns
`403` when it does not match the current identity, plus `400` when the
follow-up's source mode differs from the original.

**Verdict.** Keep, and treat as mandatory rather than optional. A future
implementation should also confirm that `resolve_sources()` is re-run on the
follow-up path against the *current* identity, so the token's story IDs are
re-authorized rather than trusted — the token proves what was asked, not what is
still permitted. A story whose permission was revoked between the first answer
and the follow-up must fail.

## Layer 5 — Cross-site and mutation guards

**Old branch API.** A `before_request` hook on the story blueprint requires, for
every `POST`/`PATCH`/`PUT`/`DELETE`: an `X-PeerSlate-Request: same-origin`
header, a matching `Origin` when present, `Sec-Fetch-Site` in
`{same-origin, none}` when present, and a JSON content type.

**Released model-answer route.** Rejects `Sec-Fetch-Site: cross-site` and a
mismatched `Origin`, requires JSON, and is rate limited at 6/minute.

**Gap.** The custom `X-PeerSlate-Request` header is the strongest of these — a
simple cross-origin form post cannot set it — but it is a convention this
package would introduce. It should be checked against whatever the released
`owner_routes.py` private surfaces already do rather than inventing a second
pattern. Rate limiting on the private endpoints is not addressed by the old
branch and would be needed.

## Layer 6 — What must never be logged or returned

The old branch is careful here and the care must be preserved:

- The API's `DatabaseServiceError` handler returns a fixed message and `503`,
  never the underlying error.
- `app.py` logs `'Interview story grounding rejected: %s'` with the exception
  message only — the exception messages in `services/interview_stories.py` are
  all fixed strings containing no member text.
- `usp_SetInterviewStoryGroundingPermission` writes a JSON **literal**
  (`{"allowed_for_ai_grounding":true}`) into the audit event, not member content.
- `dbo.interview_answer_sources` stores identifiers only.

**One thing to check.** `dbo.interview_answer_attempts` stores
`@AnswerText` — the generated answer, up to 5,000 characters, which is derived
from private member facts. That is private member content in an audit table.
It is defensible (the member needs to see what was generated) but it is a
different retention class from Placement's identifiers-only contract, and it
must be covered by whatever export and deletion story the package adopts.
Deleting a story should have a defined effect on prior answer attempts derived
from it.

## What a future implementation must prove

Modelled on the evidence PS-MOMENT-001 and PS-PLACEMENT-001 actually produced.

**Service-level tests (fake database):**

1. Owner A requesting owner B's story key gets `InterviewStoryAccessError`, and
   the API surfaces `404` with no distinguishing detail.
2. A confirmed story with `allowed_for_ai_grounding = 0` is never resolvable.
3. An unconfirmed, archived, or deleted story is never resolvable.
4. Requesting three IDs where one is ineligible fails the whole request.
5. A row lacking explicit `visibility = 'private'` fails eligibility.
6. A malformed or non-UUID story ID is rejected before reaching SQL.
7. `record_answer` writes the server-resolved source set (per D-5), not the
   model's list.

**Route-level tests:**

8. An anonymous caller selecting a `PRIVATE_*` mode receives the agreed gate
   state and no story data, under whichever answer question 2 in `06_…` gets.
9. A follow-up token minted for owner A is rejected for owner B with `403`.
10. Permission revoked between answer and follow-up causes the follow-up to fail.
11. With the feature flag off, every private endpoint returns a neutral `404`
    and the public Studio output is byte-identical to the current release.

**SQL-level verifier (isolated database, no member content printed):**

12. Two synthetic owners; each procedure invoked with the wrong `@UserKey`
    returns no rows and performs no write.
13. Version immutability: `UPDATE` and `DELETE` on
    `interview_story_versions` are blocked by the trigger.
14. The grounding procedure returns nothing for unconfirmed, unpermitted,
    archived, deleted, or foreign rows.
15. Full synthetic rollback and reapply, with the guarded rollback refusing
    while member rows exist.

**Guardrails:** `tests/test_site_rules.py`,
`tests/test_governance_pointers.py`, and the full suite via
`venv/bin/python -m unittest discover -s tests -t .`

## Residual risks that no test removes

- **Prompt-level leakage.** Containment (K-6) reduces injection risk but cannot
  guarantee a model never restates a private fact in a way the member did not
  intend. The fact-boundary UI (K-8) and the member's review step are the real
  controls; neither is automated.
- **Provider transmission.** Grounding sends confirmed private member text to an
  external model provider. That is a genuine privacy expansion beyond anything
  released, and the member's consent (K-1) must be informed about *that*, not
  just about "AI use" in the abstract. Consent wording is a Pete decision.
- **Public-route conflation.** As long as private grounding lives on a public
  route, a future refactor of that route can widen the boundary by accident.
  Whichever placement is chosen, the private branch should be structurally
  isolated — its own function, its own tests — so it cannot be reached from the
  public path without an explicit identity resolution.
