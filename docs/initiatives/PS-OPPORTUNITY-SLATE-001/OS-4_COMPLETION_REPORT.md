# PS-OPPORTUNITY-SLATE-001 — slice OS-4 completion report

> **Continuation record, 2026-08-05 (Claude lane).** Final candidate SHA for
> this slice is `5b164c5b713988610b3eec811cd5e7cead257a15` on
> `work/2026-08-05-oppslate-os4-app`, one correction commit atop the ported
> checkpoint. Independent review first REFUSED the port (`a87e713`) because
> the three new mutating routes shipped with no rate limit and the rate-limit
> guard test was inert; the correction adds `save_slate`/`delete_slate` at
> 30/min and `reanalyze` at 6/min (the same AI budget as `run_analysis`,
> which shares its model helper), replaces the guard with a real
> `app.url_map` enumeration checking the limiter's own wrapper marker, fixes
> the reanalyzed-state footer truth, links an orphaned saved slate from
> intake (owner-only, leak-checked), and pins `ALLOWED_PROCEDURES` with an
> exact-set test. Re-review APPROVED with all five fixes verified
> behaviorally. This branch merges only after `PS-OPPSLATE-003` is gated,
> merged, and applied to production.


**The save lifecycle.** Writer: Claude Opus 5, sole runtime writer.
Branch `work/2026-08-04-opportunity-slate-os4`. Self-certification: **Pass**,
with the limits named in §8 — nothing is deployed, the flag stays off, and
Pete's visual acceptance has not been given.

Base: `work/2026-08-04-opportunity-slate-os3` at
`7bd18d83acc0c9d908264896976a6c0c08ffd490`, reconciled onto that branch's
moved tip `254fd839dcaa586ca8e700084b8dbbf83cb121cd` (which itself carries
`origin/main` at `ed257c7b5dbc21b99208d117f509f9b6d457e95a`). `origin/main`
is an ancestor of this branch's head.

