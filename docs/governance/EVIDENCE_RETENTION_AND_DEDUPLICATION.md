# Evidence retention and deduplication

## Purpose

PeerSlate keeps evidence that proves product authority, trust decisions,
release history, recovery, and current behavior. It keeps the smallest useful
canonical proof in Git and stores bulky reproducible or generated evidence once
when repository replication would add material cost.

This standard governs tracked files under `docs/initiatives/` and `artifacts/`.
It does not authorize deletion, migration of existing evidence, or removal of
Git history by itself.

## Retention order

When exact copies exist, retain the location with the strongest durable role:

1. Pete-accepted visual authority and its hash manifest;
2. package-local release, migration, authorization, incident, legal, privacy,
   security, rollback, or recovery evidence;
3. unique candidate evidence needed to explain a decision;
4. transient comparison and capture artifacts.

One canonical file may serve multiple packages through explicit relative
pointers. A pointer records the canonical path, SHA-256, byte length, and why
the secondary path no longer carries a copy.

## Never deduplicate automatically

- unique bytes, even when filenames or screenshots look similar;
- accepted authority without a byte-verified retained replacement;
- applied or proposed migration and rollback evidence;
- release, incident, security, legal, privacy, or authorization proof;
- sealed or externally delivered self-contained handoffs;
- user-authored, production, secret, local-only, dirty, or ambiguous content;
- files with different semantic roles unless the allowlist documents why both
  names must remain.

Runtime and dormant-asset retirement is a separate Gate Retire decision. It is
never inferred from this evidence policy.

## Large exact-duplicate rule

The repository check scans files under `docs/initiatives/` and `artifacts/`.
An exact SHA-256 group with files of at least 1,000,000 bytes fails unless
`EVIDENCE_DUPLICATE_ALLOWLIST.json` names the complete group, one canonical
path, every retained duplicate path, and a meaningful retention rationale.

The allowlist is for intentional evidence topology, not convenience. Adding a
new path to an existing hash group without updating and reviewing the complete
group fails. This existing whole-tree duplicate check remains unchanged.

## Prospective generated-evidence rule

The storage rule is diff-only. It applies to evidence files added under
`docs/initiatives/` or `artifacts/` and to storage manifests added or changed by
the current branch. It does not demand manifests for unchanged historical
evidence.

- Inventory every newly added evidence file of at least 1,000,000 bytes in the
  nearest ancestor `EVIDENCE_STORAGE_MANIFEST.json`.
- Keep the smallest useful canonical proof in Git. The proof must be a regular
  repository file below the manifest directory with verified bytes and SHA-256.
- Add all raw, intermediate, reproducible, or bulky generated items to one
  complete per-item SHA-256 ledger.
- Compute replication cost as `declared_set_bytes` multiplied by the greatest
  of the current full-worktree count, projected full-worktree count, and any
  observed count supplied to the checker.
- When replication cost is at least 1 GiB (1,073,741,824 bytes), `external` is
  the default storage mode.
- `repo_canonical` above that trigger requires a meaningful rationale and a
  durable independent-review reference in `repository_exception`.
- External custody requires an immutable coordinate, complete item count and
  bytes, source/base/final Git SHAs, UTC verification time, named retention and
  recovery owners, and `complete_verified: true`.
- Azure may not be the sole copy unless retention is explicitly pinned and the
  pinned retention policy has a durable reference.

The 1 GiB test is a storage default, not deletion authority. A reviewer may
accept a documented repository exception when runnable, legal, incident,
security, migration, or recovery proof genuinely needs repository custody.

## `EVIDENCE_STORAGE_MANIFEST.json` schema version 1

Place one manifest at the root of each generated evidence set. Repository paths
use forward slashes and stay below that manifest directory. For external
storage, item paths are relative keys below `immutable_coordinate`; the
repository proof remains a repository-relative path.

