# PS-INTERVIEW-PUBLIC-GATE-001 — Gate 2.4 Correction and Feasibility Addendum

_Recorded 2026-07-19 by the Claude/Fable architecture-and-feasibility session.
This is the one bounded correction-and-feasibility addendum requested by
`08_GATE_24_FINAL_VISUAL_REVIEW.md` §I. Design and feasibility only; product
implementation has not started. No product code was edited._

## A. Status

- Package: `PS-INTERVIEW-PUBLIC-GATE-001` Gate 2.4 correction + feasibility
- Base: authoritative Azure `origin/main`
  `229bfba4cd31e0eb56b99a94e90f16aa3fabb396`
- Branch: `work/2026-07-19-interview-gate-24-final-review`, continued by
  Claude/Fable after the Codex handoff of exact tip
  `50e0e75906bea4e8578bcb3c13e8ecc64af55139` (tip re-verified against
  `origin` before writing)
- Files added by this addendum: `11_REAL_STUDIO_IMPLEMENTATION_ARCHITECTURE.md`,
  this file, `13_SONNET_IMPLEMENTATION_BRIEF.md`, `14_OPUS_REVIEW_CHARTER.md`,
  README pointer update — documentation only
- Visual authority: unchanged — Image 5 Concept A (light) / Concept C (dark);
  supplied boards and PUBLIC-03…V02 ZIP per the §B manifest
- Pete visual acceptance: recorded for the supplied appearance (unchanged)
- Feasibility result (implementation inside the four reserved files, no API or
  route change): **Pass** — see architecture §10
- Gate 2.4 readiness result (complete design package): **Conditional** — see §E
- Production state: unchanged; the existing public Studio remains live; these
  designs are not implemented, deployed, or live
- Self-certification for this addendum's own scope: **Pass** (documentation
  work; complete-diff review of this branch's additions; guardrail suites run
  — results in §F)

## B. Asset identity re-verification

Recomputed 2026-07-19 from this branch (SHA-256; byte counts):

| File | Bytes | SHA-256 | Matches Codex record |
|---|---:|---|---|
| `PeerSlate_Interview_Studio_PUBLIC-03-V02_Final_Visual_System.zip` | 13,786,088 | `C4A0156AE572956AE0F7D99F0CCCFC483CB4B5D988207844F66FDDE0118F5599` | Yes |
| `PUBLIC-01-02-supplied-board-1.png` | 1,711,584 | `31488D93AE50ADBC959EBA948BB4F5E8FD331DAF0DA80CF0E633BFDB94BDEBB5` | Yes |
| `PUBLIC-01-02-supplied-board-2.png` | 1,681,308 | `6E9146AE133AC67A24ABD5373F95BCFF25D41A3A030717AD60CB30E11A755209` | Yes |

Original Image 5 source identity is recorded in the architecture §1 (offline
file; not re-hashable from this repository — identity carried forward from the
repository authority records).

All 28 ZIP exports and both boards were reviewed at full scale in this
session, including the mobile exports whose defects are corrected below.

## C. Closure of the eleven Codex corrections

| # | Codex §E item | Closure |
|---|---|---|
| 1 | PUBLIC-01/02 exact authority unresolved | Board 1 (`31488D93…DEBB5`) recommended as controlling with composition rationale and a full panel map (arch §1.1). **Round 2: delivered artifacts replace the earlier evidence-equivalence** — eight separate PUBLIC-01/02 primary exports (light/dark × desktop/mobile) plus the editable source, hash-pinned in `artifacts/ps-interview-public-gate-001/gate-24-fable-evidence/EVIDENCE_INDEX.md`. **Open owner action: Pete's one-yes ratification.** |
| 2 | Shared shell inconsistent | Resolved: production keeps the global header/footer; Studio-local bar per the boards; ZIP chrome ruled a renderer simplification (arch §1.2, D1). No global-navigation redesign. |
| 3 | Mobile hides the fifth progress step | Corrected normatively: all five stage circles render at every viewport; the `nth-child(n+5)` rule is prohibited and a CSS guardrail test asserts its absence (arch §2.3, §9.4, D14). |
| 4 | Light small gold text misses AA | Corrected with measured tokens: text gold `#8A5A00` (4.92–5.87:1); `#B87900` retained for meaningful non-text indicators (3.43–3.60 ≥ 3:1); `#d2a24b` decorative-only in light (2.20–2.31). Full measured table in arch §3.1, including two additional fixes the review had not measured (light caution text on soft amber; dark step-done glyph). |
| 5 | No-JavaScript evidence absent | Closed as architecture + test contract: every view is server-rendered with real links and full truth labels; `<noscript>` note specified; template-only orientation derivation avoids `app.py`; server-render tests enumerated (arch §2.1, §8, §9.4). The static ZIP renderer is explicitly non-production. |
| 6 | Source is not a semantic/accessibility specification | Closed: component inventory with roles/names/states, focus design, live-region policy, dialog behavior, and visible-focus tokens (arch §4, §7). |
| 7 | Responsive evidence incomplete (landscape, 200%, long, label stress) | Closed normatively (arch §7) **and, in round 2, with delivered pre-implementation design evidence**: 844×390 landscape for the written/review/video/history/failure journeys, 200%-reflow equivalence, long-content, and focus-visible boards in both themes (`gate-24-fable-evidence/EVIDENCE_INDEX.md`). Implementation-time evidence (arch §12) still applies to the built product. |
| 8 | Reduced motion unspecified | Closed: existing kill-switch retained, spinner meaning carried by text, static gold focal treatment, no meaning via motion (arch §7). |
| 9 | Unavailable-state evidence incomplete | Closed: full matrix — JS unavailable, storage unavailable (new visible caution state), media unavailable/denied, request error, retry, repeated failure, History empty (arch §5.7–5.9, §8). |
| 10 | Component/token/feasibility artifacts absent | Closed: component inventory (arch §4), token sheet with measured contrast (arch §3.1), 5A/5C parity duty + deviation register (arch §11, §12), current-file mapping (arch §9), risk matrix (arch §10). |
| 11 | Theme persistence/no-state-loss unproved | Closed by construction + proof plan: zero theme code in Studio JS, CSS-value-only theming, guardrail string tests, 10-row manual matrix (arch §6). The renderer's query-string/innerHTML approach is expressly rejected. |

