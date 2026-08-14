# PS-REPOSITORY-RATIONALIZATION-001 completion record

## Core record

- **Task/package and delivery path:** `PS-REPOSITORY-RATIONALIZATION-001`;
  Protected because this slice removes tracked secondary evidence copies.
- **Outcome and member/site effect:** the repository now has a complete
  non-authoritative registry for all 113 initiative directories, corrected
  status framing for eight stale or mixed packages, an evidence retention and
  exact-deduplication standard, and a deterministic recurrence check. This
  changes no member-facing behavior or live site state.
- **Branch and base:**
  `work/2026-08-13-repository-rationalization-001`, based on
  `fdb71c604f81d305b971775bd28aeac964231ebe`.
- **Activation evidence:** activation PR 472 was squash-merged as
  `fdb71c604f81d305b971775bd28aeac964231ebe`; required build 1023 succeeded.
- **Changed paths:** governance registry/retention files; the package README
  and this record; eight initiative status banners; two Community candidate
  manifests; the OS-4 canonical evidence map; the approved exact duplicate
  deletion set; the recurrence checker and focused tests.
- **Release state:** the implementation candidate is locally validated and is
  delivered only through the normal Azure PR policy. The exact PR, build,
  merge, and inert lifecycle disposition are recorded in the current control
  plane and the August 13 audit companion. Nothing was deployed.
- **Known limits and deferred work:** the registry is an index, not lifecycle
  authority. `CURRENT_LANES.json` and `CURRENT_BASELINE.yaml` remain
  authoritative. Runtime asset retirement, package implementation, product
  redesign, production operations, and live verification are outside this
  slice.
- **Next action:** follow the current lane control plane. No runtime release is
  required or authorized by this package.

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
- **Shared infrastructure:** no runtime, route, schema, migration,
  configuration, dependency, pipeline, deployment, production-data, or live
  state changed. Deployment and rollback evidence do not apply.
- **Material visual work:** none. Accepted visual authority was preserved
  byte-for-byte; this slice only removes redundant copies and corrects
  pointers.
