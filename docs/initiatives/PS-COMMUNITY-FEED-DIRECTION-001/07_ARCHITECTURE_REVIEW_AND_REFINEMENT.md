# Community Feed architecture review and refinement record

## 1. Status and verdict

- **Review date:** 2026-07-31
- **Pre-review branch tip:**
  `5be3b817aa03a33a4157cea4e9291c6a9224b2f7`
- **Scope:** documents 04 through 06, the six Pete-locked screens, current
  shared authority, and current repository integration seams
- **Runtime files changed:** none
- **Current verdict:** architecture review-complete; runtime entry
  **blocked**
- **Owner acceptance:** Pass, Pete, 2026-07-31, against
  `aa69c5ec87ddddf6a408726f8944e3daff9d4fef`
- **Reason:** the technical shape is now explicit;
  `PS-COMMUNITY-FEED-AUTHORITY-001` resolves the narrow constitutional/Journal
  boundary, while complete visual states, exact audience/mode decisions, and a
  runtime package remain unresolved

This review originally ran against the detailed v2.9/v2.8 control model. The
2026-07-31 lean v3 control plane later superseded those shared documents and
removed the global checkpoint premise. The architecture findings remain valid;
the gate conclusion below is reconciled to Constitution v3.0, Roadmap v3.0,
the lean site rules, and the scoped holds in `CURRENT_BASELINE.yaml`.

The initial architecture had the right core: one canonical conversation,
authorization before projection, a finite Feed, one post-local horizontal row,
selected/full conversation separation, rail truth, Spark, safe attachment
intent, accessibility, and deferred messaging. It was not yet safe to build
because several visible controls and cross-surface trust behaviors were left
implicit.

This record preserves the review/refine/review discipline. It does not convert
an architecture review into runtime authority.

## 2. Review method

The first pass used three independent read-only lenses:

1. **Visual-contract audit** — compared the architecture with all six exact
   Pete-locked images and the lock manifest.
2. **Trust/data audit** — checked identity, audience, provenance, lifecycle,
   moderation, files, idempotency, caching, and deletion/revocation behavior.
3. **Repository-integration audit** — inspected the current Flask routes,
   template/JavaScript seams, database procedure boundary, SQL foundation,
   fixture/prototype history, and then-current governance checkpoint.

The manager then performed a complete-diff refinement and routes the result
through a fresh second-pass review. The second pass must inspect the refined
text rather than merely restating the original findings.

## 3. First-pass screen comparison

| Locked state | What was already sound | Gap found in the original architecture | Refinement in document 04 |
| --- | --- | --- | --- |
| Desktop Feed | Finite vertical Feed, left/right rail roles, Spark, one-row shelf, caught-up | Main Feed media was incorrectly described as compact; Search/New post/member shell and exact actions were not contracted | Adds full Feed media versus compact Motion cues, shell/search gate, action matrix, Pulse/Question derivation, and caught-up destinations |
| Desktop selected contribution | Modal, authorization, full attachment, focus restoration | Missing explicit parent context, parent chain, revision/save/action payload, reply composer, and transition to full thread | Adds `SelectedContribution` shape, contribution composer, capability payload, non-stacked transition, and history restoration |
| Desktop full conversation | One canonical vertical conversation, nesting, pagination, full media | Missing root/header label derivation, selected/unread anchor, per-entry action/save state, revision truth, and sticky-composer contract | Adds complete conversation read model, deterministic label, parent keys, current revisions, anchors, and composer target |
| Mobile Feed | Real one-column reflow, compact shelf density, no rails | Missing exact breakpoint/shell evidence, mobile View all semantic label, search/new-post actions, and Catch up count semantics | Requires per-file comparison matrix, locked compact label with full accessible name, shared composer action, and immutable catch-up snapshot |
| Mobile Catch up/Spark | Correct reflow of return context and Spark, no Break | Missing modal-sheet behavior, seen acknowledgement, CTA targets, partial failures, and Pulse/Questions disposition | Adds bottom-sheet accessibility/restoration, seen rules, exact action targets, module states, and an explicit mobile visual gate |
| Mobile selected contribution | Full-screen detail, Back behavior, full attachment, View all | Missing original-context expansion, target-specific synchronized Save, overflow actions, contribution composer, and safe-area behavior | Adds parent/original context, typed capabilities, save synchronization, contribution composer, and full-screen/safe-area evidence requirements |

## 4. First-pass finding disposition

