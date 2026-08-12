# Opportunity Slate Replacement — Technical Architecture

Date: 2026-08-11
Author: Claude (architecture role, assigned by Pete)
Status: Design only. This document authorizes no repository write, branch, migration, deployment, or release. Implementation follows then-current governance (START_HERE, baseline, lanes, delivery preflight, a newly activated package).

---

## 0. How to read this document

Every load-bearing claim is tagged with exactly one provenance marker:

| Tag | Meaning |
|---|---|
| `[OBSERVED]` | Read directly from a locked image or the controlling 2026-08-09 review PDF. |
| `[OWNER]` | An explicit Pete decision (2026-08-11 set unless dated otherwise). Latest wins. |
| `[LOCKED]` | Required by the exact hash-pinned visual files (`ASSET_SHA256SUMS.txt`) — the nine `final-mockups/` files plus the two `locked-references/` files. |
| `[REPO]` | Verified against `origin/main` of the Azure DevOps repository (deployed main `aa4a4ec6…`, pipeline 722, live release `689d0be742c2c8d02c585827`). |
| `[PROPOSED]` | My architecture decision. Implementable without further approval unless flagged otherwise. |
| `[OPEN]` | An unresolved owner decision. Listed in Section 13. Never silently chosen here. |

Controlling authorities, in precedence order:

1. Pete's 2026-08-11 owner decisions (replacement not evolution; sign-in only; locked mockups; controlling PDF; avoid-list; truth-type separation; zero-evidence rule; AI-proposes-people-decide; light-only theme). `[OWNER]`
2. The 11 hash-pinned visual files. `[LOCKED]`
3. `PeerSlate_Independent_Visual_Experience_Review_2026-08-09.pdf` — CONTROLLING visual/experience authority, not advisory. `[OWNER]`
4. Repository trust invariants that survive the replacement: no score/rank/recommendation at any layer, authorization-before-retrieval, additive-only schema, append-only saved versions, explicit reanalysis, no silent consequential action. `[REPO]` `[OWNER]`

---

## 1. Reconciliation: what is superseded, and why

The 2026-08-10 architect handoff remains the factual floor for functions, states, cardinality, truth classes, and the AI contract. The following of its framings are superseded:

| # | Superseded item | Superseded by | What survives |
|---|---|---|---|
| 1 | Public anonymous + member dual mode (signed context tokens, demo evidence fixture, sessionStorage rehydration, public caps 40/12, spend-guarded public AI). | `[OWNER]` Opportunity Slate stays behind sign-in; no public trial now. | The anonymous safeguards remain reference patterns if public exposure ever returns. The signed-in intake/SSRF/upload contracts still bind. |
| 2 | "Evolve and protect every current function" mandate. | `[OWNER]` The experience is REPLACED, not evolved. | Production data preservation, additive-only schema, all trust/truth invariants, and a deliberate function retirement matrix (Section 11) so nothing is dropped by accident. |
| 3 | 2026-08-02 ChatGPT visual lock (images 01–10, image-04 exact geometry, 24px card-gap ruling, mismatch register M1–M19, `--os-*` palette). | `[OWNER]` The nine `final-mockups/` files + two `locked-references/` files, hash-pinned, are the visual truth; the 2026-08-09 PDF is controlling. | The behavioral truths those old images encoded (failure copy discipline, read-only-during-analysis, saved-vs-currency) survive as product rules, not pixels. |
| 4 | 2026-08-10 banked alignment-concept JPG as "the direction" (qualification ledger + inline row expansion + evidence connector line). | `[OWNER]` `[LOCKED]` The locked set depicts a guided per-qualification workroom, not a ledger with inline expansion. | The banked function map's *inventory* — every real function it listed is dispositioned in Sections 5 and 11. |
| 5 | The review PDF treated as advisory (precedence rank 5 in the old source index). | `[OWNER]` It is controlling. | — |
| 6 | Old open decision #1 (public vs sign-in), the Q3 public entry point, "Back returns to site root", noindex-because-public. | `[OWNER]` Sign-in-first. Entry point, nav presence, and gate presentation are re-decided (partly `[OPEN]`, Section 13). | `noindex` headers stay — private content is never indexable. `[PROPOSED]` |
| 7 | "Runtime standardizes on claude-haiku-4-5; implementer selects tier" language. | `[OWNER]` OS-2 precedent: Sonnet 5 for statement interpretation on measured evidence; select per-step on evidence; never promise a third party's retention behavior. | — |
| 8 | Journal as an adjacent concern. | `[OWNER]` Journal is backburnered and NOT a dependency. Evidence sources are Workshop/My Knowledge (and, contractually reserved, Moments). | — |
| 9 | The old elevated-card visual grammar. | `[OWNER]` Avoid list: no blue-dominant theme, no giant floating cards, no card soup, no sparse full-screen prompts, no tiny all-requirements list dumps. Preserve the earned three-zone workroom. | — |
| 10 | The five-kind response model (Tell us more / Connect existing evidence / Provide a real example / Confirm I do not have this / Skip) as the response UI. | `[LOCKED]` The locked set shows a three-option "Your take" + one free-text response with dictation. | The old `opportunity_responses` rows are preserved as production data (Section 6.7). The functional retirement is deliberate — see Section 11 rows 6–8 and open decision D-8. |

Everything not listed above from the handoff digest — the state inventory, cardinality matrix, twelve truth objects, AI validator discipline, production schema — carries forward unchanged.

---

## 2. Product model of the replacement

The replacement is a private, signed-in, evidence-backed workroom for one member-brought role at a time, delivered as one continuous plane that transforms through five stages `[LOCKED]` `[OBSERVED]` (PDF dominant-plane rule 5: advance transforms the same plane, never a new collection of cards):

1. **Bring in a role** — paste/type/dictate, upload PDF/DOCX/TXT, or import a public link. Nothing is interpreted until the member reviews the captured source. (Image 04.)
2. **Review captured source** — member checks employer, role title, and the captured wording; corrects capture errors; explicitly confirms. Requirements remain visibly "not organized" until then. (Image 05.)
3. **Review requirements** — PeerSlate proposes an organization of the confirmed source into Required qualifications / Preferred qualifications / Responsibilities / Informational statements; the member reviews each statement (Accurate / Needs correction / Not a requirement), corrects organization in a right inspector, and explicitly confirms the set. (Image 06.)
4. **Qualification review (alignment)** — a guided walk through the qualifications, one dominant qualification at a time, with sections A–F: Employer wording; Your take; your own-words response; Evidence PeerSlate matched; PeerSlate finding (three states only); What remains unestablished. A conditional evidence inspector (desktop rail / mobile full-screen sheet) opens only on selection. (Images 01, 02, 03, 07, 08, 09, 10, 11.)
5. **Save and revisit** — explicit private versioned snapshot save, history, staleness, reanalysis, deletion. No locked visual exists for this stage yet; it is architecturally specified here (Section 6.8) and its composition goes to the ChatGPT visual lane (Section 10). `[OPEN]` for composition, not for behavior.

Non-goals (unchanged, binding): no job board, no scoring or ranking, no employer surface, no hiring recommendation, no aggregate fit number anywhere including API and DB, no AI chat, no auto-application, no silent truth change. `[OWNER]` `[REPO]`

The four owner truth types map onto the twelve handoff truth objects as follows `[OWNER]` `[PROPOSED]`:

| Owner truth type | Contained objects |
|---|---|
| Employer source | Verbatim original text and captured versions; source identity as captured. |
| PeerSlate organization / findings | Normalized display wording; AI proposals (concerns, interpretation, citations); server-derived statuses, rationale, unestablished gaps; projections. |
| Member response | Member corrections (source, identity, organization), Your take, own-words response, explicit confirmations, saved-snapshot decisions. |
| Authorized evidence | Workshop/My Knowledge items at exact versions; bounded excerpts pinned inside analyses and snapshots. |

No object may silently move between rows of that table. AI proposes; the member decides; the server derives findings only from validated citations. `[OWNER]`

---

## 3. Shell, navigation, and access

- Global header: PEERSLATE wordmark; nav Pete's Slate / Community / Interview Studio / Workshop / Opportunity Slate (active, underlined); account menu "PC / Pete Carter". `[OBSERVED]` (all desktop images). The mobile shell is only PEERSLATE + "Opportunity Slate" local label + account menu — the full nav is deliberately absent on mobile `[LOCKED]` (images 07–11; VISUAL_AUDIT item 10 required this refinement).
- Route stays `/opportunity-slate` `[PROPOSED]` — the route-name guardrail (never `/job`, `/jobs`, `/hiring`, `/listing`) is test-enforced `[REPO]`.
- Access: server-derived identity on every request; anonymous requests to any replacement surface receive the site-standard sign-in gate (redirect to sign-in with return target), never a partial page. Flag-off remains a neutral 404 indistinguishable from not-found. `[PROPOSED]` `[REPO]`
- Every response: `Cache-Control: private, no-store` and `X-Robots-Tag: noindex, nofollow, noarchive`. `[REPO]` `[PROPOSED]` (retained deliberately even though the public rationale is gone — private workroom content must never be cacheable or indexable).
- The cutover that makes the live route sign-in-only is a route-gate flip and therefore triggers Pete's 2026-08-02 two-mode audit entry gate before it happens. `[REPO]` (recorded in PS-OPPORTUNITY-SLATE-001 §18). Scheduled in slice R5, Section 14.
- Light theme only; no new dark rules authored; existing dark rules not ripped out. `[OWNER]`

---

## 4. Visual lock → contract map

