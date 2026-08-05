# PS-OPPORTUNITY-SLATE-001 · slice OS-3 · completion report

Writer: Claude Opus 5, sole runtime writer.
Date: 2026-08-04.
Branch: `work/2026-08-04-opportunity-slate-os3`.
Base: OS-2's tip, `95d184e2846023bbf0134af43911ae6a3d1b4a15`.
Package: `docs/initiatives/PS-OPPORTUNITY-SLATE-001/01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md`,
§16 row OS-3; §1, §2, §7, §8, §9, §10, §11, §13, §14, §18.
Visual authority: `visual-authority/2026-08-02-chatgpt-lock/04-PRIMARY-Alignment-Unsaved-VISUAL-AUTHORITY.png`
(the exact geometry authority for this package), with 08 and 09-b for the
processing and failure frames.

Self-certification: **Conditional on the production schema release only.**
The three visual questions formerly listed here were resolved by Pete on
2026-08-04: defer the filter row to OS-4, use the measured 24px image-04 card
rhythm, and retain the OS-3 closing strip beside the results rather than
creating the measured 138px desktop separation. None changes the no-verdict
rule, privacy, the public boundary, or member-data safety. The application
branch must not open its release PR until the governed production ledger and
OS-3 objects are verified.

**Reconciliation note, 2026-08-05 (application-port branch
`work/2026-08-05-oppslate-os3-app`).** Wherever this report describes the
production schema release as one combined seventeen-procedure
`PS-OPPSLATE-001` migration (including the "Current-main integration, owner
decisions, and schema gate" section below), that plan changed after this
report was written. The schema instead shipped as an **additive** correction:
`PS-OPPSLATE-001` was restored to its exact OS-1/OS-2 form (thirteen
procedures, eight tables), and the four OS-3 procedures and four new tables
released separately under the new migration ID `PS-OPPSLATE-002`, applied to
production 2026-08-05 by pipeline run 528. The application-layer facts below
(this branch's code calls all seventeen procedures; the isolation and
rollback evidence) are unaffected — only the schema's release packaging and
ID changed. See `OS-3_SCHEMA_RELEASE_COMPLETION_REPORT.md` for the additive
schema's own record. This note does not rewrite the narrative below, which is
preserved as written at the time.

**Independent review, 2026-08-04.** A fresh reviewer read this slice against
`4870b3bd0287aead2ce4b96f169771ae8ab6ccd4`, could not break the structural
control (14 attack classes, all refused), and confirmed no field carries model
prose to a member and that the status is genuinely derived server-side. It
returned thirteen findings. All are resolved on this branch and recorded in
**§11** below; the corrections are summarised here because one of them
(**F1**) was a live truth defect on the primary member-facing surface.

**Focused recheck, 2026-08-04.** A recheck of those corrections confirmed
twelve of the thirteen closed and found that **F4 had been half-fixed**: it
reordered the painted layout below 640 and left the DOM alone, so keyboard and
screen-reader order still ran the response rail before any qualification —
WCAG 2.4.3 and 1.3.2. That is corrected here in the markup, with the tab order
measured before and after at 390 and 320 in both modes (§11 F4). The recheck
also found three report-accuracy defects (§8) and two coverage tests that could
not fail (§7), all corrected.

---

## 1. The structural control, and why it is this one

Handoff §10 withdrew "OS-3 applies a stricter scan" as **wrong**, because five
rounds of regex tuning on OS-2 proved it does not converge and each tightening
bought recall by paying in false positives a visitor cannot see, cannot fix and
pays for. It named three candidate structural controls. **This slice implements
all three at once, and they collapse into one idea.**

### The composition boundary

Every sentence a member reads on the Alignment screen is written by one of
exactly three authors, and the model is not one of them:

1. the **employer**, in their own confirmed wording;
2. the **member**, in their own evidence title, version, body and responses;
3. **PeerSlate**, in a fixed set of reviewed sentence templates that live in
   `opportunity_slate_routes.py` beside the room's other member-facing copy.

The model's entire contribution is a set of citations:

```json
{"qualifications": [
   {"n": <a qualification it was given>,
    "cites": [{"clause":   <an index into that qualification's own clauses>,
               "covers":   "<a verbatim span of THAT clause's text>",
               "evidence": "<an id from the server-built allowlist>",
               "excerpt":  "<a verbatim span of THAT evidence's body>"}]}]}
```

There is **no field in that schema that can hold a sentence.** Two of the five
values are integers; the other three are refused unless they are found verbatim
inside text the model was handed. A model that writes "You are an 85% match"
has nowhere to put it: an added field is refused by the exact-key check, a
known aggregate key by the named-key check, and a verdict is not a verbatim
span of an employer's clause or a member's record, so it cannot arrive as a
value either.

### The status is not the model's either

`supported` / `partially supported` / `not enough information` are **derived**,
deterministically, from the citations and the member-confirmed AND/OR
structure (`derive_alignment`):

* a clause is fully covered when its covered spans, merged, span the whole clause;
* a path is complete when every clause in it is fully covered;
* **supported** = at least one path complete; **not enough information** = no
  citation at all; **partially supported** = anything between.

So the model cannot even *say* "supported". It can say "this excerpt of this
record covers these words of this clause", and PeerSlate does the rest.

### Where the OS-2 prose scan went

It is **not** run at request time in this step, because there is no
model-authored text to run it on — and running it over the employer's or the
member's own words is exactly the false-positive failure the scan was narrowed
to avoid (finding F3's reasoning for keeping `quote` and `text` out of it).

It moves instead to where free text now actually lives: **PeerSlate's own
composition templates**, asserted statically by
`CompositionTemplateTests.test_every_composition_template_survives_the_os2_prose_scan`.
That is a stronger placement, not a weaker one: a static assertion over a fixed
set of constants has no false-positive risk at all and cannot be defeated by an
input. The keys-only `_reject_aggregate_fields` check still runs over every
OS-3 reply, because it costs nothing and keeps the named rule pointing at
something a reviewer can read.

OS-2's scan and its pinned tests are untouched. The stylesheet, likewise, is a
strict superset: 613 lines added, **zero OS-1 or OS-2 selectors removed**
(checked mechanically against `HEAD`).

### Adversarial probe — the refusing direction

`TheModelCannotWriteAboutThePersonTests`, every case a reply a model could
plausibly return, every one refused **whole** and never censored:

| Attempt | Refused as |
|---|---|
| `{"summary": "You are an excellent fit for this role."}` and two siblings | `unknown_field` |
| `score`, `match_percentage`, a nested `rating`, a per-citation `confidence` | `aggregate_field` |
| `{"status": "supported"}` — declaring the verdict outright | `aggregate_field`, and `unknown_field` under any other name |
| `covers: "You are an 85% match for this role"` | `span_not_verbatim` |
| `covers: "excellent candidate"` | `span_not_verbatim` |
| `excerpt: "This person scores 9/10 on systems engineering"` | `excerpt_not_verbatim` |
| `excerpt: "a strong hire"` | `excerpt_not_verbatim` |
| an excerpt taken from a **different** authorized record than the one cited | `excerpt_not_verbatim` |
| an evidence id the server never handed over | `unauthorized_evidence` |
| a qualification number it was not given | `unknown_qualification` |
| a clause index out of range | `unknown_clause` |
| two entries claiming one qualification | `duplicate_qualification` |
| over the per-statement citation cap | `over_limit` |
| one clean qualification beside one carrying an unauthorized id | whole reply refused; no partial render |

### Adversarial probe — the permissive direction, pinned

`WhatTheBoundaryDeliberatelyPermitsTests`. A control that refuses ordinary
employer wording is not safer; it is an outage. These must keep working:

* An employer clause containing a percentage — "Achieve a 95% first-time-fix
  rate", "Report on the top 10% of accounts" — is analysed normally, and the
  percentage reaches the screen because it is the employer's requirement.
* An employer clause containing the word "score" — "Maintain a customer
  satisfaction score above 90" — likewise.
* A member's evidence excerpt containing numbers — "from 78% to 96%" — likewise.
* The model chooses **which** clauses it claims. That selection is the
  analysis. Claiming more or less is a wrong answer to the real question, not a
  verdict about a person, and every claim carries an excerpt the member reads
  in the evidence rail to check it.
* A qualification the reply omits is reported as "not enough information"
  rather than dropped: silence is an answer the member is owed.
* Line wrapping is the only normalisation a span may carry; what is stored is
  the employer's and the member's own characters, never the model's retyping.

### What the boundary does NOT stop, stated plainly

It does not stop the model **over-claiming coverage** — citing a real excerpt
for a clause that excerpt does not really establish. That is the irreducible
core of the task and it is why the model choice below is what it is. It is
bounded three ways: the claim is always accompanied by the member's own words
in the rail; the covered fragment is always the employer's own words; and no
number, rank or judgement about the person exists at any layer to amplify it.

---

## 2. Model selection, measured

Handoff §10 requires a deliberate choice with recorded evidence. Trial run
against the live API on 2026-08-04, **outside the test suite**, using this
file's real prompt contract and real validators: six fixture qualifications
(including one whose employer wording is itself verdict-shaped and one that
nothing in the library addresses), three fixture evidence records, three runs
per configuration. Raw output:
`evidence/os-3/model-trial-thinking-default.json` and
`evidence/os-3/model-trial-thinking-disabled.json`.

| | haiku-4-5 | sonnet-5 (default) | sonnet-5 (thinking off) |
|---|---|---|---|
| valid replies | 3/3 | 3/3 | 3/3 |
| fabricated an evidence id | 0 | 0 | 0 |
| correctly reported the unaddressed qualification | 3/3 | 3/3 | 3/3 |
| claimed the WHOLE of "Excellent analytical, problem-solving, and communication skills" from a record about chairing reviews | **3/3** | 0/3 | 0/3 |
| claimed the WHOLE of "Achieve a 95% first-time-fix rate across the supported estate" from a two-region record | **3/3** | 1/3 | **3/3** |
| run-to-run stability | varied | varied | identical |

**An earlier draft of the code comment guessed that verbatim compliance would
decide this. It did not, and the comment has been corrected to the
measurement.** Both models quoted verbatim on every run. What separates them is
**over-claiming**, which is the failure that matters here because it is the one
that tells a member their evidence establishes something it does not.

* **`claude-sonnet-5` for step 3.** It is the conservative reader, and this is
  the step where conservative is correct.
* **Thinking left at the model default (on).** Disabling it buys perfect
  run-to-run determinism and costs one more over-claim on one qualification in
  six. Over-claiming wins: a member told their evidence establishes something
  it does not has been misled about themselves, while a member who sees a
  result move slightly between two runs has seen a judgement being made.

Steps 1 and 2 are unchanged (`haiku-4-5`, `sonnet-5`).

---

## 3. The grounding contract, and how it was proved

The prompt receives the confirmed qualification set plus a **server-built**
allowlist of the member's confirmed evidence — id, title, version, bounded
body — and may cite nothing else.

* **Signed in:** `usp_ListOpportunityEvidenceForOwner`, a new READ-ONLY
  owner-scoped procedure over `dbo.knowledge_items`, returning only
  `item_status = 'confirmed'` and unarchived items at their confirmed version,
  bounded `TOP (@MaxItems)`. Nothing in this room writes a Workshop or Moment
  row — asserted per procedure by
  `test_evidence_is_referenced_and_never_written`.
* **Anonymous:** Workshop's own demo library
  (`services/workshop_demo_library.py`, the fictional Jordan Ellis), which
  imports no database at all. Every surface that shows it says whose it is.
* The ids the prompt sees are opaque short labels (`e1`…). Real keys never
  leave the server, so a leaked prompt carries no addressable identifier.

Proved by: the refusal table in §1; the isolation verifier's new OS-3 section
(§4); and `test_the_grounding_allowlist_refuses_an_unknown_evidence_id` plus
`test_an_excerpt_from_a_DIFFERENT_authorized_record_is_refused`.

**Moments are deferred, deliberately.** §17-Q2 keeps them in scope as evidence
references. OS-3 grounds on confirmed knowledge items only: Moments have no
owner-scoped read that already exposes confirmed wording with a version fence
for this use, and adding one is its own read contract rather than a line of
this slice. `evidence_kind` is CHECK-pinned to the full architectural enum
(`knowledge_item | moment`) and OS-3 only ever writes `knowledge_item` —
exactly the precedent OS-1 set with `capture_method`.

---

## 4. The SQL gate

Throwaway Azure SQL database `ps-oppslate-003-dev-20260804` (Basic, server
`peerslate`, collation `SQL_Latin1_General_CP1_CI_AS` — identical tier, server
and collation to production). Driver `mssql-python`, each file executed as ONE
batch exactly as `scripts/apply_sql_migrations.py` does. **Deleted at the end
of this report; see §9.** `peerslate-database` was never touched.

Baseline: the **slice OS-1 revision exactly as `origin/main` carries it**
(`git show a55a4c5:…`), i.e. byte-identical to what production runs, then
POPULATED through the OS-1 procedures themselves with two distinct owners — two
working sessions, two sources, three appended versions, a member correction
overlay and a confirmed source. Nothing was hand-inserted where a procedure
existed.

| Step | Result |
|---|---|
| **upgrade** | PASS. This revision applied over that populated OS-1 database. Both OS-2 guarded upgrades ran (`UQ_opportunity_source_versions_id_owner`, the widened `CK_opportunity_working_sessions_state`). Afterwards: 12 tables, 17 procedures, 20 foreign keys, 61 CHECKs, 46 key constraints, 17 definition-hash properties — **every constraint enabled and trusted, zero untrusted**. |
| **data** | PASS. **Existing member data survived byte for byte.** A per-row SHA-256 over `original_text`, `original_sha256` and `member_corrected_text` across all version rows: aggregate digest `44F97E1F920218B6EBCC5A1A70C391EA8A49EF02277D161282148FE45D26CD45` before and after, row count unchanged. |
| **exercise** | PASS. All four OS-3 procedures CALLED on the populated database, after the real OS-2 chain: evidence allowlist read (owner A sees their one confirmed item, owner B sees zero), analysis saved and read back across four result sets, both response kinds saved, connected evidence resolved to its real title and version by the procedure rather than by the caller. |
| **negative** | PASS. Stale `row_version` → `changed`. Forged `@UserKey` → `changed`. Owner B against owner A's set → `changed`. Malformed JSON → `invalid`. A "supported" result with zero citations → `invalid`. A statement key from another version → `invalid`. Unknown response kind → `invalid`. Text on a `skip` → `invalid`. Evidence the member does not own → `invalid`. Cross-owner statement → `changed`. **After all ten, the previous analysis and the member's response were still there.** |
| **atomicity** | PASS. A citation whose excerpt exceeds its CHECK: engine error, rolled back whole, no partial rows, no orphan analysis, the previous analysis intact, and the member's source data digest unchanged. |
| **isolation** | PASS. `PS-OPPSLATE-001_owner_isolation_verify.sql` returned `verified = 1` across **all seventeen** procedures, with a new OS-3 section proving the evidence allowlist is owner-scoped and confirmed-only, that an unconfirmed item never reaches it, that an analysis cannot be attached to another owner's set, that a rejected payload leaves the previous analysis and every member response untouched, that a response cannot connect evidence the member does not own, and that a statement correction takes the stale analysis but **spares the member's own answer**. Left no residue. |
| **rollback** | PASS. Refused in turn on `opportunity_responses`, `opportunity_analysis_citations`, `opportunity_analysis_statements` and `opportunity_analyses` while each held rows; refused again on a deliberately drifted procedure definition; then, after the member data was cleared through the room's own delete, removed exactly the 12 tables and 17 procedures it owns, leaving all ten prerequisite migrations intact. |
| **re-apply** | PASS. Clean re-apply, and a SECOND apply over itself was a genuine no-op: same object counts, same ledger row, same `applied_at_utc`, no extra audit event. |

**Two defects the gate found and fixed, both invisible to static assertion:**

1. **The ledger write aborted the whole migration.**
   `dbo.schema_migrations.description` is `nvarchar(500)` and the new
   description was longer, so the file failed on its final statement after
   creating everything. Shortened, and pinned by
   `test_the_ledger_description_fits_the_column_it_is_written_into`.
2. **The verifier would not parse.** A stored-procedure parameter cannot take
   an expression, and three apostrophes in the summary string were unescaped.
   Both fixed; the verifier now runs green.

**The two hard-won lessons this package asked me to apply, applied:**

* Every rejection inside a transaction returns **before** any mutation.
  `usp_SaveOpportunityAnalysisForOwner` validates the payload, the statement
  ownership and the status/citation pairing *and returns* before the first
  DELETE. Pinned statically by `test_every_rejection_returns_before_any_mutation`
  and proved on the engine by the negative row above.
* Every new table declares its composite `(id, owner_profile_id)` candidate key
  **up front**. Pinned by
  `test_every_new_table_declares_its_composite_candidate_key_up_front`.

**No aggregate column exists at any layer.**
`opportunity_analysis_statements.derived_status` is a per-statement enum — the
locked accounting itself — paired to its own citation count by
`CK_opportunity_analysis_statements_citation_pair`, so a "supported" row with
nothing behind it is refused by the database as well as by the application.

**What the migration header now states precisely:** three supported starting
shapes (empty; the OS-1 revision **which is what production carries today**;
the OS-2 revision, gated but unapplied anywhere), the four OS-1/OS-2 procedures
this revision had to change and why, and the one delete that destroys
member-authored text. This revision has **not** been applied to production.

**One member-data behaviour is named rather than hidden.** Re-running AI step 2
replaces the whole statement set, so member responses attached to the old
statements go with them. The alternative — orphaned rows the member can never
see — is worse. The Review Requirements screen now warns before the member
presses that control.

---

## 5. Visual parity, per viewport, honestly

Method: the owner's own, from `OWNER_VISUAL_REVIEW_2026-08-03.md` — render the
real page, put it beside the locked mockup at full width, judge it, correct the
drift, re-render, repeat. Four rounds. Sheets and measurements:
`evidence/os-3/EVIDENCE_MANIFEST.md`.

**Desktop 1440 — good.** Image 04's own proportions, measured off the PNG the
way the other three screens were, and matched: workbench **58.6%** against the
authority's 58.6%; rails 235 / 211 against 235 / 211; the authority's *unequal*
gaps (44 left, 56 right) reproduced with the smaller value on the column gap
and the difference on the rail's margin. Structure matches: four separate
cards, the same five table columns with the authority's visible headers, both
rails, the footer strip.

Corrections made between rounds, each against the sheet:

1. The rails were first scaled DOWN to preserve the room's shared 40px page
   padding. Wrong lever — image 04 spends less on page margin and more on rail
   than any other screen, and shrinking them ran "Confirm I do not have this
   experience" to three lines where the authority holds it on two. The page
   padding moved instead.
2. The workbench is **not** one containing card on this screen. Measured off
   the PNG, the canvas shows between every card (surface 253,253,253; gaps
   247,248,250, at x=270 and x=1100 alike). `_room.html` renders the alignment
   step's cards straight onto the canvas; wrapping them would have been the
   "card within a card" the owner rejected as V9 and again as R5.
3. The card stack was casting `--os-shadow-raised` — the level-3 pool one
   workbench card uses to darken the canvas behind both rails. Six cards each
   casting it read heavier and busier than the authority. Dropped to level 2,
   with the canvas gradient doing the room lighting, which is finding V4/V7/V17
   read the other way round. Radius to 14px to match.
4. The rail's textarea inherited the full-width paste box's 66px right-hand mic
   reservation, leaving ~150px of writing width in a 211px panel. The mic moved
   under the field at 36px (still well past 2.5.8) and the field kept its
   measure.
5. "Tell us more" now opens by default, as image 04 draws it. Five closed rows
   invite nothing.
6. Row rhythm and the supported-explanation wording tightened, twice.

**Mobile 390 and narrow 320 — sound, and judged rather than glanced at.** There
is no mobile authority (§14-M9), so the question is whether it reads as the
same product. The alignment table restacks into one card per qualification
preserving image 04's reading order (number and wording → explanation → status
→ authorized evidence → review control); the header row is hidden and the
evidence cell carries its own label; the review control becomes a full-width
40px button. R16's lesson is applied directly: the desktop row rhythm is
measured off a FIVE-column row and would be paid five times over stacked, so
the cells carry their own smaller spacing below 640. At 320 the card padding
comes in to 0.9rem, as OS-1 established. `scrollWidth <= clientWidth` at all
seventeen swept widths.

### Named deviations from image 04

| # | Deviation | Why |
|---|---|---|
| 1 | `Save privately` renders **grey and inert**, not cobalt and live. | Saving is slice OS-4. This is the honest-inert grammar OS-1 and OS-2 established, with `aria-disabled`, an `aria-describedby` note saying why, and a spoken announcement on press. A live-looking button that did nothing would be worse. |
| 2 | The footer carries **`Run this again`** beside `Review inputs`. | §7 requires a retry and §2 requires reanalysis to be an explicit member action. It is image 09-b's `Retry analysis`, present in the happy state because that is where a member decides to re-run. |
| 3 | The type is roughly one step larger than the authority's, so rows run ~1.3× taller. | Image 04's table type measures ~10 CSS px at a 1440 reading of its frame. The room's own floor is 0.8rem / 12.8px, set in OS-1 and accepted by the owner. Matched as a RATIO — tight lines in a shallow row — which is the same scale-free method the state title already uses. |
| 4 | A public-session banner and an amber demo-evidence note appear above the workbench. | §18 safeguards 5. Public mode only; a signed-in member sees neither. |
| 5 | No decorative prop in the left rail. | Image 04 has none: the rail is given entirely to the title, the truth card and the response panel. |
| 6 | The context strip carries **Source · Version · Session** where image 04 carries **Role · Employer · Source · Version · Session**, and the Source chip reads `Confirmed` rather than a filename. | Independent review finding F14. PeerSlate never extracts a role title or an employer name — nothing in OS-1's capture, OS-2's interpretation or OS-3's analysis produces either, and printing a Role of "Systems Engineer" or an Employer of "Northrop Grumman" would be inventing a fact about the member's opportunity. The filename chip is the same case: OS-1 captures pasted text only (§14-M2), so there is no document to name. Three chips are what this build can say truthfully. Restoring the other two is not a visual change — it needs an extraction contract, which belongs to a later slice. |

### The three findings that need a decision above the writer

**A. The filter row (§14-M4) is NOT built, and that is a deliberate deviation
from an accepted architecture instruction.** M4 directs implementing
`All · Supported · Partially supported · Not enough information` in **both**
Alignment states, "same component, image 04 geometry", and flags it for Pete's
confirmation at visual review. I did not build it, for one reason: image 05
draws that row above a **merged single table**, and image 05's merge is
prohibited by §14-M14 and by the README's locked separate-cards rule. In image
04's geometry there are four separate cards, so "the same component in image 04
geometry" cannot be satisfied without inventing a composition — which is
material visual direction and belongs to the ChatGPT lane, not to me. Filtering
rows inside four cards also makes each card's count ambiguous, and the counts
are the entire locked accounting.

Deferred to OS-4, where image 05 is the authority for it, and reported here
rather than decided quietly. Reversing this is a small piece of work if the
manager rules the other way.

**Owner resolution, 2026-08-04:** Pete approved the OS-3 deferral. The filter
row remains OS-4 work under image 05; OS-3 does not invent a four-card filter
composition.

**B. The locked 12px card gap disagrees with its own PNG.**
`00-READ-ME-FIRST.md` and the architecture both state a "uniform 12-pixel card
spacing" for image 04. Measured off image 04 itself, the gaps between its cards
are 23–27px in a 1365 frame — about 24–28 CSS px at 1440, roughly double. The
build ships the **written rule** (12px, which is also what OS-1 and OS-2 ship
throughout the room), because changing a locked written rule is not a writer's
decision. Side by side, the authority's stack reads airier than the build's.
One token (`--os-card-gap`) settles it either way.

**Owner resolution, 2026-08-04:** Pete approved the measured-image reading.
The shared token is now `24px`; that exact clarification is recorded in the
package README and controlling handoff and supersedes the contradictory 12px
generated prose. The historical captures below remain honest evidence of the
pre-clarification 12px build and are not relabeled as current acceptance proof.

**C. The closing action strip stays inside the workbench on a phone, against
the recheck's stated preference.** The recheck asked for the footer strip —
the `Session private · Nothing is saved yet` truth line, `Review inputs`,
`Run this again` and `Save privately` — to render after the response and
evidence rails as the page's closing actions, instead of between the
qualification table and the response composer. It was built that way first,
measured, and reverted, for two reasons.

*The measured one.* A CSS grid's rows are shared across its columns. With the
strip a sibling of the rails, its row is sized by whichever column is taller,
so a role whose workbench is shorter than the left rail detaches the strip from
the cards it belongs to. Captured at 1440 in the public preview: **138px of
bare canvas** between the provenance line and the strip, against image 04,
which draws it hard under the workbench. There is no CSS fix — decoupling two
columns' row flows needs a wrapper, and no wrapper can hold the workbench and
the strip adjacent while the rails sit between them in source order. Out-of-flow
positioning removes the strip's row dependency but lets a tall response rail
overflow past the site footer, which is worse. Choosing the phone's reading
order therefore costs a deviation from a locked authority at 1440, which is not
a writer's decision to make.

*The product one, and it is not just an excuse for the first.* The strip's
dominant content is a truth statement **about the results** — "Session private ·
Nothing is saved yet. This analysis is session-private. Nothing here has been
published, shared, sent to an employer, or used to alter your evidence."
Keeping it directly under the results keeps that sentence beside the thing it
is true of, rather than roughly 1,500px below it on a 390px screen. The one
control that can destroy member work, `Run this again`, is likewise next to the
analysis it would replace. `Save privately` is inert until OS-4, so there is no
action here a member can complete out of order.

The reading flow is otherwise exactly what §12 asks for: qualifications, then
the workbench's own closing strip, then respond, then check the evidence. If
the owner prefers the strip at the page's end, the cost is the 1440 deviation
above and it should be an explicit acceptance, not a silent one.

**Owner resolution, 2026-08-04:** Pete approved retaining the strip in the
OS-3 workbench. The truth statement stays adjacent to the result it qualifies,
and the locked desktop geometry keeps its measured continuity.

---

## 6. Accessibility (§13)

* One `h1` per state; the qualification cards are headed `<section>`s with a
  real `h3`; the two non-qualification cards are `<details>` disclosures.
* The alignment table is a real `<table>` with visible `<th scope="col">`
  headers, and an equivalent labelled structure when restacked.
* Row selection is performed by a real link (so it works with JavaScript off)
  carrying `aria-current="true"` — the OS-2 finding-F7 correction applied to
  the new control, rather than `aria-selected` on a `<tr>` where nothing
  announces it. Selecting moves both rails without stealing focus.
* Status is a **dot AND a label**, never colour alone. Green supported, amber
  partially supported, slate-grey not enough information, with the room's
  `--os-warning-ink` / `--os-neutral-ink` text-safe values on the labels and
  the raw hues reserved for the non-text dots.
* Processing disables the correction rail and the response rail visibly, never
  hidden, with `aria-disabled`, a `role="status"` explanation authored in the
  template, and a live Cancel that aborts via `AbortController` and restores
  editing.
* Stage changes announce politely from inside the rail, exactly one
  `aria-current="step"` at a time.
* The inert mic carries `aria-disabled`, an accessible name ending "(not
  available yet)", a reason in `title`, and an always-visible text note.
