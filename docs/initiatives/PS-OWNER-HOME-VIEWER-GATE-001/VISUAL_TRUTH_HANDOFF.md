# PS-OWNER-HOME-VIEWER-GATE-001 Visual Truth Handoff

Status: early Gate B truth checkpoint for ChatGPT Work. This document constrains future experience design; it does not choose a final composition or authorize implementation.

## Authority and current boundary

- Source baseline: original architecture audit at Azure DevOps `origin/main` `31864e43287d7cefb5a0d1c0441e94bec0bd6b1f`, synchronized for this owner-direction update through current `origin/main` `5cc5b69346ee354bcc36248f7ee5724ce13c9d08`; Bible v2.5, Roadmap v2.4, the Owner Visual Integrity Standard, and the now-released Voice capability-preview precedent at application commit `864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82`.
- Named future visual authority: the approved July 18, 2026 Owner Home and Journal/My Slate boards under docs/governance/approved_owner_visual_baseline/. Their hierarchy and quality are binding when implementation is authorized; their sample content is illustrative, not product data.
- Authority conflict requiring owner/manager reconciliation: those boards use a dark outer shell and legacy-looking `Shared`/projection controls, while the current repository authority is light-first Deep Navy Gold and the Roadmap requires explicit selected-person, connection, authenticated-member, and public modes. Preserve the boards' hierarchy, interaction promise, and finish, but do not copy their theme or audience labels until ChatGPT Work and Pete approve a production-intent reconciliation. The boards also do not authorize Journal implementation.
- Owner direction, 2026-07-19: approved Roadmap capabilities that belong in the intended experience must remain present in the next production-intent composition even before their backend is live. Follow the accepted Voice capability-preview pattern: preserve the intended feature's real visual silhouette and location, make it genuinely disabled, add a visible **Coming later** label, provide equivalent screen-reader text, and show no fabricated content or working-state behavior. Future capability does not mean visually absent.
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

An unavailable **record** never becomes fixture activity. An approved future **capability** that belongs in the selected composition still occupies its intended slot as a truthful capability preview labeled **Coming later**. The preview contains no member, insight, connection, count, recommendation, timestamp, or simulated result. It is a disabled presentation state, not an empty-data state and not authorization.

## Finite Home content budget

The maximum default response is:

- 1 primary Capture action;
- up to 3 review items, with a single route to the bounded remainder;
- 1 recent Moment;
- 1 resurfaced Moment;
- 1 governed insight;
- 1 authorized connection item; and
- 1 next step.

Maximum content objects: 9, excluding shell context, status messaging, and retry controls. A full-size capability preview occupies the same one category slot that its eventual real item would occupy, so showing **Coming later** does not increase the nine-object budget. Categories are never backfilled with sample activity. No cursor, endless pagination, infinite scroll, activity filler, trending rail, popularity count, streak, or simulated community density belongs on Home.

## Capability-preview rule: show future capability now

The next ChatGPT Work appearance pass should include approved future capabilities wherever they are important to understanding the intended product. Use the accepted Voice pattern rather than removing them:

- Render the intended control/card/rail/tab silhouette at production visual quality so later activation is a state change, not a redesign.
- Add a visible **Coming later** tag beside the feature name. Tooltip-only, icon-only, color-only, or footnote-only disclosure is insufficient.
- Use a genuinely non-operational control: native `disabled` plus `aria-disabled="true"` where applicable; exclude it from forms and backend requests; provide no working pointer/keyboard behavior.
- Accessible wording follows the pattern: **"[Feature] - coming later. Not yet available."**
- The capability may explain its future purpose in one concise sentence, but it may not contain a fabricated person, insight, recommendation, audience count, notification, activity, content record, success state, or generated output.
- If an explanatory detail is useful, provide a separately identified **Learn what is coming** disclosure/link. It must not look like the unavailable feature itself works.
- Presentation flags or design state never enable backend access. Later activation requires the real service, authorization, lifecycle, tests, release flag, and owner acceptance.

