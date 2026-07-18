# PeerSlate — Current State

_Verified 2026-07-18 by PS-BASELINE-001. Repository facts are a snapshot; every writer must fetch `origin` before starting._

## Verified production and repository baseline

- `origin` is Azure DevOps and the only source of truth. `github` is a backup mirror whose pushes are on hold.
- The audit started from `origin/main @ ec6eae83feedff45d8fe87600e1031253cfd6021`, the squash merge of Azure PR 59 (PS-GOV-001).
- Azure pipeline 79 succeeded for that commit. The last application-behavior change remains `d5dd7bdacc52b7324cb679c6c936eb1ff517ab28`; PR 59 changed governance only.
- PS-BASELINE-001 then squash-merged through Azure PR 60 at `89c8797b498a411f426e5e0efd042d0816996adf`; automatic pipeline 80 succeeded. That merge also changed governance only. Fetch `origin` for the exact current tip rather than treating any recorded SHA as a substitute for synchronization.
- Production probes returned 200 for `/`, `/petec/resume`, and `/interview-studio`. `/petec/resume2` redirected to `/petec/resume`. `/app/capture` and `/app/settings` redirected unauthenticated requests to sign-in.
- The approved shared theme is Deep Navy Gold.
- There were no active Azure pull requests when the audit began.

## Real and reusable — do not rebuild

- **Identity (PS-AUTH-001):** external identity, owner sessions, opaque owner IDs, and two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1):** protected `/app/settings` and sign-out.
- **Private text Capture (PS-CAPTURE-001):** protected create/list experience backed by `dbo.captures`, owner-derived database procedures, validation, privacy-safe logging, migration evidence, and tests.
- **Public résumé:** canonical `/petec/resume`, existing redirects, download path, Ask Pete AI hooks, and the shared résumé dataset.
- **Interview Studio public slice:** a public browser-local practice experience. It is not an authenticated private history system.
- **Deep Navy Gold (PS-THEME-001):** shared owner visual foundation and approved mockups under `docs/governance/approved_owner_visual_baseline/`.

## Manager and delivery lanes

ChatGPT Work is the owner-designated manager. It maintains repository truth, sequences packages, reviews handoffs, and verifies merges and releases. ChatGPT Codex owns backend convergence. Claude Code owns assigned public front-end work. Each package has one writer, one short-lived branch, and a separate file reservation.

Two packages are prepared to start in parallel from the same post-baseline `origin/main`:

1. **PS-CAPTURE-002 — ChatGPT Codex:** correction, archive/restore, explicit delete, and per-capture export over the existing private source.
2. **PS-RESUME-PUBLIC-REFINE-001 — Claude Code:** shorten and clarify the public résumé's default scan through hierarchy and progressive disclosure without a data fork.

Interview Studio refinement is deliberately not bundled into the résumé package. It waits for PS-INTERVIEW-PUBLIC-GATE-001 so its public/private route and identity boundary can be handled separately.

## Roadmap position

| Area | Evidence state | Next gate |
|---|---|---|
| Governance and baseline | Complete through PS-BASELINE-001 | Keep records synchronized at each handoff |
| Public résumé | Shipped; refinement prepared | PS-RESUME-PUBLIC-REFINE-001 |
| Interview Studio | Public slice shipped | Separate route/private-practice gate after résumé |
| Capture | Private create/list shipped | PS-CAPTURE-002 lifecycle |
| Canonical Moment | Not implemented | Start only after Capture lifecycle is verified |
| Placement references | Not implemented | Start only after Moment boundary is verified |
| Journal UI | On hold | Owner must explicitly restart it |

## Honest boundaries

- No Capture correction, archive/restore, delete, or export is claimed live yet.
- No canonical Moment or placement-reference model is implemented yet.
- No private Interview Studio history is claimed on the public route.
- No second résumé dataset, Journal UI, authentication rewrite, or public navigation/theme redesign is authorized in the active wave.
- The GitHub mirror is not current and must not be used as a release source.

## Required release evidence

Both guardrail suites, package-focused tests, and the Azure pipeline must pass. A package is not “live” until its Azure squash merge is deployed and the affected production boundary is verified.
