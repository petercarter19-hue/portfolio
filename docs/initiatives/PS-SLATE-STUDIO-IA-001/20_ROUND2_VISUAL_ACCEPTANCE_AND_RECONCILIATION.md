# Round-2 visual acceptance and architecture reconciliation

**Initiative:** PS-SLATE-STUDIO-IA-001
**Recorded by:** Claude Code (Fable architecture lane), 2026-08-01
**Source:** owner-supplied `PeerSlate-Workshop-Visual-Handoff-2026-08-01.zip`,
package-copied and hash-pinned at
`visual-authority/workshop-approved-2026-08-01/`
**Status:** documentation only. No runtime code, route, schema, migration,
flag, deployment, or live capability.

## 1. Authority status

Files `03`–`10` are the **Pete-approved corrected visual direction**, approved
in the ChatGPT/Codex visual lane on 2026-08-01 per the package's
`00_READ_ME_FIRST.md` and `ASSET_MANIFEST.md`. All ten SHA-256 hashes were
recomputed on package copy and match the originating manifest exactly. This
record completes the durable hash-pin; the approved set is the binding visual
authority for the states it draws.

Files `01`–`02` are **composition reference only**. They are byte-identical to
the round-1 candidates (hashes match), and their navigation, browser chrome,
competing primary actions, and Type/Speak tabs are explicitly superseded.
**Consequence: the Workshop opening and the direct-entry composer have no
current approved visual authority.** See §4.

The round-1 candidate set at `visual-authority/workshop-candidate-2026-07-31/`
is now historical evidence in its entirety.

## 2. Doc 19 findings — resolution map

| Doc 19 item | Resolution in the approved set |
|---|---|
| **Blocker: no final-review / `Save privately` screen** | **Delivered** — `04` desktop, `08` mobile: "Review what will be saved," editable final wording, classification, source with `View original` (D1 honored), AI-use permission, single primary `Save privately`, `Keep working` / `Save unfinished` exits |
| **D6: résumé card superseded** | **Delivered** — `05`: "Use this elsewhere — Coming later" with Résumé-page content / My Story / Feed each badged `Coming later`; `Close for now` is the primary; save stated as complete |
| M1 wording drift between screens | Resolved — `04`, `05`, `06` show the identical saved wording |
| M2 `Back to skills` phantom state | Resolved — back link is now `Choose another starting point` |
| M3 mic vs Type/Speak tabs | Resolved structurally — **Type/Speak tabs are eliminated product-wide**; one composer with inline mic and submit arrow (`10`, six states) |
| M4 review CTA hierarchy | Resolved — primary is `Review final wording`, leading to the new consent screen; `Improve with AI`, `Save unfinished`, `Stop for now` are secondary |
| M5 destination-card dominance | Resolved — see D6 row above |
| M6 privacy-reassurance repetition | Resolved — one `PRIVATE SAVE` card plus item-level rows |
| M7 filter ambiguity | Resolved — labeled `Area` and `Status` rows; selection is blue-filled and unmistakable, clearest in `09` |
| M8 blanket source line | Resolved — related information is a collapsible per-item block |
| Nav placeholder | Resolved by owner decision — real navigation is **Pete's Slate · Community · Interview Studio · Workshop** |
| URL in browser chrome | Resolved — no URL is drawn; the route remains an architecture decision |
| Voice states | Delivered — `10`: ready, listening, transcribing, transcript-ready (editable before submit), failed with retry, microphone-off; text entry always available; long-form editors keep their screen-level action |
| Mobile | Delivered for review, final-review, and My Information as full-page captures |

The truth banner on `03` — "Nothing is saved as confirmed information until you
choose Save privately" — plus the transcript-editable-before-submit voice state
give the D1 decision its honest mechanics end to end.

## 3. OPEN — the AI-use default conflict (Pete decision required)

The creating lane explicitly refused to resolve this and routed it here; it
must not be decided by inference.

- **Owner decision D2** (doc 16, 2026-08-01): a saved item defaults to
  *available for private PeerSlate suggestions*.
- **The approved visuals** (`04`, `05`, `08`): `Do not use as context` is drawn
  as the **selected default**, and `06` shows the item with AI use off and
  `Use as context — Unavailable — AI use is off`.

These cannot both be the default. Implementation of the save flow cannot start
until Pete picks one; the schema (`ai_use_permission` default) follows the
answer.

The approved visuals also **unify the permission semantics**, which the
architecture adopts regardless of the default: one per-item AI-use permission
governs both (a) whether the item may ground private suggestions and (b)
whether it is *available* for explicit session-context selection. `not_allowed`
disables both; session use additionally always requires the member's explicit
per-session selection. This replaces the architecture's earlier
two-concept description and simplifies it. The suggestion card's grounding
language ("information you previously allowed it to use") matches.

