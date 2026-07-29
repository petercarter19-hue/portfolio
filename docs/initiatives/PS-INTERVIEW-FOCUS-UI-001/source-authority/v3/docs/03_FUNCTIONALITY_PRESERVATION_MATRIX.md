# 03 — Functionality Preservation Matrix

| Capability | Required treatment | Prohibited drift |
|---|---|---|
| Interview Me textarea | Preserve current source of truth, validation, character count, autosave, and submit behavior; make it visually primary | Voice-only workflow, separate transcript source, changed limits |
| Interview Me dictation | Optional secondary utility; insert into same textarea; preserve permission/error lifecycle | Permission on page load, audio upload, separate answer state |
| Coaching submit | Preserve explicit-submit trigger, endpoint, payload, and response handling | Auto-submit, endpoint/prompt/rubric changes |
| Coaching review/improve | Preserve real response fields, score semantics, handlers, and original-answer safety | Invented fields, new scoring semantics, silent overwrite |
| Retry/next/new question | Preserve behavior and queue semantics | Lost draft, changed routing |
| Autosave/history | Preserve browser-local keys and migration semantics | Renamed keys, cloud/account claims |
| Interview AI answer basis | Preserve best-practice, approved-public-history, and compare options with their existing semantics | Merging bases, changing default without evidence, private data use |
| Interview AI question entry | Preserve custom-question behavior, validation, optional dictation, and explicit Get Answer trigger | Generic chat replacement, auto-generation on typing |
| Interview AI output | Preserve answer, why-it-works/reasoning, relevant approved history/sources, comparison content, and source labels | Unlabeled synthesis, fabricated evidence, hidden provenance |
| Interview AI follow-up | Preserve unlock condition, grounding continuity, request contract, and error behavior | Follow-up before first answer if not currently supported, ungrounded chat |
| Practice This Answer | Preserve existing transfer destination, payload/state, and confirmation behavior | Silent overwrite, new persistence/publication behavior |
| Video camera/mic | Preserve explicit permission request, device selection, error states, and cleanup lifecycle | Permission on route load, forced devices, hidden errors |
| Video recording | Preserve local start/stop/playback/retake/discard behavior and timer | Media upload, automatic server processing, retained-cloud claim |
| Video transcript coaching | Preserve typed/pasted/optional-dictation text path and existing coaching request behavior | Claiming automatic transcription, tying coaching to media upload |
| Video result truth | Preserve honest local playback/duration status and current history semantics | Pace, eye-contact, filler-word, confidence, or delivery analytics unless real |
| History | Preserve browser-local records, goals, filters, detail, deletion, and storage-unavailable behavior | Account/cloud/cross-device implication, retained video claim |
| Theme | Preserve current theme persistence and state retention | Separate light/dark implementations |
| Auth/public demo | Preserve released public/private identity boundaries | Sign-in requirement, private-Slate claims |

Codex must create a repository-grounded version of this matrix with actual files, functions, routes, storage keys, media objects, requests, and tests before editing.
