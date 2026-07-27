# PS-AUDIT-WEB-001 - Cross-site responsive architecture and implementation audit

**Owner:** Pete
**Package-designated governance manager for setup:** current ChatGPT Work/Codex
task
**Setup writer:** Codex on
`work/2026-07-26-responsive-site-audit-001`
**Setup base:** Azure `origin/main` at
`453662adc022b6ea0b1b38208c7100697d119a8b`
**Future audit manager, visual inspector, implementation writer, and fresh
reviewer:** unassigned until activation
**Status:** Planned gate established; no route review, visual lock, runtime
implementation, release, or production claim is made by this package setup
**Roadmap authority:** the existing `PS-AUDIT-WEB-001` allocation for the
public/authenticated/mobile/desktop route and state inventory
**Runtime authority:** none

## 1. Owner decision and purpose

Pete directed PeerSlate to establish a deliberate whole-website responsive
review after the purpose and intended desktop direction of the selected pages
are settled. The review must examine how the actual website composes at tablet,
phone, short-landscape, zoom/reflow, and representative desktop sizes instead
of allowing each implementation writer to improvise breakpoints independently.

This package creates two connected gates:

1. **Responsive Architecture Lock** - review and owner-lock the cross-site
   shell, navigation, content order, component transformations, and
   route-specific responsive/state authority before the selected release wave
   is considered ready for broad visual implementation.
2. **Responsive Implementation Audit** - inspect the real implementation across
   the same route/state/viewport matrix before a major launch, public beta, or
   other owner-designated website-wide visual completion claim.

The first gate prevents avoidable rework. The second proves that the browser
implementation matches the approved responsive system. Neither replaces the
responsive, accessibility, truth, security, or visual acceptance required by
each page's own package.

This is a responsive **website** gate. It does not authorize or specify a native
mobile application.

## 2. Timing and activation

Record this package now so the gate cannot be lost. Activate it only when all of
the following are true for a named release wave:

- the exact route and surface inventory for that wave is frozen;
- each included page has an approved page-purpose/non-redundancy inventory;
- each included page has an exact primary desktop visual authority or a
  recorded missing-authority blocker;
- the applicable signed-in and public route-map decisions are ready for review;
- `PS-SHELL-001`, Overview width authority, the Context Rail standard, and any
  route-local shell exceptions are reconciled enough to compare as one system;
- active implementation lanes have returned exact branches/SHAs and released
  overlapping shell, navigation, template, CSS, and test files;
- one manager, the visual inspector, the fresh audit reviewer, writable files,
  forbidden files, fixtures/accounts, environments, and evidence locations are
  recorded; and
- no included page is presented as complete merely because its desktop concept
  is approved.

The intended sequence is:

```text
page purpose and primary desktop direction settle
        ->
Responsive Architecture Lock
        ->
bounded page/shell implementation with page-local responsive evidence
        ->
Responsive Implementation Audit
        ->
owner/manager website-wide responsive acceptance
        ->
major launch or public-beta readiness decision
```

An individually bounded page may still release through its own complete package
before the master audit. It may not be used to claim that the whole website's
responsive architecture or implementation has passed.

## 3. Exact audit manifest

At activation, create a versioned route/state/viewport manifest from the real
Flask route map, current navigation, feature flags, and active product packages.
Do not rely on a remembered page list.

The manifest includes, as applicable:

- canonical logged-out marketing and explanation routes;
- public member Slate, resume, Story, Work, Project, Community, Interview, and
  other public-product routes that exist in the selected wave;
- sign-in, sign-out, callback-safe return, denied, expired-session, and
  unavailable boundaries without exercising real credentials in evidence;
- protected owner Home, Settings, Journal, Capture, Studio, Goal, Project, and
  other routes that are actually released or admitted to the review;
- homepage product projections and their canonical destination links;
- route redirects, not-found, permission-denied, feature-off, maintenance, and
  storage/service-unavailable states that affect orientation or recovery;
- the shared public shell, authenticated shell, contextual navigation,
  Context Rail or mobile twin, footer, theme behavior, dialogs/sheets, and
  persistent actions; and
- every explicitly excluded or retired route with its reason and disposition.

For each included route, enumerate the meaningful states required by its own
package. At minimum consider loading, processing, empty, standard, rich or
many-item, long-content, missing-media, success, validation failure, provider or
network failure, retry/recovery, permission denied, unavailable, stale/conflict,
feature-off, light theme, and dark theme where the route supports them.

The manifest records:

- canonical route and owner/viewer/audience mode;
- purpose and dominant object/action;
- source visual authority, exact file/hash, frame/state, and intended viewport;
- capability and truth status;
- required states;
- required viewports and browser/device coverage;
- expected shell/navigation/content-order behavior;
- evidence path and reviewer;
- result: `Pass`, `Conditional`, `Fail`, `Excluded`, or `Not Applicable`; and
- owner, correction, recheck, and next action for every non-pass row.

