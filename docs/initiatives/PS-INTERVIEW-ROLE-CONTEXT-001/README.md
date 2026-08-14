# PS-INTERVIEW-ROLE-CONTEXT-001 - Role-tailored Interview Me

**Status:** Direction package recorded; implementation not active.
**Owner:** Pete.
**Delivery class:** Protected when implemented because it introduces private
external-source intake, cross-room authorization, and consequential AI.
**Runtime status:** No Interview Studio, Opportunity Slate, O*NET, schema,
provider, configuration, deployment, or production behavior is changed by this
package record.

## Owner outcome

A member can bring the role they are actually pursuing into Interview Me and
practice questions shaped by that role. The member may:

1. paste a job posting;
2. upload a supported job-source document;
3. provide a public job-posting link; or
4. explicitly transfer an exact authorized role/source version from
   Opportunity Slate.

After the member reviews and confirms the captured source, PeerSlate proposes a
role-tailored question set. The released Interview Me sequence remains intact:
question -> type or dictate -> submit -> coaching -> improve -> next question.
Role context changes the questions; it does not replace the answer or coaching
workflow.

## Package placement

This is a new functional package. It is intentionally separate from:

- `PS-INTERVIEW-STUDIO-EXPERIENCE-POLISH-001`, which remains visual-only;
- `PS-INTERVIEW-ASK-MY-SLATE-001`, which retrieves permitted member evidence to
  jog memory and does not own employer-source intake; and
- the completed authenticated Interview Studio package and its current
  route/name/visual authority.

A setup or source-review composition that materially changes the released
Interview experience requires a fresh ChatGPT-created, Pete-accepted visual
lock before runtime implementation. This charter alone is not visual authority.

## Context-entry contract

### Direct Interview intake

- Reuse the hardened public-link and upload acquisition boundary already used
  by Opportunity Slate. Do not build a second URL fetcher or document parser.
- Treat all external text as untrusted content, never as instructions to the
  model or application.
- Preserve the member's pasted text, selected file name, or URL through
  validation and recoverable failure states.
- Show the captured employer, role title, source type, and wording for member
  correction and explicit confirmation before question generation.
- A direct Interview intake creates private role context for the Interview
  session. It does not silently create an Opportunity Slate, publish a job
  listing, or add canonical member evidence.

### Opportunity Slate transfer

- The member explicitly chooses **Practice this role in Interview Me**.
- Transfer an opaque reference to the exact authorized opportunity, confirmed
  source version, confirmed requirement-set version when one exists, and
  member-controlled interview stage. Do not copy a second canonical job-source
  fact body into Interview Studio.
- Derive identity server-side and authorize the opportunity and every referenced
  source before retrieval. A browser-supplied opportunity or source identifier
  is never proof of ownership.
- Pin the context version used to create each question set. A later source or
  requirement revision makes the set visibly older; it never silently rewrites
  existing questions, answers, or coaching.
- If the source is deleted or permission is lost, retain only the minimum
  permission-safe history/tombstone the final retention contract allows. Never
  disclose the deleted source through question history.
- If Opportunity Slate has only a confirmed source and no confirmed requirement
  set yet, Interview Me may tailor from that source and must label that narrower
  basis honestly.

## Question-generation contract

The employer posting is the primary source for employer-specific questions.
Question generation may use confirmed role identity, responsibilities,
requirements, hard constraints, and the member-selected interview stage.

Every generated question record must bind:

- the exact role-context version;
- the applicable confirmed source spans or requirement references;
- a PeerSlate question family and interview-stage label;
- the prompt/model contract version; and
- any optional O*NET data release and internal mapping version used for
  background enrichment.

The member can skip, replace, or add a custom question. AI proposes the
questions; the member decides what to practice. The system must not infer an
employer's private intent, promise likely questions, score the member, rank
their fit, produce a qualification verdict, or treat missing PeerSlate evidence
as proof that the member lacks a skill.

When source-grounded generation is unavailable, Interview Me remains useful:
keep the confirmed role context and offer the existing generic/family-aware
question bank plus retry. O*NET unavailability must never block this fallback
or the core employer-source path.

## O*NET boundary

