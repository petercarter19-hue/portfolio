# F: member visitor AI eligibility and buffered orchestration

## Accepted continuation

The first milestone merged through PR1141 as `7951bcb3c2f62abd8d3a51ae5ef1ecb8a4e27c57`.
Pete's keep-going direction prospectively extends this same active package through
F areas 3-5 under decision
`session:01a08dfb-7229-75f0-8017-07dd590f1795/decision:evt-538eccb4-0d30-4f6a-8e62-d14650783ef1`.
Claim-only PR1143 admitted ten tracked route/UI/browser surfaces; CI3575 passed
all four jobs and current policies, and main is
`491a3c3c5759a455835c76e65d12926c57dd2850`. The historical claim outcome below
remains first-milestone evidence, not the current continuation boundary.

Independent citation access, guest and authenticated visitor preview, provider/
support and operational-protection seams, browser/adversarial tests, independent
review, CI, merge and close are now included. SQL3571 remains evidence for its
unchanged readers; it does not certify later Python or UI changes. Production,
live providers/identities/members, spending and Package G remain excluded.

Naming decision
`session:01a08dfb-7229-75f0-8017-07dd590f1795/decision:evt-f263bf7e-9e07-4892-b6f6-530b1c9afb15`
requires an explicitly publication-authorized full name, otherwise neutral
"Ask about this Resume" / "Try visitor AI". Actual production approved-name
binding is unavailable and remains an integrated-readiness dependency. Account
identity, slug, legacy Profile ownership and fixture names are not substitutes.

## Assignment and boundary

Implement the first two F acceptance areas from the accepted MVP1 architecture
and `12_PACKAGE_F_ASSIGNMENT.md` (September 26, 2026). Base: admission merge
`acd20fcaf63ac618dfbb9cc5db93a79820fb41a3`, PR 1140, CI 3558 all four jobs passed.
This is a substantive checkpoint within F. The active claim records the exact
writer, surfaces, independent review and through-merge repository authority.
The existing writer remains Astra High; the separate final reviewer remains
Astra Extra High. Production authority is withheld.

## Actual implementation

- `usp_GetMemberVisitorAiBySlug` derives the member from current sharing state.
  It checks active identity, current independent AI manifest membership and
  current policy before returning source bytes. Display permission is separate.
- `usp_GetMemberVisitorAiPreviewForOwner` resolves an authenticated server
  owner's key. It returns saved canonical evidence and versions for the owner
  application. Explicit proposed AI choices are bound to that exact snapshot,
  draft and candidate by a process-local immutable binding. Proposed wording,
  uploads, raw documents, pending proposals and artwork are never evidence.
- The internal SQL reader owns a short transaction using E's sharing, sorted
  policy, draft, publication and media/catalog lock order. It creates no durable
  fact store. The transaction ends before the provider is called.
- Guest evidence uses E's committed codec bytes and SHA-256, validated against
  current canonical fields, row versions and policy. Owner preview can select
  current saved canonical facts before sharing or an AI grant is saved; its
  binding cannot be used as a guest credential or private-assistance context.
- Source bundles reuse `PublicationEvidenceVersion`, `VisitorAIManifest`,
  `VersionTuple` and foundation `SourceVersion`. Canonical/content/access/source,
  identity, publication/sharing, draft/candidate, parent and media dependencies
  are retained in typed references and the complete snapshot digest. Existing
  publication revision pins media placement when E's published JSON has no
  independent placement version. Unknown or unavailable authority is refused.
- The service sends the exact question and only the eligible immutable sources
  to the existing foundation gateway. It buffers the result, validates citation
  structure, asks the support adapter to assess the complete answer, builds a
  safe output, and performs a fresh SQL comparison immediately before return.
  Changes or failed rechecks discard every factual answer and citation.
- Public results omit internal source IDs, private URLs, provider metadata and
  unvalidated follow-up prose. Unsupported and ambiguous answers use neutral
  boundary text; failures preserve the question. There is no account quota or
  five-question sign-in gate.

## Semantic support boundary

