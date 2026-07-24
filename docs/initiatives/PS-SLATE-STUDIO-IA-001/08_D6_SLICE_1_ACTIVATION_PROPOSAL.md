# PS-SLATE-STUDIO-IA-001 — D6 proposed Slice 1 activation

**Date:** 2026-07-23. **Author:** Codex at Pete's direction.
**Status update 2026-07-24:** **OWNER-ACTIVATED AND CODEX
MANAGER-ACCEPTED; controlled governance merge pending.** It is not yet
branched for runtime, implemented, merged, deployed, enabled, or live. Document
11 controls current roles and the current-main file correction.

## 1. Proposed package

- **Proposed ID:** `PS-SLATE-STUDIO-SLICE-1-001`
- **Name:** Protected Studio shell and Build Your Future frame
- **Roadmap unit:** Slice 1 only
- **Future runtime branch:**
  `work/2026-07-24-slate-studio-slice-1-shell`
- **Base:** current `origin/main` at the time Pete activates the package, never
  this direction branch's historical base
- **Designated manager:** active ChatGPT Work/Codex manager task
- **Sole implementation writer:** one bounded Codex writer assigned only after
  the controlled governance merge
- **Visual acceptance:** Pete plus the designated manager
- **Independent review:** one fresh review-only Codex task
- **Final audit / governance closeout:** the Codex manager

These roles implement Pete's 2026-07-24 instruction to keep the manager,
writer, and reviewer inside the active agent family. They do not waive the
single-writer or independent-review gates.

## 2. Member outcome

A signed-in member can open the protected Build Your Future route, understand
where they are, move between the correct global and Studio destinations, see
that the workspace is private, open their real published Slate when one
exists, and understand truthful loading, empty, permission, and unavailable
states.

The slice proves the shell and frame only. It does not prove that Slate Board,
selected work, editing, AI, experiments, practice grounding, or publication
exists.

## 3. Proposed runtime scope

### Build

- protected `GET /app/studio/build-your-future`;
- shared signed-in Studio shell;
- global `My Slate | Slate Studio | Community` navigation;
- Studio `Workshop | Build Your Future | Interview Studio` navigation;
- Workshop link to protected `/app`;
- public/browser-local disclosure on the current `/interview-studio` handoff;
- page identity, sandbox copy, and private workspace status;
- real `View published Slate` link or honest no-published-Slate state;
- dominant Build Your Future workspace frame;
- truthful ready, real loading/retry, empty when admitted by contract,
  unauthenticated, permission-denied, unavailable, and recovery states;
- light/dark theme parity, no-JavaScript baseline, responsive reflow, focus,
  forced-colors, and reduced-motion behavior; and
- private `Cache-Control: private, no-store`.

### Explicitly do not build

- Board reads beyond the minimum state-admission contract;
- Board cards, selection, connectors, zoom, fullscreen, arrange, drag, layout,
  or persistence;
- selected-work detail, evidence, draft/published wording comparison, or
  Work–Story–Future lenses;
- editing, save, undo, stale-write handling, Voice, Upload, or Capture changes;
- experiments, Try Another Future, future postcard, evidence kit, Compass, or
  Receipts;
- Ask Slate UI, retrieval, grounding, proposals, or persistence;
- authenticated practice grounding, history, feedback expansion, rename, or
  `/app/interview-studio`;
- publishing, audience preview, visibility changes, or Story/Project/resume
  placements;
- Community pulse;
- public Résumé, My Story, Interview Studio, Slate Board, Community, homepage,
  or public-page visual alignment;
- Bible/Roadmap or shared-governance edits in the implementation branch unless
  a separate controlled reservation explicitly says otherwise.

## 4. Feature exposure

Propose a package-specific default-off server flag:

`PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED=false`

Reason: the package adds a protected route and user-facing visual contract that
must be deployed dark, verified, visually accepted, and deliberately enabled
without changing the current `/app` or public behavior.

Required behavior:

