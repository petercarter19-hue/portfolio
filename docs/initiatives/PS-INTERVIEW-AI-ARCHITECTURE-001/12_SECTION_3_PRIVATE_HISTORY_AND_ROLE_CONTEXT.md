# Section 3 — Private History, the History Nudge, browser migration, and Role Context consumption

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Gate:** B — staged architecture, increment 3 (Private History Nudge and private retrieval).
**Status:** Architecture proposal for Pete and Codex review. Documentation only.
**Runtime effect:** None. No application, schema, migration, prompt, provider, configuration, or live behavior changes with this file. Every runtime slice named here requires its own separate Protected activation.
**Evidence base:** `01_GATE_A_CURRENT_SYSTEM_DIAGNOSIS.md` §§7–8 as corrected by `02_GATE_A_ERRATA.md` (E4 especially); accepted owner decisions `06_INTERVIEW_AI_OWNER_DECISIONS.md` and `07_INTERVIEW_AI_ACCEPTED_DIRECTION_CONTINUATION.md`; existing accepted authority `docs/initiatives/PS-INTERVIEW-ROLE-CONTEXT-001/`; and the deployed source (byte-identical to diagnosed SHA per errata E6): `app.py:1972-1986`, `app.py:4113-4200`, `static/js/interview-studio.js:45-60, 340-400, 1875-2005, 5140-5160`.

---

## Plain-language summary

- Today, practice History lives only inside the member's browser. It cannot follow them to another device, cannot be searched, and silently throws away the oldest record once 100 exist. Deleting a record in the browser does work today (each record, or all at once) — but only in that browser.
- This section designs the account-backed version: History that belongs to the member's account, is private by default, can be searched and filtered, corrected, archived, and deleted — and when a member deletes something, it is provably gone from every place the system could find it again, not just hidden from a list.
- It designs the real "Need a nudge?": PeerSlate searches only that member's own History for similar questions and first shows a short reminder — question, date, a small excerpt. The full prior answer reaches the AI only after the member picks it, and the server, not the browser, enforces that rule.
- Moving existing browser History into the account is optional, previewed record-by-record, and never automatic. The member is also told the truth that the browser kept at most their 100 most recent records, so older practice may already be gone.
- Role context (the job the member is practicing for) keeps the already-accepted contract from PS-INTERVIEW-ROLE-CONTEXT-001. This section only defines how Interview AI consumes it, and confirms the role-tailored question generator stays future work.

---

## 1. The one design, in one paragraph

Account-backed History is stored in the existing production Azure SQL database, in owner-scoped tables reached only through allowlisted `usp_*ForOwner` stored procedures that resolve identity server-side, exactly in the idiom Opportunity Slate already ships. **Authoritative storage and revocable projections are physically separate tables in the same database**, and every projection row is bound to its authoritative record with an enabled, trusted `ON DELETE CASCADE` foreign key and is maintained in the **same transaction** as every record mutation — so deletion and revocation are transactional facts, not eventually-consistent hopes. The initial retrieval path is **deterministic in-database lexical search over a synchronously maintained projection table — not Azure AI Search and not embeddings**. The History Nudge is a two-step boundary: step 1 is a provider-free, owner-scoped candidate search that structurally cannot return full content; step 2 requires a server-minted, single-use, expiring **selection authorization row** before the full prior answer can enter a provider payload. Browser History migrates only through an explicit, previewed, per-record, idempotent import. Role Context is consumed read-only, version-pinned, and untrusted, from the contract PS-INTERVIEW-ROLE-CONTEXT-001 already fixed.

---

## 2. Part A — Account-backed private History

### 2.1 What exists today, integrated rather than ignored (errata E4)

There is no server-side History of any kind (diagnosis §8: no table, no migration, no service). The browser holds the only copy: member-scoped `peerslate:interview-studio:<scope>:v3:history` keys (`interview-studio.js:52-56`), a non-destructive sanitizing read boundary (`readHistoryRecords()`, `:1971`), a silent 100-record cap (`records.slice(0, 100)`, `:1983`), **working per-record local deletion** (`removeHistoryRecord()`, `:1997`) and **working confirm-guarded bulk local clear** scoped to the member's own `:v3` keys only (`:5140-5157`, owner decision Q-B). This design **extends** those affordances: local delete/clear keep governing local data with their existing "this browser" copy; account records get their own server-side delete, archive, exclude, and clear actions. Neither side ever triggers the other.

### 2.2 The two-plane rule

Every piece of History data lives on exactly one of two planes:

| Plane | Contents | Mutability | Deletion behavior |
|---|---|---|---|
| **Authoritative storage** | The practice record, its append-only answer versions, its review artifacts, member settings | Written only by owner-scoped procedures on explicit member action | Member delete = physical `DELETE` in one transaction |
| **Revocable projections** | The search projection row (normalized text, filter columns, precomputed excerpt); outstanding selection authorizations | Never written directly; maintained by the same procedures, same transaction | Removed by `ON DELETE CASCADE` in the deleting transaction; kept consistent by the same-transaction discipline |

Round one deliberately keeps **every projection inside the same Azure SQL database**. That single choice is what makes revocation provable instead of asserted: there is no second system to reconcile, no crawl delay, no cache tier holding member text. There is **no server-side cache of History content anywhere** — request-scoped memory only — so "removed from every cache" is true by construction and stated as such, not enforced by a purge job that could fail.

### 2.3 Authoritative schema

Design shapes below follow the shipped Opportunity Slate idiom: `dbo.` tables, internal `BIGINT` identity keys, external `UNIQUEIDENTIFIER` opaque keys (the service layer already validates these as UUIDs — `_opaque_key`, `services/opportunity_slate_v2_service.py:174`), `DATETIME2` UTC columns, `rowversion` optimistic-concurrency tokens, UTF-16 code-unit bounds (`utf16_length`, `:159`), and set-equality row discipline (`_require_exact_fields`, `:164`). Text bounds mirror the browser sanitizer's existing bounds (`sanitizeHistoryRecord`, `interview-studio.js:1908-1967`) so import loses nothing.

