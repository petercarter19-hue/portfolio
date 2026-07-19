# PS-INTERVIEW-PUBLIC-GATE-001 — Implementation Brief (Sonnet writer session)

_Prepared 2026-07-19 by the Claude/Fable architecture session; blocker list
updated after the round-2 closure. Use only after the addendum §E blockers
are recorded as resolved: Pete's board-1 ratification and Pete +
designated-manager visual approval of the package. Product implementation
before that recording is a governance violation._

## Role and boundaries

You are the sole implementation writer for the real public Interview Studio
5A-light/5C-dark package. You self-manage the branch end to end under
`docs/AI_WORKFLOW.md` (implementation → complete-diff self-review → tests →
evidence → report → after acceptance: PR, pipeline, live verification,
closeout).

- Branch: fresh `work/YYYY-MM-DD-interview-public-gate-001` from then-current
  `origin/main`. Record the full base SHA. Do not reuse or continue any
  existing branch or worktree, including this review branch and the preserved
  homepage-demo worktree.
- Writable files — exactly four, plus package records:
  `templates/interview_studio.html`, `static/css/interview-studio.css`,
  `static/js/interview-studio.js`, `tests/test_interview_studio.py`,
  screenshots under `artifacts/ps-interview-public-gate-001/`, and this
  initiative directory (architecture re-validation note + completion report).
- Read-only / forbidden: `app.py`, any route/API/entitlement code,
  `templates/base.html`, global theme/nav/footer files, other products'
  templates/styles/scripts, deployment configuration, database anything.
  If a need appears outside the four files, **stop and ask the manager for a
  reservation — do not edit.**
- No new dependencies, no build tooling, no framework. Jinja + page-scoped
  CSS + vanilla JS, as today.

## Read in this order (all on `origin/main` after the gate merge)

1. `START_HERE.md`, `docs/AI_WORKFLOW.md`, current governance pointers
2. This initiative `README.md`, files `01`–`10`
3. `11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md` — your build contract
4. `12_GATE_24_CORRECTION_AND_FEASIBILITY_ADDENDUM.md` — gate state and
   deviation register D1–D21
5. The authority assets under
   `artifacts/ps-interview-public-gate-001/gate-24-final-visual-review/`
   (verify the §B hashes before relying on them)

## Non-negotiable product invariants (from the architecture)

1. One product, one DOM, one state machine; theme changes presentation only.
2. Zero theme code in `interview-studio.js`; all theming is CSS token values
   under `body[data-theme="dark"] .is`; theme switch preserves every state in
   the architecture §6 matrix.
3. Every existing `data-is-*` hook, listener, guard, confirm, abort
   controller, storage key, endpoint call, entitlement check, redirect, and
   announcement is preserved. You are re-composing and re-skinning, not
   rebuilding behavior.
4. All required truth strings render server-side (orientation, truth strip,
   demo-profile card with "You are not signed in as Pete.", transmission and
   browser-storage lines, practice-signal score label, video local-only copy,
   history browser-only copy).
5. The deviation register D1–D21 is binding: implement the deviations exactly
   as recorded; if implementation reality forces a new deviation, record it
   with a reason in the register and report it — never silently.
6. Light must be recognizably Image 5 Concept A; dark recognizably Concept C;
   both per the exact authority hashes. Do not import the ZIP renderer's
   markup, query-string theming, or `innerHTML` repaint pattern.
7. Mode names: Interview Me, Interview AI, **Video Practice**, History.
8. WCAG 2.2 AA: use the measured token sheet exactly (text gold `#8A5A00` in
   light; `#d2a24b` decorative-only in light; dark done-disc recolor); ≥44px
   targets; visible focus everywhere; reduced-motion and forced-colors blocks
   extended to new components.

## Build order (small, reviewable commits)

1. Architecture re-validation: confirm `origin/main` still matches the
   architecture's assumptions (four files unchanged since the gate merge;
   entitlement attributes; test baseline green). Add a dated "Re-validation"
   section at the top of `11_…ARCHITECTURE.md` (above §1) on your branch. If
   anything drifted, stop and report before coding.
2. Tests first where stable (server-rendered markup: orientation, truth
   strip, labels, stage-rail markup, CSS guardrails, theme guardrails), then:
3. CSS token layer + shell/bar (§9.2 order), template §9.1 steps 1–2, JS §9.3
   items 1–2 — orientation + practice through PUBLIC-04 + V01.
4. AI panel (PUBLIC-05), video panel (PUBLIC-06/V02), history (PUBLIC-07).
5. Dark token block + dark decorative rules; both-theme QA pass.
6. Responsive + zoom + landscape + long-content pass; a11y media blocks.
7. Full §12 evidence capture; complete-diff self-review; fix everything you
   find; rerun all tests.

Test commands (minimum): `python -m unittest tests.test_interview_studio -v`,
`tests.test_navigation`, `tests.test_site_rules`,
`tests.test_governance_pointers`, then the complete configured suite in the
repository venv (`python -m unittest discover -s tests -v`) with the
documented non-secret local test placeholder.

## Completion report

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`. It must include:
exact base SHA; branch + clean pushed full tip SHA; changed files; every test
command with results; the full §12 evidence set with named files; the 5A/5C
parity matrix against the authority hashes; the theme no-state-loss matrix
results (10 rows × both directions); the deviation register status; honest
limitations; and `Pass` / `Conditional` / `Fail`. State explicitly:
implemented but **not merged, not deployed, not live** until its own Azure
PR, pipeline, and production verification complete after Pete/manager
acceptance. Do not self-approve the visual gate. Do not relinquish the branch
unless handing off; you own post-acceptance release and closeout unless the
manager reassigns them.

Stop-and-ask triggers: any need outside the four files; any behavior that
would require an API/entitlement change; any mockup element you cannot build
truthfully; any test that can only pass by weakening a truth or accessibility
assertion; homepage edits (Gate 4 belongs to a later package).

## Paste-ready kickoff

> Open the authoritative Azure repository and follow `START_HERE.md` and
> `docs/AI_WORKFLOW.md`. Fetch `origin`, verify current `origin/main`, and
> read the `PS-INTERVIEW-PUBLIC-GATE-001` package through
> `14_OPUS_REVIEW_CHARTER.md`, treating
> `11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md` as your build contract and
> `12_…ADDENDUM.md` §E as your entry gate — confirm Pete's board-1
> ratification and package visual approval are recorded before any product
> edit. You are the sole self-managed implementation writer. Create
> `work/<today>-interview-public-gate-001` from current `origin/main`, record
> the base SHA, and implement the 5A-light/5C-dark real public Studio exactly
> per the architecture: four reserved files only, all existing behavior and
> hooks preserved, orientation view added template-only, semantic token
> re-skin with the measured contrast sheet, zero theme code in Studio JS,
> truth strings server-rendered, deviation register D1–D21 honored, and the
> full §12 evidence matrix captured. Run focused, guardrail, and complete
> configured suites. Return the standard completion report with exact SHAs
> and evidence, state that nothing is merged/deployed/live, and request
> Pete + designated-manager acceptance. Then stop.
