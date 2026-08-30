# PS-MYOPP-CRITERIA-001 — candidate evidence

## Scope and authority

Pete authorized the exact bounded disposable proof envelope at
`session:01a02f42-15ac-7d92-a2a9-60b7e800c388/authorization:2026-08-29/c3-disposable-proof-envelope`.
Repository authority remains `through_merge`; production authority remains
withheld. This evidence grants no staging or production schema action,
deployment, enablement, provider contact, search execution, UI work, C4, or C5.

## P-1 repository evidence

The owner-scoped criteria service and proposal-only interpretation seam prove a
visible draft before explicit Apply, deterministic create/edit/clarify/dismiss/
refine/keep-current/discard/apply commands, manual parity, provider-unavailable
behavior, immutable snapshots and terminal receipts, complete idempotency and
stale/terminal precedence, and cross-member not-found isolation. Apply only
allocates an execution key; no retrieval or search implementation exists.

The writer's bounded suite at the proof-bearing checkpoint covers focused C3,
relevant C2 regression, package/registry, governed migration-path, evidence
policy, and whitespace controls. Exact counts and commands are in the writer
return for the pushed checkpoint.

## P-2 disposable Azure SQL proof

- Authorized attempt: 1 of 3, `ps-myopp-c3-gate-20260829-a1`.
- Attempts a2 and a3 were never created.
- Pre-create exact-name lookup: `ResourceNotFound`.
- Azure scope: resource group `peerslate`; server `peerslate`
  (`peerslate.database.windows.net`); `centralus`; `Basic`;
  `SQL_Latin1_General_CP1_CI_AS`.
- Gate time: `2026-08-30T02:44:08Z`.
- Executable SHA-256:
  `d262351a52566b9b4a29386ad32773f3a17580b8291ce68b4e4c5b3714ba1a16`.
- Prerequisites applied: `PS-PLAT-000`, `PS-MYOPP-001`.
- Forward apply: 73 objects created.
- Idempotent reapply: object inventory and ledger unchanged.
- Verifier: `PS-MYOPP-002_criteria_state_verify.sql returned verified = 1`.
- Rollback rehearsal: 73 objects reversed and the target ledger row removed.
- Forward after rollback: target ledger row restored.
- Registry proof: written by `govern_sql_migrations.py --update-registry` only
  after the complete gate passed.
- Cleanup: exact delete exited 0; the first exact post-delete `az sql db show`
  returned `ResourceNotFound`; total attempt time was 1.34 minutes.

No production or staging database was connected to or changed. No persistent
infrastructure remains.

## Review and release state

Claude Opus independent reviewer session
`8f7b703c-9a6e-4d5f-95f7-6d113138b09b` reviewed exact pushed candidate
`41af22defb479834f5758b7ddd31a819b0dd2545` read-only in the authoritative
Azure environment and returned **PASS**. No blocking or important finding
remains. Two minor future observations were explicitly nonblocking and require
no C3 candidate change. The reviewer made no repository mutation.

The paired receipt is
`docs/governance/lane_claims/receipts/PS-MYOPP-CRITERIA-001.json`. This receipt
and this runtime-inert evidence tail are the only changes after the reviewed
candidate. No implementation, migration, verifier, registry gate, package
record, route, UI, provider, retrieval, search, deployment, enablement,
staging, or production byte changed after review.

At receipt creation, no PR, CI, merge, production schema apply, deployment,
enablement, or live claim had occurred. The exact reviewed SHA is eligible for
the governed merge preflight; repository merge remains separate from every
production operation.
