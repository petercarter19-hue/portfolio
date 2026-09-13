# PS-CALLER-COMPATIBILITY-001 implementation evidence

Owner authorization:
`session:01a0882f-9e94-74d3-8812-0c85df1f5aae/owner:fix-caller-compatibility-2026-09-12`.

This Protected package makes lifecycle and delivery caller checks usable from
Codex and Pete-operated external handoffs without user or global identity
environment setup. Codex resolves only native `CODEX_THREAD_ID`, normalized as
`session:<UUID>`; inherited `CODEX_SESSION_ID` is never caller identity. Legacy
`PEERSLATE_CALLER_REF` remains supported, and all identity sources must agree.

External receivers use an opaque caller-context ID registered in the existing
machine-local worktree registry. Each active record is bound to one canonical Git
common directory, receiver, package, registrar, and exact owner authorization
reference. Registration and revocation require the independently resolved current
control holder and the exact current lease token. Registration can precede the
package claim or receiver acceptance, but it changes no claim, lease, custody,
branch, repository authority, review, CI, or production boundary.

Every caller-context use reloads and validates its live registry record and exact
operation package. Context use cannot create an unscoped control lease. Explicit
and native identities are reconciled even when the registry has no custody
history; legacy identity-free operations remain compatible. Delivery preflight
validates any supplied or guarded context before applying CI or absent-registry
exemptions. `control-run` and both runtime verification workspace modes pass the
scoped context into children while removing the bare legacy caller value.

The first independent exact-candidate review returned REVISE with five reproduced
issues: preflight exemption ordering, missing-package scope, no-history identity
conflict suppression, tokenless context registration/revocation, and missing
runtime verification propagation. Correction round one adds direct regression
coverage for each issue. Final focused and regression results are recorded with
the replacement candidate supplied for renewed independent review.

Correction-round verification:

- `tests.test_caller_context`, `tests.test_delivery_preflight`, and
  `tests.test_governance_pointers`: 280 tests passed in 5.744 seconds.
- `tests.test_worktree_lifecycle`: 105 tests passed in 577.714 seconds.
- The two command-level reviewer probes added after that run passed in 3.734
  seconds: missing-package context acquisition and no-history explicit/native
  identity disagreement.
- Initiative/package registry accounting: the exact previously failing test
  passed after this evidence replaced the unregistered initiative directory.
- Python compilation and `git diff --check` passed.

The first lifecycle rerun was stopped after its synthetic tasks inherited the
real host `CODEX_THREAD_ID` and therefore correctly disagreed with their fake
task references. The test modules now explicitly isolate identity-free legacy
fixtures; representative failing cases passed before the clean full rerun.

Independent exact-candidate review passed
`388ae824c211aefd5942768786aea7a133650ca6` with no findings. Reviewer
`session:01a09829-21dd-7ba0-b8ef-bdf1d319d745` ran verified
`gpt-6-astra` at `high` effort, passed 21 affected tests in 8.843 seconds, and
successfully repeated the original five adversarial probes in disposable
repositories. The reviewer confirmed the pushed branch and clean checkout at
the exact candidate and recorded no writer-tree, production-registry, or PR
mutation. This review is synthetic Windows validation; actual external-runtime
proof, CI acceptance, merge, and production remain separate boundaries.

These controls are operational attestations between cooperating processes on the
same Windows account. They are not cryptographic authentication and do not confer
filesystem isolation from another same-account process.
