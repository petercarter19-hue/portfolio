# PeerSlate Shared Site Rules

**Lean revision:** 2026-07-31
**Authority:** subordinate to the Constitution, Roadmap, and control plane named
in `docs/governance/CURRENT_BASELINE.yaml`.

These are shared runtime and interface invariants. Feature details belong in
the affected package; delivery mechanics belong in `docs/AI_WORKFLOW.md`.

## 1. Multi-user trust

- PeerSlate is reusable and multi-user. Pete, Danielle, and other named people
  are fixture/content records, never shared product logic.
- New content, sources, captures, drafts, AI work, goals, sessions, and imports
  are private by default.
- Never trust a browser-supplied user ID, slug, path, or session identifier as
  proof of ownership. Resolve server-derived identity and authorize before
  protected retrieval or mutation.
- Canonical content, source evidence, AI proposals, and audience projections
  are separate data classes. Store one authoritative fact body and reuse exact
  references instead of copying truth between rooms.
- AI output remains a proposal until the member accepts it. Deterministic code
  controls authentication, authorization, ownership, audience, publication,
  deletion, billing, audit, and retention.
- Show truthful live, demo, fixture, local-only, disabled, queued, unavailable,
  failure, and permission-denied states. Never imply a capability is deployed
  or connected without evidence.

## 2. Journal, Capture, and projections

- Capture is an authorized in-context action, not a required destination.
- Save Moment creates one private canonical Moment. The owner's Journal uses
  deterministic derived membership; there is no second Journal-entry fact body
  and no Add to Journal step.
- Use This Moment, placement, sharing, audience change, and publication are
  separate previewed member actions over exact references. They never happen
  automatically or as part of Save Moment.
- My Story is a deliberate member-curated projection, not the complete private
  Journal. Work, resume, Projects, Story, Slate, Feed, Studio, and public views
  do not become competing truth stores.
- Private prompts are optional, dismissible, and calm. Momentum is not
  necessarily daily and never uses guilt, public rank, reset/loss framing, or
  engagement theater.
- The final signed-in route map remains an explicit later decision. Capture is
  not another user-facing destination or an Add to Journal gate.

## 3. Focused product boundaries

- Community supports purposeful progress, questions, learning, support, and
  connection. No job posts, job-listing routes, hiring marketplace, engagement
  rankings, popularity pressure, or decorative polls.
- A privately uploaded external job description may support Qualification
  Alignment, but it is never published, indexed, recommended, or converted
  into a listing. Required and preferred qualifications remain distinct;
  unknown history is a question, not a failed match.
- Interview Me means the member answers and PeerSlate coaches. Interview AI
  clearly separates generic best-practice examples from permitted member-
  grounded answers, displays relevant history, and never attributes generic
  material to the member.
- Ask Slate AI is the signed-in umbrella; Ask My Slate is contextual; public
  assistants are Ask [Name] AI. Ashley AI is retired terminology. AI remains
  useful in context and does not force every task through generic chat.
- Projects are private-first connected containers, not task-management,
  issue-tracking, procurement, timesheet, or delivery-management software.
- The public Interview Studio retains its current public/browser-local truth
  boundary until a separately authorized transition package changes it.

## 4. Navigation, brand, and accessibility

- Pages are focused views of one connected Slate. Do not add a permanent top-
  level destination for a filter, prototype, empty page, Capture action, or
  unfinished concept without approved route authority.
- About PeerSlate belongs in logged-out marketing/footer context, not signed-in
  product or public-member navigation.
- Deep Navy Gold is the shared default visual system. Use the established
  tokens/components and existing dark-theme contract; do not invent competing
  room themes or recolor member imagery.
- Target WCAG 2.2 AA. Essential paths support semantic structure, keyboard,
  visible focus, assistive technology, contrast, 200% zoom/reflow, reduced
  motion, mobile touch, long content, missing media, and recovery.
- Preserve approved first-class alternatives such as Speak and Type.

## 5. Proportional delivery

- Follow `START_HERE.md` and select Routine, Bounded, or Protected.
- One focused branch and one active writer own a mutable surface. A handoff is
  required only when another writer actually continues it.
- Every slice gets a clear outcome, focused verification, and complete-diff
  self-review. Add architecture, privacy, rollback, independent review,
  Candidate, visual, or broader evidence only when its risk trigger applies.
- Azure DevOps `origin/main` is authoritative and Azure Pipelines is the
  production path. A merge is not deployment; record pipeline and affected-
  route live evidence separately.
- `GET /healthz` remains member-data-free and may expose only service/status
  plus an opaque build identity—never secrets, configuration, dependencies,
  storage, providers, quota, or member diagnostics.
- Use `OWNER_VISUAL_INTEGRITY_STANDARD.md` for a new/materially revised page or
  direction. Routine UI changes preserve locked authority and receive
  proportionate browser checks. Demonstrations must identify what is
  illustrative, live, stored, transmitted, local-only, private, public, or
  future.
- Story and Projects standards apply only when their respective behavior is in
  scope. OPS gates apply only to their Protected Candidate, broad Launch,
  operated-service, Retire, or emergency trigger. They do not block unrelated
  Routine or Bounded work.
