# PS-MYOPP-MEMBER-IMPORT-001 — candidate evidence

## Scope and authority

Owner outcome: Pete's confirmed registry handback and go
(`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/registry-handback-confirmed-go`,
claim `owner_outcome_ref`), within the recorded full-sequence directive.
Disposable-proof envelope: Pete's direct answer, reference
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-08-31/disposable-proof-envelope-c4-through-c9-yes-i-do`.
Repository authority `through_merge`; production authority withheld. No HTTP
route, fetch capability, member_url_fetch_service.py file, shared-inventory
promotion, deployment, enablement, or production/staging schema action.

## P-1 repository evidence

The permanent private member_import path: deterministic paste and
document-upload intake (PDF/DOCX/plain text, magic-byte admission), the
doc 06 s2 closed outcome states per stage (never AI), owner-scoped
provenance, identical not-found owner isolation, export and member delete via
body-removal tombstones (member-lifecycle and rights-at-point-of-use dual
retention), content-free audit (host class + reason code only), and the
prebuilt DISABLED service-level URL-fetch port (truthful url_fetch_unavailable;
member_url_fetch_service.py absent, stop-control tested) are implemented and
locked at the frozen candidate by 156 package tests (2 Linux-gated, skipped
on the macOS host) and the complete 5,423-test repository suite (26 skips),
all green with pypdf 6.16.1. The focused failed-path test, `pip check`, and
`git diff --check` are green as well.

Untrusted-content safety was the review's focus. The initial self-review
fixed the first PDF decompression bomb; independent review then found the
same memory-exhaustion class evaded through four further paths
(font-auxiliary streams, Form-XObject-nested fonts, cross-page accumulation,
compressed object/xref streams, and PDF-tokenizer blind spots in a
raw-structure scanner). The decisive fix abandons in-process bounding
entirely: all PDF/DOCX parsing runs in a short-lived isolated child process
(subprocess, never fork-from-worker) with a hard RLIMIT_AS/DATA 256 MiB
ceiling and wall-clock deadline; the parent maps any child
timeout/nonzero-exit/signal-kill/malformed-output uniformly to a truthful
refused parser_resource_bounds. The parent worker's memory is bounded
unconditionally (independently verified via getrusage: a 2.7 GiB child left
the parent at +15 MiB). Sanitizer, owner isolation, invariant-8
no-shared-promotion, fetch port, and dual retention all passed adversarial
probing.

Azure Linux CI then falsified one refusal label. Build 2224 at candidate
c7ddc10c failed a single test of 5440: the large-scale compressed-object-stream
bomb refused `parser_failure` instead of `parser_resource_bounds`. The cause is
that on Linux the child's RLIMIT_AS genuinely enforces, so the bomb raises
MemoryError inside the child, where generic `except Exception` handlers
mislabelled it as a parse failure. The refusal was always correct and the
isolation guarantee was never in question; only the reason code was wrong.
`MemoryError` is now mapped to `parser_resource_bounds` at all six guarded
sites, including the nested `reader.decrypt("")` guard that the delta review
found still open and proved reachable end-to-end through the real child worker.
A fresh full enumeration of every `except Exception`, every narrow handler, and
every unguarded allocation region in the child path found no remaining gap; a
MemoryError escaping the final stdout write leaves the child nonzero and the
parent maps it correctly by fallback.

Azure Linux CI build 2267 evaluated merge ref
`1a5edbb0c4d8d4a8483ec45723ab050d502032f6`. Dependency, secret, and compile
checks passed, but the monolithic unittest task ran from 14:44:30.926Z until
the configured 60-minute job timeout canceled it at 15:42:59.623Z. The log
emitted `MemoryError` at 14:46:46.520Z immediately after the direct worker
mapping test. That test invoked `_subprocess_worker_main()` in the unittest
runner, so the production `resource.setrlimit` call permanently lowered the
caller's hard RLIMIT_AS and poisoned the rest of the runner. Candidate
`d62ad090ed09dbad8645445dc639fa0289972f0a` corrects only the test: it mocks
`resource.setrlimit` for that direct in-process call while retaining the
mapping assertions. Service code and the real fresh-child
`LinuxCeilingEnforcementTests` are unchanged.

## P-2 disposable Azure SQL proof

- Attempts: a1 proved verified=1 but was not recorded (operator
  output-capture error), its database deleted with ResourceNotFound
  confirmed; a2 SUCCEEDED and was recorded. Executable SHA-256
  `b5eb0aff9150387f75145356f2b34d8c921b0025cf72401072c2279657b422f1` (independently recomputed by the reviewer);
  gate database `ps-myopp-c10-gate-20260901-a2` (throwaway), verifier
  returned verified = 1, rollback rehearsed, full object inventory.
- Both throwaway databases deleted with ResourceNotFound confirmed; the
  temporary firewall rule was removed. No production or staging database was
  contacted.

## Review

Independent read-only exact-SHA review over five rounds: REVISE on
candidates 76c72c3c, f9987594, 8ee329e1, 5842db84 (each a further evasion of
the memory-exhaustion class, all execution-proven under memory measurement);
PASS on bf6d84072a28579de9bcff99620645ccc3f9eec8, carried to
`c7ddc10c69e4d538118121c85b83a1d91239b086` after a behavior-identical
stderr=DEVNULL hardening (delta re-confirmed). Reviewer: a fresh Claude Opus
session with a fixed pre-written handoff (provenance disclosed); reference
`agent:independent-review/ps-myopp-member-import-001/c10/adversarial-parse-audit`.

The CI reason-code finding above reopened the review after that PASS. Fix
`fed12d29` drew a delta REVISE from a further fresh reviewer with four
findings: F1, a missed and execution-proven reachable MemoryError site at the
nested `reader.decrypt("")` guard; F2, the receipt no longer covering the
candidate; F3 and F4, a test name and a code comment made false by the fix.
All four are corrected in
`abb58f7ed3c016b8f3d72525d368dee29f79fe59`, which the same reviewer then
CONFIRMED after re-running its reachability probe, re-enumerating every
handler from scratch, and rerunning both suites. That reviewer also declined to
let the CI failure discharge the enablement obligation below, on the merits;
its ruling is recorded there verbatim. Reference
`agent:independent-review/ps-myopp-member-import-001/c10/memoryerror-delta-confirm-r2`.

Build 2267's deterministic runner-poisoning failure reopened review once
more. A fresh independent read-only delta reviewer CONFIRMED exact candidate
`d62ad090ed09dbad8645445dc639fa0289972f0a`: the mock is lexically scoped and
restored, the direct worker's `parsed == false` and
`parser_resource_bounds` assertions remain intact, and the production
ceiling plus real fresh-child Linux tests cannot inherit the Python mock.
Reference
`agent:codex/ps-myopp-member-import-001/c10/rlimit-direct-worker-delta-review`.
The receipt names this exact SHA and reviewer; the commit tail after it is
receipt and evidence only.

## Forward obligations (recorded; none blocks this merge)

1. Member-data erasure path across C5/C6/C10 tables before any real member
   data (shared program obligation; doc 08 s5).
2. Shared-store unknown-outcome lockout before multi-worker enablement.
3. BINDING pre-ENABLEMENT gate, and it remains **OPEN**: prove the 256 MiB
   child RLIMIT_AS cap enforces on the Azure Linux runtime in CI (killed child
   -> refusal) before the feature flag is enabled. The parent-isolation
   guarantee holds without it; rlimit is not enforced on the macOS dev host
   (disclosed).

   The writer proposed that Azure Linux build 2224 had incidentally discharged
   this gate, since a real Linux runtime demonstrably stopped a real bomb. The
   independent reviewer rejected that on the merits and the rejection stands:
   build 2224 is **corroborating, non-dispositive**. It proves that something
   stopped the bomb, not that our 256 MiB RLIMIT_AS was the mechanism — an
   agent-level cgroup or container OOM-kill produces the same observable — and
   the MemoryError fix destroys the accidental oracle that produced the
   evidence, so it cannot be re-run for a stronger reading. This package
   therefore claims no discharge.

   Discharge path, carried by the two Linux-gated tests added at this
   candidate in `LinuxCeilingEnforcementTests`: (a) a fresh child sets and
   reads back exactly `MAX_SUBPROCESS_MEMORY_CEILING_BYTES`; (b) a 40x30 MiB
   compressed-object-stream bomb is refused `parser_resource_bounds` through
   the real shipped pipeline in under half the wall-clock deadline, the timing
   being the discriminator that separates a memory stop from the timeout
   backstop. The reviewer confirmed (b) drives the shipped path and excludes
   the pypdf `LimitReachedError` confound.

   Two strengthenings are required **before the discharge is claimed**, not
   before this merge:
   - Add a differential enforcement probe: two children run the identical
     program, one applying the shipped ceiling and one not, each attempting an
     allocation at 1.5x the ceiling; assert the limited child refuses and the
     unlimited child succeeds. The differential is what excludes a cgroup or
     container limit as the cause, converting "the ceiling is settable" into
     "the kernel enforces at exactly this value".
   - Bind (a) to the shipped block rather than a hand-written replica: run a
     child that feeds a trivial payload to `_subprocess_worker_main()` and
     reports `resource.getrlimit` on stderr (stdout carries the worker JSON),
     asserting the production code path set the ceiling. As written, (a) would
     still pass if the shipped block or its constant drifted.

   Reading condition on the discharge evidence: a skipped test is green.
   `azure-pipelines.yml` pins `ubuntu-latest`, so these will run — but the
   discharge record must cite `LinuxCeilingEnforcementTests` as **executed,
   not skipped** (the CI log must show this module's tests run with zero
   skips). A future agent-image change that silently skipped them would
   otherwise read as a passing discharge.
4. Per-upload subprocess concurrency footprint for C8 route wiring / PS-OPS.

## Coordination record

Both registry surfaces (SQL FIles/Migrations/registry.json and
docs/governance/PACKAGE_REGISTRY.json) entered the claim via extend-surfaces
transitions after the Settings export program released the migration
registry, coordinated with that program in parallel.

For this correction, the existing writer ref, branch, and durable worktree
were preserved under the recorded relinquishment. Current lifecycle tooling
cannot rebind an existing durable record for a same-branch voluntary transfer,
so no registry was hand-edited and no replacement branch or worktree was
created.
