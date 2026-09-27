# PeerSlate Completion Record

Use once per slice as a release fact record. Add protected fields only when
triggered.

## Core record

- Task/package and delivery path: Routine / Bounded / Protected
- Outcome and member/site effect:
- Package manager and why (ChatGPT Work yes/no when relevant):
- Triggered specialists and return target:
- Root/selected child session IDs, configured model/effort, effective settings
  or `unavailable`:
- Optional local usage: input, cached-input subset, output, reasoning-output
  subset already included in output, or unavailable reason. Never a live-usage,
  quota, billing, price, invoice, or merge-gate claim:
- Observed elapsed time and known waiting, with sources. Never infer waiting
  from silence, gaps, or tokens:
- Accepted outcome, rework, interventions, with evidence pointers or
  `unavailable`:
- Branch, base SHA, final SHA, and changed paths:
- Verification performed and result:
- Package acceptance: criterion/source mapping and
  `python -B scripts/package_acceptance.py check --package <PACKAGE-ID> --candidate <REVIEWED-SHA>`
  result; or explicit `--read-only` skip. Incomplete is not accepted.
- Release state: local only / PR / merged / pipeline verified / live verified
- Dependency/custody: owner, state, release condition, control-window sequence.
- Delivery state: active / paused / held / scope-release-frozen /
  scope-sync-required / reconciliation-refresh-required. Distinguish hold
  policy from claim pause.
- Known limits, deferred work, or owner decision needed:
- Next action (or `None`):

## Protected additions - only when applicable

- **Data, identity, privacy, authorization, deletion, publication, or AI:**
  contract changed, threat/risk review, migration or rollback proof, and
  permission/negative-path evidence.
- **Material visual work:** exact locked visual authority, relevant
  accessibility/reflow evidence, comparison result, and owner visual decision.
- **Shared infrastructure or broad release:** deployment/rollback evidence,
  monitoring/operational owner, and independent review when the package
  requires it.
- **Actual handoff:** receiving owner, exact pushed SHA, open finding, and
  explicit relinquishment.

State `Conditional` or `Fail` if a required applicable check is unresolved.
Do not imply that a fixture is live, a merge is deployed, or an AI proposal is
accepted without evidence.