## 4. OPEN — opening and direct-entry authority gap

The approved journey starts at the review screen. The **Workshop opening**
(the four-door rail with Spark and the open thought entry) and the
**direct-entry composer** exist only in superseded reference files.

Consequences for sequencing:

- **W1's checkpoint page is My Information** (`06` + `09`) — fully approved.
- W1 direct entry can be assembled from approved components (`04`'s layout, the
  `10` composer pattern, `05`'s confirmation) **only with Pete's explicit
  acceptance of that assembly**, or after a small ChatGPT visual addition.
- **W2 cannot start its session-opening work** until a corrected opening visual
  is created by the ChatGPT lane and Pete locks it. The corrected opening must
  use the real navigation, the four doors, the no-tabs composer, and a single
  primary action.

The four-door rail in the approved screens (`Continue where I left off` /
`I brought something` / `Work on something` / `Give me a spark`) matches the
Pete-approved doc 13 inventory. Per that inventory, `I brought something`
starts an honest handoff to separately authorized intake paths or explains
unavailable intake — it must render the honest unavailable state until Capture
integration is separately authorized.

## 5. Owner process instruction — first-page checkpoint (2026-08-01)

Pete's instruction, recorded verbatim in effect: when implementation produces
the **first main page** — no other states or pages — work **stops** and Pete
receives a side-by-side comparison of the real rendered page against the exact
approved mockup, including the mockup image itself, for his visual acceptance
before implementation continues.

This is added to slice W1 as a hard gate (doc 18). Given §4, the first main
page is **My Information**, compared against
`06_APPROVED_desktop-my-information.png` and
`09_APPROVED_mobile-my-information.png`.

## 6. Delivery-lane effort correction

Pete's 2026-08-01 clarification supersedes the effort phrasing in doc 16 §5:
implementation is **Claude Sonnet 5 at max effort**; independent review is
**Claude Opus 5 at max effort**. Architecture remains Claude Fable 5. The
routing-document update (Opus 4.8 → Opus 5) remains owed as a
documentation-only change with a shared-file reservation.

## 6a. Owner confirmations of 2026-08-01 (same session, after this record)

- **A1 resolved.** Pete confirmed the route: Workshop ships at `/app/workshop`;
  `/app` (Owner Home) convergence stays deferred to the later combining phase.
  Doc 17 §A1's recommendation is adopted as decided.
- **Checkpoint page confirmed.** The W1 first-page checkpoint is the
  My Information main page as a single rendered page (desktop and mobile),
  compared side-by-side with mockups `06` and `09`. Pete explicitly does not
  need interaction states or click-through views at the checkpoint — the main
  page only.
- **§3 RESOLVED — owner decision, 2026-08-01 (same session):** AI use of
  confirmed private information is **always on, with no member-facing toggle at
  all**. Pete: it should be behind the scenes; "that's just part of our site."
  This supersedes both D2's default-allowed *and* the approved visuals'
  default-off control. Consequences:
  - The `ai_use_permission` column, its stored procedure, and every
    permission-control UI element are **removed from the design**. AI grounding
    uses all confirmed, non-archived items. Everything remains private;
    this permission never affected publishing or sharing.
  - "People decide" is preserved through the controls that remain: explicit
    save consent, edit, **archive** (which removes an item from AI grounding),
    and delete.
  - **Owner-directed visual amendment:** the AI-use permission radio/rows on
    approved screens `04`, `05`, `08` and the AI-use row, `Use as context —
    Unavailable` block, and `Change permission` link on `06`/`09` are removed.
    The screens otherwise stand as locked. The session-scoped `Use as context`
    selection on the review screens is a relevance choice, not a permission,
    and **stays**. The round-3 opening visual should reflect this amendment.
  - Doc 16 §D2 is superseded by this stronger decision and stands as history.

## 6b. Owner checkpoint acceptance and W1 continuation (2026-08-01)

- **The W1 first-page checkpoint PASSED.** After one correction round driven
  by Pete's six findings (right-rail/column alignment, info-card height,
  square chips, full desktop sweep, mobile rebuild) plus two architect-caught
  mobile ordering fixes, Pete reviewed the final desktop and mobile
  comparisons and accepted: "These are great. They're improved. Keep going.
  Finish this off." Implementation is authorized to complete slice W1 through
  release.