This rule requires the next appearance pass to show future `What PeerSlate noticed`, Connections, audience/viewer modes, My Slate preview, and other already approved Roadmap capabilities selected for that experience. It does not authorize unapproved scope, Journal implementation, Feed/Community data, publication, matching, or a new global navigation system.

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
- Preview as: Public / Member / Connection / Selected person - these modes may appear now as disabled **Coming later** capability previews; when activated later, each must use the same authorization and projection path as that real viewer.
- Private - not retrievable by another viewer.
- Permissioned - retrievable only through the named active grant and audience.
- Public - deliberately published and retrievable through the public projection.
- Unpublished - no viewer projection exists; do not show a decorative preview as if it were live.
- Coming later - an approved future capability is deliberately visible but genuinely disabled and not yet available.
- Unavailable - a normally live capability cannot currently be used because of state, configuration, or failure; do not use this label for planned future work when **Coming later** is more accurate.
- Loading - a request is pending and no prior payload is represented as current.
- Stale - the displayed response is no longer current and protected actions are disabled until refresh.
- Revoked - a previously valid grant or publication no longer authorizes retrieval.
- Deleted - the authoritative source or projection is deleted; no copied content remains in the payload.
- Failed - the authorized request failed without falling back to broader or cached private data.

Avoid vague labels such as shared, visible, live, verified, matched, recommended, or AI noticed unless the exact audience, state, source, and enforcement behind the word are present and inspectable.

## Prohibited or misleading visual claims

- Do not show raw Captures, private Moment proposals, private sources, private insights, owner settings, audit data, or owner controls in any non-owner response.
- Do not show a Placement reference as proof that destination content is visible, published, or available to a viewer. The current Placement foundation grants no access and copies no content.
- Do not show selected-person, connection, member, or public **content** until a real server-side grant/publication query exists. Their disabled, visibly labeled **Coming later** controls may be shown now.
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
- Category empty: a live category has no eligible record and says so concisely. A separately approved future category may instead render its disabled **Coming later** capability preview, without sample content or another category's data.
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

The appearance pass may reserve the intended visual position for a future destination and label it **Coming later**. It may not give that item a live URL, active-route state, notification count, sample content, or implied permission before the route map and backend exist.

## Generic fixture requirements

- Provide at least two distinct owner profiles plus viewer identities; Pete and Danielle may be founding-alpha validation participants but not reusable constants.
- Use opaque identifiers and generic data builders; no reusable component may assume Pete's name, employers, dates, roles, metrics, education, skills, profile slug, relationship, or publication state.
- Cover zero, one, maximum, and over-budget eligible records; long titles/body text; missing optional media; deleted sources; stale versions; revoked grants; and mixed lifecycle states.
- Include owner, unrelated signed-in member, active connection, expired/revoked connection, selected person with narrow grant, selected person with expired grant, and signed-out public viewer.
- Make every fixture label explicit: test fixture, prototype content, or demonstration. Fixture data must never appear in production telemetry or be described as live member activity.
- Capability previews use no fixture people or results. Their only content is the feature name, **Coming later** status, concise future-purpose copy, and optional truthful explanatory disclosure.

## Paste-ready instruction for the next ChatGPT Work appearance pass

> Redo the Owner Home production-intent appearance pass. Do not remove an approved future capability merely because its backend is not working yet. Follow the accepted Voice capability-preview pattern: keep the feature's intended production-quality silhouette and location, make the control genuinely disabled, add a visible **Coming later** label beside the feature name, and provide screen-reader wording such as "Connections - coming later. Not yet available." Do not include fabricated people, insights, recommendations, messages, activity, counts, publication states, or generated output. Show the future `What PeerSlate noticed`, Connections, audience/viewer options, and My Slate preview affordances this way where they belong in the composition. A future Journal/shell destination may also be visibly reserved as **Coming later**, but it has no active route or Journal content. Keep Capture dominant, keep the complete Home within the nine-object budget, make desktop and mobile intentional, and include loading, empty, failure, stale, restricted, and coming-later states. Reconcile the approved storyboard's hierarchy and finish with the current light-first Deep Navy Gold authority. Do not implement code or imply that a disabled preview is live.

## Checkpoint decision

Conditional pass for truth definition. The future visual/design lane may proceed only after the complete architecture package confirms current service contracts, payload schemas, negative-access behavior, performance budgets, and unresolved route/authorization decisions. No implementation or final visual composition is authorized by this checkpoint.
