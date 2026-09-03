# PS-OWNER-HOME-RETIREMENT-001

This Protected package retires both executable Capture-first Owner Home
implementations. `/app` remains the stable authenticated ingress and now renders
one neutral, shared-shell **My PeerSlate** launchpad. Capture remains available as
an ordinary destination; it is neither the signed-in home nor the dominant call
to action.

## Delivered contract

- A signed-out request to `/app` continues through the existing authentication
  flow, including the bounded same-origin `return_to` contract for valid protected
  deep links.
- A signed-in request to `/app` renders one server-generated launchpad with one
  main landmark and one page heading.
- The launchpad lists only implemented destinations: Workshop when its existing
  availability gate is on, My Opportunities, Interview Studio, Community,
  Capture, and Settings.
- The page does not create or link to `/app/profile`, does not present Pete's
  public profile navigation as the member's Profile, and explicitly says the
  launchpad is not a Profile.
- The old `PEERSLATE_OWNER_HOME_ENABLED` configuration path, Owner Home API,
  service, template, partials, stylesheet, script, evidence-capture script, and
  decorative image are removed. A stale injected flag cannot restore them.
- Account navigation that targets `/app` uses the temporary truthful label
  **My PeerSlate**.
- The launchpad works without JavaScript and uses a two-column grid that becomes
  one column on narrow screens and under high zoom. Every destination has a
  visible keyboard focus state and a generous target.

## Preserved boundaries

This package does not implement or enable Profile, change Capture, Settings,
Workshop, Interview Studio, Community, or My Opportunities behavior, or alter
their independent gates. Historical documentation, migrations, immutable
evidence, and the retired package records remain in place.

Merge is not deployment. This package grants no deployment, production
configuration, schema, identity, provider, or live-operation authority.

## Verification

The frozen candidate must pass focused authentication, safe-return, navigation,
security, accessibility, narrow-screen, 400-percent reflow, historical-migration,
and regression tests; package-registry integrity; complete-diff review; and an
independent exact-SHA review before merge.
