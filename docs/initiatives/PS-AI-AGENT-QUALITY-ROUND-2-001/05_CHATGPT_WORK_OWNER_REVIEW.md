# ChatGPT Work owner review - Interview Studio AI

**When:** after the repository dossier, golden cases, and scorecard pass review
**Surface:** Interview Studio only
**Purpose:** combine Pete's live product judgment with the source-backed Codex
baseline
**Runtime effect:** none

## Why ChatGPT Work adds value here

Codex is strongest at tracing the repository, authorization, prompts,
validators, tests, history, and release truth. ChatGPT Work adds material value
when Pete needs to stay in the actual signed-in page and judge the experience in
context:

- walk the same flow at desktop, tablet, and mobile sizes;
- hear Pete react to wording, pacing, usefulness, and visual hierarchy while
  the result is still on screen;
- compare a strong, weak, contradictory, and insufficient case without losing
  the page context;
- exercise voice/dictation with Pete controlling the microphone permission;
- inspect whether the strong example, source label, “Why this works,” and
  improvement path appear where a member expects them;
- record owner decisions immediately against the prepared dossier and
  scorecard.

ChatGPT Work should not independently redesign prompts, choose a model, or
declare a release. Codex remains responsible for turning accepted findings into
source-controlled packages, tests, PRs, and release evidence.

## Account and privacy boundary

- Prefer the dedicated PeerSlate QA member once the Interview audit/handoff is
  complete.
- Until that account exists, Pete may use his own signed-in session, but only
  synthetic questions and answers should be submitted during the walkthrough.
- Never share a password, MFA code, token, cookie, or session artifact with an
  agent.
- Pete handles microphone/camera permission prompts and any login challenge.
- Do not paste real confidential, personnel, customer, medical, financial, or
  export-controlled information into an evaluation.
- Delete only test records created during the walkthrough, and only after Pete
  confirms which records are synthetic.

## Prepared materials

ChatGPT Work should have these repository files available:

1. `02_INTERVIEW_STUDIO_AI_DOSSIER.md`
2. `03_INTERVIEW_STUDIO_GOLDEN_CASES.md`
3. `04_INTERVIEW_STUDIO_SCORECARD.md`

The comprehensive site-review ZIP is context, not authority over current
production behavior. Current live behavior and the current package control the
walkthrough.

## Walkthrough sequence

### 1. Establish current truth

Open signed-in `/interview-studio` and confirm:

- account identity is the intended QA member or Pete;
- Interview Me, Interview AI, Video Practice, and History are reachable;
- the page describes browser-local storage accurately;
- no unrelated private page or record is opened.

### 2. Responsive composition check

Use at least:

- desktop: 1440 x 900;
- tablet portrait: 820 x 1180;
- mobile: 390 x 844;
- small mobile: 360 x 800.

For each size, inspect the ready composer, active dictation state, coach review,
improvement draft, Interview AI answer, and History. Record:

- overflow, clipping, overlap, unexpected wrapping, or unreachable controls;
- whether the current task remains primary;
- placement of History/recent answer information;
- whether mic, live dictation, and send read as one integrated text composer;
- focus movement, visible status, and error recovery.

The accepted target for the composer is ChatGPT-like integration: editable
text, interim dictation, microphone, and send belong to one visible input
surface. The logo remains unchanged.

### 3. Interview AI model-answer check

Run one question in each source mode:

- member/public-profile grounded;
- generic best practice;
- compare.

Verify source labels before judging quality. Check that grounded claims can be
traced to authorized evidence, generic content is unmistakably illustrative,
and “Why this works” explains concrete features rather than offering generic
praise.

### 4. Interview Me quality spine

Run Wave 1 cases from the golden library, beginning with:

- INT-001 short/direct;
- INT-003 strong behavioral;
- INT-008 ambiguous;
- INT-010 weak/vague;
- INT-013 contradictory;
- INT-015 injection in opportunity context;
- INT-016 insufficient evidence.

For each successful review, inspect review, improvement, and strong-example
paths separately. Do not assume that a good review implies a good rewrite.

### 5. Voice and dictation

Pete activates the microphone permission. At mobile and desktop sizes, verify:

- clear listening state;
- visible interim transcript inside the composer;
- stop-on-second-click and ten-second silence behavior;
- final/interim text lands in the same editable field;
- sending uses the visible final text only;
- audio is not uploaded or retained by PeerSlate;
- denial/unsupported-browser messages remain usable.

### 6. Failure behavior

Use fixture or non-production failure controls where available. Do not attempt
to damage or manipulate the live provider. Confirm that an unavailable or
malformed response preserves the member's draft and exposes a useful retry.

### 7. Owner decision review

Walk Pete through the eight decisions in the dossier. Record each as:

- accepted;
- accepted with wording change;
- rejected;
- needs another example;
- deferred to a separate package.

Do not convert discussion into production code during this session.

## Paste-ready ChatGPT Work instruction

```text
We are reviewing one PeerSlate AI surface only: signed-in Interview Studio.
Use the current live page and the three attached package files:
02_INTERVIEW_STUDIO_AI_DOSSIER.md,
03_INTERVIEW_STUDIO_GOLDEN_CASES.md, and
04_INTERVIEW_STUDIO_SCORECARD.md.

Do not redesign or implement anything. Do not select a provider or model. Do
not open unrelated private records. Use only synthetic questions and answers.
I will handle login and microphone/camera permission prompts.

Walk me through the live surface at 1440x900, 820x1180, 390x844, and 360x800.
Test Interview Me, Interview AI source modes, the same-page strong example and
Why this works, improvement, History, mobile composer placement, and live
dictation. Then run the Wave 1 golden cases one at a time and help me score each
result using the attached scorecard.

For every finding, distinguish:
1. live-confirmed behavior,
2. source/package expectation,
3. my owner judgment,
4. a proposed follow-up package.

Finish with a concise decision log. Production changes remain blocked until
Codex turns accepted findings into bounded source-controlled implementation
packages.
```

## Handoff back to Codex

Return:

- viewport-by-state findings;
- exact case IDs run;
- raw outputs or screenshots containing synthetic data only;
- completed human scorecards;
- provider/model and latency/usage evidence if the product exposes it;
- Pete's decision log;
- synthetic records created and whether Pete approved their deletion;
- unresolved questions and recommended implementation package boundaries.

Codex then verifies the evidence, updates this package, and creates only the
runtime packages Pete explicitly accepts.
