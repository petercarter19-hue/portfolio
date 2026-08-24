# 16 — End-to-end traceability matrix

Every approved product state and every required functional/failure scenario,
mapped to backing data (docs 02–03), API contract (docs 04/09), authorization
(doc 08), UI behavior (doc 10), test obligation, owning child (doc 14), and
proof level.

**Proof levels** (kept strictly separate; no level ever claims a higher one):

- **P-1 component/fixture** — deterministic fixtures, unit/contract/browser
  tests, negative multi-member tests.
- **P-2 disposable infrastructure** — throwaway SQL/index/job proofs with
  exact-target cleanup.
- **P-3 candidate application** — the integrated application exercised on the
  candidate path.
- **P-4 deployed release** — dark or enabled behavior verified in the
  deployed environment, stated separately from merge.
- **P-5 licensed live data** — only after Pete's licensed-feed decision;
  the only level that may make live-inventory claims.

## 1. Product states — fifteen approved visuals plus the required mobile fully-verified functional state

| State | Backing data | API/authorization | UI + tests | Child / proof |
|---|---|---|---|---|
| Fully verified selected (desktop base) | `result_snapshot` entry (gate `fully_verified`) + `requirement_version` + `assessment[Verified]*n` | results read, owner-scoped | Dossier + anchors + rail; near-black title; copy truth `Review in Opportunity Slate`; parity + copy assertion | C8 / P-1→P-3 |
| Fully verified selected (mobile 390×844) — **required functional contract; approved visual artifact pending** | identical backing to the desktop base: `result_snapshot` entry (gate `fully_verified`) + `requirement_version` + `assessment[Verified]*n` | identical results/assessment reads, owner-scoped | Single-column reflow per doc 10 §2: gate status, complete dossier + anchors, actions (Save, `Review in Opportunity Slate`, View original posting); failure/fallback behavior identical to the desktop contracts (docs 03/04/09). Functional browser test at 390×844 asserting complete content, truthful gate copy, working actions, and no horizontal overflow. Visual composition remains quarantined for Original ChatGPT + Pete (doc 10 §6); the quarantine does **not** waive or defer this functional row | C8 / P-1→P-3 (functional); visual parity gated on the Pete-locked artifact |
| No fully verified results (desktop) | snapshot with empty qualified set + separated broader set; criteria snapshot preserved | results read | Two-column explanation; standards unchanged; broader set labeled; two-row reference geometry | C8 / P-1 |
| Qualified selected (iPad 1024×768) | same as desktop base | same | Contained two-pane; no third row; geometry per Pete's corrected artifact (quarantine) | C8 / P-1 |
| Selected not fully verified (mobile, `5 of 6 required verified · 1 not established`) | assessments incl. `Not established(no_evidence_in_scope)` | results + assessment read | Explicit gate label; per-item reason; no-negative-inference copy | C8 / P-1 |
| No fully verified results (mobile) | as desktop empty | same | Constructive explanation; separated broader set | C8 / P-1 |
| Saved list (mobile) | `saved_opportunity` rows + lifecycle overlays | saved read (owner-scoped) | Mixed verification + lifecycle states visible; local search/filter (doc 03 §7) | C6+C8 / P-1 |
| Save confirmation (mobile) | save write + undo window | save/remove/undo mutations, idempotent | `Saved for later`; Undo; never opens a Slate; live-region announce | C6+C8 / P-1 |
| Opportunity Slate first-use confirmation (mobile) | `slate_link` create path | doc 11 §4 command, explicit confirm | Dialog semantics; private-workspace explanation; cancel creates nothing | C7+C8 / P-1→P-3 |
| Posting changed (mobile) | new `source_version` (a new `requirement_version` only on material normalized-clause difference, doc 03 §10); listing `changed`; member context per REC-03 | results/saved reads | What-changed rendering old vs new; history preserved; member review clears (that member only); a non-requirement change shows truthful what-changed without assessment churn | C2+C6+C8 / P-1 |
| Closed by source (mobile) | listing `closed` (source-confirmed) | reads | Removed from current; saved/Slate history preserved; alternatives offered | C2+C6+C8 / P-1 |
| Could not reverify (mobile) | listing `unreachable`; `last_attempted_at` ≠ `last_successfully_verified_at` | reads | **REC-07 binding**: show last *successful* check age; failed attempt separately; not closure; prior data labeled historical | C2+C8 / P-1 |
| Searching/loading (mobile) | `search_execution` stages | status polling | Meaningful stages; **loading copy bound to accepted topology** (index wording vs live-check wording — fixed at C4, asserted by copy test); no invented counts | C3+C4+C8 / P-1 |
| Reduced coverage (mobile) | execution `coverage=reduced` + named checks; affected assessments `Review unavailable` | results + disclosures | Available results + precise limitation; unavailable ≠ failure | C4+C5+C8 / P-1 |
| Evidence-authorization boundary (mobile) | `evidence_grant` absent/insufficient → `Not established(no_evidence_in_scope)` | grant create/inspect; assessment read | Explicit consent boundary; "does not mean you lack the experience"; grant flow correctable | C5+C8 / P-1 |
| AI clarification sheet (mobile) | `criteria_draft` + clarification (pre- or post-result) | interpret response | Dialog semantics; nothing preselected; Apply disabled until choice; **current results unchanged**; `Keep current criteria` discards draft | C3+C8 / P-1 |

