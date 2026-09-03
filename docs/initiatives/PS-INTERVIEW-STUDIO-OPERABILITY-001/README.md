# PS-INTERVIEW-STUDIO-OPERABILITY-001

## Outcome

This Protected package makes the existing authenticated Interview Studio
operable without changing its product model. The page has one visible H1, one
canonical guarded History destination, one responsive Session setup launcher,
and one Studio settings launcher for the existing page-local dialog.

The authenticated controls use a single DOM instance at every breakpoint.
Session setup explains before application that changed setup starts a new
browser-local session and retains the established draft and recording guards.
Settings and setup synchronize expanded state, move focus into their surface,
handle explicit close or cancel and Escape, return focus to the launcher, and
announce state without including member content.

## Progressive enhancement and accessibility

JavaScript-only launchers are hidden in server-rendered markup and become
available only after their handlers are installed. With JavaScript disabled,
the real mode and History anchors remain visible and navigable. Authenticated
controls keep a 44-by-44 CSS-pixel target, visible focus, narrow-screen reflow,
and usable forced-colors, reduced-motion, text-spacing, 200%, and 400%
equivalent layouts.

The dedicated local Playwright suite uses only an isolated test identity. It
checks exact control counts, focus entry and return, Escape, backdrop and close
behavior, Tab containment, setup application, draft persistence, video guard
refusal, no-JavaScript navigation, public flag-off isolation, overflow, target
sizes, forced colors, reduced motion, and text spacing. Optional captures go
only to lifecycle-allocated external evidence storage.

## Preserved behavior

Public and flag-off Interview Studio rendering remains byte-comparable after
normalizing existing static-asset fingerprints. Browser-local storage keys and
records, History meaning, question/session behavior, APIs, request payloads,
provider behavior, authentication and safe return, private cache/indexing
rules, Quiet Preview, robots and sitemap behavior, and default-off feature
flags are unchanged.

## Boundaries

This package does not edit `app.py`, the shared shell, authentication,
safe-return logic, schema, migrations, providers, Profile, Workshop, Settings,
deployment files, feature configuration, identities, live data, or production.
It does not decide a broader Interview Studio redesign, cross-device settings,
session persistence, public enablement, or the future experience-polish
package.

The initial activation intentionally deferred
`docs/governance/PACKAGE_REGISTRY.json`. The later governed surface extension
added only that path, and this refreshed implementation registers the package
once under `current_protect` with reconciled category and total counts. The
pre-extension candidate and review remain provisional evidence only; final
acceptance depends on a fresh exact-SHA review of this post-extension branch.

## Acceptance

Acceptance requires the focused route/unit and browser suites, the inherited
shared-shell/auth/navigation/privacy regressions, the full repository suite,
governance and secret scans, exact external capture hashes, and a fresh
independent review of one immutable post-registry candidate SHA. Repository
merge is not deployment or live proof.
