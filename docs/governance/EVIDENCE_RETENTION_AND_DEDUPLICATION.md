# Evidence retention and deduplication

## Purpose

PeerSlate keeps evidence that proves product authority, trust decisions,
release history, recovery, and current behavior. It does not need multiple
unexplained byte-identical copies of large files to do that.

This standard governs tracked files under `docs/initiatives/` and
`artifacts/`. It does not authorize deletion by itself.

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
group fails.

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
