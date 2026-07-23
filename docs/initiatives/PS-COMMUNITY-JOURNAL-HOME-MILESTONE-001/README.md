# PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001

## Status

- Stage: **CLOSED — released and verified live 2026-07-23.** See
  `RELEASE_CLOSEOUT_2026-07-23.md` for the complete release record, and
  `IMPLEMENTATION_COMPLETION_REPORT.md` for the writer finish.
- Release state: merged (Azure PR 161, squash `88d6f8fa…`; CI repair PR 162,
  `b426aea…`), deployed by pipeline run 221 (`20260723.4`, succeeded), and
  verified live. Community Feed / The Break are live;
  `PEERSLATE_JOURNAL_ENABLED` and `PEERSLATE_OWNER_HOME_ENABLED` remain
  `false` — Journal J1 and Owner Home are merged and dormant behind their
  activation gates.
- Azure base: `e1272220f539f41810698855341b9399b14ebd73`
- Rendered-product commit (P): `ed533acd2b89bb7458b64a047b1b6199ddb423c0`;
  evidence commit (E): `e3107ce72627a0b5960b7de9f9a8cee86fe3aa50`
- Review chain as executed: Sonnet 5 writer finish (Pass) → Pete visual
  acceptance (2026-07-23: Owner Home, Community, and Journal approved) →
  Claude Code final technical audit (Pass). The Opus review stage was waived
  by Pete on 2026-07-22; see `ROLE_ROUTING_NOTE_2026-07-22.md` §Post-audit
  addendum.

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