`SupportValidationPort` evaluates the complete summary and claims, including
meaning, numbers, dates and uncertainty. Missing support validation returns
unavailable. The synthetic catalogue demonstrates accepted paraphrase and
rejects claims with contradictory meaning, changed quantities/dates, stronger
certainty or unsupported summary text despite an exact matching citation.
This is a bounded test oracle, not a production semantic validator or a claim
of comprehensive entailment. No live provider is called or selected here.

## Verification and isolated SQL plan

Focused unit/adapter tests exercise real Python repository/service code using a
protocol database fixture. They do not establish SQL acceptance. New engine
oracles in `tests/test_member_visitor_ai_sql_engine.py` use the actual procedures,
driver, repository and service on two synthetic databases. Required cases cover
forward/verify/rollback/reapply, two members, the display/AI matrix, exact bytes
and question, owner preview and stale binding, effective application privilege,
mutations on a second connection during generation and validation, media,
malformed manifests and preservation of populated E state on F reader rollback.

The new F runner/YAML reuse E's unchanged pinned disposable runtime, offline
wheel verification, internal network, bounded resources and identity-bound
cleanup. The inherited fixed resource names are explicitly disclosed by the
read-only plan; each run has new F custody. Only the isolated oracle entrypoint
is replaced. A fresh dispatcher-verified exact-source, exact-plan, one-run
authorization is required. Environment/queue equality is a consistency check,
not independent authentication. E's consumed decisions do not authorize F.
Default plan mode creates no resource and makes no SQL connection. SQL scripts
remain proposed with a null migration gate. Syntax parsing is not engine proof.

Independent review, actual isolated engine results, CI and merge evidence belong
in this package's fixed receipt/evidence files when obtained. No such result is
claimed by source or protocol tests alone.

## Continuation implementation and configuration

F registers these independently gated, private/no-store APIs in the existing
publication blueprint:

- `POST /api/public/profiles/<slug>/ai/questions`
- `GET /api/public/profiles/<slug>/ai/citations/<opaque-handle>`
- `POST /api/resume/me/visitor-preview/questions`
- `GET /api/resume/me/visitor-preview/sources`
- `GET /api/resume/me/visitor-preview/citations/<opaque-handle>`

Both publication and `PEERSLATE_MEMBER_VISITOR_AI_ENABLED` must be true. The
registered default service binds the durable SQL repository to actual
`get_current_identity()` for private preview and remains unavailable without
explicit settings. The implemented startup composition reads optional JSON
`PEERSLATE_MEMBER_VISITOR_AI_SETTINGS`. It builds the existing foundation's real
`AzureFoundryResponsesProvider` with F-specific answer instructions, a second
complete-summary/claim semantic-support call, bounded citation cache and runtime.
Construction acquires no token and makes no provider call. Credentials use the
existing passwordless Azure credential chain, with interactive browser excluded;
token acquisition occurs only inside an explicitly enabled, admitted request.
No deployment, account, credential, price schedule or live provider is selected
implicitly. Both feature flags default false and are independent of settings.

Required settings keys: `endpoint`, `deployment`, `scope`, `limits`, `provider`,
`prices`, `citation_capacity`, `citation_lifetime_seconds`. `limits` uses all
`VisitorOperationalLimits` fields. `provider` requires positive integer
`maximum_input_tokens`, `maximum_input_bytes`, `maximum_output_tokens`;
the token reservation must cover the byte ceiling plus1024 framing tokens.
`prices` explicitly supplies positive `input_micro_usd_per_million`,
`output_micro_usd_per_million`, and a `schedule_ref`. These are conservative
operator safety inputs, not a current-price or billing claim. The runtime's
per-request cost reservation must cover BOTH complete Foundry calls under that
schedule. Invalid settings log only a constant diagnostic and stay unavailable.
Multi-instance settings require an explicitly injected
`MEMBER_VISITOR_AI_PROTECTIONS` implementing distributed accounting; there is
no automatic local fallback. The optional public-name binding remains separate.

