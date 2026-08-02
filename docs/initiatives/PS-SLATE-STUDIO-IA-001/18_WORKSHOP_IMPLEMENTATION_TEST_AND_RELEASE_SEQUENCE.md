# Workshop — implementation, test, and release sequence

**Initiative:** PS-SLATE-STUDIO-IA-001
**Migration/package id for runtime work:** `PS-WORKSHOP-001`
**Author:** Claude Fable 5 (architecture lane), 2026-08-01
**Controlling architecture:** `17_WORKSHOP_PRODUCT_AND_TECHNICAL_ARCHITECTURE.md`
**Status:** PROPOSED sequence. No slice below is activated. Documentation only.

## Sequencing rule

Do not build the knowledge store, the AI session, Spark, and downstream
destination use in one branch. Build one end-to-end truth path at a time while
preserving the final architecture. Each slice is independently releasable behind
`PEERSLATE_WORKSHOP_ENABLED`, default off.

The order below is deliberate: the store and the library come first because they
are the product (owner decision D5), they are provable without any AI, and they
are what makes the AI slice safe to add.

---

## Slice W0 — Entry gate and allocation

**Output:** no product behavior.

- Resolve architecture decision **A1** (route: recommendation is `/app/workshop`;
  `/app` convergence deferred) with the designated manager or Pete.
- Resolve architecture decision **A2** (v1 ships no destination writes; the
  résumé/Story data home is a separate later package).
- ~~Obtain the corrected, Pete-locked visual authority~~ **Satisfied
  2026-08-01** for the drawn journey: the approved set is hash-pinned at
  `visual-authority/workshop-approved-2026-08-01/` (files 03–10). See doc 20.
- ~~Resolve the **AI-use default conflict**~~ **Resolved 2026-08-01 (doc 20
  §6a): AI use is always on with no member-facing toggle.** No permission
  column, procedure, or UI; archive/delete are the removal controls.
- Name one manager and exactly one writer; create a fresh branch from current
  `origin/main` and reserve exact files.
- Confirm no overlap with `PS-HOME-FRONTEND-001` (`/app`, Owner Home shell),
  `PS-JOURNAL-001` (`moments`), or the active Codex community lanes.
- Update `docs/AI_MODEL_AND_ROLE_ROUTING.md` Claude reviewer row from
  Opus 4.8 to Opus 5 (documentation-only; requires a shared-file reservation).

**Exit:** one writer and branch, resolved A1/A2, Pete-locked visuals, no
unresolved file-ownership or canonical-data conflict.

---

## Slice W1 — Private knowledge store and My Information

The foundation. Proves ownership, isolation, provenance, and lifecycle with **no
AI involved at all**.

**Includes:**

- `PS-WORKSHOP-001` migration: `knowledge_items` and `knowledge_item_versions`,
  with guarded rollback and owner-isolation verifier.
- Owner-scoped procedures for list, get, save, update, archive, and delete;
  all registered in `ALLOWED_PROCEDURES`.
- `services/knowledge_service.py` plus serializer with exact-shape validation and
  output caps; contract `workshop-knowledge.v1`.
- `GET /app/workshop` rendering the **My Information** mode: search, Work /
  Personal / Both lenses, Confirmed / Suggested / Unfinished / Archived states,
  item detail with provenance and edit history,
  archive, restore, and delete.
- **Direct entry and editing** — a member can create and confirm an item with no
  AI step. This is what makes the AI-unavailable promise real.
- Navigation entry after Interview Studio, signed-in and flag-gated, in the
  desktop list, the mobile mirror, and the nav search data.
- Repoint the two existing "Workshop" references that currently resolve to
  `/app`: `auth_routes.py:178` and
  `templates/partials/owner_studio/_studio_navigation.html`. Both sit in the
  released default-off Slice 1 shell; leaving them stale would make the Studio
  nav lie about where Workshop is.
- Destination capabilities declared `coming_later`; no destination write exists —
  matching the approved `05` screen's `Use this elsewhere — Coming later` card.
- Feature flag default off; neutral 404 when off.

**Hard gate — Pete's first-page checkpoint (owner instruction, 2026-08-01):**
implementation builds the **first main page only — My Information — and stops.**
No other states, no session flow, no second page. The writer presents Pete a
side-by-side comparison of the real rendered page (desktop and mobile
screenshots) against the exact approved mockups
`06_APPROVED_desktop-my-information.png` and
`09_APPROVED_mobile-my-information.png`, with the mockup images included in
what Pete sees. Implementation continues only after Pete's visual acceptance
of the comparison.

**Direct-entry visual dependency:** the direct-entry composer has no approved
standalone mockup (round-2 file `02` is reference-only). Before building it,
either Pete explicitly accepts assembly from approved components (`04` layout,
`10` composer pattern, `05` confirmation) or a small ChatGPT visual addition is
obtained. Recorded in doc 20 §4.

**Excludes:** every AI behavior, sessions, Spark, voice capture (the composer
renders its text-entry form only), destination uses.

**Evidence:** two-owner SQL isolation with forged-key canary; route test proving
a `user_key` query parameter is ignored; byte-canary test; flag-off test
asserting identity is never resolved; migration-shape static test; full
keyboard, focus, contrast, 200% zoom, and 320 px reflow evidence; desktop and
mobile screenshots against the locked authority; generic-member fixtures.

