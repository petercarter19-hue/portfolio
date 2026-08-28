# PS-WORKSHOP-PROVENANCE-EDGE-001 — completion evidence

Runtime-inert Protected delivery record. Production, deployment, schema,
identity-use, and live-verification authority remain withheld. The review time
below is the writer-recorded UTC immediately after receipt of the independent
verdict.

## Outcome

The reviewed candidate closes the two accepted Workshop provenance gaps
without a schema change. Taking up a Spark now preserves PeerSlate's generated
focus seed as separately labelled context and starts the member's answer empty.
An AI proposal cannot be accepted until the session contains nonblank member
wording. The first member wording remains retained across later acceptances,
and accepted AI wording remains labelled `ai_assisted_approved`.

Signed legacy 6/7-element AI-assisted sessions that contain an answer but no
retained member original are still readable, but their source cannot be proved.
They are classified as provenance-ambiguous and fail closed before proposal
acceptance, quick durable save, or final durable save. The refusal is atomic:
the session is unchanged and no owner save occurs. A new Spark is structurally
distinguishable without a ninth cookie field because its nonblank focus seed is
stored separately in `opening_thought`; that provenance-bearing seed is never
dropped to fit the cookie budget.

Anonymous Workshop remains browser-only and database-free. Existing provider
GET, spend, refusal, archive, and Workshop D use-disclosure behaviour is
unchanged. No history display, edit provenance, schema, product redesign,
deployment, or production action is included.

## Candidate and independent review

- Activation merge/base: `51285339b67aaec28d5c70f5f599f90c33e208bc`.
- Reviewed candidate: `20144f00831197e53a8bd83a679e6b37327cfb76`.
- Branch: `work/2026-08-28-workshop-provenance-edge-001`.
- Writer: `agent:/root/workshop_e_implementer`.
- Independent reviewer: `agent:/root/workshop_e_implementer/workshop_e_exact_sha_reviewer_r2` (fresh Sol Ultra assignment).
- Writer-recorded receipt UTC: `2026-08-28T02:40:16Z`.
- Final verdict: **unconditional PASS**, read-only, with no remaining findings.

The initial exact candidate `2a0905679f339ce3f6240b023272ee6599b57a72`
received a FAIL because exact-base stale Spark and blank-first 6/7-element
cookies could promote generated text into `original_member_wording` on a later
acceptance or durable save. The writer reproduced the issue, added the explicit
fail-closed provenance state and route gates, refroze once, and obtained a
fresh review of the corrected exact SHA. No byte of the final candidate changed
after the PASS.

The final reviewer independently verified the Azure remote SHAs, exact
merge-base, clean detached checkout, and exact-base scope. The reviewed
candidate changes exactly these claimed implementation surfaces:

- `services/workshop_work_session.py`
- `templates/workshop_work_session.html`
- `tests/test_workshop_review.py`
- `tests/test_workshop_spark.py`
- `tests/test_workshop_work_session.py`
- `workshop_work_routes.py`

Only this evidence file and its matching receipt are added after review; no
reviewed candidate byte changes.

## Verification

Writer verification on the corrected candidate:

- `ANTHROPIC_API_KEY=test-key-for-ci-only PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements.txt python -m unittest discover -s tests -p 'test_workshop*.py'`
  — **651 tests passed, 1 skipped, 0 failed**.
- `ANTHROPIC_API_KEY=test-key-for-ci-only PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements.txt python -m unittest tests.test_site_rules tests.test_governance_pointers`
  — **40 tests passed, 0 failed**.
- Focused correction coverage passed for exact stale Spark 7 and blank-first
  6/7 states across service acceptance, route acceptance, quick owner save, and
  final owner save; new Spark member save; cookie-shape classification; and all
  three byte-budget cases.
- `git diff --check`, claimed-surface comparison, exact remote-tip proof, and
  the fetched clean write preflight all passed.

Independent reviewer verification:

- **324 targeted tests passed, 0 failed**.
- **741 contracted Workshop, Workshop D, provider/spend, and governance tests
  passed; 1 expected SQL-gate skip; 0 failed**.
- Coverage included 4/6/7/8 cookie compatibility, the `<3072` adversarial
  shared-cookie ceiling, atomic refusals, anonymous database-free behaviour,
  no provider use on GET, spend caps, Spark attribution, and Workshop D.
- The reviewer supplied result counts and scope but no literal commands, so no
  reviewer command is invented here.

All provider calls were mocked. No database was contacted.

## Release state and boundaries

At this evidence-tail state the exact reviewed candidate is pushed and accepted
but not yet merged, deployed, enabled, schema-applied, or live-verified. The
next authorized action is the guarded repository merge PR and CI. Repository
merge authority does not grant deployment, schema, identity, or production
authority; those states remain withheld.