```json
{
  "schema_version": 1,
  "evidence_set_id": "PS-PACKAGE-001/candidate-2026-08-23",
  "generated": true,
  "storage_mode": "external",
  "declared_set_bytes": 250288380,
  "declared_item_count": 1,
  "worktree_count": {
    "current_full": 61,
    "projected_full": 61
  },
  "source_sha": "1111111111111111111111111111111111111111",
  "base_sha": "2222222222222222222222222222222222222222",
  "final_sha": "3333333333333333333333333333333333333333",
  "verified_at": "2026-08-23T12:00:00Z",
  "retention_owner": "PeerSlate package owner",
  "recovery_owner": "PeerSlate repository owner",
  "complete_verified": true,
  "repository_proof": {
    "path": "docs/initiatives/PS-PACKAGE-001/evidence/candidate-2026-08-23/SUMMARY.md",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "bytes": 2841
  },
  "items": [
    {
      "path": "captures/desktop-home.png",
      "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "bytes": 250288380
    }
  ],
  "external_custody": {
    "provider": "azure_devops",
    "immutable_coordinate": "azure://peerslate/build/1234/artifact/candidate-evidence",
    "sole_custody": true,
    "retention_pinned": true,
    "retention_policy_ref": "azure-retention:permanent-evidence-v1"
  },
  "repository_exception": null
}
```

Required semantics:

- `schema_version` is exactly `1`; `generated` is exactly `true`.
- `storage_mode` is `repo_canonical` or `external`.
- `declared_set_bytes` equals the sum of every item `bytes` value, and
  `declared_item_count` equals the ledger length.
- Every item has a unique safe relative `path`, a lowercase 64-character
  `sha256`, and a non-negative integer `bytes` value.
- `source_sha`, `base_sha`, and `final_sha` are lowercase 40-character Git SHAs
  for the source input, comparison base, and evidence-generating final state.
  They are evidence provenance; `final_sha` need not be the later manifest
  commit itself.
- `verified_at` is an ISO-8601 UTC timestamp ending in `Z`.
- `retention_owner` and `recovery_owner` identify accountable roles or people;
  `complete_verified` confirms the count, total bytes, and hashes were checked.
- `repository_proof` records the actual repository-relative path, SHA-256, and
  byte length of the smallest useful proof retained in Git.
- For `repo_canonical`, every ledger path names an actual file below the
  manifest, hashes and sizes are verified, `repository_proof` matches one
  ledger item, and `external_custody` is null.
- For `external`, ledger paths are external keys, `external_custody` is
  required, and `repository_exception` is null.
- `repository_exception`, when the 1 GiB trigger is crossed, contains
  `rationale` of at least 40 characters and a durable `review_ref`.

Unknown additive fields are permitted so a package may record provider-specific
recovery details without changing schema version 1. Required fields and their
meaning may not be redefined within schema version 1.

## Validation

The existing command remains compatible:

```bash
python scripts/check_repository_evidence_policy.py --json
```

It uses the Azure pull-request target when available, then `origin/main`, then
`HEAD^`, and includes untracked files. For deterministic local or CI checks,
name the comparison base explicitly:

```bash
python scripts/check_repository_evidence_policy.py --base-ref origin/main --full-worktree-count 61 --json
```

Tests and narrow tooling may supply `--changed-path` and `--added-path`
repeatedly instead of consulting Git. When only `--changed-path` is supplied,
those paths are treated as additions. Manifest validation is deliberately
limited to changed manifests and manifests governing newly added files.

## External recovery check

Before accepting an external manifest:

1. retrieve the immutable coordinate without relying on a mutable “latest”
   alias;
2. verify every ledger item SHA-256 and byte length;
3. verify item count and total bytes;
4. open the repository proof and confirm it identifies the same evidence set
   and source/base/final SHAs;
5. confirm the retention owner can preserve it and the recovery owner can
   retrieve it;
6. for Azure sole custody, confirm pinned retention independently of the build's
   ordinary expiry setting;
7. set `complete_verified` only after the entire ledger passes.

## Removal procedure

Before deleting a secondary copy:

1. verify exact SHA-256 equality and byte length;
2. select and preserve the canonical retained path;
3. search tracked readers, manifests, tests, and handoffs for the old path;
4. replace required references with a portable repository-relative pointer;
5. retain unique siblings in the same directory;
6. run the evidence-policy and package-registry checks;
7. record before/after duplicate groups, extra instances, and bytes;
8. deliver through the normal reviewed Azure pull-request path.

Do not rewrite published Git history simply to reduce clone size. Historical
objects remain recoverable through Git even after a tracked secondary path is
removed from the current tree.
