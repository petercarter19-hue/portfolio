# PS-PROFILE-CONNECTIONS-PROVIDER-INTEGRATION-001 — candidate evidence

## Scope and authority

Pete authorized this package under
`session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`.
This is a Protected repository package with authority through merge.
Production authority is withheld. No deployment, production request, SQL,
schema, migration, grant persistence, identity or relationship operation,
provider registration, credential use, or live operation is part of this
record.

## Governance lineage

- Claim-only activation: PR 878 / build 2333 / merge
  `771fcea93facb858fa41078c2e84617ba9f59013`.
- Deferred Package Registry surface extension: PR 886 / build 2351 / merge
  `d846bb265c3cd7436d9a902c4fd012a2fcda94b8`.
- The implementation branch was rebased onto that exact extension merge before
  registration, final validation, or final review.

## Candidate outcome

Exact candidate `690181f9ffd880dd227be329c95a36e031eb113e` on direct
parent/base `d846bb265c3cd7436d9a902c4fd012a2fcda94b8` adds only the
three PS-CONNECT-002 actor-scoped procedure names to the shared database
allowlist and proves their values remain positional parameters. The unchanged
closed repository remains injected, and `ConnectionFoundationProfileReader`
remains unregistered and unwired from Profile.

The unchanged provider contract derives the actor only from an exact
`PeerSlateIdentity`; preserves request, accept, decline, cancel, expire,
disconnect, block, unblock, and reconnect state; keeps relationship versions
distinct from block epochs; and fails closed on invalid, self, absent,
cross-owner, malformed, or unavailable results. A focused reader test proves
pending and disconnected states, relationship versions, block epochs, and
block precedence reach Profile's existing snapshot shape without changing its
consumer.

The candidate changes exactly six claimed paths: the Package Registry, two
initiative documents, `services/database_service.py`, and two focused test
modules. The Registry gains one locally alphabetized `current_protect` row and
recomputed counts of 72 `current_protect` entries and 140 total entries. It
does not change the claim, Profile, application composition, routes,
templates, navigation, providers, the connection service or repository, SQL,
migration, rollback, verifier, SQL registry, production schema state, grants,
identities, relationships, reports, flags, deployment, or live behavior.

## Validation

- Database boundary and connection service suites: **32 passed**.
- Immutable connection repository and Profile relationship suites: **11
  passed**.
- Static PS-CONNECT-002 migration suite: **11 passed**.
- Combined focused matrix: **54 passed**.
- Package Registry validation: **2 passed**; one unique row, correct local
  alphabetical neighbors, category counts, and total all reconcile.
- Exact-candidate full repository suite in a requirements-only isolated
  environment: **5,552 tests**, comprising **5,526 passed** and **26 inherited
  skips**, with no failures.
- Python compilation, claimed-path and forbidden-path checks, exact allowlist
  set/count, immutable input checks, and `git diff --check`: pass.
- The PS-CONNECT-002 executable migration digest recomputes to
  `b5a2695916d0b1b658341cd7b103894456dcc58b13db580525ed45600f315606`.
- Strict fetched, clean, task-bound write preflight: pass; exact head
  `690181f9ffd880dd227be329c95a36e031eb113e`, ahead 1 / behind 0, six
  changed paths, and current main
  `d846bb265c3cd7436d9a902c4fd012a2fcda94b8`.
- Current-tree Gitleaks scanned approximately 37.23 MB with zero findings;
  exact one-commit range Gitleaks scanned approximately 16.07 KB with zero
  findings; all local refs scanned 2,474 commits / approximately 94.27 MB with
  zero findings.

Before the first provisional commit, a working-tree scan found two
generic-api-key false positives in deterministic `SubjectUserKey` test
fixtures. Only those fixture values were changed to low-entropy local IDs;
their parameter-binding assertions and semantics remained identical. The
affected 32-test suite and every secret scan then passed. No credential or
rejected committed candidate existed.

## Independent review

Independent final exact-SHA review ACCEPTed candidate
`690181f9ffd880dd227be329c95a36e031eb113e` on base
`d846bb265c3cd7436d9a902c4fd012a2fcda94b8` with zero findings. Reviewer:
`agent:/root/profile_d1_writer`; reviewed at `2026-09-03T07:12:51Z`.

The review verified the exact six-path claimed delta, three-name allowlist,
positional binding and pre-connection rejection, unchanged provider and SQL
boundaries, exact Registry row/counts, negative relationship-state proof,
complete validation, and dark/unregistered runtime scope. Acceptance
authorizes repository merge only.

## Release truth

This evidence binds an immutable repository candidate. It does not state or
imply that PS-CONNECT-002 is applied, granted, registered as a runtime
provider, enabled, deployed, production-ready, or live. Any schema apply,
database identity/grant binding, provider composition, Profile wiring,
deployment, or live proof requires a separate claimed package and explicit
authority; it is not inferred here.