Known visual coverage gaps (mobile fully-verified dossier; non-mobile
adaptations of mobile-only states) are carried in doc 10 §6 — closed via
Original ChatGPT + Pete before C8 claims those states.

## 2. Required functional scenarios

| Scenario | Contract | Backing | Test obligation | Child / proof |
|---|---|---|---|---|
| Fresh search (no restored state) | doc 04 §6 | no persisted applied state loaded | browser + contract test | C3 / P-1 |
| Visible interpretation, explicit Apply | doc 03 §3, 04 §§1–2 | draft → snapshot chain | contract + browser; "first submit never executes unseen interpretation" | C3 / P-1 |
| Pre-search clarification | doc 03 §3 | clarification on draft | nothing preselected; Apply fenced | C3 / P-1 |
| Post-result clarification, results unchanged | doc 03 §3 | new draft beside live snapshot | assert applied snapshot + rendered results byte-stable until new Apply | C3+C8 / P-1 |
| Edit/apply criteria; direct filters; parity | doc 04 §§1–1a | `create_draft`/`edit_draft` commands, live token rotation, terminal receipts, manual provenance | AI-off parity suite: every criterion settable manually through the §1a commands; the complete §1a precedence table proven — original-receipt replay (a), `idempotency_mismatch` (b), `terminal_draft` with receipt (c), `stale_draft` with live state (d), no mutation on refusal (e); interpret canonical-input identity (same text, different snapshot ⇒ no collision) | C3 / P-1 |
| Saved-view search/filter | doc 03 §7 | member-side query | owner-scoped filter tests incl. cross-member negative | C6 / P-1 |
| AI unavailable | doc 04 §9 | `manual_required` | full manual journey green with AI stubbed down | C3 / P-1 |
| Index unavailable | doc 04 §9 | degraded path / truthful failure | both branches tested | C4 / P-1→P-2 |
| Pagination/restoration | doc 04 §§3,5,6 | snapshot cursors | cursor stability on snapshot; restoration renders with age | C4 / P-1 |
| Partial execution and results | doc 04 §11 | completeness-marked immutable partial snapshot; reason enum; cursors; retry-as-new-Apply | timeout/provider-failure/index-failure/budget cases each produce an immutable partial snapshot containing only fully evaluated entries; "at least N" count truth; retry never mutates; idempotency returns the same partial outcome | C4 / P-1 |
| Interrupted search | doc 03 §4 | TTL abandonment | abandoned executions leave no restorable snapshot (distinct from §11 partial terminations) | C4 / P-1 |
| Sign-in return round trip for `/my-opportunities` | doc 01 §2; doc 14 C8 | `ProtectedDestination("/my-opportunities", "PEERSLATE_MY_OPPORTUNITIES_ENABLED")` (proposed key) in `safe_return.PROTECTED_DESTINATIONS`; the same prefix-and-flag contract bound in both browser allowlists (`static/js/auth-state.js`, `static/js/easy-auth-callback.js`) | round trip through the real endpoints per the `tests/test_signin_member_arrival.py` structural pattern; an unregistered destination fails a test, not a member journey; flag-off means the destination is not a valid return target | C8 / P-1 |
| Two-destination navigation (My Opportunities beside Opportunity Slate) | doc 14 C8; `templates/base.html` | flag-aware shared-shell navigation entry | `tests/test_navigation.py` parity: both accepted Opportunities destinations discoverable when their flags are on; no new destination beyond the accepted two; bounded `base.html` change only | C8 / P-1 |
| Long/missing fields | doc 09 §5 | bounded intake/render | fixture extremes; `Not stated` truth | C2+C8 / P-1 |
| Empty / one / many results | doc 04 §3 | snapshot entries 0/1/n | fixture matrix incl. real counts | C4 / P-1 |
| Stale results | doc 04 §8 | snapshot age + lifecycle overlays | age disclosure; overlay correctness | C6+C8 / P-1 |
| Duplicate results / duplicate correction | doc 03 §9, 05 §4 | merge/split tombstones | member keys stable through merge + reversal | C2 / P-1 |
| Stale criteria snapshot | doc 04 §2 | `409 stale_draft` | stale-token refusal renders current state | C3 / P-1 |
| Save failure / removal / undo | doc 03 §7, 09 §4 | idempotent mutations | failure keeps truthful state; undo window; unknown-outcome lockout | C6 / P-1 |
| Existing Slate continuation | doc 03 §8, 11 §4 | `continue_slate` | never a second create; unlink history label | C7 / P-1→P-3 |
| Revoked evidence | doc 03 §5, 07 §5 | grant revocation recompute | `Verified → Not established(evidence_revoked)`; history not rewritten | C5 / P-1 |
| Posting changed / confirmed closure / temporary reverify failure | doc 03 §§1–2 | lifecycle states | three-way distinction tests (never conflated) | C2 / P-1 |
| Governing-source failover (multi-source) | doc 03 §§9.3–9.6 | governing selection, aggregate eligibility, failover, requirement-version comparison | governing head closes/loses rights/goes unreachable while another eligible head exists → opportunity stays eligible; posting-changed/source-history truth rendered for the governing change either way; equivalent clauses retain the `requirement_version` (no assessment churn); materially different clauses create a new version with re-evaluation; member history unchanged; field-level attribution and "sources differ" rendering asserted | C2 / P-1 |
| Application-link validity lifecycle | doc 05 §§5–6; docs 02 §1, 03 §1 | persisted `application_link_state` (valid \| invalid \| unknown) with attempt/validation timestamps and reason enum; safe-outbound validator | `valid → invalid` on failed validation (each reason enum case); `invalid → valid` recovery restores gate eligibility with no lifecycle event; `unknown`/out-of-window fails gate condition 6; Live Opportunity Gate excludes the head while the listing stays `current`; link invalidity never renders as closure or outage; outbound adversarial matrix (DNS rebinding, private/link-local/metadata denial, redirect chains, timeout, no credential forwarding) | C2 / P-1 |
| Result-time basis restoration | doc 04 §§3, 8; doc 02 `result_snapshot` | bound `governing_source_version_key` + `display_attribution_refs` per entry | restoration renders every entry from its bound result-time references; a later non-requirement source change never rewrites a restored result; content since removed under rights renders as unavailable — never substituted with newer facts; cursor and ordering identity remain byte-stable across restorations | C4 (snapshot/restoration) + C2 (version/rights basis) / P-1 |
| Assessment persistence failure | doc 08 §2a; doc 04 §11; doc 07 §4 | durable-row backing rule; `partial(assessment_persistence_failure)` | a durable `Review unavailable` row is written whenever computation fails but persistence works, and only then may the entry appear; when assessment-row persistence itself fails the entry is excluded and the execution terminates `partial(assessment_persistence_failure)`; no per-item state ever appears in a snapshot without its backing row | C5 (assessment writer) + C4 (execution/result boundary) / P-1 |
| Reduced coverage | doc 04 §9 | named unavailable checks | no silent upgrade of incomplete evidence | C4+C5 / P-1 |
| Authorization denial | doc 08, 09 §4 | identity gates | signed-out redirect; 503 ≠ signed out; cross-owner not-found | every runtime child / P-1 |

