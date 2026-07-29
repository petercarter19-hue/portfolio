# Page Purpose and Non-Redundancy Inventory

This is the controlled V0/V1 inventory required by
`docs/templates/PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md`. It transcribes
the meaningful items already present in the owner-approved V3/V2 package and
Pete's compact-height correction. It does not add a new capability or infer
approval for an item outside that accepted authority.

## A. Scope and approval

- Initiative / slice: `PS-INTERVIEW-FOCUS-UI-001`.
- Page or surface: public `/interview-studio` and
  `/interview-studio/history`, including Interview Me, Interview AI, Video
  Practice, and browser-local History states in the shared Studio shell.
- Member need this page serves: practice an interview answer, request bounded
  text coaching or an evidence-labeled model answer, rehearse locally on
  camera, and revisit records held in the current browser without confusing
  any of those activities with private account history or cloud retention.
- Named capability and visual authority status: V3
  `v3-all-modes-complete` is the controlling ChatGPT-created, Pete-approved
  authority; V2 White is supplemental; Pete's 2026-07-28 compact-height and
  automatic-growth correction controls composer geometry. The exact archives
  and hashes are recorded in this initiative's `README.md`.
- Known source / capability limits: this is the existing public/browser-local
  Studio. The package changes presentation, semantic markup, responsive
  layout, accessibility, and state visibility only. It adds no route, request
  schema, prompt, rubric, provider, private-history retrieval, storage key,
  media upload, automatic transcription, delivery analysis, authentication,
  database, or cloud persistence.
- Prepared by / date: current ChatGPT Work/Codex designated manager,
  2026-07-28.
- Pete inventory approval / date: Pete's written 2026-07-28 approval covered
  the supplied all-modes V3 mockups and instructions, retained V2 as
  supplemental authority, and changed only the pictured empty composer
  heights: start at approximately half height and grow automatically with
  content. His later written instruction authorized validated release while he
  sleeps. The rows below are a traceability transcription of that approved
  package and correction, not a later agent-created product decision.
- Inventory status: **Pete approved — 2026-07-28**.

Repeated decorative borders, divider lines, icons, and background treatments
are grouped with their parent item because they carry no separate claim,
action, destination, privacy meaning, or lifecycle.

## B. Meaningful item decisions

### Shared Interview Studio shell

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision: Keep / Change / Combine / Remove / Defer | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Existing global PeerSlate header and navigation | Keep the Studio connected to the public site and known destinations | Existing shared shell; this package does not create a second global navigation system | Uses existing public links and current mobile navigation | Public; no Studio data is created by navigation | Only site-level navigation layer | Keep | V3 requires existing-site continuity |
| Interview Studio identity and public-practice truth | Explain where the person is and that this is the current public practice experience | Existing route and public/browser-local boundary | Orients; no separate destination | Public; does not imply an authenticated owner workspace | Only route-level identity and audience statement | Change | Make it concise and task-supporting in the approved Focus shell |
| Interview Me / Interview AI / Video Practice mode selector | Move among the three active practice modes | Existing route/state behavior and existing confirmation/cleanup rules | Selects one mode; preserves or safely stops work according to released behavior | Public interaction; text/history remains subject to current browser/request behavior and video remains local | Only primary mode switcher | Change | Preserve all modes while giving the selected task visual dominance |
| History entry | Reach attempts and goals stored by this browser | Existing browser-local records only | Opens History in the current Studio routing/state model | Current browser/device only; not private account history or cross-device sync | Only history destination; deliberately adjacent to, not a fourth practice action | Change | Keep distinct from the three practice modes and label its local truth |
| Theme control | Choose the same Studio in light or dark treatment | Existing theme mechanism; identical DOM, state, actions, and capability | Toggles approved theme without resetting work | Browser presentation preference; no content/audience change | Only theme control | Change | Apply the approved white/navy/cobalt/teal system and its dark-token twin |
| Session summary | Keep experience level, question family, and format visible | Existing session configuration and fixture/public context | Read-only summary of current settings | Public/browser-local session context; not canonical profile truth | Only compact session-orientation object | Change | Retain context but reduce competition with the active task |
| Edit Session | Adjust current session configuration through existing behavior | Existing configuration contract; no new settings or persistence | Opens the existing edit/configuration path | Uses current browser/session lifecycle | Only configuration action | Keep | Required capability remains available but secondary |
| Current question, progress, and essential metadata | Preserve continuity across answer, AI, video, and review states | Existing question/session state | Read; question changes only through existing next/new-question behavior | Public fixture/session content | One canonical current-question presentation per active state | Change | Place near the active task and avoid duplicate large question panels |
| Context rail / mobile disclosure | Supply basis, device, session, source, or coaching context without obscuring the task | Existing real state only; rail is presentational, not a second state owner | Opens existing disclosures/settings where applicable | Inherits each item's public, browser-local, or local-media boundary | Only secondary context region; becomes an accessible disclosure/sheet when narrow | Change | Preserve supporting detail while keeping the task dominant |
| Status, success, and failure announcements | Explain asynchronous, dictation, generation, coaching, device, storage, and recovery state | Only real current state; no fabricated completion or analysis | Announces status and exposes the applicable retry/recovery action | Does not create new storage or transmission | Only programmatic status channel for each active operation | Change | Progressive disclosure and accessible, non-noisy announcements |
| Concise Studio truth/footer language | Keep public-profile, browser-local, AI-proposal, and local-media limits understandable | Existing repository truth rules supersede illustrative package wording | Informational; canonical links/actions remain elsewhere | Public; states what is sent, stored, local, illustrative, or unavailable | Only cross-mode summary of trust boundaries | Change | Retain truth without repeating large orientation panels |
| Compact auto-growing multiline fields | Keep the active input immediately usable without empty vertical space or clipped content | Pete's explicit 2026-07-28 correction; same textarea remains source of truth | Type, paste, restore, dictate, or receive an explicit draft transfer; fields grow with content | Inherits the answer/question/transcript lifecycle; geometry itself stores nothing | One shared geometry rule for editable multiline fields | Change | Start at about half the pictured height, never enlarge text merely to fill space, and grow the document naturally |