* **Focus order and meaningful sequence (2.4.3, 1.3.2).** The alignment step's
  four regions are emitted in reading order — lead, workbench, response rail,
  evidence rail — so the tab order, the screen-reader order, the no-CSS order
  and the painted order are the same sequence at every width. Image 04's three
  columns are rebuilt from that markup with grid areas, not with `order`. Tab
  order walked on the real build at 390 and 320 in both modes; the numbers are
  in §11 F4 and in the evidence manifest.
* Reflow captured at an effective 640 CSS px; reduced-motion captured; touch
  targets ≥ 36px on every new control.

---

## 7. Tests

Everything is mocked at the Anthropic client boundary. **No test in the suite
makes a network call.** The live model trial ran separately and is recorded in
§2.

| Suite | Result | After review corrections (§11) | After the recheck corrections |
|---|---|---|---|
| `tests/test_opportunity_slate_ai.py` | 134 passed, 374 subtests | 141 passed | **143 passed** |
| `tests/test_opportunity_slate.py` | 80 passed, 75 subtests | 80 passed | **80 passed** |
| `tests/test_opportunity_slate_migration.py` | 60 passed, 1 skipped (the engine gate, run separately — §4), 124 subtests | 69 passed, 1 skipped | **69 passed, 1 skipped** |
| `tests/test_site_rules.py`, `tests/test_governance_pointers.py` | green | green | **15 + 18 passed** |
| **full suite** | **2,036 passed, 7 skipped, 1,508 subtests, 0 failed** (109s) | 2,058 passed, 7 skipped, 0 failed (73s) | **2,060 passed, 7 skipped, 0 failed** (77s) |

