# PS-WORKSHOP-PROVENANCE-001 — delivery evidence

Runtime-inert record. Protected path, independent review required and obtained.

## Outcome

Workshop again retains the member's own wording when they accept an AI rewrite.

Owner decision D1 (2026-08-01) makes the member-approved wording canonical **and**
requires the member's original words to be retained; doc 16 records that retention as
"required and not optional", and it is what makes the deliberate absence of an
AI-changed badge honest. Neither half held in the shipped product.

## What was wrong

Accepting an "Improve with AI" proposal wrote the proposal over the session's single
wording slot, so the member's own sentence stopped existing at that instant. Both save
paths then passed one string to `approved_wording` and `original_wording`, so
`dbo.knowledge_item_versions.original_member_wording` — the column its own migration
header calls "retained, never overwritten" — received AI-produced text. The quick save
additionally hardcoded `authored_via="typed"`, so the nearer of two adjacent save
buttons filed AI-refined text as unaided typing while the other filed it correctly.

## What changed

- Session state gained an eighth element, `original_answer`, following the same
  graceful-degradation idiom as the existing 4→6 and 6→7 growths. It is written only
  when it holds something, so a session that never accepts a proposal writes the
  identical seven-element bucket it wrote before this package.
- `accept_ai_proposal()` replaces an `update_session` + `mark_ai_assisted` pair with one
  atomic write. The pair could half-succeed and leave AI text that was not flagged
  AI-assisted with no original captured — silently the exact corruption this package
  removes.
- The first original wins; a later acceptance never displaces the member's own words.
- Both save paths derive `authored_via` and the retained original identically.

**No schema change.** `usp_SaveKnowledgeItemForOwner` already accepted `@ApprovedWording`
and `@OriginalWording` as separate parameters and `services/knowledge_service.py` already
passed them separately. Only the callers were wrong.

## Verification

- Workshop suites plus `test_site_rules` and `test_governance_pointers`: **745 passed,
  2 skipped, 0 failed.** The two skips are the SQL-gate class (gate deliberately unset)
  and one Spark test that skips when no suggestion renders. No test touched a database
  and none made a provider call.
- The two retention tests were confirmed to **fail against the unfixed source** with the
  exact wrong-value assertions, and pass here. A test that passes either way proves
  nothing.
- Byte-budget module run 15 consecutive times after the fix: **0 failures.**

## Independent review

Three adversarial lenses reviewed candidate `6f5ea885` (data truth, regression and byte
budget, product truth), each instructed to refute rather than confirm. All three returned
CONDITIONAL, together raising one blocker and several majors. A focused two-lens re-review
then examined the correction round.

The blocker was real and reproduced by the writer before fixing: an unconditionally
written empty slot moved the documented adversarial worst case to exactly the ceiling and
made an existing test fail intermittently. Re-review confirmed the fix causally, not just
by observation, measuring the seven-element bucket at 3062–3070 bytes against the
3072 ceiling versus 3066–3072 with the empty slot appended.

Every finding is recorded with its resolution in
`lane_claims/receipts/PS-WORKSHOP-PROVENANCE-001.json`.

The reviewed candidate is `06358da3`; the merged candidate `7fb4a2e8` differs from it only
in comments, docstrings and one member-facing message string, verified by diffing all
non-comment lines. No executable logic changed after review.

## Honest limitations

- Two routes by which PeerSlate-generated text can still reach `original_member_wording`
  remain open, deliberately outside this package's declared scope and recorded as an
  explicit Known-limitation block in `services/workshop_work_session.py`: a Spark-seeded
  session, whose answer begins as generated text; and a second acceptance following a
  blank first one, because an empty retained slot cannot be distinguished from "never
  accepted" without a sentinel the shared cookie has no room for. Both are recommended
  as the first item of a follow-up package.
- The retained original is still **not visible anywhere in the product**. D1 asks for
  "inspectable history"; this package restores the retention half only. Display was
  excluded from scope by the owner outcome and remains owed.
- The My Information edit path is unchanged and cannot preserve a separate original: its
  procedure takes no `@OriginalWording` parameter, so fixing it needs its own migration.
- The anonymous preview cannot retain a separate original — a preview row structurally
  holds one wording. Nothing claims otherwise, and nothing anonymous is canonical or
  durable.
- Nothing here is deployed. Merge is repository truth only; production deployment is a
  separate manual operation requiring an exact main SHA and Pete's authorization
  reference.

## Next action

Deploy is not requested by this package. The follow-up candidates, in the owner's stated
priority order, are the remaining provenance gaps above, then the visual and preview
truth work recorded in the 2026-08-23 Workshop diagnosis.