### Interview Me

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision: Keep / Change / Combine / Remove / Defer | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Answer textarea | Write the person's own answer in one editable place | Existing canonical client-side answer input | Type/paste/edit; submitted only by the explicit review action | Uses existing draft/history/request behavior; no new cloud or canonical store | Only source of truth for the current answer | Change | Keep type-first and apply compact automatic growth |
| Dictate answer | Optional speech entry into the same answer | Existing browser speech-recognition path where available; not required | Starts/stops dictation and commits text into the answer textarea | Microphone only after explicit action; no separate answer or upload | Only optional voice utility for the answer | Change | Keep visibly secondary to typing and preserve denial/unavailable recovery |
| Draft length / local-save status | Quietly explain limits and current browser draft behavior | Existing validation and browser-local behavior only | Informational; does not submit | Current browser/device; not account sync | Only lightweight draft-state feedback | Keep | Useful feedback without becoming a competing card |
| Review My Answer | Request bounded coaching on the current text | Existing review endpoint and payload | Explicitly submits the answer | Sends the existing text/question data; AI proposes and does not silently save/publish | Sole primary ready-state action | Change | One dominant action attached to the composer |
| Submission / processing workspace | Show queued, submitting, and coaching-in-progress states in place | Existing asynchronous request lifecycle | Cancel only where current behavior supports it; otherwise wait | No result is claimed until a complete response exists | Only replacement for the ready composer while its request is active | Change | Replace, rather than stack beside, the ready workspace |
| Coaching failure and retry | Explain a real failed review without losing the answer | Existing error/retry behavior | Retry or return to the preserved draft | Failure does not create history or clear the draft | Only review-failure recovery state | Change | Preserve work and place recovery where the result would appear |
| Submitted-answer reference | Let the person see exactly what was coached | Preserved original submitted text | Read-only in review; retry/improve actions are separate | Same existing request/browser history lifecycle | Only immutable reference for this coaching result | Keep | Maintains provenance between the person's words and AI feedback |
| Score and bottom-line review | Give the current returned overall coaching result | Existing real response fields only; no new rubric or employer prediction | Read; next actions remain explicit | AI feedback, not canonical truth | Only top-level review summary | Change | Make the result scannable without inventing analysis |
| What worked | Identify returned strengths | Existing coaching response only | Read | AI proposal/feedback | Only strengths section | Keep | Required feedback category |
| Improve next | Identify returned improvement guidance | Existing coaching response only | Read or proceed to Improve Answer | AI proposal/feedback | Only improvement-priority section | Keep | Required feedback category and bridge to revision |
| STAR completeness and coaching dimensions | Show the returned structured assessment | Existing response fields and current rubric only | Read | AI feedback; no new scoring source | Only structured diagnostic detail | Change | Keep subordinate to the bottom-line result |
| Relevant history you may have missed | Present only current permitted relevant-history guidance | Existing approved public-history behavior; retired "Proof" wording is prohibited | Read and use only through an explicit existing path | Public-approved context only; no private Slate/account claim | Only relevant-history prompt in review | Change | Use repository-approved truthful wording |
| Improve Answer | Request or open the existing proposed revision workflow | Existing improve endpoint/behavior | Explicitly requests an editable proposal | AI proposal; never silently replaces the person's answer | Sole primary revision action from review | Change | Preserve deliberate human control |
| Original answer in Improve | Keep the person's words available for comparison | Preserved submitted answer | Read-only comparison reference | Same current browser/request lifecycle | Only original-side comparison object | Keep | Prevents AI text from erasing provenance |
| Improved draft | Let the person inspect and edit the proposed revision | Existing generated draft response | Edit in the compact auto-growing field | Proposal only until explicitly used; no automatic publication/save | Only editable AI-proposed answer | Change | Apply compact automatic growth and preserve clear proposal labeling |
| Use improved answer / return to feedback | Let the person deliberately accept the draft for further practice or reject/leave it | Existing transfer/back behavior and confirmation rules | Explicitly use the draft or return without applying | Does not publish or silently overwrite contrary to current safeguards | Only proposal-decision actions | Change | Keeps "AI proposes; person decides" visible |
| Retry out loud | Move deliberately to Video Practice with the current question | Existing mode-switch and video cleanup/permission behavior | Opens Video Practice; media permission still requires explicit action | No recording or permission is created by the switch itself | Only review-to-video continuation | Keep | Preserves the approved practice continuation |
| Continue / New Question | Advance through the current question/session behavior | Existing next/new-question logic | Advances or resets only the intended current state | Does not clear unrelated browser-local history | Only forward session action | Keep | Preserves released progression |

