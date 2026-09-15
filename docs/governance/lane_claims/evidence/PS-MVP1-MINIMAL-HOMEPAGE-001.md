# PS-MVP1-MINIMAL-HOMEPAGE-001 — candidate evidence

## Scope and authority

This Protected repository package replaces the long signed-out homepage body
with Pete's accepted minimal MVP1 composition inside the unchanged shared
shell. Repository authority extends through merge. Deployment, production,
schema, provider, identity, billing, and live-operation authority remain
withheld.

The sole implementation writer is
`session:01a0a4f1-90df-7561-95cc-5d6c40df571e`. The independent reviewer is
`agent:/root/independent_review`.

## Governance lineage

- The package was activated from main
  `74e2d9fd313bf983ab6574c4b53ab52ea9e826a6`.
- Source commits `eb4e7702`, `78c38985`, and `fb622e31` established the
  minimal body, restrained status treatment, and Pete's final approved
  selective-access wording.
- `PS-INTERVIEW-RECOVERY-MOBILE-NAV-001` released
  `tests/test_shared_shell_convergence.py` after its accepted merge and claim
  closure on main `92cf0b70739e710e59900cc41a624395eafb32eb`.
- Claim-only extension candidate
  `e61387408d9ac698a4bd6c201319505dac36786d` added that exact released test
  path. Required build 3042 passed and PR 1051 squash-merged it at
  `8e2b30b803f4b5b966fe5c2d857bbe5a4c49b84a`.
- The product branch merged that current main, replaced only the stale legacy
  homepage assertion on the newly claimed test surface, and froze exact
  candidate `33ecd9bbe148d589538743be8458d36732b26b51`.

## Exact reviewed candidate

Against exact base `8e2b30b803f4b5b966fe5c2d857bbe5a4c49b84a`, candidate
`33ecd9bbe148d589538743be8458d36732b26b51` changes exactly five claimed paths:

- `static/css/homepage-minimal.css`
- `templates/homepage.html`
- `tests/test_dark_theme_availability.py`
- `tests/test_homepage_scenes.py`
- `tests/test_shared_shell_convergence.py`

The rendered homepage body contains one existing decorative aurora image, one
H1 (`Your Work. Your Story. Your Future.`), and Pete's exact approved status
copy (`A considered beginning. PeerSlate is taking shape. Access is by
invitation as we prepare for what’s next.`). It contains no body links, form,
login panel, call to action, product destination, capability claim, biography,
fixture, or legacy homepage scene. Shared shell account controls, navigation,
footer, authentication routes, noindex behavior, and security policy remain
outside the candidate delta.

The access wording records Pete's selective-access policy; this repository
package does not create or claim an invitation workflow. The separately
managed live self-service-signup control is not a code or deployment action in
this candidate.

## Validation

Writer validation on the frozen candidate:

- Homepage, shared-shell, theme, navigation, search-visibility, and
  operational-readiness suites: 100/100 passed.
- Exact browser checks at 1440x1000, 390x844, and 200% zoom confirmed the
  approved copy, image, zero body links, natural-flow scrolling, and no
  horizontal overflow.
- Decorative-image semantics, intrinsic dimensions, forced-colors handling,
  and the image-failure fallback remain covered by focused tests.
- `git diff --check`: passed.
- Local HEAD and fetched remote package branch both equalled the exact
  candidate before review.

The independent reviewer verified exact candidate and base identity, the
five-path claimed delta, scope exclusions, rendered content, accessibility,
failure behavior, visual reflow, and test truth. The reviewer independently
reran 91 relevant homepage, shared-shell, theme, site-rule, and HTTP/security
tests; all passed. The reviewer issued **PASS with zero findings**.

## Release truth

This evidence and its review receipt are runtime-inert post-review records.
They do not alter the reviewed product or test bytes. The PASS grants
repository merge admission only after required Azure policies pass. Merge is
not deployment, production authorization, or authenticated live proof.
