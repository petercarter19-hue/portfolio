# PeerSlate v1.3 Implementation Instructions

**Instruction version:** 1.0  
**Product baseline:** PeerSlate Company & Product Bible, Foundation Edition v1.3  
**Decision date:** July 16, 2026  
**Owner:** Peter Carter  
**Authoritative repository:** Azure DevOps `origin`; `origin/main` is production  
**Production deployment:** Azure Pipelines only

## Purpose

These instructions turn the v1.3 product direction into a safe, reviewable
implementation program. They do not authorize a one-branch rebuild, a visual
mock shell presented as working, or a parallel data model. Each package must
inspect the repository and deployed prerequisites it depends on, write an
explicit plan, obtain the required plan approval, and ship one coherent result.

## Authority and precedence

Use the following order when sources disagree:

1. Peter's current task-specific instruction.
2. `docs/AI_WORKFLOW.md` for Git, branch ownership, pull requests, deployment,
   cleanup, and handoff.
3. `PeerSlate_Company_and_Product_Bible_v1.3.docx` for product direction. Within
   the Bible, Appendix J governs the Journal Profile System where earlier
   prototype language conflicts.
4. `docs/PEERSLATE_SITE_RULES.md` as the concise, binding product guardrails.
5. This file for current package status, resolved interpretations, prerequisites,
   and execution order.
6. The current repository as evidence of what is actually implemented.
7. `docs/PEERSLATE_V12_IMPLEMENTATION_INSTRUCTIONS.md`, v1.2 initiative records,
   the personal-portfolio briefs, Foundation C, and Blueprint Light as historical
   implementation context only.

Never erase a historical package record to make it look current. Add a new
package or addendum. When a product ambiguity would change access, retention,
publication, identity, schema, or public claims, stop that package at the plan
gate and record the owner decision needed.

## Locked v1.3 interpretation

PeerSlate is a private-first, voice-first, AI-enabled system for capturing work
and life, understanding its meaning, improving expression, and deliberately
choosing what to share. The working professional is the primary user;
recruiters are a secondary downstream audience.

The owner loop remains the center:

> Capture something real -> let PeerSlate understand it -> review it -> keep it
> private or share it -> receive more value from it later.

The system rule is:

> Enter once. Link everywhere. Publish deliberately.

Version 1.3 additionally locks these behaviors:

- Journal is the member profile and the default audience-aware profile view.
- The Slate Vault remains the private structured source. Journal is a canonical
  profile and timeline projection; it is not a requirement to force every
  domain object into one physical Journal table.
- Item type, placement, audience, publication state, and typed content links
  are independent decisions.
- Journal and Community share one composer and one canonical record. Feed is a
  projection, not a second post-body database.
- `View As` uses the production authorization resolver and real server-filtered
  queries. Client-side concealment is not authorization.
- Photos is a private-first library and profile view with protected delivery.
- Connections are mutual people relationships. PeerSlate has no person-follower
  economy; an object subscription such as “Follow progress” is a distinct,
  explicitly scoped concept.
- AI may draft, structure, label, connect, summarize, and ask. It may not approve
  Sources, save a relationship, publish, or broaden an audience by itself.

## Required route and authorization boundary

The implementation plan for PS-PROFILE-001 must preserve two distinct contexts:

- `/app` and its descendants are the authenticated owner's private workspace.
- `/<slug>` and connected public-profile routes are audience-filtered member
  views. An owner visiting the public route may receive an owner bar and a
  selected `View As` mode, but the route must not become the private dashboard.

The target route family is:

| Context | Target route | Contract |
|---|---|---|
| Marketing | `/` | Honest product marketing and labeled demonstrations |
| Mission | `/peerslate` or approved replacement | Footer-only Why PeerSlate destination |
| Owner Home | `/app` | Authenticated private command center |
| Capture | `/app/capture` | Persistent owner capture path |
| Owner rooms | `/app/journal`, `/app/slate`, `/app/work`, `/app/studio`, `/app/community` | Protected member domains |
| Member profile | `/<slug>` | Journal-first, server-resolved viewer projection |
| Connected views | `/<slug>/story`, `/<slug>/work`, `/<slug>/slate`, `/<slug>/photos` | Same owner and authorization model |
| Optional modules | approved Ask AI, Interview, or Connections route/module | Only after their own access and status gates pass |

Do not finalize route names from this table without checking collisions in the
current Flask route map and writing the approved route/access diagram. Do not
use a browser-supplied owner id, username, query parameter, cookie field, or
`View As` value as authorization.