- flag off: the new route returns neutral `404`; no nav link, template, asset,
  bootstrap data, or private payload is emitted;
- flag on, signed out: safe redirect to sign-in with the exact same-origin
  return path;
- flag on, signed in: server-resolved owner shell and frame;
- partial service failure: no fixture fallback; truthful unavailable state;
- enabling in production is a separate Pete/manager decision after flag-off
  release evidence.

The proposal does not change configuration or create the flag now.

## 5. Minimum server contract

Slice 1 should use one finite, server-owned frame view model:

```text
studio-frame.v1
member:
  display_name
  account_url
navigation:
  my_slate_url
  community_url
  workshop_url
  build_your_future_url
  public_interview_studio_url
workspace:
  access_state = ready | denied | unavailable
  content_state = not_connected | empty | has_supported_items
published_slate:
  state = available | not_published | unavailable
  url = present only when state=available
theme:
  light | dark
```

Contract rules:

- identity and every URL are server-derived;
- `has_supported_items` does not return item content in Slice 1;
- `empty` is admitted only after authorized successful evaluation of the exact
  supported-source set;
- `not_connected` renders unavailable/not-connected language, never empty;
- no profile slug, owner ID, published URL, or permission comes from query
  parameters or browser state;
- no Pete fixture, Board note, résumé row, Project, Moment, or draft text is
  included;
- published state is read-only and cannot be changed by this slice; and
- no client request is necessary to decide initial ownership or permission.

If the future architecture review cannot justify the supported-item state
without entering Slice 2, remove `empty | has_supported_items` from the runtime
contract and ship only `not_connected`. Preserve the visual empty state for
later review; do not fake it.

## 6. Proposed writable runtime files

Exact paths are proposals for the future implementation package and must be
reconfirmed against then-current `origin/main`.

- `app.py` — one bounded default-off
  `PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED` configuration entry;
- `auth_routes.py` — protected route, flag-off neutral boundary, no-store
  response, and server view-model allocation only;
- `templates/owner_studio_build_your_future.html`;
- `templates/partials/owner_studio/_global_header.html`;
- `templates/partials/owner_studio/_studio_navigation.html`;
- `templates/partials/owner_studio/_workspace_status.html`;
- `templates/partials/owner_studio/_build_future_frame.html`;
- `templates/partials/owner_studio/_state_panel.html`;
- `static/css/owner-studio.css`;
- `static/js/owner-studio.js` only if progressive enhancement is necessary
  for a real retry or existing theme behavior; the baseline cannot depend on
  it;
- `tests/test_owner_studio_slice1.py`;
- `tests/test_owner_studio_slice1_accessibility.py`;
- `docs/initiatives/PS-SLATE-STUDIO-SLICE-1-001/**`;
- `artifacts/ps-slate-studio-slice-1-001/**`.

`templates/base.html` is not automatically writable. Prefer a route-local
Studio shell so the slice does not modify public/global navigation. If current
architecture proves a shared conditional is unavoidable, the future manager
must name the exact bounded edit and collision review before writing it.

No new service, API, schema, migration, storage, or JavaScript state store is
proposed for Slice 1.

## 7. Forbidden runtime files and surfaces

- `owner_routes.py`, `peerslate_api.py`, `identity.py`;
- `services/**`, SQL, migrations, infrastructure, deployment configuration,
  environment settings, or production flags;
- existing `templates/owner_home.html`,
  `templates/owner_workspace.html`, and Owner Home partials unless Pete
  separately expands Slice 1 to include the Workshop convergence;
- existing public Résumé, My Story, Slate Board, Interview Studio, Community,
  homepage, Capture, Journal, Moment, Placement, Project, and Ask Pete files;
- shared global CSS/JavaScript and approved visual-baseline assets;
- controlled Bible/Roadmap and shared governance without a separate written
  reservation;
- the locked JPG files, except read-only comparison.

A future manager stops if the desired shell cannot be implemented within this
reservation.

## 8. Reused contracts

