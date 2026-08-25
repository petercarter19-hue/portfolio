# PS-CLOSED-CLAIM-EVIDENCE-ERRATA-001 — delivery evidence

Runtime-inert record. Protected path; independent review required and obtained
(ACCEPT, zero findings, at exact candidate `b9405d59`).

## Outcome

`delivery_preflight.py` gains one generic, fail-closed control-style
transition, **`evidence-errata`**: an owner-authorized amendment of an already
CLOSED package's one fixed runtime-inert `lane_claims/evidence` file, without
reopening or changing any claim. Before this, no sanctioned path existed —
`write` and `merge` require an active claim, `close` is terminal, and `resume`
applies only to `paused`. The motivating need is the Workshop B+C route-truth
evidence correction, deliberately NOT performed in this candidate; it happens
later, through this mechanism, as its own act.

## The gate

Admission requires ALL of: the package's authoritative origin/main claim is
`closed`; the branch claim and every other claim are byte-identical to
origin/main; the run comes from the leased `_control` singleton (purpose
`control`, exact task ref, the closed package) on a
`work/YYYY-MM-DD-delivery-evidence-errata-<slug>` branch with `--fetch` and
`--require-clean`; the branch delta is exactly the claim's single fixed
`evidence_surfaces` path; the branch is exactly one commit ahead of and zero
behind current origin/main; the path is one ordinary tracked `100644` blob at
both origin/main and the candidate; the amended file carries the exact marker
`<!-- evidence-errata-authorization: <owner-ref> -->` for a `REF_RE`-valid
`--owner-authorization-ref` that origin/main does not already contain; and the
owner reference is rejected on every other intent. Admitting that single
evidence-only PR is all the intent grants — it never deploys and never
modifies claim state.

## Verification

- 19 new `EvidenceErrataTests` (happy path plus every gate fail-closed),
  borrowing the existing evaluation harness by reference so no parent tests
  are duplicated; the tracked-blob helper additionally verified against the
  real repository.
- Full run: `test_delivery_preflight` (91), `test_governance_pointers`,
  `test_operational_readiness`, `test_site_rules`, `test_package_registry`,
  `test_production_operation_preflight` — **173 passed, 0 failed**. Hermetic:
  no real provider or database call.
- Docs: operating instructions in `START_HERE.md` §5 beside the other
  transitions; pointer bullet in `AGENTS.md`; `_control` lease note in
  `WORKTREE_LIFECYCLE.md`. `docs/AI_WORKFLOW.md` deliberately untouched at
  1098 words under its sub-1100 test cap; disclosed to and unchallenged by
  the independent reviewer.

## Honest limitations

- One pre-existing machine-local failure in `tests/test_worktree_lifecycle`
  (a PID assertion) fails identically with this candidate stashed and passes
  in CI; its file is not a claimed surface and was not touched.
- Merged is repository truth only. This package deploys nothing and changes
  no runtime behaviour; the preflight is repository tooling.
- The Workshop B+C evidence amendment itself remains NOT performed and awaits
  its own owner-authorized `evidence-errata` run after this merges.
