# 02 — Authority and Conflict Rules

## Authority hierarchy

### A. Functional authority

The current released application, route handlers, request contracts, storage behavior, media behavior, and passing tests are authoritative for what the product does.

The live public experience currently includes real links for Interview Me, Interview AI, Video Practice, and History; browser-local drafts/history; dictation; coaching submission; failure recovery; review; improve; local camera rehearsal; and explicit public-demo truth. Preserve those capabilities.

### B. Visual authority

The 14 numbered PNGs in `visual-authority/` are the controlling direction for this update.

They control:

- hierarchy;
- relative geometry;
- component placement;
- visual density;
- active/secondary emphasis;
- crisp white, navy, cobalt, and teal light treatment;
- cinematic dark parity;
- desktop/mobile relationships;
- state-to-state continuity.

### C. Existing theme authority

The repository's accepted Interview Studio structural language—editorial light and cinematic dark—remains relevant for typography, depth, and atmosphere. **The v2.0 white/cobalt palette in this package supersedes the earlier warm beige/gold light-theme colors.** Do not use the old light palette merely because it exists in prior tokens or screenshots.

### D. Prototype authority

The HTML prototypes are a measurement aid. They may be opened locally to inspect CSS values and box relationships. They are not semantic, runtime, data, or accessibility authority.

## Conflict resolution examples

### Mockup action label differs from code

Preserve the real action and endpoint. Use the mockup location and prominence. Change the label only if the new copy remains completely truthful.

### Mockup displays illustrative Pete content

Use the existing public-demo profile and real approved public fixtures already in the repository. Do not hardcode new Pete-specific data into reusable logic.

### Prototype uses a static score or response

Use deterministic test fixtures for screenshot capture only. Production must continue to render the real response contract.

### Prototype shows a fixed height

Match the composition responsively. Do not introduce viewport-specific hardcoded heights that clip at 1366×768, 200% zoom, mobile landscape, or long content.

### Mockup omits a current capability

Do not delete the capability. Place it in the appropriate drawer, rail section, disclosure, or later state unless the owner explicitly removed it.

### Current DOM renders all future states at once

Refactor presentation so inactive sections are not visible or exposed to assistive technology. Reuse the existing state machine rather than creating duplicate state.

### Current route and history deep link differ from assumptions in this package

Keep actual route and deep-link behavior. Update documentation to the discovered truth.

## Reference index — exactly 14 authoritative product screens

The folder `visual-authority/` contains exactly fourteen PNG files. There is no fifteenth product screen. Failure recovery is fully specified in the written state contract and must use the same architecture.

| ID | File | Controlling purpose |
|---|---|---|
| 01 | `01_interview_me_ready_light.png` | Primary desktop structural authority; type-first ready state and first-viewport target |
| 02 | `02_interview_me_answering_queue_light.png` | Optional dictation integrated with the same editable answer; desktop queue drawer |
| 03 | `03_interview_me_processing_light.png` | Preserved answer and in-place coaching progress |
| 04 | `04_interview_me_coach_review_light.png` | Bottom-line-first review hierarchy and next actions |
| 05 | `05_interview_me_improve_light.png` | Original/improved comparison and approval boundary |
| 06 | `06_interview_ai_light.png` | Shared shell and source-mode hierarchy |
| 07 | `07_video_practice_light.png` | Honest local recording stage and device/status rail |
| 08 | `08_history_light.png` | Browser-local history as a separate destination |
| 09 | `09_interview_me_ready_dark.png` | Dark relighting of the same ready geometry |
| 10 | `10_interview_me_coach_review_dark.png` | Dark review parity |
| 11 | `11_mobile_interview_me_ready.png` | Mobile type-first ready hierarchy and bottom action dock |
| 12 | `12_mobile_interview_me_listening.png` | Mobile optional dictation state; same editable answer remains canonical |
| 13 | `13_mobile_coach_review.png` | Mobile review stacking and dominant action |
| 14 | `14_mobile_improve_answer.png` | Mobile improve state |

## Visual-reference rules for Codex

- Open each PNG at 100% before coding the corresponding state.
- Use the current site shell from the repository, not a traced screenshot recreation.
- Compare screenshots at the exact target viewport before declaring a state complete.
- Match structural relationships before polishing tiny decoration.
- Do not use the prototype HTML as a shortcut around repository discovery.
