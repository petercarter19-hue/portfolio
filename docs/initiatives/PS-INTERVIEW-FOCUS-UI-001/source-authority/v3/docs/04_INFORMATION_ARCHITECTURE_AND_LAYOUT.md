# 04 — Information Architecture and Layout Contract

## Shared desktop active-mode shell

1. Real PeerSlate global header.
2. Existing secondary navigation, if present on the released route.
3. Compact Interview Studio title/context area.
4. Compact mode selector for Interview Me, Interview AI, and Video Practice.
5. History visually adjacent but separate as a destination, not a fourth practice method.
6. Compact session-summary strip with Edit Session.
7. Mode-specific workspace: flexible task stage plus quiet contextual rail.

At 1440×900, the main task should receive approximately 72–78% of the available workspace width. The rail receives the remainder and may collapse into a drawer/sheet at narrower widths.

## Interview Me

Question, metadata, intent, textarea, optional Dictate, save/word state, and Review My Answer form one integrated stage. Processing, review, improvement, and failure replace the active stage content rather than stacking permanently beneath it.

## Interview AI

Screen 06 controls the desktop geometry:

- Main stage: question composer, generation/result workspace, reasoning/source evidence, and result actions.
- Context rail: answer-basis selection and concise source boundary.
- The question composer remains visible at the top of the mode.
- Generated content occupies the dominant area; provenance remains attached to the content it explains.
- Follow-up appears only after a first answer exists.
- On compare mode, differences must be scannable without creating three unrelated full-page columns.

## Video Practice

Screen 07 controls the desktop geometry:

- Current question remains above the recording stage.
- Camera preview is the dominant surface in ready/recording/playback states.
- Local-only status and elapsed time are attached to the preview.
- The rail shows device status, recording truth, and the next relevant action—not generic instructions.
- Transcript coaching remains secondary and is revealed before or after recording without competing with the camera during active recording.

## Context rail by mode

- Interview Me ready: session summary, Up Next, optional example, concise privacy truth.
- Interview Me review/improve: priority improvement, compact scoring/status, grounding/nonpublication truth.
- Interview AI: answer basis, selected source boundary, compact profile grounding, generation status/error recovery.
- Video Practice: devices, permission state, local recording status, after-stop choices.
- History: filters or goal context only when they support the list/detail task.

## Progressive disclosure

Do not keep empty review, answer, comparison, follow-up, transcript, playback, analytics, processing, or failure panels mounted as visible placeholders before they are active. Hidden inactive states must also be removed from normal accessibility traversal.
