# Authenticated evidence supplement — bounded synthetic test batch

**Package:** `PS-INTERVIEW-AI-ARCHITECTURE-001`
**Date:** 2026-08-15
**Identity:** `PeerSlate Test` — a synthetic non-owner member. **Confirmed** via the account
menu label `"Account menu for PeerSlate Test"` and the History namespace
`peerslate:interview-studio:member-8c65e0ca650231aba46e:v3`. Pete's owner account was
**not** used.
**Deployed application SHA:** `f42e5399fd579df4efb2e13ce8bc962438e3a53f` (Azure run 1096).
**Application AI requests made: exactly 5**, the authorized budget — observed as five
`POST /api/interview/*` requests each returning 200. Each **establishes one logical
provider invocation** by the 200 plus the source path it exercises; that is an inference
from application evidence, not an observed provider transport or billing event. No sixth request was made. **Bounded claim:** SDK transport
retries and the provider's billing count were not observed; "exactly five paid calls" at
the provider ledger is therefore inferred (the SDK's default retry policy re-attempts only
on failure, and all five requests succeeded first time at the application layer), not
proven.
**Data used:** synthetic only, marked `QA SCRATCH 2026-08-15`. No real member or job data.
**Credentials:** Pete signed in manually. The reviewer did not request, inspect, copy,
export, store, or separately handle credentials in any form; the browser simply used its
existing signed-in session normally (which is what a signed-in browser session does —
no absolute no-transmission claim is made about the session's own normal operation).

## How to read this

| Label | Meaning |
|---|---|
| **OBSERVED** | Seen directly in the authenticated UI or network layer today. |
| **SOURCE-CONFIRMED** | Read in source at the deployed SHA. |
| **INFERRED** | Supported but not directly executed. |
| **UNVERIFIED** | Not checked. Stated as unknown. |

## The five calls

| # | Specialist | Endpoint | Status |
|---|---|---|---|
| 1 | Answer Coach | `POST /api/interview/review` | 200 |
| 2 | Revision Partner | `POST /api/interview/improve` | 200 |
| 3 | Nudge | `POST /api/interview/nudge` | 200 |
| 4 | Generic Example | `POST /api/interview/model-answer` (`best_practice`) | 200 |
| 5 | Grounded Example | `POST /api/interview/model-answer` (`member_history`) | 200 |

Two fictional questions were used: *"Tell me about a time you improved a process that
wasn't working."* and *"Tell me about a time you set a challenging goal and achieved it."*
One synthetic answer (86 words, Northwind Testing Ltd, explicitly fictional) was reused.

## The two predictions, and how they resolved

### P1 — Grounded Example fails safely for a normal member. **CONFIRMED.**

**OBSERVED.** Mode `member_history` for `PeerSlate Test` returned HTTP 200 with:

> **NOT ENOUGH APPROVED PUBLIC EVIDENCE**
> PeerSlate could not support a profile-grounded answer to this question from the approved
> public evidence available for your account.
> **Nothing was invented or borrowed from another person.**

Recovery offered: *Use best practice*, *Change question*. Programmatic checks confirmed the
response contained **no fabricated content** and **no leakage of the owner's evidence**.

This confirms Gate A finding G2 for **this one synthetic account** as a live observation.
The universal claim — that *every* non-owner gets an empty evidence set — remains
SOURCE-CONFIRMED (`_interview_identity_evidence_context()`, `app.py:1972-1985`, has exactly
two branches) rather than live-observed across accounts. It also
**corrects the tone of Gate A**: I reported the empty-evidence path as a serious gap. The
*capability* gap is real — a non-owner cannot get a grounded answer. The *safety* of the
failure is exemplary: truthful, non-fabricating, explicitly disclaiming borrowing from
another person, and offering a working alternative. Both facts belong in the record.

**OBSERVED, additional.** The UI pre-discloses the behaviour before the member sends an
application AI request: *"If approved public evidence is unavailable, PeerSlate keeps the result insufficient
instead of inventing it."*

**SOURCE-SUPPORTED INFERENCE, and this matters for the architecture.** A logical
provider invocation still occurred even though the member has no evidence and the outcome
was predetermined — inferred from the observed 200 plus the code path, which reaches
`client.messages.create` unconditionally (`app.py:4340`) with the “No approved public
evidence” grounding block. The provider transport itself was not observed. Section 5 proposed a server-side short-circuit with zero
provider calls; Section 4 assumed a provider-returned insufficient. **Section 5's
approach is correct and this evidence settles the disagreement:** the application
traversed the provider-call code path for an outcome that was predetermined before the
call. Provider transport and billing were not observed.

### P2 — Nudge is generic and does not retrieve History. **CONFIRMED.**

**OBSERVED:** after answering the stock-count question, a new question was loaded and Nudge
requested; the returned hints referenced the new question only, and a programmatic scan of
the rendered page for `Northwind`, `stock count`, `warehouse`, `shared count sheet`, and
`double-count` found **no match**. That negative UI scan is the observation.
**SOURCE-CONFIRMED:** the *absence of History retrieval itself* — the nudge endpoint has no
History parameter and its prompt forbids history use (`app.py:4138-4140`, `:4162`) — is
established by source, not by the scan; a UI scan alone could not prove non-retrieval.

Specialist 4 (Private History Nudge) does not exist: source-confirmed, consistent with the
observation. Gate A section 2 stands.

## Findings not predicted

### F1 — The universal length instruction exists; adherence is UNVERIFIED.

The improve prompt demands a `"60-120 second spoken answer"` (`app.py:4067`, present in
deployed SHA `f42e5399` — SOURCE-CONFIRMED). The returned draft was **111 words** — that
word count is the only thing OBSERVED here. Delivery time was not measured, and whether
the draft violates the instructed band therefore remains UNVERIFIED: a spoken duration
depends on delivery, and no timing was taken.

**Correct statement of G3:** an inappropriate universal length instruction exists in the
deployed source (SOURCE-CONFIRMED); one 111-word output was returned under it (OBSERVED);
delivery time and adherence remain UNVERIFIED. The defect is the presence of a universal
rule where the accepted direction requires obligation-driven length — not any proven
failure to follow it. The architecture should not claim removing the literal will visibly
change most answers; it removes a wrong instruction and replaces it with a reasoned band,
and measures adherence in evaluation.

### F2 — Answer versions are not preserved. **OBSERVED. This closes Gate A's answer-version UNVERIFIED item.**

The stored History record is **flat**. Its fields are exactly:

`id, createdAt, mode, question, family, competency, reviewVersion, dimensions, answer,
verdict, encouragement, whatCameThroughClearly, strengths, improvements, strongerApproach,
focusedFollowUp, context, contextIdentity, sessionContextId, sessionId, experience,
attemptNumber, durationSeconds, status`

There is **no version array and no parent lineage**. The improved draft was **not persisted
at all** — the record detail view showed the original answer and no proposal.

So today: one record holds one answer. The revision proposal lives only in the DOM and is
lost when dismissed. The accepted direction's compare / apply-as-working-draft / discard /
restore model has **no storage foundation whatsoever**. Section 2's requirements R1–R9 are
therefore additive construction, not adjustments.

### F3 — Discarding a revision correctly preserves the original. **OBSERVED.**

"Keep original answer" restored the submitted answer intact at 86 words, still carrying its
opening marker. The History record stored the **original**, not the draft. Member work was
preserved exactly as the accepted direction requires.

### F4 — The product tells the truth about its own limitations. **OBSERVED.**

Unprompted, in four separate places:
- *"Drafts and History stay in this browser for this account. They do not sync across devices."*
- *"This session is stored only in this browser for this account."*
- *"Illustrative best-practice example — this is not PeerSlate's real history."*
- *"Coaching is guidance. Your answer remains yours."*
- Delete affordances are labelled *"Delete this browser record"* and confirm with
  *"Delete this Interview Studio record from this browser?"*

The browser-local limitation Gate A treats as a gap is **already honestly disclosed** to
members. The architecture must not remove this honesty when it adds server storage; the
disclosures will need rewriting rather than deleting.

### F5 — Comparison status refuses to fabricate a trend. **OBSERVED.**

With one record, History showed *"Not enough comparable practice yet. More like-for-like
reviewed answers are needed before PeerSlate shows a p…"* rather than inventing progress.
Consistent with the never-invent rule.

### F6 — Local deletion works, per-record and bulk. **OBSERVED.**

Per-record deletion removed the record (count 1 → 0) after an explicit confirmation. A bulk
*"Clear local History"* control is also present. This confirms errata **E4** against the live
UI: any design treating deletion as absent is wrong.

### F7 — The revision silently dropped framing text. **OBSERVED.**

The submitted answer opened `"QA SCRATCH 2026-08-15."` and described the company as
`"a fictional company"`. The generated draft removed both. Harmless here, but it shows the
Revision Partner may drop member-authored framing it judges extraneous. The change ledger
Section 2 designs must record removals, not only additions.

### F8 — A confirmation-marker round trip worked in the one observed instance. **OBSERVED.**

The draft contained two markers in the required form — imperative, capitalised verb, full
stop:
`[Explain what triggered your attention to this inefficiency.]` and
`[Specify the quantified improvement in error rate, such as a percentage reduction or the
change from X errors to Y errors.]`

The coach asked the member to quantify *"the error rate dropped a lot"*; the reviser
**did not invent a percentage**. The UI showed *"Needs your confirmation (2 remaining)"* and
*"Replace or remove every bracketed prompt before review."* This is **one observed
instance** of the never-invent rule working end to end — the strongest single behaviour
observed in this batch. It is a bounded observation plus source-confirmed mechanism
(`_IMPROVEMENT_MARKER_PATTERN`, the improve prompt's marker instruction, and the marker
gate at `app.py:3889-3900`), not universal live proof that invention can never occur.

### F9 — Provenance labelling is present and accurate. **OBSERVED.**

The improve panel stated its basis: *"Based on: your submitted answer · no approved evidence
selected."* Review's evidence block read *"No authorized evidence suggestion is available for
this answer."* Source classes are already surfaced truthfully to the member.

### F10 — Follow-up refusal is visible to the member. **OBSERVED.**

The Interview AI panel showed *"Follow-up isn't available yet"*, matching the deliberate
server-side refusal at `app.py:4249-4250`. The boundary is honest in the UI, not hidden.

## Responsive behaviour

**OBSERVED**, viewport emulation in the in-app browser. **Labelled honestly as emulation** —
this is not a real device. Pete supplies real iPad/iPhone evidence separately.

| Width | Horizontal overflow | Key controls visible | Tap target height |
|---|---|---|---|
| 1280×800 (desktop) | 0 px | yes | — |
| 805×1024 (~tablet) | **0 px** | yes | — |
| 390×844 (~phone) | **0 px** | yes | **45 px** |

The insufficient-evidence message and its recovery actions remained visible and legible at
390 px. Tap targets meet the 44 px minimum. No layout defect was found at any width.

**UNVERIFIED:** real iOS Safari behaviour, real device performance, and screenshots — the
browser pane was not compositing frames, so all evidence here is DOM- and
measurement-based rather than visual. No screenshot was captured.

## Scratch data cleanup

Created during this test and then removed: one History record and the session draft state.
Per-record deletion was used for the History record, exercising the real affordance. A final
programmatic sweep confirmed **no remaining content matching `QA SCRATCH` or `Northwind`** in
any `peerslate:interview*` key. History returned to empty (`[]`).

**No pre-existing record was deleted.** The account's Interview namespace contained nothing
before this test.

## What this supplement does NOT establish

1. Behaviour for a member who **has** authorized evidence — no such member exists yet.
2. Real device behaviour, real screenshots, or real network conditions.
3. Provider latency, token, or cost figures — not instrumented, and reading them was outside
   the call budget.
4. The 100-record cap in practice — deliberately not tested, as it would require
   manufacturing 101 records.
5. Multi-tab, sign-out/sign-in, and background-resume behaviour — not exercised.
6. Whether any invented content could appear for a member **with** evidence; only the
   empty-evidence path was observable.
