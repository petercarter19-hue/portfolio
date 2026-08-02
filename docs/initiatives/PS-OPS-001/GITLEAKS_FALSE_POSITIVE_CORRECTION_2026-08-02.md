# Gitleaks false-positive correction - 2026-08-02

## Completion and risk record

- **Path:** Protected shared-infrastructure correction under `PS-OPS-001`.
- **Branch/base:** `codex/2026-08-02-gitleaks-history-fingerprint-unblock`
  from authoritative `2126928ec8dcd704ad278a509da1c3102a5af854`.
  The exact local final SHA is reported in the handoff because a commit cannot
  embed its own SHA.
- **Outcome:** three `generic-api-key` false positives are suppressed only
  when rule, one exact historical commit, one anchored path, and one anchored
  harmless source line all match. Each exception uses its own `AND` allowlist;
  no commit or path is allowlisted by itself.
- **Changed paths:** `.gitleaks.toml`, the focused configuration regression in
  `tests/test_operational_readiness.py`, and this record. No runtime,
  deployment YAML, credential, provider, application setting, data, identity,
  or production resource changes.
- **Release state:** source-branch correction only; not merged, deployed, or
  live. Exact branch-build and PR state are reported in the SHA-specific
  handoff and Azure records.

## Cause and credential assessment

Main build 340 (`20260802.15`) checked out exact source
`efb0b5f846a87ac8132e8d5b90dca628b040ac1e` after PR 237 and failed the
redacted full-history Gitleaks step with two findings. PR 237 was an Azure
squash merge, so those Community commits are not ancestors of that main SHA.
The clean Azure checkout first fetched all remote heads, and Gitleaks scanned
all fetched refs; the still-active Community branch therefore remained in the
scanner graph. After that branch advanced, the current graph contained a third
false positive in its evidence prose.

Inspection at the three exact commits established that no credential exists:

- two findings are the same serializer call that passes the local cursor
  parameter with a fixed expiry constant; and
- one finding is a plain-English protected-cleanup sentence in a Markdown
  evidence record.

The findings contain source identifiers/prose, not a credential, connection
string, deployable secret, or literal cursor-token value. No secret value was
printed during pipeline-log or report inspection.

PR 239 attempted to unblock the scanner but omitted `condition = "AND"`.
Gitleaks 8.30.1 defaults multiple allowlist criteria to `OR`, so that version
allowed whole commits or paths independently. This correction removes that
broad suppression and uses three non-combinable conjunctive entries.

## Verification, limits, and rollback

Verification covers the checksum-pinned Gitleaks 8.30.1 binary/config, the
full local all-ref graph after a current `origin` fetch, exact TOML structure,
and negative controls showing that the same detector still reports a match
when any required dimension is absent:

- the pipeline's pinned Linux archive SHA-256 matched the official 8.30.1
  checksum and a fresh download; the independently downloaded Windows archive
  also matched its official checksum and reported executable version 8.30.1;
- the pre-correction control config found the three exact false positives in
  the full local all-ref graph after a current `origin` fetch; after the local
  correction series was rewritten into one commit, the corrected exact tip
  scanned the updated graph with zero findings (exact SHA and commit count are
  reported in the handoff);
- one synthetic unlisted commit reproduced both harmless patterns at their
  listed paths and at alternate paths; all four findings remained detectable;
- the focused operational suite passed 22 tests, including the exact TOML
  regression;
- the full repository suite passed 1,374 tests with 4 environment-dependent
  skips after supplying the required non-secret test placeholder. The first
  invocation omitted that placeholder and was invalid at test discovery, not
  a product failure; and
- dependency compatibility, compilation of the changed test, and
  `git diff --check` passed.

Gitleaks retained its pre-existing non-fatal extraction warning for one
historical truncated DOCX. The scanner completed the graph and returned the
expected finding/exit results; this correction does not change archive
extraction behavior.

A safe rollback restores the exact pre-PR-239 config, which has no Community
exceptions and therefore fails closed on the historical findings. That can be
done by reverting both PR 239's config change and this correction; reverting
only this correction is forbidden because it would resurrect PR 239's broad
`OR` suppression. Rollback is source-only and needs no application or data
recovery. The narrow exceptions should be removed only when the corresponding
historical refs are no longer scanned or the detector no longer classifies the
exact lines as findings. Any broader scanner-graph change is a separate PS-OPS
decision.

**Result:** `Pass` for the correction and complete-diff self-review. Fresh
protected-path review passed at patch-equivalent source
`8b96e13385bb2cbe3e802a903a4e85b05d66db94`; the later authoritative-base
refresh preserved the config/test patch and changed only this provenance.
Release remains separate. Production remains unchanged.