### Interview AI

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision: Keep / Change / Combine / Remove / Defer | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AI question textarea | Enter the exact question for the model-answer workspace | Existing question input and validation | Type/paste/edit before explicit generation | Sent only through the existing request; no automatic generation | Only source of truth for the AI question | Change | Keep type-first and compact with automatic growth |
| Dictate AI question | Optional speech entry into the same question | Existing speech-recognition support where available | Starts/stops dictation into the question textarea | Microphone only after explicit action; no separate recording/upload | Only optional AI-question voice utility | Change | Secondary to typing and failure returns to intact text |
| Answer basis selector | Choose best-practice, approved public history, or compare | Existing values and request mapping; actual radio-group semantics | Changes the basis for the next explicit request | Best-practice is illustrative; history is approved public evidence only; compare keeps both labels | Only source-basis decision | Change | Keep selection visible before and after generation |
| Selected-basis explanation and grounding truth | Explain exactly what the selected basis may use | Existing public/demo truth; no private or unpublished history | Informational | Public approved evidence only; no account-history claim | Only adjacent explanation of generation scope | Change | Prevents unlabeled source blending |
| Get Answer | Explicitly request the selected model answer | Existing generation endpoint/payload and validation | Submits current question and selected basis | Sends existing text/context only; no silent save or publication | Sole primary pre-generation action | Change | One deliberate generation trigger |
| Empty answer workspace | Explain what will appear before a request | No fabricated answer, sources, follow-up, or comparison | Informational | Stores/sends nothing | Only initial state of the shared answer workspace | Change | Empty, loading, failure, and result replace one another in one geometry |
| Generating state | Show real in-progress model generation | Existing request lifecycle | Wait; cancellation only if current behavior supports it | No answer is claimed before a complete response | Only loading state of the shared answer workspace | Change | Preserve question and basis while announcing progress once |
| Generation failure / retry | Preserve question and basis and explain a failed request | Existing error/retry behavior | Retry or edit/new question through supported actions | Failure creates no accepted answer or new store | Only generation-failure recovery state | Change | Error replaces the result rather than appearing as a remote alert |
| No-grounding state | State that approved public evidence could not support the requested answer | Existing no-grounding behavior; gaps must not be invented | Adjust question, choose best practice, retry, or new question as supported | No private history lookup or fabricated experience | Only evidence-insufficiency state | Change | Honest recovery instead of invented grounding |
| Generated answer and textual source label | Present the real returned example with its basis beside it | Existing response fields only; best-practice remains illustrative | Read; explicit downstream actions are separate | AI proposal; not the person's experience unless approved public evidence actually supports it | Only primary generated-answer object | Change | Answer first, visibly basis-labeled |
| Why this answer works / structural lessons | Explain returned reasoning and useful structure | Existing real response fields only | Read | AI explanation, not deterministic truth | Only reasoning section | Change | Keep below the answer and avoid generic chat architecture |
| Approved public-history evidence | Show the real approved sources/history used | Existing approved public evidence returned or already available | Read/open existing disclosure | Public-approved sources only; no private Slate/account access | Only grounding-evidence section | Change | Evidence stays discoverable and text-labeled on all viewports |
| Compare presentation | Distinguish best-practice and public-history approaches | Existing compare response only | Read/inspect labeled differences | Each basis retains its truth label; no employer-outcome prediction | Only compare-specific structure | Change | Avoid unlabeled blending or three equal dense columns |
| Follow-up question and Ask action | Ask one explicit follow-up after a first answer | Existing follow-up unlock, request, and grounding behavior | Type and explicitly submit | Uses the same current evidence basis; failure preserves first answer and question | Only bounded follow-up workflow; not generic chat | Change | Keep attached to the answer workspace and hidden until relevant |
| Practice This Answer | Deliberately transfer useful text to Interview Me | Existing safe transfer and nonempty-draft confirmation | Opens Interview Me with explicit transfer | Proposal remains editable; no silent acceptance, storage, or publication | Sole primary forward action after a useful result | Change | Preserves human decision and destination safeguards |
| New Question | Reset only the current AI question/result workflow | Existing reset behavior | Clears intended AI state and restores logical focus | Does not clear session configuration or unrelated browser history | Only AI-workspace reset | Keep | Preserves released behavior |

