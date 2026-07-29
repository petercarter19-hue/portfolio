# 01 — Owner Intent and Scope

## Owner intent

Interview Studio already has a strong product loop. The redesign must reveal that strength instead of burying it under simultaneous panels.

The owner-approved product loop is:

> **Question → Answer → Coaching → Improve → Retry or Continue**

The update succeeds when the interface feels calm, obvious, and premium without becoming simplistic or removing depth.

## Controlling input decision — typing first

The normal Interview Me experience is **typing-first**. The large editable textarea is present immediately, receives the strongest input affordance, and remains the canonical answer value. Dictation is an optional secondary utility labeled `Use dictation`; it never becomes a separate workflow, never replaces typed text, and never requests microphone permission until the user activates it. A microphone denial or unsupported browser must leave typing, autosave, word count, keyboard submission, and coaching submission fully usable.

## Core design principle

> **Do not remove capability. Give each capability the right moment.**

Simplicity means the user can understand and follow the flow without hunting, not that advanced capabilities disappear.

## Primary goals

### UX-001 — Active-task dominance

The question and answer task must dominate the active Interview Me viewport. Marketing/orientation content, empty review panels, advanced settings, queue details, and long privacy explanations may not compete with the active answer.

### UX-002 — Integrated answer stage

The following must be visually and semantically connected:

- question;
- progress;
- metadata and recommended answer framework;
- interviewer intent;
- editable answer;
- dictation state;
- browser-local save state;
- word count;
- primary coaching action;
- concise submission/privacy truth.

### UX-003 — Progressive disclosure

Only the current state is visually active:

- before submission: question and answer tools;
- during coaching: preserved submitted answer and processing;
- after coaching: review and next action;
- while improving: original, improved draft, change summary, and application actions;
- on failure: preserved answer and recovery actions.

### UX-004 — One dominant action

Each state has exactly one visually dominant action. Secondary actions remain available but do not compete.

### UX-005 — Question continuity

The user must not lose the active question while typing, dictating, reviewing, or improving. On long content, use a compact sticky question summary rather than forcing the user to scroll back to the top.

### UX-006 — Type-first composer with reachable dictation and submit

Typing is the default and primary input. Optional dictation and coaching submission must remain adjacent to the editable answer on desktop and reachable in a mobile action dock on small screens.

### UX-007 — Existing-site continuity

Reuse the real PeerSlate header, secondary navigation, typography, tokens, theme mechanism, icons, and button system wherever they already exist. The Studio should feel like the same site, not a separate app pasted into it.

## Scope by product area

### Interview Me — full implementation scope

Implement the complete focus-stage treatment for:

- ready/empty answer;
- typed draft;
- dictation/listening;
- queue open;
- coaching processing;
- coaching review;
- improve answer;
- retry/next question;
- coaching failure/recovery;
- settings and optional example access;
- desktop, tablet, mobile, light, and dark.

### Interview AI — shared-shell consistency scope

Preserve all current modes and behavior. Apply the quieter shell, mode navigation, session context, truth boundary, hierarchy, and responsive treatment. Do not redesign AI generation logic or source attribution.

### Video Practice — shared-shell consistency scope

Preserve camera, microphone, local recording, playback, discard, transcript coaching, and honest unavailable-analytics behavior. Apply the same question/session context and visual system. Do not add upload or delivery analysis.

### History — shared-shell consistency scope

Preserve browser-local records, goals, filters, detail, deletion, and storage warnings. Treat History as a separate destination rather than a fourth equal practice mode. Do not imply cloud or account history.

## Explicitly out of scope

- changing the product names Interview Me, Interview AI, Video Practice, or History;
- altering the number or content of questions;
- changing question generation logic;
- changing session setup semantics;
- changing autosave or history semantics;
- changing server request payloads or responses;
- changing coaching language, rubric, scores, STAR calculation, or improvement generation;
- creating a protected/authenticated Studio;
- adding an account-based save action;
- merging Interview Studio into Ask Slate or Ask Pete;
- adding coach avatars, chat bubbles, gamification, streak systems, or new analytics;
- redesigning unrelated PeerSlate pages;
- converging the homepage Interview walkthrough in this package.

## Copy direction

Copy refinements are allowed only when they clarify existing behavior.

Preferred control labels in the approved vision:

- `Use dictation` as the optional secondary input label; typing remains the default;
- `Review My Answer` for the existing submit-for-coaching action;
- `Listening…`, `Stop`, `Saved in this browser`, and current word count inside the composer action area;
- `Up next · 4` as a concise disclosure;
- `Your submitted answer` and `preserved` during processing;
- `Practice signal — not an employer prediction` near any score;
- `Use This Draft` only if it maps exactly to the existing apply/use behavior.

If a preferred label would misstate the actual current action, keep the truthful current label and preserve the mockup's placement and hierarchy.
