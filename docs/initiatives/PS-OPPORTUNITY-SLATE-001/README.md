# PS-OPPORTUNITY-SLATE-001 — Opportunity Slate: private role-alignment workbench

**Owner:** Pete.
**Designated session manager:** Pete directly for this architecture phase; a
package manager is assigned only if a real cross-lane decision appears.
**Claude delivery pipeline (owner decision, 2026-08-02):** Claude Fable 5
(Extra High) architect → fresh Claude Fable 5 (Extra High) session as the
mandatory independent reviewer → Claude Opus 5 (Extra High) implementation
writer for the runtime lane → the same writer corrects accepted findings →
Pete gives final visual acceptance on the corrected real build → Azure PR,
pipeline, live verification, closeout. The reviewer and implementer choices are
owner routing exceptions recorded here per
`docs/AI_MODEL_AND_ROLE_ROUTING.md` (defaults: Sonnet implementation, Opus
review). Independent review is mandatory for this package regardless of
ecosystem: it is architecture-heavy, touches private cross-referenced member
data, includes consequential AI behavior, and includes deletion behavior.
**Branch:** `work/2026-08-02-opportunity-slate-architecture` from `origin/main`
at `803b34b364b53eb77edc34c197b3b38d02431b56`.
**Status:** ARCHITECTURE PHASE. The ChatGPT visual-creation round is complete
and locked. This package contains the architecture-ready visual-authority and
implementation handoff. **No runtime code is authorized.** The implementation
lane opens only when Pete explicitly activates it against this package.

## What this package is

Opportunity Slate is a new private, signed-in, single-role alignment workbench:
a member brings in one employer role (paste, voice dictation, document upload,
or public-link import), reviews the captured source, reviews PeerSlate's
proposed requirement interpretation, and then explores how their authorized
evidence aligns with the employer's Required and Preferred qualifications —
qualification by qualification, with voice-or-text responses and explicit
evidence connections. Results stay session-private until the member explicitly
saves them privately. Nothing is ever published, shared, or sent to an
employer from this surface.

Opportunity Slate is separate from Workshop and reuses the shared site shell.

**Owner decisions, Pete, 2026-08-02 (post-review):** (1) no Ask Slate AI
affordance — the generated images' subheader chrome is artifact, ignored;
(2) one active slate per member in v1, with versioned saved results; (3) v1
is **publicly reachable at a direct link, not behind the sign-in wall**,
Workshop-style: anonymous visitors get a truthful, banner-labeled public
session against a fixture demo evidence library with hard safeguards
(paste-only intake, rate/size limits, spend guard, noindex, nothing
persisted); signed-in members get the full private workbench; the Owner Home
entry card arrives when the sign-in wall lands. Handoff §§17–18 are the
authoritative record.

## Visual authority record

The locked set lives in
[`visual-authority/2026-08-02-chatgpt-lock/`](visual-authority/2026-08-02-chatgpt-lock/)
and is hash-pinned by its included `SHA256SUMS.txt` (verified at package
intake, 2026-08-02). ChatGPT created the set; Pete supplied it as the locked
authority for architecture and implementation handoff. The manifest's line
endings were normalized CRLF→LF at intake so `sha256sum -c` runs as shipped;
the twelve listed hashes are unchanged and all twelve files re-verified OK
after normalization. The image and document bytes are untouched.

Authority hierarchy (from the set's
[`00-READ-ME-FIRST.md`](visual-authority/2026-08-02-chatgpt-lock/00-READ-ME-FIRST.md)):

| Image | Authority |
|---|---|
| 01–03 | Primary flow truth: Role intake, Review Source, Review Requirements |
| 04 | **Exact Alignment authority** for geometry, separate cards, shadows, depth, and the uniform 12px card spacing |
| 05 | Saved-state **content and actions only**; its flatter geometry, compressed spacing, and blue-heavy palette must **not** be implemented |
| 06–09 | Supporting behavior and state truth (voice active, source processing, analysis processing, fallback/lifecycle sheet) |
| 10 | Typography and palette **reference only**; does not place Opportunity Slate inside Workshop and does not authorize Workshop navigation |