## 4. Minimum CSS viewport and device matrix

Evidence uses actual browser CSS viewports. A portrait concept board, monitor
diagonal, operating-system display scale, device-pixel screenshot size, CSS
`zoom`, or transform fitting is not viewport proof.

Minimum cross-site matrix:

| Context | CSS viewport | Purpose |
|---|---:|---|
| Reference desktop | 1440 x 900 | Primary desktop composition and shared-shell comparison |
| Wide desktop | 1920 x 1080 | Wide-stage behavior, readable measure, and intentional outer space |
| Tablet landscape | 1024 x 768 | Navigation, two-column transitions, and touch behavior |
| Tablet portrait | 820 x 1180 or an approved equivalent | Deliberate tablet composition rather than compressed desktop |
| Large phone | 430 x 932 | Large-phone wrapping, controls, and safe-area behavior |
| Primary phone | 390 x 844 | Primary touch-mobile evidence |
| Minimum supported phone | 320 x 568 | Minimum-width containment and priority decisions |
| Short landscape | 844 x 390 or an approved equivalent | Reachability when height is constrained |
| Browser reflow | 200 percent zoom with effective CSS viewport recorded | One-dimensional reflow, text growth, and control reachability |

Add 2560 x 1440 and 3840 x 2160 CSS-pixel evidence where an included page's
authority requires wide-desktop proof. Add intermediate widths when a component
changes composition there or when real usage evidence identifies another
material boundary. Breakpoints are selected from content behavior, not popular
device labels alone.

Before broad launch, the activated audit records the supported browser/engine
matrix and includes at least:

- current Chromium-based desktop coverage;
- WebKit/Safari representation for relevant Apple use;
- Firefox when it remains in the declared support matrix; and
- one real touch-device task walk in addition to browser emulation.

Any unsupported browser or device class is documented as an owner-approved
product support decision, not silently omitted.

## 5. Gate R1 - Responsive Architecture Lock

### Review subjects

Review every route/state row for:

- cross-site information architecture and whose space is being viewed;
- public versus authenticated shell and audience/privacy clarity;
- desktop/mobile route labels, grouping, order, return paths, and persistent
  Capture behavior without turning Capture into a destination;
- consistent shell geometry without forcing every room into one arbitrary
  content width;
- deliberate content priority and semantic source order;
- transformation of grids, rails, tables, timelines, canvases, document panes,
  AI panes, and continuation controls;
- Overview versus Focus/task-mode composition;
- contextual rail-to-chip-row behavior and prevention of duplicate navigation;
- sticky or fixed controls, bottom bars, sheets/dialogs, virtual keyboards,
  safe areas, and short-height reachability;
- touch targets, pointer alternatives, hover independence, focus order,
  screen-reader landmarks/status, forced colors, reduced motion, and 200-percent
  reflow;
- readable type, line length, media crop/focal behavior, responsive images,
  missing media, long names, long content, and many items;
- theme parity and truthful loading, processing, denied, unavailable, failure,
  conflict, retry, and recovery composition;
- primary task completion when AI, media, or a provider is unavailable; and
- homepage-to-product responsive parity where the homepage presents that
  experience.

Mobile is a deliberate task composition, not a shrunken desktop canvas. Content
may reflow, reorder only when semantic meaning remains correct, disclose
progressively, or move into an accessible sheet when the owner-locked direction
permits it. Essential capability, privacy context, state, and recovery may not
disappear to make the layout fit.

### Authority and decision

ChatGPT creates any missing or materially revised responsive/state visual
authority. Pete locks the exact durable files/hashes. Writers and audit
reviewers may identify defects and capture evidence, but they do not invent a
responsive interaction model.

Gate R1 closes `Pass` only when:

- the route/state/viewport manifest is complete;
- required responsive and state authorities are exact and owner-locked;
- the cross-site shell and route-map decisions are explicit;
- every known exception is named with a reason and owner;
- page-specific packages can trace their implementation evidence to the master
  decisions without losing their own authority; and
- Pete and the designated manager accept the architecture lock.

A route with missing required responsive/state authority is `Conditional` or
`Fail` and remains blocked from broad visual implementation. The gate does not
paper over the gap with CSS assumptions.

## 6. Gate R2 - Responsive Implementation Audit

Run R2 against an exact integrated branch or deployed candidate SHA after the
included page and shell packages complete their page-local responsive evidence.
Use a fresh review-only auditor as required by the full-site audit policy.

Evidence includes:

- the exact route/state/viewport manifest and candidate SHA/environment;
- named full-browser screenshots, not cropped concept boards alone;
- measured shell, stage, primary content, rail, dialog/sheet, and overflow
  geometry where applicable;
