# PS-HOME-INTERVIEW-DEMO-001 — Accessibility and Validation Plan

## 1. Accessibility contract (WCAG 2.2 AA target)

### 1.1 Structure and semantics

- One `<section aria-labelledby="hv-interview-title">` landmark inside `<main>`;
  heading order within the scene: H2 (scene title) → H3 (sheet title) → H4
  (state headings). The homepage keeps exactly one H1 (hero).
- Every walkthrough control is a native `<button type="button">`; the final
  CTA and no-JS link are native `<a>` elements. No click handlers on
  non-interactive elements.
- Step rail: ordered list; current step exposed via `aria-current="step"`;
  completed steps add a visually-hidden `(completed)` to the accessible name.
  Meaning never depends on the ✓ glyph or color alone — numbers and labels
  are always present.
- Method switch: `aria-pressed` toggle buttons named `Voice` and `Text`;
  the marigold `Default` tag is supplementary text, not the only signal.
- Decorative SVGs (mic orb, waveform, arrows, glyphs) are `aria-hidden="true"`
  with explicit `width`/`height`. The waveform is static in all modes.
- STAR tiles carry their full text (`S — Situation clear`); the improvement
  target additionally says `Strengthen result` in text.

### 1.2 Focus and announcements

- Visible `:focus-visible` outline (≥3px, ≥3:1 contrast against surface) on
  every control and on state headings when programmatically focused.
- Keyboard-triggered transitions move focus to the new state's
  `h4[tabindex="-1"]`; pointer transitions do not steal focus (file `01` §4.3).
- One `role="status"` (`aria-live="polite"`) region per scene announces
  `Step {n} of 4: {name}` exactly once per transition; empty at load; no other
  live regions; no announcement loops.
- Focus is never trapped; there are no dialogs, no roving tabindex, and Tab
  order follows DOM order.

### 1.3 Color, contrast, and motion

- Text contrast ≥4.5:1 (body/metadata) and ≥3:1 (large headings): navy ink on
  warm paper, ivory on navy truth bar, marigold **text** only in the
  text-safe dark shade (`#8A5A00`-equivalent token) on light washes.
- State meaning never depends on color alone (D7 in file `02` §6).
- `prefers-reduced-motion: reduce`: no slide/fade/pulse/waveform/count-up;
  instant state swaps; hover transforms neutralized (extends the existing
  `.home-v3` reduced-motion block).

### 1.4 Reflow, zoom, and touch

- 200 % zoom (and 320 CSS px effective width): single-column reflow, no
  horizontal page scrolling, no clipped or overlapped content, truth bar
  visible.
- Touch targets ≥44×44 CSS px at every breakpoint (file `02` §4–5).
- Mobile landscape (844×390): normal vertical document flow — content scrolls;
  nothing is height-capped or hidden.

### 1.5 No-JavaScript truthfulness

Server HTML alone must deliver: State 1 question and explanation, the truth
checklist and truth bar, the no-JS notice, and a working link to
`/interview-studio`. Interactive controls are CSS-hidden until the JS class is
added, so no dead controls appear (file `01` §5).

## 2. Test plan — `tests/test_homepage_scenes.py`

Add `HomepageInterviewDemoTests` (new class; existing 17 tests untouched).
Helper: slice `self.html` to the scene region between
`data-home-interview-demo` and the following scene marker so scene-scoped
assertions don't collide with the rest of the homepage.

### 2.1 Placement and structure

1. `test_scene_present_between_resume_and_story` — index of the Living Résumé
   marker < index of `data-home-interview-demo` < index of the Story/Future
   marker in the homepage HTML.
2. `test_four_states_server_rendered` — `data-int-state="1"` through `"4"` all
   present; states 2–4 carry `hidden` in server HTML; state 1 does not.
3. `test_existing_scenes_untouched` — hero, Living Résumé, Story/Future, and
   invitation-band markers all still present (belt-and-braces beside the
   existing tests).

### 2.2 Truth boundary

4. `test_no_answer_input_in_scene` — scene region contains no `<form`,
   `<textarea`, or `<input`.
5. `test_no_media_apis_in_scene_script` — `static/js/homepage-interview-demo.js`
   contains none of: `getUserMedia`, `mediaDevices`, `MediaRecorder`,
   `SpeechRecognition`, `AudioContext`.
6. `test_no_network_apis_in_scene_script` — none of: `fetch(`,
   `XMLHttpRequest`, `sendBeacon`, `WebSocket`, `EventSource`.
7. `test_no_storage_apis_in_scene_script` — none of: `localStorage`,
   `sessionStorage`, `indexedDB`, `document.cookie`, `caches.`.
