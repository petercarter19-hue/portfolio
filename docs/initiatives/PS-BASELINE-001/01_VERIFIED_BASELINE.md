# PS-BASELINE-001 — Verified Evidence Baseline

_Observed 2026-07-18 before this package changed repository records._

## Repository and delivery

| Evidence | Verified value |
|---|---|
| Authoritative remote | `origin` on Azure DevOps |
| Authoritative branch | `main` |
| Starting main commit | `ec6eae83feedff45d8fe87600e1031253cfd6021` |
| Governance PR | Azure PR 59, completed |
| Governance source SHA | `4cb0b0b914035ef395785ffb0a7f663685c48d50` |
| Last verified Azure pipeline | 79 / `20260718.2`, succeeded |
| Last app-behavior commit | `d5dd7bdacc52b7324cb679c6c936eb1ff517ab28` |
| Active Azure PRs at audit | None |
| GitHub mirror | Backup only; observed behind at `d5dd7bd...`; pushes on hold |

## Production probes

| Route | Observed boundary |
|---|---|
| `/` | 200 |
| `/petec/resume` | 200 |
| `/petec/resume2` | 302 to `/petec/resume` |
| `/interview-studio` | 200 public experience |
| `/app/capture` | 302 to sign-in when unauthenticated |
| `/app/settings` | 302 to sign-in when unauthenticated |

These probes prove reachability and route protection only. They do not prove authenticated Capture lifecycle behavior, because that lifecycle does not exist yet.

## Local-work protection

The original checkout was already on the merged PS-GOV-001 task branch and contained an untracked setup script. It was not switched, cleaned, deleted, staged, or edited. PS-BASELINE-001 used a separate clean worktree.