- computed `zoom`, transforms, font size, line measure, focus visibility, target
  size, and horizontal-scroll checks where relevant;
- keyboard, screen-reader task walk, touch, forced-colors, reduced-motion,
  orientation, and 200-percent reflow evidence;
- long-content, many-item, missing-media, failure/retry, denied, unavailable,
  feature-off, and theme evidence;
- owner-derived authorization and zero protected-payload checks for protected
  states;
- real-member validation with Pete and at least one generic second fixture or
  account where authenticated behavior is in scope;
- a complete core task on the primary phone without a product tour;
- a cross-route consistency register for navigation, shell, type, spacing,
  state language, privacy context, and persistent actions;
- page-authority compare/refine evidence or Pete-run correction evidence under
  `OWNER_VISUAL_INTEGRITY_STANDARD.md`; and
- every mismatch, correction, focused recheck, owner, and final result.

R2 fails when any included critical journey has:

- unintended page-level horizontal scrolling or clipped essential content;
- inaccessible or unreachable controls;
- a desktop canvas merely scaled down;
- lost identity, audience, privacy, capability, or state context;
- duplicate or contradictory navigation;
- a material unapproved visual-direction change;
- missing failure/recovery behavior;
- a cross-user or protected-payload exposure;
- an unreviewed supported-browser failure; or
- an unresolved accessibility blocker.

After correction, run one focused recheck against the same rows. Do not create a
recursive audit. R2 closes only with Pete's website-wide responsive visual
acceptance, manager scope/readiness acceptance, and the fresh auditor's
`Pass`.

## 7. Relationship to existing controls

### Page-local visual gates

V0-V4 remain mandatory for every user-facing package. This master gate samples
and integrates their evidence; it does not postpone mobile work until the end,
replace page-specific authority, or replay every prior technical review.

### PS-SHELL-001

`PS-SHELL-001` owns shared shell implementation: width behavior, headers,
two-tone ground, type, and approved shared context/navigation components.
`PS-AUDIT-WEB-001` owns the cross-route responsive decision and audit matrix.
Neither package may treat the older approximate 1120-1200-pixel stage as a
universal fixed rule. The final shell uses owner-locked, measured, fluid
relationships and reconciles the Overview wide-desktop authority before runtime
implementation.

### Route-map gate

The still-open desktop/mobile route map is an input to Gate R1. This package
does not invent permanent navigation merely to complete an audit. It records
the owner-approved route-map decision or keeps affected rows blocked.

### Periodic audits

R2 may satisfy the responsive/visual/accessibility portion of the next
checkpoint, phase-boundary, or full-site audit only when the manager records the
same exact scope, reviewer, SHA, routes, states, viewports, evidence, and result
in `AI_DELIVERY_AUDIT_REGISTER.md`. Reuse the evidence; do not run a duplicate
ceremony.

### Release meaning

This setup is documentation only. It changes no route, template, CSS,
JavaScript, data, schema, feature flag, deployment configuration, or production
behavior. A passed R1 is design/architecture readiness. A passed R2 is
integrated responsive implementation evidence. Neither alone proves Azure
deployment or live production behavior.

## 8. Setup ownership and file boundary

For this governance setup only, the current ChatGPT Work/Codex task reserves:

- `docs/initiatives/PS-AUDIT-WEB-001/**`;
- `docs/initiatives/PS-SHELL-001/README.md`;
- `docs/governance/CURRENT_BASELINE.yaml`;
- `docs/governance/CURRENT_STATE.md`;
- `docs/governance/ACTIVE_INITIATIVES.md`;
- `docs/governance/DECISIONS.md`;
- `docs/governance/DOCUMENT_CONTROL.md`;
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`;
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md`;
- `docs/AI_WORKFLOW.md`; and
- focused governance guardrail tests.

No other active lane is authorized to write those files until this setup branch
is handed off or relinquished. The setup must not touch runtime routes,
templates, CSS, JavaScript, data, authentication, APIs, migrations, feature
flags, Azure configuration, visual assets, screenshots, or another initiative's
package-local records.

## 9. Setup acceptance and next action

Setup acceptance requires:

- all new pointers agree that `PS-AUDIT-WEB-001` is planned, not active;
- `PS-SHELL-001` explicitly coordinates with this package and no longer treats
  its old approximate stage width as binding;
- the Visual Integrity Standard and audit cadence link the master responsive
  gate without duplicating page-local review;
- focused governance and site-rule guardrails pass;
- the complete diff contains no runtime or unrelated changes; and
- the completion report distinguishes package creation from a completed audit.

After this setup is accepted and merged, continue current page-purpose and
visual-authority work. Activate Gate R1 only when the named release wave meets
section 2. Do not start a route-by-route audit against an unstable or incomplete
page set merely because the package now exists.
