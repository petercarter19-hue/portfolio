# Functional V1 Architecture and Trust Contract

This is the controlling architecture contract from the completed Sol xhigh
read-only audit. It applies before and throughout runtime implementation.

## Verdict and boundary

This is a public-only Protected enhancement, not a rebuild, route transition,
or private expansion. It has no Workshop collision. The approved visual sources
are sufficient; do not make material visual invention.

The route remains `/interview-studio`. Provider/model configuration, legacy
redirects, and the public/browser-local privacy boundary remain unchanged.

## Local session contract

```text
SessionContext = {
  kind: general | role | opportunity,
  role_title,
  interview_stage,
  question_mix,
  opportunity_text_local,
  context_id
}
```

Visitor-supplied opportunity text is local, length-bounded, never dereferenced,
and treated as untrusted data. It cannot alter system or product instructions.

An active session uses an open-ended `questionTrail[]`. There is no fixed queue,
fixed total, predetermined question count, or fixed-session progress bar.

## Mode state contract

- Interview Me: `ready -> draft/record -> submit -> review -> retry/next/finish`
- Interview AI: explicit generate -> example/comparison -> recoverable unavailable
- Video Practice: off -> explicit permission -> preview -> record -> playback

All three modes retain the same current question, local context, and safe draft
state. Typed and voice input share one editable canonical transcript. Video
bytes never enter AI, network requests, browser-local persistent storage, or
History.

## Question and coaching contract

Question selection and setup are local and deterministic. They make no provider
call. Question/context leaves the browser only on an explicit nudge, example,
review, or improve action. The answer leaves only on an explicit review or
improve action.

Do not render, calculate, or persist `overallScore`, `/100`, universal STAR,
target averages, hireability, or employer prediction.

Use only these family dimension allowlists:

| Family | Dimensions |
| --- | --- |
| Professional introduction | identity, relevant proof, value, direction |
| Behavioral | situation clarity, action ownership, evidence, outcome, reflection |
| Motivation and fit | authentic rationale, specificity, role connection, forward direction |
| Situational | problem framing, judgment, tradeoffs, action plan, communication |
| Role-specific | relevance, reasoning, evidence, priorities, execution |
| Technical or case | framing, assumptions, reasoning, tradeoffs, conclusion |

Dimension status is one of: `strong`, `clear`, `developing`, or `missing`.

Review sections are:

1. What came through clearly
2. What worked
3. What to strengthen
4. A stronger approach
5. One focused follow-up

## AI and trust contract

AI requests are explicit. Preserve existing rate, content-type, cross-site,
schema, no-payload logging protections and the current provider/model.

When local opportunity text is included in an allowed request, delimit it as
untrusted reference material. It cannot supply product instructions. A malformed
or incomplete response is rejected and replaced with a recoverable unavailable
state. AI unavailable never blocks manual practice modes or local History.

No private My Knowledge, reflection, member data, Opportunity Slate integration,
schema/migration, cloud media, automatic transcription, raw media upload,
appearance/emotion/personality/confidence/honesty/employability inference, or
composite delivery score is authorized.

## Browser-local V2 history contract

History stores meaningful local session outcomes only. It shows coverage,
coaching carry-through, and one next focus without a universal score. Compare
only like question families and dimensions. If there is insufficient evidence,
say: `Not enough comparable practice yet.`

Migrate V1 browser-local state safely: preserve drafts and history. Legacy
scored reviews are visibly labeled as legacy and excluded from Functional V1
trends.

## Stop conditions

Stop and return to Root if a required behavior would exceed the six authorized
surfaces, conflict with a locked visual artifact, overlap an active lane, alter
the public/privacy boundary, change provider/model behavior, require private
data, schema, media storage/upload, or fail the package preflight.
