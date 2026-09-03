# PS-PROFILE-MEDIA-VOICE-PROVIDERS-001 — candidate evidence

## Scope and authority

Pete authorized this package under
`session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`.
This is a Protected repository package with authority through merge.
Production authority is withheld. No deployment, production request, SQL,
schema, migration, grant persistence, identity operation, provider contact,
credential use, or live operation is part of this record.

## Governance lineage

- Claim-only activation: PR 876 / build 2327 / merge
  `ab6e4f58cf71768e63e86b7a43f4e96a7a8b665d`.
- Deferred Package Registry surface extension: PR 883 / build 2344 / merge
  `dd0585f6f4150a3a6d708225d43c6a4db1d47e26`.
- The implementation branch was rebased onto that exact extension merge before
  registration, validation, or final review.

## Candidate outcome

Exact candidate `4e321882df38d0ca60809739102213439ffba523` on direct
parent/base `dd0585f6f4150a3a6d708225d43c6a4db1d47e26` adds dark,
unregistered Profile Photo and retained-Voice provider modules over injected
canonical ports and deterministic local fakes. It also adds the package's one
alphabetized `current_protect` registry row and recomputes the current baseline
counts to 71 / 33 / 6 / 23 / 6, total 139.

Media resolution admits only a clean, metadata-stripped Photo preview bound to
the exact owner, publication grant, audience, projection/source versions,
content type, length, and digest. It does not expose Photo originals, albums,
or video. Voice resolution binds the exact retained source version and
approved Capture revision. Only the member-approved transcript can be
canonical output; transcript-only and audio-only results stay truthful and
audio never autoplays.

Public and Connections are distinct authorization decisions with no fallback.
Either block direction wins. The complete grant, authorization epoch/block
decision, and source lifecycle snapshot are re-read after any private-byte
open and must remain identical before content returns. Authorization and
source validation therefore precede bytes, while unpublish, revoke,
where-used removal, block, version, Capture-revision, or deletion races fail
closed. Dependency failures are stable and content-free; return-value
representations suppress private bodies, transcripts, identities, source
keys, projection values, and digests.

The candidate changes exactly seven claimed paths: the Package Registry, two
initiative documents, two provider modules, and two focused test modules. It
does not change routes, templates, flags, application registration,
`services/database_service.py`, SQL, migrations, schema, provider grants,
credentials, identity, deployment, or production behavior.

## Validation

- New provider suites: **25 passed**.
- Combined provider, closed D0 projection, Capture lifecycle, Photo, Voice,
  adapter, and Community Voice matrix: **115 passed**.
- Closed D0 Profile media/voice tests within that matrix: **7 passed**.
- Package Registry validation: **2 passed**; one unique row, exact alphabetical
  neighbors, per-category counts, and total all reconcile.
- Exact-candidate full repository suite in a clean requirements-only virtual
  environment: **5,548 passed, 26 expected skips** in 260.281 seconds.
- Python provider compilation and `git diff --check`: pass.
- Strict fetched, clean, task-bound write preflight: pass; exact head
  `4e321882df38d0ca60809739102213439ffba523`, ahead 1 / behind 0, seven
  changed paths, and current main `dd0585f6f4150a3a6d708225d43c6a4db1d47e26`.
- Current-tree Gitleaks scanned approximately 49.46 MB with zero findings;
  exact one-commit range Gitleaks scanned approximately 76 KB with zero
  findings; all local refs scanned 2,466 commits / approximately 94.18 MB with
  zero findings.
- A brand-new isolated Azure fetch reproduced the exact main and candidate
  SHAs. Its current-tree, one-commit range, and every fetched ref/tag Gitleaks
  scans were all clean (1,009 commits / approximately 49.37 MB for the final
  all-ref scan).

## Rejected-candidate correction

The first unmerged implementation candidate
`54c7752182f718d42a4c0b22f75f1dd8823b9d17` was rejected after Gitleaks
correctly surfaced 11 deterministic generic-api-key matches in synthetic test
identifiers. They were false positives rather than credentials, but they would
have poisoned full-ref CI. The fixture shapes were changed within the two
claimed test files without changing semantics, and the unmerged branch was
rewritten with an exact force-with-lease so the rejected commit was no longer
reachable. The later registry refresh replaced the provisional corrected tip
`d5a6c6128c7fa7b53dd91d59a3e8c5ee94e1b452` with the final candidate.
The fresh isolated Azure fetch contains neither superseded object and reports
zero findings.

An auxiliary review virtual environment containing Playwright also triggered
two existing sealed-browser tests' intentional
`sealed_browser_runtime_contaminated` refusal. A clean environment installed
only from `requirements.txt` reproduced the repository order and passed all
5,548 tests. The provider package neither imports nor installs Playwright.

## Independent review

Independent final exact-SHA review ACCEPTed candidate
`4e321882df38d0ca60809739102213439ffba523` on base
`dd0585f6f4150a3a6d708225d43c6a4db1d47e26` with no blockers. Reviewer:
`agent:/root/workshop_polish_prep`; reviewed at
`2026-09-03T06:17:04Z`.

The review verified the exact seven-path claimed delta, registry row and fresh
counts, owner/audience/source/version/block/digest/revalidation ordering,
authorization-before-bytes boundary, neutral errors, privacy-preserving
representations, deterministic tests, and dark/unregistered runtime scope. It
confirmed no SQL, schema, grant, provider registration, deployment, or live
change. Acceptance authorizes repository merge only.

## Release truth

This evidence binds an immutable repository candidate. It does not state or
imply that the providers are registered, enabled, deployed, production-ready,
or live. A real SQL-backed grant reader or runtime binding requires a separate
claimed package and explicit authority; it is not inferred here.
