# PS-ASK-PETE-DIRECT-001 — the private recruiter-question path

**State: built dark. Nothing is registered, applied, deployed, or enabled.**

A recruiter who reaches the end of what Ask Pete can answer from public
information can send the remaining question to Pete privately, with consent and
bounded input, and it lands in an owner-only inbox Pete checks on the site.
Replying never teaches Ask Pete anything, nothing becomes public without a
separate explicit decision, and no reply is ever sent automatically — there is
no outbound channel in this package at all.

Authority: the owner-approved package brief (iCloud, *Ask Pete Release Prep
2026-08-07/05-DIRECT-001-PACKAGE-BRIEF.md*) built from the 2026-08-08 read-only
discovery, activated under Pete's standing full approval and recorded in
`docs/governance/CURRENT_LANES.json`.

## Start here

| I want to… | Read / run |
|---|---|
| **See it, and click through it** | `venv/bin/python tests/ask_pete_direct/run_direct_preview.py` — the local preview. Fixture data, no provider, no database. Prints two URLs on 127.0.0.1. |
| Prove the preview still boots | `…/run_direct_preview.py --check` |
| Turn the routes on in `app.py` | [`REGISTRATION_LEG_SPEC.md`](REGISTRATION_LEG_SPEC.md) — four copy-ready edits and their verification checklist |
| Move the schema | [`SCHEMA_GATE_RUNBOOK.md`](SCHEMA_GATE_RUNBOOK.md) — the gate sitting and the governed apply |
| Know exactly what is and is not done | [`COMPLETION_RECORD.md`](COMPLETION_RECORD.md) |

The remaining legs run in this order, each separate and recorded: **gate →
production apply → registration + deploy → owner key configured → Pete reviews
the copy in the preview → flag on.**

## What "dark" means here, precisely

Three independent things must all change before a visitor can reach any of
this. None of them happened in this package:

1. **Registration.** `ask_pete_direct_routes.py` is imported by nothing.
   `app.py` belongs to PS-INTERVIEW-STUDIO-FUNCTIONAL-V1-001, so the two-line
   blueprint registration is a later recorded leg. Until then the routes do not
   exist at run time. `tests/ask_pete_direct/test_darkness.py` asserts this and
   is designed to FAIL the day someone registers it — that failure is the
   tripwire that forces the registration to be a deliberate, reviewed act.
2. **Schema.** The migration passed its disposable-database gate on
   2026-08-08 (`ps-ask-pete-direct-gate-202608082309`, verifier returned
   `verified = 1`) and the proof is recorded, so the governed applier will
   now accept it — but **no production database carries these tables**,
   because the Part 4 apply has not been run. See `SCHEMA_GATE_RUNBOOK.md`.
3. **The flag.** `PEERSLATE_ASK_PETE_DIRECT_ENABLED` defaults false and is
   read with `is True`, so a `"false"` string cannot enable it. With it off,
   every route answers a neutral 404 and the companion partial renders
   byte-for-byte what it rendered before this package existed.

## What was built

| Surface | What it does |
|---|---|
| `SQL FIles/Migrations/proposed/PS-ASK-PETE-DIRECT-001_recruiter_questions.sql` | `dbo.recruiter_questions` (owner-addressed, bounded, consent-versioned, new/read/archived) + a `knowledge_item_save_requests`-shaped idempotency ledger + three procedures. |
| `..._recruiter_questions_rollback.sql` | Guarded reversal that **refuses while any question is stored**. |
| `SQL FIles/Verification/PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql` | Two synthetic recipients, one rolled-back transaction, `verified = 1`. |
| `SQL FIles/Migrations/registry.json` | Registry entry, carrying its passed gate proof (2026-08-08). |
| `services/database_service.py` | Three names added to `ALLOWED_PROCEDURES`. |
| `services/ask_pete_direct_service.py` | Bounded, consent-first storage seam. Resolves no identity itself. |
| `ask_pete_direct_routes.py` | The unregistered blueprint: one public POST, the owner inbox page, and the inbox status action. |
| `templates/partials/ask_pete_evidence_companion.html` | One flag-conditional hidden config element. Nothing else. |
| `static/js/ask-pete-evidence-companion.js` | The consent-first form built inside the accepted handoff card with safe DOM APIs. |
| `static/css/ask-pete-resume-evidence.css` | Appended, namespaced `.ask-pete-direct*` rules only. |
| `templates/ask_pete_inbox.html` | Standalone, server-rendered, JavaScript-free owner inbox. |
| `.env.example` | The flag, documented off, with its prerequisites. |
| `tests/ask_pete_direct/` | The whole package's coverage, on a test app that registers the blueprint directly. |