Every depicted field, label, state, action, rail, inspector, and sheet across the 11 files, mapped to its data/state contract. Fixture content (Meridian Aerospace, Pete's response text, dates) is fixture, never product logic. `[OBSERVED]` throughout; contract column is `[PROPOSED]` unless marked.

### 4.1 Image 04 — Desktop first arrival ("Bring in a role.")

| Depicted element | Contract |
|---|---|
| Eyebrow `START AN OPPORTUNITY`, H1 `Bring in a role.`, intro copy ending "You'll review the captured source before PeerSlate organizes any requirements." | Static stage-1 copy. Renders only when the member has no working opportunity. One dominant purpose; no left rail, no inspector exists at this stage `[LOCKED]`. |
| `Paste or type the job posting` textarea with placeholder `Paste the complete job posting or role description here...` | Uncommitted client-side draft. Limit 20,000 UTF-16 units (existing source cap `[REPO]`). Nothing persists until `Review source`. |
| `Dictate` button (mic icon) inside the textarea | Shared dictation module `static/js/dictation.js` `[REPO]`: voice and text edit the same field, explicit start/stop, silence timeout never submits, `aria-pressed`/`aria-live`, honest unavailability when the browser lacks speech support. |
| Helper `Keep the employer's original wording whenever possible.` | Static copy; encodes the verbatim-source truth rule. |
| Right column eyebrow `BRING THE SOURCE ANOTHER WAY`; `Upload a document — PDF, DOCX, or TXT` row with chevron; `Import a public link — Use a publicly accessible job-posting page` row with chevron | Entry points to the two alternate capture methods. Upload: native file picker then inline processing row (no locked visual for in-flight state; Section 10 row N-3). Import: small bounded temporary surface for URL entry (Section 10 row N-4). Both reuse the hardened OS-6 intake service verbatim: MIME allowlist, magic bytes, bounded read, structure-only parsing; https-only, public-unicast IP pinning, redirect re-validation ≤3, size/time caps, content-as-data `[REPO]`. |
| Footer truth line `Nothing is interpreted until you review the captured source.` | The stage-1 page-level truth statement (PDF rule: one page-level truth statement `[OBSERVED]`). |
| `Review source` primary button, disabled while input is empty `[LOCKED]` (VISUAL_AUDIT item 04) | POST creates working session + source + version 1 (`capture_method` = pasted/dictated/uploaded/imported), computes sha256, transitions to stage 2. Idempotency key per submission `[REPO]`. |

### 4.2 Image 05 — Desktop review captured source

| Depicted element | Contract |
|---|---|
| Left rail `Current opportunity` → `Meridian Aerospace` / `Senior Systems Engineering Manager` | Source identity (employer, role title) from the identity record (Section 6.2). Before the member enters them, the rail shows honest placeholders ("Employer not entered yet") — no locked visual conflict; the rail simply reflects the record. |
| Rail `Captured role source · Version 1`, `Captured Apr 30, 2025` | `opportunity_sources.current_version_number` + version `captured_at_utc` `[REPO]`. Label is `Captured` pre-confirmation and `Confirmed` after (images 01/02 show `Confirmed role source · Version 1`) — the label is a truth state, not decoration `[LOCKED]`. |
| Rail section `CURRENT REVIEW` → `Source wording`, `Requirements not organized` | Stage indicator. `Requirements not organized` is the truthful pre-interpretation state `[LOCKED]` (VISUAL_AUDIT item 05: "requirements remain explicitly unorganized"). |
| H1 `Review captured source` + subtitle | Stage-2 heading. |
| `A. Source identity`: `Employer` text input, `Role title` text input | Member-entered structured metadata, stored per source version (Section 6.2). MVP: member-entered, optional, prefill absent. AI prefill is a separate later proposal — D-6 `[OPEN]`. |
| Meta row `Source type — Job posting`, `Version — Version 1`, `Captured — Apr 30, 2025` | `source_type` (identity record, default `job_posting`), version number, capture timestamp. Read-only. |
| `B. Captured wording` + helper `Correct only the captured details or wording. Keep the employer's wording intact wherever possible.` | Editable document area rendering `member_corrected_text ?? original_text` `[REPO]`. `original_text`/`original_sha256` are write-once `[REPO]`; member edits write `member_corrected_text` only. Employer wording and member correction never overwrite each other. |
| Footer `Back` link | Returns to stage 1 with the captured source intact (replace/delete requires explicit confirmation — Section 6.9). |
| Footer truth line `PeerSlate will organize requirements from this exact source only after you confirm it.` | Consequence-specific truth at the commit point (PDF rule 7 `[OBSERVED]`). |
| `Confirm source` primary button | Sets the confirmation triple at exactly the current version; any later wording edit clears it (CHECK-enforced `[REPO]`). Confirmation gates interpretation. |

Not depicted but required at this stage: AI wording concerns (extraction uncertainty). Deliberately deferred — Section 10 row N-6 and decision D-7 `[OPEN]`.

### 4.3 Image 06 — Desktop review requirements + correction inspector

| Depicted element | Contract |
|---|---|
| Left rail: `Confirmed role source · Version 1`, `Review source` (pencil action) | Post-confirmation source state; `Review source` returns to stage 2 (a wording edit there clears confirmation and invalidates the requirement set — Section 6.5). |
| Rail `REVIEW SECTIONS`: `Required qualifications 8 — Current`, `Responsibilities 3`, `Informational statements 2`, `Final check` | Section counts by proposed/member class. Counts are category counts only — never mixed with finding counts `[OBSERVED]` (PDF; old open decision 9 resolved by this rail). `Preferred qualifications` appears as its own row when present (fixture has none) — count-driven rendering, minimal extension of the locked pattern, flagged Section 10 row N-8. `Final check` is the confirm step (Section 10 row N-7). |
| H1 `Review requirements`, `12 of 13 reviewed` + progress bar | Reviewed count = statements with a current review decision; total = all statements in the proposed set (8+3+2 = 13 in fixture). The bar is the locked high-count degradation of the dot stepper. |
| Eyebrow `CURRENT REVIEW`, statement title `Agile / SAFe delivery experience` | The selected statement's organized label (member-corrected organized wording once applied, else the proposed label). |
| `A. Employer wording` | Verbatim `employer_text` span from the confirmed source `[REPO]`. Never editable. |
| `B. PeerSlate organized it as`: rows `Organized requirement` and `Category` | The current organization: proposed values or, after correction, the member's decision columns. AI proposal and member decision remain separate columns `[REPO]`. |
| `C. Your review`: segmented `Accurate` / `Needs correction` (selected, check) / `Not a requirement` + helper `Your correction changes PeerSlate's organization, not the employer's source.` | Per-statement review decision (Section 6.3). `Not a requirement` excludes the statement from the confirmed set (it never enters analysis) while preserving the row and its history — a deliberate remove, not a delete of employer wording. |
| `D. Source location`: `Confirmed role source · Version 1`, `Required qualifications · Item 1`, `Captured Apr 30, 2025`, `View source in context` link | Provenance from `span_start`/`span_length` + section/ordinal `[REPO]`. `View source in context` opens the confirmed source scrolled/highlighted to the span — read-only view, focus returns on close. |
| `E. Review status`: badge `Needs correction` + helper `Apply the correction in the inspector before confirming this requirement.` | Status = review decision state. A `needs_correction` decision without an applied correction blocks that statement's completion; text + shape, never color alone. |
| Footer `Back`; `Confirm requirements` (disabled) | Confirm enables only when every statement has a completed review (accurate, corrected, or excluded). Confirming freezes the member-confirmed requirement set version and triggers analysis (Section 6.2); afterwards this stage is reachable read-only with a `Revise requirements` action (Sections 6.5a, N-16). |
| Right inspector `Correct requirement` with `×` close; context `Required qualification 1 of 8` | Conditional inspector, exists only because a `Needs correction` selection earned it `[LOCKED]`. Focus moves to its title on open and returns to the invoking control on close (VISUAL_AUDIT item 09 rule generalized `[PROPOSED]`). |
| Inspector `SOURCE WORDING`: quoted employer wording, caption `From the confirmed role source` | Read-only verbatim span. The quote border marks employer truth `[LOCKED]`. |
| Inspector `ORGANIZED WORDING`: editable text box showing the pending correction | Pending member correction of the organized label (≤1,200 units, the requirement cap `[REPO]`). `Apply correction` stays disabled until a pending change exists `[LOCKED]` (VISUAL_AUDIT item 06 was refined for exactly this). |
| Inspector `CATEGORY` dropdown `Required qualification` | Reclassification among the four CHECK-pinned classes `[REPO]`. |
| Inspector helper `Correct PeerSlate's organization without changing the employer's source.` | Truth-boundary copy. |
| Inspector footer `Cancel` / `Apply correction` | Cancel discards the pending edit (no confirmation needed — nothing committed). Apply records a review event (Section 6.3), updates the center, sets status to corrected. |

### 4.4 Images 01 / 02 — Desktop qualification review (locked references)

| Depicted element | Contract |
|---|---|
| Left rail `Current opportunity` block; `Confirmed role source · Version 1`; `Captured Apr 30, 2025`; `Review source` | As above. Entering `Review source` from here warns that a wording change will invalidate the confirmed requirements and current analysis (Section 6.5). |
| Rail `Required qualifications` numbered list 1–8, chevron per row, row 2 highlighted with left bar | Qualification navigator: all analyzed qualifications, ordinal = presentation order (numbers are order, not identifiers — resolves the banked-map ambiguity `[PROPOSED]`). Click/Enter selects that qualification into the dominant plane. `aria-current` on the active row. With Preferred present, a second `Preferred qualifications` group renders below (Section 10 row N-8). |
| Center H1 `Required qualifications`; `Qualification 2 of 8`; 8-dot stepper (done = filled check, current = ring, rest empty) with numerals | Guided-flow progress. Done = member has continued past that qualification (Section 6.7). The stepper is decorative-plus-text: at 320px it collapses to text only `[LOCKED]` (image 11), and above ~12 qualifications it degrades to the `N of M` text + progress bar exactly as image 06 does at 13 items `[PROPOSED]` — a locked-set-internal pattern, not an invention. |
| Eyebrow `CURRENT REVIEW`; qualification title | Organized label of the selected qualification. |
| `A. Employer wording` | Verbatim employer text. |
| `B. Your take`: three options `I've done this` / `I've done something related` (selected, green check) / `I haven't done this yet` | Member self-assessment, a member-truth field (Section 6.4). Radiogroup semantics; optional — the member may continue without choosing. Never enters the AI grounding allowlist and never changes the finding `[OWNER]`. |
| `C. Describe what's relevant in your own words`: textarea, `Dictate`, counter `299 / 4,000`, status `Response reviewed ●`, helper `Your response is specific to this opportunity. It does not change your evidence or the current finding automatically.` | Member response (Section 6.4): ≤4,000 units, typed/dictated into one field, explicit review commit sets `Response reviewed`. The helper is the binding non-consequence contract `[LOCKED]`. The commit control for a dirty draft is not depicted — Section 10 row N-9. |
| `D. Evidence PeerSlate matched` + `Select an item to inspect its supporting excerpt or excerpts.`; evidence rows `Systems Engineering Experience Summary · Version 3 / Updated Mar 15, 2025` (image 01: highlighted, `Viewing` label) and `Program Delivery Notes · 2024 · Version 1 / Updated Dec 10, 2024`, chevrons | Server-derived citation groups: one row per distinct evidence item cited for this qualification, pinned title + exact version + item's last-updated date. Row count = distinct items (not citation count — resolves the banked-map "evidence count" ambiguity `[PROPOSED]`). Selecting a row opens the inspector (desktop rail, image 01) or the full-screen sheet (mobile, image 09); the selected row shows `Viewing` `[LOCKED]`. |
| `E. PeerSlate finding · Current analysis`: diamond glyph with center dash; `Partially supported`; rationale `Cited for "leading Agile delivery in a SAFe environment" and "PI planning." The matched evidence does not establish direct ownership of PI planning and ART-level coordination, or when the work occurred.` | The derived status (three values only `[REPO]`) with its shape glyph (dash = partial; filled check = supported per stepper vocabulary; empty diamond = not enough information per image 03/10) — status is never color alone `[OBSERVED]`. The rationale is server-composed from validated citations: `Cited for` + the citations' verbatim `covered_text` quotes; the gap sentence names each uncovered clause by its member-confirmed **clause display phrase** (Sections 6.2 and 7) — image 01's `or when the work occurred` is the display phrase of an uncovered temporal clause, confirmed with the requirement set, not analysis prose. No alignment-run prose reaches this line (Section 7). `· Current analysis` is the currency tag; its stale counterpart is Section 10 row N-10. |
| `F. What remains unestablished` | Server-derived list of uncovered clauses of the member-confirmed AND/OR structure, each rendered via its confirmed clause display phrase (image 03's F says `recency within the last five years` for the employer clause `within the last five years` — Sections 6.2/7), phrased as unestablished-by-evidence, never as the member lacking the experience `[OBSERVED]` (PDF dignity rule). |
| Footer `Back` link; `Continue to next qualification` primary | Back returns to the previous qualification (or requirement review from qualification 1). Continue marks the current qualification reviewed and advances. Always enabled — zero evidence and empty take/response never block `[LOCKED]` (image 03). After the final qualification the flow reaches the completion/save surface — no locked visual; ChatGPT lane (Section 10 row M-1). Until M-1 lands, R2 builds the interim completion state N-17 in its place — never member-visible, because the v2 flag stays off in production until R5, which requires R3 (Section 14). |
| Right inspector `Selected evidence` with `×` (image 01): context line `Evidence for Agile / SAFe delivery experience`; title `Systems Engineering Experience Summary · Version 3`; rows `Version 3`, `Last updated Mar 15, 2025`; `Exact excerpt` quoted; `WHAT THIS EVIDENCE SUPPORTS` (`Cited for "…" and "…"`); `WHAT THIS EVIDENCE DOES NOT ESTABLISH` | Conditional inspector, selection-earned only `[LOCKED]`. Content is entirely derived: exact bounded excerpt(s) (≤400 units each) pinned in the citation rows; Supports = that item's `covered_text` quotes; Does-not-establish = uncovered clauses rendered via their confirmed display phrases (Section 7). No action exists inside the inspector `[LOCKED]` (VISUAL_AUDIT item 09: "adds no action"). Close restores focus to the invoking row. |
| Image 02 (inspector closed): identical plane, center expanded, evidence rows plain chevrons | The inspector's absence is a real state: closing never discards anything; the plane keeps object identity and scroll position `[OBSERVED]`. |

### 4.5 Image 03 — Desktop zero authorized evidence

| Depicted element | Contract |
|---|---|
| `D.` block: doc-with-magnifier icon; `No matched evidence`; `No authorized evidence was available to compare for this qualification. This does not mean you lack the experience.` | Zero-evidence truth state: neutral, no evidence rows, no chevron, no count, no invented "add evidence" action `[LOCKED]` (VISUAL_AUDIT item 03). |
| `E.` block: empty diamond; `Not enough information`; `No authorized evidence was available to compare with this qualification. Your reviewed response remains private opportunity-specific context and does not change this finding automatically.` | Zero-evidence finding: always `not_enough_information` (DB CHECK ties zero citations to exactly this status `[REPO]`). Never a green connector or fabricated support `[OWNER]`. |
| `F.` text ends `…remain unestablished by authorized evidence.` | The zero-evidence variant appends `by authorized evidence` — precise-cause language `[LOCKED]`. |
| `Continue to next qualification` enabled | Zero evidence is non-blocking `[OWNER]` `[LOCKED]`. |

Mechanism guarantee: when the authorized evidence set is empty, the analysis step short-circuits server-side — every Required/Preferred qualification is derived `not_enough_information` with zero citations, no model call is made, no AI egress occurs, and the result is immediate and honestly labeled. `[PROPOSED]`

### 4.6 Images 07 / 08 / 11 — Mobile qualification review (390 and 320 CSS px)

| Depicted element | Contract |
|---|---|
| Shell: PEERSLATE; `Opportunity Slate` label (underlined); `PC ˅` account menu — nothing else | Mobile shell carries no full nav `[LOCKED]`. |
| Context block: employer, role title, `Confirmed role source · Version 1` | First-fold identity + persistence/source mode `[OBSERVED]` (PDF first-fold budget). |
| `All qualifications >` button | Opens the qualification navigator as a full-screen sheet (the desktop rail's mobile transformation). The sheet itself is not depicted — Section 10 row N-11. Hit area ≥44×44 CSS px `[LOCKED]` (VISUAL_AUDIT item 07 names PC, All qualifications, choice, and Dictate hit areas). |
| `Qualification 2 of 8` + dot stepper (390) / text only (320) | Progress; the 320 file proves the decoration-collapse rule `[LOCKED]`. |
| Sections A → C in image 07, ending at the `D.` heading as scroll cue | Same contracts as desktop; the lower scroll (image 08) carries D → F, `Back`, full-width `Continue to next qualification`. Order A-B-C-D-E-F is fixed `[LOCKED]` (VISUAL_AUDIT item 08 "preserves D-E-F order"). |
| Image 08 sticky-context row: `Agile / SAFe delivery experience | Qualification 2 of 8 | All qualifications ˅` | One shallow local context row once scrolled past the title; it must never trap the work area (PDF sticky budget `[OBSERVED]`). |
| B options stacked full-width; C textarea + Dictate + counter + helper | Two-column relationships become labeled vertical sequences without duplicated content `[OBSERVED]`. Long labels wrap; controls grow vertically (image 11 proves at 320px + large text) `[LOCKED]`. |

### 4.7 Image 09 — Mobile selected-evidence sheet

One full-screen temporary surface replacing the desktop inspector: `Selected evidence` title + `×` close (44×44 hit area, focus returns to the invoking evidence row `[LOCKED]` VISUAL_AUDIT item 09); context line; evidence title + version; Version / Last updated rows; `Exact excerpt`; supports; does-not-establish. No actions. It inherits every temporary-surface contract from the PDF: why it appeared, close/back behavior, its own loading/failure states, no nested scroll traps, closing never discards work. `[OBSERVED]`

### 4.8 Image 10 — Mobile zero-evidence lower scroll

The zero-evidence D/E/F blocks of image 03, restacked at 390px with the same wording, `Back`, and enabled `Continue`. `[LOCKED]`

---

## 5. Data architecture

### 5.1 Ground rules

- Azure SQL, existing `peerslate-database`. All sixteen `opportunity_*` tables from PS-OPPSLATE-001/002/003 are applied in production and carry real member data. They are preserved: no drop, no row mutation, no destructive migration. `[REPO]` `[OWNER]`
- All new schema ships as **PS-OPPSLATE-004**, additive only, through the governed migration path (`scripts/govern_sql_migrations.py` registry + gate proof + approval check id 11 + `PRODUCTION_SCHEMA_STATE.md` regeneration + 3-file release-record lockstep). `[REPO]`
- Procedure ownership: PS-OPPSLATE-004 creates only new procedures with new names, except `usp_PurgeExpiredOpportunityWorkingData` and `usp_DeleteOpportunitySourceForOwner`-class cleanup procedures, which must learn the new child tables; those are taken over with explicit `@ProtectedProcedures`-style hash stamping exactly as PS-OPPSLATE-002 did — one migration owns each definition or explicitly takes it over, or the forward-idempotency gate fails. `[REPO]` `[PROPOSED]`
- The replacement reuses the existing tables wherever the truth shape is unchanged: working sessions, sources, source versions, requirement sets/versions/statements, analyses/statements/citations, slates/saved results. New truth shapes get new tables. Old-experience rows (including old `opportunity_responses` and old saved slates) remain intact and readable. `[PROPOSED]`

### 5.2 New objects (DDL sketch — PS-OPPSLATE-004, additive only)

Sketch, not final DDL; the implementer finalizes constraint names, `_id_owner` composite candidate keys, and FKs following the house pattern (every table carries `UNIQUE (id, owner_profile_id)` and composite owner-scoped FKs `[REPO]`).

```sql
-- 1. Structured source identity (image 05 section A). One row per source
--    version; member-entered; separate from write-once employer wording.
CREATE TABLE dbo.opportunity_source_identities (
    opportunity_source_identity_id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    opportunity_source_version_id  bigint       NOT NULL,
    owner_profile_id               bigint       NOT NULL,
    employer_name                  nvarchar(200) NULL,
    role_title                     nvarchar(200) NULL,
    source_type                    nvarchar(30)  NOT NULL
        CONSTRAINT DF_osi_source_type DEFAULT N'job_posting',
    entered_by_user_id             int          NOT NULL,
    created_at_utc                 datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at_utc                 datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    row_version                    rowversion   NOT NULL,
    CONSTRAINT UQ_osi_version UNIQUE (opportunity_source_version_id),
    CONSTRAINT UQ_osi_id_owner UNIQUE (opportunity_source_identity_id, owner_profile_id),
    CONSTRAINT FK_osi_version FOREIGN KEY (opportunity_source_version_id, owner_profile_id)
        REFERENCES dbo.opportunity_source_versions
                   (opportunity_source_version_id, owner_profile_id),
    CONSTRAINT CK_osi_source_type CHECK (source_type IN (N'job_posting'))
);

-- 2. Requirement review events (image 06 section C + inspector). Append-only;
--    the latest event per statement is the current review; full correction
--    history falls out for free.
CREATE TABLE dbo.opportunity_requirement_review_events (
    opportunity_requirement_review_event_id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    opportunity_requirement_statement_id    bigint       NOT NULL,
    owner_profile_id                        bigint       NOT NULL,
    event_ordinal                           int          NOT NULL,
    review_decision                         nvarchar(30) NOT NULL,
    corrected_organized_text                nvarchar(1200) NULL,  -- only with needs_correction
    corrected_class                         nvarchar(40)   NULL,  -- only with needs_correction
    decided_by_user_id                      int          NOT NULL,
    decided_at_utc                          datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_orre_ordinal UNIQUE (opportunity_requirement_statement_id, event_ordinal),
    CONSTRAINT UQ_orre_id_owner UNIQUE (opportunity_requirement_review_event_id, owner_profile_id),
    CONSTRAINT FK_orre_statement FOREIGN KEY
        (opportunity_requirement_statement_id, owner_profile_id)
        REFERENCES dbo.opportunity_requirement_statements
                   (opportunity_requirement_statement_id, owner_profile_id),
    CONSTRAINT CK_orre_decision CHECK (review_decision IN
        (N'accurate', N'needs_correction', N'not_a_requirement')),
    CONSTRAINT CK_orre_class CHECK (corrected_class IS NULL OR corrected_class IN
        (N'required_qualification', N'preferred_qualification',
         N'responsibility', N'informational_statement')),
    -- a correction payload travels only with a needs_correction decision
    CONSTRAINT CK_orre_payload CHECK (
        (review_decision = N'needs_correction')
        OR (corrected_organized_text IS NULL AND corrected_class IS NULL))
);

-- 3. Member take + own-words response (images 01/02/03 sections B and C).
--    One current row per qualification; replaces the old five-kind
--    opportunity_responses for the NEW experience. Old rows are untouched.
CREATE TABLE dbo.opportunity_member_takes (
    opportunity_member_take_id           bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    opportunity_requirement_statement_id bigint        NOT NULL,
    owner_profile_id                     bigint        NOT NULL,
    take                                 nvarchar(30)  NULL,
    response_text                        nvarchar(max) NULL,   -- <= 4000 units, CHECK below
    authored_via                         nvarchar(30)  NOT NULL DEFAULT N'typed',
    response_reviewed_at_utc             datetime2(7)  NULL,   -- explicit member commit
    alignment_continued_at_utc           datetime2(7)  NULL,   -- 'Continue' progress marker
    created_by_user_id                   int           NOT NULL,
    created_at_utc                       datetime2(7)  NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at_utc                       datetime2(7)  NOT NULL DEFAULT SYSUTCDATETIME(),
    row_version                          rowversion    NOT NULL,
    CONSTRAINT UQ_omt_statement UNIQUE (opportunity_requirement_statement_id),
    CONSTRAINT UQ_omt_id_owner UNIQUE (opportunity_member_take_id, owner_profile_id),
    CONSTRAINT FK_omt_statement FOREIGN KEY
        (opportunity_requirement_statement_id, owner_profile_id)
        REFERENCES dbo.opportunity_requirement_statements
                   (opportunity_requirement_statement_id, owner_profile_id),
    CONSTRAINT CK_omt_take CHECK (take IS NULL OR take IN
        (N'done_this', N'done_related', N'not_yet')),
    CONSTRAINT CK_omt_response_length CHECK
        (response_text IS NULL OR DATALENGTH(response_text) / 2 BETWEEN 1 AND 4000),
    CONSTRAINT CK_omt_authored CHECK (authored_via IN (N'typed', N'dictated'))
);

-- 4. Analysis currency columns (Sections 6.5 and 6.5a). Nullable additive
--    columns; old rows stay NULL and are simply treated as not-current.
ALTER TABLE dbo.opportunity_analyses
    ADD evidence_snapshot_sha256 char(64) NULL,          -- evidence-set hash at run time
        confirmed_requirements_ordinal int NULL;         -- which confirmation this run read (6.5a)

-- 5. Requirement-set confirmation ordinal (Section 6.5a). Bumped by every
--    successful Confirm requirements; lets a post-confirm revision supersede
--    an analysis without a new set version. Old rows NULL = ordinal 1 on
--    first v2 confirm.
ALTER TABLE dbo.opportunity_requirement_sets
    ADD member_confirmed_ordinal int NULL;
```

Clause display phrases (Section 6.2) live inside the existing
`proposed_structure_json` on `opportunity_requirement_statements` — a contract
extension of the JSON, not a new column. If phrases outgrow the current
4,000-unit `CK_..._structure_length` bound, PS-OPPSLATE-004 re-issues that
CHECK with a strictly larger bound — a superset CHECK change is additive-safe
(no existing row can fail it). `[PROPOSED]`

New procedures (owned by 004): `usp_SaveOpportunitySourceIdentityForOwner`, `usp_SaveOpportunityRequirementReviewForOwner`, `usp_ConfirmOpportunityRequirementsForOwnerR` (also bumps `member_confirmed_ordinal` — Section 6.5a), `usp_ReviseOpportunityRequirementsForOwner` (clears the confirmation triple — Section 6.5a), `usp_SaveOpportunityMemberTakeForOwner`, `usp_ReviewOpportunityMemberResponseForOwner`, `usp_ContinueOpportunityQualificationForOwner`, `usp_SaveOpportunityAnalysisForOwnerR` (writes `evidence_snapshot_sha256` + `confirmed_requirements_ordinal`), `usp_GetOpportunityRoomForOwnerR` (single aggregate read for the room). Takeovers with hash re-stamping: the purge and delete procedures, to include the three new tables in owner-scoped cleanup. `[PROPOSED]`

Saved-snapshot schema impact (slice R3, after the save/history visual lock): the OS-4 tables (`opportunity_slates`, `opportunity_saved_results`, `opportunity_saved_qualifications`, `opportunity_saved_evidence`) remain the snapshot store; the new fields (take, response-reviewed state, source identity) enter via additive nullable columns or one small child table in a follow-up migration **PS-OPPSLATE-005**, gate-proofed the same way. Old saved slates remain readable exactly as written. `[PROPOSED]`

### 5.3 Truth-type enforcement in the schema

| Truth type | Where it lives | Write rule |
|---|---|---|
| Employer source | `opportunity_source_versions.original_text/original_sha256`; `opportunity_requirement_statements.employer_text/span_*` | Write-once; verified by the owner-isolation greps `[REPO]`. |
| PeerSlate organization / findings | `proposed_*` columns (including per-clause display phrases inside `proposed_structure_json`); `opportunity_analyses` + statements + citations; server-composed rationale (built from confirmed clause display phrases + validated covered spans — no alignment-run prose is ever stored) | AI proposals land in proposal columns only; findings derive from validated citations; no aggregate column exists anywhere by design `[REPO]`. |
| Member response | `member_*` columns; `opportunity_requirement_review_events`; `opportunity_member_takes`; confirmation triples | Written only by member action through owner-scoped procedures; never written by the AI path (`opportunity_slate_service` has no AI import, guardrail-tested `[REPO]` — the replacement service keeps that guardrail). |
| Authorized evidence | Workshop/My Knowledge tables (PS-WORKSHOP-001/002); pinned titles/versions/excerpts inside citations and snapshots | Never copied except bounded excerpts; never written by this room `[REPO]`. |

---

## 6. Behavioral contracts

### 6.1 Source capture and versioning

- One working opportunity per member (`UQ_opportunity_sources_session`, one-active-slate Q2 ruling stands `[REPO]`).
- Capture methods: pasted, dictated (client-side into the same field, lands as pasted text with `authored_via` provenance), uploaded, imported. Each capture creates an append-only source version with sha256. `[REPO]`
- Replacing the source text after confirmation creates version N+1 and clears the confirmation triple (CHECK-enforced); the prior version remains readable. `[REPO]`
- Member wording corrections write `member_corrected_text` on the version; the original is never touched. Original-vs-corrected comparison is a read of the two columns.
- Source identity (employer, role title) is member-entered at review, stored per version (Section 5.2 table 1), correctable any time before analysis; correcting it does not create a source version and does not invalidate anything (it is member metadata, not employer wording). `[PROPOSED]`
- Confirmation: explicit `Confirm source` sets the triple at exactly the current version. Interpretation refuses to run against an unconfirmed source. `[REPO]`

### 6.2 Requirement organization and correction

- Interpretation (AI step 2) proposes statements with class, explanation, and AND/OR structure mapped to verbatim spans; proposals land in `proposed_*` columns. `[REPO]`
- **Clause display phrases.** Each clause of the proposed structure carries, alongside its verbatim employer span, a bounded natural-language **display phrase** (≤200 units) that later composition uses verbatim (Section 7). This is what makes the locked copy producible without stored analysis prose: image 03's F renders `recency within the last five years` for the employer clause `within the last five years`, and image 01's rationale ends `or when the work occurred` — both are confirmed display phrases, not alignment output. The phrase is part of `proposed_structure_json`; the interpretation validator requires one per clause, enforces the bound, and applies a deterministic digit guard (any numeral sequence in the phrase must appear in the clause's employer text). At `Confirm requirements` the phrases freeze into the member-confirmed set exactly as the AND/OR structure itself does — before any analysis exists. Clause-level editing of structure or phrasing is not in the locked review UI; it falls inside D-9's scope `[OPEN]`. `[PROPOSED]`
- Review flow: each statement receives a member decision — `accurate`, `needs_correction` (with corrected organized wording and/or class), or `not_a_requirement` (excluded from the confirmed set). Decisions are append-only events (Section 5.2 table 2); the latest event is current; the event stream is the correction history. Re-deciding is free before `Confirm requirements`; after confirmation, decisions reopen only through the explicit `Revise requirements` action (Section 6.5a) — the review stage itself stays reachable read-only.
- Confirm requirements: enabled only when every proposed statement has a current decision and no statement sits in `needs_correction` without an applied correction. Confirming freezes the member-confirmed set (writing `member_class`/member columns from the current events via the 004 procedure) and is the explicit trigger for analysis. `[PROPOSED]`
- **Split and merge are not built.** No locked visual depicts them; the correction inspector edits one statement's organization only. The event table's shape does not preclude a future split/merge (events referencing statements), but building them is decision D-9 `[OPEN]` and would need the ChatGPT visual lane.
- Zero Required+Preferred after review: the flow proceeds to a truthful "no qualifications to analyze" completion state (Section 10 row N-12) — Responsibilities/Informational stay inspectable but never enter qualification analysis. `[REPO]`
- Caps: ≤60 statements interpreted, ≤40 qualifications analyzed, statement ≤1,200 units. `[REPO]`

### 6.3 Evidence authorization, citation, and manual connection

- Evidence universe: the member's confirmed Workshop/My Knowledge items (`knowledge_service`), server-listed via `usp_ListOpportunityEvidenceForOwner` under the member's own identity — authorization happens before retrieval, never retrieve-then-filter. `[REPO]`
- The analysis prompt receives a server-grounded allowlist (id + exact version + bounded body ≤8,000 units per item, ≤24 items). The validator rejects any citation whose evidence id/version is not in the allowlist, any aggregate field, and any prose field — the output schema is citations only (Section 7). `[REPO]`
- A citation pins: qualification clause ordinal, verbatim `covered_text` from the employer clause, evidence kind/key/version, pinned title, bounded exact excerpt ≤400 units. Up to 24 citations per qualification. `[REPO]`
- Presentation derives everything else: D-rows group citations by evidence item; the inspector's Supports = that item's covered quotes; Does-not-establish = the confirmed clauses no citation covers, rendered via their confirmed clause display phrases (Section 6.2); E's rationale and F's gap list are the same derivation at qualification level. No alignment-run prose is stored or rendered anywhere — the only natural-language restatement is the interpretation-time display phrase, which entered the member-confirmed set before the analysis existed. `[PROPOSED]`
- **Manual evidence connection ("Connect existing evidence") is not in the replacement's locked visuals and is not built now.** The member's lever on evidence is Workshop itself (add/confirm knowledge there, then reanalyze here). Whether a direct connect-from-the-room affordance returns is D-10 `[OPEN]`; it would need the visual lane and its own authorization contract.

### 6.4 Member take and response — persistence and conflict

- One current take row per qualification (Section 5.2 table 3): `take` (three values), `response_text` (≤4,000), `authored_via`, `response_reviewed_at_utc`.
- Selecting a take persists immediately on explicit selection (a click of a labeled option is an explicit member action, not a silent save). The free-text response is a client draft until the member explicitly commits via the review control (Section 10 row N-9); commit stamps `response_reviewed_at_utc` and renders `Response reviewed ●`. Editing after commit clears the reviewed stamp until re-reviewed. `[PROPOSED]`
- A response never becomes durable evidence, never enters the grounding allowlist, and never changes the finding; the C-section helper states this in place `[LOCKED]` `[OWNER]`. Responses and takes survive reanalysis (they attach to the requirement statement, not to an analysis run — same rationale as the OS-3 comment `[REPO]`).
- Conflict: optimistic concurrency via `row_version`. A stale write (second tab, second device) returns a stable `conflict` error; the client keeps the member's typed text locally, shows the current stored response, and offers "keep mine" (overwrite with fresh rowversion) or "keep stored". Failure preserves valid input. `[PROPOSED]` (PDF state contract `[OBSERVED]`.)
- **Persistence across requirement revision (same set version, Section 6.5a):** a post-confirm revision keeps the same statement rows, so takes and responses stay attached and render unchanged when the guided flow resumes. A take on a statement the member excludes at re-confirm stays stored on its row but leaves the guided flow with the statement — nothing is deleted. `[PROPOSED]`
- **Persistence across source re-versioning (new set version):** re-confirming changed source wording triggers re-interpretation, which creates a new requirement-set version with new statement rows `[REPO]`. Takes and responses on the old rows are never deleted — but they are also never auto-copied or auto-matched onto the new statements: auto-carry would attach member-authored words to employer wording the member never responded under, a truth violation. They remain readable wherever the old set legitimately surfaces (saved snapshots pin them exactly `[REPO]`; old-set rendering depth is D-3), and the owner-scoped purge/delete procedures own their cleanup. Because member work is at stake, the replace/re-confirm dialog (N-5) must name the consequence explicitly — "Your qualification takes and responses will not carry into the new review" — and point at saving first. Whether the new flow should additionally surface prior responses as read-only context is a real owner/visual decision, **D-14 `[OPEN]`** — not silently chosen here. `[PROPOSED]`

### 6.5 Analysis currency, staleness, and reanalysis triggers

- An analysis is pinned to the requirement-set version it read (UNIQUE per version; re-running replaces the working analysis rather than stacking a second opinion — the durable record is the saved slate `[REPO]`) and now also records `evidence_snapshot_sha256` = SHA-256 over the ordered set of (evidence key, version) pairs the allowlist contained at run time, plus `confirmed_requirements_ordinal` = the set's confirmation ordinal at run time (Section 6.5a). `[PROPOSED]`
- **Current** means all of: (a) the requirement set is confirmed and the analysis's set version is the confirmed current one; (b) the analysis's `confirmed_requirements_ordinal` equals the set's current `member_confirmed_ordinal` (Section 6.5a); (c) recomputing the evidence snapshot hash over today's authorized evidence equals the stored hash. Then E shows `· Current analysis` `[LOCKED]`.
- **Stale** triggers: source wording re-confirmed at a new version (invalidates the requirement set → re-review → new analysis); requirement set revised and re-confirmed (confirmation-ordinal mismatch, Section 6.5a — detected even though the set version is unchanged); any authorized evidence item added, removed, or re-versioned in Workshop (hash mismatch). Stale never deletes or hides the existing analysis — it re-labels it (Section 10 row N-10) and offers explicit reanalysis. Saved snapshots keep their own pinned truth regardless. `[PROPOSED]`
- Reanalysis is always explicit — a member action, rate-limited (≤6/min AI floor `[REPO]`), never automatic, never triggered by saving, opening, or responding. `[OWNER]`
- Analysis failure (validator reject, provider outage): HTTP 502, nothing partial renders or persists, confirmed inputs and existing analysis remain untouched, retry offered. `[REPO]`
- Reads during analysis: the room is read-only for the affected sections with in-place progress (Section 10 row N-2); cancel is offered only where truthfully cancellable — Section 6.11 names exactly which operations those are. `[OBSERVED]`

### 6.5a Post-confirmation requirement revision

Resolves the confirm/re-review boundary so the currency model can never lie about superseded wording:

- After `Confirm requirements`, the review stage stays **reachable read-only** — `Back` from qualification 1 and the rail return to it for reading and span inspection. Decision controls render disabled with an in-place explanation and one secondary action, `Revise requirements` (presentation: Section 10 row N-16). `[PROPOSED]`
- `Revise requirements` opens a bounded confirmation naming the consequence ("Your current analysis will be marked outdated until you re-confirm and reanalyze"). Confirming it clears the set's confirmation triple — the exact existing mechanism by which a correction clears confirmation (`CK_opportunity_requirement_sets_confirmation_state` `[REPO]`) — and unlocks decisions again under Section 6.2's rules.
- While the set is unconfirmed: analysis refuses to run `[REPO]`, the guided qualification flow is unreachable (its inputs are unconfirmed), and the existing analysis immediately fails currency clause (a) — E renders the N-10 outdated label with the cause "You are revising the confirmed requirements". Nothing is deleted.
- Re-confirming runs the same completeness gate as first confirmation and **bumps `member_confirmed_ordinal`** (additive 004 column). Because the statements are re-decided in place, no new set version and no new statement rows are created — takes and responses stay attached (Section 6.4). The prior analysis is now permanently non-current by clause (b): a superseded confirmation can never read `· Current analysis`, even at the same set version.
- Explicit reanalysis after re-confirm replaces the working analysis for that set version via the existing replace-not-stack mechanism (`UQ_opportunity_analyses_version` `[REPO]`), recording the new ordinal. A saved snapshot made from the superseded analysis keeps its own pinned truth. `[PROPOSED]`

### 6.6 The working opportunity's lifetime

Today `opportunity_working_sessions` expire at 48h idle with purge-at-read `[REPO]` — a rule designed when anonymous privacy was in scope. For a signed-in-only replacement I propose the working opportunity is **durable until the member deletes or replaces it** (the rail's `Current opportunity` promise), with saved snapshots remaining the explicit versioned record. This is a retention-policy change and is decision **D-1 `[OPEN]`** — the implementer must not change the purge behavior until Pete decides. Until then the replacement honestly surfaces expiry ("This working opportunity expired after 48 hours of inactivity") rather than silently losing work. `[PROPOSED]`

### 6.7 Guided-flow progress

- Requirement review progress = statements with a current review event ÷ total (image 06's `12 of 13`).
- Qualification progress = takes rows with `alignment_continued_at_utc` set (the stepper's filled checks). `Continue to next qualification` sets it; `Back` never unsets it. Jumping via the rail or `All qualifications` sheet is free navigation and does not alter progress. `[PROPOSED]`

### 6.8 Save, history, staleness of saves, and failure

Behavioral contract (composition goes to the ChatGPT lane, Section 10 row M-1):

- A save is an explicit member action producing an immutable versioned snapshot: pinned source version + identity, confirmed requirement set, full analysis (statuses + citations + excerpts), takes and reviewed responses, and the analysis `input_fingerprint` (existing OS-4 mechanism `[REPO]`).
- Saved versions are append-only, never silently overwritten; the list surfaces up to 50 `[REPO]`.
- Saved-vs-current currency = fingerprint comparison; states: unsaved current / saved-and-current / saved-but-stale / prior-saved-plus-newer-unsaved. `[REPO]`
- Saving never closes the room, never reruns analysis, never publishes, never touches Workshop. `[OWNER]`
- Save failure leaves the prior saved version intact and says so; idempotency via `opportunity_save_requests` `[REPO]`.
- Old-experience saved slates remain in the member's history, rendered read-only from their own pinned truth (they lack takes/identity; the renderer shows what was actually saved, honestly labeled). Presentation depth is D-3 `[OPEN]`.

### 6.9 Deletion

- Delete current working opportunity (start over) and delete a saved version are separate actions with separate consequences.
- Every deletion uses a bounded confirmation dialog naming the exact target, consequence, and reversibility — never a popover, never closable by accidental outside click `[OBSERVED]` (PDF). Copy sketch, Section 10 row N-13.
- Failed delete leaves the object visibly intact ("still saved") with a conflict-safe error. `[REPO]`
- Deleting the working opportunity never deletes saved snapshots; deleting a saved snapshot never touches the working opportunity or any Workshop evidence. `[REPO]` `[PROPOSED]`

### 6.10 Authorization boundaries

- Identity derived server-side per request (`identity` module); no client-asserted identity anywhere. `[REPO]`
- Every read and write goes through owner-scoped procedures with composite `(id, owner_profile_id)` keys; cross-owner access is structurally impossible and verified by the owner-isolation scripts. `[REPO]`
- Authorize before returning or mutating; neutral 404 for other-owner or nonexistent keys; opaque keys (GUIDs) in all client-visible identifiers. `[REPO]`
- Same-origin write guard on every mutation; rate limits 30/min mutations, 6/min AI endpoints per member; `private, no-store` everywhere. `[REPO]`
- Feature flag `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` as stop control; flag-off = neutral 404. `[PROPOSED]`
- The `PEERSLATE_OPPSLATE_DAILY_AI_CEILING` spend guard was public-mode-scoped; keeping a global ceiling as a stop control under signed-in-only is D-11 `[OPEN]` (I recommend keeping it). Employer sources remain adversarial input: source content is data, never instructions. `[REPO]`

### 6.11 Cancellation contract

The rule (Section 6.5) is: a Cancel control exists only where the server can guarantee the operation's effects do not land after the member cancels. Operation by operation `[PROPOSED]`:

| Operation | Cancel? | Contract |
|---|---|---|
| Dictation | Stop, not cancel | The shared module's explicit stop; stopping never submits `[REPO]`. |
| Upload (N-3) | **Yes**, while in flight | Cancel aborts the client request and returns to intake with the typed/pasted draft intact and an honest notice ("Upload cancelled — nothing was captured"). Server-side capture is atomic: the source version row commits only at request completion, so no partial version can exist. In the disconnect race where the server completes anyway, the next read shows the captured version honestly and the member can replace or delete it (N-5). |
| Public-link import (N-4) | **Yes**, while in flight | Same contract as upload; the server-side fetch is additionally bounded by the intake service's hard size/time caps `[REPO]`, so an abandoned request always terminates. |
| Interpretation (AI step 2) | **No** | An in-flight provider call cannot be truthfully cancelled from the client; offering a Cancel whose result lands anyway would be a lie. The call is request-scoped and time-capped `[REPO]`, alters no member input or canonical truth (the result lands as labeled proposals awaiting review), and the affected sections show in-place progress (N-2). Navigating away is always safe: on return the room shows the completed proposals or the failure anatomy — never a corrupted intermediate. |
| Analysis / reanalysis (AI step 3) | **No** | Same reasoning and same guarantees; the result lands as derived findings with the currency tag, and the existing analysis is only replaced on successful completion (Section 6.5). |
| Save (R3) | **No** | Bounded and idempotent via `opportunity_save_requests` `[REPO]`; failure leaves the prior saved version intact (Section 6.8). |

If Pete wants a Cancel affordance on interpretation or analysis anyway, the truthful implementation is discard-on-arrival (the server checks a member-set cancellation marker before persisting) — a deliberate scope addition, not this document's default. The no-cancel choice here follows directly from the truthfulness invariant; the in-flight upload/import cancels are the only controls this contract adds to the locked visuals.

---

## 7. AI contract

Three steps, unchanged in shape, each with a versioned prompt contract and a strict validator; a malformed reply is a 502 and nothing partial renders or persists. `[REPO]`

| Step | Purpose | Model | Notes |
|---|---|---|---|
| 1. Source wording concerns | Extraction-uncertainty flags as character spans; never rewrites employer wording | `claude-haiku-4-5-20251001` (existing) | **Deferred from the replacement MVP** — no locked visual depicts concerns (D-7 `[OPEN]`, Section 10 row N-6). The service and contract already exist `[REPO]` and can be re-enabled when the visual exists. |
| 2. Statement interpretation | Classes + AND/OR structure mapped to verbatim spans, plus one bounded display phrase per clause (Section 6.2) | `claude-sonnet-5` `[OWNER]` (OS-2 measured-evidence decision) | Runs on explicit member action from the confirmed source only. Validator requires a display phrase per clause, enforces the ≤200-unit bound, and applies the digit guard. |
| 3. Alignment | Citations only | `claude-sonnet-5` | Structural no-aggregate control (below). |

**Structural no-aggregate control (binding for the replacement):** the alignment output schema holds only citations — (statement ref, clause ordinal, covered verbatim span, evidence id + version, excerpt bounds). It structurally cannot carry a score, verdict, status, or prose. Status is derived server-side from citation coverage; rationale (E), per-evidence supports/does-not-establish (inspector), and gaps (F) are server-composed from the member-confirmed clause **display phrases** (proposed at interpretation, frozen at requirement confirmation — Section 6.2) and validated verbatim covered spans. The alignment run contributes citations only, so there is no alignment-run prose to store — the locked natural-language gap wording (image 03's `recency within the last five years`) is reproduced from confirmed phrases, not generated at analysis time. Ungrounded claims are invalid by construction. The deleted OS-2 lexical prose scan is **not** restored, and no keys-only rule is inherited — this satisfies the recorded OS-3 mandate. `[REPO]` `[PROPOSED]`

Zero-evidence short-circuit: empty allowlist → no model call, all statuses `not_enough_information`, immediate honest result (Section 4.5). `[PROPOSED]`

AI-unavailable behavior: source capture, source review, identity entry, and confirmation are fully non-AI and keep working. Interpretation/analysis outages present the PDF failure anatomy (what failed / what is safe / what did not happen / retry / continue-without) and degrade to review-and-respond — the member can still read the source, review requirements already proposed, and write takes/responses; nothing blanks. `[OBSERVED]` `[PROPOSED]` Never promise a third party's data retention behavior in any copy. `[OWNER]`

Anthropic remains the only AI egress; there is no background scheduler — every AI call is request-scoped. `[REPO]`

---

## 8. Hard-case proofs (mechanisms, not assertions)

| Case | Mechanism |
|---|---|
| Zero authorized evidence | Deterministic short-circuit (no AI egress); locked neutral D/E/F wording; Continue always enabled; response stays private context. Images 03/10 are the locked truth. |
| Long text | Source ≤20,000; statement ≤1,200; response ≤4,000 with live counter (locked); excerpt ≤400; all text containers wrap (image 11 proves 320px + large text with no horizontal clipping `[LOCKED]`); rationale/gap lines are composed from bounded confirmed clause display phrases (≤200 units each) so they cannot run away. |
| Many requirements (up to 40 analyzed / 60 interpreted) | Rail is an independently scrolling list (40 rows ≈ 2,200px — scroll, no virtualization needed); the dot stepper degrades to `N of M` text + progress bar (the locked image-06/image-11 pattern); one qualification at a time keeps the dominant plane constant regardless of count; review flow already proves 13 items. |
| Many evidence items/citations (≤24 items, ≤24 citations per qualification) | D-rows group by evidence item (≤24 rows, plain vertical list); the inspector shows one item at a time with its bounded excerpts — complete evidence inspection lives in the inspector/sheet, resolving the old "extremely tall inline expansion" problem by never inlining it. |
| Mobile reflow | Locked 390px masters define first fold (identity + source mode + current work) and D-E-F order; 320px master proves decoration collapse + wrapping; two-column relationships become labeled sequences; the inspector becomes one full-screen sheet with 44×44 close and focus return `[LOCKED]`; sticky context row has an explicit budget and never traps the work area. Reflow at 320 CSS px and 200% zoom without horizontal scroll is a release gate (verification plan, Section 15). |
| Keyboard / screen reader | DOM order: main heading and dominant plane precede rails even where a rail sits visually left `[OBSERVED]`; skip link + named landmarks (`nav`, `main`, `complementary` for inspector); rail = list of buttons with `aria-current`; stepper dots `aria-hidden` with the `Qualification 2 of 8` text as the accessible truth; B = radiogroup; D-rows = buttons with `aria-expanded`; inspector focus-in on open, focus-return on close, trapped only when modal; async transitions (analysis complete, save complete, retry failed) announced via polite live regions, never per-token. |
| Reduced motion | No ambient motion anywhere in the workroom `[OBSERVED]`; stage transitions and sheet presentation gate on `prefers-reduced-motion` to instant state swaps; comprehension never depends on motion (every transition also changes visible text/state). |
| AI unavailable | Section 7: non-AI stages unaffected; failure anatomy with retry + continue-without; confirmed inputs preserved; no blank page. |
| Failure injection generally | Every failure names the object and version it applies to; retrieval failure ≠ save failure; empty ≠ unavailable ≠ unauthorized `[OBSERVED]`; stable machine error codes from procedures up `[REPO]`. |

---

## 9. Template, JS, and CSS structure

`[PROPOSED]` — new files beside the old (never editing the live experience until cutover):

- `opportunity_slate_v2_routes.py` — new Blueprint, same `ROOM_PATH`. `app.py` registers exactly one of (legacy blueprint, v2 blueprint) at the path based on `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED`; both flag-off → neutral 404. Rate limits attached post-registration, same pattern as today. `[REPO]`
- `services/opportunity_slate_v2_service.py` — persistence for the replacement (no AI import; guardrail test replicated). Reuses `opportunity_source_intake_service` (upload/import) and `opportunity_analysis_service` (adding the v2 alignment prompt contract + validator beside the existing ones) rather than duplicating them.
- `templates/opportunity_slate_v2/room.html` + partials: `_shell.html`, `_rail_opportunity.html`, `_stage_intake.html`, `_stage_source_review.html`, `_stage_requirements.html`, `_inspector_correction.html`, `_stage_qualification.html`, `_inspector_evidence.html`, `_sheet_evidence.html`, `_sheet_qualifications.html`, `_failure.html`, `_icons.html`.
- `static/css/opportunity-slate-v2.css` — light-only, warm-neutral per the locked set; no new dark rules `[OWNER]`.
- `static/js/opportunity-slate-v2.js` — progressive enhancement: fetch-based stage posts, draft management, inspector/sheet focus management, live-region announcements. `static/js/dictation.js` reused untouched (shared with Interview Studio — regression test on touch `[REPO]`).

Route/API contracts (all POST JSON unless noted; all identity-required, same-origin-guarded, owner-scoped):

| Endpoint | Effect |
|---|---|
| `GET /opportunity-slate` | The room at its current stage (or first-arrival). Anonymous → sign-in gate. |
| `POST /opportunity-slate/source` / `/source/upload` / `/source/import` | Capture a source version (paste / file / link). |
| `POST /opportunity-slate/source/identity` | Save employer / role title / source type for the current version. |
| `POST /opportunity-slate/source/corrections` | Save member wording correction (clears confirmation if confirmed). |
| `POST /opportunity-slate/source/confirm` | Confirm the current source version. |
| `POST /opportunity-slate/source/delete` | Delete working source (bounded confirmation upstream). |
| `POST /opportunity-slate/requirements` | Run interpretation (AI step 2) on the confirmed source. |
| `POST /opportunity-slate/requirements/review` | Record one statement's review event (decision + optional correction). |
| `POST /opportunity-slate/requirements/confirm` | Freeze the member-confirmed set (bumps the confirmation ordinal, Section 6.5a); runs analysis. |
| `POST /opportunity-slate/requirements/revise` | Reopen decisions post-confirmation (clears the confirmation triple, Section 6.5a). |
| `POST /opportunity-slate/analysis` | Explicit (re)analysis. |
| `POST /opportunity-slate/qualifications/<key>/take` | Save take selection. |
| `POST /opportunity-slate/qualifications/<key>/response` | Commit (review) the own-words response. |
| `POST /opportunity-slate/qualifications/<key>/continue` | Mark reviewed, advance. |
| R3 adds: `GET /opportunity-slate/saved`, `POST /save`, `POST /reanalyze`, `POST /delete` | Saved lifecycle per Section 6.8. |

---

## 10. States without a locked visual — adaptation register

Per the owner instruction: minimal **non-material** adaptations are designed here and flagged; anything **material** goes to the ChatGPT visual lane and is never invented by me. Pete may promote any N-row to the lane if he judges it material.

**Needs ChatGPT visual lane (material new composition):**

| ID | State | Why material |
|---|---|---|
| M-1 | Alignment completion + save + saved history + saved-version detail (the whole Section 6.8 surface) | A new screen family with a new dominant object (the saved version). Blocks slice R3 only. |
| M-2 | Requirement split/merge UI (if D-9 approves building it) | New interaction pattern with truth consequences. |
| M-3 | Source-concerns presentation (AI step 1) inside source review (if D-7 keeps the function) | New annotation layer over the captured wording. |
| M-4 | Manual evidence connection from the room (if D-10 approves it) | New action surface with authorization consequences. |

**Minimal non-material adaptations (designed, flagged):**

| ID | State | Adaptation |
|---|---|---|
| N-1 | Sign-in gate for anonymous visitors | Site-standard sign-in redirect with return target. No new composition. |
| N-2 | Processing states (capture, interpretation, analysis) | In-place progress inside the owning section, naming the object ("Organizing requirements from Confirmed role source · Version 1…"); affected controls disabled; polite live-region announcement. No Cancel control for interpretation/analysis (Section 6.11). PDF state contract followed. |
| N-3 | Upload in-flight/failure | Inline row under the Upload entry point: filename, progress, in-flight `Cancel` (Section 6.11), then success (advance to review) or precise failure (unsupported type / unreadable / oversize) with retry. |
| N-4 | Public-link import entry | Small bounded temporary surface: URL field, `Import` action, in-flight `Cancel` (Section 6.11), inline validation and precise failure (not public / too large / timed out). Full PDF temporary-surface contract. |
| N-5 | Source replace/delete confirmation | Bounded dialog (Section 6.9 pattern): "Replace the captured source? Version 1 remains in this opportunity's history. Your confirmed requirements and current analysis will need review again, and your qualification takes and responses will not carry into the new review." (Consequence wording required by Section 6.4.) |
| N-6 | Concerns absent in MVP | Source review runs entirely member-driven (no AI annotation). Honest and simpler than the old flow; the function's return is D-7. |
| N-7 | Requirement review "Final check" | The rail's last step: a summary list (counts per section, any excluded statements named) above the enabling of `Confirm requirements` with consequence line "PeerSlate will analyze the N required and M preferred qualifications you confirmed." Composition = the existing review plane, no new panels. |
| N-8 | Preferred qualifications in rail/stepper | A second labeled group in the rail (`Preferred qualifications`), continuous numbering in the guided sequence; stepper counts span both. Pure extension of the locked list pattern. |
| N-9 | Response commit control | When the C-draft is dirty, a secondary `Review my response` button appears directly under the textarea; committing restores the `Response reviewed ●` state. Keeps the explicit-commit rule without inventing a new surface. |
| N-10 | Stale analysis label | E's tag swaps `· Current analysis` → `· Analysis outdated` with one sentence naming the cause ("Your evidence library changed since this analysis") and an explicit `Reanalyze` secondary action; the rail mirrors the state. No banner, no new panel. |
| N-11 | Mobile `All qualifications` sheet | Full-screen sheet mirroring the desktop rail list (numbered rows, status glyph + text per row), 44×44 close, focus return — the exact pattern image 09 locks for evidence, applied to the navigator. |
| N-12 | Zero Required+Preferred after review | Truthful completion state: "This source contained no required or preferred qualifications to analyze. Responsibilities and informational statements remain viewable." No invented analysis. |
| N-13 | Delete confirmations (working opportunity; saved version, R3) | Bounded dialog naming exact target + consequence + reversibility; destructive action is never the default focus; failure leaves the object visibly intact. |
| N-14 | Error/notice presentation | Inline failure blocks per PDF anatomy; page-level only when the primary resource cannot load; dialog only when a decision is required. No toast system is introduced. |
| N-15 | Working-opportunity expiry notice (until D-1 resolves) | On purge-at-read: honest empty state "Your working opportunity expired after 48 hours of inactivity" with `Bring in a role` restart. |
| N-16 | Post-confirmation read-only requirement review (Section 6.5a) | The locked review plane with decision controls disabled, an in-place explanation ("You confirmed these requirements. Revise them to change a decision."), and one secondary `Revise requirements` action opening the bounded consequence dialog. No new composition — the locked plane plus the site's standard disabled/explanation treatment. |
| N-17 | R2 interim completion state (until M-1 lands) | After the final qualification's `Continue`: a minimal state titled "All N qualifications reviewed" with navigation back into the flow and the honest line "Saving this review arrives with the save surface." Interim by design, replaced wholesale by the M-1 surface in R3; never member-visible because the v2 flag stays off in production until R5, which requires R3 (Section 14). |

---

## 11. Function retirement matrix (old experience → replacement)

Deliberate dispositions so replacement drops nothing by accident `[OWNER]` requirement:

| Old function | Disposition |
|---|---|
| Anonymous public session (paste-only, signed tokens, demo evidence, sessionStorage rehydration, spend-guarded public AI) | **Retired** by owner decision (sign-in only). Endpoints not registered in v2; data (none — it never persisted) unaffected. |
| Paste/type/dictate/upload/import intake | **Carried** (images 04; OS-6 services reused). |
| Source review with verbatim/normalized separation, corrections, replace/delete, explicit confirm | **Carried** (image 05; same tables). |
| AI wording concerns (step 1) | **Deferred** — D-7 `[OPEN]`, needs visual (M-3). Service retained. |
| Requirement interpretation, four classes, clarify/reclassify, explicit confirm | **Carried and extended** (image 06 adds per-statement Accurate/Needs-correction/Not-a-requirement review with history). |
| Five response kinds (tell_more / connect_evidence / real_example / no_experience / skip) | **Replaced** by Your take (3 options) + one own-words reviewed response. `not_yet` covers "Confirm I do not have this"; continuing without input covers "Skip"; free text covers "Tell us more"/"Provide a real example". `connect_evidence` has no successor in MVP — D-10. Old rows preserved. |
| Status filters (All / Supported / Partially / Not enough info) | **Retired** — no locked visual shows filters; the guided flow + navigator replace the ledger context that needed them. Return is D-12 `[OPEN]`. |
| "Group by" control | **Never really existed** (decorative) — not built. |
| Inline row expansion / evidence connector line / mixed summary counts (banked JPG inventions) | **Superseded** by the locked guided flow; category counts and finding language never mix (image 06 rail vs E-section). |
| Three-state finding, citations with exact excerpts, rationale, unestablished gaps | **Carried** (images 01–03; same tables + derivation). |
| Saved slate lifecycle (save, history, stale, reanalyze, delete) | **Carried** into R3 behind the M-1 visual lock; OS-4 tables reused; old saved slates readable (D-3 for depth). |
| Shared dictation module | **Carried untouched** (Interview Studio regression on any touch). |
| Ask Slate AI | **Never existed; stays out** (Q1 standing). |

---

## 12. MVP, later phases, and rejected capabilities

**MVP (slice R1, implemented immediately after this document)** — Section 14.

**Later phases:** R2 requirements + alignment; R3 save/history (after M-1 visual lock); R4 hardening + audits; R5 cutover; R6 legacy removal. Section 14.

**Explicitly rejected / not invented (a mockup could visually accommodate them; the contract does not):**

- Any aggregate score, percentage, rank, verdict, employer prediction, or traffic light — at UI, API, and DB layers. `[OWNER]` `[REPO]`
- AI chat, ambient assistant rail, AI-authored response drafts, AI prefill of "Your take". `[OWNER]`
- Automatic reanalysis on any event (save, open, evidence change, response). `[OWNER]`
- Turning a member response into evidence, Workshop knowledge, or a finding input. `[OWNER]`
- Employer-side surfaces, egress to employers/third parties, multi-role comparison, job feeds. `[REPO]`
- Structured location/compensation chips, "Analysis complete" chips, "Open source" external-destination actions — old banked-map inventions with no locked visual and no requirement.
- Pagination/virtualization/grouping controls — not needed at real cardinality (Section 8); adding one later is a product decision, not decoration.
- Public/anonymous mode in any form, including "just a demo". `[OWNER]`

---

## 13. Unresolved owner decisions

Listed, not chosen. Each is safe to defer past R1 except where noted.

- **D-1 — Working-opportunity retention:** keep the 48-hour idle expiry for the signed-in replacement, or make the working opportunity durable until the member deletes or replaces it? (Affects purge behavior; decide before R2 ships alignment work members will care about losing.)
- **D-2 — Entry point and gate presentation:** Owner Home card, Back target from the room, and whether anonymous visitors hitting the nav link see a sign-in redirect or a branded gate page.
- **D-3 — Old saved slates:** how deeply the new history renders pre-replacement snapshots (full read-only room vs summary card).
- **D-4 — Preferred-qualifications presentation:** accept the N-8 minimal rail/stepper extension, or send it to the ChatGPT lane.
- **D-5 — Adaptation register sign-off:** which N-rows in Section 10 Pete accepts as non-material, and which he promotes to the ChatGPT lane (N-7, N-9, N-10, N-11, and N-16 are the likeliest candidates).
- **D-6 — Employer/Role title prefill:** member-entered only (MVP) or AI-proposed prefill later (new prompt contract + proposal/decision separation).
- **D-7 — Source wording concerns (AI step 1):** retire, or return behind an M-3 visual lock.
- **D-8 — Response-model replacement:** confirm the Your-take + single-response model fully replaces the five response kinds (Section 11 rows 6–8), accepting that "Connect existing evidence" has no MVP successor.
- **D-9 — Requirement split/merge and clause-level editing:** build (M-2 visual lane + event-model extension) or leave out. Includes member editing of clause structure and clause display phrases (Section 6.2), which the locked review UI does not expose; until decided, a materially wrong phrase is corrected by revising and re-interpreting from source review.
- **D-10 — Manual evidence connection:** build later (M-4) or keep Workshop as the only evidence lever.
- **D-11 — AI spend ceiling:** keep `PEERSLATE_OPPSLATE_DAILY_AI_CEILING` as a global stop control under signed-in-only (recommended), or retire it in favor of per-member rate limits alone.
- **D-12 — Status filters:** stay retired, or return in the qualification navigator once real usage shows need.
- **D-13 — Cutover timing:** when R5 flips the live route to sign-in-only (requires the two-mode audit gate first) and how long R6 waits before deleting legacy code.
- **D-14 — Prior takes/responses after source re-versioning:** when re-interpretation creates a new requirement set, the member's earlier takes and responses are preserved but do not appear in the new flow (Section 6.4). Should a read-only "your earlier responses" context surface exist there (would need the ChatGPT visual lane), or is preserved-in-history plus the N-5 warning enough?

---

## 14. Implementation sequence

Proposed package: **PS-OPPORTUNITY-SLATE-002 — Opportunity Slate Replacement** (continues the existing package numbering; migration series continues at PS-OPPSLATE-004). Protected path under `docs/AI_WORKFLOW.md` + PS-OPS-001 (consequential AI, private cross-referenced member data, migration, deletion) — independent review is mandatory for this surface class per the package precedent `[REPO]`. Azure DevOps PR flow; never push to `main`; merge ≠ deployment; Azure runs Python 3.14 vs local 3.13 — validate any new dependency against the App Service runtime (this design adds none). `[REPO]`

### R1 — MVP: replacement shell + intake + captured-source review (first slice, implement now)

Delivers, behind `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED` (default false; production keeps the legacy experience untouched and live):

1. New blueprint `opportunity_slate_v2_routes.py` registered at `/opportunity-slate` when the flag is on (legacy blueprint otherwise); sign-in gate; `private, no-store` + noindex headers; same-origin guards; 30/min mutation rate limit.
2. Stage 1 (image 04): paste/type/dictate intake; upload and link import reusing `opportunity_source_intake_service` unchanged; disabled-until-nonempty `Review source`; N-3/N-4 in-flight and failure states.
3. Stage 2 (image 05): captured-source review — identity fields, meta row, editable captured wording (member correction column), Back, `Confirm source`; N-5 replace/delete confirmation.
4. Migration **PS-OPPSLATE-004** (Section 5.2): three new tables + three nullable columns (two on `opportunity_analyses`, one on `opportunity_requirement_sets`) + new procedures + purge/delete takeover with hash re-stamping; registry entry, gate proof (prerequisites, forward, idempotent reapply, owner-isolation verifier, rollback, forward-after-rollback), rollback + verification scripts; applied via the pipeline schema stages behind approval check 11; `PRODUCTION_SCHEMA_STATE.md` regenerated; release-record 3-file lockstep. (Tables 2–3 are consumed by R2 but gate-proofed once here.)
5. Templates/CSS/JS per Section 9 (stage 1–2 partials only), light-only, WCAG 2.2 AA for the shipped states (landmarks, labels, focus, 320px reflow, reduced motion).

Affected repo paths (all new files unless noted): `opportunity_slate_v2_routes.py`; `services/opportunity_slate_v2_service.py`; `templates/opportunity_slate_v2/…`; `static/css/opportunity-slate-v2.css`; `static/js/opportunity-slate-v2.js`; `SQL FIles/Migrations/proposed/PS-OPPSLATE-004_opportunity_slate_replacement.sql` (+ rollback + verification + registry.json entry); `app.py` (flag + conditional registration + rate limits — edited); `tests/test_opportunity_slate_v2.py`, `tests/test_opportunity_slate_v2_migration.py`.

Explicitly NOT in R1: any AI call; requirement review; alignment; save; cutover; any change to legacy routes, templates, services, tests, or data.

R1 test plan (CI runs `unittest discover` — alphabetical, not pytest `[REPO]`):

- Gate: anonymous → sign-in redirect on every v2 endpoint; flag-off → 404 both modes; legacy unaffected when flag off (existing suites stay green untouched).
- Intake: paste/upload/import happy paths; oversize; unsupported type; SSRF contract regression (reusing existing intake tests as the model); idempotent double-submit.
- Source review: identity save + cross-owner isolation (owner A cannot read/write B via any new procedure); wording correction preserves `original_text`/`original_sha256`; confirm sets the triple; correction-after-confirm clears it.
- Migration: forward, idempotent reapply, rollback, forward-after-rollback on a disposable database; fingerprint-guard proof that 004's takeovers re-stamp and nothing else redefines 001–003 procedures.
- Templates: render tests for empty/filled/failure states; no-AI-import guardrail on the v2 service; header assertions (`no-store`, noindex).

### R2 — Requirements + alignment

Interpretation (Sonnet 5, including per-clause display phrases) + review flow (image 06) + confirm + post-confirm revision (6.5a, N-16); analysis (citations-only contract + validator + zero-evidence short-circuit + evidence snapshot hash + confirmation ordinal) + guided qualification flow (images 01/02/03/07/08/09/10/11) + takes/responses + stale labeling (N-10) + AI failure anatomy + upload/import cancel (6.11). The final qualification's `Continue` leads to the interim completion state N-17 — R2's terminal state until M-1 lands in R3; because the v2 flag stays off in production until R5, no member ever sees it. Contract tests: validator rejects unknown evidence ids, aggregate fields, prose fields, and missing/oversize/digit-violating display phrases; derivation tests proving E/F/inspector text is byte-composed from confirmed phrases + covered spans; confirmation-ordinal currency tests (a revised-and-re-confirmed set never lets the superseded analysis read `· Current analysis`); take/response persistence tests across 6.5a revision; conflict tests for takes; dictation shared-module regression (Interview Studio).

### R3 — Save, history, deletion

Blocked on the M-1 ChatGPT visual lock. OS-4 tables + PS-OPPSLATE-005 additive columns; fingerprint currency; old-slate read-only rendering (D-3); N-13 delete dialogs; rollback evidence per protected-operations standard.

### R4 — Hardening and audits

Full verification matrix (Section 15); failure injection; accessibility pass; performance at max cardinality; independent review of the protected surfaces (mandatory `[REPO]`).

### R5 — Cutover

R5 requires R1–R4 complete — in particular R3: the replacement is never made member-visible without the save lifecycle, so the M-1 visual dependency blocks member exposure, never just R3's code. Then: two-mode audit gate (Pete's 2026-08-02 direction) → flip `PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=true` in App Service config → live smoke of the affected routes → anonymous endpoints now unregistered (neutral gate), legacy UI unreachable, all legacy data intact. Rollback = flip the flag back (both experiences coexist in the artifact). D-13 governs timing.

### R6 — Legacy retirement

After a soak Pete accepts: remove legacy routes/templates/JS/CSS and the public-session code paths; retire `PEERSLATE_OPPSLATE_CONTEXT_SIGNING_KEY` (config removal only after code removal); keep `PEERSLATE_OPPORTUNITY_SLATE_ENABLED` semantics resolved (v2 flag becomes the only gate). **No schema removal ever** — PS-OPPSLATE-001..003 tables, procedures, and rows stay, preserved production truth.

---

## 15. Verification plan (release gates for every slice)

From the controlling PDF's acceptance battery `[OBSERVED]`, binding here:

1. Composition gate: dominant object identifiable in 5 seconds; hierarchy survives removing borders/shadows; every surface has a semantic reason; no equal-elevation fragmentation.
2. Truth gate: employer source vs PeerSlate organization vs member response vs authorized evidence distinguishable on every screen; one page-level truth statement; consequence-specific truth only at consequential actions.
3. State gate: the canonical 8-step sequence (bring → review source → review requirements → explore qualification/evidence → respond → save exact version → resume/stale → bounded delete) verified end-to-end, with the same object identifiable through loading/result/save/history/failure.
4. Mobile gate: 390×844 first fold = identity + source mode + current work; 320 CSS px + 200% zoom reflow with no horizontal scroll or hidden functions; sheets keyboard-safe with focus return.
5. Accessibility gate: keyboard-only, screen reader, dynamic type, forced colors, reduced motion, touch targets ≥44×44 (WCAG 2.2 AA).
6. Failure-injection gate: AI/network/auth/upload/voice/save/retrieval failures preserve work and offer cause-specific recovery; failed delete leaves the slate visibly saved.
7. Release-truth gate: source-main ≠ merged ≠ deployed ≠ live-verified; pipeline + live smoke reported separately; nothing called live without evidence. `[REPO]`

---

*End of architecture document.*
