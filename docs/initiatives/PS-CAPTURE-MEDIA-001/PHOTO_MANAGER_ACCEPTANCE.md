# PS-CAPTURE-PHOTO-EXPERIENCE-001 - Manager visual-product acceptance

## Decision

- Decision date: 2026-07-20
- Owner direction: Pete asked the ChatGPT Work/Codex manager session to review
  the returned work, make the required approvals, complete the authorized
  release work, and prepare an exact cross-computer handoff.
- Designated session manager: ChatGPT Work/Codex for this owner-authorized
  Photo package exception.
- Writer branch reviewed: `work/2026-07-19-capture-photo-experience-001`
- Accepted writer SHA before this record:
  `f6c62bdf2b31095648421c1643a4effad4b35f45`
- Visual-product result: **Accepted for flag-off release**.
- Enablement result: **Not authorized**.

## Evidence reviewed

The manager reviewed the selected Photo 1 authority and all five named
implementation images:

- `visual-authority/photo-1-selected-authority.jpg`
- `evidence/photo-opening-desktop-1440x900.png`
- `evidence/photo-local-preview-desktop-1440x900.png`
- `evidence/photo-review-desktop-1440x900.png`
- `evidence/photo-opening-mobile-390x844.png`
- `evidence/photo-review-mobile-390x844.png`

The implementation is recognizably the accepted design. It preserves the deep
navy frame, warm ivory stage, editorial heading, one dominant Photo action,
restrained gold, persistent private status, and mobile document flow. The five
adaptations listed in `PHOTO_DESIGN_AUTHORITY.md` are accepted: Photo-scoped
modal context, separate Take/Choose paths, CSS architectural depth, complete
backend-enforced state coverage, and an explicit accessible close control.

The manager also verified:

- exact branch/remote SHA match and a clean working tree;
- focused Photo/Capture/Voice/database/lifecycle tests: 61 passed;
- full repository suite: 550 passed, 1 expected environmental skip;
- `git diff --check`: passed;
- flag-off rendering hides the Photo choice and asset;
- owner-scoped rehydration and neutral cross-owner not-found behavior;
- no Blob locator, SAS URL, client filename, local/session storage, or public
  publication path in the browser contract; and
- no dependency, migration, infrastructure, homepage, global navigation, or
  feature-flag enablement change in this experience branch.

The branch report's prior JavaScript syntax check is accepted as writer
evidence. The current Windows session did not have Node on `PATH`; the browser
contract tests and full suite passed, and no JavaScript source changed during
manager acceptance.

## Release boundary

This acceptance authorizes an Azure squash PR and production deployment with
`CAPTURE_PHOTO_ENABLED=false`. It does not authorize changing the flag, exposing
Photo to members, claiming a new live Capture method, or closing
`PS-HOME-CAPTURE-PHOTO-PARITY-001`.

After the flag-off release, the package must record the exact PR, squash SHA,
pipeline, production neutral-404 proof, unchanged public/protected route
boundary, and release of the temporary `owner_routes.py` reservation. Real
signed-in scanning/rejection/deletion and homepage parity remain enablement
gates.