```sql
-- Future migration: SQL FIles/Migrations/proposed/PS-INTERVIEW-HISTORY-001_private_history.sql
-- (+ _rollback.sql sibling, + owner-isolation and revocation verifiers; see 2.8)

dbo.interview_history_records
  record_id             BIGINT IDENTITY      PRIMARY KEY          -- internal only
  record_key            UNIQUEIDENTIFIER     NOT NULL UNIQUE       -- external opaque key
  owner_profile_id      BIGINT               NOT NULL              -- resolved from @UserKey inside every procedure
  client_record_id      NVARCHAR(160)        NULL                  -- browser record id when imported (sanitizer bound :1910)
  import_batch_key      UNIQUEIDENTIFIER     NULL
  import_fingerprint    BINARY(32)           NULL                  -- SHA-256 of canonicalized imported content (dedupe)
  record_provenance     NVARCHAR(20)         NOT NULL CHECK IN ('studio_save','browser_import')
  question_text         NVARCHAR(1200)       NOT NULL              -- browser bound :1911
  question_family       NVARCHAR(40)         NOT NULL              -- CHECK-pinned to the existing closed family enum
  competency            NVARCHAR(80)         NOT NULL
  experience_level      NVARCHAR(20)         NOT NULL CHECK IN ('entry','experienced','management','leadership','mixed')
  practice_mode         NVARCHAR(10)         NOT NULL CHECK IN ('me','ai','video')
  attempt_number        INT                  NOT NULL DEFAULT 1
  duration_seconds      INT                  NOT NULL DEFAULT 0
  role_context_key      UNIQUEIDENTIFIER     NULL                  -- opaque, version-pinned reference; never a copied source body
  role_context_version  INT                  NULL
  role_label            NVARCHAR(160)        NULL                  -- member-owned practice metadata captured at save time
  employer_label        NVARCHAR(160)        NULL                  -- (survives later role-context deletion; see 5.4)
  imported_context_json NVARCHAR(4000)       NULL                  -- opaque snapshot of a browser record's local context; never AI-eligible
  review_generation     NVARCHAR(20)         NOT NULL CHECK IN ('v2','legacy-v1','local-recording')
  lifecycle_state       NVARCHAR(20)         NOT NULL CHECK IN ('active','archived') DEFAULT 'active'
  ai_eligibility        NVARCHAR(20)         NOT NULL CHECK IN ('eligible','excluded') DEFAULT 'eligible'
  current_version_number INT                 NOT NULL DEFAULT 1
  created_at_utc        DATETIME2            NOT NULL              -- original practice time (imported records keep theirs)
  saved_at_utc          DATETIME2            NOT NULL              -- when it entered the account
  updated_at_utc        DATETIME2            NOT NULL
  row_version           ROWVERSION
  -- UNIQUE filtered index (owner_profile_id, client_record_id) WHERE client_record_id IS NOT NULL

dbo.interview_answer_versions                                      -- append-only; no UPDATE procedure exists for this table
  version_id            BIGINT IDENTITY      PRIMARY KEY
  record_id             BIGINT NOT NULL  FK -> interview_history_records ON DELETE CASCADE
  owner_profile_id      BIGINT               NOT NULL              -- owner re-asserted in every predicate
  version_number        INT                  NOT NULL              -- UNIQUE (record_id, version_number)
  version_provenance    NVARCHAR(30)         NOT NULL CHECK IN
                        ('member_original','member_edit','ai_revision_accepted','restored_from_version')
  answer_text           NVARCHAR(MAX)        NOT NULL              -- app-enforced <= 5,000 UTF-16 units (browser bound :1950)
  created_at_utc        DATETIME2            NOT NULL

dbo.interview_reviews                                              -- one row per stored review of a version
  review_id             BIGINT IDENTITY      PRIMARY KEY
  record_id             BIGINT NOT NULL  FK -> interview_history_records ON DELETE CASCADE
  owner_profile_id      BIGINT               NOT NULL
  version_number        INT                  NOT NULL
  verdict               NVARCHAR(160)        NOT NULL
  encouragement         NVARCHAR(600)        NULL
  stronger_approach     NVARCHAR(900)        NULL
  focused_follow_up     NVARCHAR(300)        NULL
  specialist_version    NVARCHAR(80)         NULL                  -- Section 1's version identity, when produced server-side
  created_at_utc        DATETIME2            NOT NULL

dbo.interview_review_dimensions                                    -- browser bounds :1897-1900
  dimension_id  BIGINT IDENTITY PK;  review_id BIGINT NOT NULL FK -> interview_reviews ON DELETE CASCADE
  owner_profile_id BIGINT NOT NULL
  dimension_key NVARCHAR(80) NOT NULL;  dimension_status NVARCHAR(40) NOT NULL
  rationale NVARCHAR(400) NOT NULL;    next_action NVARCHAR(300) NOT NULL

dbo.interview_review_findings                                      -- strengths / improvements / what-came-through, <=4 each
  finding_id BIGINT IDENTITY PK;  review_id BIGINT NOT NULL FK -> interview_reviews ON DELETE CASCADE
  owner_profile_id BIGINT NOT NULL
  finding_class NVARCHAR(30) NOT NULL CHECK IN ('strength','improvement','came_through_clearly')
  finding_text NVARCHAR(400) NOT NULL;  ordinal INT NOT NULL

dbo.interview_history_settings                                     -- one row per member
  owner_profile_id      BIGINT               PRIMARY KEY
  saving_mode           NVARCHAR(20)         NOT NULL CHECK IN ('undecided','save_to_account','session_only')
                                             DEFAULT 'undecided'
  disclosure_acknowledged_at_utc DATETIME2   NULL                  -- set only by the member's explicit acknowledgement
  created_at_utc DATETIME2 NOT NULL;  updated_at_utc DATETIME2 NOT NULL
```

Labelled uncertainty: the exact canonical FK target for `owner_profile_id` (the profiles/users table name and key column) is stated here by idiom from the Opportunity Slate procedures' own comments ("re-asserts owner_profile_id in every predicate", `services/database_service.py:36`); the implementation package must pin it from the applied PS-PLAT migrations before writing SQL. The exact closed `question_family` enum values are pinned at implementation time from `_normalize_interview_family` — this document deliberately does not restate an enum it has not read in full.

### 2.4 Record lifecycle, correction, and member control

