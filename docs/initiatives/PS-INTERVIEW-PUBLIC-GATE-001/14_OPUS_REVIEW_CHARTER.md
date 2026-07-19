# PS-INTERVIEW-PUBLIC-GATE-001 — Independent Review Charter (Opus reviewer session)

_Prepared 2026-07-19 by the Claude/Fable architecture session. Run this review
after the Sonnet writer returns its completion report and before Pete/manager
acceptance. The reviewer is read-only on the writer's branch._

## Role and boundaries

You are the independent technical and parity reviewer for the Interview
Studio 5A/5C implementation. You do not edit the writer's branch, product
code, or governance records. Your output is a durable review report (this
initiative directory on your own short-lived review branch, or the report
channel the manager designates) with findings and a verdict. The
self-managed-lanes model means you do not repeat the writer's whole audit by
default — you verify the claims, probe the highest-risk areas, and
adversarially spot-check.

Inputs you must obtain: the writer's branch name + exact full tip SHA, its
completion report, and the evidence set. Verify the SHA against `origin`
before reviewing; if they differ, stop and report.

## Review matrix

1. **Diff hygiene.** Complete diff vs the recorded base: only the four
   reserved files + initiative records/artifacts; no `app.py`, base template,
   global theme/nav, deployment, or unrelated changes; no new dependencies;
   asset version strings bumped; `git diff --check` clean.
2. **Behavior preservation.** Every pre-existing `data-is-*` hook, endpoint
   call (`/api/interview/review|improve|model-answer` only), storage key
   (`peerslate:interview-studio:<profile>:v1:*`), entitlement gate, redirect,
   dialog, confirm, abort/cancel path, and announcement survives. Probe: the
   JS diff must show no removed listener or fetch-contract change.
3. **Truth.** Server-rendered HTML contains the required strings (demo
   profile + "You are not signed in as Pete.", truth strip's four items,
   submit-time transmission line, browser-only history language, local-media
   language, "Practice signal — not an employer prediction"). No invented
   analytics: compare shows only real payload content (deviation D8); history
   goals show only computable stats (D10); no "Design authority" mockup
   footer; no sign-in/account/sync implication anywhere, in either theme.
4. **Theme and no-state-loss.** CSS: single dark token block under
   `body[data-theme="dark"] .is`; theme selectors change only
   color/background/border/shadow/filter/outline values. JS: zero occurrences
   of `ps-theme`, `data-theme`, `theme-toggle`, `prefers-color-scheme`.
   Reproduce at least rows 2, 3, 7, 8, 9, 10 of the architecture §6 matrix
   yourself in a browser (draft text, in-flight request, active recording,
   playback, open dialog + filters, error states) in both switch directions.
5. **Visual parity (5A/5C).** Compare the writer's 18 primary screenshots and
   your own live renders against the exact authority hashes (arch §1): same
   composition, hierarchy, dominant object, editorial/cinematic finish; light
   is recognizably Concept A, dark recognizably Concept C, not a palette
   swap; the D1–D21 register covers every visible difference, and no
   unrecorded deviation exists. Confirm the two authority-defect corrections
   (five mobile stage circles; mobile ring caption).
6. **Accessibility.** Keyboard-only walk of all five views + three dialogs
   (focus visible, order logical, restore on close); stage rail and score
   ring semantics; radiogroup semantics on AI grounding; live-region
   announcements single-sourced; reduced-motion honored; 390×844, 844×390,
   200% reflow; ≥44px targets; spot-check the measured contrast pairs (light
   text-gold #8A5A00, dark done-disc, caution text on soft amber).
7. **Tests.** Focused + guardrail + full configured suites pass in a
   configured environment; new guards exist (orientation server-render, truth
   strip, theme guardrails, CSS guardrails incl. the `nth-child(n+5)`
   prohibition and light `#b87900`-as-text prohibition); no assertion was
   weakened to pass — inspect every test the writer edited and confirm each
   maps to an enumerated copy/structure change (arch §9.4).
8. **Report integrity.** The completion report's claims match the evidence;
   layer separation is honest (implemented ≠ merged ≠ deployed ≠ live);
   limitations disclosed; self-certification level justified.

## Verdict and handoff

Return: findings (numbered, each with file/line or screenshot reference,
severity, and whether it blocks), the §6-matrix rows you reproduced, and one
verdict — `Pass` (recommend Pete/manager acceptance), `Conditional`
(acceptance only after enumerated fixes), or `Fail` (return to writer).
Findings go back to the same writer for fixes on the same branch; you do not
fix them yourself. Your review does not substitute for Pete's and the
designated manager's visual acceptance — it informs it.

## Paste-ready kickoff

> Open the authoritative Azure repository and follow `START_HERE.md`. Fetch
> `origin` and read the `PS-INTERVIEW-PUBLIC-GATE-001` package: the
> architecture (`11_…`), addendum (`12_…`), implementation brief (`13_…`),
> and this charter (`14_…`). You are the independent read-only reviewer of
> the Interview Studio implementation branch <branch> at exact tip <full
> SHA> — verify that SHA against `origin` first. Execute the eight-point
> review matrix in `14_OPUS_REVIEW_CHARTER.md`, including your own browser
> reproduction of the theme no-state-loss rows and a keyboard-only pass in
> both themes. Do not edit the writer's branch. Return numbered findings
> with severity and a `Pass`/`Conditional`/`Fail` verdict to the designated
> session manager and the writer.
