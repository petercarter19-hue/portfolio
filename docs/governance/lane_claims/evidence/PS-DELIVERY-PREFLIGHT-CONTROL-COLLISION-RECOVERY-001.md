# PS-DELIVERY-PREFLIGHT-CONTROL-COLLISION-RECOVERY-001 — completion evidence

Runtime-inert Protected delivery-control record. Production authority remains
withheld.

## Outcome

Read-only delivery preflight now reports existing active cross-claim path and
hierarchical-domain collisions as explicit non-authorizing warnings and facts.
It keeps malformed claims, branch collisions, and every other claim-set defect
fatal. Mutating admission remains fail-closed whenever the candidate claim set
contains any path or domain collision. A collision in the authoritative
pre-transition state becomes nonfatal only when the complete candidate claim
set has the same package keys and removes every such collision; the ordinary
intent-specific transition checks must still pass.

This lets an exact pause or close release colliding active ownership while
write, activation, authorization, surface extension, transfer, owner
reassignment, resume, merge, evidence errata, and every collision-preserving or
collision-creating transition remain blocked. Collision and structural errors
are constructed separately rather than classified from rendered text, so a
malformed package label cannot spoof a read warning.

## One-time bootstrap authority

- Owner decision:
  `pete-chat-2026-08-29/full-package-blocker-recovery-and-rules-must-not-deadlock`.
- Base: `dc3ea244377b7e00acf48897a641c0380a024fe9`.
- The Darwin package's required pre-edit read failed solely on its three
  already-active path collisions with the Windows child-runtime package.
- The disjoint claim-only recovery commit
  `b7fc04d5dc8006e1f2edf18fd36b8b8e72f84b03` then failed ordinary activation
  solely on those same collisions.
- `docs/governance/DECISIONS.md` records Pete's one-time authorization for this
  exact combined activation-and-implementation PR under the authority order in
  `DOCUMENT_CONTROL.md`. It is not a reusable bypass and does not claim the
  failed activation passed.

## Candidate and review

- Branch:
  `work/2026-08-29-delivery-activation-preflight-control-collision-recovery-001`.
- Writer: `agent:/root/preflight_collision_writer`.
- Reviewed candidate: `4499b99b121f1241dcae129ad3c519f545c7cc47`.
- Independent reviewer: `agent:/root/preflight_collision_reviewer`.
- Review evidence:
  `agent:/root/preflight_collision_reviewer/review:4499b99b121f1241dcae129ad3c519f545c7cc47`.
- Reviewed at: `2026-08-29T22:13:40Z`.
- Verdict: **PASS**, read-only, with zero P0-P3 findings.
- Earlier candidate `99768edaba9778737695d4dfc7e170adc18f7676` was
  independently rejected because rendered-prefix classification was spoofable.
  The writer accepted that P1, constructed structural errors and collision
  diagnostics separately, added both adversarial label cases, and refroze.

The reviewed candidate changes exactly:

- `START_HERE.md`
- `docs/governance/DECISIONS.md`
- `docs/governance/lane_claims/PS-DELIVERY-PREFLIGHT-CONTROL-COLLISION-RECOVERY-001.json`
- `scripts/delivery_preflight.py`
- `tests/test_delivery_preflight.py`

No broker, application runtime, identity, privacy, schema, configuration,
credential, deployment, external-operation, or live-operation file changed.

## Verification

- Focused collision and adversarial regression set — **7 tests passed; OK**.
- `python3 -m unittest -q tests.test_delivery_preflight` — **129 tests passed;
  OK**.
- `python3 -m py_compile scripts/delivery_preflight.py tests/test_delivery_preflight.py`
  — passed.
- `git diff --check` — passed.
- The exact Darwin `--intent read --fetch --require-clean` command passed on the
  reviewed candidate and reported the three existing overlapping broker paths
  as non-authorizing warnings/facts.
- Azure PR 736 build 1913 passed against source
  `4499b99b121f1241dcae129ad3c519f545c7cc47` and target
  `dc3ea244377b7e00acf48897a641c0380a024fe9`; its full repository discovery ran
  **4,553 tests successfully with 24 skipped**.
- A writer-invoked broad discovery from the intentionally sparse `_control`
  checkout was not a valid full-application run because application files and
  dependencies are deliberately absent there. It failed on those absent
  surfaces; the focused module and Azure's full checkout are the applicable
  evidence.

## Release state and boundaries

PR 736 is open with squash configured, source-branch retention, no
auto-complete, and no self-approval. At this evidence-tail state the package is
not merged, deployed, enabled, or live. The ordinary activation and merge
preflights cannot bootstrap a claim that is not yet on main; Pete's recorded
one-time decision admits only this exact independently reviewed combined PR.
After it merges, every ordinary package and control transition uses the normal
claim, worktree, preflight, review, and merge gates.

Automatic PR and main runs are CI-only. Production, schema, credential,
identity, broker, external-operation, and live-operation authority remain
withheld. Repository rollback, if required, is an ordinary reviewed revert of
the squash merge; there is no deployment or schema rollback in this package.
