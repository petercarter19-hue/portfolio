# PeerSlate Completion Record — PS-ASK-PETE-DIRECT-001

_Implementation build, 2026-08-08. Uses
`docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`._

## Core record

**Task/package and delivery path:** PS-ASK-PETE-DIRECT-001 — the private
recruiter-question path. **Protected**, because it adds a new store of
member-private data written by anonymous callers, a new authorization surface,
and a consent contract. The Protected triggers that did **not** fire: no
deletion path, no publication path, no consequential AI, no shared
infrastructure change, no materially revised visual direction.

**Outcome and member/site effect:** **None. Zero runtime effect today.** The
work is complete as source and dark by construction. A recruiter cannot reach
it, Pete cannot open the inbox, and no database carries the tables. Three
independent gates each hold on their own:

1. `ask_pete_direct_routes.py` is imported by nothing. `app.py` belongs to
   PS-INTERVIEW-STUDIO-FUNCTIONAL-V1-001 and was not touched, so the blueprint
   is unregistered and the routes do not exist at run time.
2. The migration is registered with `gate: null`; the governed applier refuses
   it. No schema moved.
3. `PEERSLATE_ASK_PETE_DIRECT_ENABLED` defaults false and is read with
   `is True`, so a non-boolean value cannot enable it.

With the flag off, `templates/partials/ask_pete_evidence_companion.html`
renders byte-for-byte what it rendered before this package existed — asserted,
not assumed, by rendering the partial against a copy of its own source with the
new conditional block cut out and comparing the two outputs.

**Branch, base SHA, final SHA, and changed paths:**

- Branch: `work/2026-08-08-ask-pete-direct-001`
- Base: `edd5cc4` (the merged activation record), from `origin/main` `cadbc55`
- Slice SHAs: `b2b2f10` (S1 migration set) → `1a7f6c2` (S2 allowlist +
  service) → `5657d72` (S3 blueprint endpoint) → `2e653c2` (S4 companion form)
  → **final: the commit carrying this record** (S5 owner inbox + package
  record)
- Changed paths:
  - `SQL FIles/Migrations/proposed/PS-ASK-PETE-DIRECT-001_recruiter_questions.sql` (new)
  - `SQL FIles/Migrations/proposed/PS-ASK-PETE-DIRECT-001_recruiter_questions_rollback.sql` (new)
  - `SQL FIles/Verification/PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql` (new)
  - `SQL FIles/Migrations/registry.json` (one entry appended, `gate: null`)
  - `services/database_service.py` (three allowlist names + comments)
  - `services/ask_pete_direct_service.py` (new)
  - `ask_pete_direct_routes.py` (new, unregistered)
  - `templates/ask_pete_inbox.html` (new)
  - `templates/partials/ask_pete_evidence_companion.html` (one flag-conditional block)
  - `static/js/ask-pete-evidence-companion.js` (the form inside the handoff card)
  - `static/css/ask-pete-resume-evidence.css` (appended namespaced rules)
  - `.env.example` (the flag)
  - `tests/ask_pete_direct/` (new: `support.py`, `test_migration.py`,
    `test_service.py`, `test_endpoint.py`, `test_companion.py`,
    `test_inbox.py`, `test_darkness.py`)
  - `tests/test_database_service.py` (allowlist mirror — see limits below)
  - `docs/initiatives/PS-ASK-PETE-DIRECT-001/` (new)
  - **`app.py`: not touched.** No other lane's surface was touched.

**Verification performed and result:**

| Command | Result |
|---|---|
| `venv/bin/python -m pytest tests/ask_pete_direct/ -q` | **188 passed, 245 subtests passed** |
| `venv/bin/python -m pytest tests/ -q` (whole suite, once) | **3174 passed, 5 skipped, 3960 subtests passed**, 73s |
| `venv/bin/python scripts/govern_sql_migrations.py check` | **exit 0** — "Registry is internally consistent and every gate proof matches"; PS-ASK-PETE-DIRECT-001 listed as `draft (no gate proof)`, which is the truthful state |
| `pytest tests/ask_pete/ tests/test_governance_pointers.py tests/test_database_service.py tests/test_schema_migration_path.py` (with the package) | **387 passed, 360 subtests passed** |

Complete-diff self-review performed once across all five slices.