- **Owner reminder recorded:** verify the navigation-bar integration is
  correct. Remaining nav work in W1: the `#nav-search-data` entry, and
  repointing the two stale `/app` Workshop references
  (`auth_routes.py` `workshop_url`, Studio section nav partial).
- **Direct-entry composition (§4) — exercised interpretation:** Pete's
  "finish this off" is read as acceptance that W1's direct-entry flow is
  assembled from approved components (the `04` final-review layout minus AI
  panels, the `10` composer pattern, the `05` confirmation), subject to his
  final visual acceptance of the complete W1 build before merge. If he
  rejects the assembly at final acceptance, it returns to the ChatGPT lane.
- **Accepted documented adaptations from the checkpoint rounds:** the four
  status chips wrap at 390 px rather than shrinking below readable size; the
  left rail ends above the aligned band (matches the mockup); the
  info-disclosure panel renders open.
- **Routing exception disclosed:** one mobile-ordering micro-fix was applied
  by the Fable architect lane after a Sonnet agent stalled on infrastructure
  before editing (commit `af3f193`). All other runtime code in the slice is
  Sonnet-lane work.

## 7. States still owed by implementation, not by mockups

Per the approved package's own README: 320 px reflow, 200% zoom, visible
focus, touch targets, reduced motion, long content, loading, empty,
AI-unavailable, and failure/permission behavior are proved in the browser
implementation against the approved visual language. They do not require
additional mockups. The architecture's §11 requirements bind them.

## 6c. W1 build, review, and release record (2026-08-01/02)

- Slice W1 implemented per docs 17/18: knowledge store (migration
  `PS-WORKSHOP-001`), My Information with real search/filters, direct entry
  with explicit save consent, edit/archive/restore/delete, honest states.
- Independent Opus review: **Conditional** (2 Blockers, 3 Majors, 6 Minors,
  15 test gaps) — all corrected by the Sonnet lane. Focused recheck:
  **Conditional** with two required truth fixes (hardcoded shown-count;
  zero-match copy overclaiming), both applied exactly as specified with
  pinning tests at `4e0e17a`. Optional deeper fix (filter inside the SQL
  window) deferred to a later slice by design; recheck notes recorded.
- Live staging rehearsal on `peerslate-staging`: apply → verify → rollback
  → reapply GREEN 3×; three genuine engine defects fixed (nested
  INSERT-EXEC, INSERT-EXEC result-set shape, rollback-guard false
  positive).
- Owner acceptances: first-page checkpoint; corrected set; depth rounds 2–3
  ("more depth" → approved dial, chips flat, canvas washes + grain);
  final ten-image evidence set delivered to the owner's records.
- Owner enablement decision: flag ON immediately after deploy verification
  so external reviewers (friends) can use it; each sees only their own
  private library. W2 (Work on Something) remains gated on the ChatGPT
  round-3 opening lock, in progress.
- Full suite at release: 1268 passed, 3 skipped.
- Exact merge/pipeline/production-migration/enablement facts are recorded
  in the W1 completion report and its closeout addendum.

## 6d. Public preview mode (owner decision 2026-08-02)

- **Owner instruction:** "Workshop must not be behind a login right now."
  Pete is showing the site to friends pre-launch; clicking Workshop
  redirected to sign-in, and he wants the surface immediately visible and
  explorable. Sign-in comes later.
- **What changed:** the sign-in gate is removed, for now, from three routes —
  `GET /app/workshop`, `GET /app/workshop/add` (and its review step), and
  `POST /app/workshop/items`. A signed-out visitor gets the real page over
  honestly-labeled SAMPLE content on the library (reusing the existing
  `get_my_information_checkpoint` fixture, never a second sample source) or
  their own typed text through add/review. The confirming save never writes
  and never says "Saved privately" — it renders an honest preview-complete
  state that keeps the member's text visible and explains that saving needs
  an account, with a clear sign-in action.
- **What did not change:** flag-off still resolves to a neutral 404 before
  any identity resolution, on every route, signed-out included. A
  `DatabaseServiceError` while resolving identity is never treated as "just
  signed out" — it still renders the truthful 503 recovery state. No
  anonymous request ever reaches `list_knowledge_items_for_owner`,
  `get_knowledge_item_for_owner`, `save_knowledge_item_for_owner`, or any
  other `*_for_owner` service method, and none reaches a stored procedure —
  the public preview path is entirely separate, in-process, and
  database-free. Edit/Archive/Restore/Delete stay behind sign-in: the
  sample library items simply carry no action URL, the same inert-row
  treatment the pre-existing `PEERSLATE_WORKSHOP_DEV_FIXTURE` seam already
  used, so those controls render visibly preview-only rather than either
  pretending to mutate or opening a fake edit flow for data with no real
  backing record. The dev-fixture flag/banner itself is untouched — public
  preview is a separate code path with its own banner style
  (`wk-status-banner--preview`) and its own checkpoint identity
  (`_PREVIEW_IDENTITY`, never the dev-identity seam).