## 3. Untrusted-import and company-context scenarios (doc 06)

| Scenario | Test obligation | Child / proof |
|---|---|---|
| Unsupported/malformed URLs (scheme, userinfo, garbage) | refusal enum per case | C1 policy → C13 (`PS-MYOPP-URL-FETCH-001`) gate tests when Pete enables fetching / P-1 |
| DNS/address changes (rebinding: resolve-then-swap) | per-connection revalidation proof | same / P-1 |
| Redirect chains (incl. into denied space; >3 hops) | every hop revalidated; budget refusal | same / P-1 |
| Private-network and metadata targets (all §1 families incl. mapped-IPv6) | deny-set matrix | same / P-1 |
| Oversized / mislabeled content | streaming cutoff; sniff-mismatch refusal | C10 (upload path unconditional); fetch cases in C13 / P-1 |
| Parsing failure / parser bombs | named failure states; no fabricated text | C10 / P-1 |
| Sanitized source display | sanitizer output only; canary injection never renders | C10 + C8 / P-1 |
| Company context absent / stale / contradictory | truthful empty; `as_of` age; both-or-neither rendering | C1 policy; C12 runtime; C8 absent-state UI / P-1 |
| Direct/manual path when import or company context unavailable | paste/upload path green (C10); opportunity fully usable without company context (C8 absent state) | C10 + C8 / P-1 |
| URL import unavailable (flag off, adapter absent, or C13 never activated) | C10's **service-level** port answers the truthful `url_fetch_unavailable` outcome; C8's route `POST /my-opportunities/import/url` (existing from C8 onward) surfaces it with paste/upload offered inline, and C8 renders the URL affordance only when both `PEERSLATE_MY_OPPORTUNITIES_ENABLED` and `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` are true (no dead chrome); configuration-only disable restores the refusal (C13 rollback) | C10 (service port) + C8 (route/UI); C13 (enable/rollback proof) / P-1 |

