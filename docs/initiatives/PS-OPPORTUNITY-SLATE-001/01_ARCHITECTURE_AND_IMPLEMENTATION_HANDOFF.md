# PS-OPPORTUNITY-SLATE-001 — Architecture-ready visual-authority and implementation handoff

Author: Claude Fable 5 (Extra High), architect, 2026-08-02.
Base: `origin/main` at `803b34b364b53eb77edc34c197b3b38d02431b56`.
Visual authority: `visual-authority/2026-08-02-chatgpt-lock/` (hash-verified;
hierarchy in the package README). This document is the single architecture
deliverable requested by `CLAUDE-ARCHITECTURE-HANDOFF-PROMPT.md`. It authorizes
no runtime work by itself.

Contents: §1 product truth · §2 flow and state machine · §3 shell vs state
content · §4 component inventory · §5 layout/typography/palette/shadows ·
§6 voice contract · §7 processing/failure/lifecycle · §8 data model ·
§9 routes and services · §10 AI contract · §11 security and privacy ·
§12 responsive · §13 accessibility · §14 mismatch register · §15 acceptance
checklist · §16 implementation slices · §17 open owner decisions.

---

## 1. Product summary and truth boundaries

Opportunity Slate is a private, signed-in, single-role alignment workbench.
The member brings in one employer role, reviews the captured source, reviews
PeerSlate's proposed interpretation of the employer's statements, and explores
how their authorized evidence aligns with the Required and Preferred
qualifications. Everything is member-directed; nothing leaves the workbench.

Five data classes, never collapsed into one another:

| Class | Content | Truth owner |
|---|---|---|
| Employer source | The imported/uploaded/dictated role wording, preserved verbatim, versioned (`Source Version N`) | Employer wording; member confirms capture fidelity |
| AI proposals | Extraction concerns, statement classifications, interpreted structures, alignment statuses, evidence rationales | Proposals only; never canonical until member-confirmed, and alignment output is always labeled analysis |
| Member workbench inputs | Confirmed source version, confirmed requirement set (with member corrections), per-qualification responses (tell-us-more, connected evidence, real examples, confirm-not-have, skip) | Member |
| Authorized evidence | Confirmed Workshop knowledge items and Moments, referenced by key + version — never copied wholesale, never modified from here | Member, in their home surfaces |
| Saved slate | An explicit private snapshot: source version + confirmed requirements + analysis result + evidence references with bounded excerpts + response context | Member; created only by `Save privately` |

Binding truth rules (from the locked set, restated as architecture):

- Session-private until explicitly saved. `Save privately` is the only way any
  durable, member-visible record comes to exist. Nothing is ever published,
  shared, sent to an employer, or used to alter canonical evidence.
- Saved state and analytical currency are separate truths: a saved result
  remains identifiable and available for the inputs it was computed from, even
  after inputs change; new analysis is unsaved until explicitly saved.
- Qualification accounting is per-status counts only (`3 Supported · 2
  Partially supported · 1 Not enough information`). No overall score,
  percentage, recommendation, employer prediction, or traffic-light verdict —
  at any layer, including the API and the database.
- AI proposes; the member confirms. Voice never automatically submits,
  confirms, analyzes, saves, publishes, or navigates.
- Not a job board: one member-brought role at a time; no browsing, no
  employer-side surface, no route path containing `/job`, `/jobs`, `/hiring`,
  or `/listing` (guardrail-enforced by `tests/test_site_rules.py`).

