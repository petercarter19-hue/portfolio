# PS-INTERVIEW-PUBLIC-GATE-001 - Dual-Theme Visual Authority and Claude Brief

_Owner decision recorded 2026-07-19. Design and feasibility only. Product
implementation is not authorized._

## Controlling owner decision

The current public `/interview-studio` has one product architecture and two
approved theme expressions:

- **Default/light authority:** Image 5, Concept A, **Editorial Studio Ledger** -
  the left panel and its lower active-written-practice state.
- **Optional dark authority:** Image 5, Concept C, **Cinematic Studio** - the
  right panel and its lower active-written-practice state.
- **Exact original source:**
  `C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`
- **Source identity:** 1,990,578 bytes; 1536x1024 pixels; SHA-256
  `7A03EE1F4569478F067EE2996C575B130077633CB6C2AAA36A058EFE772467DD`.

Concept A controls the recognizable light composition. Concept C controls the
recognizable dark composition. Image 1A and Image 2A are discussion history,
not co-authorities. The separate homepage Interview walkthrough is also not a
co-authority for the real Studio.

This owner decision supersedes only the earlier claim that Concept C or a dark
Studio treatment must wait for a future authenticated product. It does not
authorize an authenticated Studio, a new route, different functionality, or
implementation. Light remains the default Deep Navy Gold expression. Dark is
an optional theme of the same current public Studio.

The current written-practice framing remains controlling. This decision does
not make the public Studio voice-first. Dictation and local media remain
available where the current product truthfully supports them.

## Paste-ready instruction package for Claude

### Assignment

Open the authoritative Azure DevOps repository and follow `START_HERE.md` and
`docs/AI_WORKFLOW.md` before doing anything. Fetch `origin`, verify current
`origin/main`, and read the authority chain in
`docs/governance/CURRENT_BASELINE.yaml`, including Bible v2.5, Roadmap v2.4,
`OWNER_VISUAL_INTEGRITY_STANDARD.md`, and the complete
`PS-INTERVIEW-PUBLIC-GATE-001` package through this file.

You are preparing the complete current-public Interview Studio design and
feasibility package. Do not edit product code, create a product implementation
branch, change routes, or claim implementation. Product implementation remains
blocked until the complete Gate 2.4 package, truth/accessibility review,
Claude/Fable feasibility review, and explicit Pete plus designated-manager
visual approval all pass.

Use this exact visual authority:

- Image 5 Concept A, Editorial Studio Ledger, controls default/light.
- Image 5 Concept C, Cinematic Studio, controls optional dark.
- Original source path:
  `C:\Users\peter\iCloudDrive\Documents\Career\Website\Changes\Interview Studio\ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png`.
- Do not substitute Image 1A or Image 2A and do not blend Concept B into the
  controlling composition.

The finished design must be recognizably the source composition in each theme,
not the current page with borrowed colors. Preserve the website's simplicity
through hierarchy, spacing, and progressive disclosure while reaching the
professional, cinematic finish of the authority.

### One product, one DOM, one state machine

Design one public Studio, not separate light and dark products. Both themes
must use the same:

- `/interview-studio` and `/interview-studio/history` routes;
- information architecture and semantic DOM;
- controls, labels, actions, tab order, focus behavior, live regions, and
  keyboard behavior;
- written-practice, AI, compare, video, history, goal, draft, error, retry, and
  recovery state machine;
- public-profile data and browser-local persistence behavior; and
- responsive and accessibility behavior.

Theme changes presentation only. Do not duplicate the template, fork the
JavaScript state machine, create a dark route, or introduce dark-only actions.
Dark styling must not imply sign-in, private history, account persistence, or a
protected owner Studio.

Use the existing site mechanism in feasibility planning: the global
`#theme-toggle` changes `body[data-theme]`, stores the explicit preference under
`ps-theme`, defaults to light (`modern-blue`), and already applies the saved
dark preference before paint. Do not invent a second Studio theme key or a
second toggle. No-JavaScript behavior stays truthful and light by default.

