# F: member visitor AI eligibility and buffered orchestration

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

## Later F work and deployment

Routes, UI wiring/rendering, independent citation endpoint authorization,
operational deployment limits and a qualified production support/provider
adapter remain later F acceptance work. The authenticated identity port must be
bound to the real request identity in that integration; no client owner key may
construct it. No production deployment, schema application, enablement, real
member/identity/provider action, paid capacity purchase or Package G activation
is included. Existing application behavior remains unwired to these services.
