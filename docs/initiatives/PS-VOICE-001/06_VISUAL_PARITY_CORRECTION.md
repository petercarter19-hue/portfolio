# PS-VOICE-001 Visual Parity Correction

_Owner decisions: 2026-07-19. Current writer: Claude Code, self-managed._

## Current truth

Private Voice Capture is implemented and deployed through Azure PR 75 at
`eede8565d703a466bd788962d494e8b385b53409`; pipeline 105 passed Build and
Deploy. Pete completed the signed-in production workflow and confirmed that it
functions. Pete then withdrew visual acceptance because the protected desktop
and mobile experience does not match the approved production-intent Voice
walkthrough.

Implementation, deployment, functional validation, visual acceptance, and
closeout remain separate. This correction changes the visual/product layer; it
does not reopen the working backend.

## Assignment and branch

- Writer: Claude Code
- Delivery model: self-managed under `docs/AI_WORKFLOW.md`
- Task manager and visual authority: ChatGPT Work
- Final product acceptance: Pete and ChatGPT Work
- Branch: `work/2026-07-19-voice-visual-parity-001`
- Base: current fetched `origin/main`
- Preserve completely: `C:\Users\peter\Documents\portfolio-voice-001`

Observed planning checkpoint on 2026-07-19:
`0158daf22d26e7c38be494e2b32e6b51fdaca0fb`. It contains design instructions
only. It is not implementation, acceptance, deployment, or live evidence, and
Claude must synchronize it with the current `origin/main` before implementation.

Claude owns implementation, complete-diff review, correction, tests, evidence,
PR readiness, and, after acceptance, Azure PR/pipeline/production verification
and package closeout. Return `Pass`, `Conditional`, or `Fail`; never hide an
evidence gap or material deviation.

## Binding visual authority

The protected experience must be recognizably the same or better than:

- the homepage Voice walkthrough in
  `templates/partials/homepage/_voice_hero.html` and
  `static/css/homepage-scenes.css`;
- the repository's working design-preview states at
  `/feed-living-stream?state=voice` and
  `/feed-living-stream?state=review`;
- the Voice overlay/review composition in
  `static/js/feed-living-stream.js` and
  `static/css/feed-living-stream.css`; and
- `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`.

The public demonstration files are read-only references. Copy or adapt only the
visual language into Capture-scoped selectors and real protected state; do not
change or depend on simulated Feed behavior.

## Required desktop result

- Voice and Type remain first-class opening choices.
- Recording becomes the dominant focused stage: editorial header, backdrop,
  microphone/ring, listening state, timer/waveform, transcript/status, clear
  Cancel and Stop/review actions, and premium Deep Navy Gold finish.
- Review preserves the mockup's deliberate composition: audio, editable
  transcript, private/provenance information, future-capability rail, and one
  unmistakable live completion action.
- Browser-default controls may remain only where replacing them would reduce
  accessibility; their surrounding composition must still meet the visual
  authority.

## Required mobile result

Mobile is a primary experience, not a compressed desktop column. Use a
purpose-designed full-screen or bottom-sheet composition with:

- the same dominant recording/review hierarchy;
- readable transcript editing and audio controls;
- a persistent unobscured **Save private Capture** action;
- progressive disclosure for future options;
- no floating Ask Pete AI overlap; and
- verified portrait, landscape where applicable, touch targets, safe areas,
  long content, keyboard, screen-reader, reduced-motion, and 200% reflow.

## Truthful future-capability scaffolding

The approved mockup's future controls may be visible now to preserve the target
composition and product direction:

- Connections, Community, and selected people;
- My Story, Slate Board, and résumé;
- photo, video, and document attachments;
- AI-assisted wording; and
- publication.

Every unavailable capability must carry a visible and accessible `Coming later`
label or equivalent, remain genuinely non-operational, and be excluded from the tab/order
model as an active action. It may explain the future capability, but it may not
pretend to save, publish, share, place, upload, generate, or authorize anything.

**Save private Capture** is the only live completion action. `Keep private` is
the only active audience. Do not display fabricated AI output. Frontend flags
are presentation only and never grant backend access or publication authority.

## Writable files

- `templates/owner_capture.html` - protected Voice/Type presentation only
- `static/css/owner-app.css` - strictly Capture/Voice-scoped selectors
- `static/js/owner-capture-voice.js` - real existing Voice states only
- focused Voice UI tests
- PS-VOICE-001 evidence and completion-report updates

Do not change `owner_routes.py`, services, SQL, Azure infrastructure, identity,
Capture lifecycle procedures, public Voice/Feed demo files, public résumé,
Interview Studio, global navigation/theme, Journal, Moment, Placement, Story,
Slate Board, or publication behavior without a new explicit reservation.

## Self-managed acceptance evidence

Before requesting Pete/ChatGPT Work acceptance, Claude must:

1. inspect the complete diff against the exact base and remove unrelated work;
2. run focused Voice UI tests, governance guardrails, and the complete configured
   suite;
3. verify the real working Voice and Type paths plus permission denied,
   unsupported browser, upload/transcription failure, retry, long transcript,
   and save behavior;
4. capture clean desktop recording/review/Type and mobile recording/review
   evidence plus focus, 200% reflow, reduced motion, and failure states;
5. produce a parity/deviation matrix against the named authority;
6. confirm that every future affordance is disabled and truth-labeled and that
   **Save private Capture** remains the only live completion action; and
7. commit, push, and return the exact branch/full SHA and standard completion
   report with `Pass`, `Conditional`, or `Fail` self-certification.

Pete and ChatGPT Work then perform a focused review of the real product and the
self-certified report. After acceptance, Claude may complete its own Azure PR,
pipeline, production checks, and closeout.

## Manager decisions for the design-instructions checkpoint

The existing design-instructions checkpoint is approved to proceed under these
binding answers; no separate pre-build manager pause remains:

1. The repository walkthrough named above plus Pete's supplied desktop Voice
   screenshots are sufficient visual authority. The completion report must
   capture new durable desktop/mobile comparison evidence; implementation does
   not wait for the supplied screenshots to be copied into Git.
2. **Save private Capture** uses the approved gold emphasis in the light and
   dark protected review experience. Use the text-safe strong gold
   (`#8A5A00`) where needed for WCAG 2.2 AA contrast, with marigold treatment
   around it. This is the one approved exception for the walkthrough's dominant
   completion action; other primary product actions keep the shared navy
   semantics.
3. A `position: fixed` overlay is approved only inside the Voice-scoped dialog
   implementation, with a working no-JavaScript document-flow fallback. The
   focused test may be revised to enforce that narrower rule.
4. Approved dismissal copy: `Close keeps your private draft; resume any time
   from this page.` Closing never deletes or confirms the draft.
5. Pete's request to have Claude correct the real desktop and mobile experience,
   together with this manager decision, authorizes implementation on the
   assigned branch. Pete/ChatGPT Work acceptance still occurs against the real
   completed product before merge.