## 4. Cross-cutting truth bindings

- **`Last checked` semantics** (REC-07): UI may not render a single ambiguous
  timestamp; copy binds to `last_successfully_verified_at` (with age) and
  failed attempts render separately. Contract test: fixture with
  `attempted today / succeeded 6 days ago` must render both truths.
- **Retrieval/loading language**: copy selected by the accepted topology at
  C4; a copy-level contract test asserts indexed retrieval never renders
  query-time employer-source-check wording (and vice versa).
- **Alias table** (doc 07 §4): every UI qualification string maps to exactly
  one canonical state; a test enumerates rendered strings against the closed
  map — an unmapped string fails.
- **No-score rule**: serialization tests assert no score/probability/
  percentage/prediction field ever reaches the browser payload.
- **Fixture labeling**: every fixture-backed render carries the fixture
  label; a test asserts the label at each approved state.

## 5. Proof-level separation (release truth)

| Claim allowed | Requires |
|---|---|
| "Contracts and states work" | P-1 green across §§1–4 rows |
| "Pipeline/index/jobs operate" | P-2 with exact-target cleanup evidence |
| "The application does this end-to-end" | P-3 on the exact candidate SHA |
| "It behaves this way in production (dark or enabled)" | P-4, stated separately from merge; enablement separately again |
| "Live opportunities / live inventory / live verification" | P-5 only, after Pete's licensed-feed decision — never before |

No row in this matrix authorizes skipping a level, and no fixture or dark
result may be described with P-5 language anywhere in the program.
