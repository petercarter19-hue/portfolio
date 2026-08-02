# Workshop — product and technical architecture

**Initiative:** PS-SLATE-STUDIO-IA-001
**Architect:** Claude Fable 5 (architecture lane)
**Date:** 2026-08-01
**Base:** Azure `origin/main` at `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`
**Status:** PROPOSED architecture. Documentation only. No runtime code, route,
schema, migration, feature flag, deployment, visual lock, or live capability is
authorized by this document.

**Controlling inputs:** `16_OWNER_DECISION_RECORD_WORKSHOP_2026-08-01.md`
(Pete's decisions D1–D6), `13_WORKSHOP_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md`
(Pete-approved element rulings), `12_OWNER_CORRECTION_RECORD_GOALS_WORKSHOP_AND_PROJECTS.md`,
`06_D3_SLATE_STUDIO_INFORMATION_ARCHITECTURE.md` (accepted route IA), and
`CLAUDE_AUDIT_2026-08-01.md`.

**Amended 2026-08-01 by doc 20** (round-2 approved visuals): §13's "no
implementable authority" is superseded — the approved set is hash-pinned at
`visual-authority/workshop-approved-2026-08-01/`. Voice is the no-tabs single
composer per approved file `10`. The AI-use permission control is **removed
entirely by owner decision** — always on, no toggle (doc 20 §6a). The
opening/direct-entry screens remain without approved visuals (doc 20 §4).

---

## 1. What Workshop is, architecturally

Workshop is a **private member knowledge base** with an AI-assisted way to grow
it. Pete's D5 decision makes this the controlling frame: the knowledge base is
the product; downstream use of that knowledge is secondary and optional.

That single sentence drives every decision below. In particular it means
Workshop is **not** an editor for the résumé, Story, or Feed. Those surfaces
consume Workshop's knowledge later, by reference, when the member explicitly
chooses it (D6).

Two modes over one store:

| Mode | Role |
|---|---|
| **Work on Something** | Guided contribution: focused question → member answer → AI review (proposal only) → explicit private save |
| **My Information** | The library: search, lenses, states, direct entry, edit, provenance, current uses, archive, delete |

---

## 2. Two decisions that need Pete or the manager

These are cross-lane and cannot be settled inside this package. Everything else
in this document is a normal architecture proposal.

### A1 — Workshop's route collides with an active lane

`06_D3_SLATE_STUDIO_INFORMATION_ARCHITECTURE.md` §2 rules that **Workshop's
canonical route is `/app`**, with Owner Home "absorbed into the Workshop role."
`auth_routes.py:178` already defines `workshop_url = url_for("auth.owner_workspace")`,
which resolves to `/app`.

But `/app` is contested today:

- Owner Home's frontend is **merged into `main`** (PR 148) and sits behind
  `PEERSLATE_OWNER_HOME_ENABLED`, default false (`app.py:111-113`). Flag-off
  `/app` renders `owner_workspace.html`; flag-on renders `owner_home.html`.
- `PS-HOME-FRONTEND-001` is a **currently active package** in
  `CURRENT_BASELINE.yaml` whose reserved domain is exactly that shell.
- Doc 06 anticipated this and deferred it: "Existing Owner Home implementation
  and flag behavior remain untouched until a separately activated runtime
  package owns the convergence."

Pete's D4 decision independently says consolidation comes later — Workshop
should sit **next to Interview Studio** now, and "once we get everything
together, then we'll start combining."

**Recommendation.** Build Workshop on its own protected route, `/app/workshop`,
and leave `/app` untouched. This satisfies D4, avoids writing another lane's
reserved files, and keeps doc 06's `/app` convergence available as the later
consolidation step Pete described.

State the trade-off plainly: this **is** a temporary departure from doc 06,
which names `/app` as Workshop's canonical route. It is not a reinterpretation.
Doc 06's own deferral clause anticipates a separately activated convergence
package, and Pete's D4 independently sequences consolidation later, so the
departure is bounded and reversible — but it needs an explicit decision, not an
architect's assumption.

The competing option (take `/app` now) forces `PS-HOME-FRONTEND-001` to be
closed or reassigned first and merges two products before Pete has seen either
in place. Not recommended.

**Needed:** manager or owner confirmation that `/app/workshop` is the v1 route,
that `/app` convergence is a later separately activated package, and that doc 06
§2 is amended to record the interim route.

**RESOLVED 2026-08-01:** Pete confirmed `/app/workshop` (doc 20 §6a). The doc 06
amendment is owed as part of the W1 governance updates.

**Integration consequence.** Two existing references already point "Workshop" at
`/app` and must be updated in the same slice, or they will be silently wrong:
`auth_routes.py:178` (`"workshop_url": url_for("auth.owner_workspace")`) and the
Slate Studio section nav at
`templates/partials/owner_studio/_studio_navigation.html`, which lists Workshop
alongside Build Your Future and Interview Studio. Both belong to the released
default-off Slice 1 shell, so the change is small but must not be missed.

### A2 — Destinations cannot be wired until résumé data moves

D6 says confirmed knowledge may update what already exists on the site. But the
résumé and My Story render today from **JSON fixtures on disk**
(`static/data/resume_data.json`, `story_data.json` — `app.py:1687-1706`,
`app.py:1048-1051`), not from the database. The `career_*` tables (PS-PLAT-006)
are the intended eventual home and hold no production content.

So "update the résumé page" has no write target today. A destination write
would require either editing JSON fixtures on disk (wrong — fixtures are
Pete-specific content, not a multi-member store) or completing the
fixture → database migration for the résumé/Story domain, which is a large
separate package.

**Recommendation.** Ship Workshop's knowledge base and AI session **without**
destination writes. Model the downstream use as a body-free reference from the
start (§5.4) so the contract is right, but activate it only in a later slice
after the résumé/Story data-home decision. This matches D5: the knowledge base
is the product and is fully useful on its own.

**Needed:** owner acknowledgement that v1 Workshop does not change the résumé,
Story, or Feed, and that "Use this elsewhere" arrives in a later slice.

---

## 3. Where Workshop sits

### 3.1 Route

| Surface | Route | Notes |
|---|---|---|
| Workshop (both modes) | `GET /app/workshop` | New protected HTML route; mode is a query/tab within one page |
| Workshop JSON API | `/api/v1/workshop/...` | Follows the `peerslate_api` conventions |

One route serves both modes. Mode selection is a tab, not a second route, per
doc 13's "Workshop remains one room" ruling and doc 06's rejection of
intermediate index routes.

### 3.2 Navigation

Pete's D4: next to Interview Studio. The mockups' navigation is placeholder and
must not be implemented by inference — it drops Living Résumé and Interview
Studio and invents "View private profile."

The real global header is `templates/base.html:191-206` with a mobile mirror at
`:284-291`: Pete's Slate · Community · Interview Studio.

**Add Workshop immediately after Interview Studio, visible only when signed in
and only when the Workshop flag is on.** `shared_authentication_state`
(`auth_routes.py:294-321`) already injects `current_member` into every template,
so the conditional needs no new plumbing. Both the desktop list and the mobile
mirror must be updated, plus the `#nav-search-data` JSON at `base.html:433-468`.

Do **not** rename Interview Studio, and do not remove anything from the header.

### 3.3 Naming

D4 anticipates a later rename to "My Slate." Therefore: **no user-facing product
name in any identifier.** Tables, procedures, routes, flags, schema versions,
and CSS classes use `knowledge_*` / `workshop` as structural names; the visible
string "Workshop" lives only in templates and copy. A rename must be a template
and copy change, never a migration.

---

## 4. The truth model

Four data classes, kept structurally distinct — this is the product's core
promise and it is enforced in the schema, not in the UI.

| Class | Where it lives | Rule |
|---|---|---|
| Member source | `knowledge_item_versions.original_member_wording` | Never overwritten; retained for the life of the item |
| AI interpretation / proposal | **Nowhere durable.** A signed, expiring token | Never written to the database unless the member accepts it |
| Confirmed private information | `knowledge_item_versions.approved_wording` on a `confirmed` item | Canonical (D1). Server-derived ownership; private-locked |
| Purpose-specific use | `knowledge_item_uses` (later slice) | Body-free reference pinning an exact version |

### 4.1 D1 in the schema

Pete's D1: the member-approved wording is canonical, and accepted AI refinement
is **not** labelled as AI-changed. This is honest only because the member
explicitly reviews and approves the exact final wording before it is saved —
the save-consent state the audit's finding C1 requires. The two ship together or
neither is truthful.

The repository already has this exact pattern:
`career_chapters.original_member_wording` + `.approved_wording`, and
`career_achievements` likewise (PS-PLAT-006). Workshop mirrors it rather than
inventing a shape. The original is retained and inspectable in history; it
simply carries no AI-attribution badge.

`authored_via` records `typed | spoken | ai_assisted_approved` for internal
provenance and evaluation. It is **not** rendered as a member-facing AI label —
that would reintroduce exactly what D1 removed.

### 4.2 The AI proposal never touches the database

A review or refinement proposal round-trips to the browser through a
**server-signed, short-lived token**, reusing the existing
`_sign_interview_model_context` / `_load_interview_model_context` pattern
(`app.py:2730-2782`: `URLSafeTimedSerializer`, 30-minute max age, size cap,
per-field re-validation on read).

This makes "AI proposes, people decide" a structural property: there is no
proposal row to leak, resurrect, or accidentally promote. Only an explicit
member save writes anything.

---

## 5. Data model

Follows the established conventions exactly: `bigint IDENTITY` PK, external
`uniqueidentifier` key (routes never see integer ids), `owner_profile_id` FK to
`member_profiles`, states as `nvarchar(30)` + `CHECK IN`, paired state/actor/
timestamp CHECK constraints, `row_version rowversion` for optimistic
concurrency, `UNIQUE (<pk>, owner_profile_id)` plus composite FKs for
structural tenant isolation (PS-PLAT-005 idiom).

Package id for migrations: **`PS-WORKSHOP-001`**.

### 5.1 `dbo.knowledge_items`

The canonical record. One row per thing the member knows or has said about
themselves.

| Column | Type | Notes |
|---|---|---|
| `knowledge_item_id` | `bigint IDENTITY` | PK |
| `knowledge_item_key` | `uniqueidentifier` | `DEFAULT NEWSEQUENTIALID()`, UNIQUE — the only id a route sees |
| `owner_profile_id` | `bigint` | FK `member_profiles(profile_id)` |
| `item_status` | `nvarchar(30)` | `CHECK IN (N'suggested', N'unfinished', N'confirmed', N'archived')` |
| `classification` | `nvarchar(20)` | `CHECK IN (N'work', N'personal', N'both', N'unclassified')` |
| ~~`ai_use_permission`~~ | — | **Removed by owner decision, 2026-08-01 (doc 20 §6a):** AI use of confirmed information is always on with no member-facing toggle. No column, no permission procedure, no permission UI. Grounding uses all confirmed, non-archived items; archive and delete are the member's removal controls |
| `visibility` | `nvarchar(20)` | `CHECK (visibility = N'private')` — hard-locked in v1 |
| `current_version_number` | `int` | |
| `confirmed_version_number` | `int NULL` | |
| `confirmed_by_user_id` / `confirmed_at_utc` | | Paired CHECK: confirmed ⟺ all three set **and** `confirmed_version_number = current_version_number` |
| `archived_at_utc` / `archived_by_user_id` | | Paired CHECK with `item_status = N'archived'` |
| `created_at_utc` / `updated_at_utc` | `datetime2(7)` | `DEFAULT SYSUTCDATETIME()` |
| `row_version` | `rowversion` | Optimistic concurrency |

Plus `UNIQUE (knowledge_item_id, owner_profile_id)` for composite FK targets.

The confirmation-state CHECK is copied from `CK_moments_confirmation_state`
(PS-MOMENT-001) — it makes "confirmed but nobody confirmed it" unrepresentable.

`visibility` is hard-locked private exactly as `CK_moments_visibility` is. A
later audience decision relaxes it in its own migration; it is not left open
"just in case."

### 5.2 `dbo.knowledge_item_versions`

The content body. Append-only in practice: an edit writes a new version.

| Column | Type | Notes |
|---|---|---|
| `knowledge_item_version_id` | `bigint IDENTITY` | PK |
| `knowledge_item_id` / `owner_profile_id` | `bigint` | Composite FK to the parent |
| `version_number` | `int` | `UNIQUE (knowledge_item_id, version_number)` |
| `title` | `nvarchar(160)` | |
| `approved_wording` | `nvarchar(max)` | **Canonical** (D1). Length CHECK via `DATALENGTH/2` |
| `original_member_wording` | `nvarchar(max) NOT NULL` | Retained, never overwritten (D1) |
| `body_format` | `nvarchar(20)` | `CHECK IN (N'plain', N'rich')` — see §8 (D3) |
| `authored_via` | `nvarchar(30)` | `CHECK IN (N'typed', N'spoken', N'ai_assisted_approved')` |
| `saved_by_user_id` / `saved_at_utc` | | |

Text limits use the repo idiom `CHECK (DATALENGTH(col)/2 BETWEEN 1 AND N)`
(UTF-16 code units), matched in Python by `len(v.encode("utf-16-le"))//2` per
`services/moment_service.py:34-36`.

### 5.3 `dbo.knowledge_item_sources` *(slice W2)*

Provenance for items created from a Work on Something session: which session,
and for spoken input the exact voice media/transcript reference. Follows
`moment_sources` including its **body-free tombstone** behavior — if the
underlying source is deleted, the row keeps the reference shape with payload
columns nulled and a `source_state = N'deleted'`, enforced by CHECK.

### 5.4 `dbo.knowledge_item_uses` *(slice W4, contract defined now)*

The downstream-use reference. Body-free, pinning **one exact version**, modelled
directly on `moment_placements` (PS-PLACEMENT-001) rather than a new shape.

| Column | Notes |
|---|---|
| `knowledge_item_id` + `knowledge_item_version_number` | Composite FK pins the exact version the member approved for that use |
| `target_kind` | `CHECK IN (N'resume_page', N'story', N'feed')` — D6's three surfaces, nothing else |
| `target_reference` | Server-resolved destination reference |
| `use_status` | `CHECK IN (N'active', N'removed')` with paired actor/timestamp CHECKs |

Because the use pins a version, editing the item later **cannot** silently
change a published surface. The member is shown the affected uses and decides
per use — the behavior the mockup's banner promises, and the same rule the
Journal package already applies to publications.

### 5.5 What this is not

It is not a second copy of anything. The knowledge base holds a data class no
existing table holds: durable member-stated facts and self-description.
`moments` are timestamped events (`moment_kind`, `occurred_on`,
`occurred_precision`); a skill or an interest is not an event and would be
distorted by that shape. `career_*` is a structured résumé schema that cannot
hold "long-distance running." `captures` are raw intake drafts.

Workshop must not write to `moments` (reserved by PS-JOURNAL-001), `career_*`,
or the JSON fixtures.

---

## 6. Authorization

Every rule here is an existing repository pattern, not a new invention.

1. **Flag gate outermost, before identity resolution.**
   `PEERSLATE_WORKSHOP_ENABLED`, default `false`, in the single
   `app.config.update(...)` block (`app.py:93-149`) with the initiative id in a
   comment, plus `.env.example`. Read via a one-line predicate using
   `is True` so a truthy string cannot enable it.
2. **Neutral 404 for everything.** Use `require_identity_or_not_found`
   (`peerslate_api.py:75-91`) rather than 401/403, so *signed out*, *flag off*,
   *another owner's item*, and *does not exist* are indistinguishable. HTML
   routes `abort(404)` before identity resolution when the flag is off.
3. **Identity is server-derived only.** Routes pass `identity.user_key` and
   nothing else. A `user_key`-shaped query parameter is ignored, proven by a
   test in the shape of `tests/test_owner_journal.py:290-300`.
4. **SQL resolves `@UserKey` → `@ProfileId` and returns empty when unresolved.**
   Every read filters `owner_profile_id = @ProfileId`; every JOIN re-asserts the
   owner in its predicate. No procedure accepts `@OwnerProfileId`.
5. **Same-origin guard on every write** — `_is_same_origin_write()`
   (`owner_routes.py:127-148`), which fails closed when no signal is present.
6. **`Cache-Control: private, no-store`** on every Workshop response, via the
   blueprint `after_request` pattern (`owner_routes.py:150-162`), and the
   blueprint added to the `prevent_stale_html` set (`app.py:479-484`).
7. **Optimistic concurrency** on every write: `@ExpectedRowVersion binary(8)`,
   surfaced to the member as the existing `"changed"` key.
8. **New procedures must be added to `ALLOWED_PROCEDURES`**
   (`services/database_service.py:11-84`) or they fail closed.

Procedures: `usp_ListKnowledgeItemsForOwner`, `usp_GetKnowledgeItemForOwner`,
`usp_SaveKnowledgeItemForOwner` (idempotent, with a save-request ledger in the
shape of `moment_save_requests`), `usp_UpdateKnowledgeItemForOwner`,
`usp_ArchiveKnowledgeItemForOwner`, `usp_DeleteKnowledgeItemForOwner`.

---

## 7. Application layers

Follows the four-layer convention with `owner_home_service` as the reference
implementation.

```
route (flag → identity → same-origin → service)
  └─ services/knowledge_service.py      class + singleton, injected `database`
       └─ services/database_service.py  allowlisted usp_* only
            └─ dbo.usp_*ForOwner        @UserKey → @ProfileId → owner-filtered
```

- **Service:** `services/knowledge_service.py`, class `KnowledgeService`, module
  singleton on the last line, `__init__(self, database=None)` defaulting to the
  singleton for test injection, and a code-carrying
  `KnowledgeServiceError(RuntimeError)` whose `.code` a route maps to a message
  dict.
- **Serializer:** `_require_exact_fields` (set equality, not superset), per-field
  coercion, then a re-validation of the serialized output including an item-count
  cap and a serialized-byte cap — the `owner_home_service.py:148-379` discipline.
- **Contract version:** `SCHEMA_VERSION = "workshop-knowledge.v1"`. Capabilities
  not yet built are declared `{"state": "coming_later"}` rather than omitted, per
  the availability-registry idea in `owner_home_service.py:54-60`. This is how
  the UI stays truthful about destinations before slice W4.
- **Template:** `templates/workshop.html` extending `base.html`, composing
  `templates/partials/workshop/_*.html`. Server-rendered state panels branching
  on an explicit state field, in the style of
  `partials/owner_studio/_state_panel.html`. JavaScript is progressive
  enhancement only — the library, direct entry, editing, and save must work
  without it.
- **Static assets:** `static/css/workshop.css`, `static/js/workshop.js`. Never
  hand-write a `?v=` token; `@app.url_defaults` stamps a content hash
  (`app.py:294-326`).

---

## 8. Rich text (D3)

D3 keeps the candidate set's formatting affordances. Because Workshop is not a
document product, formatting carries no export burden — but it must not become a
provenance or injection problem.

- Store `body_format` per version. v1 accepts `plain` and `rich`.
- `rich` is a **constrained subset**: bold, italic, unordered/ordered list, link.
  Nothing else. Sanitize server-side on write to that allowlist; never trust the
  client. Links are stored with an explicit scheme allowlist (`https`, `mailto`).
- `original_member_wording` is stored in the same format as authored.
- AI grounding uses the **plain-text projection** of the wording, never the
  markup, so formatting cannot influence a prompt.
- Downstream uses (W4) resolve to the plain-text projection unless the
  destination explicitly supports the same subset.

---

## 9. AI architecture

### 9.1 Reused patterns

- **Bounded, ID-addressable grounding.** Mirror
  `_interview_evidence_from_profile` (`app.py:1279-1316`): server selects the
  grounding set, hard-caps it (10 items), projects to a minimal shape, and the
  resulting `by_id` map doubles as the **return-path authorization allow-list**.
  A proposal citing an id outside the map is rejected before the member sees it.
- **Grounding is state-filtered.** Only `confirmed`, non-archived items may
  ground a prompt — a SQL predicate in the same procedure, not a Python filter.
  Per the owner decision in doc 20 §6a there is no per-item permission;
  archiving or deleting an item is how a member removes it from AI grounding.
- **Validate-then-render.** Every field type-checked, enum-checked, length-capped
  before it reaches the browser, per `validate_interview_review`
  (`app.py:2572-2678`).
- **Heal vs reject.** Derived aggregates are recomputed from validated parts
  (the PR 176 pattern at `app.py:2641`); missing *deliverables* are rejected.
  For Workshop: a missing "one thing worth strengthening" is a rejectable
  degraded response; an empty "what's already strong" is delivered honestly as a
  stated absence, matching the PR 123 asymmetry.
- **Privacy-safe failure taxonomy.** A `WORKSHOP_FAILURE_REASONS` map of
  low-cardinality labels; logs record reason, error class, provider stop reason,
  and reply length — **never member text**, locked by a test in the shape of
  `tests/test_interview_studio.py:1551`.

### 9.2 Required new controls

The existing AI integration has gaps Workshop must not deepen:

| Gap today | Workshop requirement |
|---|---|
| Model id hardcoded at five call sites | Define one module-level model constant and use it. Do not add a sixth literal |
| No SDK timeout or retry config | Pass an explicit `timeout` on every Workshop call. A hung provider must not hold a worker |
| No token accounting or spend cap | Bound every Workshop prompt by construction: capped grounding set, capped member input, capped `max_tokens`. Record an estimated-token log line for later budgeting |
| No per-route rate limit by default | Apply `flask-limiter` limits to every Workshop AI route, matching the Interview Studio range |

**Out of scope, flagged as a dependency.** `app.py:72-75` raises `RuntimeError`
at import when `ANTHROPIC_API_KEY` is unset, which makes the entire site —
résumé, Story, Community — unbootable without an AI key. That directly
contradicts the standing invariant that the core experience remains usable when
AI is unavailable. Workshop does not fix it and must not depend on it being
fixed; the deferral is already recorded in
`docs/governance/HANDOFF_SNAPSHOT_2026-07-21.md`. It is named here so the
architecture is not read as endorsing it.

### 9.3 AI-unavailable behavior

Workshop must be genuinely usable with AI down. Because the knowledge base is
the product (D5), this is not a degraded shell:

- My Information — full function: search, lenses, direct entry, edit, classify,
  archive, delete.
- Work on Something — direct entry and save still work end to end. A member can
  create and confirm an item with **no AI step at all**.
- Spark, AI review, and Improve show an honest unavailable notice. Never a
  skeleton loader that implies a pending result.

---

## 10. State machine

```
                    ┌──────────── direct entry ────────────┐
                    │                                      ▼
opening ──▶ session ──▶ AI review ⇄ (improve / answer follow-up) ──▶ FINAL REVIEW ──▶ saved
              │  ▲                                                        │
              │  └──────────────── keep working ────────────────────────┘
              ▼
        unfinished (autosaved, resumable)
```

**FINAL REVIEW is the screen the candidate set is missing** (audit finding C1)
and the state D1 depends on. It shows the exact wording to be saved, its
classification, and its source attribution, with
`Save privately` as the single primary action and `Keep working` /
`Save unfinished` as exits. Nothing is written before it.

Transitions:

| From | Trigger | To | Writes? |
|---|---|---|---|
| opening | Spark `Work on this`, a starting path, resume unfinished, or an open thought | session | no |
| session | autosave while typing/speaking | unfinished | yes — owner-private draft |
| session | `Review what I shared` | AI review | no |
| AI review | `Improve with AI` / answer the follow-up | AI review (updated) | no — signed token only |
| AI review | proceed to save | final review | no |
| final review | **`Save privately`** | saved | **yes — the only confirming write** |
| saved | `Use this elsewhere` *(W4)* | use created | yes — body-free reference |

Editing a confirmed item writes a new version, leaves provenance intact, and
leaves existing uses pinned to their approved version until the member reviews
them.

---

## 11. Accessibility and responsive requirements

Binding for implementation; the visual authority does not yet cover them
(§13). Full detail is in `CLAUDE_AUDIT_2026-08-01.md` §7.

- Complete keyboard operability including mode tabs, `Use as context` toggles
  with pressed state, filter chips with selection exposed to assistive
  technology, and `Save privately`. Visible focus throughout; no keyboard trap
  in the voice UI.
- Typing is the built-in equivalent for every voice action; microphone
  permission denied is a first-class state.
- Selection and status are never color-only. Status colors belong on item
  badges, not on filter controls.
- Contrast verified ≥ 4.5:1 for the orange "Suggested" text, gray metadata, and
  blue accents on the pale field.
- `prefers-reduced-motion` honored by the mic pulse and all transitions.
- 200% zoom and 320 px reflow with no horizontal scroll; defined three-rail
  collapse order — workstage first, starting rail as a collapsed menu, context
  rail last.
- AI-generated regions labelled as such to screen readers; save confirmation
  announced via a live region; the suggestion card announced as unconfirmed.
- Minimum 24 px touch targets for `Use as context`, filter chips, and rail links.

---

## 12. Testing and evidence

| Layer | Requirement |
|---|---|
| Owner isolation (SQL) | `PS-WORKSHOP-001_owner_isolation_verify.sql` with two synthetic owners, byte canaries, a **forged-key canary** asserting a fabricated `@UserKey` returns nothing and produces no truthful-looking save outcome, all inside an outer transaction that always rolls back |
| Owner isolation (route) | `?user_key=someone-else` is ignored; the service is called with the server-resolved key only |
| Owner isolation (bytes) | Two-owner serialized payloads share no marker bytes |
| Migration shape | Static test asserting forward/rollback/verify exist, dependency and object guards present, definition fingerprint in both forward and rollback, procedure is owner-resolving and bounded, and the read selects no prohibited column |
| Flag-off | Route returns 404, response contains neither the CSS filename nor any Workshop copy, and identity resolution is never called |
| AI boundary | A proposal citing an unauthorized grounding id is rejected; a proposal never writes; archived and unconfirmed items never enter a prompt |
| AI failure | Member text is never lost; the failure log contains no member content |
| Truthfulness | Destination capabilities render `coming_later` honestly while W4 is unbuilt |
| Guardrails | `tests/test_site_rules.py` and `tests/test_governance_pointers.py` stay green |
| Multi-member | Every behavioral test uses a generic fixture member, not Pete |

Migrations follow the full repository convention: `SET XACT_ABORT ON`, ledger
guard, dependency guards, object guards, idempotent additive DDL,
`CREATE OR ALTER` via `EXEC(N'...')`, a SHA2_256 definition fingerprint stored
as an extended property, ledger insert plus audit event, and a **guarded**
rollback that refuses on missing ledger record, later-migration presence, or
definition drift. One file is one batch — no `GO`.

Registration checklist: `ALLOWED_PROCEDURES`
(`services/database_service.py`), `APPROVED_OPTIONAL_MIGRATIONS` and a
`verify_*` function (`scripts/apply_sql_migrations.py`), and `EXPECTED_TABLES`
if the tables become foundation.

---

## 13. Visual authority status

**Implementation cannot begin from the current candidate set.** It is
`CANDIDATE — NOT OWNER-LOCKED`
(`visual-authority/workshop-candidate-2026-07-31/ASSET_MANIFEST.md`), it is
missing the final-review/save screen this architecture depends on, its
destination card is superseded by D6, and no responsive, focus, zoom, empty,
loading, error, AI-unavailable, permission-denied, or reduced-motion visuals
exist.

Those corrections belong to the **ChatGPT visual-creation lane**, followed by
Pete's exact hash lock. Claude implements the locked authority; it does not
originate it.

**Homepage impact:** none in v1. Workshop is authenticated-only, the logged-out
homepage neither presents nor links it, and v1 changes no public surface. If a
later slice adds a public projection or a homepage claim, the homepage parity
check applies then.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| `/app` route contention with an active lane | A1 — resolve before implementation; recommendation is to avoid `/app` entirely in v1 |
| Destination promise outruns the data home | A2 — declare destinations `coming_later`; do not fake a write |
| A second truth store | Workshop holds a data class no table holds; it writes to no existing content table; uses are body-free references pinning exact versions |
| Unbounded AI cost | Capped grounding, capped input, capped output, per-route rate limits, explicit timeout |
| Rename to "My Slate" churns the schema | No product name in any identifier |
| Site unbootable without an AI key | Pre-existing, recorded deferral; named as a dependency, not inherited as a design assumption |
| Fixture content mistaken for product | Every test uses a generic member; Pete's fixtures are never product logic |
