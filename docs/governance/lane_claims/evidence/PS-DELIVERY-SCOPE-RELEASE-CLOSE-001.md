# PS-DELIVERY-SCOPE-RELEASE-CLOSE-001 — completion evidence

The validator previously rejected an accepted product package after a supported partial scope release. A released claim could carry its proof only while active, but ordinary close changes the claim to closed. Close also compared the originally reviewed product paths with the reduced current surface list, so the historically reviewed and released `azure-pipelines.yml` path appeared outside the claim.

This package changes only `scripts/delivery_preflight.py` and `tests/test_delivery_preflight.py`. Closed claims retain the exact, well-formed scope-release proof. During close, the validator finds the unique first-parent main transition that introduced that same proof, revalidates the historical reduction and Git object lineage, and admits only a released reviewed path whose accepted introduction names the closing package, candidate SHA, merged SHA, and fixed receipt. The existing three-field close transition, reviewed receipt, preserved implementation branch, merged-path introduction, byte equality, and retained-surface checks remain in force. It does not change the original CI claim, receipt, release proof, or custody.

- Base: `0750c3cf0f6830b8aa47c9e63c23b8fd9599df57`.
- Reviewed candidate: `fa47cf6828c12637e0a59eb4921ae6734b7be8b6`.
- Writer: `session:01a0bc90-6ec9-72f0-8be8-cb0bd56355fe`.
- Independent reviewer: `session:01a0bcb7-7969-7413-952f-8b6ed2262651`, PASS for that exact candidate with no actionable findings. Full review evidence is retained outside the repository at `C:\Users\peter\Documents\Codex\2026-09-16\peerslate-delivery-repair-evidence\scope-release-close-review-fa47cf68\REVIEW.md`.
- Verification: `python -B -m unittest tests.test_delivery_preflight` passed all 263 tests. Temporary-Git cases cover accepted release, unrelated path, changed or ambiguous proof, candidate/merge/receipt mismatch, changed Git blob, and close-delta tampering. `git diff --check` passed.
- Actual CI history check: the new helper admitted only `azure-pipelines.yml` from `PS-CI-TRUSTED-TARGET-CONTROL-ONLY-001`, with zero errors. The independent reviewer also confirmed the original reviewed candidate, accepted merge, receipt, mode/blob lineage, and reconciled remote branch against real immutable Git objects. This was read-only; the original writer still owns its governed close.

This is a repository validator repair only. Production authority remains withheld. The implementation PR, required Azure CI, accepted merge, and this package's claim close are separate delivery steps.
