# PS-REPOSITORY-RATIONALIZATION-001 completion record

## Core record

- **Task/package and delivery path:** `PS-REPOSITORY-RATIONALIZATION-001`;
  Protected because this slice removes tracked secondary evidence copies.
- **Outcome and member/site effect:** the repository now has a complete
  non-authoritative registry for all 113 initiative directories, corrected
  status framing for eight stale or mixed packages, an evidence retention and
  exact-deduplication standard, and a deterministic recurrence check. No
  application-runtime source or intended member-facing behavior changed. The
  implementation merge did advance the deployed application release through
  automatic main run 1027, as recorded below.
- **Branch and base:**
  `work/2026-08-13-repository-rationalization-001`, based on
  `fdb71c604f81d305b971775bd28aeac964231ebe`.
- **Activation evidence:** activation PR 472 was squash-merged as
  `fdb71c604f81d305b971775bd28aeac964231ebe`; required build 1023 succeeded.
- **Changed paths:** governance registry/retention files; the package README
  and this record; eight initiative status banners; two Community candidate
  manifests; the OS-4 canonical evidence map; the approved exact duplicate
  deletion set; the recurrence checker and focused tests.
- **Release state:** implementation candidate
  `08eed8f14cce53cd543ac9b7922e7daa2335b3e4` passed required build 1026 and
  merged through PR 473 as
  `eea1293a80091b8f19229a47782b5c2222e7ec32`. Delayed automatic main run 1027
  succeeded, including the production application stage. Live `/healthz`
  returned HTTP 200 with release `8f30f3770dc1d8a6a440da94`. The governed
  pause passed build 1028 and merged through PR 474 as
  `28445244346385361470b465337c1c934bf6903d`. Release-truth correction
  activation PR 475 passed build 1031 and merged as
  `207f1e33213daac3b366990201c1e85852eb3d32` with an explicit `[skip ci]`
  squash message.
- **Known limits and deferred work:** the registry is an index, not lifecycle
  authority. `CURRENT_LANES.json` and `CURRENT_BASELINE.yaml` remain
  authoritative. Runtime asset retirement, package implementation, product
  redesign, production operations, and live verification are outside this
  slice.
- **Next action:** finish this documentation-only truth correction and inert
  pause with explicit `[skip ci]` squash messages. No rollback or additional
  runtime release is required: run 1027 succeeded and the rationalization
  changed no application-runtime source.

## Exact evidence reduction

The repository was scanned by content hash before and after the approved
deletion set:

| Measure | Before | After | Reduction |
|---|---:|---:|---:|
| Files scanned | 2,202 | 2,169 | 33 net |
| Exact duplicate groups | 74 | 43 | 31 |
| Extra duplicate instances | 81 | 46 | 35 |
| Exact duplicate bytes | 112,734,481 | 14,836,517 | 97,897,964 |

The net file reduction is 33 because 35 secondary PNG copies were removed and
two new evidence files under the scan roots were added. The 35 removals were:

- 25 OS-4 artifact-side PNG copies totaling 83,938,230 bytes, with exact
  canonical copies retained under
  `docs/initiatives/PS-OPPORTUNITY-SLATE-001/evidence/os-4/`;
- six Community public-pilot candidate PNG copies retained in the accepted
  Community visual authority; and
- four Community completion-candidate PNG copies retained in that authority.

Ten unique OS-4 HTML captures and two unique Community completion-candidate
PNGs remain in their original locations. The full OS-4 path/hash/size mapping
is in `artifacts/2026-08-04-os4/CANONICAL_EVIDENCE.md`; the Community manifests
point to the accepted canonical authority.

Two large exact-duplicate groups remain intentionally and are documented in
`docs/governance/EVIDENCE_DUPLICATE_ALLOWLIST.json`: OS-3 default/reduced-motion
parity evidence and a Workshop image promoted into accepted Community visual
authority.

## Verification

- `python scripts/check_repository_evidence_policy.py --json`: Pass; the only
  duplicate groups at or above 1,000,000 bytes are the two exact allowlisted
  groups.
- `python -m unittest tests.test_package_registry
  tests.test_repository_evidence_policy`: Pass; four tests.
- `python -m unittest tests.test_package_registry
  tests.test_repository_evidence_policy tests.test_governance_pointers`: Pass;
  25 tests.
- Registry completeness: Pass; every one of the 113 initiative directories is
  represented exactly once.
- Canonical retention: Pass; each deleted path was checked against an existing
  retained path by SHA-256 and byte count before deletion. All 25 retained
  OS-4 screenshots, ten unique OS-4 HTML captures, and 12 Community manifest
  entries also match their recorded hashes and sizes.
- `git diff --check`: Pass.

## Protected additions

- **Deletion and rollback:** only exact secondary copies were removed. Every
  retained canonical file is present, and every removed file remains
  recoverable from Git history. No unique evidence, accepted authority,
  release/incident/migration proof, legal/privacy/security evidence, sealed
  handoff, member data, branch, stash, worktree content, or recovery ref was
  removed.
- **Shared infrastructure:** the source change contained no runtime, route,
  schema, migration, configuration, dependency, pipeline, or production-data
  mutation. Run 1027 nevertheless built and deployed the production
  application because PR 473's squash message lacked `[skip ci]`. The
  production application stage and `DeployWebApp` job succeeded; schema apply,
  isolated candidate, maintenance, and candidate-stop stages were skipped.
  Live health returned 200. `artifacts/` is excluded from the deployment
  package, while `docs/` is retained for live Control Room and knowledge
  readers. A rollback is not indicated because the deployment succeeded and
  carried no application-runtime source change. Follow-up control merges use
  explicit `[skip ci]` merge messages.
- **Material visual work:** none. Accepted visual authority was preserved
  byte-for-byte; this slice only removes redundant copies and corrects
  pointers.
