# PeerSlate Roadmap Briefing — 2026-07-22

> **What this document is.** An owner-facing, plain-English distillation of the
> current authority — Bible v2.8, Roadmap v2.7, `CURRENT_BASELINE.yaml`,
> `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`, and the 2026-07-21 handoff
> snapshot — prepared by a Claude Code remote session for Pete's review. It is
> a dispatch and orientation aid, **not** an authority record. Where this
> briefing and the controlled documents disagree, the controlled documents win.
> Nothing in this briefing authorizes, assigns, schedules, enables, or claims
> any implementation.

---

## 1. Where PeerSlate stands today

**Live and verified in production (https://peerslate.com):**

- The public homepage with the Interview walkthrough, converged to the released
  real Studio through the closed homepage-Interview-parity package.
- The public résumé (`/petec/resume`) and the released 5A-light/5C-dark
  Interview Studio (`/interview-studio`).
- Real identity (email/password, OTP, Google, Microsoft personal) with
  two-owner isolation, protected Settings, and the private text Capture →
  Moment → Placement backend foundation.
- Voice capture: functionally deployed, visually accepted, and closed.
- Sample-community honesty labels and the signed-in Sign out control.
- The Journal J1 **backend** with accent-insensitive search — merged with the
  flag off; its SQL migration is proposed-only and has **not** been run.

**Released but intentionally dark (flag off, default off):**

- Capture Photo (backend and experience) — enablement gates still open.
- Owner Home backend (`PEERSLATE_OWNER_HOME_ENABLED=false`; API neutral 404).
- Journal J1 backend (`PEERSLATE_JOURNAL_ENABLED=false`; migration gate not run).

**Built but unmerged (held on Azure work branches, per the 2026-07-21 handoff):**

- **Journal J1 frontend** — bound-book rebuild landed; a 60-item owner
  punch-list fix pass was stopped mid-flight; unaudited. Highest priority.
- **Owner Home frontend** — build complete through fix round 1; two NO-GO
  audits; fix round 2 stopped mid-flight; unaudited.
- **Community tabs** — reviewer-certified GO; awaiting Pete's visual verdict
  and a successor second review, then Azure PR → pipeline → verification.

**Planning-only (documented, not implementation):**

- Return-value services, owner-only Ask Slate AI, Messaging, Story Composer,
  Projects, Ask Pete AI, Shell, Onboarding, Résumé Studio.

**Authority state:** Bible v2.8 + Roadmap v2.7 are current, activated through
`PS-GOV-JOURNAL-SYSTEM-001` with recorded SHA-256 integrity hashes. The GitHub
mirror was synchronized by the owner after the 2026-07-21 handoff cutover and
remains one-way backup only; GitHub Actions deployment stays disabled.

---

## 2. The product model everything now follows (the "new approach")

Bible v2.8 makes the **one-Journal system** constitutional. In plain English:

1. **Capture is an action, not a place.** Any eligible signed-in room can open
   the same pop-out composer over the current page and return you to it.
2. **Save Moment is the only commit.** One tap saves one private canonical
   Moment in the member's own words. Nothing else happens automatically.
3. **The Journal is derived.** Every saved Moment is automatically part of the
   owner's one private Journal — no "Add to Journal" step, no copies.
4. **Catch the moment.** Right after saving, the composer offers first-class
   `Use This Moment` options — Feed, My Story, Work, Résumé — plus an audience
   choice. Each is explicit, previewed, and a *reference* to the exact Moment
   version, never a copy. New Moments default to Only Me.
5. **Type and Speak are equal**, and the essential loop must survive when AI or
   speech providers are down.
6. **Destinations light up in stages.** Private capture + Journal ship first
   (J1); the destination chooser and audience projections follow (J2+).

Every downstream product — Story, Work, Résumé, Feed, Projects, Slate Mirror,
Ask Slate AI — reads from this same canonical layer by governed reference.

---

## 3. The road ahead

### Wave 1 — Finish what is in flight (now)

| # | Work | Where it stands | Exit condition |
|---|---|---|---|
| 1 | **Community tabs acceptance** | Reviewer-certified GO; review zip delivered | Pete's visual verdict + successor second review → Azure PR → squash merge → pipeline → production verification |
| 2 | **Journal J1 frontend** | 60-item punch list partially applied, unaudited | Finish all 60 items, measured per-item audit, desktop+mobile+dark screenshots, Pete visual review |
| 3 | **Owner Home frontend** | Fix round 2 stopped mid-flight, unaudited | Finish fix round 2 against the ~20-screen authority set, measured re-audit, screenshots, Pete visual review |
| 4 | **Login "not set up" nag** | Awaiting Pete's screenshot + sign-in email; likely allowlist mismatch (`peerslate19@gmail.com`) | Small fix in `auth_routes.py`, coordinated with the Home lane's reservation |

Standing rules for this wave: one writer per branch; the accepted mockups'
sampled pixels are the palette and typography authority; fixtures mirror the
mockups exactly; flags stay false; Pete is the final visual gate.

### Wave 2 — Turn the Journal on safely (next)

1. **Migration gate** — run the PS-JOURNAL-001 migration runbook
   (doc 12) through the secure connection path with rollback proof.
2. **Two-member isolation proof** and the accessibility, retry/failure,
   deletion, and performance gates named by the package.
3. **Enablement** — `PEERSLATE_JOURNAL_ENABLED` flips only after the gates,
   Pete's acceptance, and an explicit go.
4. **Homepage parity** — when the Journal becomes a real member experience,
   the logged-out homepage must tell that story truthfully in the same wave or
   an explicitly sequenced downstream package.

### Wave 3 — Activate the connected system (after the private core is real)

- **J2+ `Use This Moment`** — the destination chooser and audience projections
  (Feed, My Story, Work, Résumé), each explicit, previewed, reference-only.
- **Photo dark-launch, then enablement** — server-only dark launch first
  (fail-closed synthetic gating, `CAPTURE_PHOTO_ENABLED` stays false), then the
  signed-in lifecycle, two-owner, and homepage-parity gates.
- **Bounded Return services and owner-only Ask Slate AI** — may start after the
  private Journal foundation without waiting for public Journal; private,
  source-linked, correctable, member-controlled.
- **Interview coaching reliability** — characterize and bound the intermittent
  provider 502s; honest degraded states, no fabricated coaching.
- **Owner Home enablement** — after its frontend passes visual acceptance and
  the backend contract's runtime states are truthfully supported.

### Wave 4 — The platform grows outward (Roadmap v2.7 phases 8–12)

| Phase | What it delivers | Gate |
|---|---|---|
| 8 — Connection, publication, finite Feed | Real two-member connections and selective sharing with exact audience grants | Phases 4–7 foundations; no auto-connect; server-enforced audiences |
| 9 — Slate Mirror, What PeerSlate Noticed, Replay | Governed longitudinal member intelligence — private, source-linked, correctable | Mature authorization, provenance, and correction foundations |
| 10 — Moment Lab, Story, Work, Projects, connected views | The same Slate reused across preparation and expression; member-directed Story Composer; private-first Projects | Phases 7–9; Story/Projects packages' own entry gates |
| 11 — Next Chapter and Qualification Alignment | Future-direction guidance without ever becoming a job marketplace | Phases 9–10 |
| 12 — Scale, integrations, business expansion | Operational scale and monetization after proven member value | All prior gates plus a separate business decision |

Deferred by explicit owner decision (not forgotten, parked): AI bill
protection, the navigation route map, rail R2 résumé restyle, PS-SHELL-001,
PS-ONBOARD-001, PS-RESUME-STUDIO-001, and the multi-tenant question.
FitSlate remains tabled.

---

## 4. Decisions that are Pete's alone right now

1. **Community tabs verdict** from the delivered review zip.
2. **Login-nag evidence** — the screenshot plus which email was used.
3. **Branch disposition** — row-by-row approval of
   `BRANCH_DISPOSITION_RECORD.md` before any branch deletion.
4. **The two `.pages` files** in the repository root — commit, convert, or
   keep local; their disposition is still unrecorded.
5. **Staffing** — which lane the next working session takes first
   (the handoff names Journal J1 frontend as highest priority, with the
   Community-tabs second review as the successor's first assignment).

---

## 5. How releases happen (unchanged, and why it matters)

Azure DevOps is the only source of truth; every change rides a short-lived
task branch through an Azure squash-merge PR, the Azure pipeline, and live
production verification before anything is called done. GitHub stays a one-way
backup mirror with Actions disabled. Flags stay off until their gates pass.
Nothing user-facing merges without named visual authority, measured parity
evidence, and Pete's acceptance. These rules are what let three parallel lanes
move quickly without stepping on each other — the roadmap above only works
because the delivery discipline underneath it is boring and strict.