8. `test_truth_bar_server_rendered` — all four labels (`Fictional example`,
   `No visitor input`, `No AI request`, `Nothing stored`) in the scene region.
9. `test_no_pete_attribution_in_walkthrough` — the scene region's walkthrough
   content does not attribute the sample to Pete (the string `Pete` appears
   only inside the truth checklist item `not Pete’s`, which is asserted
   verbatim; no other occurrence).
10. `test_final_cta_resolves_to_interview_studio` — scene region contains
    `href="/interview-studio"` on the State 4 CTA **and** in the no-JS panel;
    `interview_studio` route resolves 200 (client GET).

### 2.3 Copy corrections and banned language

11. `test_corrected_sequence_language` — `capture, to presentation, to
    practice` present; `capture, to proof, to practice` absent from the whole
    page.
12. `test_retry_does_not_invent_outcomes` — `repeatable review process` absent;
    the corrected highlight sentence present verbatim.
13. `test_no_private_history_language` — scene region contains none of:
    `Use my history`, `your history`, `signed in`, `saved to your account`.

### 2.4 Interaction and accessibility contract (server-HTML-checkable)

14. `test_buttons_have_explicit_type` — every `<button` in the scene region
    includes `type="button"`.
15. `test_step_rail_semantics` — four `data-int-step` buttons; exactly one
    `aria-current="step"` (on step 1) in server HTML.
16. `test_live_region_present_and_empty` — one `role="status"` element with
    `data-int-live` in the scene region, empty at load.
17. `test_state_headings_are_focus_targets` — each state panel contains an
    `<h4` with `tabindex="-1"`.
18. `test_method_switch_semantics` — `data-int-method="voice"` button with
    `aria-pressed="true"`, `data-int-method="text"` with
    `aria-pressed="false"`.
19. `test_nojs_fallback_present` — no-JS panel text and its Interview Studio
    link present in server HTML.
20. `test_reduced_motion_css_covers_scene` — `homepage-scenes.css` contains a
    `prefers-reduced-motion` block that references `.hv-interview`
    (static file read).
21. `test_no_fixed_viewport_heights_in_scene_css` — the appended scene CSS
    section contains no `100vh`/`100svh` height locks and no
    `overflow: hidden` on the scene root (static file read of the marked
    section).

### 2.5 Required commands (all must pass)

```bash
python -m pytest tests/test_homepage_scenes.py -q
python -m pytest tests/test_navigation.py -q
python -m pytest tests/test_site_rules.py -q
python -m pytest tests/test_governance_pointers.py -q
python -m pytest -q                # complete configured suite
git diff --check
```

## 3. Manual/behavioral verification (implementation session)

Because unit tests read server HTML, the following are verified by driving the
page (preview server on port 5000; if the Browser pane is frozen, use the
established headless-Chrome fallback):

- Advance through all four states by mouse and again by keyboard; confirm
  focus lands on each state heading only for keyboard activation; confirm one
  announcement per transition (screen reader or live-region inspection).
- Toggle Voice/Text; confirm only the explanation swaps.
- Step-rail direct navigation both directions.
- DevTools network panel: **zero requests** after page load when operating the
  scene; Application panel: no storage keys created.
- `prefers-reduced-motion: reduce` emulation: no animation anywhere in the
  scene.
- JS disabled: State 1 + no-JS panel + working Studio link; no dead controls.

## 4. Screenshot / evidence inventory — `artifacts/ps-home-interview-demo-001/`

| Filename | Capture |
|---|---|
| `desktop-1600x1000-state1.png` … `state4.png` | Each walkthrough state, desktop |
| `mobile-390x844-state1.png` … `state4.png` | Each state, portrait |
| `mobile-844x390-state1.png` | Landscape (truth bar visible) |
| `zoom-200-state3.png` | 200 % zoom reflow, review state |
| `focus-voice.png` | Visible keyboard focus on the Voice control |
| `focus-submit-sample.png` | Visible keyboard focus on Submit sample answer |
| `reduced-motion-state2.png` | Reduced-motion emulation |
| `no-js-initial.png` | JavaScript disabled |

Plus `PARITY_DEVIATION_MATRIX.md` if exported from file `02` §6 for review
convenience.

## 5. Self-review gate

Before requesting manager review, the implementer re-checks every row of:
file `01` §2 pinned copy, §3 prohibited APIs, §4 DOM contract; file `02` §5
correction table; and this file's §1 contract — then records
**Pass / Conditional / Fail** with evidence links in
[COMPLETION_REPORT.md](COMPLETION_REPORT.md).