- **Active → archived → active**: reversible, member action, metadata only. Archived records remain in member search (behind a filter) and are **never** nudge candidates.
- **AI eligibility — `eligible` / `excluded`**: independent of archive. `excluded` records stay fully visible and searchable to the member but can never be selected into any AI context. Checked on the authoritative row at selection creation **and again at consumption** (3.3).
- **Correction**: metadata corrections (`competency`, `question_family`, `role_label`, `employer_label`) edit the record in place through `usp_CorrectInterviewHistoryRecordForOwner`, updating the projection in the same transaction. Answer corrections are never in-place: they append a new `interview_answer_versions` row (`member_edit`), move `current_version_number`, and rewrite the projection's normalized text and excerpt in the same transaction. The original answer version is written once and never updated — the same write-once discipline Opportunity Slate applies to `original_text`.
- **Deletion**: `usp_DeleteInterviewHistoryRecordForOwner` performs a physical `DELETE` of the record; versions, reviews, dimensions, findings, the projection row, and any outstanding selection rows go with it via enabled, trusted cascades **in the same transaction**. No tombstone: a private practice record has no downstream referent that needs one, and `archived`/`excluded` already cover every reversible intent. Bulk clear is `usp_ClearInterviewHistoryForOwner`, gated by a literal confirmation field (4.5-style `{"confirm":"delete-all-history"}`) — deliberately parallel to, and separate from, the browser-local clear at `interview-studio.js:5140`.
- **Deletion honesty (member-facing copy, required)**: "Deleted records are removed immediately from your History, search, and all AI use. Encrypted database backups retain deleted data until they expire on their normal schedule." The exact Azure SQL PITR window for `peerslate-database` is configuration this document has not read (default 7 days, configurable to 35); the implementation package verifies and states the real number. No impossible instantaneous-erasure promise is made — matching the accepted decision's wording exactly.
- **Saving is never silent**: `usp_SaveInterviewHistoryRecordForOwner` refuses unless the request is an explicit member save action, or `saving_mode = 'save_to_account'` **and** `disclosure_acknowledged_at_utc` is set. `'undecided'` saves nothing and triggers the one-time disclosure choice in the UI. Choosing `session_only` disables future saving **without deleting existing records** — the procedure that sets it touches only the settings row. These are procedure-level refusals, not UI conventions.

### 2.5 The search projection (the initial retrieval path — deliberately not Azure AI Search)

```sql
dbo.interview_history_search_projection                            -- REVOCABLE PROJECTION, one row per non-deleted record
  projection_id         BIGINT IDENTITY      PRIMARY KEY
  record_id             BIGINT NOT NULL UNIQUE FK -> interview_history_records ON DELETE CASCADE
  owner_profile_id      BIGINT               NOT NULL              -- every query predicates on this, always
  question_normalized   NVARCHAR(1200)       NOT NULL              -- lowercased, whitespace-collapsed
  answer_normalized     NVARCHAR(MAX)        NOT NULL              -- current version only, normalized ('' for text-free video records)
  excerpt_text          NVARCHAR(280)        NOT NULL              -- precomputed at write time; the ONLY content field step 1 may return
  question_family NVARCHAR(40) NOT NULL;  competency NVARCHAR(80) NOT NULL
  experience_level NVARCHAR(20) NOT NULL;  practice_mode NVARCHAR(10) NOT NULL
  role_label NVARCHAR(160) NULL;  employer_label NVARCHAR(160) NULL
  lifecycle_state NVARCHAR(20) NOT NULL;  ai_eligibility NVARCHAR(20) NOT NULL   -- denormalized copies, same-transaction maintained
  has_answer_text       BIT                  NOT NULL              -- selection of empty-answer records is refused (3.3)
  created_at_utc        DATETIME2            NOT NULL
```

**Maintenance discipline:** only the owner-scoped write procedures touch this table, and always inside the transaction that mutates the authoritative record — save, import, correct, new version, archive, exclude, delete. No trigger, no background indexer, no scheduler: this runtime has none (the Opportunity Slate purge design records the same constraint) and this design does not introduce one.

**Retrieval algorithm (deterministic, provider-free):**

- *Member manual search* — `usp_SearchInterviewHistoryForOwner(@UserKey, @QueryText, @Family, @Competency, @Mode, @IncludeArchived, @FromUtc, @ToUtc, @Page)`: parameterized token `LIKE` matching over `question_normalized` and `answer_normalized`, with the metadata filters the accepted decision names (role, company via the label columns, type, competency, date, mode), newest first. Returns list metadata + `excerpt_text` only.
- *Nudge candidate search* — `usp_FindInterviewNudgeCandidatesForOwner(@UserKey, @QuestionNormalized, @Family, @Competency)`: hard-pinned predicate `lifecycle_state = 'active' AND ai_eligibility = 'eligible'` (in the SQL, not in the caller), deterministic score
  `score = 3*(family match) + 2*(competency match) + (count of query tokens, minimum length 3, capped at 8, present in question_normalized)`,
  recency as tiebreak, **top 5 maximum**. Zero rows is the legitimate `no_history_match` outcome, not an error.

**Why this path:** it adds zero infrastructure, inherits the database's existing security and backup posture, keeps revocation transactional (2.6), is fast at honest round-one scale (a private member's own records — hundreds, not millions), and is fully evaluable offline without a provider. Its known weakness is stated plainly: pure lexical overlap misses paraphrases ("tell me about a conflict" vs "describe a disagreement with a coworker"). The family/competency boost covers part of that; the rest is the explicit, measured trigger for the upgrade below — not a reason to build semantic infrastructure speculatively.

**Exact conditions under which a later Azure AI Search (or embeddings) path is justified — all five, together:**

1. **Measured retrieval failure on real volume**: the Section 8 evaluation slice's paraphrase-recall cases, or live no-match/mis-match telemetry (content-free counters), show the lexical path failing at a rate Pete judges member-harming, after ranking-weight tuning has been tried and measured.
2. **Measured performance failure**: p95 member-facing search latency exceeds its budget at real member record volumes — not projected volumes.
3. **The out-of-database revocation contract is designed and proven first**: an external index cannot ride a foreign-key cascade, so that package must deliver a projection epoch/outbox, deletion reconciliation with a standing proof query (authoritative eligible count vs index document count, mismatch alarms), a verified deletion SLA stated to members honestly, and a kill-switch that falls back to this lexical path.
4. **Provider/service facts verified at that release time** — region, retention, key handling, cost — per the accepted rule that PeerSlate cannot rely on old assumptions, and never promises a third party's retention behavior.
5. **A separate Protected package with Pete's explicit acceptance of the recurring cost.** Embeddings additionally inherit the accepted constitution's rule as-is: private derived data bound to the source record's owner, permission, retention, revocation, and deletion lifecycle, never used for cross-member ranking or profiling.

Until all five hold, Azure AI Search remains prematurely implemented by definition — the owner direction this section is bound to.

### 2.6 Revocation propagation — the design

Revocation means: after a member deletes a record (or excludes it from AI), **no code path can return its content to the member's screen, to search, to a candidate list, or to a provider payload**. Propagation is achieved by construction, in one transaction, with no asynchronous step:

1. **One entry point per intent.** Delete, archive, exclude, and clear each run through exactly one allowlisted `ForOwner` procedure. There is no second write path (the service layer refuses non-allowlisted procedures — `services/database_service.py:251`).
2. **Cascade, not cleanup.** Versions, reviews, dimensions, findings, the projection row, and outstanding selection rows all carry enabled, trusted `ON DELETE CASCADE` foreign keys to the record. The deleting transaction removes them all or removes nothing.
3. **Exclusion propagates synchronously.** `usp_SetInterviewHistoryAiEligibilityForOwner` updates the authoritative row and its projection copy in the same transaction, and deletes any outstanding unconsumed selection rows for that record.
4. **Consumption re-checks the authoritative row.** Even a selection minted seconds before a deletion is refused at use time, because consumption re-reads the authoritative record under the owner predicate and requires `active`/`eligible`/version-current (3.3). The projection is never the last word — the accepted rule "rechecked on authoritative records returned from a search projection," implemented literally.
5. **Nothing else exists to purge.** No server-side content cache, no embedding store, no external index, no queue carrying member text — in round one these are absent by design, so the revocation surface is exactly the tables above.

### 2.7 Revocation proven, not asserted — the four proof artifacts

- **P1 — Migration gate rehearsal.** The future migration's apply gate (same practice as the recorded PS-OPPSLATE-001 gate: throwaway database, apply → verify → exercise → rollback → re-apply) includes a scripted create → delete → zero-residue pass: insert a synthetic member's record with versions, reviews, projection, and an unconsumed selection; delete through the procedure; assert row count zero across all six child/projection tables for that record key. The result is recorded in the migration header per house practice.
- **P2 — Standing verifier.** `SQL FIles/Verification/PS-INTERVIEW-HISTORY-001_revocation_verify.sql`, runnable against production at any time, asserts: (a) every FK in the package is enabled and trusted (`sys.foreign_keys.is_disabled = 0 AND is_not_trusted = 0` — a disabled cascade is the one way orphans become possible, so its enabled state *is* the proof); (b) zero projection rows whose denormalized `lifecycle_state`/`ai_eligibility` disagree with the authoritative record; (c) zero selection rows referencing missing or excluded records; (d) zero child rows without a parent. Owner isolation gets the sibling `_owner_isolation_verify.sql` every data package here already ships.
- **P3 — Contract tests (Python, provider-free).** Delete → member search returns nothing; delete → candidate search returns nothing; selection minted pre-delete refused post-delete; selection refused after exclusion; excluded record visible in member search but absent from candidates; import idempotency (4.4); cross-member key returns the uniform not-found (2.9).
- **P4 — Continuous runtime shape enforcement.** Every row the service reads passes the set-equality field check (`_require_exact_fields` idiom): if anyone ever widens the step-1 procedure's result set to include a content column, every read **fails loudly in production** rather than silently over-disclosing. The bounded-disclosure boundary is thereby enforced at runtime forever, not just at review time.

### 2.8 Answer versions and the Revision Partner boundary

`interview_answer_versions` is the storage contract behind Section 2's Revision Partner: the original is version 1 (`member_original`) and is never mutated; accepting an AI revision as working draft appends `ai_revision_accepted`; restore appends `restored_from_version` copying an earlier version's text forward. Compare/discard need no storage — discard simply appends nothing. Diagnosis flags the browser-side version shape as UNVERIFIED (§8); this schema is the account-side contract regardless, and import (Part C) maps only the single current answer the sanitized browser record actually carries.

### 2.9 Anti-enumeration and authorization posture

All record reads and writes go through `ForOwner` procedures that resolve `@UserKey` server-side from the authenticated identity (`get_current_identity()` via `_interview_api_authenticated_identity()`, the guard every Interview endpoint already calls first — errata E5) and predicate every statement on the resolved owner. A forged, guessed, or other-member `record_key` produces the same no-row result as a nonexistent one — the procedure cannot even see other members' rows, so no code path exists that could distinguish "not yours" from "not there." Responses are a uniform not-found. Client-supplied IDs, slugs, emails, and any History-owner field are never authorization inputs; the new request schemas contain no owner field at all.

Rejected alternatives, one sentence each: **Azure AI Search now** — owner direction forbids premature implementation and the out-of-database revocation burden is unjustified at current volume. **Embeddings-first retrieval** — same external-revocation burden plus routing private answer text through an embedding provider for marginal round-one gain. **SQL Server full-text (`CONTAINSTABLE`)** — index population is an asynchronous crawl, so deletion-to-index-removal is not provable inside the deleting transaction. **localStorage-plus-sync** — leaves the browser authoritative, making server-side revocation and cross-device truth permanently unfixable. **Tombstone soft-delete for member deletes** — leaves content on disk against the member's stated intent when `archived`/`excluded` already cover every reversible case. **A projection-epoch counter in round one** — redundant while every projection shares the deleting transaction; it becomes mandatory (condition 3 above) the day any projection leaves the database.

---

## 3. Part B — Specialist 4: Private History Nudge

### 3.1 The two-step boundary is the design

Today's `/api/interview/nudge` is a generic hint generator whose prompt explicitly forbids history use (`app.py:4162`) and which receives no History — specialist 4 does not exist (diagnosis 11.2). The accepted specialist is built as **two server steps with a member decision between them**:

- **Step 1 — candidate reminder (provider-free).** Choosing **Need a nudge?** authorizes exactly one thing: a deterministic search of that member's own History. The response is bounded metadata plus the precomputed ≤280-unit excerpt. No provider call occurs. Full answer text is structurally absent from the result set (P4).
- **Member decision.** The member picks one candidate (or none). Nothing is inferred from hesitation; skipping is a first-class path.
- **Step 2 — grounded nudge (provider call).** Only after a server-verified selection does the full prior answer enter a provider payload, fetched server-side from the authoritative table — never round-tripped through the browser.

### 3.2 Step 1 — `POST /api/interview/nudge/candidates`

Guard order (identical idiom to every existing Interview endpoint): authenticated identity → entitlements (`written_practice` or `model_answers`) → History capability flag → JSON/schema validation → rate limit `12 per minute`. Request (closed schema; unknown fields rejected as malformed):

```json
{ "question": "<current question, bounded as today>", "family": "behavioral", "competency": "Leadership" }
```

Response:

```json
{
  "status": "candidates",                         // or "no_history_match"
  "candidates": [
    {
      "record_key": "8f0c…",                      // opaque UUID
      "question": "Tell me about a time you led through a disagreement.",
      "practiced_at": "2026-06-02",
      "family": "behavioral", "competency": "Leadership",
      "mode": "me", "experience_level": "experienced",
      "role_label": "Product Manager", "employer_label": "Contoso",
      "excerpt": "<= 280 units, precomputed>",
      "selectable": true                          // false for text-free video records, with reason copy
    }
  ],
  "no_match_prompt": null
}
```

