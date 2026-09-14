# Owner Technical Completion Report: PS-MVP1-MY-DATA-INTAKE-AI-001

## What was built

Private My Data intake and Luna Extra High processing on collision-free
surfaces. The composer draft now persists on the server across signed-in
devices, expiring 30 days after the last edit, with version-checked saves
and a truthful two-version recovery choice on conflict. Typed text,
selectable-text PDF/DOCX/TXT (10,000,000 bytes each), and English voice
(180 seconds per recording, several per draft) flow through the accepted
intake lifecycle. The adapter is configured to request GPT 5.6 Luna
extraction and semantic comparison at reasoning effort `xhigh` with strict
structured output. Matching is
exact-then-semantic over the member's own eligible facts, yielding new,
equivalent, additional-detail, contradiction, and uncertain outcomes.
Equivalents keep the existing entry with a quiet receipt and one explicit,
independently bound keep-as-separate path per equivalent, including mixed
equivalent/new/uncertain extraction results. Extracted text, document, and
recording candidates live in mutable source-version-bound storage; immutable
receipts retain identifiers only, and purge redacts and invalidates pending
candidates. The server-held override is bound to the authenticated owner and
validated candidate; it does not accept arbitrary client-supplied canonical
values. Draft load, save, discard, replay, and expiry mutate only the draft
portion of current owner state under an owner-scoped repository lock. Every
nondraft command commit preserves that live draft map, so a stale whole-owner
snapshot cannot overwrite a newer acknowledged draft.
Candidate validation, consumption, canonical write, and intake commit now run
under the same owner mutation guard as source purge. If purge wins, a stale
keep-separate action refuses without restoring the source or writing canonical
content. In the browser, accepting one equivalent removes only that bound
action; all remaining equivalent actions, mixed proposals, and unfinished
draft state stay available on desktop and mobile.
The in-memory adapter proves this atomic boundary under its owner lock. The
proposed SQL adapter fails extracted keep-separate closed until a separately
authorized schema transaction can validate and consume the source candidate
with the canonical and intake writes; no process-local lock is claimed as
cross-worker database authority.
Provider failure leaves a retryable, manually finishable state and never
discards input. AI proposes; only the member's decision writes canonical
truth, always private by default. The adapter is configured to request Luna
processing; live provider use remains deferred.

## Files

- `services/my_data_extraction_adapter.py` (new)
- `services/ai_foundation/contracts.py`, `services/ai_foundation/azure_foundry.py`
- `services/resume_intake_service.py`, `services/resume_intake_repository.py`,
  `services/resume_intake_proposals.py`
- `resume_intake_routes.py`
- `static/js/my-data.js`
- `tests/test_my_data_intake_ai.py`, `tests/test_my_data_drafts.py`,
  `tests/test_my_data_intake_sources.py` (new)
- `tests/test_resume_intake_service.py`, `tests/test_resume_intake_routes.py`,
  `tests/test_my_data_browser.py`, `scripts/run_my_data_browser_tests.py`
- `docs/initiatives/PS-MVP1-MY-DATA-INTAKE-AI-001/README.md` and this report
- `docs/governance/PACKAGE_REGISTRY.json` (truthful initiative registration)

## Verification

Unit, route, repository-adapter, and real Flask browser suites green. Exact
numbers, candidate SHA, branch, PR, and CI builds are recorded in
`docs/governance/lane_claims/evidence/PS-MVP1-MY-DATA-INTAKE-AI-001.md`.
All provider contact in tests uses deterministic fakes that assert the
model, effort, and schema demanded.

## Boundaries and honest limits

- No production deployment, schema application, live provider use, feature
  enablement, or public/visitor effect. Deterministic fakes prove no SQL
  engine, Azure deployment, live provider, or public-consumer behavior.
- Draft SQL procedures and tables, the expiry worker host, and production
  wiring of the adapter and exclusion source remain separately authorized.
  Reads already enforce draft expiry; the SQL store reports drafts
  truthfully unavailable until its procedures exist.
- Generic Azure live Foundry execution remains deferred. Local tests assert
  the outbound Responses `text.format` envelope and a recursively strict
  closed schema; they do not prove a live deployment ran.
- Member-facing copy avoids dash punctuation. Public resume and visitor AI
  effects are never described as active.
- Claim-only control PR 1028 merged the package-registry surface admission as
  `1c9c6769c1c44b73498e5a013a3ae552b78d894a` after CI 2952 succeeded. The
  final package candidate adds the one truthful `current_protect` registry
  entry and matching counts.
- Pete superseded the external Cursor/Grok path and reassigned the package to
  the internal writer. The same independent Codex Astra High reviewer remains
  the required exact-SHA gate. That reviewer returned PASS on exact product
  code candidate `fb6af5cd78da3e4be4d5b27db82f1e5be80beece`; the later registry
  and completion-record delta does not change product code. Exact lineage and
  verification live in the evidence file.