### Video Practice

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision: Keep / Change / Combine / Remove / Defer | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Camera-off stage and local-only truth | Explain that devices are off and nothing is uploaded | Existing browser-local media contract | Read; enable is separate and explicit | No permission, stream, recording, upload, or retention on route load | Only initial media state | Change | Make local rehearsal premium without implying a remote interviewer |
| Enable Camera | Start the browser permission/preview flow deliberately | Existing `getUserMedia` behavior | Requests camera/microphone access | Permission only after this action; media remains on device | Sole primary camera-off action | Change | No automatic permission request |
| Permission-requesting status | Explain the active browser permission request | Real request state only | Wait or follow current recovery behavior | No server processing or upload | Only requesting state in the camera stage | Change | Stable, accessible in-place status |
| Permission-denied / device-unavailable recovery | Explain real denial, unsupported API, busy/missing device, or generic failure to the supported level | Existing browser error distinctions and retry/settings behavior | Retry, open settings guidance, or use transcript typing | Transcript remains usable; no repeated automatic prompt | Only media failure/recovery state | Change | Preserve a complete non-camera path |
| Live preview and local-only badge | Let the person frame and rehearse before recording | Existing local `MediaStream` | View preview; start is separate | Live local stream; not uploaded, analyzed, or retained | Only camera-preview object | Change | Keep the camera stage visually dominant and truth-labeled |
| Start Answer | Begin the existing local recording | Existing `MediaRecorder` path when supported | Starts one take | Local transient recording only | Sole primary preview-ready action | Change | Prevent double start and keep secondary controls quiet |
| Recording status and elapsed timer | Confirm that recording is active without noisy announcements | Existing recorder/timer state | Informational; stop is separate | Local media only; no server analysis | Only active-recording status | Change | Clear text/status, not color alone or per-second announcements |
| Stop Recording | Finish the current local take | Existing recorder stop/finalize behavior | Stops/finalizes locally | No implied server processing | Sole primary recording action | Change | Keeps recording controls unambiguous |
| Playback | Review the just-recorded local take | Existing blob/object URL and native playback | Play/pause through existing controls | Local and transient; may disappear on discard/exit | Only media review object | Change | Reuse the dominant camera stage |
| Record another take / Retake | Replace the current take through existing cleanup | Existing reset/cleanup behavior | Explicitly retakes | Does not retain multiple takes unless already supported | Only retake action | Change | Preserve question/session context and release old media |
| Discard | Remove the current local take deliberately | Existing destructive cleanup/confirmation | Explicitly discards | Revokes current local blob/object URL; does not delete unrelated history/transcript | Only destructive media action | Change | Keep subordinate and explicit |
| Device status and settings | Understand current camera/microphone state and reach supported settings help | Existing device state only | Opens current settings/disclosure | Device metadata only; no new persistence | Only device-control context | Change | Move to the supporting rail/sheet rather than compete with preview |
| Transcript textarea and truth label | Type or paste what was said for content coaching | Existing text-coaching input; automatic transcription is not claimed | Type/paste/edit independently of camera | Text only follows existing draft/request lifecycle; recording is not attached | Only source of truth for transcript coaching | Change | Keep camera and text as separate sources and apply compact automatic growth |
| Dictate transcript | Optionally enter transcript text through existing speech recognition | Existing optional dictation support | Starts/stops dictation into the transcript textarea | Microphone only after explicit action; no media analysis/upload | Only optional transcript voice utility | Change | Typing/paste remains primary |
| Submit Transcript | Request the existing content-coaching flow on transcript text | Existing coaching endpoint/payload | Explicitly submits text | Sends expected question/text only, not recording bytes | Sole primary transcript-coaching action | Change | Honest content coaching, not video delivery analysis |
| Transcript coaching result / failure | Present the existing text feedback or recover without losing transcript | Existing review/improve response and error behavior | Read, retry, or use existing review actions | AI text feedback only; no pace, eye-contact, filler, confidence, or vocal-clarity inference | Only transcript-feedback state | Change | Reuse the truthful coaching hierarchy |
| New Question | Move to the next/currently supported question behavior | Existing question progression | Explicitly changes question | Cleans media according to existing lifecycle; unrelated history remains | Only video question-reset action | Keep | Preserves released behavior |
| Route-exit media cleanup | Ensure devices and transient media do not continue after leaving | Existing track, recorder, timer, listener, and object-URL lifecycle | Automatic safe cleanup when mode/route exits, with confirmation where current behavior requires it | Stops local device use; stores/uploads nothing new | Only media lifecycle safeguard | Keep | Required privacy and recovery behavior even when not a persistent visible card |

