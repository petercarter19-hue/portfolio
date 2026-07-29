# 09 — Test, Visual QA, and Acceptance

The implementation is not complete when it merely resembles one screenshot. It must preserve the real product across states, routes, viewports, themes, failures, and assistive technology.

## Test strategy

Use the repository's existing test tools. Prefer existing Playwright/browser harnesses and fixtures. Do not add a heavy visual-test dependency unless the repository has no viable equivalent and the owner approves the dependency change.

For dynamic AI states, use deterministic test fixtures or network interception in test environments only. Production behavior and response contracts remain unchanged.

## Functional regression suite

### Routing and modes

- base Studio route loads;
- all existing Interview Me, Interview AI, Video Practice, and History URLs/deep links load;
- back/forward and refresh preserve the currently supported state;
- no-JS fallback remains truthful;
- neighboring public pages render normally.

### Interview Me

- empty answer cannot submit according to current validation;
- type/paste/edit/undo/redo;
- autosave and restore;
- local-storage blocked state;
- word count;
- new question;
- custom question;
- queue open/close/select;
- draft replacement confirmation;
- keyboard shortcut;
- submit exactly once;
- processing;
- success;
- error and retry;
- try again;
- next question;
- automatic browser-local history;
- review detail;
- improve request/edit/back/use/retry out loud.

### Dictation

- supported + allow;
- permission denied;
- unsupported browser;
- listening;
- stop;
- silence timeout if currently supported;
- text remains editable;
- pre-existing typed text preserved;
- no audio network request or retention claim.

### Interview AI

- best-practice mode;
- Pete public history mode;
- compare mode;
- custom question;
- generated answer;
- source labeling;
- follow-up;
- Practice This Answer;
- failure state;
- no private history access.

### Video Practice

- permission not requested;
- permission allowed;
- permission denied;
- device unavailable;
- record;
- timer;
- stop;
- local playback;
- discard/delete;
- transcript coaching path;
- no upload request;
- no fabricated delivery analytics.

### History

- empty;
- populated;
- filters;
- goals;
- detail dialog;
- delete one record;
- clear local history;
- storage unavailable;
- no cross-device/account claim.

### Theme/state retention

Toggle theme while:

- typing a draft;
- listening;
- queue open;
- settings open;
- processing;
- review visible;
- improve draft edited;
- video permission granted/recording state where technically safe;
- history detail dialog open.

The current supported state may not reset solely because the theme changed.

## Accessibility suite

- automated accessibility scan for each major state in both themes;
- keyboard-only walkthrough;
- visible focus review;
- focus trap and return for dialogs/drawers;
- screen-reader heading/landmark/state review;
- live-region review for save/listening/processing/error;
- reduced-motion review;
- 200% zoom/reflow;
- 320px width;
- touch targets;
- contrast verification;
- no hidden inactive state exposed to accessibility tree.

## Visual state matrix

Capture each state using deterministic fixture data.

| Evidence ID | Reference | Required capture |
|---|---|---|
| VIS-01 | 01 ready light | 1536×1024, 1440×900, 1366×768 |
| VIS-02 | 02 answering/queue light | 1536×1024 |
| VIS-03 | 03 processing light | 1536×1024 |
| VIS-04 | 04 review light | 1536×1024 |
| VIS-05 | 05 improve light | 1536×1024 |
| VIS-06 | 06 Interview AI | 1536×1024 |
| VIS-07 | 07 Video Practice | 1536×1024 |
| VIS-08 | 08 History | 1536×1024 |
| VIS-09 | 09 ready dark | 1536×1024 |
| VIS-10 | 10 review dark | 1536×1024 |
| VIS-11 | 11 mobile ready | 390×844 and 320×568 |
| VIS-12 | 12 mobile listening | 390×844 |
| VIS-13 | 13 mobile review | 390×844 |
| VIS-14 | 14 mobile improve | 390×844 |
| VIS-15 | failure reference | desktop light and 390×844 |
| VIS-16 | tablet reflow | 1024×768 and 834×1194 |
| VIS-17 | mobile landscape | 844×390 |
| VIS-18 | 200% zoom | 1440×900 browser at 200% |

## Visual comparison method

1. Capture the implemented state at the exact reference viewport.
2. Create an overlay or side-by-side comparison with the PNG.
3. Review hierarchy first:
   - question position;
   - composer/action relationship;
   - stage/rail proportions;
   - visible current-state content only;
   - mode/session hierarchy;
   - mobile dock reachability.
4. Review theme and polish:
   - white canvas/navy/cobalt/teal balance;
   - typography scale;
   - border/shadow density;
   - active/secondary emphasis.
5. Review content stress and actual production text.

Do not fail the build on tiny anti-aliasing differences. Do fail visual review for structural drift, missing controls, clipping, wrong hierarchy, or theme divergence.

## Owner acceptance criteria

### First-use clarity

- Within five seconds, a user can identify the current question and where to answer.
- The textarea is immediately obvious; optional dictation and the primary action are visible without hunting.
- Only one action looks primary.
- Supporting content is present but quiet.

### Desktop

- At 1366×768, question, answer field, mic, and primary action appear in the first viewport.
- No horizontal scroll.
- Rail never makes the main stage unusably narrow.

### Mobile

- At 390×844, question context remains visible and actions remain reachable.
- Virtual keyboard does not cover the active input/action.
- Bottom dock does not cover content.
- Drawers/sheets restore focus.

### State truth

- No score/review appears before real review data.
- No improved draft appears before existing improve behavior completes.
- Failure preserves the answer.
- Browser-local and public-demo truth remain accurate.
- Video remains local and no unsupported analytics appear.

### Functional preservation

- No existing core capability is removed.
- No route, endpoint, payload, storage key, auth rule, AI contract, media contract, or history semantic changes.
- All baseline tests remain passing; new regression tests cover the refactor.

### Theme parity

- Light and dark have the same DOM, actions, state order, and responsive behavior.
- Theme switching does not lose state.

## Release boundary

Passing this package produces a reviewable branch/PR only. Merge, Azure pipeline, deployment, and live verification require separate owner authorization and normal PeerSlate release governance.