After merging current `origin/main` — which squash-merged OS-2 as `ed257c7` and
added PR 269's Workshop polish as `fb7110d`, contributing 27 more tests — the
full suite is **2,087 passed, 7 skipped, 0 failed** (141s), with
`test_workshop_polish` at 26 passed. Every conflict in that merge was the
squash artifact and nothing else: `git diff 95d184e origin/main` is exactly PR
269's sixteen Workshop files, every conflicted path is byte-identical between
main and the OS-2 tip this branch is built on, and the merged tree differs from
the pre-merge commit only in those sixteen files. The tab order and the 1440
geometry were re-measured on the merged build and are unchanged.

The review corrections added **22** tests: five pinning F1's derivation in both
directions including the read path, one for F2's transit sentence, one making
F9's static guard cover what actually renders, and nine for the SQL corrections
(F7's re-derivation and the service payload, F8's three parts, F12's counts,
F13's two).

The recheck corrections added **two**, and strengthened **two more that could
not fail**:

* `test_the_alignment_regions_are_emitted_in_reading_order` — the source order
  of the step's regions, asserted on the rendered room: lead before workbench
  before the first qualification row before the response rail before the
  evidence rail, with the closing strip pinned inside the workbench and each
  rail rendered exactly once. Nothing in the suite asserted order before, which
  is why F4 shipped twice. Reverted against `7bd18d8`'s templates and CSS it
  fails on `assertLess(qualification, response)` — 60821 not less than 3672.
* `test_no_css_rule_reorders_the_alignment_regions_away_from_the_markup` —
  scans every `.os-layout--alignment` rule in the stylesheet and refuses an
  `order` declaration, which is the one property that can make the painted
  sequence differ from the source sequence in this stack, and the one the first
  F4 fix used. Reverted, it fails listing all three of them.
* `test_a_discontiguous_clause_never_reaches_the_full_coverage_sentence` and
  `test_the_stored_read_path_derives_the_same_partial_result` **cited only
  clause 1**, so their path could never complete and the row was partial for a
  reason unrelated to contiguity. Both stayed green with the F1 fix reverted —
  proved by mutation: `covers_whole_clause` replaced in a scratch copy with the
  pre-fix first-run-start / last-run-end rule, both tests **pass**. With clause
  2 now cited in full, clause 1's uncited middle is the only thing between the
  row and `supported`, and under the same mutation both **fail**. The read-path
  test also gained the opposite direction — one unbroken run over clause 1
  reaches `supported` — so "always partial" cannot satisfy it either.

New coverage, by the brief's list:

* grounding allowlist rejecting unknown evidence ids — §1 table;
* the structural control probed hard in both directions, with what it
  deliberately permits pinned — §1;
* no aggregate surviving any layer — validator, service, template, rendered
  HTML, and the migration's column declarations;
* analysis failure honest with inputs preserved — image 09-b asserted word for
  word, with the confirmed statements still on screen behind it;
* read-only during analysis and Cancel restoring editing — carried forward from
  OS-2 and extended to the response rail;
* anonymous never reaching the database — asserted against **both** seams
  across every OS-3 action, including the step that is given evidence;
* rate limits and the spend guard — the AI budget asserted against `app.py`,
  and a spent ceiling proved to fail closed into image 09-b's card with the
  visitor's inputs intact;
* flag-off 404, and the flag checked **before** identity resolution.

**Three OS-2 tests were rewritten rather than deleted**, because OS-3 changed
the truth they pinned, and each rewrite keeps the rule and moves the example:

1. `test_no_stage_names_the_evidence_analysis_that_does_not_exist` → the
   evidence analysis exists now, so image 08's stage names are *required* on
   the two screens that run it and still forbidden on Review Source.
2. `test_the_inert_primary_says_why_it_is_inert` → "Explore alignment" is a
   real destination now, so the assertion moved to the screen that does carry
   an honestly inert primary, plus a check that the old one is genuinely gone.
3. `test_an_unrecognized_step_falls_back_neutrally` → used `?step=alignment` as
   its example of a step that does not exist.

---

## 8. User-visible copy

No existing trust string was reworded or removed. **Three were moved**, and the
first version of this line wrongly said none were: finding F9 took the footer's
`Session private · Nothing is saved yet`, `This analysis is session-private.
Nothing here has been published, shared, sent to an employer, or used to alter
your evidence.` and `Saving this analysis privately arrives in a later update.
Nothing is waiting behind this button, and nothing has been saved.` out of
`_alignment.html`, where they had been typed a second time and had already
drifted, and into the `ALIGNMENT_FOOTER_TRUTH_*` / `ALIGNMENT_FOOTER_DETAIL` /
`ALIGNMENT_SAVE_NOTE` constants the static prose guard scans. The rendered
bytes are identical; only the source of the sentence changed. Verified against
the five sentences the owner is currently re-accepting and against §14-M11's
trust-critical list.

### Which of the five re-accepted sentences renders on which step

Independent review finding F3. The first version of this section said the five
sentences were "verified", which was true of the room but not of every step:
`_room.html` chooses ONE card for the left rail, and on the alignment step it
chooses image 04's amber "Results not saved" card. The public session-truth
card therefore stops rendering on exactly the screen where the OS-3 model call
happens. The suppression is deliberate — two truth cards in one rail is the
duplication finding R14 rejected on the previous screen — but the owner is
re-accepting these sentences and is owed the real matrix rather than a summary.
No sentence was reworded, and none was removed from the room.

Measured, not read: each room was rendered at each step in each mode and the
exact sentences counted (`f3_matrix`, reproduced in
`evidence/os-3/EVIDENCE_MANIFEST.md`).

| # | Sentence | Where it lives | Role | Review Source | Review Requirements | **Alignment** |
|---|---|---|---|---|---|---|
| 1 | "This preview sends your role text to PeerSlate to draw each screen, and on to PeerSlate's AI provider when you ask it to read the wording." | Public banner | ✅ | ✅ | ✅ | **✅** |
| 2 | "Nothing is stored on PeerSlate, and nothing is shared or sent to an employer." | Public banner | ✅ | ✅ | ✅ | **✅** |
| 3 | "Your text is sent to PeerSlate to draw this screen, and on to its AI provider when you ask for a reading." | Public session-truth card | ✅ | ✅ | ✅ | **❌** |
| 4 | "PeerSlate stores none of it." | Public session-truth card, and the amber card's public variant | ✅ | ✅ | ✅ | **✅** |
| 5 | "The copy you keep is in this browser tab." | Public session-truth card | ✅ | ✅ | ✅ | **❌** |

So **two** sentences lose a surface on the alignment step, not three: 4 survives
because image 04's amber card carries "This analysis lives in this browser tab
only. PeerSlate stores none of it." in its public variant. The AI-transit
disclosure that sentence 3 carries is still on the screen — sentence 1 is in the
banner above it, and the banner renders on every step. Nobody reaches the OS-3
model call without reading that their text goes to PeerSlate's AI provider.

**Both of those survival arguments are PUBLIC-MODE ONLY, and the recheck was
right to want that said rather than implied.** Sentences 1–5 are public copy;
the banner and the `--public` truth card do not exist for a signed-in member.
In signed-in mode the *analysed* alignment page therefore carries no AI-transit
sentence at all. What it carries instead is finding F2's disclosure on the
prompt card — "This sends the wording of those items to PeerSlate's AI
provider." — which the member reads on that same screen immediately before
pressing **Explore alignment**, and which is replaced by the result the press
produces. That is defensible: the disclosure is present at the moment of the
decision it informs. It is not the same as a standing sentence on the results
page, and if the owner wants one there it is a small addition to the amber
card's signed-in variant and belongs in the ChatGPT visual-copy lane.

Truth cards actually rendered, per step (public / signed-in):

| Step | Public | Signed-in |
|---|---|---|
| Role, Replace | `--public` | plain "Session private" |
| Review Source | `--public` | `--confirmed` "Source confirmed" |
| Review Requirements | `--confirmed` + `--public` (two cards; the first names the source version) | `--confirmed` + plain "Session private" |
| **Alignment** | `--warning` "Results not saved" only | `--warning` "Results not saved" only |

Signed-in mode never renders sentences 1–5 at all: they are public-mode copy.
It renders "Session private / Nothing is saved yet / You decide what happens
next" on the earlier steps and image 04's "Results not saved / This analysis
remains session-private until you explicitly save it / Nothing was published or
shared" on Alignment.

Two options were available and this is the one taken: **record the matrix, do
not restore the card**. Restoring it would put two truth cards in one rail on
the one screen the owner has a locked image for, which is a material visual
change and not a writer's decision. If the owner wants sentences 3–5 present on
the alignment step in their own words, that is a small edit to the amber card's
public variant and belongs in the ChatGPT lane.

**Three OS-2 sentences became false when OS-3 shipped and were corrected to the
truth, not softened:**

* the right-rail help said "The evidence alignment map is not built yet" —
  it is built;
* the requirements footer said confirming "does not save the slate or produce
  qualification results" — it now produces them (the saving half is kept);
* the confirmation banner said "nothing has been compared against your
  evidence" — that clause is removed.

New copy added in `opportunity_slate_routes.py`, beside the room's other
member-facing constants, and all asserted verdict-free:

* the composition templates — three explanation forms, the two rail headings,
  the cited-for line, the remainder line and its "everything is covered"
  counterpart, and the "that is a gap in the evidence PeerSlate could read, not
  a statement about you" line;
* image 09-b's card, now reproduced **word for word** because this is the slice
  it was drawn for;
* the footer's saving truth and the inert-save note;
* the demo-evidence label and note (§18 safeguard 5);
* the warning before re-reading statements, because that action destroys
  member-authored responses.

New copy added **in templates**, which the first version of this section left
out. Both came from independent review and both are member-facing, so they
belong in the same re-acceptance pass:

* **F2, `_alignment.html`, signed-in prompt card:** "This sends the wording of
  those items to PeerSlate's AI provider." It sits between the existing count
  sentence and the existing "Nothing in your library is changed", and it is the
  first disclosure in the room that member-owned content leaves PeerSlate.
* **F10, `_alignment.html`, the post-swap announcement** — visually hidden, read
  through the room's persistent live region: "Evidence alignment ready. Each
  qualification below shows what the evidence you authorized establishes, and
  the excerpt PeerSlate read." Without it a screen-reader user was told the
  screen was being rebuilt and never told that it had been. F10's other two
  halves add no copy: `data-os-focus` markers and a focus ring.

---

## 9. The gate database

`ps-oppslate-003-dev-20260804`, Basic tier, server `peerslate`, collation
`SQL_Latin1_General_CP1_CI_AS`. Created 2026-08-04 for this gate and
**deleted at the end of it**; `az sql db list -g peerslate -s peerslate`
afterwards returns `master`, `peerslate-staging`,
`ps-journal-001-gate-20260722` (another lane's, left alone) and
`peerslate-database`. **Production was never touched.** No credential was
written into the repository at any point: the harness read the untracked
`.env` and substituted the database name in memory.

A **second** throwaway database, `ps-oppslate-003-shot-20260804`, was created
and deleted the same way after independent review, because the F7/F8/F13
corrections change a stored procedure's control flow. Its results are in §11;
same tier, same server, same collation, same discipline, same deletion.

---

## 10. Limits and next actions

* **Not deployed. No PR opened.** The flag `PEERSLATE_OPPORTUNITY_SLATE_ENABLED`
  remains default-off; the migration is `proposed/` and unapplied to
  production.
* **The base moved and has been reconciled.** OS-2 was squash-merged to
  `origin/main` as `ed257c7` on 2026-08-04, and PR 269 (`fb7110d`) landed
  Workshop polish beside it. `origin/main` is merged into this branch, the
  squash-duplication conflicts are resolved and verified lossless (§7), and the
  full suite and the browser measurements were re-run on the merged result.
* The OS-1 post-commit result-set race is inherited unchanged and now exists in
  four more procedures. It is still unreachable while the flag is off, and it
  is still the one open question to settle **before** the flag is turned on for
  anyone.
* Moments as evidence references: deferred with a named reason (§3).
* Independent review: OS-3 is Protected on two triggers (consequential AI,
  cross-referenced private data), so a fresh Fable 5 review against this exact
  SHA is the next step per §16.
* Owner/manager decisions outstanding: the filter row (§5 finding A), the card
  gap (§5 finding B), and the closing action strip's position on a phone
  (§5 finding C).
* Two sibling `INSERT … EXEC` call sites in the verifier carry the same defect
  F13 found, and were deliberately **not** changed here — see §11.

---

## 11. Independent review corrections (2026-08-04)

Reviewer verdict on the control itself: real, unbroken, 14 attack classes
refused, no field carrying model prose to a member, status genuinely derived
server-side. **None of that was weakened by any correction below.** The
composition boundary, the keys-only `_reject_aggregate_fields` scan, OS-2's
prose scan and its narrowing, and the validators are untouched except where
F1 made the derivation stricter.

### F1 — HIGH. Full coverage reported from discontiguous citations

The one that mattered. `_merge_spans` returns **disjoint** runs, and
`derive_alignment` tested only the first run's start and the last run's end:

```python
if merged and merged[0][0] <= offset and merged[-1][1] >= offset + len(stripped):
    fully_covered.add(index)
```

Reproduced end to end before the fix. Clause *"Five years of hands-on
Kubernetes administration in a regulated environment"*, citations covering only
*"Five years of"* and *"regulated environment"* — merged to `[(0, 13), (54, 75)]`
— derived **`supported`**, and PeerSlate then said, in its own composed voice,
*"Your evidence covers every part of this qualification."* and *"Every part of
this qualification is covered by the evidence you authorized."* That is
PeerSlate telling a member their evidence establishes something it does not,
which is the exact failure direction the model selection in §2 was decided on.
`_derive_from_stored` shares the function, so the read path had the identical
hole, and the DB CHECK cannot catch it — the citation count is genuinely > 0.

The fix is a new `covers_whole_clause(text, spans)` in
`services/opportunity_analysis_service.py`. A naive `len(merged) == 1` was
**not** available: `locate_spans` trims trailing whitespace, so two adjacent
citations that legitimately cover a whole clause arrive as `(0, 33)` and
`(34, 75)` and never touch. So runs are bridged when everything between them
**in the clause's own text** is whitespace, and full coverage then requires
exactly one effective run spanning the stripped clause:

```python
bridged = []
for start, end in _merge_spans(spans):
    if bridged and not text[bridged[-1][1] : start].strip():
        bridged[-1][1] = max(bridged[-1][1], end)
    else:
        bridged.append([start, end])

return (len(bridged) == 1
        and bridged[0][0] <= start_bound
        and bridged[0][1] >= end_bound)
```

Both directions are pinned in `DerivedStatusTests`, because each is a real
failure — over-reporting coverage misleads a member about their evidence, and
under-reporting it misleads them the other way:

| Case | Spans | Before | After |
|---|---|---|---|
| Head + tail, uncited middle | `[(0,13), (54,75)]` | `supported` ❌ | **`partially_supported`** ✅ |
| Two adjacent halves, whole clause | `[(0,33), (34,75)]` | `supported` | **`supported`** ✅ |
| One whole-clause citation | `[(0,75)]` | `supported` | **`supported`** ✅ |
| Head only | `[(0,13)]` | `partially_supported` | **`partially_supported`** ✅ |

Five new tests: `test_head_and_tail_citations_with_an_uncited_middle_are_partial`,
`test_a_discontiguous_clause_never_reaches_the_full_coverage_sentence` (asserted
on the composed sentence, where the member reads it),
`test_two_adjacent_citations_covering_the_whole_clause_stay_supported`,
`test_covers_whole_clause_refuses_a_gap_that_carries_wording`, and
`test_the_stored_read_path_derives_the_same_partial_result`. The module's own
block comment, which already stated the correct rule, now states the bridging
rule too.

Visible in the new signed-in evidence: qualification 3 is deliberately built to
the F1 shape and renders **Partially supported**.

### F2 — MEDIUM-HIGH. Members not told their own evidence goes to the provider

OS-3 is the first step in the room at which **member-owned content leaves
PeerSlate**; every earlier AI call sent only the employer's role text. Up to 24
items × 3,000 units of the member's own confirmed Workshop wording are
serialised into `<authorized_evidence>`. The signed-in prompt card said only
that the items would be "read".

Exact new sentence, in the room's established grammar (`_review.html:163` /
`_requirements.html:104` use "This sends the role text to PeerSlate's AI
provider"), **scoped to PeerSlate by name and asserting nothing about what the
provider retains** — that rule is recorded at `_room.html:56-68` and held by
`test_no_surface_in_the_room_asserts_the_ai_providers_retention`:

> **"This sends the wording of those items to PeerSlate's AI provider."**

It sits between the existing count sentence and the existing guarantee, so the
card now reads: *"N confirmed Workshop items will be read for this comparison.
This sends the wording of those items to PeerSlate's AI provider. Nothing in
your library is changed."* The last sentence is kept deliberately: it is a
different fact, and it is one PeerSlate **can** guarantee. Asserted by
`test_the_signed_in_alignment_prompt_discloses_the_evidence_transit`. Owner
sign-off on room copy still applies.

### F3 — MEDIUM. Three privacy sentences lost a rendering surface

Recorded rather than restored, with the real matrix measured per step and per
mode — see **§8**. Measurement corrects the finding slightly: **two**
sentences lose a surface on the alignment step, not three, and the AI-transit
disclosure is still on that screen in the banner. Restoring the card would put
two truth cards in one rail on the one screen with a locked image, which is
material visual direction and not a writer's decision.

### F4 — MEDIUM. Response rail rendered above the alignment table below 640

§12 requires the response and evidence rails to become in-flow sections
**beneath** the selected qualification. The evidence rail already was; the
response rail is inside the left rail, which stacks first, so at 390 the member
met ~800px of "For this qualification", a textarea, a mic and five action rows
before a single qualification — inverting the select→detail relationship.

**Corrected twice, and the second correction is the real one.** The first pass
used `display: contents` on `.os-layout--alignment .os-rail--left` below 640
plus `order` on the workbench, the response rail and the right rail. That moves
**paint** order and leaves DOM order alone — and the sentence "DOM order is
unchanged, so reading order for a screen reader is unchanged" was written in
this report as if that were the fix rather than the remaining half of the
defect. It is the half that actually names WCAG **2.4.3 Focus Order** and
**1.3.2 Meaningful Sequence**: a keyboard or screen-reader user still met the
response rail before any qualification, and now met it ~2,700px away from where
it was painted. Measured on the pre-correction build at 390, signed-in:

| Tab stops | Region | Painted at |
|---|---|---|
| 6–13 | response rail (inside the left rail) | y 3102–3699 |
| 14–24 | workbench, qualification cards | y 443–2785 |
| 25 | evidence rail | y 4326 |

Focus travelled down 3,699px, back up to 443px, then down to 4,326px.

The second correction moves the response rail in the **markup**.
`_room.html` now emits four regions in reading order — lead (state title,
intro, truth card), workbench, response rail, evidence rail — which is exactly
what a phone renders in one column with no CSS involved at all. Desktop is what
needs the override now: `.os-layout--alignment` declares `grid-template-areas`
and puts the response rail back in the left column directly under the truth
card, where image 04 draws it. `grid-template-rows: auto 1fr` is load-bearing —
a spanning item that crosses a flexible track does not contribute to the
intrinsic sizing of the content-sized tracks it also crosses, so the tall
workbench cannot push the response rail out of its place under the truth card.

No `order` declaration survives anywhere in the alignment layout, and
`test_no_css_rule_reorders_the_alignment_regions_away_from_the_markup` keeps it
that way.

Measured after, on the real build, signed-in and public:

| Viewport | Tab stops 6–16 | Tab stops 17–24 | Tab stop 25 |
|---|---|---|---|
| 390 signed-in | workbench, y 438–2780 | response rail, y 3098–3695 | evidence rail, y 4321 |
| 320 signed-in | workbench, y 501–3033 | response rail, y 3349–3975 | evidence rail, y 4643 |

| Viewport | Tab stops 6–14 | Tab stops 15–22 | Tab stop 23 |
|---|---|---|---|
| 390 public | workbench, y 689–2496 | response rail, y 2813–3410 | evidence rail, y 4066 |
| 320 public | workbench, y 816–2779 | response rail, y 3095–3721 | evidence rail, y 4439 |

Focus now moves monotonically down the page in all four cases. Stops 1–4 are
the site header (skip link, home, Menu, Sign In) and stop 5 is the room's own
`Back` link in the subheader above the layout; all five are outside the three
regions and are identical before and after.

**Desktop is unchanged, measured rather than asserted.** Every region's
bounding box at 1440, before (`7bd18d8`) and after, in both modes:

| Region | member 1440 | public 1440 |
|---|---|---|
| workbench | 304,162 844×1266 — identical | 304,279 844×1089 — identical |
| first qualification card | 304,376 844×422 — identical | 304,549 844×235 — identical |
| response rail | 25,487 235×860 — identical | 25,624 235×860 — identical |
| evidence rail | 1204,162 211×921 — identical | 1204,279 211×952 — identical |
| closing strip | 304,1194 844×202 — identical | 304,1134 844×202 — identical |

One measured phone difference, and it is a restoration rather than a change:
with the left rail no longer `display: contents`, the gaps between the state
title, the intro and the truth card go back to the room's 12px card rhythm from
the 14.4px page-grid row gap the first correction had given them. Everything
below shifts up 4.8px.

**The closing action strip stays inside the workbench, and that is a decision
against the recheck's stated preference.** See §5.

### F5 — MEDIUM. Composed explanations printed mid-phrase fragments

Before, from the reviewer's own evidence:

> Your evidence covers Bachelor's degree in, 3+ years of and a Master's degree, and 1 more.

After, on the same shape:

> Your evidence covers “Bachelor's degree in”, “3+ years of” and “a Master's degree”, and 1 more.

The fix is in **composition only**. Nothing changed about what a citation may
claim, the verbatim-span requirement, or the coverage rule:

1. every phrase is **quoted**, so a reader can see where PeerSlate's sentence
   stops and the employer's wording starts — the same grammar `.os-excerpt`
   already uses for the member's own excerpt, with the same `\201C`/`\201D`
   characters. Typographic quotes deliberately: Jinja escapes a straight `"` to
   `&#34;`;
2. a fragment that is nothing but a function word (`in`, `of`, `and`, `the`, …)
   is dropped. **Deliberately not a character minimum** — "SQL", "PhD" and
   "AWS" are real three-letter qualifications and a length rule would delete
   them;
3. duplicates are collapsed case-insensitively;
4. when nothing survives, two new reviewed constants take over —
   `EXPLANATION_PARTIAL_UNNAMED` ("Your evidence covers part of this
   qualification.") and `RAIL_SUPPORTS_LINE_UNNAMED` — rather than printing
   "Your evidence covers ." at the member.

The `excerpts=True` filter applies to covered **fragments** (sub-spans) only.
Unestablished **clauses** are whole confirmed statements and are quoted but
never dropped: losing one would hide a requirement.

### F6 — MEDIUM. No visual evidence for the signed-in workbench

Every previous OS-3 capture was the anonymous public session. §15's image-04
acceptance item is the **private** workbench, which differs in visible chrome.
Six new captures, listed in the evidence manifest, at 1440 / 390 / 320 plus the
selected-row rails at 1440 and 390, and a side-by-side against image 04 taken
from the **signed-in** build. What is real and what is stood in is stated in
full in the manifest; in short, everything visual is real and the database row
→ view mapping and the provider call are stood in. The nav still shows "Sign
In" because the room was rendered outside a real login session — that is a
capture artifact of the harness, not the product, and it is called out on the
sheet.

### F7 — MEDIUM. The store never re-derived cited evidence identity

`usp_SaveOpportunityAnalysisForOwner` took `evidence_key`, `evidence_version`,
`evidence_title` and `evidence_kind` verbatim from the payload with no lookup
against `dbo.knowledge_items`. Its sibling
`usp_SaveOpportunityResponseForOwner` already did it correctly. The analysis
procedure now matches it: the payload supplies a **key**, and the version, the
title and the kind are read from the member's own `item_status = 'confirmed'`,
`archived_at_utc IS NULL` item at its confirmed version, owner-scoped. A key
belonging to somebody else, to a draft, to an archived item or to nothing
resolves to NULL and is refused **before** any mutation. The three derived
fields are also removed from the service's payload, so nothing in the caller
looks like it controls them.

### F8 — LOW-MEDIUM. Citation validation happened after the DELETE

Member data was never at risk (`XACT_ABORT` + CATCH rollback, and the service
re-bounds every field first) and this is materially not the OS-2 defect class —
but the header claimed *every* rejection returned before the first DELETE, and
that was false for citations, which could only fail as a 503 instead of
`'invalid'`. Three corrections:

* the citations are shredded into `@Citations` and validated in the same guard
  phase as the per-qualification rows, before the first `DELETE`, so the header
  claim is now true of the whole payload;
* the OPENJSON declarations use `nvarchar(max)` rather than column widths — the
  wider-parameter idiom this file already documents at MIG:1676-1679 — so an
  over-length value reaches the guard instead of being silently truncated and
  tripping a CHECK later;
* `citation_count` is reconciled against the rows actually shredded for that
  statement, so `CK_opportunity_analysis_statements_citation_pair`'s "cannot
  drift" comment is true rather than overstated.

### F9 — LOW. Three composition constants nothing rendered

`ALIGNMENT_FOOTER_TRUTH`, `ALIGNMENT_FOOTER_DETAIL` and `ALIGNMENT_SAVE_NOTE`
had zero references; the sentences shipped hardcoded in the template and
`ALIGNMENT_FOOTER_TRUTH` had already drifted from what rendered. `ALIGNMENT_*`
is what `CompositionTemplateTests` scans, so part of the static guard pointed at
strings no member saw. The single constant is replaced by the two labels that
actually render (`..._TRUTH_PRIVATE`, `..._TRUTH_PUBLIC`), all three are carried
to the template on the room dict the way `demo_label`/`demo_note` already were,
and a new test —
`test_every_scanned_alignment_template_actually_reaches_a_member` — fails if any
scanned constant is unreferenced.

### F10 — LOW, accessibility. Three fixes

* `data-os-focus tabindex="-1"` added to each of the alignment screen's three
  states (the two prompt-card headings and the first qualification card's
  `<h3>`), so `restoreFocus` no longer leaves focus on `<body>` after a
  successful analysis. Every other screen already had one.
* A completion announcement. The stage rail's last message is stage 3, fired
  immediately **before** the DOM swap, so the screen was never announced as
  ready. `_alignment.html` renders a `[data-os-swap-announce]` sentence and
  `swapRoom` repeats it through the **persistent** live region that lives
  outside the swapped fragment — a live region inserted together with its own
  text is not reliably announced. The sentence is server-authored; the script
  still owns no member-facing copy.
* `input` and `select` added to the branded focus rule, which covered
  `a, button, summary, [tabindex], textarea` but not the response rail's
  `connected_evidence_key` radios. Radios and checkboxes get a hugging ring
  rather than a square box floating beside a round control.

### F11 — LOW. Anonymous stage naming

In the two-request anonymous path, stage 2 (the one that names the evidence
check) was set synchronously and therefore displayed throughout the confirm
round-trip, which checks no evidence. Stage 1 now covers the confirm request and
stage 2 begins when the request that actually reads the member's records is
issued. The signed-in single-request path is unchanged; its stage 2 always
spanned the real read.

### F12 — LOW. Rollback header counts

"thirteen procedures and the eight tables" → **seventeen** and **twelve**,
verified by counting the file's own lists in
`test_the_rollback_header_counts_what_the_rollback_removes`. The lists were
correct throughout; only the summary was stale.

### F13 — LOW. Verifier defects

* The owner-B analysis check was an `INSERT … EXEC` of a **four**-result-set
  procedure into one nine-column table variable. It passed only because owner B
  has no requirement set, so it proved nothing and would have become error 213
  the moment the fixture changed. Isolation is now asserted on the tables —
  fixture-independent — plus a check that no analysis row escapes its owner
  across the joins.
* `usp_GetOpportunityAnalysisForOwner` gains positive-path coverage: it is
  executed for the **owner** (any runtime failure surfaces as a real error) and
  the rows it is contracted to return are asserted.
* The no-aggregate guard matched four fixed names, so `alignment_rating`,
  `fit_index` or `confidence` would have passed. It is now concept-based across
  eleven patterns, and a test asserts that none of the seventeen procedure
  bodies trips it.

**Deliberately not changed, and disclosed.** The same `INSERT … EXEC` shape
exists at two earlier call sites in the same verifier —
`usp_GetOpportunitySourceReviewForOwner` (VER ~592) and
`usp_GetOpportunityRequirementsForOwner` (VER ~773), both two-result-set
procedures. They have the identical latent error-213 hazard and prove the
identical nothing. They belong to OS-1 and OS-2, which have their own open PRs
and their own certified evidence; editing them from this branch would broaden
the slice and risk conflicting with those PRs. Routed to the manager as a
follow-up rather than fixed quietly.

### The corrected SQL was re-proved on a real engine

The F7/F8/F13 changes alter a stored procedure's control flow, which no static
assertion can execute. A second throwaway database was created and destroyed
for this: **`ps-oppslate-003-shot-20260804`**, Basic tier, server `peerslate`,
collation `SQL_Latin1_General_CP1_CI_AS`. `peerslate-database` was never
touched, and no credential entered the repository — the harness read the
untracked `.env` and substituted the database name in memory. Deleted at the
end; `az sql db list -g peerslate -s peerslate` afterwards returns `master`,
`peerslate-staging`, `ps-journal-001-gate-20260722` (another lane's) and
`peerslate-database`.

| Step | Result |
|---|---|
| **apply** | PASS. Nine platform migrations + PS-WORKSHOP-001, then this revision. 12 tables, 17 procedures, **0 untrusted constraints**. The new `@Citations` table variable, the `UPDATE … FROM` against it, and the `CROSS APPLY OPENJSON` guard all compile and create. |
| **F7 proved, not assumed** | PASS. The verifier's payload was changed to send a **wrong** identity beside a real key — `"evidence_kind":"moment"`, `"evidence_version":99`, `"evidence_title":"A title the caller invented"`. The stored row reads back `knowledge_item`, version `1`, `Synthetic evidence item`: **the member's own confirmed item, read by the procedure**. A second assertion fails if any caller-invented value reaches the store. The old payload sent values that happened to be correct, so its pass proved nothing. |
| **F7 negative** | PASS. Owner A citing **owner B's** confirmed evidence → `invalid`, and owner A's previous analysis still present afterwards. Needed a real item belonging to owner B, so the verifier now provisions one — and asserts owner A cannot read it. |
| **F8 proved** | PASS. A 900-character excerpt (cap 400) returns **`invalid`** rather than being truncated to 800 by a narrow OPENJSON declaration and then tripping `CK_opportunity_analysis_citations_excerpt_length` as an engine error after the DELETEs. |
| **F8 count reconciliation** | PASS. `citation_count: 4` with one citation row → `invalid`, previous analysis intact. |
| **verify** | PASS. `verified = 1` across all seventeen procedures, with the four new clauses in the summary detail. Left no residue. |
| **re-apply** | PASS. A second apply over itself is a genuine no-op: one ledger row, unchanged. |
| **rollback** | PASS. Removed exactly its own 12 tables and 17 procedures, cleared its ledger row, and left all ten prerequisite migrations and `dbo.knowledge_items` intact. |

### F14 — LOW / documentation

The missing **Role** and **Employer** context chips are now deviation 6 in §5's
named-deviations table, with the reason: PeerSlate never extracts a role title
or an employer name, so printing either would invent a fact about the member's
opportunity.

---

## Owner decision — controlled OS-3 evaluation, 2026-08-04

Pete approved proceeding with OS-3 for the current small, unpromoted demo
audience after reviewing the semantic limitation below. This is an explicit
acceptance of a bounded evaluation risk, not a claim that semantic entailment
has been mechanically proved or that the anonymous route is access-restricted.

The model may occasionally connect an allowed, verbatim demo-evidence excerpt
to an employer clause that the excerpt does not actually establish. Existing
guards still prove the important structural facts: the excerpt is verbatim,
comes from the labeled fictional demo library (or the signed-in member's own
authorized evidence), names no record outside the allowlist, and contributes
no model-written prose. Deterministic coverage code cannot independently prove
the meaning of that connection, so a false-positive citation can still yield
`Supported`.

For this controlled evaluation, the owner accepts that `Supported` is an
AI-proposed interpretation that may be wrong. The demo-persona and ownership
labels remain mandatory, the evidence excerpt stays visible for human review,
and no score, application recommendation, publication, or canonical-evidence
change is introduced. Broader promotion remains a separate release decision;
this acceptance does not waive a later truth-boundary review for that audience.

No runtime copy or visual treatment changed for this decision. The current
surface already labels the fictional evidence and exposes the cited excerpt;
inventing a new warning or visual hierarchy from the implementation lane would
exceed the locked authority.

## Current-main integration, owner decisions, and schema gate — 2026-08-04

- The application branch was merged with governed-schema `main`
  through `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`. The one migration-test
  overlap was resolved in favor of OS-3's full seventeen-procedure application
  contract while retaining the newer shared governance, Community work, CLI
  ordering correction, and approved Azure-identity task boundary.
- Pete resolved finding B above in favor of the measured image-04 geometry.
  The one shared token is now `--os-card-gap: 24px`; the package README and
  controlling handoff record that the decision supersedes the contradictory
  12px generated prose. The old evidence manifest is explicitly labeled
  historical. Fresh exact-viewport evidence now lives under
  `evidence/os-3/owner-gap-2026-08-04/`: 1440×1024 desktop, 390×844 mobile
  from page start, and 390×844 at the card stack. Each capture asserted the
  computed shared token was `24px`; visual inspection found no overlap or
  horizontal clipping.
- Focused OS-3/schema/Community integration before the final ops-only merge:
  **349 passed, 2 skipped; 780 subtests passed**. After merging `f59dd9a`, the
  five affected OS-3/AI/migration/schema/service modules passed **351 tests,
  2 skipped**. Repository-wide Windows run excluding the known
  POSIX-only `0o600` assertion: **2,391 passed, 9 skipped, 1 deselected;
  3,200 subtests passed**. `git diff --check`: pass.
- Production schema remains the release gate. Run 497 failed before opening
  the database because the pipeline placed a global CLI option after the
  subcommand. Run 501 reached connection establishment and failed closed
  because its plain shell had no Entra credential. PR 278 corrected the task
  boundary and the service connection is mapped to a narrow contained SQL
  user. Run 506 was superseded by the same-SHA automatic release before the
  schema stage. Run 507 received an exact recorded approval but was separately
  canceled before its deployment job started. Run 508 passed Build and was
  then canceled at the account level; its timeline says `The build was
  canceled by peerslate19@gmail.com.` Production was re-read afterwards: the
  ledger still describes OS-1/OS-2 and all four sampled OS-3 objects are absent.
  No further run was queued over that repeated external cancellation. A new
  exact-main apply must be deliberately allowed to finish before this
  application branch can open its release PR.
- **Reconciliation note, 2026-08-05.** Runs 497–508 above targeted the
  combined single-migration form of `PS-OPPSLATE-001` this branch inherited
  at merge time. That plan was superseded before any production apply
  succeeded: `PS-OPPSLATE-001` was restored to its exact OS-1/OS-2 form and
  the OS-3 schema (four procedures, four tables) shipped separately as the
  additive migration `PS-OPPSLATE-002`, which applied to production
  2026-08-05 by pipeline run 528. This application branch
  (`work/2026-08-05-oppslate-os3-app`) was ported onto that additive
  baseline rather than the combined form described above.