Switching theme must not recreate the Studio root or reinitialize its script.
It must preserve, without change:

- the current question, session index, progress, selected mode, answer method,
  textarea value, submitted answer, feedback, and active error/retry state;
- browser-local drafts, goals, completed attempts, filters, and history;
- the active camera stream, recorder/playback state, local object URL, typed
  transcript, media-denied state, and media fallback;
- the focused control, selection/caret where applicable, dialog state, and
  scroll position; and
- every `peerslate:interview-studio:<profile>:v1` storage record.

If local storage is unavailable, the theme may still change for the current
page view, but neither theme nor Studio code may report persistence it did not
achieve. Theme switching must never clear Studio data.

### Shared structural component system

Create and document a single structural system that maps to the current Jinja,
page-scoped CSS, vanilla JavaScript, and focused tests:

1. `StudioShell` - public page frame, slim navigation, skip target, live region,
   and shared theme surface.
2. `StudioOrientation` - editorial/cinematic headline, public-demo-profile
   context, one dominant `InterviewMeLaunch`, three quieter mode choices, and
   the persistent `TruthStrip`.
3. `PublicDemoProfile` - Pete Carter labeled exactly as a **Public demo
   profile**, with public-profile grounding and no signed-in implication.
4. `ModeChoice` - Interview Me, Interview AI, Video Practice, and History using
   real availability, selection, disabled, and fallback semantics.
5. `PracticeShell` - question count/progress, Exit practice, question,
   `AnswerComposer`, optional local dictation control, Submit answer, `TipsCard`,
   and `GoalCard`.
6. `ProcessingState` - an in-progress coaching request with the visitor's
   submitted answer visibly preserved and correctly announced.
7. `BottomLineReview` - bottom line first, then What worked, Improve next,
   framework detail, practice-signal context, and progressive secondary actions.
8. `InterviewAIWorkspace` - best-practice, Pete public-profile demo, and compare
   selectors plus source-labeled results.
9. `VideoPracticeWorkspace` - local permission, preview, record/stop, playback,
   delete/retry, typed transcript continuation, and written fallback.
10. `BrowserHistoryWorkspace` - browser-local summary, filters, goal, entries,
    detail, clear/delete controls, empty state, and storage-unavailable state.
11. `RecoveryPanel` - processing failure, media denial/unavailability, preserved
    input, retry, edit, and typed continuation.
12. `DisclosureOrDialog` - optional setup and explanation with correct focus
    entry, focus restoration, escape/cancel behavior, and visible essential
    truth outside the disclosure.

The names above are design/feasibility labels, not an instruction to add a new
front-end framework. Map them to the current `is__*` DOM and data hooks. Preserve
current real functionality unless an explicit Gate 2.4 decision changes it.

### Shared semantic tokens and theme treatments

Define semantic tokens once: canvas, stage, elevated surface, recessed surface,
text, muted text, border, focus, primary action, secondary action, progress,
source/grounding, success, caution, error, shadow, and overlay. Component
structure consumes these semantic tokens; only token values and decorative
treatments vary by theme.

**5A default/light - Editorial Studio Ledger**

- Warm ivory/paper-ledger room surface, with Cloud White and white still used
  where clarity requires them; do not globally recolor the site.
- Newsreader for editorial headings and Inter for navigation, forms, controls,
  metadata, feedback, and product copy.
- Ink Navy `#141A28`, Primary Navy `#203767`, Strong Navy `#132447`, Marigold
  `#B87900`, text-safe gold `#8A5A00`, soft gold `#F4E4B4`, and Success Teal
  `#1E725F` retain their semantic roles.
- Fine warm rules, measured paper depth, soft navy/gold shadows, generous
  whitespace, and restrained editorial ornament.
- One dominant Interview Me object/action; Interview AI, Video Practice, and
  History are smaller and quieter without appearing unavailable.
- Active written practice must retain the source's ledger composition: question
  and answer dominate; progress stays calm; Tips and Goal support rather than
  compete; Submit answer is obvious.

**5C optional dark - Cinematic Studio**

