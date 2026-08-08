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

## What "dark" means here, precisely

Three independent things must all change before a visitor can reach any of
this. None of them happened in this package:

1. **Registration.** `ask_pete_direct_routes.py` is imported by nothing.
   `app.py` belongs to PS-INTERVIEW-STUDIO-FUNCTIONAL-V1-001, so the two-line
   blueprint registration is a later recorded leg. Until then the routes do not
   exist at run time. `tests/ask_pete_direct/test_darkness.py` asserts this and
   is designed to FAIL the day someone registers it — that failure is the
   tripwire that forces the registration to be a deliberate, reviewed act.
2. **Schema.** The migration is registered with `gate: null`, which the
   governed applier refuses. No database carries these tables.
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
| `SQL FIles/Migrations/registry.json` | Registry entry, `gate: null`. |
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

1. **The retention sentence is a policy statement, not an automated
   mechanism.** The consent copy says Pete's retention policy is to archive at
   90 days and remove at 180. **This package automates neither.** It cannot:
   removal is a hard delete, which the lane's recorded exclusions forbid. Before
   the flag is ever turned on, either the scheduled maintenance leg lands (the
   `usp_PurgeCommunityContent` out-of-process pattern) or the consent sentence
   is rewritten to describe only what actually happens. Pete decides which.
2. **Rate limiting is declared, not applied.** `PLANNED_RATE_LIMITS` names the
   budgets (30/hour for the public write, 60/hour for the owner action); the
   registration leg must wire them with the post-registration limiter-wrapper
   idiom in `app.py`. No parallel counter was invented here instead.
3. **The migration has no gate proof.** The disposable-database
   apply/reapply/verify/rollback/forward rehearsal and the production apply are
   an owner-attended leg.
4. **`PEERSLATE_OWNER_USER_KEYS` must name exactly one key.** Zero, several, or
   an email-only owner allowlist leaves every send answering an honest 503.
5. **No browser evidence exists yet, and could not.** The form cannot render
   anywhere until the blueprint is registered, so its appearance and keyboard
   path are asserted at source level only. Capture browser evidence during the
   registration leg, before enablement.
6. **No unread badge on another owner surface.** The package brief mentioned
   one; every surface that could host it belongs to another lane. The count is
   available (`usp_ListRecruiterQuestionsForOwner` returns `new_count`) for
   whichever lane later owns that surface.

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
  one-way archive would leave a mis-archived question stranded until the
  180-day policy removed it. Restoring is not a new capability class — it is
  the same version-fenced status write — and it makes archive honestly
  reversible, which is what the inbox tells the owner.
* **`.env.example` moved from slice 5 to slice 3**, because the darkness tests
  assert its wording.

## Running the tests

```
venv/bin/python -m pytest tests/ask_pete_direct/ -q
venv/bin/python scripts/govern_sql_migrations.py check
```

No test in this package opens a database connection or calls a model provider.
The database is mocked at the `database_service` seam; the procedures' real
behaviour is proven by the verifier during the gate.