The `no_history_match` shape carries the accepted no-match behavior verbatim (3.5). The same four options are also rendered *under* a non-empty candidate list ("None of these fit?") so a member is never cornered by five wrong reminders.

### 3.3 Step 2 — selection as a server-enforced authorization act

```sql
dbo.interview_history_selections                                   -- REVOCABLE PROJECTION of member intent
  selection_id          BIGINT IDENTITY      PRIMARY KEY
  selection_key         UNIQUEIDENTIFIER     NOT NULL UNIQUE
  owner_profile_id      BIGINT               NOT NULL
  record_id             BIGINT NOT NULL  FK -> interview_history_records ON DELETE CASCADE
  answer_version_number INT                  NOT NULL              -- pins the exact text authorized
  purpose               NVARCHAR(20)         NOT NULL CHECK IN ('nudge')   -- extensible enum; only 'nudge' in round one
  created_at_utc        DATETIME2            NOT NULL
  expires_at_utc        DATETIME2            NOT NULL              -- created + 15 minutes
  consumed_at_utc       DATETIME2            NULL                  -- single-use
```

**`POST /api/interview/history/selections`** (`limiter: 12 per minute`) — body `{"record_key":"…","purpose":"nudge"}`. The server derives identity, re-authorizes the **authoritative** record (owner predicate, `active`, `eligible`, `has_answer_text`), and mints the row via `usp_CreateInterviewHistorySelectionForOwner`, returning `{"selection_key":"…","expires_at":"…"}`. Empty-answer records are refused with `insufficient_evidence`. This POST is the recorded, auditable member decision the accepted constitution's knowledge manifest requires ("authorization, selection, confirmation, revocation … without copying private text into logs").

