# PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001

## Status

- Stage: Sonnet 5 writer finish complete (Chrome cross-platform fix, evidence
  rebuild, and record refresh); pending Pete visual review; see
  `ROLE_ROUTING_NOTE_2026-07-22.md` and `IMPLEMENTATION_COMPLETION_REPORT.md`
- Release state: unmerged, undeployed, and disabled
- Azure base: `e1272220f539f41810698855341b9399b14ebd73`
- Integration branch: `work/2026-07-22-community-journal-home-milestone-integration`
- Designated session manager: Fable for the 2026-07-22 session (re-routed from
  the earlier Codex-manager assignment; see `ROLE_ROUTING_NOTE_2026-07-22.md`)
- Rendered-product commit (P): `ed533acd2b89bb7458b64a047b1b6199ddb423c0`
- Next receiver: Pete visual review, then one independent Opus review, then
  one Claude Code final technical audit (re-routed from the contract's
  independent-Sol-High / three-Sol-Ultra chain; see
  `ROLE_ROUTING_NOTE_2026-07-22.md`)

## Purpose

This package creates one controlled Azure integration boundary for the already
owner-approved Community, Journal J1, and Owner Home source packages. It exists
to preserve their exact source histories, resolve their shared
`templates/base.html` seam once, and give three independent Sol Ultra auditors
one identical milestone SHA to inspect.

Pete's explicit 2026-07-22 authorization of this combined package is the
package-local owner exception required by the older instruction not to mix
Journal and Owner Home without a newly approved package. The exception does not
authorize redesign, feature activation, SQL execution, deployment, or unrelated
work.

## Fixed source inputs

| Package | Azure source branch | Exact required source SHA |
| --- | --- | --- |
| Community | `work/2026-07-21-community-tabs-impl` | `a8c04964a5a363d47a56829da01c9a5bfefe3653` |
| Journal J1 | `work/2026-07-21-journal-frontend-j1-impl` | `099e8e1582c05d3e13fd54dacfeb03700f90ae09` |
| Owner Home | `work/2026-07-21-home-frontend-001-impl` | `f8c882633f6e442a4f661b67f8d3c799a66a1989` |

The binding instructions are in
`INTEGRATION_ARCHITECTURE_CONTRACT.md`. The architecture closeout is in
`ARCHITECTURE_COMPLETION_REPORT.md`.

Pete's binding 2026-07-22 decision to defer Journal J1 playback is recorded in
`J1_PLAYBACK_DECISION_2026-07-22.md`. J1 keeps an honest disabled
`Coming later` composition; working owner-media playback requires a separate
future package.

Pete's 2026-07-22 re-routing of the session-manager, writer, and reviewer
roles named in `INTEGRATION_ARCHITECTURE_CONTRACT.md` is recorded in
`ROLE_ROUTING_NOTE_2026-07-22.md`. The contract's original "Terra" / "Sol
High" / "Sol Ultra" text is left unchanged as a historical record; the note
states which role performs each of those steps for this package's finish.

## Hard boundaries

- Azure DevOps `origin` remains the sole release authority.
- `PEERSLATE_JOURNAL_ENABLED=false` and
  `PEERSLATE_OWNER_HOME_ENABLED=false` remain unchanged.
- The integration and its required correction evidence are present on this
  branch; the feature flags remain default-off.
- No shared governance pointer, migration SQL, deployment, feature activation,
  production verification, or GitHub-forward movement is in scope.
- One Terra High writer owns the branch during implementation, followed by the
  exact review and audit sequence defined in the contract.