- Layered near-black and deep-navy stage, never flat pure-black emptiness.
- Warm off-white type, restrained signal gold, raised navy/glass surfaces, fine
  gold borders, and real depth.
- A controlled luminous gold focal treatment around the dominant Interview Me
  object. Do not use neon, gaming effects, room-wide glow, excessive gradients,
  or low-contrast glass.
- Use gold for the focal action, progress/current-state cues, selected source,
  and precise highlights. Teal remains success only; red remains true error;
  amber remains caution.
- Preserve exactly the light theme's hierarchy and component placement. The
  active-written state is its cinematic counterpart: readable answer surface,
  obvious gold Submit answer, gold progress/current-state cues, Tips, and Goal.

Both theme token sets must include WCAG contrast measurements for text,
controls, focus indicators, selected state, disabled state, errors, and links.

### Required nine-screen dual-theme system

Produce all nine current-public screens in both themes as separate, legible,
full-screen production-intent evidence. That means 18 primary exports, not one
collage and not a single screen with a palette swap:

1. `PUBLIC-01_ORIENTATION_AND_DEMO_PROFILE`
   - 5A/5C landing composition, one dominant Interview Me action, smaller
     Interview AI/Video Practice/History choices, public demo profile, and
     visible truth strip.
2. `PUBLIC-02_ACTIVE_WRITTEN_PRACTICE`
   - current written practice, question/progress, editable answer, local
     dictation as an available aid rather than a new default, Tips, Goal, and an
     obvious Submit answer.
3. `PUBLIC-03_PROCESSING_ANSWER_PRESERVED`
   - truthful coaching progress, answer visibly preserved, no premature score
     or fabricated success, and accessible status announcement.
4. `PUBLIC-04_BOTTOM_LINE_REVIEW`
   - bottom line first, What worked, Improve next, supporting framework detail,
     secondary next actions, and score labeled **Practice signal - not an
     employer prediction**.
5. `PUBLIC-05_INTERVIEW_AI_AND_COMPARE`
   - best-practice, Pete public-profile demo, and compare modes with explicit
     source labels that remain attached to every result.
6. `PUBLIC-06_VIDEO_PRACTICE_LOCAL`
   - camera permission, local preview/rehearsal, record/stop, local playback,
     delete/retry, typed transcript continuation, and a clear written fallback.
7. `PUBLIC-07_BROWSER_LOCAL_HISTORY`
   - browser-local drafts/goals/completed attempts, filters/detail, honest empty
     state, clear/delete controls, and no account or cross-device suggestion.
8. `PUBLIC-V01_PROCESSING_FAILURE`
   - answer and question preserved, plain-language request failure, edit and
     retry, no lost draft, and no success-looking placeholder.
9. `PUBLIC-V02_CAMERA_MIC_DENIED`
   - exact denied/unavailable explanation, retry permission where meaningful,
     camera-off/local typed path, and first-class written practice fallback.

### Responsive, accessibility, and failure source

For both themes, create editable source and named evidence for desktop,
mobile portrait, mobile landscape, and 200% zoom/reflow for the applicable
written, processing, review, AI/compare, video, history, and failure journeys.

- Desktop evidence: 1440x900 and 1920x1080.
- Mobile portrait evidence: 390x844.
- Mobile landscape evidence: 844x390.
- Mobile and 200% views reflow and scroll. Never scale the desktop frame down,
  hide the truth strip, or shrink text/controls to fit one viewport.
- Keep essential body text readable and primary touch targets at least 44x44
  CSS pixels; document any compact-control exception and its accessible target.
- Specify visible keyboard focus, logical focus order, dialog focus entry and
  restoration, tab/selected/expanded/disabled semantics, and live-region
  announcements for processing, success, error, retry, and recovery.
- Specify reduced-motion behavior; no state or meaning may depend on animation.
- Include long question, long answer, long feedback, long history, and translated
  or wrapping-label stress states.
- Include JavaScript unavailable, local-storage unavailable, media unavailable,
  permission denied, request error, retry, and recovery. Essential public/demo,
  browser-storage, transmission, media, and score truth remains visible in
  server-rendered HTML when JavaScript is unavailable.