**Release state:** **local only.** No push, no PR, no pipeline, no deployment,
no schema apply, no enablement. A merge of this branch would change no deployed
behaviour whatsoever, which is the point.

**Known limits, deferred work, or owner decision needed:**

1. **The consent copy's retention sentence is a policy statement, not an
   automated mechanism, and must be reconciled before the flag is ever turned
   on.** Senders are told Pete's retention policy is to archive at 90 days and
   remove at 180. This package automates neither, and cannot automate the
   removal half: it is a hard delete, which the lane's recorded exclusions
   forbid. **Owner decision required:** either the scheduled maintenance leg
   lands first, or the sentence is rewritten to describe only what happens.
2. **Rate limiting is declared, not applied.** A blueprint cannot reach
   `app.py`'s `Limiter`. `PLANNED_RATE_LIMITS` states the budgets (30/hour
   public write, 60/hour owner action) and a test asserts the mapping covers
   every state-changing endpoint, but until the registration leg wires them the
   endpoint is unlimited — which is safe only because it is also unreachable.
   No parallel counter was invented as a substitute.
3. **The migration has no gate proof**, so nothing may apply it. The
   disposable-database apply/reapply/verify/rollback/forward rehearsal is an
   owner-attended leg.
4. **No browser evidence exists, and none could be produced in this lane.** The
   form cannot render anywhere until the blueprint is registered. Its markup,
   labelling, live regions, focus ring, target sizes, and state copy are
   asserted at source level; the visual and keyboard pass belongs to the
   registration leg, before enablement.
5. **Enablement additionally requires `PEERSLATE_OWNER_USER_KEYS` to name
   exactly one key.** Zero, several, or an email-only owner allowlist leaves
   every send answering an honest 503 rather than guessing a recipient.
6. **`tests/test_database_service.py` was edited although the implementation
   brief's writable list did not name it.** Its
   `test_the_allowlist_is_exactly_this_set_and_nothing_more` asserts set
   equality against a hardcoded literal and count, and its own docstring
   requires "a matching, reviewed change to the literal set" whenever
   `ALLOWED_PROCEDURES` changes. The edit adds a labelled three-name group and
   moves the exact count 131 → 134. The set-equality and non-overlap
   assertions are untouched, so the test is exactly as strong as before, and
   the file is not a surface of any other active lane (the Interview lane is
   explicitly excluded from database service change). Flagged rather than done
   quietly.
7. **No unread badge on another owner surface.** The package brief mentioned
   one; every surface that could host it belongs to another lane. The count
   exists (`new_count`) for whichever lane later owns that surface.

**Next action:** Fable's non-writer review of this exact candidate SHA, then
Pete's decision on limit 1 (the retention sentence). Registration, gate,
apply, deployment, and enablement remain separate recorded legs in that order.

## Protected additions

### Data, identity, privacy, authorization

**Contract changed.** Two new tables and three new procedures, all additive.
`dbo.recruiter_questions` holds one question addressed to one member's profile;
`dbo.recruiter_question_save_requests` is a replay ledger holding a key and a
reference and no content of any kind. Nothing existing was altered, dropped, or
re-shaped.

**Threat/risk review — the five risks this design actually carries, and what
answers each:**

| Risk | Control |
|---|---|
| An anonymous caller writes into an arbitrary member's inbox | The recipient is read from `PEERSLATE_OWNER_USER_KEYS` server-side. A payload naming a recipient is refused as an unexpected field before anything runs. The procedure resolves the key itself and never accepts a profile id. |
| Storage without consent | Three independent refusals: the form's checkbox, the service's `consent is not True` (which rejects `1`, `"true"`, `"on"` and every other truthy value), and the procedure's `@ConsentGiven <> 1` THROW positioned ahead of every INSERT — verified by position, not just by presence. |
| A replayed idempotency key discloses another sender's submission | The submit procedure returns an outcome word and **nothing else** — never the question key. A caller replaying a key learns only that the key was used. The verifier asserts the return shape. |
| Private text leaking into audit or the ledger | Audit metadata carries only `has_contact` (a boolean) and the consent version. The ledger has no content column. Both are asserted at source level and again by the verifier against a real server. |
| Cross-member read or write through the inbox | Every predicate re-asserts `owner_profile_id = @ProfileId`; status changes are fenced by `@ExpectedRowVersion`; `@owner_required` guards the page **and** the action independently, each answering a bare 404. |