Each Foundry phase has its own bounded per-call ledger; the outer window
prepays both phases. This does not inherit a lifetime evaluation call limit.
Source/response bytes, token ceilings, HTTPS Azure origin/no-redirect behavior,
usage settlement and structured answer decoding reuse the accepted foundation.
Transport connect/read timeout is capped by the remaining request deadline;
no further call starts once the deadline has expired. The support adapter sends
the complete original question, summary, claims, citations and limitations with
the same eligible sources, and requires a complete matching semantic verdict.
Unknown, malformed or incomplete verdicts deny factual release. Model-based
support is implemented, but live semantic quality remains unqualified.

`MEMBER_VISITOR_AI_RUNTIME` is required for all F API work. Its immutable
`VisitorOperationalLimits` configures request bytes, question characters,
concurrency, deadline, request-rate window, bounded client cardinality and
worst-case aggregate cost reservations. Citation/options reads also consume an
operational request/reservation, conservatively using the same envelope; this
counter is not actual provider billing or a product question allowance. There
is no lifetime/session quota and no sign-in transition after five questions.
Rate/budget/concurrency refusal preserves the question and is retryable.

The runtime has no waiting queue. Reserve, generation/support, accounting finish,
serialization and final SQL/expiry checks all run within one deadline while
retaining local and distributed concurrency. `finish` completes accounting
WITHOUT releasing concurrency; the final response fence follows it. `release`
frees capacity only when the WSGI response closes, or abandoned work actually
ends. Thus remote finish work cannot sit between the final check and delivery.
A response timeout retains the running slot until work actually ends; failures
do not refund worst-case reservations. The complete configured provider path is
tested with stub transport; it does not prove live cost or quality qualification.
`SingleProcessVisitorProtections` requires an explicit
single-process scope. Multi-process/multi-instance deployments must inject a
qualified distributed `VisitorProtectionPort`; scope mismatch or unavailable
accounting fails closed, with no local fallback. None is enabled or qualified
for production by this package.

Citation tickets are random opaque handles in a capacity/TTL-bounded transient
private cache. They are not credentials or a new canonical/publication store.
Restart, expiration, eviction or routing to an instance without that cache
returns neutral unavailable. An optional shared cache must preserve the same
immutable bundle and issue/get contract. Every read resolves current subject,
purpose, permissions and full versions, validates the exact excerpt, and
rechecks before releasing only a safe label and excerpt. Preview tickets still
require the current authenticated owner; guest routes never accept them.
Excerpts must fit within one saved factual field (maximum1200 characters),
not codec metadata or sibling fields. Output is bounded to12 citations and8000
summary characters. No provider call occurs when a citation is opened.

The UI implements the approved D08/D11 contextual panel and M08/M11 mobile
sheet, real-result accordions and citation reads. Typed questions survive
hide/reopen, provider/network/operational failure and stale previews. Choosing
preview sources does not save permissions, publish, or borrow private AI
assistance. Changed local choices clear old results; changed canonical/draft/
policy versions deny old server bindings. Suggested questions are empty rather
than fabricated. Shared header and the underlying E publication page remain
their existing surfaces; the complete member-name/Resume presentation is an
explicit integrated-readiness dependency, not established by these F visuals.

## Verification and limits

The required strict publication browser runner now demands all six journeys
(the original four plus two F journeys), zero skips, and actual execution.
Local Playwright1.62 with its pinned Chromium exercised desktop/mobile, keyboard modal escape and
focus return, 320/390/640/768/1024/1440 CSS widths, exact sixth question,
hidden-but-AI-permitted evidence, independent citation revocation, XSS text,
network/provider failure recovery, and separate synthetic owner/guest/other
contexts. The narrow viewport exercises zoom-equivalent reflow; it is not
physical-device or assistive-technology certification. Provider, identity,
publication state and SQL rows are synthetic in these browser tests; real F
Python repository/service/HTTP code runs. The unchanged SQL reader engine
evidence remains SQL3571 at its recorded source, not a new engine run.

No production deployment, schema application, enablement, real member/identity/
provider action, paid capacity purchase or Package G activation is included.
The real configured provider/support path is implemented; live qualification,
distributed accounting, actual public-name binding and production enablement
remain separately unproved. Final independent review,
required CI and merge/close evidence are recorded in the fixed package evidence.