## D. Feasibility matrix (summary)

Full detail in arch §9–§10. Mapping to the four reserved files:

| Area | File(s) | Change class | Risk after mitigation |
|---|---|---|---|
| Orientation view (PUBLIC-01) | template (+JS view flag) | additive; template-only server derivation | Low |
| Studio bar + truth strip + demo cards | template + CSS | recomposition; hooks preserved | Low |
| Token re-skin light/dark (5A/5C) | CSS | rewrite with single dark token block; legacy dark block removed | Low–Medium (visual QA burden, no logic) |
| Stage rail | template + CSS + JS | additive renderer on existing transitions | Low |
| Review/improve recomposition | template + JS | markup moves; logic unchanged | Medium (test copy updates) |
| AI/compare presentation | template + CSS | semantics unchanged; D8 truth deviation | Low |
| Video sub-states + V02 | template + CSS + JS labels | existing machine; visible transcript control | Low |
| History recomposition + storage note | template + CSS + JS render targets | logic unchanged + storage probe | Low |
| Tests | tests file | enumerated updates + new guards | Medium (breadth) |

No change touches `app.py`, endpoints, entitlements, storage schema, global
theme/nav files, or deployment. No unreserved file is required.

## E. Readiness result

**Conditional.** The design direction, nine-screen dual-theme system,
truth/accessibility architecture, and implementation feasibility are complete
and coherent; implementation is not blocked by any technical unknown. After
the round-2 closure (§H), the earlier evidence-equivalence request is
withdrawn — the artifacts now exist. Exactly two recordings remain open:

1. **Owner ratification (one yes/no):** board 1 controls PUBLIC-01/02
   (arch §1.1). Until then the ZIP's controlling reference stays formally
   unbound.
2. **Pete + designated-manager visual approval of the complete package**
   (boards + ZIP + round-2 evidence exports + architecture deviation
   register D1–D21) — the standing Gate 1 approval that authorizes the fresh
   implementation branch.

When both are recorded, no further design work is required before
implementation. Single next action: Pete and the designated manager record
the ratification/approval, then start the implementation writer per
`13_SONNET_IMPLEMENTATION_BRIEF.md`.

## F. Verification of this addendum's own scope

- Branch tip before additions matched the handoff SHA exactly
  (`50e0e759…4af55139`); worktree was clean; only the five documentation
  files listed in §A are added/changed (complete-diff review at commit).
- Guardrail suites run on this branch (documentation-only change), repository
  venv: `python -m unittest tests.test_governance_pointers -v` — 16 passed;
  `python -m unittest tests.test_site_rules -v` — 9 passed. The site-rules
  suite requires the documented non-secret `ANTHROPIC_API_KEY` presence
  placeholder (`local-test-placeholder-not-a-real-key`); a first run without
  it failed at `app.py` import — environment-only, same as the Codex review's
  recorded case, superseded by the green configured run.
- No product file, test, route, API, theme, or deployment file was edited.
- Asset hashes re-verified (§B).

## G. Plain-English walkthrough for Pete

What this addendum does: it accepts your approved look exactly as supplied,
fixes the small defects the Codex review caught (the missing fifth progress
dot on phones, the score-ring caption overlap, and gold text that was too
faint to pass accessibility in light mode — replaced with the deeper approved
gold), and writes the complete blueprint for building it into the real
`/interview-studio` page.

What does not change: everything the Studio truly does today keeps working —
written practice with coaching, the AI examples with their source labels,
local camera rehearsal, browser-only history, all the honesty labels, and
the site's existing light/dark switch. Dark mode becomes the cinematic navy
and gold Studio you approved, and switching themes can never erase an answer,
a recording, or your place on the page — the design makes that impossible by
construction, and tests enforce it.

