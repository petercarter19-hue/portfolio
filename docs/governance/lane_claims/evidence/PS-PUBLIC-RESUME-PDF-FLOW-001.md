# Public resume PDF and mobile link repair

The original PDF product candidate was
`a294f4931d8a4e6fd4e77052291d251d2fd47c2f` on
`work/2026-09-16-public-resume-pdf-flow-001`. It changes only the claimed PDF
generator, published PDF, resume template mobile menu, and two focused test
files. It did not change `app.py`, the shared shell, response policy, accepted
resume wording, private routes, or production.

The former PDF had a broken cross-reference table and clipped long lines at
the right edge. The generator now writes a deterministic, strict-parseable
one-page US-letter PDF and checks actual core-font widths against 50-point
horizontal margins. The original and regenerated PDFs have identical
normalized extracted text and order, SHA-256
`37dba960e88d8ee55b8e5a25f08a26856522fc6fdf8f1974fa9fcc26c3eee2a4`.
The PDF byte SHA-256 is
`42146bb9f1c6cda91ba39592a4f42530e6b989ad625f1e7a55071e46e57fe7cb`;
the current version token is `42146bb9f1c6`. The mobile native Sections menu
now exposes the same server-rendered PDF link as the desktop rail, including
when JavaScript is disabled.

Writer validation passed 31 focused PDF/resume tests and 84 adjacent search,
HTTP edge, preview, and navigation tests. `--check` regeneration and
`git diff --check` passed. Local browser proof at desktop and mobile sizes
confirmed the current link, native no-JavaScript menu access, and a downloaded
file byte-identical to the published PDF. Poppler rendered the complete
one-page letter PDF without clipping, and `pdfinfo` reported no encryption or
JavaScript. The full repository suite was still running through lifecycle
fixtures when the original evidence tail was recorded; its result remained a separate
gate, not an inferred pass.

Independent read-only reviewer `agent:/root/exact_candidate_reviewer` issued
**PASS with no actionable findings** on the exact product candidate. The
reviewer verified the five-path scope, original/new text parity and order,
strict PDF parsing, byte-identical regeneration, 144-DPI visual margins,
mobile native-menu/no-JavaScript link, bounded noindex download policy, and
independently passed all 31 focused tests. The original review receipt was **recorded
at** `2026-09-17T01:08:54Z`; this is not an inferred reviewer-completion time.
Its detailed local record is
`C:\Users\peter\Documents\Codex\2026-09-13\peerslate-corporate-network-access-priority\outputs\PDF_MOBILE_INDEPENDENT_REVIEW.md`.

The first product PR's required Linux build 3145 ran 6,544 application tests
and failed only the integration assertion that expected one PDF URL in the
page after the mobile menu intentionally added a second link. The claim was
extended through Protected PR 1092 and successful current-target build 3155;
its accepted merge was `d6ea6de4bee62e9c53b2cb2b2b8524dc4cdf0e93`.
After synchronizing with that main, the writer changed only
`tests/test_member_overview_public_integration.py:136` from count one to two.
The corrected, clean and pushed candidate is
`a8ab249d71ec4602faf4aacf89f1e1bbf3efc60b`. All five original PDF,
generator, template and focused-test blobs are byte-identical to the first
independently reviewed candidate. The writer passed 123 focused and adjacent
tests on the corrected candidate, and `git diff --check` passed. The earlier
local Windows full-suite run had 6,392 tests with the same stale assertion
plus unrelated Windows-specific synthetic and Community fixture failures;
it is not represented as a pass.

The independent changed-risk reviewer issued **PASS with no actionable
findings** on the corrected exact candidate at `2026-09-17T03:05:15Z`.
The reviewer verified the five original blobs, accepted-main ancestry and
homepage bytes, the sole one-line assertion update, native mobile
details/no-JavaScript access, and independently passed 39 relevant tests.
At that checkpoint, the receipt referred to the corrected a8ab review; the
original a294 review remains preserved above as provenance.

An unrelated accepted-main claim-only merge moved the target to
`44fcc03a0843620d6844b2f9d1cb60ee2b5970f0`. The refreshed clean and
pushed candidate `aba80e8cc7947f1d4d35b99ea7d3937680c47bb0` has direct
parents `5b205e8add0d5fb0566bd512f7a9e8092aa2b35e` (the evidence-tail
checkpoint) and that accepted main. Independent equivalence review completed
at `2026-09-17T03:51:23Z` with **PASS and no actionable findings**: all six
product/test blobs are identical between a8ab and aba80; a8ab to 5b205
changed only runtime-inert receipt/evidence; all eight package blobs are
identical between 5b205 and aba80. The only imported path is the unrelated
`PS-MVP1-PUBLICATION-COMPONENTS-001.json` claim, byte-identical to current
main. The reviewer found no new behavior mutation or unreviewed mutable path
and confirmed the worktree and diff checks clean. No tests were repeated for
this equivalence-only review; prior test evidence remains applicable. The
receipt pointed to that exact refreshed candidate and review time at that
checkpoint.

The accepted CI trusted-target change then moved main to
`5d99a7b3459d2560cd72e70a22c5456bc14e69f3`. Fresh write admission
passed and the writer merged that main without conflict into the clean,
pushed candidate `21256b1f83a0550850ca5341c622e08d640f3e9d`, whose
direct parents are `f0cb6df9cb70ecff4d81d6c1a81785c334f01b25` and
that accepted main. Independent exact-SHA equivalence review completed at
`2026-09-17T05:39:46Z` with **PASS and no actionable findings**. All eight
package blobs are identical from f0cb to 21256, and all six product/test
blobs remain identical to independently reviewed a8ab. Exactly seven
unrelated CI/evidence/test paths were imported, each byte-identical to
accepted main. The reviewer confirmed a clean worktree and diff checks;
no tests were repeated for this equivalence-only review. This receipt binds
the exact 21256 candidate and reviewer result.

This evidence and the receipt are runtime-inert; repository acceptance is not
production deployment or live proof. Homepage release ownership remains
separate.