## Required data and audience contract

Before UI implementation, the package plan must define and test:

1. Trusted session identity and a server-derived viewer id.
2. Stable owner and canonical item identifiers.
3. Item type or domain record type.
4. Placement records that point to the canonical item without copying its body.
5. Typed, directional content links with inverse labels where required.
6. Publication workflow state separately from audience.
7. Audience values for Only Me, selected people, accepted Connections,
   Community members, and Public, including transition rules.
8. Block, report, mute, relationship-removal, and revoked-access behavior.
9. A single authorization service used by real profile requests, projections,
   AI retrieval, media delivery, interactions, and `View As`.
10. Unpublish, archive, restore, delete, and audience-change propagation across
    placements, content links, Feed, search, caches, indexes, and media.

Existing SQL and service artifacts are candidates for reuse, not proof that a
schema is deployed or v1.3-compatible. In particular, audit legacy `shared`,
`recruiter`, and `follows` terminology before reuse. Do not build a parallel
profile, post, connection, or audience model to avoid that reconciliation.

## Resolved contradictions and safe interpretations

| Bible or repository ambiguity | Binding interpretation |
|---|---|
| Earlier “Encourage/Celebrate” language | Use the locked Respond model: Celebrate, Support, I relate, Ask, Offer help. Primary actions are Respond, Comment, Save. |
| “AI-approved Sources” | Sources and publication are member-approved. AI may suggest or organize only. |
| Journal is canonical | Journal is the canonical profile/timeline projection over member-owned Slate records; it does not require one universal Journal table. |
| Owner sees the public profile | `/app` remains private. The owner at `/<slug>` receives the audience-filtered profile plus restrained owner controls. |
| A “standalone thought” may enter Feed | It may lack a Project or Goal link, but it is still a canonical Slate/Journal record with Feed placement. |
| “Connections” used for records and people | Reserve Connections for mutual people relationships. Use Content Link for record-to-record relationships. |
| Publication and audience language overlap | Model workflow state and audience separately; publishing must not imply Public. |
| Older and Appendix J navigation differ | Appendix J controls public profile navigation. Signed-in domains remain Home, Journal, Slate, Work, Studio, Community; Settings/Profile is utility navigation. |
| `follows` appears in a conceptual schema | Never use it for person following. Any object subscription requires explicit naming, ownership, and scope. |
| Generic marketplace revenue appears near a permanent job-marketplace ban | No job marketplace is permitted. Any other marketplace concept needs a separate, explicit product decision. |
| Public-profile job-description upload is suggested once | Do not accept logged-out recruiter uploads. Current safe scope is an authenticated owner's private qualification workflow until consent, retention, isolation, deletion, rate limits, and authorization are explicitly decided. |
| `View As` lists three modes but audiences are more granular | Persistent modes are Owner, Connection, and Public. Publication preview must still explain selected-people and Community visibility exactly. |
| Bible examples use `codex/...` branches | Use `work/YYYY-MM-DD-task-name`; `docs/AI_WORKFLOW.md` controls delivery. |
| PS-PLAN-002 is called “first” | It is a completed v1.2 audit. Do not rerun or rewrite it; record v1.3 findings in PS-RULES-002 and the next package plan. |

## Current repository reality at adoption

The PS-RULES-002 review was performed from `origin/main` commit
`05cec551567ce1811638e39a6b1b5ba1355ce3e9`. It found useful Flask/Jinja,
identity, data, test, and SQL foundations, but not a verified v1.3 profile
system. Repository artifacts are not evidence that Azure migrations, storage,
or production policies are deployed.

Known gaps that future packages must not present as complete:

- No verified protected `/app` owner workspace and no Journal-default profile.
- No production-backed Photos, audience-resolved `View As`, or mutual
  Connections experience.
- Existing public profile IA remains oriented around My Story, Work, Slate
  Board, and Resume.
- Public placeholder routes and sitemap entries suggest career search,
  follower-style networking, candidate comparison, and recruiter shortlisting.
- The homepage and legacy `/experience` contain demonstrations and fixed
  metrics that need unambiguous preview labeling and route cleanup.
- The Why PeerSlate page remains too Pete- and recruiter-centered for v1.3.
- CSS and templates carry multiple visual generations, including dark
  portfolio, Foundation C/modern-blue, an older Playfair/pink token file, and
  appended Iris Foundry styles.

Those findings belong in separate, reviewable implementation packages. A
marketing cleanup is valuable but must not be represented as the secure owner
milestone.

## Package order and gates