What the mockups left out that we are keeping (quietly tucked away, not
deleted): the experience/question/session pickers, the question queue,
settings, history filters and detail, and the numeric practice goal. Two
mockup details will not ship because they would be untrue: the compare bars
that pretend to measure your answer against Pete's, and the history insight
line ("4 of 6 answers included a measurable result") that nothing actually
computes — both are replaced with real data the page genuinely has.

The one thing you need to decide: **board 1 or board 2 for the opening and
writing screens.** I recommend board 1 — it is the one with a single big
"Start Interview Me" button and the three quieter cards (including History),
which is exactly what the approved brief asks for. Say "board 1 confirmed"
(or pick board 2) and give the overall package your visual yes; after that,
implementation can start the same day with no further design work.

## H. Round-2 closure (Codex Conditional verdict, 2026-07-19)

An independent Codex review of the tip-`5fe681a71d6fdf8b00ed7c1bfa30e101aea8c70f`
package returned `Conditional`: board 1 endorsed as the recommended
direction and the architecture judged technically sound, with three
conditions. Closure, delivered on this branch with all accepted
PUBLIC-03–V02 visuals and deviations D1–D21 preserved:

1. **Separate PUBLIC-01/02 exports + editable source.** Added
   `artifacts/ps-interview-public-gate-001/gate-24-fable-evidence/`: an
   editable static source derived from the accepted ZIP renderer (the seven
   accepted state renderers preserved; PUBLIC-01/02 added per board 1 with
   the registered copy corrections D7/D19/D20; only registered corrections
   D13/D14/D15/D16 applied via a banner-marked cascade appendix) and eight
   primary exports (PUBLIC-01/02 × light/dark × desktop 1440×900 / mobile
   390×844). All identities are hash-pinned in `EVIDENCE_INDEX.md`.
2. **Pre-implementation responsive/accessibility state evidence.** 35
   additional exports from the same source: 844×390 landscape
   (written/review/video/history/failure, both themes), 200%-reflow
   equivalence, focus-visible boards, long-content stress, History
   empty/storage-unavailable/delete-confirmation, retry-in-flight and
   repeated-failure recovery, no-JavaScript truth boards (light, per file
   09), reduced-motion render, and the D14/D15 mobile corrections proven on
   PUBLIC-02/04 mobile. Static-source limits (screen-reader announcements)
   remain implementation-evidence items by design (arch §12).
3. **Documentation reconciliation.** `README.md` now records the accepted
   live pre-convergence homepage walkthrough (source `90d035a…0787`, PR 86,
   merge `a98cced…f260`, pipeline 122) instead of describing the demo as
   unmerged, records the completed Codex review sequence, and carries the
   round-2 state. `COMPLETION_REPORT.md` was rewritten from the stale
   "Ready to Build / Bible v2.3" template to the truthful current-phase
   report under Bible v2.5 / Roadmap v2.4.

Verification for this round: all 43 exports rendered from the hash-pinned
source and visually inspected (board-1 fidelity, 5C dark practice, five-step
mobile rail, mobile ring caption, delete-confirmation overlay); guardrail
suites rerun green on this branch (`test_governance_pointers` 16 passed,
`test_site_rules` 9 passed with the documented non-secret placeholder).
Readiness stays **Conditional** with only the two §E recordings open; the PR
and implementation writer remain blocked until they are recorded.

## I. Owner acceptance record — Gate 1 closed, 2026-07-19

Pete reviewed the round-2 closure package (this file's §H, the round-2
evidence zip, and the underlying repository package) directly in chat and
recorded:

> "Okay. I approve this. sonnet can go ahead and now implement this."

This closes both remaining §E blockers:

1. **Board-1 ratification.** Pete's approval is given in direct response to
   the round-2 closure package, whose controlling recommendation throughout
   (arch §1.1, this addendum's §C item 1, and the independent Codex verdict)
   is board 1. No alternative was raised. Board 1 is recorded as ratified.
2. **Pete + designated-manager visual approval.** Pete gave direct visual
   approval of the complete package himself, as the actual product owner, in
   this chat session. The separately named "designated session manager"
   (Claude Co-Work) was not convened for a parallel sign-off. Per
   `docs/AI_WORKFLOW.md` ("Explicit instructions from Peter for a specific
   task can create an exception, but the exception must be stated and
   recorded in the handoff"), Pete's direct real-time approval is recorded
   here as an explicit owner-authorized exception to the parallel-manager
   step for this package's Gate 1 only. It does not waive manager
   involvement for any other package, and it does not waive the separate
   real-implementation visual acceptance required by
   `OWNER_VISUAL_INTEGRITY_STANDARD.md` V3, which still applies to the built
   product before that implementation may merge or deploy.

**Gate 1 result: Pass.** Product implementation is now authorized. The
Claude/Fable session (running as Claude Sonnet 5 from this point) proceeds as
the self-managed implementation writer per
`13_SONNET_IMPLEMENTATION_BRIEF.md`, starting a fresh branch from
then-current `origin/main` after this gate branch merges.

**Design and feasibility only; product implementation has not started.**
This file's status is superseded by the paragraph above for the single
purpose of authorizing the implementation branch; the design/feasibility
record itself remains historical evidence, not implementation.