**Reconciliation note, 2026-08-05 (application-port branch
`work/2026-08-05-oppslate-os4-app`).** Wherever this report describes the
OS-4 schema as landing inside one combined `PS-OPPSLATE-001` migration
(§5's SQL gate — 16 tables, 20 procedures, "now describes OS-1/OS-2/OS-3/OS-4
and twenty procedures" — and §6's four-starting-shapes header description),
that plan changed after this report was written, following the same
precedent OS-3 hit first. `PS-OPPSLATE-001` remains restored to its exact
OS-1/OS-2 form (thirteen procedures, eight tables); OS-3 shipped separately
as the additive `PS-OPPSLATE-002` (applied to production 2026-08-05, pipeline
run 528); and the OS-4 schema in this report — the three saved-slate
procedures and four new tables — is re-cut as its own additive migration,
`PS-OPPSLATE-003`, authored on `work/2026-08-05-oppslate-os4-schema`. It is
**registered as an ungated draft (gate: null) and not applied to any
database**, and this application branch does not open a release PR until it
is gated and applied. The application-
layer facts below (this branch's code calls all three OS-4 procedures; the
SQL gate's functional findings, defect fixes, and persistence proof) are
unaffected — only the schema's release packaging and migration ID changed.
This note does not rewrite the narrative below, which is preserved as written
at the time.

---

## 1. What this slice does, in one paragraph

`Save privately` was the last honestly-inert control in this room. It is now
live, and with it: an immutable saved result that pins the confirmed source
version, the confirmed requirement set, the analysis, every evidence
reference at the version it was cited at with its bounded excerpt, and the
member's own response context. Saving again appends a version and overwrites
nothing. A separate, mechanical notion of **currency** answers a question
"saved" cannot: does this result still apply to your inputs? When it does not,
the member gets image 09-c's card and an explicit `Reanalyze` that produces a
new unsaved result *alongside* the still-identifiable saved one. Delete is
atomic, and when it fails the slate stays visibly, completely saved.

---

## 2. Currency: the design, and how both directions were proved

> **Amended by independent review finding F1 (§11).** This section describes
> the three-fact fingerprint as shipped at `8b0db12`. It is now a **four**-fact
> fingerprint: a content digest of the confirmed source wording and the
> analysed statement set was added, because both can be rewritten in place
> without any version number moving. Everything below still holds; §11 has the
> fourth fact, why the cheaper alternative did not work, and the rendered proof.

**The fingerprint.** `compute_input_fingerprint` in
`services/opportunity_slate_service.py` is a pure function of exactly three
facts: the confirmed source version number, the confirmed requirement-set
version number, and every evidence record the result cites paired with a
version. It is SHA-256 over a canonical string whose first line is a format
version, so a future change to what counts as an input becomes a *new*
fingerprint rather than a silent reinterpretation of the old one — every
stored digest then stops matching, which reads as "inputs changed". That is
conservative in the only safe direction: it can never produce a false
"still current".

Three deliberate details:

- **Pairs are sorted inside the function, not trusted.** The two call sites
  read from different result sets, and a digest that depended on row order
  would report staleness that is not there.
- **A vanished evidence record is encoded as version `0`, not dropped.**
  Dropping it would make an archived or un-confirmed citation indistinguishable
  from one that was never made — precisely the change the member most needs to
  be told about.
- **The same function computes both sides.** At save time the versions are the
  ones the analysis pinned; at read time the same evidence *keys* are paired
  with the version the member's library carries **now**, read live by
  `usp_GetOpportunitySavedSlateForOwner` through a left join on
  `knowledge_items` (owner-scoped, confirmed and unarchived only). The saved
  row's stored digest is additionally re-derived from its own pinned rows as
  an integrity check: if the row and its evidence disagree about what was
  saved, `is_current_for` returns False rather than offering a reassurance it
  cannot support.

**Both directions, proved twice.** In tests (`CurrencyTests`, 6 tests):
unchanged inputs read current; a cited item moving from version 1 to 2 reads
stale; a cited item disappearing reads stale; a new source or requirement
version reads stale; no working inputs at all reads stale rather than current;
a snapshot that disagrees with itself is never reported current. And on a real
engine, in the SQL gate, against real rows: pinned 1 / current 1 →
`Current for these inputs`; editing the Workshop item to version 2 → pinned 1 /
current 2, **with the snapshot itself unmoved**; un-confirming it → pinned 1 /
current `NULL`.

**Savedness is a separate question, and it needs a second comparison.**
`_resolve_saved_state` is a pure three-fact function. Currency alone is not
enough: a member who presses `Run this again` on unchanged inputs gets a
*different* analysis on the *same* inputs, so a fingerprint match would have
shown a green "Saved privately" banner over a result that was never saved. The
saved row therefore stores `saved_analysis_key`, and the state resolves as:
no saved result → unsaved; the on-screen analysis is not the saved one →
unsaved (with an honest note naming the saved result that remains available);
otherwise current → saved, not current → stale.

---

## 3. Saved and unsaved are one component with a state prop

Image 04 is the package's exact geometry authority. Image 05 is authority for
saved-state **content and actions only** — its flatter cards, compressed
spacing and blue-heavy palette are prohibited (README locked rules, §14-M2).

The build makes that structural rather than disciplinary. There is no
saved-state layout: `_alignment.html` renders one component, and what the
state changes is the left-rail truth card (amber `Results not saved` → green
`Saved privately` + chip), the context strip's Session chip value, and the
footer's truth line and action set. Measured at 1440 on the real build:

| | Workbench | Share of frame | Left rail | Right rail |
|---|---|---|---|---|
| Unsaved | 844px | 58.6% | 235px | 211px |
| Saved | 844px | 58.6% | 235px | 211px |
| Saved details | 844px | 58.6% | 235px | 211px |

Image 04 measures 58.6%. Saving moves nothing: no confirmation screen, no
navigation. The save form carries the selected qualification and the applied
filter, and the redirect returns the member to exactly the screen they were
reading.

---

## 4. The filter row (§14-M4)

OS-3 deferred it here because image 05 is its only authority.

- **Placement is image 05's exactly:** below the two count summary cards,
  above the first qualification card, spanning the workbench. Asserted by
  index comparison in `StatusFilterTests`.
- **Styling is image 04's:** a card on the canvas with the room's border,
  radius and small elevation, and a cobalt-underlined active tab. Image 05's
  flatter treatment is not implemented.
- **It filters rows inside BOTH status cards at once**, and reaches neither
  Responsibilities nor Informational statements, which carry no status because
  nothing compared them against anything — and are never merged into one card
  (§14-M14, asserted).
- **The summary cards stay unfiltered.** They are the locked accounting; a
  filtered total would be a different number wearing the same label. Asserted
  by comparing the summary block across filtered and unfiltered renders.
- **Per-card "showing N of M"** appears only while a filter is applied, plus a
  polite `role="status"` announcement naming both cards. A filter matching
  nothing in a card says so rather than leaving an empty table under a heading.
- **Real links**, so it works with JavaScript off exactly as row selection
  does; the room script intercepts them for an instant filter. An unrecognised
  `?status=` falls back to `All` rather than showing an empty table.

One correction after rendering: the `All` tab was a 17px target. It has
horizontal padding now, with the row gap reduced by the same amount so the
drawn rhythm still matches image 05's ~34px between labels.

---

## 5. The SQL gate

Throwaway Basic-tier database `ps-oppslate-004-dev-20260804` on server
`peerslate`, resource group `peerslate`, collation
`SQL_Latin1_General_CP1_CI_AS` — identical tier, server and collation to
production. Engine Microsoft SQL Azure (RTM) 12.0.2000.8. Driver
`mssql-python`, each file executed as one batch exactly as
`scripts/apply_sql_migrations.py` does. **Created for this gate and deleted
immediately afterwards** — confirmed absent from
`az sql db list -g peerslate -s peerslate`. No credential was written into the
repository; the connection string was read from the App Service setting into
memory by a helper that refuses to return a string still naming production.

**The whole chain, not one shape.** Prerequisites (PS-PLAT-000…007,
PS-AUTH-001, PS-WORKSHOP-001) → the OS-1 revision at `a55a4c5`, byte-identical
to what production carries → populated through the real OS-1 procedures with
two owners → the OS-2 revision (`origin/main`) → the OS-3 revision (`7bd18d8`)
→ populated through the real OS-2/OS-3 procedures (reviews, concerns,
statements, a member reclassification, both confirmations, analyses,
responses) → **this** revision.

**53 assertions, zero failures.** Full logs:
`artifacts/2026-08-04-os4/sql-gate/`. Recorded in the migration's own header.

**Byte-for-byte survival, which is the claim that mattered.** A per-row
SHA-256 over every member- and employer-authored column that exists at each
shape — source originals and their digests, member corrections, employer
statement text, proposed and member classes, member clarifications, concern
quotes and resolutions, member responses, and citation
covered-text/excerpt/evidence-identity — was taken before and after each
upgrade and compared:

| Step | Digest before | Digest after |
|---|---|---|
| OS-1 → OS-2 | `FAE0920013C69A3E…F667ED2F` | identical |
| OS-2 → OS-3 | `FAE0920013C69A3E…F667ED2F` | identical |
| **OS-3 → OS-4** | `43120447DD88C3AD…46B366E8` | **identical** |

Row counts unchanged. Post-upgrade: 16 tables, 20 procedures, 92 CHECK
constraints, 61 key constraints, 25 foreign keys, 59 non-clustered indexes,
20 definition-hash properties, every constraint enabled and trusted.

**Saved results and responses survive their own store's lifecycle**, which is
the design point: the saved slate survived a statement correction that deleted
the working analysis, survived the member's explicit working-session delete,
and survived the expiry purge, staying fully readable after all three. That is
why **no existing procedure changed in this revision** — a saved result owns
its own immutable copy instead of pinning ephemeral rows, so no purge or
delete needs conditional retention logic.

Also proved on the engine: every rejection returns before any mutation and
leaves the content digest unchanged (forged key, cross-owner set, stale fence,
malformed fingerprint, over-length idempotency key); idempotent replay returns
`existing`, appends nothing and does not overwrite the stored fingerprint; a
fresh key appends version 2 with version 1 still identifiable; cross-owner
reads return nothing; delete refuses three ways leaving the slate whole, then
removes both versions atomically without touching the other owner's slate; the
owner-isolation verifier returns `verified = 1` across all twenty procedures;
rollback refuses on saved rows, refuses again on working rows, then removes
exactly what it owns leaving the ten prerequisites intact; re-apply from empty
is clean and a second apply is a genuine no-op.

### Two defects the gate found, both invisible to static assertion

1. **`CK_opportunity_saved_qualifications_class` was too narrow.** It pinned
   the two qualification classes on the reasoning that only a qualification is
   ever analysed. The gate hit a raw CHECK violation on a legitimate save:
   `usp_SaveOpportunityAnalysisForOwner` records a result for whatever
   statement the caller names, so a member who reclassifies a statement
   *before* analysing can leave a stored result whose effective class is a
   responsibility. Narrowing bought no safety — the column is a copy of the
   member's own decision, not a rule this room enforces — and cost a save that
   failed with nothing the member could act on. Widened to the full four-class
   enum, with `SAVED_STATEMENT_CLASSES` pointed at the same set so a row the
   database accepts cannot be refused on the way back out.
2. **The verification script did not parse at all.** T-SQL does not accept an
   expression as a procedure argument, and the second save used
   `@IdempotencyKey = CONCAT(@SaveIdemA, N'-2')`. The whole file failed with
   `Incorrect syntax near '@SaveIdemA'`. Fixed with a second variable. The same
   additions also asserted a *global* absence of `dbo.opportunity_slates` in
   two forged-owner checks, which fires on any other member's slate and is not
   something that script is entitled to assert; both are now owner-scoped like
   every other check in the file.

---

## 6. The four persistence lessons, applied

1. **Every rejection returns before any mutation.**
   `usp_SaveOpportunitySlateForOwner` has an easier job than its siblings
   because it *deletes nothing* — saving again appends — so there is no
   previous row to destroy on any path. Every guard still runs before the
   first INSERT, and the gate proved it by digest.
2. **Composite `(id, owner_profile_id)` candidate keys declared up front** on
   all four new tables, before anything references them.
3. **Identity is re-derived server-side, and so is the content.** The save
   procedure accepts **no content payload at all**: it reads the confirmed
   source, the confirmed requirement set, the analysis, its citations and the
   member's responses out of the owner's own rows and copies them. The only
   two values a caller supplies are the idempotency key and the fingerprint,
   and the fingerprint is a derived currency cache rather than a permission —
   a wrong one can make a result look stale, never make a stale one look
   current, because the read side recomputes both sides from server-read facts.
   `SavedSlateServiceTests` asserts the parameter set is exactly those five.
4. **Full `BEGIN TRY / BEGIN TRANSACTION / COMMIT / CATCH + XACT_STATE`** in
   both mutating procedures; owner scope re-asserted in every predicate;
   rowversion fencing on both; rollback refuses on data and drops in FK-safe
   order; all three `usp_` names added to
   `services/database_service.ALLOWED_PROCEDURES`; the ledger description is
   corrected in place on the upgrade path (the guarded UPDATE OS-2 added, which
   now describes OS-1/OS-2/OS-3/OS-4 and twenty procedures).

**What this revision upgrades from, and what it assumes.** Stated in the
migration header: four starting shapes are supported and guarded — empty,
the **OS-1 revision which is what production carries today**, the gated
OS-2 revision, and the gated OS-3 revision. **No existing procedure changes.**
This revision has not been applied to production.

**One deliberate divergence from handoff §8, named rather than slipped in.**
§8 proposed retaining pre-save version rows "pinned by a saved result" when
working data is purged, and a separate `dbo.opportunity_save_requests`
idempotency ledger. Neither is built. The saved result owns its own immutable
copy, so no lifetime is entangled and no purge needs to know what a saved
result still needs; and the idempotency key is a column on the row it protects
with `UNIQUE (owner_profile_id, idempotency_key)` — the key shape §8 specifies,
on the row that cannot outlive or point past what it describes. Same contract,
one fewer coupling and one fewer table that could drift.

---

## 7. Truth, privacy and the public boundary

- **Saving is signed-in only, by construction.** There is no account for an
  anonymous visitor to save into (§18), so the four routes are not merely
  gated — a signed-out caller gets the same neutral 404 a nonexistent path
  gives, the public transport imports none of them, and the anonymous action
  allowlist has no word for any of them (asserted). The preview renders **no
  save control at all**, not a disabled one, and says "Saving is available with
  membership" in its place: a disabled primary reads as a capability being
  withheld, an honest note reads as what it is.
- **Anonymous mode still never reaches the database.** The dual-seam
  assertion — both the route-held service singleton and the shared
  `database_service` the service module would call — is extended to every new
  path: `GET /saved`, and POSTs to `/save`, `/reanalyze` and `/delete`, plus
  the public transport asked for those action words.
- **No overall score, percentage, ranking, recommendation or verdict** at any
  layer, including the four new tables and the new column set. Asserted over
  the room markup at three viewports on the unsaved, saved and stale states,
  and over the saved-details screen; the verifier's concept-level guard now
  also covers the new tables and a wider word list.
- **OS-3's structural control is untouched** — the model still composes no
  prose and status is still derived server-side — and OS-2's prose scan and
  its pinned tests are unchanged.
- **No trust or privacy string moved.** Mechanically verified against the base
  with Jinja comments stripped, and re-verified after the review corrections by
  AST across both modules: the five sentences under Pete's re-acceptance and
  the seven signed-in trust sentences all appear the same number of times, in
  the same files. **Four** *additional* occurrences of "Session private" were
  added, all four in `save_slate`'s error branches and all four in the
  established grammar. (The first version of this line said three; the
  independent review measured it as four, 12 → 16 — finding F10.) Those same
  four branches now choose between `Nothing is saved yet.` and
  `Nothing new was saved. Your saved slate is unchanged.` depending on whether
  the member actually has a saved slate (finding F2). Nothing was reworded or
  removed.

### Copy this slice adds

New, and all of it either quoted from the locked authority or new to a state
that did not exist before:

| Source | Copy |
|---|---|
| Image 05, verbatim | `Saved privately`; `Current for these inputs`; "PeerSlate retained the reviewed source version, confirmed requirements, this analysis, and the authorized evidence snapshot used for it."; "Nothing was published or shared."; `View saved details`; `Done for now`; "Saved privately. Nothing was published, shared, sent to an employer, or used to alter your canonical evidence." |
| Image 09-c, verbatim | `Inputs changed · Reanalysis required`; "The saved result remains available for Source Version N."; "It does not apply to your changed inputs."; `Reanalyze`; `View saved result` |
| Image 09-d, verbatim | "We couldn't delete this saved slate."; "It remains saved privately. Nothing was removed."; `Try again`; `Cancel` |
| Image 05's meaning, corrected typography (§14-M11) | "Saving retains your current reviewed inputs. It does not publish anything, and it does not change your qualification accounting." — image 05's own line ends "It does not publish in qualification accounting", which is an AI-generation artifact rather than a sentence |
| New, for states no image draws | the saved-details screen's headings and rail copy; the delete confirmation; the filter row's "showing N of M" and its empty state; the honest public save note |

**One user-visible sentence changed rather than added.** `ALIGNMENT_SAVE_NOTE`
read "Saving this analysis privately arrives in a later update. Nothing is
waiting behind this button, and nothing has been saved." That was true of OS-3
and is false now, in the same way OS-2's "nothing is analyzed" was. It now
reads "Saving keeps this result in your private account. It publishes nothing
and shares nothing." It is a build-status sentence, not one of the five under
re-acceptance. The inherited comment in `_alignment.html` that closed with
"`Save privately` is inert until slice OS-4, so nothing here is an action a
member can complete too early" is likewise retired rather than left to
mislead; the placement argument it supported stands on its own two measured
reasons.

---

## 8. Visual parity, honestly

Method: the owner's. Render the real page, put it beside the locked mockup at
full width, judge it critically, correct the drift, re-render, repeat. Five
corrections came out of that and are listed in
[`evidence/os-4/EVIDENCE_MANIFEST.md`](evidence/os-4/EVIDENCE_MANIFEST.md).

| Viewport | Assessment |
|---|---|
| **1440 desktop** | Close. The saved state carries image 05's content and actions inside image 04's measured geometry — same workbench width, same rails, same cards, same table. Two deliberate departures from image 05, both required: its stacked full-width summary cards are its prohibited geometry, and its merged Responsibilities/Informational card is prohibited by §14-M14. The filter row sits where image 05 puts it in image 04's card grammar rather than as a bare strip, because on this screen everything is a card on the canvas. |
| **390 phone** | Reads as the same product. The rails stack in reading order, the table restacks per qualification, the filter tabs wrap to two lines, and the stale card fits its rail. There is no mobile authority (§14-M9), so this is a judgement, not a match. |
| **320 narrow** | Same, with the room's existing 320 padding step. No overflow at any of seventeen widths. |
| **200% zoom (640 CSS px)** | Single-column flow, everything reachable. |

Contrast: no failures at 1440/390/320 across the saved, stale, filtered,
saved-details and delete-failed screens. Touch targets: none below 24×24 after
the two corrections; the three native radios in OS-3's response rail measure
13×13 as glyphs but each sits inside a `<label>` measuring 303×73, which is
the target a member hits.

**`--os-card-gap` is unchanged.** The written 12px rule and the images'
measured ~24–28px disagree, and that is an open owner decision across all four
primaries. This slice does not settle it by stealth.

**Where I am least confident, and why Pete should look hardest:** the saved
details screen has no image authority at all (§14-M13a). It is built strictly
from the room's existing grammar — same shell, same rails, same workbench
cards, same status pills, same excerpt treatment, the house confirm pattern —
and introduces no new composition, hierarchy or interaction language. But it
is a screen nobody has drawn, and it is the item in this set most in need of
his eye.

**One structural note, offered rather than acted on:** the alignment screen's
heading order is `h1` → `h3` (its summary and qualification card titles are
both `h3`). That is OS-3's shipped structure and I did not change it — it is
not this slice's file to churn, and a heading-level change ripples into OS-3's
own assertions. The new saved-details screen is `h1` → `h2` → `h3`. Worth a
small follow-up in whichever slice next owns that partial.

---

## 9. Tests

| Suite | Result |
|---|---|
| `tests/test_opportunity_slate.py` | **167**, OK — 80 at the base, 61 for OS-4, **26 more for the review corrections** |
| `tests/test_opportunity_slate_ai.py` | 143, OK — unchanged in count; two inherited assertions were rewritten where OS-4 retired the inert save control |
| `tests/test_opportunity_slate_migration.py` | **73**, OK (1 skipped — the engine-backed gate, run separately above); three constants and two assertions extended for the four new tables and three new procedures, **plus 4 for findings F6, F7 and F9** |
| `tests/test_site_rules.py` + `tests/test_governance_pointers.py` | 33, OK |
| **Full suite** | **2171 passed, 7 skipped** |

**30 tests were added by the review corrections.** In
`test_opportunity_slate.py` (26): the content digest including its collision
resistance (5), the four in-place-edit currency cases at the unit level (4),
currency rendered on both real screens in both directions (5,
mutation-checked against the pre-fix rule), the save-failure truth line across
all three reachable statuses (3), the delete-failure currency both ways (2),
version distinguishability and the truncated-count contract (4), and the
saved-slate read seam including the F6 refusal (3). In
`test_opportunity_slate_migration.py` (4): the currency kind predicate, the
probe's lock hint, the unique-violation catch, and the corrected header shapes.

The 61 new tests, by contract: input fingerprint (4), saved-state resolution
(5), currency both ways (6), the saved/unsaved/stale workbench (6), the filter
row (8), the save route including idempotent replay and the
nothing-to-save/conflict/unavailable contracts (6), reanalyze including "no AI
step runs from a render" (2), delete atomicity and the delete-failure contract
leaving the slate visibly saved (4), saved details (6), the signed-in-only and
flag-off boundary including the dual-seam assertion (7), and the persistence
seam (7). Everything is mocked at the Anthropic boundary; no test makes a
provider call.

---

## 10. Status

- Not deployed. `PEERSLATE_OPPORTUNITY_SLATE_ENABLED` remains off.
- The migration ships as `proposed/` and is applied nowhere by this branch.
  **Production carries the OS-2 revision**, applied 2026-08-04 11:41 UTC under
  explicit owner authorization and verified; the apply record is the commit on
  `work/2026-08-04-oppslate-os2-prod-record`. The OS-3 and OS-4 revisions are
  gated and unapplied. (This paragraph said "the OS-1 revision" until the
  independent review caught it — finding F9. It was true when the slice was
  written and stopped being true hours later; the migration header carried the
  same error and is corrected in the same commit.)
- No PR is open. Pete's visual acceptance has not been given.
- Independent review is a Protected trigger for this slice (deletion
  behaviour, handoff §16). **It has now been run, and its ten findings are
  resolved in §11.**

---

## 11. Independent review, 2026-08-04 — what it found and what changed

The review examined this branch at `8b0db12a7a8486f63448309c9dab95cee5617590`.
It endorsed the copy-versus-pin deviation and verified in SQL that no cascade
can reach a saved row and that the snapshot is genuinely immutable; it
confirmed deletion atomicity, rejection-before-mutation across all twenty
procedures, the dual-seam public boundary, the no-aggregate guards and
migration hygiene. None of that changed here.

It also made the observation that shaped the F1 fix: **copying raises the
stakes on currency.** Under pinning, a wrong "current" label at least pointed
at live rows. Under copying, the member is reading retained old wording that
the banner calls current. Currency is the price of the copy model, and this
slice had not fully paid it.

### F1 — HIGH. "Current for these inputs" survived two ordinary member actions

Both routes the review offered were considered. **The cheap one does not
actually close it**, and that decided the fix:

> A source correction clears `opportunity_sources.confirmed_version_number`,
> and a statement correction clears the requirement set's. Refusing "current"
> while either is NULL closes the window *until the member re-confirms* — and
> re-confirming writes `confirmed_version_number = current_version_number`
> **without moving the version**. The false "current" then comes back
> permanently, over wording the member changed. A confirmation-state guard is
> a good backstop and a bad answer.

So the fix is the content route, and it needed **no schema change**, because
the copy model already pays for it: the snapshot owns the confirmed source
wording and each qualification's ordinal, class and employer text, so the
pinned side of the comparison is recomputable from the saved row itself.

`compute_content_digest` hashes two facts a member can rewrite in place:
the confirmed source wording (`working.display_text` — the same COALESCE the
save procedure copies), and the analysed statement set as
`(ordinal, class in force, employer text)`, built by running the real
`_qualifications_for_analysis` filter so the signature cannot drift from the
set actually analysed and saved. Employer text is *hashed*, not concatenated,
so no statement containing the canonical string's own delimiters can be made
to collide with a different reading. It becomes a fourth component of
`compute_input_fingerprint`, and `_FINGERPRINT_VERSION` moved to
`os4-input-fingerprint-v2` so every digest stored under v1 falls out to stale
— the conservative direction the versioning was designed for.

The confirmation guard is kept **as well**, as `inputs_confirmed`, and named
in the code as a structural backstop rather than the answer: it costs a member
at worst one unnecessary reanalysis, it catches any future in-place mutation
the digest has not been taught about, and that is exactly how F1 happened.

`member_clarification` is deliberately **excluded**, and the reason is
recorded in the function: it is not sent to any AI step
(`_qualifications_for_analysis` passes ordinal, employer text and clause
vocabulary only), and it is not part of what a saved result holds, so changing
it cannot make a saved result wrong. The un-confirmed state it produces is
still refused by the backstop.

One honest consequence, named in the code: the route reads the source wording
a moment before the procedure copies it, so a correction landing between them
makes the stored digest disagree with the stored snapshot. `pinned_fingerprint`
catches that and reports stale. The race lands on the safe side, never on a
false "current".

**Rendered proof, both directions.** `CurrencyRenderTests` renders the actual
screens — `GET /opportunity-slate?step=alignment` and
`GET /opportunity-slate/saved` — not the function, because the defect was that
the screens *said* "current":

| Case | Alignment | Saved details |
|---|---|---|
| Untouched inputs | `Current for these inputs` | `Current for these inputs` |
| Source wording corrected in place | `Inputs changed` | `Inputs changed` |
| Statement reclassified in place | `Inputs changed` | `Inputs changed` |
| Reclassified **then re-confirmed** | `Inputs changed` | `Inputs changed` |
| Reading un-confirmed, content unchanged | `Inputs changed` | `Inputs changed` |

And the tests were mutation-checked against the pre-fix rule: with
`is_current_for` reduced to the v1 behaviour, all four staleness cases fail on
both screens (8 subtest failures) while the positive case still passes — so
the suite is not passing by making everything stale.

### F2 — MEDIUM. A failed re-save told a member with a saved slate "Nothing is saved yet."

All four save-failure branches now call `_nothing_saved_truth(identity)`, which
reads the member's actual saved state and returns either the established
`Session private • Nothing is saved yet.` or a new
`Session private • Nothing new was saved. Your saved slate is unchanged.` One
extra read, on a failure path only, buys a screen that does not argue with
itself. Asserted on all three reachable statuses (503, 409, 400) in
`SaveFailureTruthTests`, and shown in `member-16/17`.

### F3 — MEDIUM. Saved versions were not distinguishable from each other

Source version, save minute and qualification count are all shared between two
saves of the same inputs, so the rail rendered byte-identical entries — the
review's own copy of `member-09` shows two. `SavedVersionView.save_version_number`
already existed and was never rendered. Each entry now leads with `Save N`,
unique per slate by construction, with the source version and count below it.
Leading with it also stops the heading wrapping at rail width. Asserted by
extracting the rendered labels and requiring three distinct ones.

### F4 — LOW. A failed delete relabelled a current saved result as stale

`_reload_saved_details_for_error` passed `is_current=False` unconditionally, so
a member whose delete failed on an unchanged result was told "Inputs changed ·
Reanalysis required" and "It does not apply to your changed inputs" — both
false, on the one screen whose job is to be believed after a failure. It now
re-reads the working session and requirement set and computes real currency
through the same `_saved_currency` helper the other two screens use. A read
failure there still resolves to "not current", which under-claims. Both
directions asserted.

### F5 — LOW. The delete confirmation quoted the truncated count

`MAX_SAVED_VERSIONS_LISTED = 50` caps the rail; delete removes **all**
versions and nothing caps saving. `SavedSlateView` now carries
`total_version_count` from the slate's own `current_save_version_number`
(already in the result set — no SQL change), the confirmation quotes it, and
the rail says "Showing the 50 most recent of 64 saved versions." when the two
differ. `member-18`.

### F6 — LOW. The currency join could not price a Moment citation

`opportunity_saved_evidence.evidence_kind` permits `moment` for handoff
§17-Q2, but the currency query reads `knowledge_items` only. Latent today, and
the failure mode when Moments arrive is the quiet kind: a saved slate reading
"Inputs changed" permanently, with no member action able to clear it. Two
halves, both required:

- the procedure's currency join is now explicitly predicated on
  `evidence_kind = N'knowledge_item'` and emits the kind;
- the service refuses any kind outside `SAVED_EVIDENCE_CURRENCY_KINDS` with
  `code="invalid"` rather than showing that permanent staleness — the same
  "a trustworthy failure beats a plausible screen" rule the module already
  applies to a saved result that disagrees with itself.

Unreachable today (AI step 3 stores the literal `knowledge_item`) and a
tripwire for the slice that adds Moment grounding: it must widen both.
**Proved on the engine**: with the pinned reference re-labelled `moment` and
its key deliberately colliding with a real confirmed knowledge item, the read
reported `moment` / `current_version = NULL` rather than resolving it against
that item.

### F7 — LOW. The idempotency probe could lose its own race

The probe ran without a lock hint, so two simultaneous requests with the same
key could both miss it; the loser hit the unique index and surfaced as a 503 —
telling the member the save failed when it had succeeded. The probe now holds
`UPDLOCK, HOLDLOCK` over `(owner_profile_id, idempotency_key)`, and the CATCH
additionally converts error 2601/2627 into the `existing` outcome a sequential
replay returns.

**This is the finding the gate reproduced.** Four connections released
together on one barrier, five times each, against both revisions:

| Revision | Result |
|---|---|
| Pre-fix (`8b0db12`) | **4 of 5 races raised** `Violation of UNIQUE KEY constraint UQ_opportunity_saved_results_idempotency` |
| This revision | 5 of 5 returned one `success` and three `existing`, naming the same `saved_result_key`, one row per key |

### F8 — LOW, evidence. Every `member-*` frame rendered the signed-out shell

The capture patched only the room's identity, so `base.html` read
`get_optional_principal()` and drew a Sign In button no signed-in member sees.
Both are patched now and **every `member-*` frame is re-captured**: each
carries `data-ps-auth-state="authenticated"`, renders My Slate and Sign out,
and hides Sign In, asserted inside the harness so a future frame cannot
regress. Re-measured after the re-capture on all seven states: no overflow at
17 widths, no contrast failure at 1440/390/320, no sub-24px target except the
pre-existing OS-3 native radios.

### F9 — INFORMATIONAL. The migration header named the wrong production shape

Corrected in §10 above and in the header itself: shape C is now "WHICH IS WHAT
PRODUCTION CARRIES TODAY", shape B no longer claims it, and the correction
says why a header that disagrees with the database in front of an operator is
worse than no header. Pinned by a migration test that reads each shape's block
separately.

### F10 — INFORMATIONAL. The "Session private" count was wrong

The report said three additional occurrences; measured base→head it is
**four** (12 → 16), all in `save_slate`'s error branches. All four are the same
four F2 rewrote, so they now read
`Session private • Nothing new was saved. Your saved slate is unchanged.` when
a saved slate exists. §7's paragraph is corrected.

### What was NOT disturbed

The copy model, the deletion contract, the dual-seam boundary, the
no-aggregate guards, OS-3's structural control and OS-2's prose scan are
unchanged. `--os-card-gap` is unchanged (open owner decision). The filter row
is unchanged. No new dependency, no dark-theme rule.

**Not one user-visible string constant changed.** Verified by AST across both
modules: 71 → 72 constants in `opportunity_slate_routes.py`, zero changed,
zero removed, one added (`TRUTH_NOTHING_NEW_SAVED`, F2); in
`services/opportunity_slate_service.py` the only changed constant is
`_FINGERPRINT_VERSION`, which is not user-visible. The five re-accepted
privacy sentences and the seven signed-in trust sentences were separately
counted per file against `8b0db12` — all identical, same counts, same files.
