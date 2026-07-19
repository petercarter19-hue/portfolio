# PS-OWNER-HOME-VIEWER-GATE-001 Visual Truth Handoff

Status: early Gate B truth checkpoint for ChatGPT Work. This document constrains future experience design; it does not choose a final composition or authorize implementation.

## Authority and current boundary

- Source baseline: Azure DevOps origin/main at 31864e43287d7cefb5a0d1c0441e94bec0bd6b1f, Bible v2.5, Roadmap v2.4, and the Owner Visual Integrity Standard.
- Named future visual authority: the approved July 18, 2026 Owner Home and Journal/My Slate boards under docs/governance/approved_owner_visual_baseline/. Their hierarchy and quality are binding when implementation is authorized; their sample content is illustrative, not product data.
- Authority conflict requiring owner/manager reconciliation: those boards use a dark outer shell and legacy-looking `Shared`/projection controls, while the current repository authority is light-first Deep Navy Gold and the Roadmap requires explicit selected-person, connection, authenticated-member, and public modes. Preserve the boards' hierarchy, interaction promise, and finish, but do not copy their theme or audience labels until ChatGPT Work and Pete approve a production-intent reconciliation. The boards also do not authorize Journal implementation.
- Current implementation truth: signed-in Settings, private Capture, owner review and confirmation of canonical Moments, and private Placement references exist. There is no finite signed-in Owner Home, reusable audience-aware viewer projection, real My Slate preview, connection grant/publication system, finite connection Feed, or governed What PeerSlate noticed service.
- This package is architecture and planning only. It changes no route, application behavior, audience, publication state, navigation, data, schema, or visual design.

## What Owner Home may truthfully show

The future Home may render only items returned by a server-authorized owner aggregation. The first implementation may use real, owner-scoped identity, Capture lifecycle, Moment review/confirmation, and Placement-reference facts that the current backend can supply. It may not infer a public audience, connection, publication, downstream placement display, or AI insight from those records.

Permitted content categories, subject to real query support and eligibility rules:

1. one persistent Capture entry action;
2. a bounded count and bounded list of real private Captures or Moment proposals that need owner review;
3. at most one recent confirmed Moment;
4. at most one resurfaced confirmed Moment only after a deterministic, documented eligibility rule exists;
5. at most one What PeerSlate noticed item only after the governed insight lifecycle, authorized source-set retrieval, support, uncertainty, correction, dismissal, staleness, and revocation contracts exist;
6. at most one connection item only after real relationship, audience, publication, and revocation contracts exist; and
7. at most one next step derived from deterministic eligibility and permitted source state, with no automatic save, placement, share, or publication.

An unavailable category consumes no visual slot. It is omitted unless an honest, useful empty or unavailable state helps the owner understand the product. Home must never fill a missing category with fixture activity.

## Finite Home content budget

The maximum default response is:

- 1 primary Capture action;
- up to 3 review items, with a single route to the bounded remainder;
- 1 recent Moment;
- 1 resurfaced Moment;
- 1 governed insight;
- 1 authorized connection item; and
- 1 next step.

Maximum content objects: 9, excluding shell context, status messaging, and retry controls. Categories with no eligible real item are omitted or represented by one concise state; they are not backfilled. No cursor, endless pagination, infinite scroll, activity filler, trending rail, popularity count, streak, or simulated community density belongs on Home.

## Dominant owner action

Capture is the one dominant owner action. The truthful destination is the existing protected private Capture flow. Secondary Home items may lead to review or inspection, but they must not visually compete with Capture or imply that a private Capture is already a Moment, Placement, share, or publication.

## Viewer modes and retrieval truth

| Viewer mode | Trusted identity/context | What may be retrieved | Current status |
|---|---|---|---|
| Owner | Signed-in internal user resolved from the trusted server session; subject is the same internal user | Owner-authorized private workspace records and owner controls, according to each service's lifecycle rules | Identity, Settings, Capture, Moment review, and Placement foundations are live; Home and My Slate preview are future |
| Selected person | Signed-in internal viewer plus a valid, active, explicit subject-to-viewer grant for the requested projection and purpose | Only the granted projection fields, pinned versions, permitted media, and permitted relationships | Future; no current generic selected-person grant/projection service |
| Connection | Signed-in internal viewer plus a valid active connection state and content published to the connection audience | Only connection-audience projection fields and permitted interaction metadata | Future; existing Feed/Community visuals are not proof of relationships or grants |
| Authenticated member | Signed-in internal viewer; no owner or relationship privilege implied | Only projections deliberately published to the authenticated-member audience | Future; sign-in alone grants no access to another member's private records |
| Public | No member session required; subject resolved through an approved public identifier | Only deliberately public, published projection payloads | Pete-specific public fixture routes exist; a reusable multi-user public Slate projection does not |

Frontend state, a route slug, a query parameter, cached data, or a preview selector never proves a viewer mode. The server resolves the subject, viewer, relationship/grant, audience, purpose, lifecycle, and permitted fields through an authorization-only boundary before retrieving canonical content from SQL, search, media, cache, or AI systems.

## Truthful capability and state labels

Use concrete labels that describe enforcement and lifecycle:

- Owner view - private workspace controls are available to the signed-in owner.
- Preview as: Public / Member / Connection / Selected person - a future real preview produced by the same authorization and projection path as that viewer.
- Private - not retrievable by another viewer.
- Permissioned - retrievable only through the named active grant and audience.
- Public - deliberately published and retrievable through the public projection.
- Unpublished - no viewer projection exists; do not show a decorative preview as if it were live.
- Coming later or Unavailable - the backend contract is not implemented or not enabled.
- Loading - a request is pending and no prior payload is represented as current.
- Stale - the displayed response is no longer current and protected actions are disabled until refresh.
- Revoked - a previously valid grant or publication no longer authorizes retrieval.
- Deleted - the authoritative source or projection is deleted; no copied content remains in the payload.
- Failed - the authorized request failed without falling back to broader or cached private data.

Avoid vague labels such as shared, visible, live, verified, matched, recommended, or AI noticed unless the exact audience, state, source, and enforcement behind the word are present and inspectable.

## Prohibited or misleading visual claims

- Do not show raw Captures, private Moment proposals, private sources, private insights, owner settings, audit data, or owner controls in any non-owner response.
- Do not show a Placement reference as proof that destination content is visible, published, or available to a viewer. The current Placement foundation grants no access and copies no content.
- Do not show selected-person, connection, member, or public content until a real server-side grant/publication query exists.
- Do not present the current Pete fixture pages as a generic multi-user projection system.
- Do not label deterministic resurfacing as AI insight; do not label fixture or hand-authored copy as What PeerSlate noticed.
- Do not imply that an insight exists merely because enough private data might exist. The governed insight record, permitted support, uncertainty, lifecycle, and member controls must all be real.
- Do not simulate community activity, connections, audience counts, comments, notifications, or matching.
- Do not render private fields and hide them with CSS or client logic.
- Do not reuse a preview payload across a different subject, viewer, audience, grant version, or authorization epoch.
- Do not add a new permanent navigation layer or decide the final public/member route map in this package.

## Required non-happy-path states

Every future implementation and design authority must cover:

- Home empty: no review items or confirmed Moments; Capture remains available and no activity is fabricated.
- Category empty: category omitted or one concise explanation, without consuming another category's budget.
- Viewer empty: authorization succeeds but the subject has published no eligible items to that audience.
- Loading: skeleton or progress language exposes no prior viewer's content and announces status accessibly.
- Restricted: an established viewer context exists but the requested projection or item is not granted; no private title, count, media, timestamp, or reason leaks.
- Unpublished: the owner has no published projection for the selected audience; preview explains that the real viewer would receive an empty/unavailable result.
- Revoked: access is invalidated immediately across route, API, media, cache, and preview paths; previously rendered private content is cleared.
- Deleted source or projection: payload contains only the minimum lifecycle response allowed by policy and never a stale content copy.
- Stale response or write conflict: protected actions stop, the context is re-authorized, and the member can refresh without silent overwrite.
- Session expired: protected data is cleared and the safe sign-in return path does not encode private payloads.
- Dependency failure: the core owner shell and Capture path remain safe; unavailable categories fail independently.
- Timeout or network failure: retry repeats the same bounded authorized request and does not broaden scope or duplicate state changes.
- Retry failed: preserve truthful failure, support/reference ID when safe, and a non-destructive return path.
- Unknown or direct-object request: fail closed with non-enumerating behavior; do not reveal whether a private subject or item exists.

## Navigation decisions still unresolved

- Final canonical route shapes for owner Home, generic viewer Slate, and preview.
- Whether preview changes audience in place, uses a dedicated route, or uses a short-lived server-held preview context.
- The stable public member identifier and rename/history policy.
- Selected-person grant entry, management, expiry, and return paths.
- Connection/profile/Feed route ownership once Phase 8 is authorized.
- How the existing Pete-specific public Story, resume, and Slate routes converge later without breaking current deep links.
- Desktop navigation composition and whether any future View As control belongs in the shell or in My Slate. Mobile remains conceptually Home, Journal, Capture, Slate, More, but Journal UI is still on hold.

These questions require a later approved route map and design package. This architecture gate may define contracts and constraints, not settle the final composition.

## Generic fixture requirements

- Provide at least two distinct owner profiles plus viewer identities; Pete and Danielle may be founding-alpha validation participants but not reusable constants.
- Use opaque identifiers and generic data builders; no reusable component may assume Pete's name, employers, dates, roles, metrics, education, skills, profile slug, relationship, or publication state.
- Cover zero, one, maximum, and over-budget eligible records; long titles/body text; missing optional media; deleted sources; stale versions; revoked grants; and mixed lifecycle states.
- Include owner, unrelated signed-in member, active connection, expired/revoked connection, selected person with narrow grant, selected person with expired grant, and signed-out public viewer.
- Make every fixture label explicit: test fixture, prototype content, or demonstration. Fixture data must never appear in production telemetry or be described as live member activity.

## Checkpoint decision

Conditional pass for truth definition. The future visual/design lane may proceed only after the complete architecture package confirms current service contracts, payload schemas, negative-access behavior, performance budgets, and unresolved route/authorization decisions. No implementation or final visual composition is authorized by this checkpoint.
