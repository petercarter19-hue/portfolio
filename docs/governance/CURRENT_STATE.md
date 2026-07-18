# PeerSlate — Current State

_Last updated: 2026-07-18 · Sources: Roadmap v2.3 Appendix D + live repository inspection._
_Supersede this file after every production-changing merge (rule PS-GOV-001-R02)._

## Production baseline
- Authoritative remote: **origin** (Azure DevOps). GitHub is a backup mirror only.
- Branch / commit: **main @ d5dd7bd** (`d5dd7bdacc52b7324cb679c6c936eb1ff517ab28`).
- Pipeline: **78 green**. Live URL: **https://peerslate.com**. Theme: **Deep Navy Gold**.
- Open PRs at baseline: none.

## What is real and reusable — do NOT rebuild
- **Identity (PS-AUTH-001)** — email/password, email OTP, Google, Microsoft personal; owner bootstrap; opaque UUID; private-by-default; forged-header rejection; verified two-owner isolation.
- **Owner Settings (PS-OWNER-001 slice 1)** — protected `/app/settings` with account information and sign-out.
- **Private text Capture (PS-CAPTURE-001)** — protected composer, recent-owner list, `dbo.captures`, owner-resolving procedures, validation, audit-safe logs, tests, migration, production verification.
- **Deep Navy Gold (PS-THEME-001 / PR 58)** — shared owner theme shipped without breaking Capture or Settings. Five approved owner storyboards are the controlling owner dark-theme visual baseline: `docs/governance/approved_owner_visual_baseline/`.

## On hold
- **PS-JOURNAL-001 (Journal UI)** — explicit owner decision ("hold off on the journal"). Backend contracts may stay Journal-ready; no Journal UI work until the owner restarts it.

## Phase status (Roadmap v2.3, evidence-based — polish is not proof)
| Phase | Status | Next gate |
|---|---|---|
| 0 · Program reset / current-state audit | In Definition | Approve PS-GOV-001 + PS-BASELINE-001 |
| 1 · Website + language consolidation | In Build | Release résumé refine, then Studio gate |
| 2 · Identity / environments / delivery safety | In Verification | Close residual environment/secret/telemetry controls |
| 3 · Canonical data / migrations / authz / media | In Build | Baseline + build PS-CAPTURE-002 |
| 4 · Owner shell + viewer modes | In Build | Decide after Moment/placement, or in a parallel lane |
| 5 · Universal Capture + private Journal | In Build | PS-CAPTURE-002 → PS-MOMENT-001 → PS-PLACEMENT-001 |
| 6–12 | Planned / Not Assessed | Later, each separately gated |

## Test & release safety
- Guardrail suites **`tests/test_site_rules.py`** and **`tests/test_governance_pointers.py`** must stay green.
- Deployment is **Azure Pipelines only** (`azure-pipelines.yml`, `docs/AZURE_DEVOPS_DEPLOYMENT_RUNBOOK.md`). GitHub Actions deployment is intentionally disabled.
- Never claim a change is live until the Azure pipeline succeeds and `https://peerslate.com` is verified.