- existing trusted-session identity and safe sign-in return;
- protected `/app` owner route family;
- current account/sign-out behavior;
- current public member Slate route resolution, when authoritative;
- current Community route;
- current public `/interview-studio` route and browser-local truth language;
- Deep Navy Gold tokens and existing approved theme mechanism where reusable
  without changing other pages;
- Owner Visual Integrity and Context Rail standards;
- locked Build Your Future desktop files plus document 07;
- private no-store response policy.

The finite `owner-home.v1` data service is not consumed by the Build Your
Future frame in Slice 1. Workshop convergence is a later bounded edit unless
Pete explicitly includes it in the activated package.

## 9. Acceptance requirements

### Contract and privacy

- flag off yields neutral 404 and emits no Slice 1 assets or data;
- signed-out route redirects to sign-in with a safe exact return;
- two real owners receive only their own server-derived identity and URLs;
- payload and rendered HTML contain no other owner's values;
- no browser-supplied owner, slug, URL, or capability decision is trusted;
- private response is `private, no-store`;
- unavailable and permission states contain no private payload;
- no publication or mutation endpoint exists.

### Navigation and truth

- exact global and Studio labels and current-state semantics;
- Workshop resolves to `/app`;
- Build Your Future resolves to its protected canonical route;
- Interview Studio resolves to the current public route and discloses
  public/browser-local history;
- My Slate and View published Slate use only real server-resolved destinations;
- no dead link appears for a member without a published Slate;
- no control implies Board, editing, Ask Slate, experiments, grounded practice,
  or publication is active.

### Visual and accessibility

- accepted desktop light/dark parity with the locked hierarchy;
- tablet, 390 px, 320 px, short landscape, and 200% reflow;
- keyboard, skip link, visible focus, screen-reader names/order,
  forced-colors, reduced-motion, and no-JavaScript;
- ready/not-connected, real loading/retry, admitted empty,
  unauthenticated, permission, unavailable, published, and not-published
  evidence;
- long name/localized copy and browser text scaling;
- no relationship curves except a later selected-item state;
- no horizontal page scroll, clipped navigation, or inaccessible fake
  disabled controls.

### Regression and complete-diff review

- existing `/app`, `/interview-studio`, Community, public Slate, homepage, auth,
  account, theme, and non-Studio routes unchanged with the flag off;
- focused tests plus the repository's then-current full guardrail suite;
- complete diff against the exact future `origin/main` base;
- implementation screenshots compared with both locked desktop files and the
  accepted Slice 1 responsive/state mockups;
- every intentional deviation recorded;
- self-certification `Pass`, `Conditional`, or `Fail`;
- Pete/manager visual acceptance before PR; and
- Opus review plus Claude final audit per the owner-set pipeline.

## 10. Homepage assessment

The logged-out homepage currently presents Interview Studio, Slate Board, and
public Slate material, but it does not present the protected Build Your Future
product as live. Slice 1 changes none of those public surfaces or their
capabilities.

At the future release gate, rerun the homepage assessment. If the homepage has
begun to present Build Your Future or the protected Studio, activate an exact
downstream parity package; do not add public-page alignment to Slice 1.

## 11. Activation conditions

Pete may activate Slice 1 only after:

- accepting D3;
- accepting document 07 and the actual responsive/state mockup set (Pete's
  visual acceptance is recorded in document 10; designated-manager receipt
  remains open);
- activating the necessary Bible/Roadmap direction through controlled
  governance;
- confirming current `origin/main`, branch, manager, writer, and file
  reservations;
- approving the flag and `studio-frame.v1` admission rules;
- confirming there is no active-writer collision; and
- explicitly authorizing the runtime package.

Pete completed owner activation and the Codex manager completed the package
review in document 11. The remaining entry condition is the controlled
governance merge. No runtime branch is created before that merge.

## 12. Single next action

Complete and merge the controlled-governance activation recorded in document
11. Then create the fresh Slice 1 runtime branch from that exact
`origin/main`, assign its one Codex writer, and implement only this bounded
shell/frame slice.