## The trust boundaries, and where each one is actually enforced

| Boundary | Enforced by |
|---|---|
| Consent is explicit, never inferred | The form's checkbox; the service's `consent is not True`; the procedure's `@ConsentGiven <> 1` THROW ahead of every INSERT. Three layers, any one of which refuses alone. |
| The sender is anonymous | No sender parameter exists in the procedure, the service, or the payload. The only personal data stored is what the sender typed into the bounded contact field. The submit audit event carries a null actor. |
| Nobody can write into another member's inbox | The recipient comes from `PEERSLATE_OWNER_USER_KEYS`, server-side. A payload naming a recipient is refused outright as an unexpected field. |
| Nothing is published or fed to AI | There is no public read procedure, no visibility column, and no shared table, column, or procedure with the knowledge store. |
| Nothing is deleted | No procedure body contains a `DELETE`; there is no delete or purge procedure; the service has no delete method; the inbox has no delete control; the rollback refuses while rows exist. |
| Only the owner reads the inbox | `@owner_required` on the page **and** on the action, independently, each answering a bare 404 to everyone else. |
| A double-tapped Send stores one question | A required `Idempotency-Key` header + the per-recipient unique ledger index, taken under `UPDLOCK, HOLDLOCK`. |
| A stale inbox cannot silently overwrite | Every status change is fenced by `@ExpectedRowVersion` and reports `changed` rather than succeeding. |

## Open items the enablement leg must close

1. **Closed, 2026-08-08.** The consent copy used to promise "archive after 90
   days and remove after 180", which nothing in this package implements and
   nothing could — the removal half is a hard delete, outside the lane. Under
   Pete's "published always" decision (this path goes live as soon as its
   remaining legs land, so every visitor-facing sentence must be true *today*),
   the sentence now reads: *"Pete manages these himself: he archives what he
   has read, and keeps a message for as long as he needs it — nothing here is
   removed on an automatic timetable."* True as written, and strictly weaker
   than the withdrawn draft, so a future automated-retention leg (the
   `usp_PurgeCommunityContent` out-of-process pattern) can strengthen it to a
   timed promise in the same change that implements one — never ahead of it.
   Tests assert both halves: the claims that are made, and the absence of any
   timed claim.
2. **Rate limiting is declared, not applied.** `PLANNED_RATE_LIMITS` names the
   budgets (30/hour for the public write, 60/hour for the owner action); the
   registration leg must wire them with the post-registration limiter-wrapper
   idiom in `app.py`. No parallel counter was invented here instead.
3. **Half closed, 2026-08-08.** The disposable-database
   apply/reapply/verify/rollback/forward rehearsal is **done**: Pete gated it
   on `ps-ask-pete-direct-gate-202608082309` at 23:10:49Z, the verifier
   returned `verified = 1`, and the proof is recorded against digest
   `ec3d21d0…`. **The production apply is still outstanding** — Part 4 of
   `SCHEMA_GATE_RUNBOOK.md`, owner-attended, with an approver on the
   `peerslate-database-schema` environment.
4. **`PEERSLATE_OWNER_USER_KEYS` must name exactly one key.** Zero, several, or
   an email-only owner allowlist leaves every send answering an honest 503.