---

## Slice W2 — Work on Something: session, AI review, and explicit save

The part Pete called the fun of the product. It is safe to add only because W1
established the store and the no-AI path.

**Includes:**

**Entry condition (added 2026-08-01):** the Workshop **opening screen has no
approved visual** — round-2 files `01`/`02` are reference-only. W2's
session-opening work starts only after the ChatGPT lane creates the corrected
opening (real navigation, four doors, no-tabs composer, single primary action)
and Pete locks it.

- Session lifecycle: the four starting doors (`Continue where I left off`,
  `I brought something` with its honest unavailable-intake state,
  `Work on something`, `Give me a spark`), focused question, autosaved
  **unfinished** state, resume, and stop — none of which confirm anything.
- Voice per the approved `10` sheet: one composer, inline microphone, submit
  arrow, six states (ready / listening / transcribing / transcript ready and
  editable before submit / failed with retry / microphone off), **no Type/Speak
  tabs**, text entry always available; long-form editors keep their screen-level
  action. The transcript lands in the same editable field the member can
  correct before it becomes their words.
- `Use as context`: per-item, off by default, **session-scoped**, with explicit
  selected / unselected / unavailable states; unavailable applies when an item
  is not confirmed (unfinished and suggested items cannot be context). It never
  confirms or reclassifies the underlying item.
- AI review: original wording preserved and separately editable; interpretation
  shown distinctly; what is already strong; one standout piece of evidence; one
  thing worth strengthening; one focused follow-up question. No score, no
  completeness meter, no deficit language.
- `Improve with AI` producing a labelled **proposal** beside the member's text —
  never an in-place rewrite.
- The proposal round-trips through a **server-signed, expiring token**. No
  proposal is ever written to the database.
- **Final review and `Save privately`** — the exact wording, classification,
  source attribution, with save as the single primary
  action. This is the only confirming write.
- Saved confirmation stating what did *not* happen.
- Grounding restricted by SQL predicate to confirmed, non-archived items,
  hard-capped, with the `by_id` map as the return-path
  allow-list.
- Model constant, explicit SDK timeout, per-route rate limits, capped input and
  output.
- Honest AI-unavailable states throughout; the W1 paths keep working.

**Excludes:** Spark, suggestions in the library, destination uses.

**Evidence:** proposal-never-writes test; unauthorized-grounding-id rejection;
archived and unconfirmed items absent from prompts; failure log contains no member
text; member text never lost on failure; heal-vs-reject behavior; voice
recording, transcribing, retry, and permission-denied states; full accessibility
and responsive evidence.

---

## Slice W3 — Spark and library suggestions

**Includes:**

- One grounded Spark on the opening, stating what confirmed information prompted
  it, with `Show another idea`.
- Durable dismissal — a dismissed Spark does not return, and
  `Do not suggest this again` is honored permanently.
- Suggestions in My Information as `SUGGESTED BY PEERSLATE — NOT CONFIRMED`,
  always citing actual member-provided evidence, with Review / Edit and confirm /
  Dismiss.
- Honest first-run and empty states: with no confirmed information there is no
  Spark, and the opening says so rather than fabricating one.

**Excludes:** cohort inference, stereotype-based suggestion, any unsolicited
sensitive-attribute inference, destination uses.

**Evidence:** suggestion cites only real member evidence; dismissal persists
across sessions; no-confirmed-information first run renders honestly.

---

## Slice W4 — Use this elsewhere *(gated on A2)*

**Entry condition:** the résumé/Story data-home decision from A2 is resolved and
a real write target exists. Until then this slice does not start, and the
capability stays `coming_later`.

**Includes:**

- `knowledge_item_uses`: body-free reference pinning one exact version.
- An explicit, previewed member action per destination — résumé page content, My
  Story, or Feed. Never bundled into save, never automatic.
- Current-uses display on the item, and the affected-use review when an item
  changes: per-use, member-decided, never bulk-silent.
- Final approval remains in the destination surface; Workshop prepares, it does
  not publish.
- Homepage parity check if any public surface changes.

**Excludes:** résumé document generation, templates, export, or anything that
competes with a word processor — permanently out of scope per owner decision D6.

---

## Release controls for every slice

1. Complete-diff self-review by the writer before handoff.
2. Focused tests plus `tests/test_site_rules.py` and
   `tests/test_governance_pointers.py` green.
3. Migration applied with plan → apply → verify → rollback → reapply proof in a
   non-production environment before production.
4. **Mandatory independent review (Claude Opus 5).** This package meets four
   `docs/AI_WORKFLOW.md` triggers — architecture-heavy, privacy and cross-user
   data, schema and migration, and consequential AI — so review is required, not
   discretionary.
5. Pete's final visual acceptance on the corrected real build against the locked
   authority.
6. Azure PR with squash merge; branch deleted after verified merge.
7. Pipeline and production verification. Note: the open PS-OPS
   Candidate-admission correction must land before any Candidate-based release.
8. Flag stays **off** through merge and deployment. Enablement is a separate,
   explicit owner decision with its own readiness audit.

## Truthful-status rule

No slice may describe Workshop as live, available, or member-facing while the
flag is off. Declaring a capability `coming_later` is the honest form; omitting
it or faking it is not.