**`POST /api/interview/nudge/grounded`** (`limiter: 6 per minute`, matching today's model-answer budget) — body:

```json
{ "question": "<current question>", "family": "behavioral", "competency": "Leadership",
  "experience_level": "experienced", "selection_key": "…" }
```

Server sequence, all deterministic, all before any provider byte:

1. Authenticated identity; entitlements; capability flag; closed-schema validation.
2. `usp_ConsumeInterviewHistorySelectionForOwner(@UserKey, @SelectionKey, @Purpose='nudge')` — atomically: row exists for this owner, unconsumed, unexpired, purpose matches → set `consumed_at_utc`; then **re-read the authoritative record** under the owner predicate and require `active` + `eligible` + `current_version_number = answer_version_number`. Any failure → fail closed, no provider call: missing/foreign/expired/consumed selection → uniform not-found (`unavailable_source` copy: "That History record is no longer available for this nudge."); version moved → `unavailable_source` with a truthful "that answer changed since you selected it" and a fresh step-1 offer.
3. Only the procedure's returned content — question, metadata, the pinned answer version text — is placed into the prompt, inside Section 1's shared untrusted-content envelope. **The request body cannot carry History content at all**: any content-bearing field is schema-rejected. The browser is a keyring here, never a courier of prior answers.

**Response** — the load-bearing facts are server-composed, so the model cannot misstate them (structural claim-support):

```json
{
  "status": "grounded",
  "reminder": {                                   // SERVER-composed from the authoritative record, not model output
    "question": "…", "practiced_at": "2026-06-02",
    "family": "behavioral", "competency": "Leadership",
    "role_label": "Product Manager", "employer_label": "Contoso"
  },
  "memoryHooks": ["<2-3 hooks, each <= 35 words, grounded in the prior answer>"],
  "adaptations": ["<1-2 notes on how this question differs from the prior one>"],
  "staleness_note": "<required when practiced_at is older than 180 days; reminds that a prior answer is preparation material, not automatically current>"
}
```

The model produces only `memoryHooks`, `adaptations`, and `staleness_note`; the validator (same fixed-literal error discipline as the four existing validators, `app.py:3402-3720`) enforces counts, lengths, and the staleness requirement deterministically. A prior answer is never presented as current truth or canonical evidence — it is a memory jog, labelled as such in the UI.

### 3.4 Specialist card (mandatory format)

| Field | Content |
|---|---|
| **Purpose** | Help the member remember a relevant prior experience for the current question, after they explicitly ask and explicitly select which memory to use. |
| **Input manifest** | `question` (client, bounded, untrusted); `history_selection` (server-fetched pinned answer version + metadata; provenance `account_history@v<n>`; authorization state `member_selected_consumed` — the only state the manifest builder accepts for this class); router/family/competency hints (untrusted labels). Never: other members' data, unselected candidates, complete History, Profile, Journal, evidence, open web. |
| **Output schema** | `{status, reminder(server-composed), memoryHooks[2..3], adaptations[0..2], staleness_note?}` — bounded strings, closed keys, validated before display; never persisted by the AI. |
| **Deterministic guardians** | identity (server-derived, first action); authorization (owner-predicated procedures; consumption re-check on authoritative row); source-allowlist (manifest accepts only the classes above); evidence-entitlement (`history_selection` requires a consumed selection row minted this request); injection-separation (Section 1's shared envelope; prior answers and questions are content, never instructions); content-bounds (all lengths above; 4,000-unit role-context bound); rate-limit (12/6 per minute); timeout (Section 1's deliberate platform policy — this section adds no bespoke value, closing errata E1's gap by adoption); idempotency (single-use selection; step 2 is side-effect-free so a member retry after `provider_failure` is safe and never silent); malformed-output (validator, fixed-literal errors, content-free logging); prohibited-action (output can trigger no save, publish, send, delete, or record mutation — there is no code path from nudge output to any write procedure). |
| **Failure behaviour** | `no_history_match` (step 1, success-shaped — 3.5); `unavailable_source` (revoked/deleted/changed/expired selection; History store unreachable — manual answering always remains); `insufficient_evidence` (text-free record selected); `denied_authorization` (entitlement/capability off); `rate_limited`; `provider_failure` / `invalid_output` (step 2 only — draft and selection context preserved, truthful copy, manual retry offered, generic planning help offered). Member work is never cleared by any of these. |
| **Evaluation slice** | Retrieval (provider-free): fixed synthetic-member corpus with graded relevance; report precision@5, paraphrase-recall cases, and ranking-order cases. Provider: golden grounded-nudge cases (useful hooks tied to the actual prior answer), stale-answer caution cases, adversarial cases (prior answer containing embedded instructions; injected role context), schema-failure cases. Negatives: cross-member key, forged/expired/consumed selection, excluded record, deleted record, empty-answer selection. Thresholds are chosen with evidence in the implementation package, per the accepted direction — none are invented here. |
| **Version identity** | `history-nudge@1.0.0+<prompt-sha8>` for the provider step; the deterministic retrieval carries the migration's procedure definition-hash fingerprints (house mechanism) as its version identity, so a ranking change is a visible, versioned event. |

### 3.5 No-match behavior (accepted wording, made concrete)

When step 1 finds nothing useful:

```json
{
  "status": "no_history_match",
  "candidates": [],
  "no_match_prompt": {
    "ask": "Nothing similar is in your practice History yet. Do you have an experience, example, or detail in mind you'd like to add for this answer?",
    "options": ["add_detail", "manual_search", "generic_help", "skip"]
  }
}
```

- **`add_detail`** — the member types a detail; it becomes `confirmed_context` (provenance `member_typed_current_practice`, authorization state `member_confirmed_current_practice`), bounded at 2,000 UTF-16 units, held client-side for the current practice activity, transmitted only with subsequent explicit AI requests, and **never silently promoted** to History, Profile, Journal, or canonical truth — saving it is a separate previewed action.
- **`manual_search`** — opens member History search (2.5) — a member tool, not an AI grant.
- **`generic_help`** — invokes the existing generic hint path (3.6).
- **`skip`** — returns to the answer, no state recorded, no score, no nagging.

`no_history_match` is a truthful search outcome, not an error: orchestration (Section 5) must not retry it, and telemetry counts it separately from failures.

### 3.6 The existing generic nudge is kept, truthfully relabelled

`POST /api/interview/nudge` (`app.py:4113-4200`) remains exactly what it is — generic planning hints with **no** History access, its prompt's history prohibition now load-bearing rather than ironic — and becomes specialist 4's `generic_help` fallback with its own version identity (`nudge-generic@1.0.0+<prompt-sha8>`) under Section 1's versioning scheme. It is also the AI-unavailable degradation for the grounded path. The endpoint list therefore stops implying that a History nudge exists when it does not (diagnosis 11.2): the UI labels the two paths distinctly ("From your History" vs "General planning help").

---

## 4. Part C — Browser-History migration

### 4.1 Owner direction, restated as invariants

Optional. Previewed. Explicitly member-confirmed, record by record. **Never silently uploaded.** The member-scoped `:v3` namespace is the only migration source; anonymous `v1`/`v2` records are never read, adopted, imported, or deleted by any part of this flow (owner decision Q-B, already enforced in the client at `interview-studio.js:352-366`, and the accepted rule that guest History is never silently imported after sign-in). Honesty note, stated because the server cannot verify a browser's storage: the namespace restriction and the "read only what the member checked" rule are client-code controls with JS test coverage — the server-side control is that import accepts only the explicit record payloads the member confirmed in the preview, and re-validates every one.

### 4.2 Preview

From the History view: "Move this browser's practice History to your account." The client reads records through the existing non-destructive sanitizing boundary (`readHistoryRecords()`, `:1971` — malformed entries are skipped, never destroyed), and renders a preview list: per-record checkbox (default checked), question, date, mode, review state, and an "already in your account" marker computed by asking the server (`POST /api/interview/history/import/preview` with `[{client_record_id, fingerprint}]` — a metadata-only dry run, no content transmitted). Nothing uploads until the member presses the single explicit confirm ("Move N selected records to my account").

### 4.3 The cap truth (100-record silent eviction, told plainly)

The preview always states, before confirmation: **"This browser kept at most your 100 most recent practice records. If you practiced more than that, older records were removed automatically before today and cannot be recovered — moving History to your account cannot bring them back, but it does stop that limit from applying to new practice."** Shown unconditionally (the client cannot know whether eviction ever occurred — `records.slice(0, 100)` at `:1983` leaves no trace, so the truthful statement is about the limit, not a claimed count). Account History carries **no silent cap**: no record is ever evicted without member action; if an abuse quota is ever needed it must refuse loudly at save time, never delete quietly.

### 4.4 Import: idempotent, per-record, recoverable

`POST /api/interview/history/import` (`limiter: 4 per minute`), batches of ≤20 records, body `{"import_batch_key":"<client UUID>","records":[<sanitized record shapes>]}`. Server behavior, all inside owner-scoped procedures:

- **Re-sanitize everything.** The server applies its own mirror of the sanitizer bounds (question ≤1,200, answer ≤5,000, enum coercion, date validity) — client sanitization is convenience, never trust. Failures are per-record `rejected_invalid`, never batch-fatal.
- **Idempotency, two layers.** `dbo.interview_history_import_batches` records `(owner_profile_id, import_batch_key)` uniquely, so a retried batch cannot double-import; per record, the filtered unique index on `(owner_profile_id, client_record_id)` plus `import_fingerprint` (server-computed SHA-256 over canonicalized question|answer|createdAt) decides: same id + same fingerprint → `duplicate_skipped`; same id + different fingerprint → imported as a **new** record with `client_record_id = NULL`, result `imported_as_copy` (append-only truth: nothing on the server is ever overwritten by an import).
- **Provenance kept.** `record_provenance = 'browser_import'`, original `createdAt` preserved as `created_at_utc`, `saved_at_utc` = now, `review_generation` mapped from the record's `reviewVersion` (`v2` review artifacts populate the review tables; `legacy-v1` and `local-recording` records import with empty review children, labelled honestly in the UI as "reviewed under an older format" / "local recording"). The browser record's local `context` object — whose full shape Gate A left partially unverified — is preserved as the opaque, member-visible, never-AI-eligible `imported_context_json` snapshot rather than half-interpreted.
- **Per-record results returned**: `imported | duplicate_skipped | imported_as_copy | rejected_invalid`, each with the `client_record_id` it answers, so the client can render a truthful outcome list. A dropped connection mid-batch is recovered by resending the identical batch: results are identical, nothing duplicates.

### 4.5 The browser copy afterwards

**Never deleted automatically.** After a batch completes, the member is offered — not forced — "Remove the moved records from this browser," which deletes only records the server confirmed `imported` or `duplicate_skipped`, via the existing `removeHistoryRecord()` path. Declining keeps both copies, and the local list labels them "Saved to your account." Implementation note recorded now because it will otherwise bite: `sanitizeHistoryRecord` (`:1908`) rebuilds records to a fixed shape and drops unknown fields, so the local marker (`accountRecordKey`) must be added to the sanitizer's preserved field set or it is silently destroyed on the next read. The existing bulk local clear (`:5140`) is untouched and continues to say, correctly, that it clears **this browser**.

After migration, with `saving_mode = 'save_to_account'`, new practice saves to the account and the local `:v3` namespace stops accumulating; a member on `session_only` keeps working browser-locally exactly as today. The History view labels the two populations distinctly ("In your account" / "On this browser only") — one authoritative source per fact, visibly.

---

## 5. Part D — Role Context consumption

### 5.1 What is fixed and not redesigned here

`PS-INTERVIEW-ROLE-CONTEXT-001` is existing accepted authority. This section changes none of it: intake by paste, upload, public link, or explicit transfer of an exact authorized Opportunity Slate source/version; reuse of the hardened Opportunity Slate acquisition boundary (no second fetcher or parser, ever); all external text untrusted content, never instructions; member review and explicit confirmation of the captured source before use; direct intake creating **private** role context only — never publishing, never creating an Opportunity Slate, never creating canonical member evidence; version pinning; deleted-source tombstone minimalism; O*NET as future attributed, versioned, offline occupational knowledge — never an online dependency, employer truth, or member evidence. Its four open pre-implementation decisions (retention period, post-session source retention shape, visual locks, size/cost ceilings) remain with that package.

### 5.2 What Interview AI consumes — the `role_context` source class

The staged pipeline the continuation fixes — (1) deterministic fetch/decode/extraction → (2) truthful extraction status → (3) labelled AI interpretation proposal → (4) member review/correction → (5) explicit use as current private Role Context — has exactly one stage visible to Interview AI specialists: **stage 5's output**. Specialists never receive raw stage-1 bytes, unreviewed stage-3 proposals, or a mid-correction draft. The consumed shape:

```json
{
  "source_class": "role_context",
  "role_context_key": "<opaque UUID>",
  "source_version": 3,                              // pinned; a later revision makes question sets visibly older, never silently different
  "origin": "pasted | uploaded | linked | slate_transfer | described",
  "confirmed_role_label": "<=160 units",
  "confirmed_employer_label": "<=160 units",
  "confirmed_text": "<=4,000 UTF-16 units of member-confirmed source wording",
  "confirmed_at_utc": "…",
  "provenance": "member_confirmed_role_context@v3",
  "authorization_state": "member_confirmed_current"
}
```

Deterministic consumption controls: identity server-derived; authorization before retrieval via an owner-scoped read procedure against the Role Context store (an opaque reference is resolved and authorized server-side — a browser-supplied key is never proof of ownership, exactly as that contract already states for Slate transfer); version pinned into every knowledge manifest; `confirmed_text` enters prompts only through Section 1's shared untrusted-content envelope — noting errata E2 honestly: the envelope is a partial, non-deterministic injection mitigation, and the deterministic strengthening of that boundary is Section 1's charter, which this section adopts rather than duplicates. Member correction wins over AI interpretation: corrected fields carry `member_corrected` provenance and outrank the proposal they replaced; conflicts between role context and member statements are surfaced, never silently resolved by the AI.

### 5.3 The interim truth, stated so no one designs against a fiction

Role Context **does not exist in the runtime today** (diagnosis §7: "Direction recorded, not implemented"). Until its own Protected package ships, the only role-context-like input is the live `opportunity_context` field — client-supplied, bounded to 4,000 units, base64-enveloped, untrusted (`app.py:3356` idiom). This design maps that interim input onto the same source class with downgraded states — `provenance: "client_supplied_unconfirmed"`, `authorization_state: "unconfirmed_untrusted"` — so specialists, manifests, and telemetry use one vocabulary across both eras, and the upgrade to confirmed server-held Role Context is a provenance change, not a redesign. History records save `role_label`/`employer_label` (member-visible practice metadata owned by the History record) plus the pinned `role_context_key`/version; if the underlying source is later deleted or permission is lost, the labels survive truthfully ("practiced for: Product Manager — Contoso") while de-referencing the key fails closed as `unavailable_source` — the tombstone-minimum rule applied from the consuming side.

### 5.4 Who receives it

Per the accepted specialist map: the Diagnostician receives bounded Role Context; the Answer Coach and Revision Partner receive it only per their manifests; the History Nudge's step-1 ranking may use the **labels** as filter boosts but step 2 sends only the current question, selection content, and (when the member's current practice carries it) the bounded confirmed text. No specialist receives it "because it exists" — the source-allowlist guardian rejects unmanifested classes. Interview AI never mutates Role Context: consumption is read-only, and nothing here can save, publish, or transfer a source.

### 5.5 The Role-Context-bound Question Generator stays future

Accepted as a future specialist only. It is **not in the first implementation sequence**, gets no schema, prompt, endpoint, or evaluation slice here, and when it arrives it binds to the question-generation contract PS-INTERVIEW-ROLE-CONTEXT-001 §"Question-generation contract" already fixed (exact context-version binding, source-span references, no employer-intent inference, no fit scoring, generic fallback preserved). Nothing in Sections 3's schemas blocks it: `role_context_key` + `source_version` on History records is precisely the pinning it will need.

---

## 6. Privacy-claim-to-deterministic-control matrix

Every privacy claim this section makes, with the server-side control that enforces it. No claim below rests on prompt wording.

| # | Claim | Deterministic server-side control |
|---|---|---|
| 1 | Only the member's own History is ever searched or returned | Identity derived server-side (`_interview_api_authenticated_identity()` first action); every procedure is `ForOwner`, resolves `@UserKey` itself, predicates every statement on `owner_profile_id`; request schemas carry no owner field; allowlist (`ALLOWED_PROCEDURES`) forbids any other path to the tables |
| 2 | Step 1 discloses bounded metadata + excerpt only | Candidate procedure's result set structurally excludes content columns; excerpt precomputed ≤280 units at write time; set-equality row check makes a widened result set a loud runtime failure (P4) |
| 3 | Full prior content reaches the AI only after member selection | Single-use, expiring, purpose-bound selection row minted by an explicit member POST; provider call site accepts `history_selection` content only from `usp_ConsumeInterviewHistorySelectionForOwner`; request schemas reject content-bearing fields, so the browser cannot inject "prior answers" |
| 4 | Authorization precedes retrieval and is rechecked on authoritative records | Owner predicate inside every procedure (before rows exist to return); consumption re-reads the authoritative record and requires active/eligible/version-current after the projection hit |
| 5 | Deleting a record removes it from every index, cache, and AI eligibility | One deleting transaction; enabled+trusted `ON DELETE CASCADE` to versions, reviews, projection, selections; no external index, embedding, or server content cache exists in round one; proven by P1–P4, not asserted |
| 6 | Excluding a record from AI is immediate and complete | Same-transaction update of authoritative + projection rows and deletion of unconsumed selections; candidate predicate and consumption re-check both read `ai_eligibility` |
| 7 | A record ID or search hit is not access authority | Keys are opaque UUIDs; owner-predicated lookups make foreign keys indistinguishable from nonexistent ones (uniform not-found); selection adds purpose, version, expiry, single-use on top |
| 8 | Nothing saves silently | Save procedure refuses without an explicit save action or `save_to_account` mode + recorded disclosure acknowledgement; `session_only` change touches only the settings row (existing records untouched) |
| 9 | Browser History is never silently imported | No server code path reads browser storage; import accepts only member-confirmed explicit record payloads with a client-generated batch key; anonymous-namespace exclusion additionally enforced in client code (labelled honestly as a client-side control) with JS tests |
| 10 | Cross-member, forged, stale, expired references fail closed | Owner predicates; version pinning on selections; expiry + single-use; uniform not-found responses; contract-test negatives (P3) |
| 11 | Routine telemetry stays content-free | New endpoints log via the `_log_interview_failure` idiom (reason code, class name, stop reason, counts); unexpected-exception handlers log `type(error).__name__` only — closing errata E3/G7's `%s` hole for every endpoint this section introduces, from birth |
| 12 | No Journal, no open web, no O*NET at runtime | No fetcher, join, or procedure touching those sources exists in any path here; the manifest builder's source-allowlist rejects unmanifested classes; O*NET remains future attributed versioned offline knowledge per the Role Context authority |
| 13 | AI output causes no side effects | No code path from any specialist response to a write procedure; saving a nudge, review, or revision is a separate member action on a separate endpoint (prohibited-action guardian is an absence of code, verified by test) |

---

## 7. Failure states used in this section (shared spine, no variants)

`provider_failure` (step-2/generic provider errors; draft and selection context preserved; manual retry) · `invalid_output` (validator rejection; content-free log) · `no_history_match` (truthful step-1 outcome; triggers the four-option ask; never retried automatically) · `insufficient_evidence` (text-free record selected; grounded example insufficiency remains Section 4's use) · `denied_authorization` (entitlement/capability/saving-mode refusals) · `unavailable_source` (deleted/revoked/changed/expired selection; unreachable History store; dangling role-context reference — manual answering and generic help always remain) · `rate_limited` (limiter refusals, truthful copy). Every state preserves member work; none fabricates success; each maps to distinct, stable, content-free telemetry reasons.

---

## 8. Evaluation slices owned by this section

Composition only — launch thresholds are selected with evidence in the implementation package, per the accepted direction.

1. **Retrieval slice (provider-free, runs in CI):** synthetic member corpora (no production data); graded-relevance cases for exact overlap, family/competency boost, paraphrase misses (documenting the known lexical limit), recency tiebreaks; precision@5 and no-match honesty reported per run; procedure-fingerprint version recorded with every result.
2. **Boundary slice (provider-free):** the P3 negatives — cross-member, forged/expired/consumed selection, excluded, deleted, empty-answer, uniform not-found shape, import idempotency, closed-schema rejections, result-set shape enforcement.
3. **Grounded-nudge provider slice:** golden cases (hooks genuinely tied to the prior answer's content), stale-answer caution cases, adversarial prior answers and role context carrying embedded instructions (injection-separation), schema failures, provider failures.
4. **Migration slice:** preview truthfulness (cap statement always present), per-record results, duplicate/copy/invalid handling, batch retry identity, browser-copy preservation, sanitizer round-trip of the `accountRecordKey` marker.

---

## 9. Implementation sequencing note

For the consolidated sequence (Section 5's charter), the dependency order inside this section is fixed: **(1)** `PS-INTERVIEW-HISTORY-001` migration + settings + save/list/detail/correct/archive/exclude/delete/clear + verifiers, behind a default-off `PEERSLATE_INTERVIEW_HISTORY_ACCOUNT` flag; **(2)** member search; **(3)** nudge candidates + selections + grounded nudge; **(4)** browser import. Role Context consumption activates only when PS-INTERVIEW-ROLE-CONTEXT-001's own runtime package ships; nothing in (1)–(4) waits on it. Every step is Protected (identity, privacy, deletion, consequential AI) with the negative/rollback evidence its trigger requires.

## 10. Honest uncertainty

- The canonical FK target for `owner_profile_id` and the exact closed family enum are pinned at implementation from the applied PS-PLAT migrations and `_normalize_interview_family` respectively — stated by idiom here, not read end-to-end.
- The browser record's `context` object shape and any in-browser answer-version structure remain partially unverified (Gate A §8/§Not-verified item 2); import therefore preserves context opaquely and maps the single current answer only.
- The production Azure SQL PITR retention window is unread configuration; the deletion-honesty copy ships with the verified number, not this document's placeholder.
- Real per-member record volumes and search latency are unmeasured until the authenticated evidence batch and live telemetry exist; the retrieval-upgrade conditions (2.5) are written to be decided by those measurements, not by taste.

## 11. Assumptions this section imposes on, or takes from, the other sections

1. **Section 1 (Constitution/platform)** owns the single provider call site, the knowledge-manifest builder, the untrusted-content envelope and its deterministic strengthening (E2), the deliberate timeout/retry policy (E1), and version identity — this section's evidence-entitlement rule (selection row → `history_selection` manifest entry) must be enforced *there*, at the call site, or the two-step boundary has a bypass.
2. **Section 2 (Coach/Revision)**: the Answer Coach gets **no History access** — its "small authorized evidence-discovery projection" is `member_evidence`, a different class that is empty for non-owners today (G2). Prior answers are preparation material and never become `member_evidence`; any Section 2 assumption of History-informed coaching conflicts with the accepted map and this design.
3. **Section 4 (Examples)**: `insufficient_evidence` stays the Grounded Example's state for missing `member_evidence`; the nudge's `no_history_match` is distinct and must not be collapsed into it.
4. **Section 5 (Orchestration/evaluation)**: `no_history_match` is success-shaped (never auto-retried); the generic nudge endpoint survives as `generic_help` rather than being replaced; the selection TTL (15 minutes) and single-use rule constrain any workflow resumption design.
5. `confirmed_context` (the add-detail path) is client-held current-practice material in round one — if another section assumed all source classes are server-persisted, that conflicts and this section's definition governs the class.
