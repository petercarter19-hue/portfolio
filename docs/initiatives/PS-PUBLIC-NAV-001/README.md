# PS-PUBLIC-NAV-001 — Public Navigation Correction

## Status

Active by Pete's explicit direction on 2026-07-29.

This package is a narrow owner-authorized override of the
`PS-AI-OPS-CHECKPOINT-001` hold. It does not reopen unrelated runtime work.

## Authority and ownership

- Owner and product authority: Pete Carter
- Session manager and writer: Codex
- Authoritative base: Azure DevOps `origin/main`
- Base commit: `0eed47e7201a40fcd7858ca3040712ed2f2dd8f2`
- Branch: `work/2026-07-29-public-nav-001`
- Visual authority: Pete's accepted public-navigation direction in the
  2026-07-29 session, implemented through the existing released shell language
  without a new visual theme

## Release decision

Pete accepted the completed public-navigation result and directed deployment on
2026-07-29. Gate Candidate is recorded as **Not Applicable** for this bounded
release: it changes only the shared public template, CSS, client-side
navigation, and tests; it introduces no dependency, backend, route, data,
identity, authorization, integration, secret, setting, migration, feature flag,
or new audience. The already-public routes and capabilities remain the same.
The normal Azure pull request, production pipeline, liveness/route smoke, and
git-revert rollback controls still apply.

## Problem statement

The shared public shell currently renders Pete's profile tabs on unrelated
product and marketing routes, exposes non-authoritative or retired
destinations through header search, clips the three global destinations on
phones, and uses different horizontal geometry for the global header and
Pete's profile subheader.

## Approved contract

1. Keep the released public global destinations:
   - Pete's Slate
   - Community
   - Interview Studio
2. Render Pete's profile subnavigation only within canonical `/petec` public
   profile routes.
3. Use these current profile destinations:
   - My Story
   - Slate Board
   - Résumé
4. Remove Work from the profile navigation until a real Work destination is
   approved and implemented. Existing compatibility redirects remain.
5. Make Pete's Slate enter the Overview state and make Résumé enter at the
   detailed résumé boundary on the consolidated `/petec/resume` page.
6. Keep Ask Pete AI inside Pete's public Slate only. Community, Interview
   Studio, marketing, authentication, and owner surfaces must not inherit it
   from the shared shell.
7. Give phones one accessible global menu containing all three global
   destinations and public destination search.
8. Align the global header and Pete profile subheader to one shared horizontal
   gutter and one stable primary-header height.
9. Remove stale, private, preview, and retired destinations from public header
   search.

## Owned files

- `templates/base.html`
- `templates/partials/profile_tabs.html`
- `static/css/public-navigation.css`
- `static/js/public-mobile-nav.js`
- `static/js/public-site-search.js`
- Navigation-focused tests whose expectations are changed by this contract
- This package's documentation and evidence

The legacy `static/js/mobile-nav.js` and `static/js/site-search.js` files are
reference-only and remain unchanged for the deferred owner shell.

## Explicit exclusions

- Owner-facing navigation or owner workspace changes
- Moving or renaming Interview Studio
- Replacing the current global product taxonomy
- Creating a new Work page
- Changing homepage scene content or homepage visual composition
- Changing Community or Interview Studio local workspace architecture
- Merge, deployment, or production release

## Acceptance evidence

- Focused Flask route/template tests for scope, labels, destinations, search,
  and AI availability
- Full repository test run
- Browser verification at desktop, tablet, 390px, and 320px widths across:
  homepage, Pete's Overview/Résumé, My Story, Slate Board, Community,
  Interview Studio, and Why PeerSlate
- Keyboard, focus, Escape, active-state, overflow, and reduced-motion checks
- Complete-diff self-review