### Browser-local History

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision: Keep / Change / Combine / Remove / Defer | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Browser-local History title and truth | Explain what these records are and where they live | Existing local-storage records on this browser/device | Informational | Not an account archive, cloud sync, private Slate, or retained video library | Only History audience/lifecycle statement | Change | Make local truth unmistakable |
| Empty History state | Explain that no browser-local attempts are available and offer a useful next step | Real absence of current records | Start/resume practice through existing mode actions | Creates nothing until the person practices under existing behavior | Only no-record state | Change | No empty analytics or fabricated activity |
| Attempt list and current filters | Find existing browser-local attempts | Existing stored attempt metadata only | Select/filter through current controls | Current browser/device; recording bytes are not implied | Only collection view | Change | Keep scan-friendly and secondary to truthful practice return |
| Attempt detail | Review one existing local record | Existing stored question/answer/feedback metadata only | Read; resume/manage actions are separate | Current browser/device; no private account retrieval | Only selected-attempt projection | Change | Natural-height content, not a second canonical store |
| Resume practice | Continue from an existing local attempt through current behavior | Existing deep-link/state behavior | Opens the appropriate practice mode/question | Uses current browser state only | Only History-to-practice continuation | Keep | Provides a meaningful next action |
| Goals | View or manage current browser-local practice goals where already supported | Existing local goal records only | Uses existing add/update/remove behavior | Current browser/device; not account goals | Only goal summary within History | Change | Keep truthful and subordinate to attempts |
| Delete / clear confirmation | Remove only the selected current-browser record through existing safeguards | Existing destructive local-storage behavior | Explicitly confirms deletion | Local record only; no server or unrelated history deletion | Only destructive History action | Keep | Preserve explicit human control |
| Storage-unavailable / corrupted-record recovery | Explain when browser storage cannot be read or used | Real storage failure only | Retry, continue without History, or use supported cleanup | No claim that a server copy exists | Only History failure/recovery state | Change | Honest degradation without blocking practice |
| Recording-retention reminder | Prevent a History item from implying saved video | Existing media lifecycle: video bytes/object URLs are transient unless repository behavior proves otherwise | Informational | No retained recording or cross-device playback claim | Only bridge between local attempt metadata and media truth | Keep | Prevents a false cloud/local-video archive promise |