**Ephemeral working state (explicit design decision).** Role sources exceed
cookie limits and uploads must be parsed server-side, so pre-save state lives
in a server-side *working session* record that is owner-scoped, never listed
anywhere, and expiry-bounded (proposed: 48 hours idle). "Session private —
nothing is saved yet" means exactly: no durable member-visible slate exists.
The working session is infrastructure, not a saved artifact, and must never
appear in any listing, export, or projection. Expiry is enforced at read
(an expired session is immediately inaccessible and the member starts
fresh); physical destruction is performed by the purge mechanism defined in
§8 — no background scheduler exists in this runtime and none is added.
Member-facing copy promises privacy and member control ("You decide what
happens next"), never a destruction timer.

**Homepage-impact check (required by the visual standard).** Determination,
2026-08-02: the logged-out homepage does not currently present, demonstrate,
or link Opportunity Slate, so this package triggers no homepage parity work.
Re-evaluate at the PS-OPS-001 Launch gate (§18); if the homepage then
claims the product, sequence a parity package per the standard's homepage
rule.

---

## 2. Final member flow and state machine

Primary flow (images 01→05): `ROLE_INTAKE → SOURCE_PROCESSING →
REVIEW_SOURCE → REVIEW_REQUIREMENTS → ANALYSIS_PROCESSING →
ALIGNMENT_UNSAVED → ALIGNMENT_SAVED`.

```text
                       paste/type/dictate ──┐ (same stage rail,
                                            ▼  truthful stage names)
ROLE_INTAKE ── upload ──► SOURCE_PROCESSING ── ok ──► REVIEW_SOURCE
   ▲   ▲       import ──►   (3 stages)                    │  ▲
   │   │                      │ cancel/fail               │  │ corrections,
   │   └── IMPORT_FAILED ◄────┘  (import path)            │  │ replace source
   │        (paste / upload / try again)                  │  │
   │                                                      ▼  │
   │                              confirm source ─► REVIEW_REQUIREMENTS
   │                                                      │  ▲
   │                                     confirm + analyze│  │ cancel analysis
   │                                                      ▼  │ restores editing
   │                                            ANALYSIS_PROCESSING
   │                                              │ ok        │ fail
   │                                              ▼           ▼
   │                                    ALIGNMENT_UNSAVED   ANALYSIS_FAILED
   │                                      │      ▲          (retry / review
   │                            save      │      │ reanalyze  inputs; inputs
   │                            privately ▼      │            preserved)
   │                                    ALIGNMENT_SAVED ◄─────────────┐
   │                                      │        │                  │
   └── delete (destroys working session   │        │ inputs changed   │
        and, from saved, the slate)       │        ▼                  │
                                          │   SAVED_STALE ── reanalyze┘
                                          │   ("Inputs changed ·
                                          ▼    Reanalysis required")
                                     DELETE_FAILED
                                     (remains visibly saved; try again / cancel)
```

State definitions and allowed actions:

| State | Image | Member actions |
|---|---|---|
| `ROLE_INTAKE` | 01, 06 | Type/paste; start/stop dictation; upload document; import public link; `Review source` (enabled only when text or a source exists) |
| `SOURCE_PROCESSING` | 07 | Every capture method passes through this state, because AI step 1 (§10) runs on pasted and dictated text too. Watch bounded stages — upload: Upload complete → Extracting employer wording → Preparing source review (image 07); paste/dictation: Text received → Checking wording for review → Preparing source review (truthful equivalents, §14-M13); `Cancel` returns to `ROLE_INTAKE` with prior inputs preserved |
| `IMPORT_FAILED` | 09-a | `Paste role text`, `Upload document`, `Try again`; "Nothing was saved or analyzed" |
| `REVIEW_SOURCE` | 02 | Read normalized source; resolve extraction concerns (voice/text corrected wording); `Open original`; `Compare with original`; `Replace source`; `Delete source`; `Return to role input`; `Confirm source` |
| `REVIEW_REQUIREMENTS` | 03 | Review statements grouped Required/Preferred/Responsibilities/Informational; per-statement rail: reclassify, read interpreted structure, clarify/correct (voice/text), `Apply correction`/`Cancel`; `Review source` (back); `Confirm requirements and analyze` |
| `ANALYSIS_PROCESSING` | 08 | Watch stages (Requirements confirmed → Checking authorized evidence → Preparing the evidence map); correction controls **read-only**; `Cancel analysis` restores editing in `REVIEW_REQUIREMENTS` |
| `ANALYSIS_FAILED` | 09-b | `Retry analysis`, `Review inputs`; confirmed source and requirements unchanged; "Results not generated · Nothing was saved" |
| `ALIGNMENT_UNSAVED` | 04 | Full workbench (see §4); `Save privately`; `Review inputs`; per-qualification responses; row selection drives the evidence rail |
| `ALIGNMENT_SAVED` | 05 | Same workbench component and geometry; saved banner "Saved privately · Current for these inputs"; `View saved details`; `Done for now`; delete available from saved details |
| `SAVED_STALE` | 09-c | Saved banner gains "Inputs changed · Reanalysis required"; `Reanalyze`, `View saved result`, `Review inputs`; the prior saved result remains identifiable for its source version |
| `DELETE_FAILED` | 09-d | `Try again`, `Cancel`; "It remains saved privately. Nothing was removed." |

Transition invariants:

1. Every arrow that runs an AI step or mutates durable state is an explicit
   member action (button/submit). No timer, no voice event, and no navigation
   triggers analysis, save, or delete.
2. Changing any confirmed input (source, requirement corrections) after
   analysis invalidates *currency*, never the saved snapshot. New analysis
   results enter `ALIGNMENT_UNSAVED`; the previous saved result remains
   reachable until the member saves again (new saved version) or deletes.
3. Failure states preserve every confirmed input and always offer a safe
   retry plus a non-AI fallback (paste/upload for import; review inputs for
   analysis).
4. `Back` (subheader) and `Done for now` leave the workbench without mutating
   anything; an unsaved analysis simply remains in the working session until
   expiry (stated plainly in the leave-state UI copy).

---

## 3. Shared shell versus state-specific content

**Shared shell (all states).** The real signed-in PeerSlate shell —
`templates/base.html` global header, nav, theme, footer — exactly as other
`/app` rooms use it. The images' simplified top nav is a rendering artifact
(§14-M1). Inside `block content`, Opportunity Slate owns a room-level
sub-shell present in every state:

- Subheader row: `← Back` + "Opportunity Slate" wordmark-style label only —
  no Ask Slate AI affordance (owner decision, §17-Q1; register M7).
- Left rail: state title (`Role · Bring a role`, `Review · Source`,
  `Review · Requirements`, `Alignment · Explore alignment`), supporting copy,
  and the session-truth card (`Session private` / `Saved privately` /
  failure-truth variants).
- Central workbench panel: one elevated card that hosts the state content.
- Right rail: contextual help (`What happens next`, `Supported sources`,
  `Import limitations`, `Original source`, `Review this statement`,
  `Evidence review`) — content varies by state, geometry does not.
- Footer strip inside the workbench: truth note (lock icon + plain sentence)
  left, secondary links center, one primary action right. Primary is disabled
  with a descriptive processing label during processing (`Preparing source…`,
  `Analyzing…`) while a `Cancel` link remains enabled.

From `REVIEW_SOURCE` onward the workbench adds the **context strip**: Role ·
Employer · Source · Version · Session chips (image 02/03/04/05), with
`Review inputs` appearing from `ALIGNMENT_*` states.

**State-specific content** is only what changes inside the workbench panel and
rails, per §2's table. Saved vs unsaved Alignment is one implementation
component with a state prop: banner, footer actions, and session chip differ;
geometry, cards, table, and rails do not (image 04 is the geometry authority;
image 05 supplies saved-state content/actions only).

---

## 4. Component inventory and ownership

New, owned by this package (templates under `templates/`, partials under
`templates/partials/opportunity_slate/`, styles in
`static/css/opportunity-slate.css`, behavior in
`static/js/opportunity-slate.js`):

| Component | Used in | Notes |
|---|---|---|
| `os-shell` (subheader + rails + workbench grid) | all | fills `base.html` blocks per the Workshop skeleton (`workshop.html:1-13`) |
| `os-context-strip` | 02–05 | chips with icon + label + value; `Review inputs` link slot |
| `os-truth-card` | all | lock/status icon + heading + sentences; variants: private, saved, warning, error |
| `os-intake-editor` | 01, 06 | textarea + mic button + dictation status line; upload and import tiles; info note |
| `os-source-doc` | 02 | normalized source with section headings, concern highlight spans |
| `os-concern-card` | 02 | original wording (read-only) + corrected wording (editable, mic-equipped) |
| `os-stage-rail` | 07, 08 | 3-step bounded stepper: done ✓ / active n / pending n; descriptive stage names; `aria-current="step"`; follows the `interview-studio.js` `setStage` idiom |
| `os-statement-list` | 03 | grouped, collapsible statement groups with counts; row select drives rail |
| `os-interpretation-tree` | 03 | Path A/B AND/OR structure blocks + plain-language explanation |
| `os-correction-rail` | 03, 08 | classification select + clarify/correct field (voice/text) + `Apply correction`/`Cancel`; read-only during analysis |
| `os-alignment-summary` | 04, 05 | Required/Preferred count cards (counts only, no aggregate) |
| `os-alignment-table` | 04, 05 | columns: # · qualification + explanation · status pill · authorized evidence (name + version) · review link; row selection state |
| `os-response-rail` | 04, 05 | "For this qualification" + five actions: Tell us more (voice/text), Connect existing evidence, Provide a real example, Confirm I do not have this experience, Skip. `Review my response` (image 04, under Tell us more) is the explicit apply step: it surfaces the composed response for member confirmation and only then stores it as the response for that qualification — the field alone never auto-commits |
| `os-filter-tabs` | 04, 05 | All · Supported · Partially supported · Not enough information filter row over the alignment table; present in both Alignment states (§14-M4) |
| `os-saved-details` | 05 (`View saved details`) | Saved-result versions list inside the workbench card grammar: source version, save time, open, and delete initiation per §7; no image authority — §14-M13 adaptation |
| `os-compare-original` | 02 (`Compare with original`) | Read-only in-page disclosure pairing the verbatim original wording with the normalized/corrected wording, section by section; no new route — data already serves with the source payload; keyboard accessible; §14-M13 adaptation |
| `os-evidence-rail` | 04, 05 | selected qualification detail: category, status, why-this-supports, what-remains-unestablished, evidence reference card, bounded excerpt |
| `os-status-pill` | 03–05, 09 | supported (green) / partially supported (amber) / not enough information (slate gray); classification chips |
| `os-saved-banner` | 05, 09-c | green saved card + `Current for these inputs` or `Inputs changed · Reanalysis required` chip |
| `os-fallback-card` | 09 | icon + heading + sentence + action row + truth footer; four variants |
| `os-footer` | all | truth note + secondary links + primary action; processing/disabled states |

Shared modules this package extracts or reuses (coordination points, not
rewrites):

- **`static/js/dictation.js` (new shared module, extracted from
  `static/js/interview-studio.js:1740-2060`).** Interview Studio's
  `SpeechRecognition` block is the only dictation implementation and is not
  currently reusable. Extract it behind the same behavior contract
  (insert-at-caret, `input` event dispatch, silence timeout, bounded
  restarts, status/interim/error hooks) and have Interview Studio consume the
  module unchanged. This is the one intentional touch of another room's code
  and is its own slice (§16, OS-5) with a focused regression run of the
  Interview Studio dictation tests.
- Stage-rail semantics from `interview-studio.js` (`setStage`,
  `[data-*-stage-rail]`, single `aria-current="step"`) — pattern reuse, not
  code import.
- Icon macro pattern from `templates/partials/workshop/_icons.html` — new
  `_icons.html` local to Opportunity Slate; do not extend Workshop's file.
- `services/database_service.py` — add new `usp_OpportunitySlate*` names to
  `ALLOWED_PROCEDURES` (shared file, additive lines only).
- `app.py` — blueprint registration, addition to the private-cache blueprint
  set (`app.py:573-584`), and post-registration rate-limit attachment for AI
  endpoints (`app.py:530-545` idiom). Additive, small, listed as a shared
  integration zone in every slice brief.

Explicitly not touched: Workshop routes/templates/CSS, Journal, Capture,
Interview Studio behavior (beyond the dictation extraction), `identity.py`,
`base.html` nav (no nav entry in v1 — §17-Q3/§18; the Owner Home card
arrives with the sign-in wall).

---

## 5. Layout, spacing, typography, palette, and shadow rules

Image 04 is the exact geometry authority; image 10 is the typography/palette
reference. Per the established room convention (`--wk-*`, `--jbook-*`,
`--ss-*`), Opportunity Slate defines a page-scoped palette `--os-*` under
`body.opportunity-slate-page`, seeded from the Foundation C tokens in
`static/css/style.css:81-92` — not bound directly to the global cascade.

- **Canvas and surfaces.** Cool porcelain canvas (`--os-canvas`, in the
  `#eef2fb` family per images/Workshop), near-white workbench surface
  (`--os-surface`), muted panel tint for secondary cards. `color-scheme:
  light` for v1, matching Workshop's locked light room (§14-M8).
- **Card system.** Separate elevated cards for the workbench panel and each
  rail card. **Uniform 12px vertical card spacing** inside the Alignment
  workbench (image 04's locked rule): `--os-card-gap: 12px`, applied as a
  single `gap` on card stacks — no ad-hoc margins. Card radius large-soft
  (~14–16px, matched visually to image 04 at implementation). Required
  qualifications, Preferred qualifications, Responsibilities, and
  Informational statements are **separate cards**, never merged.
- **Shadows.** Deep, soft, layered elevation per image 04 — follow the
  `--wk-shadow` / `--wk-shadow-sm` layering idiom (inset top highlight + two
  or three descending umbra layers in the `rgb(31 45 89 / n%)` family),
  tuned by side-by-side comparison against image 04. Image 05's flatter
  presentation must not be implemented.
- **Typography.** Display serif (Newsreader, already loaded site-wide by
  `base.html:95-98`) for state titles and workbench headings (`Role · Bring a
  role`, `Reviewed source`, `Employer statements`, `Alignment · Explore
  alignment`); Inter for UI, body, tables, and controls. Near-black navy ink
  for headings and primary text; muted slate for supporting copy.
- **Color semantics (locked).** `--os-ink` near-black navy; `--os-muted`
  slate; `--os-action` cobalt reserved primarily for actions, links, selected
  outlines, and important icons; `--os-success` green = saved/supported;
  `--os-warning` amber = partially supported / recoverable warning, with the
  documented `--os-warning` vs `--os-warning-ink` split (border/icon 3:1 vs
  text 4.5:1) copied from `workshop.css`; `--os-neutral` slate gray = not
  enough information. Status pills carry a leading dot + label, never color
  alone.
- **Selection.** Selected alignment row / statement row: cobalt outline +
  faint cobalt tint (images 03/04), `aria-selected` state, visible at 3:1
  against adjacent rows.
- **The blue-heavy palette, compressed spacing, and flattened cards of image
  05 are prohibited** (locked). One stylesheet serves both Alignment states.

---

## 6. Voice-first interaction contract

One dictation contract everywhere a mic appears (intake editor, corrected
wording, clarification field, tell-us-more response):

1. Voice and text edit **the same field**. Dictation inserts at the caret
   into the bound textarea and dispatches `input` so counters/autosave hooks
   fire — the extracted `dictation.js` behavior (§4).
2. Explicit start, explicit stop. Mic button toggles; listening state shows
   the status line ("Listening… You can keep typing while you speak.") and a
   visible `Stop voice input` control (image 06). Silence timeout ends
   listening with a status message — it never submits.
3. Voice never automatically submits, confirms, analyzes, saves, publishes,
   or navigates. No voice commands exist in v1; speech is transcription only.
4. The transcript stays editable indefinitely; helper copy "Type or speak.
   Your transcript stays editable." appears with every mic-equipped field.
5. Mic availability is progressive enhancement: no `SpeechRecognition` →
   mic button hidden or disabled with an honest tooltip; typing is always
   sufficient. Microphone permission denial surfaces a bounded error hook,
   never a broken state.
6. Accessibility: mic button has an accurate `aria-label` and
   `aria-pressed`; listening status is `aria-live="polite"`; the pulsing
   listening glow respects `prefers-reduced-motion` (static ring under
   reduced motion).

---

## 7. Processing, failure, lifecycle, and reanalysis behavior

**Processing.** Both processing states are bounded three-stage steppers with
descriptive, truthful stage names, rendered locally inside the workbench
(images 07/08) — never a modal, overlay, or navigation. Implementation is
synchronous request(s) + client stage rail (the proven `setStage` pattern);
there is no background-job system in the runtime and this package does not
introduce one. Stage transitions reflect real request boundaries (e.g.
upload complete → extraction call in flight → review render); stages never
display invented partial results. During `ANALYSIS_PROCESSING` the correction
rail and statement controls are read-only (visibly disabled, not hidden;
image 08 + locked rule); `Cancel analysis` aborts the in-flight request
(`AbortController`) and restores editing. Cancel is always enabled while the
primary action shows its processing label.

**Failure.** Image 09 defines all four fallback contracts:

| Failure | Truth line | Actions | Server guarantee |
|---|---|---|---|
| Public-link import unavailable | "Nothing was saved or analyzed." | Paste role text · Upload document · Try again | No partial source persisted |
| Upload extraction failure (corrupt/unreadable PDF, DOCX, TXT) | "We couldn't read this document." + "Nothing was saved or analyzed." (09-a pattern; §14-M13) | Paste role text · Upload a different document · Try again | No partial source persisted; the failed upload's bytes are discarded |
| Analysis failure | "Results not generated · Nothing was saved." + "Your confirmed source and requirements are unchanged." | Retry analysis · Review inputs | Confirmed inputs untouched; no partial result rendered or stored |
| Saved + inputs changed | "The saved result remains available for Source Version N. It does not apply to your changed inputs." | Reanalyze · View saved result · Review inputs | Currency flag only; snapshot immutable |
| Delete failure | "It remains saved privately. Nothing was removed." | Try again · Cancel | Delete is atomic; a failed delete leaves the slate fully intact and visibly saved |

AI-unavailable (Anthropic outage) maps to the analysis-failure contract with
honest copy; the member's confirmed inputs, responses, and any saved slate
remain fully readable and editable without AI — the core experience degrades
to review-and-respond, never to a blank or broken page.

**Save lifecycle.** `Save privately` creates an immutable saved-result
version: pinned source version, confirmed requirement set, full analysis
output, evidence references pinned to item+version with bounded excerpts, and
the member's response context. Footer copy states exactly what saving does
and does not do (image 04/05 wording). Saving does not move, flatten, close,
or regenerate the evidence workspace — the member stays in place; banner,
chip, and footer switch to saved state.

**Currency and reanalysis.** Currency = fingerprint comparison between the
saved result's pinned inputs (source version, requirement-set version, the
evidence reference versions inside the snapshot) and the current working
inputs plus current versions of referenced evidence. Match → "Current for
these inputs." Mismatch → `SAVED_STALE` chip; explicit `Reanalyze` runs a new
analysis into `ALIGNMENT_UNSAVED` alongside the still-identifiable prior
saved result. Saving again writes a new saved version; prior saved versions
remain identifiable (View saved details lists them by source version and
save time). Nothing is ever silently overwritten or auto-reanalyzed.

---

## 8. Data model and persistence

No ORM exists; follow the house pattern exactly: hand-written idempotent
T-SQL in `SQL FIles/Migrations/proposed/PS-OPPSLATE-001_opportunity_slate.sql`
with `*_rollback.sql` and an owner-isolation `Verification/` script;
owner-scoped stored procedures registered in
`services/database_service.ALLOWED_PROCEDURES`; frozen-dataclass service
(`services/opportunity_slate_service.py`) with `_require_exact_fields` row
discipline, `rowversion` optimistic concurrency, and idempotency ledgers for
create/save — all mirrored from `services/knowledge_service.py` and
`PS-WORKSHOP-001_knowledge_items.sql`.

Proposed tables (names final at implementation; shapes are the contract):

- `dbo.opportunity_working_sessions` — the ephemeral pre-save workbench:
  `working_session_key` (opaque UUID), `owner_profile_id`, workbench state
  enum (§2 states), `expires_at_utc`, `row_version`. One active working
  session per member (v1, §17-Q2). **Purge is new in-scope work (no
  maintenance mechanism exists in this runtime today):** expiry is enforced
  at read (expired = inaccessible, member starts fresh), and physical
  deletion runs through an owner-scoped procedure
  (`usp_PurgeExpiredOpportunityWorkingData`, shipped in the OS-1 migration)
  invoked opportunistically at the start of any Opportunity Slate request
  for that owner, plus manually via the documented ops path when needed.
  Retention split on expiry or explicit discard: all pre-save child rows —
  source and source versions, requirement sets, analyses, responses — are
  deleted, **except** version rows pinned by a saved result, which the saved
  slate owns durably from the moment of save. Uploaded blobs follow the
  established Capture split: the procedure deletes rows and returns opaque
  cleanup locators; the service layer deletes the blobs.
- `dbo.opportunity_sources` + `dbo.opportunity_source_versions` — employer
  wording. Version rows are append-only: `capture_method`
  (`pasted|dictated|uploaded|imported`), original verbatim text, normalized
  text, original filename/URL where applicable, uploaded original stored as
  a private blob (photo-capture storage pattern: `DefaultAzureCredential`,
  no SAS), `sha256_digest`, extraction-concern spans (bounded JSON),
  member-corrected wording per concern with the original always retained
  (the Capture voice pattern: immutable provider record + member-approved
  text).
- `dbo.opportunity_requirement_sets` + `_versions` — the confirmed
  requirement set: statements with employer wording, AI-proposed class +
  interpreted structure (bounded JSON: AND/OR paths of atomic clauses),
  member corrections (reclassification, clarification text, structure
  acceptance), and confirmation metadata. AI proposal fields and
  member-confirmation fields are separate columns — provenance is never
  collapsed.
- `dbo.opportunity_analyses` — one row per analysis run: pinned source
  version + requirement-set version, per-statement results (status ∈
  `supported|partially_supported|not_enough_information`, explanation,
  why-supports, what-remains-unestablished), evidence references
  (`evidence_kind ∈ knowledge_item|moment`, evidence key, pinned version,
  bounded excerpt), model/prompt-contract version for provenance, counts
  derived — **no aggregate score column exists by design; a CHECK-style
  review at PR time keeps one out**.
- `dbo.opportunity_responses` — member responses per statement:
  `response_kind ∈ tell_more|connect_evidence|real_example|confirm_not_have|
  skip`, response text, `authored_via ∈ typed|spoken` (Workshop's provenance
  enum), connected evidence reference where applicable.
- `dbo.opportunity_slates` + `dbo.opportunity_saved_results` — the durable
  member-visible slate (created on first save) and its append-only saved
  snapshots: pinned versions of everything in §7's save contract plus
  `input_fingerprint` for currency. `visibility` CHECK-pinned to
  `N'private'` exactly like `knowledge_items.visibility` — there is no
  audience model on this surface, by design.
- `dbo.opportunity_save_requests` — idempotency ledger keyed
  `(owner_profile_id, idempotency_key)`.

Evidence is referenced, never copied: reads go through new read-only
owner-scoped procedures over confirmed knowledge items (and Moments when
included, §17-Q2 scope note); the only copied material is the bounded excerpt
inside a saved snapshot, retained for identifiability of what the analysis
saw. Opportunity Slate writes no Workshop or Moment table. The future
Workshop `knowledge_item_uses` ("used elsewhere") ledger is W4 scope in the
Studio lane; when it exists, saved-slate evidence references should register
there — recorded here as a named cross-lane integration point, not built now.

Migration prerequisites mirror the house guards (`THROW` if PS-AUTH-001 /
PS-WORKSHOP-001 absent, since evidence reads depend on `knowledge_items`).

---

## 9. Route and service contract

New blueprint `opportunity_slate` in `opportunity_slate_routes.py`. Room path
for v1 is the **public** `/opportunity-slate` (owner decision §18), following
the Interview Studio public-room precedent (`/interview-studio`,
`app.py:1456`). For the record: there is no `/app`-wide signed-out redirect —
Workshop's public session is deliberately explorable at `/app/workshop` — so
the top-level path is a positioning choice (public-first room), not an auth
necessity. Its real consequence: `robots.txt` carries `Disallow: /app`, so a
top-level route forfeits that crawl umbrella — **§18 safeguard 4 (noindex
header/meta, no sitemap entry) is therefore mandatory, not optional.** The
path satisfies the route-language guardrail; when the sign-in wall lands, the
route decision returns to the deferred site-rules route map. Signed-in
members and anonymous visitors use the same routes; mode is derived
server-side from optional identity (`get_optional_identity`), never from
client input. Shape (paths below shown relative to the room root):

| Route | Purpose |
|---|---|
| `GET /opportunity-slate` | State-routed shell: intake, resume working session, or saved view (anonymous: public session mode per §18) |
| `POST …/source` | Set/replace pasted or dictated source text |
| `POST …/source/upload` | Upload PDF/DOCX/TXT (bounded, §11) |
| `POST …/source/import` | Public-link import (guarded, §11) |
| `POST …/source/corrections` | Apply a concern correction |
| `POST …/source/confirm` | Checkpoint 1 confirm |
| `POST …/source/delete` · `…/source/replace` | Source lifecycle within the working session |
| `POST …/requirements/corrections` | Reclassify / clarify a statement |
| `POST …/requirements/confirm` | Checkpoint 2 confirm + start analysis |
| `POST …/analysis` (or `/analysis/retry`) | Run/retry analysis; returns full validated result |
| `POST …/responses/<statement_key>` | Save a member response action |
| `POST …/save` | Create saved result (idempotency key) |
| `POST …/reanalyze` | Explicit reanalysis from saved-stale |
| `POST …/delete` | Delete saved slate (atomic) |
| `GET …/saved` | View saved details (versions list) |
| `GET …/source/original` | Serve the retained original (owner-scoped) |

Contract rules (all house patterns, verified in runtime), **mode-aware per
§18**: flag check `PEERSLATE_OPPORTUNITY_SLATE_ENABLED` (default off)
**outermost, before any identity resolution**, neutral 404 on every route.
Room routes resolve mode via `get_optional_identity`: signed-in → the
private workbench; signed-out → the §18 public session. Owner-only routes —
upload, import, save, delete, saved details, `source/original`, and
server-side response persistence — require identity and return a neutral
404 signed-out (`require_identity_or_not_found` semantics); anonymous mode
never reaches a database procedure, and every procedure remains
owner-scoped regardless. Opaque UUID keys normalized with the
`_normalize_*` null-on-failure idiom; same-origin write guard mirroring
`workshop_routes._is_same_origin_write` on all POSTs, both modes; blueprint
added to the private-cache set in `app.py` plus its own `after_request`
`Cache-Control: private, no-store` (anonymous responses carry signed state
tokens, so no-store applies in both modes); `DatabaseServiceError` → 503
with inputs preserved, `AuthenticationRequired` handled separately;
optimistic-concurrency `changed` outcome re-renders with member text
intact; AI endpoints rate-limited via the post-registration
`limiter.limit` wrapper in both modes; no route may leak whether another
member's key exists.

Services: `opportunity_slate_service.py` (persistence + lifecycle),
`opportunity_source_intake_service.py` (upload extraction + link import with
its security contract), `opportunity_analysis_service.py` (AI calls +
validators). Server-rendered pages with focused JS (dictation, stage rail,
row selection, fetch+abort) — Workshop proved the mostly-server-rendered
shape; Alignment interactivity justifies bounded JS, not an SPA.

---

## 10. AI contract

Reuse the validated-proposal discipline exactly as built in `app.py`'s
interview endpoints: single synchronous `client.messages.create` per step →
`_extract_json_object` → **strict dedicated validator** → 502 with honest
copy on any malformed reply; nothing partial ever renders or persists.

Three AI steps, each its own prompt contract with a version string persisted
alongside output:

1. **Source extraction review** (`REVIEW_SOURCE` prep): normalize captured
   wording into sections; flag potential extraction concerns as
   character-span references into the verbatim source. It proposes concerns;
   it never rewrites the employer's wording.
2. **Statement interpretation** (`REVIEW_REQUIREMENTS` prep): segment the
   confirmed source into statements; propose class (required / preferred /
   responsibility / informational) and interpreted structure (AND/OR paths of
   atomic clauses). Validator enforces: every statement maps to verbatim
   source spans; class ∈ enum; structure references only its own statement's
   clauses.
3. **Alignment analysis**: server-side grounding — the prompt receives the
   confirmed requirement set plus a server-selected allowlist of the member's
   confirmed evidence (id, title, version, bounded body) and **may only cite
   allowlisted evidence ids**; the validator rejects any unknown id (the
   `allowed_evidence_ids` pattern from `/api/interview/review`). Output per
   statement: status enum, explanation, why-supports, remains-unestablished,
   cited evidence + excerpt spans. The validator also rejects any aggregate
   field — scores, percentages, recommendations — as a schema violation, and
   rejects fabricated metrics/employers/titles by construction (grounding
   list is the only evidence vocabulary).

**The no-aggregate rule binds prose, not only keys — and OS-3 is where that
matters most.** Slice OS-2 implemented the rule as a recursive check over
every *key* of every reply (`_reject_aggregate_fields`), on the reasoning that
a member's or an employer's own wording may legitimately contain "score" or a
percentage while a machine-readable field carrying one may never exist. Its
independent review (finding F3) established that this is necessary and not
sufficient: `explanation`, `clauses`, and a concern's `reason` are
**model-authored**, so a reply of `{"explanation": "You are an 85% match for
this role."}` satisfied a keys-only rule completely. OS-2 added
`_reject_aggregate_prose`, a scan bound to a judgement about a person rather
than to a number, so that ordinary employer wording ("travel up to 25% of the
time", "a satisfaction score above 90%") still validates.

**The OS-2 prose scan operates at HIGH PRECISION, not high recall.** Architect's
decision after four rounds of correction, each of which introduced a defect its
own tests missed. The two error types are not symmetric at OS-2. A false
positive is expensive and certain: budget is reserved **before** the provider
call and the scan runs **after** it, so a refusal burns the visitor's free daily
allowance, shows a generic failure card, and fails identically on retry because
the wording is the employer's own — and job adverts are written in the second
person, so the triggering wording is ordinary. A false negative at OS-2 is
nearly harmless, because steps 1 and 2 receive only the employer's source text
and so the model has nothing to ground a verdict about a person in. The scan is
therefore **defence in depth**: it makes the rule structurally true where a
model unmistakably addresses the reader, and it deliberately lets
judgement-shaped prose pass. Measured: **zero false positives across 616
legitimate sentences (498 unique), 36% recall on the verdict side.** Round 5
lowered recall on purpose: an independent audit of 461 sentences found the card
rule refusing ordinary advert headings ("Ideal candidate: strong communicator")
and the "`<metric>` of `<a thing>`: `<verdict>`" form, so its uninspected tail,
its superlative `candidate|applicant` label and its quality-valued
verdict/recommendation label were **deleted rather than made cleverer**. Do not
restore them to raise recall.

**Slice OS-3 must not inherit a keys-only rule, and must not inherit this scan
either.** Steps 1 and 2 are given no fact about the member. Step 3 receives an
allowlist of the member's confirmed evidence and writes `explanation`,
`why_supports`, and `remains_unestablished` about a real person against real
requirements — it is the first step in this package structurally capable of
producing a **grounded** verdict, and therefore the step where a lexical scan
stops being adequate.

**OS-3 needs a STRUCTURAL control, not a stricter scan.** Earlier revisions of
this section said OS-3 must apply "a stricter scan". That guidance is withdrawn
as wrong: five rounds proved regex tuning does not converge, and each tightening
bought recall by paying in false positives the visitor cannot see, cannot fix,
and pays for. Candidates for OS-3's architect:

* **Constrain the output schema** so free prose about the member is not
  representable — bounded enumerated fields plus citations of specific evidence
  records, with no field able to hold a sentence that judges a person.
* **And/or a separate verification pass** over the generated text, with its own
  contract and failure mode, before any of it reaches a member.
* **And/or grounding constraints** that make an ungrounded claim invalid by
  construction — every assertion must resolve to a cited evidence record or the
  reply is malformed.

The lexical scan is retained **at OS-2 only, as defence in depth**. It must not
be treated as sufficient anywhere member facts are in scope.
`OS-2_COMPLETION_REPORT.md` section 4 residual 5 lists, by class and with
measurements, every judgement-shaped sentence the scan now allows through.

Member responses (`Tell us more`, real examples) enter later reanalysis as
member-attributed context, clearly separated in the prompt from authorized
evidence; analysis output must attribute support drawn from responses as
member statements, not as evidence records.

Model selection: runtime AI endpoints currently standardize on
`claude-haiku-4-5-20251001` (`app.py`). Steps 2 and 3 are
higher-consequence reasoning; the implementer runs the routing document's
availability check at implementation time and selects the model tier with
recorded evidence (quality on a fixture role vs. cost/latency), rather than
inheriting the chat default silently. Rate limits: mirror the interview
budget (≤ 6/minute per member on analysis; import/extraction similarly
bounded).

Ask Slate AI: none in this package (owner decision, §17-Q1). If a future
package adds a workbench assistant, it must follow this same proposal
discipline and never mutate workbench state.

---

## 11. Security, privacy, and authorization

- Mode is server-derived on every route (`get_optional_identity`), never
  asserted by client input; every procedure owner-scoped (`@UserKey →
  owner_profile_id` re-asserted in each predicate) with an owner-isolation
  verification script proving cross-owner reads return nothing — the
  standing house bar. Anonymous mode never reaches a database procedure.
- All responses `private, no-store`; opaque keys; neutral 404s. Flag-off is
  indistinguishable from not-found on every route. Owner-only routes (§9
  list) are additionally indistinguishable signed-out
  (`require_identity_or_not_found` semantics); room routes serve the §18
  public session signed-out by design.
- **Upload intake** (new capability, follow `photo_capture_service`
  verbatim): declared-MIME allowlist (PDF/DOCX/TXT), bounded read
  (`MAX + 1`), magic-byte verification, per-route `max_content_length`
  override, text-extraction with hard output caps (proposed 60k units),
  extraction library additions pinned in both requirements files (guardrail:
  `DependencyPinTests`), no macro/script evaluation (structure-only parsing),
  original stored privately with `sha256_digest`, upload never executed or
  served back with an executable content type (`GET …/source/original`
  forces `Content-Disposition: attachment` semantics or safe inline PDF with
  strict CSP as implemented for capture originals).
- **Public-link import is the highest-risk new surface (SSRF).** Contract:
  `https` only; resolve and validate the target (public unicast only — reject
  private, loopback, link-local, and metadata ranges, and pin the validated
  IP for the actual fetch to defeat DNS rebinding); no redirects across the
  validation boundary (re-validate every hop, cap at 3); response size and
  time caps; HTML-to-text extraction only, no script evaluation, no asset
  sub-fetches; fetched content treated as **untrusted data, never
  instructions** — it flows only into the extraction prompt contract with the
  concern-flagging output schema. v1 may additionally restrict to a supported
  ATS/employer domain allowlist ("supported public employer or ATS page" is
  the locked copy) — implementer proposes the list; independent review is
  mandatory for this slice regardless.
- Prompt-injection posture: employer sources are adversarial inputs by
  definition. System prompts state that source content is data; validators
  (§10) are the enforcement layer — schema violations, out-of-allowlist
  evidence ids, or aggregate fields fail closed with the analysis-failure
  contract.
- No egress: nothing on this surface sends anything to an employer or any
  third party; the only outbound calls are Anthropic (existing) and the
  guarded import fetch.
- Secrets/config unchanged: `ANTHROPIC_API_KEY` env-only; no secret names in
  client JS (guardrail-enforced); no hardcoded owner identifiers in the new
  service modules (guardrail-enforced).
- Rollback/stop: the feature flag is the stop control; migrations ship with
  rollback scripts; delete is atomic with the image-09 failure truth.

---

## 12. Responsive behavior (desktop, 200% zoom, 320px reflow)

The locked set is desktop-only; the following reflow rules are the
architecture's documented non-material adaptation (flagged in §14-M9 for
Pete's acceptance at visual review):

- **Desktop (≥1200px).** Three-zone grid per image 04: left rail ~260px,
  workbench fluid center, right rail ~300px; 12px card gap throughout.
  **Superseded per screen by the owner parity rounds, 2026-08-03.** The
  locked primaries do not share one proportion, and the difference is the
  design rather than drift: measured off the PNGs, image 01's workbench holds
  53.2% of its frame and image 02's holds 64.6%, because screen 1 is an intake
  form that wants air around its paste box and screen 2 is a reading document
  that wants the width. Image 02 gets there by shrinking its rails *and*
  widening its centre — its left rail measures 197 CSS px against image 01's
  227, with the rail type a notch smaller to match. Built: intake rails
  235/249 with a ~55px gap (53.3%), review rails 196/176 with a ~29px gap
  (64.6%), the review geometry carried by `.os-layout--review` and gated on
  the same condition that selects `_review.html`. Locked by
  `test_each_screen_carries_its_own_layout_proportion`.
- **Intermediate (~900–1200px and 200% zoom).** Rails leave the columns in
  document order: left-rail state title + truth card render above the
  workbench (compact row), right-rail content renders below the workbench as
  full-width cards. Nothing hides; nothing requires horizontal scroll. 200%
  zoom at 1280px must produce this single-column flow with all functions
  reachable (WCAG 1.4.10 reflow at effective 320–640px widths).
- **Narrow (≤640px, incl. 320px).** Single column. Context strip wraps to a
  two-per-row chip grid. The alignment table restacks: each qualification
  becomes a card (number + wording, status pill row, evidence reference,
  review link) preserving reading order # → wording → status → evidence.
  The response rail and evidence rail become in-flow disclosure sections
  beneath the selected qualification card, preserving the select→detail
  relationship. Footers stack with the primary action full-width last.
  Steppers compress to vertical. Touch targets ≥ 24×24 CSS px (2.5.8).
- No fixed heights on text containers; long employer statements, long
  evidence titles, and long member responses wrap without truncation
  (long-content evidence is a named acceptance state).

---

## 13. Accessibility requirements (WCAG 2.2 AA)

- Semantic structure: one `h1` per state; card headings in a correct
  hierarchy; statement groups as headed regions; the alignment table as a
  real `<table>` with `<th scope>` (desktop) and an equivalent labeled
  structure when restacked.
- Keyboard: every action reachable and operable; row selection via
  focusable row controls with `aria-selected`; selecting a row moves
  context to the rails without stealing focus; visible focus ≥ 3:1
  (2.4.11–13 aware); no keyboard trap in the correction rail; `Esc` closes
  transient disclosures only.
- Status communication: status pills = dot + text, never color alone;
  stage rails use one `aria-current="step"` plus `aria-live="polite"`
  announcements at stage change; save/failure banners announced politely;
  processing disables controls with `aria-disabled` + descriptive labels.
- Forms: every field labeled; concern-correction pairs associate original
  and corrected wording programmatically (`aria-describedby`); errors named
  in text with focus moved to the first failure; optimistic-concurrency
  conflicts re-render with member text intact and an explained message.
- Contrast: navy ink and muted slate on porcelain meet 4.5:1; amber uses
  the `--os-warning-ink` text-safe value; cobalt on white ≥ 4.5:1 for text
  and ≥ 3:1 for UI outlines; disabled processing labels remain ≥ 3:1
  against their control.
- Motion: mic pulse, stepper transitions, and card hover elevation gated by
  `prefers-reduced-motion`.
- Voice accessibility per §6; dictation is an enhancement over a fully
  keyboard-operable text path.

---

## 14. Mismatch register — generated-image details implementation must correct

| # | Image detail | Correction |
|---|---|---|
| M1 | Simplified top nav (`Pete's Slate · Community · Interview Studio · Workshop`), no search/theme/My Slate cluster | Use the real `base.html` signed-in shell verbatim; nav content is whatever the shell renders for the member. "Pete's Slate" is fixture labeling |
| M2 | Image 05's flatter cards, compressed spacing, blue-heavy palette | Prohibited (locked). Saved state renders in image 04 geometry via the same component |
| M3 | Image 08 shows the correction rail visually active during analysis | Rail and statement controls are read-only during analysis (locked rule); visibly disabled, restored by Cancel |
| M4 | Filter tabs (`All · Supported · Partially supported · Not enough information`) appear only in image 05, absent from image 04 | Implement the filter row in **both** Alignment states (same component, image 04 geometry). Bounded adaptation flagged for Pete's confirmation at visual review (§17 note; not one of the three questions) |
| M5 | Decorative 3D props (paper stack, magnifier, stone) in the rail margins | **Superseded by owner decision, Pete, 2026-08-03** (`OWNER_VISUAL_REVIEW_2026-08-03.md`, finding V3): the props are implemented. Route 1 was taken — cropped from the locked authority PNGs, background-normalised to the room canvas and alpha-feathered, saved as `static/images/opportunity-slate/prop-source-review.png` and `prop-ambient-stone.png`. They are decorative only: `alt=""` + `aria-hidden="true"`, hidden below the three-column layout, and locked as never-content by `test_the_decorative_props_are_never_content`. This is not an implementation invention; it is the owner accepting the locked set's own artwork |
| M6 | Fixture content: Northrop Grumman role, counts (6/4/7/3), evidence names, excerpt text | Signed-in content is member-derived at runtime; anonymous mode uses only the clearly labeled §18 demo evidence fixture. Nothing from the images is seeded or hardcoded (guardrail: no owner identifiers in services) |
| M7 | "Ask Slate AI" button rendered as if live | Owner decision 2026-08-02 (§17-Q1): the subheader chrome is image artifact — no Ask Slate AI affordance is implemented; the subheader ships with Back + title only |
| M8 | Images are light-theme only | v1 room is light-scoped (`color-scheme: light`), the locked Workshop precedent; dark-theme treatment is a future ChatGPT-lane decision |
| M9 | No mobile/tablet frames in the locked set | §12 reflow rules are the documented adaptation; Pete accepts them on the real build at visual review, or routes a mobile set back to the ChatGPT lane. **Judged properly for the first time in the third parity round, 2026-08-03**, having previously been checked only for absence of overflow. Four adaptations were made and none changes the dominant object, action, hierarchy, type family or colour language: (a) the intake paste box holds five visible lines instead of `rows="10"` plus 5rem of reserved mic space, which made an empty box ~370px tall at 390, and the mic comes to a 48px target — `rows="10"` stays on the element so the no-CSS rendering is unchanged; (b) the two import tiles lay as aligned rows rather than two tall centred columns, which had given the most vertical space on the screen to the two things that are honestly unavailable; (c) the extraction-concern card moves ahead of the source document in **source order**, so when it stacks it is read and seen before the text it annotates rather than after it, and it drops the float elevation outside the container query where it no longer floats; (d) the footer's two *reveal* links are hidden below 640px, where the disclosures they point at sit a few pixels above them — the controls stay visible, focusable and operable, so no capability is removed. At 320 the workbench padding comes in to 0.9rem and the document sets a step down, because at that width padding is worth more as measure than as margin. Evidence: `compare-04-*`, `compare-05-*`, which set the desktop authority beside the phone build precisely because no mobile authority exists to match |
| M10 | Dashed connector lines between concern highlight and correction card (image 02) and between selected statement row and the review rail (image 03) | Implement as adjacency + shared accent + programmatic association, not a literal drawn connector; must survive reflow. **Settled for OS-1 by the empty state (2026-08-03, second parity round):** with nothing flagged there is no phrase to point at, and a leader landing on an arbitrary line of the member's own wording would imply PeerSlate had picked it out. Adjacency is the card sitting in the reading column's own margin, level with the top of the document; the shared accent is the rule on the card's leading edge, which takes the amber when OS-2 has a real concern; the association is the `<aside>` named by the card's heading, which is a real `h3`. Locked by `test_the_extraction_concern_card_is_tied_to_the_source_it_describes` |
| M11 | AI-generated text artifacts (odd hyphenation, spacing) in image body copy | Copy deck at implementation follows the images' meaning with corrected typography; trust-critical sentences (session-private, saved, failure truths) are reproduced exactly as written in the READ-ME rules |
| M12 | Stepper numerals/checkmarks vary slightly between images 07 and 08 | One `os-stage-rail` component with a single visual grammar (done ✓ / active numeral / pending numeral) |
| M13 | **Authority-gap adaptations** — member-reachable surfaces and copy the locked set implies but never shows | Documented non-material adaptations built strictly from this handoff's established component grammar, accepted by Pete on the real build at visual review: (a) the `View saved details` versions view (§4/§7); (b) the `Compare with original` disclosure (§4); (c) delete/replace confirmation moments (reuse the house confirm pattern, e.g. Workshop's delete-confirm page shape); (d) leave-state copy for `Back`/`Done for now` with an unsaved analysis (§2 invariant 4); (e) truthful paste/dictation stage names in `SOURCE_PROCESSING` (§2); (f) the upload-extraction failure card (§7, image 09-a pattern). None may introduce new composition, hierarchy, or interaction language; if one grows beyond this grammar, it returns to the ChatGPT lane |
| M14 | Image 05 merges Responsibilities and Informational statements into one collapsed card ("Responsibilities and informational statements · 10") | The locked separate-cards rule wins (README locked rules; handoff prompt): Responsibilities and Informational statements remain separate cards in both Alignment states. Do not import the merge as "saved-state content" |
| M15 | Image 02 puts the source-detail card at the top of the **right** rail | Owner instruction, 2026-08-03 finding V14: it moves to the **left** rail, between "Why review the source" and the session-truth card — the placement image 03 uses for its own source card. The right rail's standing help simultaneously loses its card chrome (see M16), so the rail is lighter rather than merely emptier. This is a documented owner-directed placement change, not a hierarchy change: the same data, the same actions, the same reading order |
| M16 | Images 01/02 give the right rail plain help sections with hairline rules, and reserve a card for state-specific data | Implemented as drawn (2026-08-03 parity pass). The first OS-1 pass boxed all three standing-help sections, which is the overloaded right rail and cramped centre behind owner findings V14/V15 |
| M17 | Image 02's extraction-concern card carries an AI-proposed flag, the flagged phrase, and a corrected-wording pair | The card's placement, geometry, elevation and type ship in OS-1; its content does not, because OS-1 runs no AI. It renders a truthful empty state — "Extraction concerns / None flagged / PeerSlate has not read or analyzed this source" — and deliberately does **not** use the authority's amber concern treatment while there is no concern. Locked by `test_the_extraction_concern_card_never_claims_a_concern`. **Placement corrected 2026-08-03 (second parity round):** the first attempt gave the card a grid column, which sized the reading column from the leftover width and pinched it to ~460px. Image 02 divides the workbench's 755px inner width 68.5% reading column / 4.1% gap / 27.4% margin, holds the body copy at that one measure from first line to last, rules the title block off at the column's edge rather than the workbench's, and runs the card 17px into the workbench gutter. The build now does the same: `--os-measure` (32rem) governs the heading, the lead and the document; the card is laid over the margin in the same grid cell, so the row takes the taller of the two and a card taller than the source cannot overflow; and a container query on the workbench — not a viewport breakpoint — stacks the card below a 700px workbench, because the same 1200px viewport is a 1057px workbench without rails and a 534px workbench with them. **Completed 2026-08-03 (third parity round).** Two things were still wrong. First, the measure was a fixed 32rem, which was correct for an 826px workbench and wrong once the workbench took image 02's own 64.6%: the column stayed put while the margin grew, so widening the screen made the quiet space beside the card worse. The measure, the card width and the gap are now image 02's ratios (68% / 28.3% / 4.9%, card bleeding ~1% past the inner edge), which keeps the reading column at 60–72 characters from the 700px container threshold to 1600px — a fixed card was 28% of the workbench at 1440 but 38% of it at 1280. Second, the empty state was four lines tall against a 602px document. It was given substance under a hard truth constraint: no fabricated concern, no implication that analysis has run, no amber treatment while nothing is flagged, and specifically **no promise about what PeerSlate will detect in OS-2**, which would be a specification invented at the stylesheet level and read by a member as a capability that exists. What it says instead is what the member is being asked to check, in the present tense. Result: card 442px, residual gutter 160px on a 602px document — 27%, against the authority's own 26%. The card stays top-aligned rather than centred or offset: it is a reading instruction, so it must be visible when reading starts, and an offset that flatters a long posting strands it below a short one (`member-12`). Locked by the extended `test_the_extraction_concern_card_never_claims_a_concern` |
| M18 | Image 01/02's microphone is a live dictation control | Rendered to the authority (large cobalt glyph, white disc, periwinkle halo) but honestly inert until slice OS-5: `aria-disabled`, an accessible name ending "(not available yet)", a `title` reason, `cursor: not-allowed`, an always-visible text note, and a deliberately quieter halo with no outer glow so the live control will be distinguishable from it |
| M19 | Image 01's workbench surface is a warm cream | Owner instruction, 2026-08-03 findings V2/V5/V16: "you've got a yellow flow center, it should be a white but with texture." **Revised the same day by the owner's second-round decision: "Make it an off white that has texture."** Pure white was wrong in the other direction — against this cool canvas it sampled bluer than the authority's own paper (R−B = −2, where image 01 measures +2 and image 02 is neutral). `--os-surface-paper` is `#fcfbf8`, a warm-neutral off-white at R−B = +4 and 252 lightness; the originally rejected `#f7f6f1` was +6 at 247. Procedural inline-SVG paper grain at 5%–7.5% over a top-lit sheen, whose foot moved from a cool `#f3f7fd` to a warm-neutral `#f4f3f0`. No external asset and no new dependency. The move off white cost ~0.25 of contrast ratio on every text pair, which took `--os-neutral` under 4.5:1 as text, so `--os-neutral-ink` (`#656e88`) was added for neutral TEXT uses on the same split `--os-warning`/`--os-warning-ink` already uses |

---

## 15. Implementation acceptance checklist (mapped to images)

Per the lean visual standard: side-by-side comparison per state, correct
drift before review, Pete's final acceptance on the corrected real build.

- [ ] **01 Role intake:** serif title; editor with placeholder + mic; upload
  and import tiles with `or` divider; info note; footer "Nothing analyzed
  yet…" + disabled-until-input `Review source`; left/right rail copy.
- [ ] **06 Voice active:** listening status + `Stop voice input`; transcript
  editable while listening; no auto-advance on stop; reduced-motion ring.
- [ ] **07 Source processing:** file chip + ✓; three named stages; "Nothing
  is being analyzed yet."; `Cancel import` live while primary shows
  `Preparing source…`.
- [ ] **02 Review source:** context strip; normalized sections; concern
  highlight + original/corrected pairing with mic; right-rail original
  source + `Open original` / `Compare with original` / `Replace source` /
  `Delete source`; footer truth line + `Return to role input` / `Replace
  source` / `Delete source` / `Confirm source`; checkpoint 1-of-2 label.
- [ ] **03 Review requirements:** grouped statements with counts;
  classification chips; selected-row outline; interpretation tree (Path
  A/B, AND/OR) + plain-language explanation; clarify/correct with mic +
  `Apply correction`/`Cancel`; footer "Analysis begins only when you
  explicitly confirm…" + `Confirm requirements and analyze`; checkpoint
  2-of-2 label.
- [ ] **08 Analysis processing:** three named stages incl. "Nothing is being
  saved, published, shared, or sent to an employer."; correction controls
  read-only; `Cancel analysis` restores editing.
- [ ] **04 Alignment unsaved (exact geometry authority):** 12px uniform card
  gap; separate Required/Preferred/Responsibilities/Informational cards;
  count summaries without any aggregate; amber `Results not saved` truth
  card; response rail with all five actions incl. `Review my response` as
  the explicit apply step; evidence rail with why-supports /
  remains-unestablished / reference + excerpt; `Save privately` footer with
  exact scope copy; shadows/depth match.
- [ ] **05 Alignment saved (content/actions only):** green `Saved privately`
  banner + `Current for these inputs`; session chip `Saved privately`;
  `View saved details` + `Done for now`; footer save-truth copy; geometry
  still image 04; filter row behavior per M4.
- [ ] **09 fallback sheet:** all five §7 fallback contracts — the four
  image-09 states with exact action sets and truth lines, plus the
  upload-extraction variant (M13-f); delete failure leaves the slate
  visibly saved.
- [ ] **Cross-cutting:** color semantics (§5) hold on every state; voice
  contract (§6) on all four mic surfaces; §12 reflow at 1280/200%, 768, 390,
  320; §13 checks; no score/percentage/verdict anywhere; guardrail suites
  and new contract tests green.

Evidence set per the standard: named desktop + narrow screenshots per state,
200% zoom, reduced-motion, long-content, processing, failure, and recovery
captures, plus the §14 register resolution status.

---

## 16. Implementation slices and staffing

Owner staffing decision (2026-08-02): **Opus 5 (Extra High) sole runtime
writer**; fresh **Fable 5 (Extra High)** independent review at the Protected
triggers; **Pete** final visual acceptance. Slices are sequential unless
noted; each is one branch, one writer, complete-diff self-review, focused +
guardrail tests, per the lean workflow.

| Slice | Scope | Path / triggers |
|---|---|---|
| OS-1 | Flag, blueprint, public route + room shell, working-session model + migration (incl. the purge procedure, §8), paste/type intake, Review Source (verbatim, corrections without AI concern-flagging), confirm checkpoint 1, **anonymous public mode with the §18 safeguards (demo evidence fixture, signed-context state, limits, noindex, spend guard)** | Protected (schema/migration + identity/flag surface + new public boundary, per the workflow's path table) ⇒ independent review of the schema/isolation and public-safeguard contracts |
| OS-2 | AI steps 1–2: extraction concerns, statement interpretation, correction rail, confirm-and-analyze gate | Protected (consequential AI) ⇒ review |
| OS-3 | Alignment: analysis engine with evidence grounding, workbench (table, rails, responses), processing + failure states | Protected (consequential AI + cross-referenced private data) ⇒ review |
| OS-4 | Save-privately lifecycle: saved slate + versions, currency, reanalyze, delete + delete-failure, saved details | Protected (deletion) ⇒ review |
| OS-5 | Dictation extraction into `static/js/dictation.js`; wire all four mic surfaces; Interview Studio regression | Bounded (shared-code touch) ⇒ focused review of the extraction diff |
| OS-6 | Upload extraction (PDF/DOCX/TXT) + public-link import with the §11 SSRF contract and fallback states — **signed-in-only surfaces in v1 (§18 safeguard 1)**. New extraction dependencies must be validated against the Azure App Service Python 3.14 runtime before pinning — the local venv is 3.13 and no staging app exists; this repository has previously hit the passes-locally/dies-at-boot failure class | Protected (shared infrastructure/security) ⇒ review |

OS-5 and OS-6 can run after OS-1 in parallel with OS-2/3/4 only if a second
writer is explicitly assigned; default is one writer, sequential. The flag
stays off in production throughout; enablement runs through PS-OPS-001's
lifecycle gates (§18 — Launch for the new public audience, Candidate as
applicable) after Pete's visual acceptance of the complete primary flow on
the real build, with the §15 evidence set.

---

## 17. Owner decisions (asked as the three permitted questions; resolved by Pete, 2026-08-02)

**Q1 — Ask Slate AI: not required.** Pete's decision: the subheader chrome in
the generated images — including the Ask Slate AI button — is visual-round
artifact, not a product requirement. Ignore it. No Ask Slate AI affordance
ships with this package; slice OS-7 is removed. The site-rules "signed-in
umbrella" concept is untouched and remains a separate future decision.
(This supersedes the "remains available in the subheader" line carried from
the visual set's READ-ME; the package README is annotated accordingly.)

**Q2 — One slate, v1.** Confirmed: one active Opportunity Slate per member
with versioned saved results; re-entry lands on the saved/working state; a
new role starts by explicit replace-with-confirmation. No index surface.
Moments remain in scope as evidence references for the signed-in mode.

**Q3 — Entry point: superseded by the public-v1 decision (§18).** For now
Opportunity Slate is publicly reachable at a direct link with no nav entry;
`Back` returns to the site root. The Owner Home card arrives with the
sign-in wall ("we will do that soon" — Pete), at which point Back targets
the workspace.

## 18. Public v1 access mode (owner decision, Pete, 2026-08-02)

Pete's direction: do not hide Opportunity Slate behind the sign-in ("owner")
wall yet. Like Workshop's public session mode, it is live-but-unlisted —
reachable by direct link only, for Pete and a small circle — with real
safeguards because the route is public. The private architecture in §§1–16
is unchanged and remains the destination state once the sign-in wall lands;
this section defines only the v1 public posture layered in front of it.

**Two modes, one implementation** (the Workshop and Interview Studio
precedents combined):

- **Signed-in members** get the full private workbench exactly as
  architected: server-side working session, real authorized evidence,
  `Save privately`, the complete lifecycle.
- **Anonymous visitors** get a truthful public session: same screens, same
  flow, banner-labeled like Workshop's public preview (nothing is stored);
  alignment runs against a clearly labeled fixture demo evidence library
  (the Workshop demo-library pattern — never presented as the visitor's own
  evidence); working state is held client-side with signed context tokens
  (the Interview Studio `itsdangerous` pattern) so the server persists
  nothing for anonymous use; `Save privately` is not offered anonymously —
  in its place an honest note that saving arrives with membership. Session
  ends → nothing retained anywhere. Mechanics, so the implementer does not
  guess: the carrier is `URLSafeTimedSerializer` signed context tokens (the
  verified `interview_context_serializer` precedent, `app.py:88`);
  transport is fetch JSON bodies bounded by the 2 MB `MAX_CONTENT_LENGTH`
  (not the 500 KB form-memory path), with safeguard-2 input caps bounding
  every payload well below that; page refresh rehydrates from client-held
  state (`sessionStorage`) when present and otherwise resets honestly to
  intake; anonymous mode requires JavaScript and says so plainly in a
  `noscript` note.

**v1 safeguards (all required before the flag turns on):**

1. **Anonymous intake is paste/type/dictate only.** Document upload and
   public-link import are signed-in-only until the wall lands — this keeps
   the SSRF and file-parsing attack surface off the anonymous public route
   entirely. The tiles render with an honest "available with membership"
   state, not a broken control.
2. **Rate and size limits**: Interview Studio's limiter budget as the floor
   (≤ 6/minute per client on each AI endpoint), hard input caps (role text,
   correction text, response text), and bounded token budgets per call.
3. **A kill switch and a spend guard**: the feature flag remains the stop
   control; an env-configured daily AI-call ceiling for the anonymous mode
   fails closed into the §7 analysis-failure contract (honest copy, no
   partial results).
4. **Unlisted posture**: `noindex` (X-Robots-Tag and meta) on the public
   route while unlisted; no nav link; no sitemap entry.
5. **Truth labeling**: anonymous mode never claims persistence, privacy of
   a saved slate, or that demo evidence is the visitor's own. All §1 truth
   language holds; the public banner makes the mode explicit.

**Owner direction, Pete, 2026-08-02 — the two-mode audit.** When the
sign-in-wall shift begins, its package opens with a **two-mode audit across
all pages**: every page verifies that it has a truthful anonymous branch
(labeled fixture/demo, nothing persisted) cleanly separated from its
signed-in real branch, before any route gate flips. Pages that fail the
audit are corrected inside that package, not walled as-is. This is recorded
here because the wall package does not exist yet; carry it into that
package's entry gate when it is created.

**Slice impact** (§16 amended accordingly): OS-1 now delivers the public
route with the anonymous mode and safeguards 1–5 alongside the signed-in
foundation; OS-4 (save lifecycle) is signed-in-only by construction; OS-6
(upload + import) ships as signed-in-only surfaces; OS-7 is removed per
§17-Q1. Turning the public route on runs through PS-OPS-001's lifecycle
gates — **Launch** (this opens a new public audience), with **Candidate**
as applicable for its Protected change classes — against the §15 evidence
plus these safeguards.

---

*End of handoff. Independently reviewed at `9e423de`, corrections rechecked
Pass at `184e5ca`. §§17–18 record Pete's 2026-08-02 decisions and the public
v1 posture; their delta review (Conditional at `14364d1`) was corrected and
rechecked Pass at `5c38d61`. Awaiting Pete's final acceptance.*