| ID | Finding | Severity | Refinement result |
| --- | --- | --- | --- |
| ARV-01 | Proposal approval was being confused with shared-authority activation. | P0 | The original review made activation explicit; the later v3 reconciliation narrows it to the Constitution rule 7 decision and removes obsolete shared-document edits. |
| ARV-02 | Six screens are primary-journey authority, not a complete V1 state set. | P0 | Missing-state, exact viewport, signed-out, theme, Message, mode, search, mobile rail-function, and recovery gates remain explicit. |
| ARV-03 | Approved Community-native plus Slate-projected origins were absent from the post model. | P0 | Adds a discriminated two-origin envelope, pinned exact source revision, optional social framing, no copied Slate body, and revocation behavior; recommends native creation only in the first slice unless projection states are separately locked. |
| ARV-04 | Authentication, Community membership, audience, and public-route behavior were undefined. | P0 | Adds deny-by-default viewer matrix, one effective-visibility predicate, a lowest-risk audience recommendation, and payload-free signed-out shell requirement. |
| ARV-05 | Feed attachment treatment contradicted the locked mixed-media Feed. | P1 | Separates full Feed/focused projections from compact Motion cues and keeps one canonical attachment. |
| ARV-06 | Respond, post intent/question state, Pulse/Questions sources, and response APIs were missing. | P1 | Adds the canonical response/intent model and derivation rules; exact Respond interaction remains a mandatory missing-state visual gate or first-slice deferment. |
| ARV-07 | Selected contribution, full conversation, contribution composer, saves, menus, and visible CTA targets were incomplete. | P1 | Adds explicit read models, typed capability/action matrix, reply composer, save synchronization, deep-link/history, no-third-view rules, and a complete subordinate-state visual gate. |
| ARV-08 | Feed modes, cursor, seen, caught-up, and cross-module consistency were too vague. | P1 | Keeps mode/default as an owner/visual gate; adds a finite immutable candidate window, page receipts, typed monotonic acknowledgements, catch-up snapshots, and deduplication semantics. |
| ARV-09 | Lifecycle, deletion, source revocation, block/mute/report, and moderation behavior were not buildable. | P0/P1 | Uses orthogonal publication/moderation/deletion states, revision preconditions, one propagation matrix requirement, least-privilege moderation, and neutral failures. |
| ARV-10 | Upload handling lacked a staged ownership and cleanup model. | P0 | Adds one-use direct-to-quarantine writes, finalization revalidation, authenticated monotonic callbacks, atomic binding, revocable proxy delivery, exact future allowlist/quotas, expiry, and deletion propagation. |
| ARV-11 | Idempotency, concurrency, API errors, caching, outbox, and operational evidence were discretionary. | P1 | Makes command idempotency/revisions deterministic, forbids toggles/mass assignment, standardizes safe errors, adds transactional audit/outbox and private/no-store behavior. |
| ARV-12 | Responsive semantics, shelf controls/count meaning, bottom sheet, theme, and comparison evidence were incomplete. | P1/P2 | Defines both shelf directions, child-reply count meaning, semantic mobile label, sheet contract, main-first DOM guidance, theme gate, and per-file comparison matrix. |
| ARV-13 | The current fixture/People & Interests seams could be mistaken for reusable production storage. | P0 | Names safe identity/DB/Blob/focus seams and explicitly rejects retired fixture services, proposed PLAT-008, browser-local state, and prototype CSS as the real backend. |
| ARV-14 | V1 AI, legal/readiness, and sample-to-real cutover were implicit. | P1 | Makes V1 no-generative-AI, requires external readiness before pilot/release, and requires a truthful non-mixing default-off cutover/rollback plan. |

## 5. Repository feasibility result

The current repository can support the refined architecture through a new
Community-specific domain without expanding the existing monolith further.
Recommended future boundaries are recorded in document 04:

- thin existing `/the-slate` route compatibility;
- a `/api/v1/community` blueprint;
- separate read, command, cursor, contract, media, and storage services;
- a new Community-specific migration, rollback, procedure allowlist, and
  multi-member SQL verification;
- scoped Community Feed/conversation/composer frontend modules and styles;
- isolation of unchanged The Break markup and behavior; and
- reuse of trusted identity, stored-procedure, security-header, Blob-safety,
  and focus-restoration patterns.

The retired People & Interests service/API/data and proposed `PS-PLAT-008`
migration are not a lawful starting backend. They do not satisfy the refined
audience, contribution, attachment, lifecycle, seen, and authorization
contracts. The historical Living Stream remains fixture/prototype evidence,
not canonical member data.

## 6. Decisions deliberately not invented

The review did not silently choose:

- final Community membership and audience vocabulary;
- Following versus Recent default or the exact absent mode/filter control;
- whether Search Community is adopted or truthfully removed/deferred;
- mobile access or explicit first-slice non-access for Pulse/Questions;
- dark-theme and signed-out visual treatment;
- exact pre-messaging hidden/unavailable treatment;
- mention support and notification behavior;
- post/contribution edit and deletion windows;
- moderation operations, retention, appeal, and legal-hold details;
- attachment type/size/quota and video delivery limits; or
- rollout flag, migration, and production release authority.

Each choice materially affects behavior or visuals and therefore remains a
named gate for the narrow constitutional review, the ChatGPT visual-completion
lane, Pete, or the future runtime package.

## 7. Second-pass review

Status: **Completed; no remaining P0 architecture contradiction.**

The same three independent lenses re-read the complete refined working-tree
documents. They confirmed that the core two-origin, authorization, lifecycle,
media, finite Feed, selected/full conversation, module, accessibility,
repository, no-AI, and governance shape is coherent. Runtime remained
correctly blocked.

The second pass found bounded residual issues, all addressed in the second
refinement:

| ID | Second-pass finding | Second refinement |
| --- | --- | --- |
| ARV2-01 | Respond's product vocabulary existed, but its tray/states were not in visual authority. | Keeps the canonical contract while requiring the complete visual family or first-slice deferment/hiding. |
| ARV2-02 | Several menus, See-all, Saved, media, and subordinate action outcomes were not in document 05. | Adds one bounded visible-action/subordinate-state family and forbids new routes/viewers by inference. |
| ARV2-03 | Slate-projection creation and optional conversation subject could add unseen composer controls. | Recommends Community-native creation and deterministic excerpt labels in the first slice; projection/subject entry requires later visual/runtime authority. |
| ARV2-04 | Selected-detail `View original` could be confused with the pinned Slate source. | Makes `View original` always target the root Community post and requires a separately named/locked Slate-source action. |
| ARV2-05 | Generic seen mutation could not prove Feed, activity, and conversation acknowledgement. | Adds typed monotonic commands bound to signed page receipts, catch-up snapshots, and returned conversation sequences. |
| ARV2-06 | A high-water-only Feed could still be unbounded and reorder after new activity or seen changes. | Uses an expiring immutable finite candidate-set window with high/low bounds, frozen rank inputs, separate cursors, signed returned-key receipts, and no replacement after revocation. |
| ARV2-07 | Upload byte ingress, finalize trust, callback replay safety, and immediate revocation were incomplete. | Selects one-use direct-to-quarantine write, server revalidation/finalize, authenticated monotonic callbacks, and a reauthorizing revocable application proxy for separate preview/download. |
| ARV2-08 | Response posture could silently change contribution capability. | Makes the lowest-risk first-slice semantics display-only and gates any capability effect. |
| ARV2-09 | Bootstrap could over-fetch desktop-only protected modules on mobile. | Makes module inclusion request/capability-driven and keeps server authorization independent. |
| ARV2-10 | Raw Community search text could enter ordinary logs. | Categorically excludes raw queries; only coarse non-content metrics are permitted absent a separate contract. |
| ARV2-11 | Unsafe legacy mutable APIs, tablet viewport forcing, and early-error caching were easy to miss at cutover. | Makes legacy endpoint retirement/isolation mandatory and requires explicit native-responsive plus blueprint private/no-store reservations/tests. |

Focused closure recheck: **Pass, 2026-07-31.** Independent visual-contract,
trust/data, and repository-feasibility reviewers verified their exact residual
findings against the second refinement. All three reported closure with no new
contradiction. Runtime remains blocked; this Pass covers architecture review
only.

Pete then accepted this logical architecture and review/refinement record and
directed the workflow to the next documented gate. That acceptance does not
satisfy any external gate in section 8.

## 8. Current gate conclusion

The architecture is substantially better than the initial logical outline and
is suitable as input to a future runtime initiative **after** the external
gates pass. It is not permission to build now.

The next lawful sequence under the lean v3 control plane is:

1. merge `PS-COMMUNITY-FEED-AUTHORITY-001` to activate the narrow Constitution
   rule 7 and Journal reuse boundary without reviving obsolete shared-document
   edits;
2. complete and Pete-lock the missing V1 visual state set;
3. confirm that no then-current scoped hold applies to Community;
4. create a dedicated Community runtime initiative from fresh authoritative
   main with exact ownership and contracts; and
5. implement, test, visually compare, review, release, and verify through that
   initiative.