5. **No *production* browser evidence exists yet** — the form cannot render on
   a deployed page until the blueprint is registered. A local preview does
   exist: `tests/ask_pete_direct/run_direct_preview.py` registers the blueprint
   on the real application exactly as `app.py` will and serves both surfaces
   with fixture data, so the appearance, the keyboard path, and the copy can be
   reviewed today. Capture deployed browser evidence during the registration
   leg, before enablement.
6. **No unread badge on another owner surface.** The package brief mentioned
   one; every surface that could host it belongs to another lane. The count is
   available (`usp_ListRecruiterQuestionsForOwner` returns `new_count`) for
   whichever lane later owns that surface.

## Owner-directed companion adaptation, 2026-08-08

Pete used the local preview harness and reported two things, verbatim:

> "the sixty second recruiter view is a two second recruiter view... a lot of
> information, sorted out weird"

> "there's no way to go back"

Both concern the **live grounded companion** (PS-ASK-PETE-AI-001's surface),
not the private question path — but all three of its files are in this lane, so
they were fixed here. Each was investigated against the accepted authority
before anything changed, and the two turned out to be different kinds of
problem.

### 1. Answer ordering — **DEFECT against the locked design**

**What the authority requires.** State 4 renders "answer first, followed by
clearly associated claims and inspectable evidence"
(`02_BACKEND_CONTRACT_AND_VISUAL_HANDOFF.md`); `summary` is "the concise
answer-first synthesis" (`03_VISUAL_RUNTIME_ARCHITECTURE.md`); the discovery
agenda opens with "direct answer first"; and the stylesheet's own flagship
block is captioned "compact enough to inspect in one rail view".

**What the runtime did.** The DOM order was already correct — heading, support
state, summary, claims, sources, follow-ups, handoff. The defect was that
**the rail's scroll position was never managed at all.** The only two
`scrollIntoView` calls in the file both move the *résumé*; nothing ever touched
`.ask-pete-evidence-companion__scroll`. So the rail kept whatever `scrollTop`
it had — and a recruiter who has just typed in the composer is at the *bottom*
of the rail. Inserting a tall answer above the composer left them looking at
its tail: follow-ups first, then the contact card, with the summary scrolled
off the top. That is exactly "sorted out weird".

**Measured, not assumed.** With the fix disabled, the browser check reports the
second answer's top at **−729px** relative to the rail — three-quarters of a
screen above the visible area — and "the summary is in view" fails outright.
With the fix, every answer lands at −0.09px. The check reproduces Pete's exact
sequence: type in the composer (which scrolls the rail to its bottom), then ask.

**Fix.** `revealAnswerTop()` scrolls the rail — and only the rail — so the
answer's top is the top of the visible rail after every render. It uses
`scrollTo` on the container rather than `scrollIntoView`, which would drag the
résumé behind it as a side effect, and it honours `prefers-reduced-motion`. No
DOM reordering was needed and none was done. **Because the accepted authority
already intended this, the change does not return to the visual-creation lane.**

### 2. A way back — **owner-directed ADAPTATION**

**What the authority says.** The client state model holds a single `answer`
(`03_VISUAL_RUNTIME_ARCHITECTURE.md`), and multi-answer history is named
explicitly as "future conversation-state work"
(`02_BACKEND_CONTRACT_AND_VISUAL_HANDOFF.md`). Source-opening already preserved
the current answer, so state 9's "preserve conversation state" was being met.
Asking a *second* question, though, replaced the first outright with nothing
that could return to it — and the locked model does not cover that case either
way.

So this is an addition Pete directed, not a correction. It is deliberately the
smallest one that answers him: **exactly one prior answer is retained**, and one
inline control returns to it. No history panel, no stack, no redesign. It
*swaps* rather than pops, so the control reads truthfully in both directions and
using it can never destroy the newer answer.

**Non-material by the usual test:** a transparent text button in the treatment
the composer's Cancel already uses, placed in the existing
`.ask-pete-evidence-answer__meta` row, using only existing tokens, and covered
by the accepted `:is(a, button, textarea):focus-visible` rule without a new rule
of its own. It is *prepended* rather than appended specifically so the accepted
compact rule `.ask-pete-evidence-answer__meta > span:last-child` keeps matching.

**Still true:** no retained answer is ever sent to the model. The request body
remains `{ message, action, context_key }`, so a follow-up stays independently
grounded exactly as the architecture requires. Asserted by test.

### Before / after intent

| Situation | Before | After |
|---|---|---|
| An answer arrives while the rail sits at its bottom | Recruiter sees follow-ups and the contact card; summary scrolled off the top | Rail lands on the answer's top; summary in view, follow-ups and handoff below it |
| Ask a second question | First answer destroyed, no way back | One prior answer retained; "Back to previous answer" appears in the answer's meta row |
| Use the back control | — | Swaps between the two retained answers; neither is lost |

### Flag safety

Neither change touches the server-rendered partial. The template is unchanged
by this slice, and both assets load only where
`ask_pete_evidence_companion_enabled` is true — a legacy page loads
`chatbot.css`/`chatbot.js` instead, so neither the new rule nor the new script
path can reach it. Asserted by `FlagSafetyTests`.

### Observed but deliberately not changed

* **The three starter buttons stay hidden once an answer exists.** Pete
  mentioned this alongside the back problem. It is not a defect: hiding the
  capability preview after an answer is what the accepted `is-answer-first`
  state is *for*, and state 1 is explicitly the "Empty / capability preview".
  Restoring them would work against the answer-first intent this same slice
  just repaired. Worth raising as its own decision if he still wants them.
* **Recovery cards are not scrolled to.** Only answers are. A recovery message
  landing below the fold is the same class of problem, but it is not what was
  reported, and widening the change would put more of the accepted design in
  play than the report justifies.

## Deliberate deviations from the brief

* **The inbox is `/owner/ask-pete-inbox`, not `/app/ask-pete-inbox`.** `/app/`
  is the per-member namespace, where every signed-in member owns what they
  find; this surface is site-owner only, which is what `/owner/` means here
  (`/owner/control-room` is its neighbour).
* **`tests/test_database_service.py` was edited**, though the implementation
  brief's writable list did not name it. Its
  `test_the_allowlist_is_exactly_this_set_and_nothing_more` asserts set equality
  against a hardcoded literal and count, and its own docstring requires "a
  matching, reviewed change to the literal set" whenever `ALLOWED_PROCEDURES`
  changes. The edit adds a labelled three-name group and moves the exact count
  131 → 134; the set-equality and non-overlap assertions are untouched, so the
  test is exactly as strong. The file is not a surface of any other active lane.
* **The status procedure accepts `new` as well as `read` and `archived`.** A
  one-way archive would strand a mis-archived question permanently — there is
  no expiry and no delete to eventually clear it. Restoring is not a new
  capability class — it is the same version-fenced status write — and it makes
  archive honestly reversible, which is what the inbox tells the owner.
* **`.env.example` moved from slice 5 to slice 3**, because the darkness tests
  assert its wording.
* **The consent copy's closing sentence differs from the draft wording the
  follow-up brief suggested** ("he archives what he has read and removes
  messages when they are no longer needed"). *Removes* was dropped: v1 has no
  delete procedure, no purge, and no delete control anywhere, so a removal
  claim would have replaced one untrue sentence with another under a decision
  whose whole point was truthfulness. The owner's framing ("Pete manages these
  himself", archiving named explicitly) is kept.

## Running the tests

```
venv/bin/python -m pytest tests/ask_pete_direct/ -q
venv/bin/python scripts/govern_sql_migrations.py check
```

No test in this package opens a database connection or calls a model provider.
The database is mocked at the `database_service` seam; the procedures' real
behaviour is proven by the verifier during the gate.
