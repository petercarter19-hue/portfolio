# PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001 — technical completion record

## Scope and authority

- **Package:** `PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001`
- **Delivery path:** Bounded; independent exact-SHA review required
- **Writer:** `agent:/root/workshop_polish_prep`
- **Branch:** `work/2026-09-03-workshop-reflow-accessibility-polish-001`
- **Activated from:** `df37a13d293c42a4ad3f4b0ba350bad207b0a306`
- **Activation merge/base:** `31798edff5e65bb6cf30e7c254aac524c55df5a2`
- **Owner outcome:**
  `session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`
- **Production authority:** withheld

## Repository outcome

The implementation preserves the existing owner-accepted, unflagged Workshop
facelift and makes targeted semantic and responsive corrections:

- the shared Workshop hero owns the sole H1 while each of the three W2 views
  uses an H2 for its local title;
- dead fixture links in claimed partials are inert text, unavailable controls
  use native `disabled` state, and the unclaimed suggestion partial's three
  fixture-only dead anchors are narrowly suppressed in Workshop CSS, so
  keyboard stops correspond to real actions;
- the information card is one truthful native disclosure at every breakpoint;
- Workshop links, buttons, fields, summaries, chips, and label-backed controls
  have visible focus and a 44px target floor;
- long labels and metadata wrap, dense mobile rows stack, focused list rows keep
  an unclipped inward ring, and Workshop-scoped scroll padding keeps native Tab
  scrolling clear of the shared sticky header and fixed phone bar;
- forced-colors states retain outline/selection distinctions and reduced-motion
  mode suppresses nonessential animation and transition duration.

No route, form action, copy, product flow, owner boundary, privacy/cache policy,
or accepted composition changes. Workshop E/F/G and the separate fresh
two-member proof remain untouched.

## Landmark truth

Rendered library, W2 opening, W2 session, and W2 review states each prove one
`main#main-content` and one visible `.wk-hero__title` H1 inside it. The shared
skip link targets that main. Under the central manager's bounded interpretation
of "one H1 and labelled main per view," the visible H1 names the Workshop view
within the sole canonical main and establishes the required label/ownership
relationship; no additional ARIA accessible name is required on a unique main
landmark. Because shared base is excluded and nested main landmarks are
forbidden, neither `templates/base.html` nor a second main is changed. A future
literal main-naming hook would be separate shared-shell work, not an unmet
requirement of this package.

## Verification to date

- Claimed semantic/polish/W2 suites: **102 tests run / 1 intentionally
  skipped / zero failures**.
- All `test_workshop*.py` suites: **697 tests run / 3 intentionally skipped /
  zero failures**.
- Isolated local Chromium proof: **18 screenshots / 18 checks / zero failures**
  after the full keyboard traversal. The replacement check explicitly proves
  the three fixture suggestion anchors exist in rendered markup but are not
  visible or sequentially focusable, and detects mid-word eyebrow fragments
  at every populated viewport. A first stricter run correctly found
  native focus could settle three status chips under the visible phone bar;
  Workshop-scoped document scroll padding fixed it, and the repeat traversed
  every Workshop stop with a visible ring and no sticky-chrome obstruction.
- Evidence allocation: `f86b3c3ed63b18df43908e9c`, external same-task path
  `PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001/pre-registry-browser-proof/76b7b02684a8`.
  Those capture bytes are outside the repository and remain the provisional
  comparison set. The post-registry frozen SHA repeats the same matrix into a
  SHA-bound external evidence path recorded in the governed evidence tail.
- Auth, sign-in, navigation, shared-shell, and HTTP edge-security render
  regressions: **161 passed**.
- Workshop voice plus shared auth/callback Node suites: **3 test files passed**
  (**49 behavioral checks**).
- Jinja compilation: **26 Workshop templates compiled**.
- Package Registry validation: **2 tests run / zero failures**; the one
  alphabetized `current_protect` row produces counts **74 / 33 / 6 / 23 / 6,
  total 142**.
- Clean full repository regression: **5,580 tests run / 35 skipped / zero
  failures**.
- Surface-extension independent review, PR 892, CI build 2365, merge, and
  lifecycle finalization: complete. Final diff/secret scans, immutable
  implementation review, PR/CI, merge, and package close remain pending.

The browser proof runs Playwright only in a short-lived child process. Ordinary
test discovery never imports Playwright, and the fixture restores the Flask
configuration, limiter, instance path, patches, server, and temporary instance
directory. It uses only a generic local development identity and local session
data; it contacts no live host, identity, provider, or credential.

## Governance gate

The serialized claim-only extension added exactly
`docs/governance/PACKAGE_REGISTRY.json`, passed independent exact-SHA review,
and merged/finalized before any Registry edit. The active claim now owns 17
surfaces. This implementation refreshes from exact extension main
`5c2bdf891670893978bbe194ef48b608c9567629`, registers one alphabetized
`current_protect` entry with recomputed counts, and must receive a fresh final
exact-SHA review before its implementation PR. The earlier pre-extension
candidate and review remain evidence only and do not authorize merge.

## Release truth

This record describes repository-local implementation and proof. Nothing here
has been deployed, enabled, configured, migrated, applied to an identity, or
exercised against production.
