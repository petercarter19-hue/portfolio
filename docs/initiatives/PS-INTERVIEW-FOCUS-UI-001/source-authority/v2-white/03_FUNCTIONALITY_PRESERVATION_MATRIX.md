# 03 — Functionality Preservation Matrix

Codex must replace every `TBD after inspection` item with the real file, function, route, selector, storage key, or endpoint before implementation.

| Capability | Current contract to preserve | New presentation | Required regression proof |
|---|---|---|---|
| Studio entry and deep links | Existing `/interview-studio` behavior, mode links/query parameters, browser back/forward, and history deep link remain valid | Orientation content may collapse when a practice mode is active; do not add a replacement route | Open every existing direct URL; refresh; back/forward; no 404 or state loss |
| Global site shell | Existing PeerSlate header, secondary navigation, Ask AI, sign-in/public identity behavior remain | Reuse actual shell; only Studio body changes | Screenshot and route smoke on neighboring pages; no global CSS regression |
| Practice modes | Interview Me, Interview AI, Video Practice remain real links/actions | Three practice cards stay together; History is visually separated as a destination | Keyboard and pointer activation; selected state; deep link preserved |
| Public demo identity | Pete Carter is a clearly labeled public demo profile; visitor is not signed in as Pete | Compact identity chip/rail; no competing large card | Public HTML contains only approved public fixture; no private identity claim |
| Session setup | Experience, question family, session length/mock format, settings, and current selections remain | One compact session summary strip with `Edit session` | Change each option; state updates; active draft replacement confirmation preserved |
| Question source | Existing question bank, current question, question number, competency, framework, timing | Large first-class question; metadata chips; compact sticky summary during long work | Existing question sequence and metadata unchanged |
| Optional example | Existing availability and setting remain | `Need a nudge?` disclosure/drawer; closed by default | Open/close; correct example; focus restored; draft unchanged |
| New/custom question | Existing New Question and add-your-own-question behavior remain | Quiet `New Question`; queue drawer includes custom-question action | Add custom question; select it; confirmation rules; no draft loss |
| Up Next queue | Existing queue and selection behavior remain | Collapsed by default; right drawer on desktop; bottom sheet on small screens | Open/close/select; question ordering; current draft preserved or current confirmation honored |
| Answer textarea | Existing text source of truth, validation, maximum length, and editability remain | Large central composer | Type, paste, undo/redo, long answer, empty state, max length |
| Browser-local draft | Existing autosave debounce/lifecycle and storage key remain | Quiet save status inside composer footer | Reload restores; local-storage blocked state; clear-history/settings behavior |
| Word count | Existing count semantics remain | Adjacent to save state | Updates accurately for typing and dictation |
| Dictation | Existing browser speech recognition, permission handling, silence behavior, stop behavior, and same editable answer remain | Optional `Use dictation` control attached to the type-first composer; live status/waveform; no separate transcript panel | Allow/deny/unavailable/timeout/stop; dictated text editable; no answer overwrite |
| Submit for coaching | Existing validation, keyboard shortcut, endpoint, payload, and duplicate-submit guard remain | Dominant `Review My Answer` next to typed-answer, optional dictation, and save context | Empty disabled/error; nonempty request exactly once; Ctrl/Cmd+Enter preserved |
| Submission privacy | Question/answer sent only on explicit coaching submission; audio not sent or retained | Concise line immediately below composer; details in privacy disclosure | Network inspection proves no coaching call before submit and no audio upload |
| Submitted answer | Existing submitted snapshot is preserved while processing/reviewing | Compact preserved-answer card above current result | Editing/draft semantics match current behavior; failure never destroys answer |
| Coaching processing | Existing request lifecycle and status handling remain | In-place processing panel; answer stays visible; no room/page jump | Loading, slow response, duplicate click, refresh/abort behavior as currently supported |
| Coaching failure | Existing `Keep editing` and `Retry coaching` behavior remain | Error appears where review would appear; explicit `Your answer is safe` | Inject network/server failure; answer intact; retry uses same answer; no fake partial review |
| Coach review | Existing bottom line, score, strengths, improvement, STAR/framework, score details, relevant history and source truth remain | Bottom-line-first hierarchy in one stage; no empty review before response | Deterministic fixture renders every field; missing optional fields degrade gracefully |
| Practice score | Existing value and disclaimer remain | Compact score signal; never largest element | Correct value; `not an employer prediction` remains visible/announced |
| Try again | Existing retry behavior remains | Secondary action | Same question and expected state reset; history semantics preserved |
| Next question | Existing next behavior remains | Secondary/quiet next action beside dominant improve action | Advances exactly once; correct progress; draft/history behavior preserved |
| Improve answer | Existing improve endpoint/response and original-answer preservation remain | Original and editable improved draft side-by-side desktop; stacked/tabs mobile | Request, edit, compare, back, retry out loud, use draft; no invented save/public action |
| Relevant history | Existing approved-public-history grounding only | Contextual rail/panel, secondary to task | Source attribution correct; no private data; optional absence handled |
| Automatic history | Existing completed reviews/rehearsals are added to browser-local history per current behavior | Status only; do not add a new Save button | Complete attempt; history record appears once; refresh; delete/clear works |
| Interview AI | Best-practice example, Pete public history, Compare, custom question, follow-up, source labels, Practice This Answer remain | Shared Focus Stage shell with answer-basis rail | Each mode and endpoint; source labels; no private history claim |
| Video Practice | Existing permission, camera preview, local recording, stop, playback, delete, transcript coaching, device settings remain | Large local video stage with device/recording rail | Permission allow/deny; record/stop/play/delete; no network media upload; transcript coaching unchanged |
| Unavailable video analytics | No pace, eye-contact, filler-word, confidence, or delivery result without real service | Honest unavailable copy remains | No fabricated metric appears in any state |
| History | Existing filters, attempts, goals, detail dialog, deletion, clear local history, storage warnings remain | Separate destination with browser-local summary rail | Empty/populated, blocked storage, filters, detail, delete, clear, refresh |
| Theme | Existing theme preference and toggle remain | Same geometry relit; no separate feature set | Toggle in every state; draft, selection, modal, media, focus, and scroll preserved |
| Settings/dialogs | Existing settings and confirmation logic remain | Accessible drawer/modal; not always visible | Focus trap/return; Escape; background inert; theme switch while open; no state loss |
| No-JS truth | Existing truthful no-JS fallback remains | May be visually refined but must not claim interactivity | Disable JS; links/truth remain understandable |

## Scope-change alarm

If implementing any row requires changing the backend, storage contract, AI response contract, auth boundary, or product semantics, stop and report the conflict. Do not silently expand scope.
