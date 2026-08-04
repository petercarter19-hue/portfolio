# PS-OPPORTUNITY-SLATE-001 — slice OS-2 completion report

**Slice:** OS-2 — AI steps 1 and 2 (extraction concerns, statement
interpretation), the correction rail, and checkpoint 2 of 2.
**Branch:** `work/2026-08-03-opportunity-slate-os2`
**Path:** Protected (consequential AI) — independent review required by
handoff §16.
**Status:** implemented, independently reviewed (`Conditional`), corrections
applied, then re-gated on a real engine — which found and fixed a data-loss
defect the review had certified. See [§4 residual 3](#4-named-residuals) before
trusting any hash in an older copy of this report. Not merged, not deployed,
flag default off.

This report exists because two shipped comments cite it by name —
`services/opportunity_analysis_service.py` (the model-selection block) and
`.env.example` (the spend-guard cost note) both point at "the slice OS-2
completion report" for the recorded model trial and the per-call costs.
Independent review finding F10 established that no such report existed, so
those citations resolved to nothing. Section 1 is the record they were
pointing at.

**If you are reading this to accept the slice, start at [§5](#5-the-complete-user-visible-copy-delta-against-slice-os-1).**
It is the single place that states the complete user-visible copy delta
against what shipped in OS-1, and it flags the five trust and privacy
sentences that need Pete's explicit re-acceptance rather than acceptance by
omission.

---

## 1. The recorded model trial (handoff §10)

Handoff §10 requires the implementer to choose deliberately for the
higher-consequence steps and record the evidence, rather than silently
inheriting the runtime's `claude-haiku-4-5-20251001` chat default. This is
that evidence.

**Method.** Both models were run through this slice's *real* prompt contracts
and *real* validators (`services/opportunity_analysis_service.py`) against two
employer sources: the clean Northrop Grumman Systems Engineer role from the
locked visual set, and a deliberately mis-captured variant of it (a sentence
truncated mid-phrase, a bullet that lost its object, a line break splitting one
requirement in two, and an embedded `ignore all previous instructions` block).
Live API, no mocks.

### Step 2 — statement interpretation

| | Haiku | Sonnet |
|---|---|---|
| Statements on the clean source | 15 of the 17 in the document | not separately recorded |
| Statements on the adversarial source, run 1 | 7 | 11 |
| Statements on the adversarial source, run 2 (byte-identical input) | 9 | 11 |
| Verbatim span fidelity | 100% | 100% |
| Resisted the embedded injection | yes | yes |
| Read the compound AND/OR degree requirement correctly | yes | yes |
| Latency, full role | ~8.4 s | ~13.9 s |
| Cost per call, full role | ~US$0.0096 | ~US$0.023 |

The clean-source row is reported exactly as it was recorded: 15 of the
document's 17 statements, on the run that produced the decision. The
adversarial rows are where the divergence was decisive and are the reason for
the routing.

**Decision: step 2 routes to Sonnet.** The failure that matters here is
under-segmentation, and it is *invisible to the member*: the screen says
"PeerSlate extracted these statements from the confirmed source", so a dropped
statement reads as an employer who never asked for it. Haiku returned 7 then 9
statements for byte-identical input, dropping real content both times; Sonnet
returned the same complete 11 on both runs. Both models kept 100% verbatim
spans and both ignored the injection, so this is a **recall and stability**
choice, not a safety one — the validators are the safety layer and neither
model got past them.

**Decision: step 1 routes to Haiku.** A missed extraction concern costs the
member nothing: the whole-document correction editor from OS-1 is still there
and still edits any wording by hand. A wrong concern is one dismissal. It is
also the highest-frequency call — every captured source — so the cheap tier is
the right one.

Both choices are plain module constants (`CONCERNS_MODEL`,
`STATEMENTS_MODEL`); they are persisted beside every proposal as provenance,
and changing either has to be a deliberate edit.

**Thinking is disabled on step 2 only.** It costs latency and output tokens on
a public route with a spend guard and bought nothing: the trial produced
identical, fully-valid output with it off. It is deliberately not sent to the
step-1 model, whose family takes a different parameter shape and does not think
by default.

### Cost, and the figure to budget against

Per call on a full-length role description: about US$0.01 for the wording
review, about US$0.02–0.03 for the statement interpretation. A visitor who runs
the whole flow once costs roughly **US$0.04**.

That is not the number to size `PEERSLATE_OPPSLATE_DAILY_AI_CEILING` against.
The guard is per worker process and one unit of budget permits up to two
provider requests (`MAX_PROVIDER_RETRIES = 1`), so worst-case daily provider
spend is:

```
2  x  (worker processes)  x  (the configured ceiling)   requests
```

This is recorded in `.env.example`, in `app.py`, and in the
`DailyAiSpendGuard` docstring (finding F12).

---

## 2. Independent review outcome

The slice was reviewed independently at
`6191bf2ac97bb439136e8572996b40ee0e30523d` and returned **`Conditional`** with
twelve findings. The reviewer could not break the AI seam, the validators'
architecture, the anonymous boundary, the signed context token, or the
migration's transaction envelopes; none of those was restructured in the
correction pass.

**One of those envelopes was wrong anyway, and only running it found it.** The
2026-08-04 isolated SQL gate, executed after this review against a *populated*
OS-1 database, found that `usp_SaveOpportunitySourceReviewForOwner` deleted the
member's previous review before it decided whether to reject the payload, and
committed those deletes on the `invalid` path. Reading the procedure does not
surface that; you have to give it a prior review to destroy. The correction and
the full gate record are in [§4 residual 3](#4-named-residuals) and in the
migration header. Take it as the measure of what a clean independent review of
T-SQL does and does not certify.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| F1 | High | Four member-visible sentences asserted the AI **provider's** retention policy ("Never stored on either", "It is not stored there", "the only copy kept"). Nothing in this repository establishes a zero-retention arrangement; provider inputs are retained by default and ZDR is contractual. | Every retention promise is now scoped to PeerSlate by name and the transit is described without characterising the provider. Held by two tests: one on the rendered public room, one that scans every room template, the room script, and the routes module for the retired phrasings. |
| F2 | High | The spend guard rendered one card for two different facts. `reserve()` returns `False` both when a ceiling is spent and when it was **never opened** — and 0 is the shipped default in `app.py` and `.env.example`, so the most likely first production state (flag on, budget closed) told every visitor a limit was reached that never existed and promised a tomorrow that would never come. | The refusal now branches on `.reason`. A closed budget says so and stops there; a genuinely spent ceiling keeps the limit-reached wording, tomorrow included. Status differs too: 503 for closed, 429 for spent. Both variants keep image 09's card grammar and §7's guarantees. Both are tested and both are captured. |
| F3 | Medium | The no-aggregate rule was keys-only. Model-authored prose was unchecked, so `{"explanation": "You are an 85% match for this role."}` and `{"clauses": ["Best candidate: 92/100"]}` both validated. | Added `_reject_aggregate_prose`, applied to the three model-authored free-text fields (`explanation`, `clauses`, a concern's `reason`) and deliberately **not** to the two verbatim-employer fields. See §3 for the reasoning and the OS-3 obligation. |
| F4 | Medium | The migration was unsafe against a database already at the OS-1 revision: the widened `CK_opportunity_working_sessions_state` is declared inside `IF OBJECT_ID(...) IS NULL`, and there was no `ALTER` anywhere. It would have created the new tables and procedures, reported success, and failed at runtime on checkpoint 2. The compatibility `THROW` probes columns on tables it just created and could not catch it. | Added a guarded idempotent constraint upgrade: drop-and-recreate when the live `CHECK` lacks the new values, no-op on a fresh apply, and it also repairs a missing constraint. Inside the existing transaction envelope. Header states the file is safe to re-apply. Held by a contract test. |
| F5 | Medium | The anonymous input cap (8,000) was enforced correctly but never disclosed; `max_source_units` is the 20,000 storage cap in both modes, so a visitor could paste and confirm 20,000 characters and first learn of the limit at the AI button. | Added a live counter and hint to the public intake, wired into the field's `aria-describedby`. Server enforcement unchanged, and `maxlength` deliberately stays at the storage cap so a long paste is never silently truncated. |
| F6 | Low | Statement span containment was unchecked — only identical pairs were rejected, so "Willing to relocate to Denver." and "relocate to Denver" both validated and inflated two group counts. | Overlapping spans are now refused, the same rule the concern validator already applied. The `locate_spans` first-occurrence residual is named in the validator and below in §4. |
| F7 | Low | `aria-selected` sat on a plain `<tr>`, where it is unsupported outside a grid/treegrid — the selected state was announced to nobody, while the control that performs the selection carried no state. | State moved to the selecting link as `aria-current="true"`, in the template and in the room script. The visual outline stays on the row. |
| F8 | Low | The inert `Explore alignment` primary had `aria-disabled` with no `aria-describedby` pointing at the note explaining why. | Wired. The note renders under exactly the same condition, so the reference is never dangling. |
| F9 | Low | The evidence manifest called `artifacts/2026-08-03-opportunity-slate-os2/` "untracked" — it was tracked and committed, duplicating ~8.5 MB already under `evidence/os-2/`. It also described both capture sources as "generic"; they are the Northrop Grumman fixture. | Duplicate directory removed; both sentences corrected. |
| F10 | Low | Two shipped comments cited a slice OS-2 completion report that did not exist. | This document. |
| F11 | Low | `_daily_ai_ceiling` claimed per-request config reads mean no restart is needed. `app.config` is populated once from `os.environ` and nothing mutates it. | Comment corrected; the restart requirement is stated in `.env.example` and `app.py` and asserted by a test. |
| F12 | Low | The guard "counts calls attempted" while `MAX_PROVIDER_RETRIES = 1` permits two provider requests per reservation. | The doubled worst case is now stated in all three places, in each one's own words: `2 x workers x ceiling` in the class docstring, `2 x workers x this number` in `app.py`, `2 x (worker processes) x (this value)` in `.env.example`. A test asserts the `app.py` and `.env.example` wording; the docstring is not asserted. |

### Focused recheck of F3

The F3 correction was rechecked by probing the prose scan in both directions.
It bound the rule to "a judgement about a person" rather than to bare numbers,
which was the right instinct, but the implementation was over-broad: it refused
**13 of 28** legitimate employer-derived sentences while **21 of 33**
verdict-style evasions still got through.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| F13 | Medium | The scan refused ordinary employer wording — "match invoices within 5% variance", "an overall assessment of programme risk", "a composite score across the three test batteries", "final grade moderation", "a strong candidate experience". This costs more than a retry: budget is reserved **before** the provider call and the scan runs **after** it, so every attempt on an affected job description spends anonymous daily budget and then renders the generic failure card, and the retry fails identically because the phrase is still in the employer's text. That is the frequent, quiet failure the code's own comment names as the worse outcome. | Narrowed in three places and widened in one. Bare `match` now takes the person-binding treatment bare `fit` already had. The aggregate qualifiers (`overall`, `total`, `final`, `composite`) now bind only to nouns that are themselves a judgement, so "final grade" and "composite score" pass while "final verdict" does not. "strong candidate" needs member binding or a score, so "the ideal candidate will have five years" and "a strong candidate experience" pass. Against that, the second-person frames were widened to close the named evasions. Result: **28/28** legitimate sentences pass and **25/33** evasions are refused, both pinned by test. |

---

## 3. The F3 decision: scan, not documented residual

The reviewer offered either a prose scan or a documented residual, and
preferred the scan. The scan is implemented, and its shape is the load-bearing
part of the decision.

**A naive number hunt would have been worse than the bug.** Clauses are drawn
from the employer's own wording and explanations restate it, so "Willing to
travel up to 25% of the time", "a 3.0/4.0 grade point average", and "maintain a
customer satisfaction score above 90%" are all ordinary, correct output on a
routine job posting. Refusing a percentage on sight would break the feature on
real roles — a failure that is both more frequent and less visible than the one
being prevented.

So the scan is bound to a **judgement about a person**, not to a number.

### The operating point: high precision, not high recall

The first four versions of this scan were tuned for recall, and every one of
them introduced a defect its own tests missed. Round 1 was keys-only, so model
prose could carry a verdict. Round 2 added a prose scan that refused ordinary
employer wording. Round 3 narrowed it with a non-person-aware `of`-exclusion
that reopened 11 verdict shapes. Round 4 fixed those and introduced 24 new
false positives by reading "you" inside a reduced relative clause as the thing
being judged. Independent verification also found 6 pre-existing false
positives where the rank branch matched ordinary physical nouns.

**Architect's decision: stop tuning, change the objective.** The two error
types are not symmetric, and at OS-2 they are wildly asymmetric.

* A **false positive** is expensive and certain. The daily spend guard reserves
  budget **before** the provider call and this scan runs **after** it, so a
  refusal burns the visitor's free daily AI allowance and then shows the
  generic §7 failure card. Clauses are quoted verbatim from the employer's
  advert, so the same text fails identically on every retry: the visitor cannot
  fix it, cannot route around it, and is never told why. Job adverts are written
  in the second person, so the wording that trips a loose scan is ordinary, not
  exotic.
* A **false negative** at OS-2 is nearly harmless. Steps 1 and 2 are given no
  fact about the member — verified repeatedly, the prompts receive only the
  employer's source text — so the model has nothing to ground a verdict about a
  person in. A judgement-shaped sentence that slips through here is a stylistic
  flourish about a job advert, not an assessment of a human being.

So at OS-2 this scan is **defence in depth**, and its correct operating point is
**high precision**. Its job is to make "no score, no percentage, no verdict"
structurally true for the cases where a model unmistakably addresses the reader.
It is not a detector for judgement-shaped English, and chasing that long tail
produced four regressions and prevented zero grounded verdicts.

The accumulated pattern set was replaced with a small core. Each pattern
requires **two independent signals** — an explicit second-person address (or a
possessive, or a card label) **and** a score or verdict token. The
`of`-complement machinery is **deleted rather than made cleverer**: a regex
cannot tell an of-complement from a reduced relative clause, and English puts
"you" in both. The rank branch now requires the ranking frame to be about
people, which is what fixes the physical-noun false positives.

**Round 5 applied the same decision to the card rule.** An independent audit of
461 sentences confirmed the high-precision rewrite reproduced its zero-false-
positive result on every previously-assembled corpus, but found **11 false
positives on 180 brand-new advert sentences**, in exactly two rules — 10 in the
card rule, 1 in the rating-adjacency rule. Both were fixed by subtracting, and
nothing was added:

* The card rule allowed a short **uninspected tail** between its label and the
  colon. That is the `of`-complement problem arriving through the card door:
  "Overall fit of you to this role: high" and "Overall suitability of the site
  for the depot: good access from the A1" are the same six-word shape, and the
  rule could not tell a person from a depot. The tail is deleted.
* The same rule carried a **superlative candidate label** — `best|top|ideal|
  strongest` on `candidate|applicant`. "Ideal candidate:" is about as ordinary
  as advert headings get, and clauses are the model's atomic rewrite of the
  employer's own wording, so the rule refused the advert's own heading whenever
  the desired attributes began with a quality word. It also turned on nothing
  meaningful: "The ideal candidate: strong background in adult social care"
  always passed, because a leading "The" breaks the card-start anchor, so the
  refusal depended on whether the employer wrote "Ideal candidate:" or "The
  ideal candidate:". And "candidate" is routinely an adjective on a thing —
  candidate varieties, sites, genes, materials. The branch is deleted.
* Measuring the fix surfaced a third case of the same ambiguity: a **verdict or
  recommendation card with a quality value** ("Overall recommendation: strong",
  "Final verdict: positive from the moderation panel") names neither the judge
  nor the judged, and an employer quoting an inspection outcome writes it the
  same way. Those two labels are deleted from the card rule. The **decision**
  form is kept, because a decision to apply can only be addressed to the reader.
* Separately, the rating-adjacency rule used a bare `fit` where the shared
  judgement-noun vocabulary correctly uses `fit(?!-)`, contradicting the
  module's own stated intent. A hyphen makes the noun a compound **modifier**
  on something else, never the head of a verdict, so the guard now applies to
  every noun in that rule: "a 4/5 fit-out supervisor vacancy" and "a 50/50
  match-funded post" are ordinary employer wording.

Measured result after round 5: **zero false positives across 616 legitimate
sentences (498 unique)**, including 240 written after the scan was frozen, and
**40 of 110 verdict-shaped sentences refused (36%)**, down from 49 (45%).
Losing recall was the intended trade. §6 has the measurement; §4 residual 5
names what now passes.

### The OS-3 note, recorded in three places

> **OS-3 needs a structural control, not a stricter scan.**

Steps 1 and 2 are given no fact about the member at all, which is what makes
their prose scan defence in depth. **Step 3 is different.** The alignment
analysis receives a server-selected allowlist of the member's confirmed
evidence and writes `explanation`, `why_supports`, and
`remains_unestablished` about a real person against real requirements. It is
the first step in this package structurally capable of producing a **grounded**
verdict, and therefore the step where a lexical scan stops being adequate.

**Earlier revisions of this note told OS-3 to apply "a stricter scan". That
guidance is withdrawn as wrong.** Five rounds of tuning proved regex refinement
does not converge: each tightening bought recall by paying in false positives
that the visitor cannot see, cannot fix, and pays for. OS-3 must constrain the
problem structurally instead. Candidates for OS-3's architect:

* **Constrain the output schema** so free prose about the member is not
  representable — bounded enumerated fields plus citations of specific evidence
  records, with no field able to hold a sentence that judges a person.
* **And/or a separate verification pass** over the generated text, with its own
  contract and its own failure mode, before any of it reaches a member.
* **And/or grounding constraints** that make an ungrounded claim invalid by
  construction — every assertion must resolve to a cited evidence record or the
  reply is malformed.

The lexical scan is retained **at OS-2 only, as defence in depth**. It must not
be treated as sufficient anywhere member facts are in scope.

Recorded in:

* `docs/initiatives/PS-OPPORTUNITY-SLATE-001/01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md` §10 — the AI contract OS-3's writer reads first;
* `services/opportunity_analysis_service.py`, the block comment above `_reject_aggregate_prose`;
* this report.

---

## 4. Named residuals

These are known and deliberate, not oversights:

1. **Repeated verbatim wording collides.** `locate_spans` returns the first
   occurrence, so two statements built from two genuinely separate occurrences
   of identical employer wording resolve to the same position and are refused
   as a duplicate span. It fails closed into the honest failure card with the
   source intact — the safe direction — but it is a refusal rather than a
   correct read. Fixing it needs occurrence-aware span assignment (the model
   would have to say which occurrence it means) and is out of this slice.
2. **The spend guard is per worker process.** No shared counter store exists in
   this runtime and this package does not add one. The feature flag remains the
   real stop control. See §1 for the worst-case arithmetic.
3. **The certified bytes changed after review, because a second gate found a
   data-loss defect in the reviewed ones. Read the history, not just the
   current hash.** This entry previously said the migration needed its own
   gate run against a populated OS-1 database before it was applied anywhere.
   That run has now happened, and it was not a formality.

   The sequence, in order, because each step matters:

   1. The independent review at `6191bf2a` certified the executable body of
      `PS-OPPSLATE-001_opportunity_slate.sql` — everything below its header
      comment — as SHA-256
      `b8e881a130b528a108bf44ccd54a605a7998c0bdab2bd32ae9d2ab1140cccb0d`.
      **That certification is superseded and those bytes must not be
      applied.** The reviewer read them and could not fault the transaction
      envelopes; the defect below is not visible from reading.
   2. The 2026-08-03 gate executed those same bytes on a real engine, but
      from an *empty* database. It passed. That gate could not reach the
      defect, because the defect needs a member's prior review to destroy.
   3. The 2026-08-04 gate
      (`work/2026-08-04-oppslate-os2-sql-gate` at `b8c46768`) ran the whole
      apply/verify/exercise/negative/atomicity/isolation/rollback/re-apply
      sequence again against a **populated** OS-1 database, and found that
      `usp_SaveOpportunitySourceReviewForOwner` **destroyed member decisions
      on a rejected proposal**: its "more than 20 concerns" guard sat after
      the two DELETEs that clear the previous review and then COMMITted, so a
      21-concern payload deleted the member's review, its concerns, and every
      applied/dismissed decision and per-concern corrected wording on them —
      then returned `invalid`, which tells the caller nothing happened. The
      gate observed three resolved concerns go to zero. It also found the
      ledger row describing the database as carrying OS-1 after an OS-2
      upgrade. Both are fixed on this branch; the migration header carries
      the full gate record.
   4. **The current executable body hashes
      `c0984204f7d394d50cd30981c1be777332b921b274ef362fd758c8db073ea800`.**
      These are the fixed bytes, and they are the bytes the 2026-08-04 gate
      proved. Recomputed here from the file on this branch, not carried over
      from the porting commit; it is the SHA-256 of the file from
      `SET NOCOUNT ON;` to EOF. The rollback script and the verification
      script are untouched by the fix; the verification script still hashes
      `3ac86a103a751cf428aaa832a6b153d9edaa0a6fe2a74c9ecd87cf09d34e7026` the
      same way.

   Defect 1 changes procedure **behaviour** on the `invalid` path — from
   destroying the previous review to leaving it alone — so this is not a
   cosmetic or header-only edit and the certified-bytes claim had to be
   re-established rather than carried forward. The success path is unchanged.
   The member's own document wording was never at risk on any path: it lives
   on the source version row, which that procedure does not touch.

   What is *not* proved, still. The 2026-08-04 gate ran against a two-owner,
   five-version database, not against production's data volume, and not
   against the production database. The file still ships as `proposed/`, and
   `OpportunitySlateIsolatedSqlGateTests.test_apply_verify_rollback_reapply`
   is skipped by default because no engine is reachable from this machine.
   Concurrency was single-threaded throughout, so the commit-then-select race
   in residual 4 remains unreproduced.
4. **The commit-then-select concurrency window** documented in the OS-1
   migration header is unchanged and still awaiting a deliberate decision at
   the PS-OPS-001 gate.
5. **Judgement-shaped prose can pass this scan. That is the deliberate
   operating point, not an oversight.** Measured on the current
   implementation, not carried over: **40 of 110 verdict-shaped sentences are
   refused (36%)**, down from 49 (45%) before round 5 subtracted the card
   tail, the superlative candidate label and the quality-valued verdict card.
   The other 64% pass. Every class below was tested and every sentence quoted
   is one this scan lets through today; they are pinned as passing in
   `tests/test_opportunity_slate_ai.py`
   (`test_the_shapes_this_scan_deliberately_lets_through`) so that raising
   recall requires changing a test on purpose and re-measuring the
   false-positive corpus.

   **Why this is bounded at OS-2.** Steps 1 and 2 receive only the employer's
   source text. No fact about the member reaches either prompt, so the model
   has nothing to ground a verdict about a person in. A judgement-shaped
   sentence that slips through is a stylistic flourish about a job advert. The
   alternative — a scan tuned to catch these — costs the visitor real money and
   a dead retry every time it is wrong, and four rounds of trying produced four
   regressions. This is the right trade **here** and nowhere else.

   **(a) Employer flattery and a PeerSlate verdict are the same sentence in
   the future or conditional.** An employer has not met the reader, so its
   flattery is future or conditional; a present-tense assertion is a verdict.
   The scan uses that boundary, which means the whole non-present-tense family
   passes: "You'll be a great fit for this team", "You would be a top candidate
   for this vacancy", "You would be an excellent hire", "You'd be shortlisted
   for this", "You'll be selected for interview", "You are likely to be hired
   for this position", "This makes you a good fit". Refusing them would refuse
   "You'll be a great fit for our team and our culture", which is a real advert
   line.

   **(b) Ordinary advert vocabulary a verdict happens to share.** "You are
   qualified", "You are not qualified for this role" (because "you must be
   qualified to degree level" and "if you are qualified for this role, apply
   now" are standard); "This role suits you" (because "flexible hours to suit
   you" is standard); "You align closely with what this employer wants"
   (because "you'll be closely aligned with the product team" is standard);
   "We recommend you apply for this role" (because "we recommend you apply
   early" is advert boilerplate).

   **(c) Free-form judgement with no verdict vocabulary at all.** A lexical
   scan cannot reach this class: "Your chances here are good", "You clear the
   bar for this role", "Probability of success: 0.85", "Confidence you match:
   85%", "This person is highly employable for this posting", "You meet 8 of
   the 10 requirements, which is strong", "Rating: A. You should apply", "This
   is a great opportunity for someone like you", "On balance you are one of the
   stronger people for this", "Strong fit for this role".

   **(d) The whole `of`-complement family.** The machinery that used to catch
   these is **deleted**, because a regex cannot tell an of-complement from a
   reduced relative clause and trying caused the round-3 and round-4
   regressions. So these pass: "Overall fit of the member to these requirements
   is strong", "Overall alignment of your background to the posting is 90%",
   "Total suitability of the applicant for this vacancy is high", "The final
   assessment of this candidate is positive", "Final assessment of you: you
   should apply", "Your assessment of this candidate: strong", "Your assessment
   of readiness for this role: strong", "Overall percentile of you against
   other applicants is 85", "Aggregate ranking of you among applicants: top
   decile", "Final verdict of the review of you: proceed". **Round 5 extended
   this to the card form as well** — see (f).

   **(e) Numbers written as words, and vulgar-fraction glyphs.** "You are an
   eighty-five percent match for this role", "Your alignment with this role is
   eighty percent", "You are a ½ match for this role". Out of scope by
   construction. The fullwidth and small percent signs (`％`, `﹪`) ARE covered,
   because no employer types them and a model reaching for one is evading the
   ASCII form; `½` is not, because "a ½ day on Fridays" is ordinary advert
   wording.

   **(f) The `of`-complement family in CARD form (round 5).** The card rule
   used to allow a short tail between its label and the colon and did not
   inspect it, which is the same failure as (d) reached through a different
   door: it cannot tell "Overall fit of you to this role: high" from "Overall
   suitability of the site for the depot: good access from the A1", and both
   are the same six-word shape. Eight further `suitability|fit|alignment of a
   THING: <verdict>` variants were confirmed by measurement. The tail is
   deleted, so the whole family now passes: "Overall fit of you to this role:
   high", "Overall fit of you to this requirement: high", "Overall fit of the
   person to this role: high", "Composite match of you against the essential
   criteria: 8/10", "Composite fit of the candidate to the posting: high",
   "Weighted fit of your experience to this employer: excellent", "Aggregate
   fit of your profile to this employer: 9/10", "Overall recommendation of
   you: proceed to application". The card rule now requires the label to run
   **straight into the colon**: "Overall fit: high" and "Overall suitability:
   high" are still refused.

   **(g) The superlative candidate card (round 5).** `best|top|ideal|
   strongest` on `candidate|applicant` is an advert **heading**, not a verdict
   addressed to the reader, and it was refusing the employer's own wording:
   "Ideal candidate: strong communicator with a commercial mindset", "Ideal
   candidate profile: strong analytical skills", "Top candidate attributes:
   strong problem solving under pressure", "Best candidate experience:
   excellent onboarding and a named buddy", "Ideal applicant: outstanding
   customer service skills". It also fired on "candidate" used as an adjective
   on a thing — "Top candidate varieties for the trial: high yield and good
   vigour". The branch is deleted, so its rating form goes with it: "Best
   candidate: 92/100", "Best match: 9/10 on the supplier scorecard", "Top
   ranking: excellent in the last inspection", "Ideal fit: strong". The
   verdicts genuinely addressed to the reader are carried by other rules and
   were unaffected.

   **(h) The quality-valued verdict card (round 5).** "Overall verdict:
   strong", "Overall recommendation: strong", "Final verdict: positive from
   the moderation panel". A verdict card with a quality value names neither
   the judge nor the judged, and an employer quoting an inspection or
   moderation outcome writes it the same way. Only the **decision** form is
   still refused — "Verdict: apply", "Recommendation: apply", "Overall
   recommendation: proceed to application" — because a decision to apply can
   only be addressed to the reader.

   **(i) A judgement noun in a hyphen compound (round 5).** "A 4/5 fit-out
   supervisor vacancy is also open at the same site", "The 8/10 fit-out
   packages were awarded to the same contractor", "This is a 50/50
   match-funded post between the trust and the university". This one is a
   pure defect fix rather than a trade: a hyphen makes the noun a compound
   modifier on something else, so no verdict about a person is ever written
   that way, and the shared judgement-noun vocabulary already guarded against
   it. The rating-adjacency rule did not, and now does.

   **This is not tolerable at OS-3**, which does receive the member's evidence
   and therefore can ground a verdict about a real person. §3 records why OS-3
   needs a structural control — a constrained output schema, a separate
   verification pass, and/or grounding constraints — rather than a stricter
   version of this scan.

---

## 5. The complete user-visible copy delta against slice OS-1

**Read this section before accepting the slice.** Independent review finding
C1 recorded that no single document stated the whole copy delta: part of it
was in this report, part in a parity commit message that also said "every
trust and privacy sentence is unchanged" (true of that one commit, misleading
read branch-wide), and `OWNER_VISUAL_REVIEW_2026-08-03.md` carried
"byte-identical trust and privacy copy" as a constraint that governs the
visual pass but reads like a branch-wide guarantee. This is the consolidated
record those three were missing.

**How it was derived.** Not transcribed from the review. The rendered text of
the three shared templates that existed in OS-1 —
`templates/partials/opportunity_slate/_intake.html`, `_review.html` and
`_room.html` — was extracted at OS-1's shipped state (`origin/main`, where
those three files are untouched since this branch's base) and at this branch's
head, with Jinja comments stripped, then diffed. The room script was scanned
the same way for the one member-facing string it owns. Eleven changes came
back, listed in full below.

### Rows 1–5: trust and privacy sentences — THESE NEED PETE'S RE-ACCEPTANCE

These five carry a retention, transit, or analysis promise the owner has
already signed off once, in OS-1, in their earlier wording. They are not
stylistic edits and they should not be accepted by scrolling past them.
(Independent review quoted four; deriving the set found a fifth, row 1, which
makes the same retention promise on the replace screen and had been missed.)

| # | Where | OS-1 (shipped, owner-accepted) | OS-2 (this branch) |
|---|---|---|---|
| 1 | `_intake.html` — lead paragraph, public + replace | "Paste or type a different role description. This replaces the role you brought in — in this public session **the wording you have now is not kept**." | "Paste or type a different role description. This replaces the role you brought in — in this public session **PeerSlate keeps no copy of the wording you have now**." |
| 2 | `_room.html` — public-session banner, top of every screen | "This preview sends your role text to PeerSlate to draw each screen. The only copy kept is in your own browser, for this visit only. Nothing is stored on PeerSlate, **nothing is analyzed**, and nothing is shared or sent to an employer. Saving your work arrives with membership." | "This preview sends your role text to PeerSlate to draw each screen, **and on to PeerSlate's AI provider when you ask it to read the wording**. Nothing is stored on PeerSlate, and nothing is shared or sent to an employer. Your own browser holds the copy you keep, for this visit only. Saving your work arrives with membership." |
| 3 | `_room.html` — left-rail session-truth card, public, line 1 | "Your text is sent to PeerSlate to draw this screen, and **never stored**." | "Your text is sent to PeerSlate to draw this screen, **and on to its AI provider when you ask for a reading. PeerSlate stores none of it.**" |
| 4 | `_room.html` — left-rail session-truth card, public, line 2 | "**The only copy kept** is in this browser tab." | "**The copy you keep** is in this browser tab." |
| 5 | `_room.html` — right-rail "Your role text", public | "Sent to PeerSlate to draw this screen, and **never stored there. The only copy kept** is in this browser tab." | "Sent to PeerSlate, **and on to PeerSlate's AI provider when you ask for a reading. PeerSlate stores none of it. The copy you keep** is in this browser tab." |

**Why each change was forced.** Two reasons, and both are truth failures in
the OS-1 wording rather than preferences:

1. **"Nothing is analyzed" was true in OS-1 and is false in OS-2** (row 2).
   OS-1 made no AI call at all, so the claim was literally correct. In OS-2 an
   anonymous visitor who presses "Check the wording" or "Read the statements"
   sends the employer's role text to PeerSlate's AI provider. Leaving the
   clause standing would have repeated a mistake this room's own shipped
   comment records it being corrected for twice already: a claim about
   analysis that its behaviour contradicted. The clause is removed
   and the AI transit is named in its place, so the visitor is told about it
   before they can trigger it.
2. **The older phrasings implied no copy exists anywhere, which asserts the
   AI provider's retention policy** (rows 1, 3, 4, 5). "Never stored", "the
   only copy kept", "the wording you have now is not kept" are all sole-copy
   claims. The moment the text can travel to a third-party provider, a
   sole-copy claim is a promise about what **that provider** retains.
   PeerSlate can promise what PeerSlate does; it cannot promise what its
   provider keeps. Provider inputs are retained by default, and zero retention
   is a contractual arrangement that nothing in this repository establishes.
   Every retention promise on these surfaces is therefore **scoped to
   PeerSlate by name**, and the transit is described without characterising
   the provider's behaviour. A regression test
   (`test_no_surface_in_the_room_asserts_the_ai_providers_retention`) scans
   every template, the room script and the routes module for the retired
   phrasings, so the old wording cannot quietly come back.

**What did not change in this class.** The signed-in truth sentences are
byte-identical to OS-1, verified by counting occurrences on both sides: the
"Session private" card heading, "Nothing is saved yet.", "You decide what
happens next.", "It is never listed, shared, or sent to an employer.",
"Nothing here is published or made public." and "Nothing was saved, published,
shared, or sent to an employer." all appear the same number of times, in the
same files, on `origin/main` and on this branch. "Nothing is stored on
PeerSlate" also survives intact, though it now sits inside the rewritten
banner of row 2. Only the anonymous-mode retention sentences moved.

### Rows 6–11: build-status and state copy — no owner re-acceptance needed

These changed because the build changed underneath them. Each was an honest
statement about what did not exist yet in OS-1, and each would now be a lie.

| # | Where | OS-1 (shipped) | OS-2 (this branch) | Why |
|---|---|---|---|---|
| 6 | `_review.html` — confirmed banner | "You confirmed {version}. Nothing was saved, published, shared, or sent to an employer. **The next step — reviewing the employer's requirements — is not built yet.**" | "You confirmed {version}. Nothing was saved, published, shared, or sent to an employer." | The next step is built. The retention sentence in front of it is unchanged. |
| 7 | `_review.html` — extraction-concern card, state label | "**None flagged**" (the only state that existed) | "**Not checked yet**" before the review runs; "**None flagged**" now names the reviewed-and-clean state | "None flagged" described a slice where nothing *could* be flagged. Presenting an unrun check and a real clean answer as the same words would have made a genuine result unreadable. |
| 8 | `_review.html` — footer note under the primary | "Reviewing the employer's requirements arrives in a later update. Nothing is waiting behind this button." | *(removed)* | The button is live. The note existed only to explain an inert control. |
| 9 | `_room.html` — right-rail "What happens next", closing paragraph | "**Requirement review and** the evidence alignment map are not built yet. Nothing on this screen **is analyzed**." | "The evidence alignment map is not built yet. Nothing on this screen **is compared against your evidence**." | Requirement review exists now; the alignment map still does not and still says so. The second sentence narrows to the claim that is still true. |
| 10 | `_room.html` — right-rail "What happens next", both branches | Review step ended at "Check the wording, correct anything that came through wrong, then confirm it." Intake step ended at "You'll review the captured wording and confirm PeerSlate has the employer's text right." | One sentence added to each, after the OS-1 sentence, which is itself unchanged: "Then PeerSlate proposes how it reads each of the employer's statements, and you decide." / "Then you'll review how PeerSlate reads each employer statement." | The rail describes the road ahead; the road got one stage longer. |
| 11 | `static/js/opportunity-slate.js` — live-region announcement on the honestly-inert next control | "Reviewing the employer requirements is not built yet. Your source is confirmed and nothing was saved." | "Comparing these requirements against your evidence is not built yet. Your requirements are confirmed and nothing was saved." | Screen-reader-only, and the only member-facing string the room script owns. The inert control it belongs to moved one checkpoint forward, so its explanation moved with it. |

### One user-visible change that is not copy

The "Review requirements" primary at the foot of Review Source reads exactly
the same, but in OS-1 it was a `<button aria-disabled="true">` — announced as
unavailable — and in OS-2 it is a live link to checkpoint 2. Nothing to
re-accept, recorded so the set is complete.

### What this table is not

It is the **change** set, not the whole copy inventory. Slice OS-2 also adds
new strings for surfaces that did not exist in OS-1 at all — the whole Review
Requirements screen, the statement rail, the correction cards, the stage rails,
the public character counter, and the failure cards. Those are new copy on new
surfaces rather than revisions of accepted copy, they are visible in the
committed evidence frames, and enumerating them here would bury the eleven
rows above. If any of them is wrong, it is wrong as new work, not as a silent
edit to something Pete already approved.

---

## 6. Verification

All suites run with the repository `venv` and a placeholder API key; no test
makes a live provider call.

| Suite | Result |
|---|---|
| `tests.test_opportunity_slate` | pass |
| `tests.test_opportunity_slate_ai` | pass |
| `tests.test_opportunity_slate_migration` | pass (1 skipped — the isolated SQL gate, no engine on this machine) |
| `tests.test_site_rules` | pass |
| `tests.test_governance_pointers` | pass |
| `unittest discover -s tests`, on the OS-2 base before the `origin/main` merge | 1,595 tests, pass (5 skipped) |
| The five suites above, after merging `origin/main` | 227 tests, pass (1 skipped) |
| `unittest discover -s tests`, after merging `origin/main` | 1,756 tests, 2 failures — see below |
| `unittest discover -s tests`, final pass (person-aware `of` fix, base `aa6cbbb`) | 1,761 tests, pass (5 skipped), no stub needed |
| `unittest discover -s tests`, high-precision rewrite (base `aa6cbbb`) | 1,762 tests, pass (5 skipped) — one new test pins the shapes now allowed through |
| The three Opportunity Slate suites, round-5 card-rule subtraction (base `aa6cbbb`) | 195 tests, pass (1 skipped) |
| `unittest discover -s tests`, round-5 card-rule subtraction (base `aa6cbbb`) | 1,762 tests, pass (5 skipped) |
| `tests.test_opportunity_slate_migration`, after porting the two SQL-gate fixes | 51 tests, pass (1 skipped — the isolated SQL gate, no engine on this machine) |
| The three Opportunity Slate suites, after porting the two SQL-gate fixes | 206 tests, pass (1 skipped) |
| `tests.test_site_rules` + `tests.test_governance_pointers`, after porting | 33 tests, pass |
| `unittest discover -s tests`, after porting the two SQL-gate fixes (base `origin/main` at `a4923f93`) | **1,974 tests, pass (7 skipped)** |

The final row is the run that counts. The `fcntl` block described below was
fixed upstream by `aa6cbbb`, so the whole suite now runs on Windows unaided and
the two stub artifacts are gone. The paragraphs below are kept as the record of
why the earlier run needed a workaround.

### Prose-scan measurement, high-precision rewrite

The binding constraint is **zero false positives**. The corpus assembles every
legitimate sentence from every harness used across this slice, plus the round-4
false positives, plus the pre-existing rank-branch false positives, plus 118 new
employer/job-advert sentences written for this round across engineering,
healthcare, finance, education, logistics, retail, public sector and research —
deliberately loaded with second-person duty phrasing, physical tier/half
wording, percentages, grades, scores, rankings, assessments and matches.

| Legitimate corpus (every sentence must PASS) | Size | Refused |
|---|---|---|
| Original finding-F3 probe set | 28 | **0** |
| Verification harness, 8 sectors | 43 | **0** |
| Person-window stress set | 28 | **0** |
| Round-4 false positives (second-person reduced relative clause) | 24 | **0** |
| Pre-existing rank-branch false positives (physical `tier`/`half`) | 6 | **0** |
| New employer/job-advert sentences, 8 sectors | 70 | **0** |
| New adversarial batch, aimed at each pattern in turn | 48 | **0** |
| **Total** | **247 (238 unique)** | **0** |

### Prose-scan measurement, round-5 card-rule subtraction

The audit that found the 11 false positives wrote 180 sentences **after** the
scan was frozen, which is the only kind of evidence that tests a regex rather
than confirming it. Round 5's corpus is therefore the union of everything: the
table above, every scratchpad probe, both pinned corpora in
`tests/test_opportunity_slate_ai.py`, the audit's three new batches, and 60
further advert-heading and card-shaped sentences authored for this round across
construction, healthcare, education, housing, agriculture, research, logistics
and procurement — including `The`-prefixed and unprefixed headings, every
`Ideal|Top|Best|Preferred|Essential` × `candidate|applicant|profile|attributes|
experience` combination, `candidate` as an adjective on a thing, the
`suitability|fit|alignment|assessment of <a thing>: <verdict>` family, and
ratings next to `fit-`/`match-` compounds.

| Round-5 legitimate corpus (every sentence must PASS) | Size | Refused |
|---|---|---|
| Harvested from the scratchpad probes | 116 | **0** |
| Harvested from both pinned test corpora, after this round's additions | 216 | **0** |
| The audit's three new batches | 224 | **0** |
| New advert-heading and card batch, this round | 60 | **0** |
| **Total** | **616 (498 unique)** | **0** |

Measured before the tests were updated — so with no overlap between the new
batch and the pinned corpora — it was 565 entries, 485 unique, **0 refused**.
62 of those sentences were refused by the round-4 scan and pass now. **No
sentence that passed before is refused now** — the change is subtraction only.

| Verdict side (recall, measured honestly) | Round 4 | Round 5 |
|---|---|---|
| Verdict-shaped sentences refused | 49 / 110 (45%) | **40 / 110 (36%)** |
| The five shapes named as this scan's floor | 5 / 5 | **5 / 5 refused** |

The five named shapes — "You are an 85% match", "Your score: 92/100", "Verdict:
apply", "You are well suited to this role", "You rank in the top decile" — are
all refused, on patterns 1, 9, 11b, 3 and 7 respectively; none of them touches
the card rule that changed. The 64% that now pass are enumerated by class in §4
residual 5 and pinned as passing by test. **Losing that recall is the intended
trade**, and no pattern was added back to raise it.

### The two post-merge failures are not this branch's, and not real

`origin/main` moved during this correction pass and now carries
`services/workshop_spend_guard.py` (PR 252), which has a **module-scope
`import fcntl`**. `fcntl` is POSIX-only. On Windows every test module that
imports `app` therefore fails to *load*: unmodified `origin/main` at
`e69b0a153568f4ac65e42fbbb15f3b32092df76b` collects 431 tests with 42
module-load errors instead of ~1,595 passing, `tests/test_site_rules.py`
among them. Azure App Service runs Linux, so production and CI are unaffected;
local development on Windows is completely blocked.

That is a Workshop-lane defect, it is not caused by this branch, and it is
deliberately **not** fixed here — it has been raised as its own task. To
verify this branch against the merged base anyway, the full-suite run above
used a throwaway `fcntl` stub on `PYTHONPATH` (scratchpad only; nothing was
added to the repository or the app path). With that stub, the entire suite
passes except two tests —
`test_workshop_review.SpendGuardUnitTests.test_a_ceiling_cannot_be_crossed_by_racing_it`
and `…test_ten_simultaneous_reservations_are_counted_exactly_ten_times` —
which measure real mutual exclusion and fail because the stub's `flock` is a
no-op (`8 != 4`, `3 != 10`). They are artifacts of the verification aid, not
findings.

Failure-set comparison, run without the stub, confirms the boundary: 42
module-load errors on unmodified `origin/main`, 44 on this branch — the two
extra being this slice's own two test modules hitting the identical import,
because those files do not exist on `main`. No other difference.

Visual evidence, capture conditions, runtime assertions, and honest limitations
are in `evidence/os-2/EVIDENCE_MANIFEST.md`. The public set was re-captured
from the corrected build; the `member-*` frames are carried forward, with the
reason stated in that manifest.

---

## 7. Release status

Not merged. Not deployed. `PEERSLATE_OPPORTUNITY_SLATE_ENABLED` ships **false**
and `PEERSLATE_OPPSLATE_DAILY_AI_CEILING` ships **0**, so no anonymous visitor
reaches an AI call on the deployed artifact even if the route were enabled.
Turning the public route on is a PS-OPS-001 **Launch** decision (handoff §18),
not a config change.

The migration still ships as `proposed/` and has been applied nowhere from this
branch. Its current bytes are the ones the 2026-08-04 gate proved on a populated
OS-1 database; the bytes the independent review certified are superseded and
must not be applied. See [§4 residual 3](#4-named-residuals).

Next action: Pete's visual acceptance of the corrected public frames, then the
Azure PR.