**Migration and rollback proof — status: NOT YET PROVEN, deliberately.** The
migration carries a registry entry with `gate: null`, a verifier, and a
rollback. `govern_sql_migrations.py check` passes and correctly reports it as
ungated, so the applier refuses it. The executable proof is the owner-attended
disposable-database gate, which has not run. This record makes no claim that
it has.

The rollback's own contract is worth stating plainly: **it refuses to run while
any question is stored.** A stored question is something a real person chose to
send privately; discarding it because an operator is reversing a schema change
would destroy their message without their knowledge and without Pete ever
reading it. Structurally, the script executes no `DELETE` and no `UPDATE`
against either table anywhere in its control flow — an empty-table `DROP` is
the only removal it can perform.

**Permission and negative-path evidence.** Covered executably in
`tests/ask_pete_direct/`:

- flag off → neutral 404 for every route, identical for a cross-site and a
  same-origin caller, with nothing reaching the database;
- a non-boolean flag value (`"true"`, `1`, `"yes"`, `[1]`) → still 404;
- missing/wrong `X-PeerSlate-Request`, foreign `Origin`, cross-site
  `Sec-Fetch-Site`, non-JSON body → 403/415, nothing stored;
- a form post proving neither `Origin` nor `Sec-Fetch-Site` → 403 (fail closed);
- every rung of the validation ladder, including consent as `False`, `None`,
  `1`, `"true"`, `"on"`, `"yes"`, `[]`, `{}` and absent → 422, nothing stored;
- an unexpected field, including one naming a recipient → 422, nothing stored;
- a filled honeypot → 422, and explicitly **not** a faked success;
- bounds at the exact SQL limits, and one unit over, counted in UTF-16 code
  units (an astral character that `len()` would undercount is rejected);
- an oversized body → 413 before parsing;
- a double submit under one key → one stored question, `already_sent`;
- the inbox: anonymous → 404, signed-in non-owner → 404, unconfigured
  allowlist → 404, flag off → 404 even for the owner;
- a stale `expected_version` → nothing altered, `state=changed`;
- an unknown status (`deleted`, `purged`, `""`) → never reaches the database;
- a storage failure → an honest 503 that never implies an empty inbox and
  never leaks a procedure name;
- an unresolvable recipient → 503, never reported as sent;
- no delete exists anywhere: not in a procedure body, not as a procedure, not
  on the service, not on the page.

### Material visual work

**Not triggered — and here is why that is a claim rather than an omission.**
The sender-facing form introduces no new visual language: it carries the
accepted `.ask-pete-evidence-composer` classes, so its label, field grid,
textarea, and submit are the accepted treatment unchanged. The appended CSS is
namespaced `.ask-pete-direct*` throughout (asserted by parsing every selector
in the appended section), uses only existing tokens, adds no
`prefers-color-scheme` variant, and is appended after every accepted rule so
nothing above it is reordered.

The allowed non-material adaptations, documented: the accepted focus ring
covered `a, button, textarea` only, because no `input` was reachable in the
companion before this form existed — the same ring at the same offset is
extended to the consent checkbox and the disclosure summary; and a second
`forced-colors` block is appended rather than editing the accepted one. The
owner inbox is an owner-only utility page in the Control Room's
server-rendered idiom, light-only, JavaScript-free.

Accessibility asserted at source level (no runtime is available in this lane —
see limit 4): both fields labelled, the contact field described, the state line
a live region that also announces through the companion's shared one, the
honeypot `aria-hidden` and out of the tab order, 2.75rem minimum targets, and
every failure state's text beginning "Not sent" so colour is never the only
signal.

**Owner visual decision:** none required, and none assumed. If Pete considers
any of it material, it returns to the ChatGPT visual-creation lane before
enablement.

### Shared infrastructure or broad release

Not triggered. No deployment, no pipeline change, no configuration change to
any running service, no new dependency, and no new secret. The only shared
file touched is `services/database_service.py`, and only to add three names to
its allowlist.

### Actual handoff

Not a handoff. Claude Opus 5 was the sole delegated implementation writer in
`portfolio-ask-pete-direct-001`; independent review by Claude Fable 5, which
did not write this code, is the next action.

---

**Result: Pass, with the six limits above recorded and open.** No fixture is
called live, no merge is called deployed, no migration is called applied, and
no AI proposal is involved anywhere in this package.