### 0. PS-RULES-002 — v1.3 governance adoption

Replace tracked Bible binaries with v1.3, update active agent entry points,
extend the Site Rules, document reconciliation decisions, and update guardrail
tests. This package changes no runtime route, schema, identity, storage, or
Azure behavior.

### 1. PS-PROFILE-001 — plan and dependency gate first

The first PS-PROFILE-001 deliverable is an evidence-backed plan containing:

- current and target route/access diagrams;
- identity and authorization matrix;
- canonical item, placement, link, publication, and audience contracts;
- current schema/deployment evidence;
- failure, block, removal, delete, and propagation behavior;
- mobile, keyboard, screen-reader, and 200% zoom behavior;
- migration, monitoring, rollout, rollback, and cross-user test plan.

If trusted identity, owner isolation, canonical storage, protected media, or
private Capture/Journal prerequisites are absent, stop visual implementation
and schedule the missing foundation package. Likely foundation packages are
PS-AUTH-001, PS-OWNER-001, PS-DATA-001, PS-MEDIA-001, PS-CAPTURE-001, and the
private Journal foundation. Reuse existing work where verified; do not assume
package names prove delivery.

### 2. Wave J implementation

After the profile dependency gate, deliver separately:

1. PS-PROFILE-001 — Journal profile shell backed by real audience resolution.
2. PS-PHOTOS-001 — private library, albums, protected renditions, metadata and
   retention controls, Journal shelf.
3. PS-CONNECT-001 — mutual requests, acceptance, removal, mute, block, report,
   list/count visibility, and immediate access revocation.
4. PS-LINKS-001 — typed links, inverse labels, placement picker, relationship
   UI, and propagation behavior.

If the approved architecture requires the PS-LINKS-001 data contract earlier,
record that dependency decision explicitly; do not quietly create a temporary
second relationship model.

### 3. Separate truthful-marketing cleanup

Audit `/`, `/peerslate`, `/experience`, `/career-search`, `/my-network`,
`/explore-profiles`, `/for-recruiters`, header/footer navigation, sitemap, and
structured data. Remove or redirect unfinished top-level concepts; label every
fixture and demonstration; center the owner loop; keep Pete as a clearly
identified secondary example. This package does not satisfy auth, Journal,
Photos, Connections, or private-data milestones.

## Package delivery requirements

Every package uses one `work/YYYY-MM-DD-*` branch and one reviewable outcome.
Before runtime coding, its initiative folder or approved plan must contain:

- requirements, user stories, acceptance criteria, scope, and explicit non-goals;
- current-state and dependency evidence;
- route, service, data, security, privacy, and AI boundaries;
- failure states and honest disabled/preview behavior;
- accessibility and responsive behavior;
- migrations and seed/fixture treatment, if applicable;
- unit, integration, cross-user isolation, and browser test plans;
- observability, rollout, rollback, and verification evidence;
- all answers in `docs/INITIATIVE_CHECKLIST.md`;
- branch, exact commit SHA, test commands/results, production status, known
  issues, and next action in the final handoff.

No package may claim production privacy, protected media, deletion/export,
grounded AI, voice capture, resume export, metadata stripping, verification,
or WCAG 2.2 AA conformance until implementation and deployment evidence prove
that exact claim.

## Visual direction

Iris Foundry is the active foundation:

- Newsreader for editorial headings; Inter for product and interface text.
- Warm Ivory `#F7F4EE`, White `#FFFFFF`, Ink `#191821`, Primary Iris
  `#5A2D82`, Bronze `#B87422`, and Success Teal `#16705F`.
- Neutral surfaces with one expressive focal point and restrained room accents.
- Avoid global purple wash, dark-default styling, colored global shadows,
  neon, excessive gradients, visible grain, decorative glass, and fake 3D.

Canonicalize tokens incrementally—tokens, base/shell, then page components—with
regression tests. Do not add Blueprint Light or a theme toggle. The optimized
transparent header logo is appropriate for navigation; do not place a large,
opaque source lockup directly into the header.

## Stop conditions

Stop the affected package and report the evidence when:

- a route, migration, storage policy, or deployed service cannot be verified;
- an authorization choice would be made in browser-only code;
- a public response would fetch private records and hide them later;
- the plan would duplicate canonical content, profiles, posts, audiences,
  relationships, or media metadata;
- a change would expose a selected person, private source, blocked relationship,
  photo location, job description, or AI retrieval basis;
- product copy would claim an unverified capability;
- an unresolved owner decision would materially change privacy, retention,
  publication, identity, schema, or public promises.

