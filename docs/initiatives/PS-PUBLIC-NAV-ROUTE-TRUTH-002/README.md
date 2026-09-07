# PS-PUBLIC-NAV-ROUTE-TRUTH-002

This package makes the current PeerSlate navigation and sign-in return paths
agree with routes the running Flask application can actually serve. It keeps
the existing visual composition while removing promotion of Capture, Slate
Board, and Workshop.

## Delivered behavior

- One declaration in `safe_return.py` supplies server-verified destinations
  to the desktop header, room switcher, mobile Menu, no-JavaScript navigation,
  account menus, phone bar, search index, `/app` launchpad, profile tabs, and
  homepage destination cards.
- The declaration checks the registered Flask endpoint, its GET/HEAD support,
  the flag for the blueprint that is actually registered, and any declared
  query values before emitting a navigation record.
- Safe sign-in returns accept exact declared landings and the supported
  Interview and Opportunity query values. Malformed, external, encoded
  separator, dot-segment, unknown, unavailable, and undeclared-query targets
  fall back to the validated caller default or neutral `/app`.
- Recognized object and action URLs collapse to a safe parent without looking
  up or exposing opaque keys. Existing export-key nondisclosure remains in the
  shared shell.
- `/app` remains the neutral private starting point until a real member Profile
  exists. It presents Opportunity Slate, Interview Studio, Community when
  available, and Settings. It does not use Pete's public fixture as the
  member's Profile.
- My Story and the canonical Community Feed at `/the-slate` remain available.
  Pete's profile tab strip retains My Story and Résumé after Slate Board is
  removed. Feed keeps its established shell, mobile, launchpad, search, and
  homepage representations; this package does not invent a new profile tab.
- The Capture, Slate Board, and Workshop runtimes and saved content remain in
  place for compatible direct links. Only their navigation promotion is
  removed.
- `/career-search`, `/my-network`, `/explore-profiles`, and `/for-recruiters`
  retain their activated handler, shared template/card bytes, and sitemap
  entries. A regression test freezes those boundaries.

## Boundaries

This is a nonvisual source delivery. It does not add CSS, redesign the product,
delete routes or member data, change feature flags, contact identity providers,
use a member database, deploy, or claim the future member Profile is complete.
Journal remains excluded and Projects remains deferred.

Validation uses synthetic local identities and fixed placeholder signing
values. Provider, database, SQLite, subprocess, outbound network, and repository
writes are blocked in the browser fixture. See
`OWNER_TECHNICAL_COMPLETION_REPORT.md` for candidate evidence and
`POST_DEPLOY_CRAWL_MATRIX.md` for the separately withheld deployment checks.