- Do not hide real functionality to make the composition simpler. Use hierarchy
  and progressive disclosure.

### Product truth and functionality that may not be lost

- Interview Me remains the primary mode and current written-practice flow.
- A visitor's question and answer are sent to PeerSlate only when submitted for
  coaching.
- Interview AI keeps generic best-practice, Pete public-profile demo, and
  compare modes with explicit source labels.
- Pete is **Public demo profile**, never the visitor or signed-in identity.
- Video Practice remains local camera rehearsal. Media is not uploaded,
  analyzed, or retained by PeerSlate.
- Drafts, goals, completed attempts, and History are saved only in this browser,
  are clearable there, and are not account-backed or cross-device synced.
- Practice scores are practice signals, not employer predictions.
- No public action creates or edits Capture, Moment, Journal, Story, resume,
  Placement, publication, sharing, audience, account history, or a private
  `/app/interview-studio`.
- No design may imply protected/private behavior merely because it uses the
  cinematic dark theme.

### Claude/Fable feasibility review - still no implementation

After the complete design source exists, review it against the real current
page and return a feasibility matrix that:

- maps every component and state to
  `templates/interview_studio.html`, `static/css/interview-studio.css`,
  `static/js/interview-studio.js`, and `tests/test_interview_studio.py`;
- maps light/dark styling to the existing global `body[data-theme]` / `ps-theme`
  mechanism without a second toggle or state tree;
- proves the theme-switch no-state-loss invariants above;
- identifies any requirement outside the currently reserved files and stops for
  manager reservation rather than editing it;
- identifies contrast, responsive, semantic, performance, media, storage,
  browser, and state-machine risks;
- lists every proposed deviation from 5A or 5C and explains why it improves
  truth, accessibility, or real-product fit; and
- gives a feasibility result of `Pass`, `Conditional`, or `Fail`.

Do not begin product implementation from your own feasibility result. Return it
to the designated session manager. Pete and the manager must review the actual
complete light/dark design evidence and issue explicit visual approval first.
Only then may a new implementation branch start from then-current
`origin/main`.

### Exact return package and readiness result

Return all of the following:

1. an authority manifest naming the exact Image 5 source path and identifying
   Concept A as light control and Concept C as dark control, including the
   source size, dimensions, and SHA-256 recorded above;
2. 18 separate primary full-screen exports: nine light and nine dark;
3. editable responsive source covering both themes and every required viewport,
   reflow, long-content, focus, reduced-motion, unavailable, error, retry, and
   recovery state;
4. a shared component/semantic-DOM inventory and interaction-state map;
5. a two-theme semantic token sheet with contrast results;
6. a screen-by-screen truth and accessibility review;
7. a 5A/5C visual-parity matrix with every deviation called out;
8. the Claude/Fable feasibility matrix mapped to the current reserved files;
9. the theme persistence and no-state-loss test plan;
10. exact branch and full SHA for any repository-hosted design record, plus a
    complete asset index and hashes for the editable source and exports;
11. a plain-English walkthrough for Pete; and
12. one final readiness result: `Pass`, `Conditional`, or `Fail`, with blockers
    and one next action.

`Pass` is permitted only when the complete nine-screen dual-theme responsive
system, truth/accessibility review, feasibility review, and comparison evidence
are present and coherent. Missing screens, palette-only dark treatment,
unreadable mobile scaling, hidden truth, state loss on theme switch, invented
private capability, or missing editable source requires `Conditional` or
`Fail`.

End the returned package with:

**Design and feasibility only; product implementation has not started.**

## Gate state after this owner decision

- Visual authority: **Recorded** - 5A light / 5C dark.
- Complete dual-theme nine-screen design: **Not yet accepted**.
- Truth/accessibility review: **Pending complete package**.
- Claude/Fable feasibility: **Pending complete package**.
- Pete/designated-manager visual approval: **Pending**.
- Product implementation: **Not authorized**.
- Demonstration, deployment, and live-production status: **Unchanged**.
