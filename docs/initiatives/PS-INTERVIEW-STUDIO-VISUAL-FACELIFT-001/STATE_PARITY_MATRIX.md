# State and functionality parity matrix

> **RETIRED — DO NOT IMPLEMENT.** This matrix belongs to the withdrawn
> 2026-08-01 facelift direction and remains only for provenance. The current
> Studio keeps its released Deep Navy Gold composition plus the two narrow
> Round-4 corrections.

This matrix translates the visual lock into implementation constraints. It does
not replace the released tests or the complete V3 all-mode contracts.

## Shared shell

| Surface | Must remain | Facelift treatment |
| --- | --- | --- |
| Routes | `/interview-studio`, `/interview-studio/history`, released mode query behavior, legacy redirects | No route changes |
| Route-local header | Existing destinations only | Compact mockup header inside Studio; shared header files untouched |
| Mode navigation | Interview Me, Interview AI, Video Practice, History; direct links and current ARIA/tab behavior | Compact selected-tab treatment |
| Session setup | Current level/family/format/basis values, Edit Session behavior, preservation prompts | Recompose visually without changing form values or handlers |
| Theme | Existing persisted theme preference and state retention | Pearl/green light and smoky-teal/champagne dark on one DOM |
| Profile truth | Public demo profile, not signed in as Pete, approved public history only | Mockup profile treatment; no private-Slate claim |
| Orientation | Current landing content and destinations | Preserve structure; inherit the shared facelift |

## Interview Me

| State/path | Functional lock | Visual authority |
| --- | --- | --- |
| Idle drafting | Textarea immediately usable; no permission prompt; Review disabled until text | Derive from 01/02 with idle microphone and empty composer |
| Typing | Same textarea, limits, word count, browser-local draft, autogrow | 01/02 composition |
| Dictation active | Same textarea; Stop dictation; interim text; typed text preserved | 01/02 exact pictured state |
| Permission denied/unavailable | Typing remains usable; nonblocking recovery; draft preserved | 01/02 tokens; released error structure |
| Submit/processing | Explicit submit only; submitted answer remains visible; duplicate submit prevented | Released in-place structure; 03/04 hierarchy |
| Coaching failure | Answer preserved; retry/edit available; no fabricated feedback | Released structure; 03/04 tokens |
| Review ready | Complete submitted answer preserved; 82/100-style practice score semantics; Bottom line; worked/improve; STAR; Score detail | 03/04 |
| Review actions | `Try again`, `Improve answer`, `Next Question`; current confirmation/queue behavior | 03/04 priority |
| Improve | Original answer safe; AI-assisted draft editable; What changed; current coaching controls | 05/06 |
| Improve actions | `Use This Draft`, `Retry Out Loud`, `Back to Feedback`; explicit transfer only | 05/06 |
| Nudge/example/queue/settings | Current request triggers, focus return, and draft preservation | Current responsive rail/drawer with facelift tokens |

## Interview AI

| State/path | Functional lock | Visual authority |
| --- | --- | --- |
| Empty/question entry | Type first; optional dictation into same input; explicit Get Answer | 07/08 structure with empty result hidden |
| Basis | Best-practice, approved public history, Compare; selected basis retained and labeled | 07/08 basis rail |
| Generating/failure | Question/basis preserved; current retry/error behavior; no fake result | 07/08 tokens and current state structure |
| Best-practice result | Clearly illustrative; no member history attributed | 07/08 result workspace |
| Public-history result | Approved-public-history label and real returned evidence only | 07/08 pictured state |
| Compare/no grounding | Separately labeled answers; no invented history; truthful recovery | 07/08 current structure |
| Follow-up | Unlock only after first answer; selected basis continuity; current request contract | 07/08 lower workspace |
| Practice This Answer | Safe current transfer into Interview Me; no silent overwrite/save/publish | 07/08 actions |

## Video Practice

| State/path | Functional lock | Visual authority |
| --- | --- | --- |
| Route load/camera off | Zero permission prompt; one Enable Camera action; transcript typing available | 09/10 exact pictured state |
| Requesting/denied/unavailable | Stable stage; truthful device status and recovery; transcript remains usable | 09/10 tokens; current structure |
| Preview ready | Real local preview; Start Answer primary; settings/question change secondary | Camera-dominant 09/10 structure |
| Recording | Stop Recording sole primary; timer visible; no transcript/analytics competition | Camera-dominant 09/10 structure |
| Stopping | Local finalization truth only; no server-processing claim | Stable camera stage |
| Playback | Local playback, duration, retake/discard/next; no delivery analysis | Stable camera stage and current result rail |
| Retake/discard/exit | Existing confirmation and cleanup; transcript/unrelated history preserved as released | Current handlers unchanged |
| Transcript coaching | Type/paste primary; optional dictation same textarea; explicit text-only submit | 09/10 secondary transcript card |
| Network/storage truth | No media body/upload; no retained media key | Visible local-only copy |

## History

| State/path | Functional lock | Visual authority |
| --- | --- | --- |
| Populated | Real browser-local records, written score and video metadata only | 11/12 exact pictured state |
| Empty | Honest empty state and Start practicing action | 11/12 tokens; current structure |
| Filters/goals | Current Mode/Competency/Time behavior; target save and progress | 11/12 |
| Detail | Current answer/review/video metadata; theme retained; explicit local delete | Current dialog structure with 11/12 tokens |
| Storage unavailable | Practice still works; truthful warning; no fake persistence | 11/12 tokens; current state structure |
| Clear/delete | Only intended browser-local Studio records removed after current confirmation | Restrained destructive treatment |

## Required regression evidence

- Existing Interview tests with zero weakened assertions.
- Focused tests proving the Studio-local header uses existing destinations and
  shared header files are unchanged.
- Static/DOM checks for required labels, controls, truth copy, theme single-DOM
  structure, and preserved data hooks.
- Browser pass for all pictured states and representative unpictured states.
- Network proof that media remains local and coaching sends only released text
  requests.
- Storage proof that keys and retained data classes are unchanged.
- Keyboard/focus, 200% zoom, reduced motion, 390×844 portrait, and 844×390
  Video Practice landscape.
