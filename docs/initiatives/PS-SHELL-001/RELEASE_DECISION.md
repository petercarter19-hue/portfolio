# PS-SHELL-001 — release decision, 2026-08-13

## What the owner decided

Pete reviewed rendered screenshots of the shell on 2026-08-13 — the first time
the shell had been seen by a person rather than measured by a machine. He asked
for the logo to be revealed at every width, for shell colour to be made
consistent, and then for delivery to be shortened.

He was shown three options with their trade-offs stated plainly and chose the
middle one:

> **Narrow review, skip the code-pinned attestation, merge on required CI.**

He also decided the shell should be **deployed deliberately** immediately after
merge rather than left to ride on an unrelated deploy, and that retiring
Interview Studio's sage in favour of a universal colour belongs to the
**cross-site Colour, Background and Typography Audit**, not to this package.

## What was skipped, stated plainly

The delivery control plane can bind a merge to a code-pinned attestation: an
exact reviewed SHA, the review evidence file's blob and byte hashes, and a
verdict string, all hardcoded so the validator itself can prove that the tree
merged is the tree reviewed. **That step was not exercised for this package.**

Two reasons, both recorded rather than implied:

1. The owner chose to skip it to save a delivery cycle, after being told what
   it protects and what its absence costs.
2. The machinery could not express this lane without repeated repair. The merge
   grant admits only `direction_authority` lanes plus hand-pinned package
   exceptions; a `shared_foundation` lane had no path. One repair was merged to
   open the lane-class gate (`shell_merge_preflight_repair`, main `1abb3fb`). A
   second, registering the review contract, was built and verified but not
   merged. Each pins an exact `origin/main` base, and this trunk moves often
   enough that pins expired mid-cycle more than once.

**The consequence:** the reviews are recorded in this package as documents, not
enforced as a lock. A later auditor must read `INDEPENDENT_REVIEW.md` and trust
it, rather than having the validator prove the binding.

## What still held

- Four independent reviews by fresh delegated Claude Opus sessions: three full
  rounds (16 findings, then 12, then a merge-readiness pass) and one narrow
  final round scoped by the owner to logo placement and shell colour.
- Every finding from every round was fixed and re-verified.
- Full test suite green apart from four failures pre-existing on the base.
- Azure required CI passed before merge.
- No product code merged outside the lane's recorded writable surfaces.

## What the owner has NOT accepted

Pete has seen screenshots. He has **not** accepted the shell visually on the
live site, and no visual-acceptance record exists. The ledger separately records
an earlier decision granting "implementation, review, merge, and release"; the
narrower reading — merge only, with release as a deliberate separate act — is
what was followed here. That discrepancy is flagged for reconciliation.

## Known limits carried into production

- The shell has **no feature flag**. `templates/base.html` and
  `static/css/public-navigation.css` change unconditionally, so merge and
  release are effectively the same act and rollback is a revert, not a toggle.
- The shell was never rendered locally on Community, Opportunity Slate or
  Workshop — all three return 404 without a database, and the 404 template
  renders the shared shell, which inflated earlier route-coverage figures.
  `/the-slate` is the material gap: it is the only route besides `/petec/*`
  owning its own mobile tab bar, and the single-bottom-bar rule turns on exactly
  that interaction.
- No real phone or tablet hardware, no screen reader, no non-Chromium browser,
  and no genuine authenticated session were exercised.
- Interview Studio's authenticated warm-ivory header never rendered locally.
- At 200% text with Workshop enabled, five destinations wrap the header to
  441px at 1200–1366 (§12.3). No overflow; a quality limit, not a conformance
  failure.

## First checks after deployment

1. `/the-slate` on a phone — one bottom bar only, and the page's own bar
   behaves as before.
2. The logo at tablet widths signed in, which is the defect this round fixed.
3. Interview Studio signed in, for the warm-ivory header never seen locally.
