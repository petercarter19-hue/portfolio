# PS-SYNTHETIC-MULTI-MEMBER-QA-001

Status: implementation candidate; no live-identity, merge, deployment, enablement,
or production-proof authority.

## Purpose

Provide one reusable foundation for proving that two ordinary PeerSlate members
remain distinct and private in clean clients, simultaneous clients, and a
sequential account switch. The foundation closes the tooling and evidence gap
recorded as `GAP-SYNTHETIC-MULTI-MEMBER-QA`; it does not itself close that gap
with live proof.

## Current truth at package entry

PeerSlate already has useful component evidence:

- trusted Easy Auth principals map server-side to opaque internal accounts;
- mocked provider subjects resolve to distinct accounts;
- Interview Studio tests prove distinct opaque browser-storage scopes and keep
  non-owner evidence empty;
- owner-scoped SQL transaction verifiers exercise two-owner and cross-owner
  denial behavior with rollback; and
- prior production evidence covers one existing member's sign-in, protected
  arrival, refresh, public return, additional tab, and sign-out journey.

That evidence does not prove two dedicated synthetic members through the full
deployed chain. The repository does not contain an approved two-identity
inventory, a reusable clean-client journey, bidirectional account-switch proof,
or a common evidence-and-cleanup contract. One prior package records a single
synthetic member observation, which does not establish the required pair.

## Approved identity model

The retained model contains exactly two aliases: `member_a` and `member_b`.
They represent dedicated ordinary QA members that are non-owner, non-admin,
private by default, and controlled by Pete.

Pete alone provisions or retires the identities and performs every login and
MFA action. The repository, harness, logs, and evidence must not contain their
names, addresses, provider subjects, internal account keys, credentials, MFA
material, claims, headers, cookies, tokens, browser profiles, storage state, or
session files.

No identity is provisioned by this candidate. The aliases are not proof that
two live identities exist.

## Implemented foundation

The provider-free implementation has four surfaces:

- `qa/synthetic_member/` defines the exact aliases, 38 canonical journeys,
  closed outcome and limitation codes, sanitized manifest, truthful result
  calculation, count-only cleanup evidence, and an in-process redacted cleanup
  ledger;
- `scripts/run_synthetic_member_qa.py` prints the plan, initializes evidence,
  records closed outcomes, records cleanup counts, and validates final evidence;
- `tests/synthetic_member_qa/` proves the fail-closed evidence, isolation,
  cleanup, and command-line contracts; and
- this package records the attended procedure and authority boundaries.

The tool never imports a browser driver, HTTP client, Azure identity library, or
MSAL. It cannot create an identity, open a site, sign in, read a session, query
a database, or delete application data.

## Canonical journey groups

The complete machine-readable matrix comes from:

```powershell
python scripts/run_synthetic_member_qa.py plan --json
```

It includes:

1. clean Client A, clean Client B, and a signed-out control;
2. signed-out private-data absence;
3. first arrival for both members and distinct mapping confirmation;
4. simultaneous owner-only visibility;
5. list, read, update, delete, export, and forged-reference denial in both
   directions;
6. browser-local state isolation in both directions;
7. sequential A-to-B and B-to-A account switching;
8. refresh, second tab, public return, sign-out, and expired-session behavior;
9. a clean repeat run; and
10. count-only cleanup and client-destruction evidence.

The matrix is the shared foundation. A later feature package supplies its own
approved member actions without weakening or shortening the matrix.

## Evidence minimization

Retained evidence is an exact JSON shape containing only:

- neutral run, surface, browser, source-commit, and release labels;
- `member_a` and `member_b`;
- canonical journey identifiers;
- expected structural outcomes;
- `pending`, `pass`, `conditional`, or `fail`;
- closed limitation codes; and
- per-alias created-item and active-residue counts.

There is no free-text evidence field. Safe labels reject email addresses, URLs,
UUIDs, and token-shaped values. Forbidden identity, session, private-record,
and screenshot fields are rejected recursively. A stored Pass is rejected when
the journeys or cleanup calculate to another result.

Screenshots and private-content captures are not part of the default evidence.
If a later package requires one, it needs separate authority and must use
pre-approved synthetic content and redaction.

## Cleanup contract

The attended run begins with an owner-scoped baseline for both aliases. Any
created item is kept only in an ephemeral in-process ledger; retained evidence
receives counts, never handles or URLs. Cleanup uses the application's normal
member contract when that action is separately authorized.

A Pass requires at least one created item for each alias, zero active residue
for both aliases, destruction of all four client contexts, and an honest
retention disclosure. Any active residue or failed destruction produces Fail.
Application deletion with unknown retention produces Conditional, never a
permanent-deletion claim.

## Local use

Create a pending manifest outside the repository:

```powershell
python scripts/run_synthetic_member_qa.py init `
  --output <SANITIZED-EVIDENCE-PATH> `
  --run-id qa-YYYYMMDD-001 `
  --source-commit <FULL-LOWERCASE-GIT-SHA> `
  --mode local_contract `
  --browser edge `
  --browser-version <NEUTRAL-VERSION>
```

Record only a closed structural outcome:

```powershell
python scripts/run_synthetic_member_qa.py record-journey `
  --manifest <SANITIZED-EVIDENCE-PATH> `
  --journey signed_out_private_baseline `
  --status pass
```

Final validation refuses pending evidence:

```powershell
python scripts/run_synthetic_member_qa.py validate `
  --manifest <SANITIZED-EVIDENCE-PATH> `
  --final
```

`ATTENDED_PROOF_RUNBOOK.md` governs any separately authorized two-identity run.

## Dependencies and remaining gates

- `docs/governance/PACKAGE_REGISTRY.json` is intentionally unchanged because
  the active Interview AI lane owns that exact shared path. Registration there
  waits until the collision clears.
- Pete must separately confirm and provision two suitable QA identities.
- Any deployed attended proof needs separate live-access authority and Pete's
  direct login/MFA participation.
- A fresh independent review is required on the frozen exact candidate.
- Implementation-candidate merge, deployment, enablement, and production proof
  remain separate owner decisions.

Known product limitations are reported rather than hidden. In particular, the
source repository cannot control the App Service session lifetime, and the
existing sign-in completion report records cross-tab sign-out on `/app` as
unreconciled. Those journeys may be Conditional; they cannot be silently marked
Pass.
