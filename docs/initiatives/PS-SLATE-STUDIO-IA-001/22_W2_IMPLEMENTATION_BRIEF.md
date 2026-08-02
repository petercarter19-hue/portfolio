# W2 — Work on Something implementation brief

**Owner decisions 2026-08-02 folded in:** site is delisted (reachable, not
discoverable); audience is a few invited friends; sign-in comes later and will
"close it off." Real AI for anonymous visitors, hard-capped. Database additions
welcome where needed. A "Start fresh" reset control for the demo session.

## Visual authority
`visual-authority/workshop-facelift-2026-08-02/` R01–R10 + R17 (owner-accepted).
Facelift shadow/texture/action language supersedes prior dials (doc 20 §6f).

## Anonymous vs member session model
- **Member (later):** DB-backed sessions per doc 17 (knowledge_item_sources in
  W2 migration PS-WORKSHOP-002: sessions table + source linkage).
- **Anonymous (now):** compact state in the signed session cookie — door,
  focused question id, answer text (cap 1000 UTF-16 units), spark id, loop
  count. AI review/improve results ride the **signed expiring token** pattern
  (architecture §4.2 / Interview Studio `_sign_interview_model_context`),
  never stored. Cookie budget guard: workshop_preview total ≤3KB measured in
  tests (library delta + session state together).
- **Reset:** `POST /app/workshop/preview/reset` clears the `workshop_preview`
  session key (same-origin + rate limit). Button "Start fresh" in the preview
  banner on every Workshop screen; confirm step; honest copy ("returns the
  demo library to its starting point and clears everything you added").

## AI endpoints (all same-origin, rate-limited, flag-gated)
- `POST /app/workshop/session/review` — answer → {interpretation, strong[≤4],
  standout, strengthen, question} — validate-then-render per
  `validate_interview_review` idiom; heal derived fields, reject missing
  deliverables; empty strong[] delivered honestly.
- `POST /app/workshop/session/improve` — labeled proposal beside member text.
- Spark: server-side on opening load for members (grounded in confirmed+
  non-archived); for anonymous, grounded in the DEMO library (Jordan's
  confirmed items) — real AI, same grounding discipline, cited chips.
- Grounding: id-addressed allow-list (≤10 items), plain-text projection only;
  `Use as context` session-scoped selection ids validated against it.
- Model: one module constant; explicit SDK timeout; max_tokens caps
  (review ≤1400, improve ≤800, spark ≤300).

## Cost controls (owner: real AI, capped)
- flask-limiter per-IP: review/improve 6/min, spark 4/min.
- Per-session caps in the cookie: ≤20 AI calls/session; over cap → honest
  "preview limit reached — start fresh or come back later" (never an error).
- Daily estimated-call log line (reason-coded) for spend visibility; alarm is
  ops follow-up, not W2 scope.

## Slices
- **W2a** opening + doors + focused-question session + honest states
  (first-run R05/R06, AI-unavailable R07/R08 wired to real provider failure),
  reset button. No AI call yet (question from a fixed curated set per door).
- **W2b** AI review + improve + loop + review-final-wording → save handoff
  into the existing W1 save path (member) / session library (anonymous).
- **W2c** Spark on the opening (member + demo grounding) + "Show another
  idea" + dismissal memory (cookie for anon, DB for members later).
- **W2d** voice input per R17 six states (reuse speech_transcription_service),
  transcript editable before it becomes the answer.
Each slice: tests, Playwright proof vs R-refs, side-by-side to Pete, deploy.

## Out of scope (unchanged)
Destinations (W4), sign-in, member DB sessions activation (needs auth),
`I brought something` intake (stays honest not-available), suggestion
generation into the library (W3).