O*NET is optional occupational research, not employer truth, a member profile,
or an interview-question bank. Its recovery status is recorded in
[`O_NET_RECOVERY_STATUS.md`](O_NET_RECOVERY_STATUS.md).

If later evaluation justifies use:

- acquire one official release as a versioned offline snapshot with source URL,
  download date, SHA-256, license, attribution, and an unmodified archive;
- initially evaluate only occupation records, job/alternate/reported titles,
  related occupations, and selected task cues;
- keep PeerSlate role IDs, labels, aliases, disambiguation, question taxonomy,
  and product logic canonical;
- never call O*NET Web Services in the member request path or expose the O*NET
  hierarchy as PeerSlate truth; and
- promote an O*NET-informed alias or mapping only after blinded tests show a
  measurable improvement without increasing forced incorrect resolution.

Azure AI Search is not required for the first O*NET evaluation. A small
versioned offline resolver is simpler and more auditable; search infrastructure
can be reconsidered only after real evaluation volume and retrieval needs exist.

## Privacy, retention, and member control

- Role sources and generated question sets are private by default.
- Before direct upload/import, state what is transmitted and whether the source
  will be retained with the session.
- Runtime implementation must lock the direct-source retention period,
  export/delete behavior, and history/tombstone rules before release.
- Saving direct Interview context as an Opportunity Slate is a separate,
  previewed member action; it never occurs automatically.
- No job source, question, answer, coaching result, or O*NET mapping is
  published, sent to an employer, used as canonical member evidence, or added
  to My Knowledge without a separate authorized member action.

## Required failure and abuse handling

- Public-link intake keeps the URL and offers paste/upload when the page is not
  public, times out, violates TLS/SSRF rules, exceeds limits, or cannot be
  parsed.
- Upload intake names unsupported type, size, unreadable, malware/content
  inspection, and storage failures without losing the member's other work.
- Prompt injection in employer text cannot change system instructions, request
  private sources, trigger tools, or alter retention/publication behavior.
- Cross-member references, forged IDs, stale versions, deleted sources, and
  expired authorization fail closed.
- AI failure never erases confirmed context or an answer draft.

## Implementation sequence

1. Lock direct-source retention and the setup/source-review visual states.
2. Define one shared private role-context reference contract over the existing
   Opportunity Slate intake and source-version boundaries.
3. Implement direct paste/upload/link capture and explicit source confirmation
   behind sign-in and a default-off package flag.
4. Implement exact Opportunity Slate transfer and stale/deleted-source states.
5. Add source-grounded question proposals, provenance, evaluation fixtures,
   and generic fallback without changing the answer/coaching flow.
6. Evaluate the optional offline O*NET subset independently. It does not block
   steps 1-5 and enters runtime only after blinded improvement evidence.
7. Run Protected authorization, privacy, prompt-injection, retention/deletion,
   accessibility, responsive, failure, cost, and release gates before exposure.

## Acceptance evidence for a future runtime package

- Paste, supported upload, public-link import, and Opportunity Slate transfer
  work at desktop, tablet, 390px, 320px, keyboard-only, and 200% reflow.
- Tests prove server-derived identity, authorization-before-retrieval, exact
  context/version binding, cross-member refusal, stale context, source deletion,
  session deletion, and export behavior.
- Adversarial employer text cannot override instructions or retrieve member
  data; model inputs and outputs remain bounded.
- Reviewers can trace each proposed question to the confirmed employer source
  or clearly identify it as generic/optional occupational enrichment.
- Blinded evaluation shows role-context questions are more relevant than the
  generic baseline without fabricated employer claims, fit scoring, or reduced
  question diversity.
- The generic question bank remains available when link import, AI, or O*NET is
  unavailable.
- No test or UI implies that the feature is implemented, deployed, enabled, or
  live until exact release evidence exists.

## Open decisions before implementation activation

1. Exact retention period for a direct Interview-only role source.
2. Whether saved Interview history retains the full confirmed source, a shared
   source reference, or a minimal fingerprint/title after session completion.
3. Which setup/source-review states need a new material visual lock.
4. Initial maximum source length, file size/types, question-set size, and model
   cost ceiling based on measured Opportunity Slate intake behavior.