## C. Combined, removed, and deferred items

| Item | Decision | Replacement / destination / reason | Revisit trigger |
| --- | --- | --- | --- |
| Every retained item marked `Change` in section B, except where a more specific disposition appears below | Change | Keep the same named released capability and truth boundary, but present it in the approved task-first Focus hierarchy, replacement-state geometry, white/navy/cobalt/teal visual language, responsive order, accessible semantics, and compact/natural-height content behavior stated in that item's section-B row | A later change would alter the item's product purpose, action, source, privacy/lifecycle boundary, dominant hierarchy, or approved visual direction |
| Large marketing/orientation panels inside the active workspace | Combine | Preserve their necessary route identity and truth in the concise Studio identity/truth regions; remove equal visual weight from the task viewport | A later owner-approved public Studio information-architecture package |
| Separate large question presentations repeated across the same state | Combine | One canonical current-question banner/heading per active state | A new state requires meaning that the current question presentation cannot carry |
| Empty, loading, failure, and populated regions shown simultaneously | Combine | One shared replacement workspace per workflow: composer/processing/review, AI answer workspace, camera stage, or History state | A proven concurrent task requires simultaneous visibility and receives owner approval |
| Pictured oversized empty answer, transcript, and improved-draft boxes | Change | Compact initial editable fields at approximately half pictured height, automatically growing for real content; read-only regions use natural height | Pete materially revises the 2026-07-28 correction |
| Beige, ivory, cream, and gold light-theme fallback | Remove | V3 white/cool-gray/navy/cobalt/teal visual system; V2 White only as non-conflicting supplement | New ChatGPT-created, Pete-locked material visual authority |
| "Proof you may have missed" and "Evidence-backed coaching" wording | Change | Repository-approved "Relevant history you may have missed" and current truthful labels | Shared truth/copy authority changes |
| Generic chat bubbles or unconstrained Interview AI conversation | Remove | Structured question, basis, answer, evidence, bounded follow-up, and explicit transfer workspace | Separate approved AI product/architecture package |
| Empty Video analytics scorecards | Remove | Real device/recording state, local playback, and separate transcript-content coaching only | A released measurement service with privacy, safety, evaluation, and visual authority |
| Automatic transcription from recorded video | Defer | Type, paste, or optionally dictate into the separate transcript textarea | A separately approved transcription/media package proves upload, consent, retention, failure, and truth behavior |
| Pace, pause, filler-word, eye-contact, confidence, clarity, emotion, personality, or employer-outcome analysis | Defer | No substitute metric; label transcript feedback as content coaching only | A separately approved measurement and AI-safety package with real validated inputs and evidence |
| Media upload, cloud retention, or multiple-take library | Defer | Current local transient preview/record/playback/retake/discard lifecycle | A separate media-storage, authorization, retention, deletion, and owner-accepted visual package |
| Account-backed or cross-device Interview History | Defer | Existing browser-local History with storage-unavailable behavior | Authenticated Studio/history package with server authorization, data lifecycle, migration, and visual authority |
| Private Slate/account-history grounding in this public Studio | Defer | Best-practice and approved public-history bases only | A separately approved authenticated Interview Studio transition package |
| New permanent site navigation layer | Remove | Existing PeerSlate global navigation plus one Studio-local mode selector | Approved route/navigation authority |

## D. Lock check

- [x] Every meaningful visible page item, card, control, and status in the
      approved V3/V2 authority and written all-state contracts has a distinct
      row.
- [x] Repeated decoration is grouped only because it carries no separate
      member purpose, claim, action, destination, privacy/audience/lifecycle
      meaning, or product relationship.
- [x] Each retained item has a distinct relationship; related states replace
      one another within their named workspace rather than silently claiming
      the same job.
- [x] Each action and destination is limited to released behavior, including
      disabled, unavailable, local-only, illustrative, and failure states.
- [x] Public, browser-local, local-media, request, AI-proposal, and canonical
      truth boundaries are stated separately.
- [x] Pete approved the complete supplied V3/V2 all-modes package on
      2026-07-28 and supplied the binding composer-height correction before
      release implementation.
- [x] The locked visual introduces no meaningful item outside the approved
      package and the inventory above.
