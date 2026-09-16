# Safe-custody authoritative claim-path repair

The accepted lifecycle capability check enumerated valid active claims from `origin/main` without attaching their actual Git paths, then passed them to `delivery_preflight.validate_claim_set`, which requires `_relative_path`. This made `reconcile-main start` refuse before journaling even with schema-4 index and schema-2 registry in place.

This candidate keeps default strict-live-claim snapshots raw for existing consumers. The capability check requests path-attached copies, keyed by the enumerated Git path, and still runs the actual delivery claim-set validator. Enumeration rejects a filename/package mismatch or duplicate package before any keyed collapse; a payload-supplied `_relative_path` cannot replace the enumerated path.

Temporary-Git adversarial coverage exercises the strict loader, schema-4/schema-2 capability check, actual validator, accepted-tool-byte gate, valid active claims, malformed JSON and claim data, wrong filename, forged path metadata, and duplicate-package masking. Focused six new cases passed. The full lifecycle suite passed 129 tests; affected delivery claim-validation and safe-custody claim suites passed 25 tests. AST parsing and diff whitespace checks passed.

Independent reviewer `agent:/root/production_guard_review` (configured `gpt-6-astra` High) returned PASS with no findings on exact implementation candidate `db0fd617fbf14187985581398eff54089c5fd31b` against accepted base `a8ed0ba7e198d7510f8ba66cdafab7d15fda6db7`. The reviewer independently ran 25 tests (23 safe-custody and two loader/snapshot regressions), and `git diff --check` passed. The receipt's `reviewed_at` value `2026-09-16T20:17:03Z` is the owning task's UTC time of recording this PASS, not a claim about the reviewer's exact execution/completion time.

This evidence update and matching receipt are fixed post-review metadata only; the reviewed lifecycle code and tests remain unchanged. The original `PS-DELIVERY-CONTRACTS-SAFE-CUSTODY-001` claim remains paused and its branch/checkpoint unchanged. Protected PR/CI/merge, dependency close, and any later parent reconciliation remain separate; production authority is withheld.