## Locked product rules (binding)

- Opportunity Slate is separate from Workshop. ~~Ask Slate AI remains in the
  Opportunity Slate subheader.~~ *Superseded by Pete's 2026-08-02 decision
  (handoff §17-Q1): the subheader chrome in the generated set is image
  artifact; no Ask Slate AI affordance ships with this package.*
- Near-black navy for headings/primary text; muted slate for supporting copy;
  cobalt primarily for actions, links, selected outlines, important icons.
  Green = saved/supported. Amber = partially supported / recoverable warning.
  Slate gray = not enough information.
- Required and Preferred qualification accounting stays visible **without** an
  overall score, percentage, recommendation, employer prediction, or
  traffic-light verdict.
- Voice and text edit the same member response. Voice never automatically
  submits, confirms, analyzes, saves, publishes, or navigates.
- AI proposes; the member confirms. Nothing saves, publishes, shares, deletes,
  or reanalyzes without explicit member action.
- Processing is bounded, descriptive, and local to the workbench; it never
  exposes invented partial results.
- Saved state and analytical currency are separate truths. Input changes
  require explicit reanalysis; previous saved results remain identifiable and
  are never silently overwritten; new results remain unsaved until explicitly
  saved.
- Failed deletion leaves the slate visibly saved. Failed import or analysis
  preserves confirmed inputs and offers safe retry or fallback.

## Deliverables

| # | Deliverable | Status |
|---|---|---|
| D1 | Visual authority intake, hash verification, and this package record | complete 2026-08-02 |
| D2 | Architecture-ready visual-authority and implementation handoff ([01](01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md)) | complete 2026-08-02, review findings incorporated |
| D3 | Fresh Fable 5 independent review of D2 at the exact package SHA | complete 2026-08-02 at `9e423de7bd8a3d03091597887f1fa0913a7d40e0` — verdict **Conditional**: 3 Major (nonexistent purge mechanism cited; unregistered authority-gap surfaces; missing homepage determination), 5 Minor; every runtime citation in the handoff verified true; no locked-rule, trust, or governance violation found |
| D4 | Correction of accepted findings by the same architect | complete 2026-08-02 — all eight findings corrected in place (purge defined as OS-1 in-scope work; §14-M13/M14 authority-gap register; homepage determination recorded; paste-path processing, upload-failure contract, `Review my response`, OS-1 Protected relabel, Python 3.14 dependency note, manifest normalization); focused reviewer recheck of the correction diff at `184e5caf94c9910d5397f5a97a6bf0c1b1666444` returned **Pass** — all eight findings resolved, no new defects requiring correction |
| D5 | Pete's acceptance and implementation-lane activation decision | §17 questions answered by Pete 2026-08-02 and recorded, with the public-v1 mode added as §18 (delta-reviewed); final acceptance of the amended handoff pending |

## Implementation entry gate

The Opus 5 implementation writer may begin only when all of the following are
true:

1. Pete has accepted the reviewed architecture handoff and explicitly opened
   the runtime lane.
2. The open owner decisions listed in the handoff's final section are
   resolved.
3. The writer starts from current `origin/main` on a fresh
   `work/YYYY-MM-DD-...` branch, confirms this package, and reserves its
   writable files.
4. The visual work follows `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`
   with Image 04 as the exact Alignment authority, and completes the
   homepage-impact check recorded in the handoff.

## Forbidden scope

- No new or edited visual authority: ChatGPT owns visual creation; Pete locks.
- No runtime code, schema, migration, route, or deployment change in this
  architecture phase.
- No placement of Opportunity Slate inside Workshop, and no new permanent
  navigation layer without approved route authority.
- No overall score, ranking, recommendation, or employer-prediction feature at
  any phase.
