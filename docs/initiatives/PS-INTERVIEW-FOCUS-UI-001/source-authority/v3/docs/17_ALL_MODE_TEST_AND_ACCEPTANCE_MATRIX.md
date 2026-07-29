# 17 — All-Mode Test and Acceptance Matrix

This matrix is mandatory. “Looks like Screen 01” is not sufficient evidence of completion.

## Shared shell

| Test | Expected result |
|---|---|
| Open each mode directly by current route/query | Correct mode active; no unrelated mode content exposed |
| Switch modes with empty state | Route/state changes using released behavior |
| Switch with nonempty text | Current confirmation/preservation behavior remains intact |
| Switch while camera active/recording | Existing safe stop/exit behavior occurs; no device remains active after exit |
| Toggle theme in each major state | State preserved; same DOM/action order; correct tokens |
| 200% zoom | No hidden primary action or horizontal task scrolling |
| Keyboard-only pass | Logical focus order, visible focus, usable drawers/sheets |
| Screen-reader smoke test | Hidden future states not traversed; status not noisy |

## Interview Me

| State/path | Required evidence |
|---|---|
| Ready/type-only | textarea immediately usable; no permission prompt |
| Dictation granted/denied/unavailable | same textarea; typed draft preserved |
| Submit/loading | submitted answer remains visible |
| Coaching success | real fields only; action priority correct |
| Coaching failure | answer preserved; retry/edit available |
| Improve | original safe; assisted draft editable; explicit apply |
| Queue/settings/example | no draft or focus loss |
| Mobile keyboard | no covered textarea/action |

## Interview AI

| State/path | Required evidence |
|---|---|
| Empty | question + basis + Get Answer; no fake result/follow-up |
| Type-only generation | works without microphone |
| Dictation | same question input; nonblocking failure |
| Best-practice result | illustrative label; reasoning/structure shown |
| Public-history result | approved-public-history label and real evidence |
| Compare result | both approaches clearly differentiated |
| Long result/evidence | no overlap/horizontal scroll |
| No grounding | no invented history; recovery available |
| Network failure | question and basis preserved |
| Follow-up | unlock and grounding continuity preserved |
| Practice This Answer | safe existing transfer; no silent overwrite |
| New Question | expected reset and focus behavior |
| Mobile | basis/source accessible; result and primary action readable |

## Video Practice

| State/path | Required evidence |
|---|---|
| Route load | zero camera/microphone prompt |
| Enable devices granted | real preview; device status accurate |
| Camera denied | clear recovery; transcript typing still usable |
| Microphone denied | accurate partial-device state; current behavior preserved |
| Device unavailable/busy | truthful error and retry/settings |
| Start recording | timer and state correct; no duplicate start |
| Stop/finalize | local playback becomes available; no server-processing claim |
| Playback | local status; retake/discard/next path usable |
| Retake | prior local media cleaned per current lifecycle |
| Discard | explicit; unrelated text/history preserved |
| Route exit | tracks/recorder/timers/object URLs cleaned |
| Transcript type/paste | works without camera and without recording |
| Transcript dictation | optional; same textarea; nonblocking failure |
| Transcript coaching | text-only expected request; content feedback only |
| Network capture | no media upload in any media state |
| Storage inspection | no new persistent blob/media key |
| No-analysis truth | no pace/eye-contact/filler/confidence claims |
| Mobile portrait | preview and controls reachable |
| Mobile landscape 844×390 | no clipped stop/discard/device controls |

## History

| State/path | Required evidence |
|---|---|
| No records | honest empty state and next action |
| Completed written attempt | correct local detail |
| Completed video rehearsal | metadata only as released; no retained-video implication |
| Filters/goals | current behavior preserved |
| Storage unavailable | practice works; warning truthful |
| Clear/delete | only intended browser-local data removed |
| Cross-device truth | no account/cloud implication |

## Final owner acceptance

The owner should be able to answer “yes” to all of these:

1. Does Interview Me feel simpler without losing anything?
2. Is typing obviously the normal path?
3. Does Interview AI still feel distinct and more trustworthy—not like a generic chatbot?
4. Can a user immediately tell what source an AI answer uses?
5. Does Video Practice feel like a premium local rehearsal room?
6. Is it impossible to mistake Video Practice for an uploaded or automatically analyzed recording?
7. Do all modes visibly belong to one Interview Studio?
8. Does the light UI read as white rather than beige?
9. Do mobile states remain understandable and reachable?
10. Has Codex proved no backend, grounding, storage, or media contract changed?
