# PS-HOME-FRONTEND-001 - Manager Activation and Evidence Disposition

## Decision

**Approved to activate after this governance branch releases through Azure.**

The released Owner Home backend is sufficient for the first finite frontend.
The frontend does not wait for a new backend package, but it also does not
pretend the backend supplies states that it does not represent.

## Activation decisions

### HFA1 - One writer

The separately assigned Codex frontend task is the sole implementation writer.
Claude Code, the Interview homepage writer, and the Photo lifecycle writer do
not share or continue its branch.

### HFA2 - Exact branch gate

The writer creates `work/2026-07-20-home-frontend-001` from exact
post-activation Azure `origin/main` only after the activation PR squash merge
and pipeline pass. It does not branch from stale local `main`, reuse another
worktree, or begin product edits on the manager branch.

### HFA3 - Contract remains finite

`owner-home.v1` is the complete first-release data authority. No frontend
fixture, query parameter, browser storage, JavaScript state, or duplicated
model may stand in for a missing server state. Unknown or unavailable server
data fails closed under the released contract.

### HFA4 - Evidence mismatch resolved by narrowing

The accepted review charter originally requested partial-failure, stale/`409`,
and restricted runtime screenshots. The released one-operation view model
cannot express those states: contract/database failures collapse to a complete
unavailable result, and there is no category-error, access-restriction, or
state-change response in the finite Home contract.

For the first release:

- real empty and maximum-populated results are required;
- complete unavailable/failure and actual retry/fresh-navigation recovery are
  required;
- exact flag-off fallback and unchanged non-Owner routes are required;
- truthful disabled `coming_later` availability is required;
- loading is captured only if a real navigation/retry produces it; and
- partial-failure, stale/`409`, and restricted runtime states are deferred.

The deferred exports remain useful future design authority. They are not
evidence that the current backend implements those states. A later backend
contract package must establish deterministic fields/outcomes, authorization,
tests, migration impact, and production proof before a later frontend may
render them as real.

This disposition supersedes only the conflicting first-release runtime rows in
the older evidence charter. It does not weaken responsive, accessibility,
privacy, finite-object, visual-parity, no-fabrication, no-store, flag-off, or
cross-route requirements.

### HFA5 - Visual authority remains binding

The accepted dark cinematic shell, exact alpine atmosphere, luminous ivory
stage, hierarchy, and Capture dominance remain the visual minimum. Only D1-D6
are approved deviations. Pete and the designated manager must accept the real
rendered desktop/mobile result before the implementation PR.

### HFA6 - Default-off release

Implementation and deployment keep `PEERSLATE_OWNER_HOME_ENABLED=false`.
Flag-on local/synthetic evidence proves the bounded interface; it is not
authorization for production member access. A later explicit decision controls
founding-alpha enablement.

### HFA7 - Lane separation

Owner Home frontend owns no homepage, Interview, Capture Photo, shared
governance, backend service, SQL, or `owner_routes.py` file. The accepted
`base.html` and `auth_routes.py` edits are narrow Owner Home conditionals and
must be inert elsewhere. Concurrent branches synchronize only through merged
`origin/main`, never by copying or blending worktrees.

## Entry checklist for the implementation writer

Before product edits, the writer reports:

1. exact current `origin/main` and green activation pipeline;
2. new branch/worktree and exact base SHA;
3. clean working tree and preserved unrelated state;
4. complete controlling-document read;
5. exact visual authority and alpine asset hash;
6. released `owner-home.v1` fields and error behavior;
7. exact writable/forbidden file list;
8. current Interview/Photo branch intersections; and
9. a single next action.

## Required closeout result

The writer returns a clean pushed branch, exact SHA/base, complete changed-file
list, focused/governance/site/full test results, Python/JavaScript/diff checks,
privacy and two-owner canaries, named visual evidence, a 20-row authority
comparison using only D1-D6, homepage-impact disposition, and self-certification.

No implementation PR opens before Pete and manager visual-product acceptance.
No production enablement occurs under this activation.
