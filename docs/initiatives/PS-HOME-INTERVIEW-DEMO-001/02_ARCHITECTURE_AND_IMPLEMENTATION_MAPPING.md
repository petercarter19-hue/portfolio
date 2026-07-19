# PS-HOME-INTERVIEW-DEMO-001 — Architecture and Implementation Mapping

This document maps the design authority onto the real repository. It is the
implementation blueprint: a writer following this file plus
[01_BOUNDARY_AND_STATE_CONTRACT.md](01_BOUNDARY_AND_STATE_CONTRACT.md) should
need no further product decisions.

> **Amendment — 2026-07-19b.** The interaction is now a **pop-out modal** (an
> on-page poster whose "Walk me through it" button opens a dialog that steps
> through the four states over a dimmed backdrop), replacing the original
> inline panel-swap, per owner direction for continuity with the Voice hero
> overlay. See the amendment at the top of file `01`. Net implementation
> deltas: `_interview_demo_scene.html` renders a poster + a `hidden` modal
> (`data-int-overlay` / `[data-int-modal]`); `homepage-interview-demo.js`
> opens/closes the modal, portals it to `<body>` inside a `home-v3` wrapper
> (to escape `main.main-content`'s `isolation: isolate` trap), traps focus,
> and steps through; `homepage-scenes.css` gains the overlay/modal/poster
> styles (matching the Voice overlay's values) and pins the portaled modal to
> the paper-light palette in both themes. New `[hidden]` guards were required
> for `.hv-int-overlay` (display:grid) and the `.hv-int-back/next/finish`
> controls (shared `.hv-btn` display) — the same specificity trap documented
> for `.hv-int-explain`. All truth-boundary rules and pinned copy are
> unchanged.

## 1. Current homepage facts (verified on `origin/main` @ `31864e4`)

- `templates/homepage.html` (40 lines) composes four partials in order:
  `_voice_hero.html` → `_living_resume_scene.html` → `_story_future_scene.html`
  → `_invite_band.html`, inside a `.home-v3` wrapper, and links
  `static/css/homepage-scenes.css?v=three-scenes-1`.
- **The homepage currently loads no JavaScript.** This package adds its first,
  strictly-scoped script.
- `static/css/homepage-scenes.css` (1675 lines) scopes every rule under
  `.home-v3`, uses the `hv-` class prefix and `--hv-*` tokens mapped to shared
  `--ps-*` tokens (navy `#203767` / strong `#132447`, marigold `#B87900`,
  ink `#0A1B36`, text `#22334E`, muted `#66778F`, cloud `#F6F7FA`), Inter +
  Newsreader (already loaded), radius tokens `--hv-radius-lg/md`, and
  established breakpoints at **1180 / 860 / 560 px** plus a
  `prefers-reduced-motion` block.
- Scene grammar (from `_living_resume_scene.html`):
  `<section class="hv-x" aria-labelledby>` → `.site-container` inner →
  `.hv-eyebrow`, `h2.hv-scene-title` (Newsreader, `<em>` accents),
  `.hv-scene-lede`, `.hv-actions` with `.hv-btn--primary/--ghost`, `.hv-trust`
  note. Comments at the top of each partial explain intent.
- `tests/test_homepage_scenes.py` uses `unittest` with a class-level test
  client that fetches `/` once; 17 tests pin scene content and banned copy.
- Templates may call `url_for('interview_studio')` directly — **no `app.py`
  change is needed** for the final CTA.

## 2. File-by-file implementation map

### 2.1 `templates/homepage.html` (edit: 2 small changes)

1. Insert between the Living Résumé and Story/Future includes:
   ```jinja
   {% include "partials/homepage/_interview_demo_scene.html" %}
   ```
2. Add the scene script (homepage's first JS) in the scripts block, matching
   the site's existing pattern (`defer`, cache-busting query):
   ```jinja
   {% block extra_scripts %}
   <script src="{{ url_for('static', filename='js/homepage-interview-demo.js') }}?v=int-demo-1" defer></script>
   {% endblock %}
   ```
3. Bump the CSS cache-busting query `?v=three-scenes-1` → `?v=interview-demo-1`.
4. Update the header comment block to name this package and the new scene
   order (Voice hero → Living Résumé → **Interview walkthrough** → My
   Story/Future → invitation band).

No other change. The global header, footer, hero, existing scenes, and
invitation band are untouched.

### 2.2 `templates/partials/homepage/_interview_demo_scene.html` (new)

Implements the DOM contract in file `01` §4.1, following the existing partial
conventions (top intent comment, HTML entities, `width`/`height` on any inline
SVG, no external assets). Composition per the Direction A desktop PNGs:

- **Editorial left column** (`hv-interview__copy`): eyebrow, H2, lede, badge,
  truth checklist, sequence note (pinned copy, file `01` §2.1).
- **Ledger sheet** (`hv-int-sheet`): header (kicker, H3, step counter), step
  rail, four state panels, no-JS panel, persistent truth bar (pinned copy,
  file `01` §2.2–2.7).
- The design PNGs' **top narrative rail** (Voice Capture → Living Résumé →
  Interview Studio → My Story & Future) is **not implemented as page
  navigation** — see deviation D1 (§6).
- All copy is hard-coded fixed content. The only Jinja expressions are
  `url_for('interview_studio')` for the final CTA and no-JS link, and
  `url_for('static', ...)` if any static asset is referenced. No data context
  is required from the route (nothing in `app.py` changes).
- Decorative graphics (mic orb, waveform, keyboard glyph) are inline SVG with
  `aria-hidden="true"`; the waveform is static bars, never animated.

### 2.3 `static/css/homepage-scenes.css` (append one marked section)

Append at end of file, before nothing else moves:

```css
/* =====================================================================
   PS-HOME-INTERVIEW-DEMO-001 — Interview Studio illustrative walkthrough
   Scene 3 of 4. Scoped under .home-v3 .hv-interview. Fixed fictional
   content; controls are hidden without JS (.hv-int--js gate).
   ===================================================================== */
```

Architecture rules:

- Everything scoped `.home-v3 .hv-interview …`; class prefix `hv-int-` for
  scene-internal pieces; reuse `--hv-*` tokens; **no new fonts, no new
  global tokens, no changes to existing rules.**
- Semantic accents follow Deep Navy Gold: navy = current step / primary
  action / selected method; marigold = highlights, `Default` tag, STAR
  improvement target, retry highlight (`--hv-amber` `#B87900` family with a
  soft wash background); teal/green (`--hv-green` `#2B9B6D`) only for
  completed step ✓ and completed STAR tiles; the truth bar uses the navy ink
  band styling from the PNGs.
- Layout: two-column grid `minmax(0, .38fr) minmax(0, .62fr)` at desktop;
  stacks (copy above sheet) at ≤1180 or ≤860 consistent with neighboring
  scenes; sheet is `border-radius: var(--hv-radius-lg)` with
  `--hv-shadow-lift`.
- **No fixed viewport heights anywhere.** The scene flows in the document
  and grows with content (this deliberately replaces the design source's
  `height: calc(100vh - …)` + `overflow: hidden` approach — deviation D3).
- JS gating: `.hv-interview:not(.hv-int--js) .hv-int-controls { display:none }`
  and `.hv-interview.hv-int--js .hv-int-nojs { display:none }`.
- Focus visibility: `:focus-visible` outline `3px solid var(--hv-indigo)`
  (`outline-offset: 2px`); on navy surfaces use a light outline. State
  headings (`h4[tabindex="-1"]`) show the same outline when programmatically
  focused.
- Motion: hover lifts and the optional state cross-fade live inside
  `@media (prefers-reduced-motion: no-preference)`. Extend the file's
  existing `prefers-reduced-motion: reduce` block with
  `.hv-interview` neutralizations (no transform, no transition, no animation).

### 2.4 `static/js/homepage-interview-demo.js` (new)

Plain script (IIFE), `defer`, no modules, no dependencies — consistent with
`interview-studio.js` style. Full behavioral contract in file `01` §3–4.
Skeleton:

```js
(function () {
    'use strict';
    var root = document.querySelector('[data-home-interview-demo]');
    if (!root || root.dataset.intReady) return;
    root.dataset.intReady = 'true';
    root.classList.add('hv-int--js');

    var STATE_NAMES = { 1: 'Question', 2: 'Sample answer', 3: 'Coaching review', 4: 'Improved retry' };
    var live = root.querySelector('[data-int-live]');
    var count = root.querySelector('[data-int-count]');
    var panels = root.querySelectorAll('[data-int-state]');
    var steps = root.querySelectorAll('[data-int-step]');
    var current = 1;
    var pointerActive = false;

    root.addEventListener('pointerdown', function () { pointerActive = true; });

    function go(n, viaKeyboard) { /* hidden toggles, aria-current, data-done,
        counter text, single live-region write, optional heading focus */ }
    function setMethod(method) { /* aria-pressed swap + explanation panels */ }

    root.addEventListener('click', function (event) {
        var goBtn = event.target.closest('[data-int-go], [data-int-step]');
        var methodBtn = event.target.closest('[data-int-method]');
        if (goBtn) go(Number(goBtn.dataset.intGo || goBtn.dataset.intStep), !pointerActive);
        else if (methodBtn) setMethod(methodBtn.dataset.intMethod);
        pointerActive = false;
    });
}());
```

Hard prohibitions (asserted by tests): no network, storage, media, speech, or
form APIs; no DOM access outside `root`; no timers/observers/animation frames.

### 2.5 `tests/test_homepage_scenes.py` (extend)

Add a new `HomepageInterviewDemoTests(unittest.TestCase)` class beside the
existing one; do not modify existing tests. Full test list in
[03_ACCESSIBILITY_AND_VALIDATION_PLAN.md](03_ACCESSIBILITY_AND_VALIDATION_PLAN.md) §3.

### 2.6 `artifacts/ps-home-interview-demo-001/` (new)

Screenshot evidence per file `03` §4, plus the parity/deviation matrix if
exported separately.

## 3. State/interaction architecture summary

Deterministic four-state machine, DOM-owned visibility (`hidden` attribute),
single `role="status"` live region, keyboard-modality-aware focus movement to
`h4[tabindex="-1"]` targets, always-operable step rail, method toggle that
changes explanation only. Fully specified in file `01` §4.

## 4. Responsive and reflow architecture (replaces design-source CSS)

| Breakpoint | Behavior |
|---|---|
| Desktop ≥1181 | Two-column editorial + sheet, per desktop PNGs at 1600×1000. |
| ≤1180 | Columns tighten (mirror `hv-resume` handling); sheet full width below copy if needed. |
| ≤860 | Single column: editorial copy (kept brief) above the sheet. Step rail becomes a wrapped 2×2 or horizontal scroll-free wrap; all four labels remain visible. |
| ≤560 (incl. 390×844 portrait) | Fully stacked document flow. STAR tiles wrap 2×2; retry panels stack vertically with **both** original and retry visible; truth bar wraps to two lines but never hides. |
| Mobile landscape 844×390 | Same stacked flow as portrait — the page scrolls vertically. No height-capped composition, no hidden truth labels. |
| 200 % zoom / 320 px effective | Reflow only: `minmax(0, …)` grids, `overflow-wrap: anywhere` on transcript text, no horizontal page scroll, no clipped content. |

Type floor: body/transcript copy ≥ `0.875rem` (14px), metadata/chips ≥
`0.78rem` (~12.5px), nothing below `0.75rem` ever. Controls (step buttons,
advance buttons, method toggle, CTA): `min-height: 2.75rem` (44px) and
adequate horizontal padding at every breakpoint.

## 5. Required corrections to the design source (owner list → architecture)

| # | Owner correction | Architectural resolution |
|---|---|---|
| 1 | No 5.5–10.5 px mobile text | Type floor in §4; the source's `@media (max-width:700px)` and `(max-height:500px)` sizing is discarded wholesale. |
| 2 | Reflow + vertical scroll, not one-viewport squeeze | No fixed heights, no `overflow: hidden` composition (§2.3, §4). |
| 3 | ≥44 px touch controls | `min-height: 2.75rem` on all interactive controls (§4). |
| 4 | Truth labels visible in mobile landscape | Truth bar always rendered; the source's `display:none` rules for `.truth-list`/truth bar are not carried over (file `01` §2.7). |
| 5 | Real 200 % zoom reflow | §4 last row; validated in evidence (file `03` §4). |
| 6 | "capture, to presentation, to practice" | Pinned in file `01` §2.1/§2.8. |
| 7 | Remove un-established "repeatable review process" claim | Pinned removal + tile rewording in file `01` §2.6/§2.8. |
| 8 | Corrections are documented improvements, not a visual downgrade | This table plus the deviation matrix (§6) record each change with its justification; composition, palette, and copy otherwise follow the PNGs. |

## 6. Visual parity / deviation matrix (design authority → implementation)

| ID | Design source shows | Implementation does | Why it improves the result |
|---|---|---|---|
| D1 | Top narrative rail (Voice Capture → Living Résumé → Interview Studio → My Story & Future) as a page-level bar | Not implemented as navigation. The scene uses the standard `hv-eyebrow` (`Homepage scene · Interview Studio`) and the sequence note carries the narrative order | Owner rule: "Do not add another navigation layer." The real homepage has no such rail; adding one would create a second navigation system and dead controls |
| D2 | Voice/Text switch rendered selected-only | Real two-button toggle (`aria-pressed`) that swaps the input-method explanation only | Repository rule against dead controls (see `_living_resume_scene.html` comment); voice-first addendum names Text a first-class peer. Content never changes; boundary intact |
| D3 | `height: calc(100vh - …)`, `overflow: hidden`, one-viewport mobile squeeze | Document flow, vertical scrolling, stacked mobile layout | Owner corrections 1–5; Gate 2.4 mobile-legibility finding; WCAG 2.2 AA reflow |
| D4 | 5.5–10.5 px mobile type, 27–40 px controls | ≥12.5 px metadata / ≥14 px body, ≥44 px controls | Owner corrections 1, 3 |
| D5 | Truth bar hidden in mobile landscape | Truth bar persistent at all breakpoints | Owner correction 4; package's own truthfulness claims |
| D6 | "capture, to proof, to practice"; "repeatable review process" in retry | Corrected copy per file `01` §2.8 | Owner corrections 6, 7; Site Rules deprecate user-facing "proof"; coaching must not model invented outcomes |
| D7 | Static mock buttons without types/ARIA | `button type="button"`, `aria-current="step"`, `aria-pressed`, single `role="status"` live region, `tabindex="-1"` focus targets | Gate 2.4 accessibility-annotation gap; owner interaction requirements |
| D8 | Retry hides the original sample on portrait | Both panels stack, original above retry | Comparison is the state's point; hiding one side breaks it (correction 2) |
| D9 | Package `REVIEW_GALLERY.html` / desktop-only footer id | Not carried into production | Review chrome, not product content |

All other composition — editorial split, ledger sheet, step rail placement,
chips, bottom-line treatment, STAR tiles, highlight treatment, truth bar, CTA
placement — follows the PNGs.

## 7. Rollback approach

The scene is additive and isolated:

1. `templates/homepage.html`: remove the one include line and the script
   block addition (and optionally revert the CSS cache query).
2. The partial, script, appended CSS section, and tests are inert once the
   include is gone; deleting them completes the rollback.
3. Standard path: `git revert` of the squash-merge commit restores the exact
   prior homepage. The old `/experience` rollback route from
   PS-HOME-STORY-001 is unaffected.

No data, storage, route, or backend state exists to clean up — the scene
stores nothing by design.

## 8. Explicitly out of scope

- Any edit to the real Interview Studio files, `app.py`, `base.html`, global
  navigation, shared tokens, or governance pointers.
- The two `GATE2-CORRECTION-*` full-Studio references in the ZIP (design
  material for the separate Studio initiative only).
- Analytics, telemetry, storage, personalization, or A/B behavior of any kind.