- **Real accounts and saving return when sign-in is added later** — this is
  explicitly a temporary, owner-directed relaxation of the architecture's
  general "signed out looks like flag off" posture (doc 17 §6), scoped to
  these three routes only, for the pre-launch friends-and-family showing.
- Implementation: `workshop_routes.py` (`_build_preview_view`,
  `_preview_item_view`, `_render_anonymous_preview_saved`,
  `_PREVIEW_IDENTITY`), `templates/workshop.html`,
  `templates/workshop_add.html`, `templates/workshop_review.html`,
  `templates/workshop_saved.html`,
  `templates/partials/workshop/_preview_note_card.html`,
  `static/css/workshop.css`. New `WorkshopPublicPreviewTests` class plus
  updates to the two tests that asserted the now-superseded signed-out
  redirect for the library/add routes.

## 6e. Public demo library (owner instruction 2026-08-02)

- **Owner instruction:** "Workshop's public preview is live but its sample
  library is only four thin items... build a rich, realistic demo knowledge
  base so anyone can open Workshop with no account and genuinely play with
  it — add items, edit, archive — and see it behave like the real product."
- **What changed:** the four-item checkpoint fixture (§6d, reused from
  `get_my_information_checkpoint`) is replaced, for the anonymous path only,
  by a new 17-item sample library: `services/workshop_demo_library.py`. The
  persona is **Jordan Ellis**, a fictional healthcare-technology
  professional — deliberately not Pete, in a different field, so nobody
  reads it as a real profile. Content mirrors the real knowledge-base
  categories in `docs/knowledge/` (accomplishments, career history, skills
  evidence, technical skills, personal story, portfolio projects) and
  exercises every Area (Work/Personal/Both/Not set) and Status
  (Confirmed/Suggested/Unfinished/Archived) filter, long and short wording,
  and one item (#1, "Rebuilt patient intake from 40 minutes to 9") with real
  3-version edit history. All content is fixed, deterministic (stable UUID
  keys, fixed literal timestamps) — no randomness, no wall-clock reads —
  matching this module's own docstring.
- **Session play:** a visitor's own Add/Edit/Archive/Restore/Delete now
  really takes effect, but ONLY inside their own signed Flask session
  cookie (namespaced `workshop_preview`), layered over the static base
  library — never a database, never shared between visitors, never
  permanent. Every route that used to sign-in-redirect a signed-out caller
  (`edit_information`, `keep_working_edit`, `review_edit`, `update_item`,
  `archive_item`/`restore_item` via `_run_item_state_change`,
  `delete_confirm`, `delete_item`) now treats `AuthenticationRequired` the
  same way `my_information`/`add_information` already did in §6d — exactly
  mirroring that existing pattern rather than inventing a new one. Every
  existing guard is unchanged: the flag check still runs first, same-origin
  is still required on every POST, and the five state-changing routes keep
  their existing per-minute rate limits (app.py wraps them by endpoint name,
  so nothing needed to change there).
- **Hard caps** (a signed cookie is ~4KB): at most 4 visitor-added items and
  400 characters of wording per preview item, enforced server-side. A cap
  violation renders an honest inline message ("Preview holds up to 4 added
  items — sign in for an unlimited private library.", or the equivalent
  400-character wording message) and preserves the visitor's typed text —
  never a silent drop, never a silent truncation. Measured worst case (4
  items at both caps, near-random-entropy wording) is well under 3KB
  end-to-end (`tests/test_workshop_demo_library.py`).
- **Honesty preserved:** the persistent preview banner, composer/review
  banners, and the confirming-save screen were all reworded so nothing ever
  claims "Saved privately" for an anonymous visitor. They instead say the
  item is in the sample library for this browser session only, that it
  disappears when the session ends, and that signing in is what makes it
  permanent. `_render_anonymous_preview_saved` now also links back to the
  library (`view_in_my_information_url`) so a visitor can see their own
  addition in place.
- **What did not change:** flag-off still 404s before any identity
  resolution; a `DatabaseServiceError` still renders the truthful 503; no
  anonymous request of any kind (library, add, edit, archive, restore,
  delete) ever calls a `*_for_owner` service method or reaches the
  database — session-only mutation is a parallel, self-contained code path
  in `services/workshop_demo_library.py`, never a fork of the real
  read/write methods in `services/knowledge_service.py`. The dev-fixture
  seam (`PEERSLATE_WORKSHOP_DEV_FIXTURE`, `get_my_information_checkpoint`,
  and its own tests) is completely untouched — a deliberately separate,
  still-fixture-backed local-preview path. Signed-in behavior is
  byte-for-byte unchanged on every route.
- **New required config:** `app.secret_key` (Flask's session signing key,
  previously unset anywhere in this app) is now set in `app.py`, using the
  same deterministic-fallback idiom as the existing
  `INTERVIEW_CONTEXT_SIGNING_KEY` — a dedicated `PEERSLATE_SESSION_SECRET_KEY`
  env var if set, else a value derived from the already-required
  `ANTHROPIC_API_KEY`, so no new mandatory production secret is required.
- Implementation: `services/workshop_demo_library.py` (new module);
  `workshop_routes.py` (`_build_demo_library_view` replaces
  `_build_preview_view`/`_preview_rows`/`_preview_item_view`;
  `_render_anonymous_preview_saved` reworked; every edit/archive/restore/
  delete route gains an anonymous branch); `app.py` (`app.secret_key`);
  `templates/workshop.html`, `workshop_add.html`, `workshop_review.html`,
  `workshop_saved.html`, `workshop_delete_confirm.html`,
  `partials/workshop/_preview_note_card.html` (copy updates). New
  `tests/test_workshop_demo_library.py` (`WorkshopDemoLibraryContentTests`,
  `WorkshopDemoLibraryMergeTests`, `WorkshopDemoLibrarySessionSizeTests`)
  plus ten new methods on `WorkshopPublicPreviewTests` and two updates to
  existing methods there for the new persona content and the now-real
  unfinished-save redirect.

## 6f. Visual facelift accepted — supersedes the round-3 shadow dial (owner acceptance 2026-08-02)

- **Owner instruction:** Pete accepted a further visual facelift produced by
  the ChatGPT visual-creation lane, hash-pinned at
  `visual-authority/workshop-facelift-2026-08-02/` (README plus 17 PNGs,
  `R01`–`R17`; see that folder's `ASSET_MANIFEST.md` and `SHA256SUMS.txt`).
  Track 1 (this implementation slice) applies the facelift to the **live**
  Workshop screens only: My Information/library (`R11`, `R12`), Add
  information (`R13`), Review & save (`R14`), and Saved/private (`R15`,
  `R16`). `R01`–`R10` and `R17` are the accepted **W2 (Work-on-Something)**
  authority for the later session-opening slice gated in §4 above — they are
  hash-pinned now, alongside the rest of the accepted set, but are not built
  by Track 1.
- **Supersession, explicit:** the facelift's softer, layered-shadow language
  (matte white cards, soft multi-layer shadow recipe, subtle icy
  concentric-ring/dot canvas texture, navy ink typography, royal-blue
  primary actions) **replaces** the round-3 "more depth" heavy shadow dial
  recorded in §6c ("more depth" → approved dial, chips flat, canvas washes +
  grain). The round-3 dial was correct for its moment; this is a newer,
  owner-accepted visual-direction decision and controls going forward. Chip
  geometry (12px squares, flat fill) is unchanged by either round and stays
  as-is.
- **Scroll-cap adaptation:** the owner separately approved a desktop-only
  behavioral adaptation — the My Information item-list column gets an
  internal scroll (`max-height` bound to the detail-column region,
  `overflow-y: auto`) once the list exceeds the space the three-column
  layout affords, so the three content columns stay visually balanced
  regardless of library size. This is a responsive/interaction adaptation
  within the locked composition (doc `AI_WORKFLOW.md`'s "non-material
  accessibility, truth, focus, or reflow adaptations are allowed when
  documented"), not a new composition, hierarchy, or dominant-action change.
  It applies only above the existing ≤1100px stacking breakpoint, where the
  three-column desktop layout is in effect; below it the existing
  single-column stack is unaffected. The "Showing X of Y" footer stays
  outside the scrolling region so counts are never hidden.
- **Known gap carried into Track 1:** the accepted set has no desktop
  reference for library, add, or review (`R11`–`R14` are mobile-only). `R15`
  (saved/private) and `R09` (AI-review canvas, token reference only) are the
  only desktop facelift compositions. Track 1 therefore applies the
  facelift's token system to the **existing, already-implemented** desktop
  compositions for My Information, Add information, and Review & save as a
  documented adaptation — layout and composition are unchanged; only
  surface/shadow/texture/type/action-color tokens change. See the asset
  manifest's "Known gap" section for the full statement.

