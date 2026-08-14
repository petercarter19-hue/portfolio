# PS-OPPORTUNITY-SLATE-CONTINUATION-001 - Home, autosave, history, and scale

**Status:** Planned - not active.
**Authority placement:** Continuation/amendment of `PS-OPPORTUNITY-SLATE-002`;
it does not replace that package's staged intake and review architecture.
**Risk path:** Protected when persistence/history work is activated.
**Runtime status:** No implementation, migration, or release is authorized.

## Owner outcome

Clicking **Opportunity Slate** opens an Opportunity Home rather than reopening
the last retained review. Unfinished work is preserved, but resuming it is an
intentional choice. The workbench feels bounded and calm on a wide monitor.

## Urgent owner-reported diagnostic intake - 2026-08-14

Pete reports that Opportunity Slate is substantially broken in current use.
A link imported on 2026-08-14 appears in the source list, but no expected
extracted content or usable downstream result appears. The sidebar/workbench
also feels strange or broken. These are owner observations, not yet reproduced
causes or verified fixes.

The next activation must begin read-first and preserve the existing source.
It must separately trace URL acquisition, redirects/response type, parsing,
raw-text extraction, persistence/version state, refresh/resume, and the later
requirements-interpretation handoff. It must not delete and re-import Pete's
source merely to make the symptom disappear.

### Extraction direction

- Fetching, decoding, normalizing, and raw-text extraction use focused,
  deterministic tooling with explicit failure states.
- A general-purpose LLM is not the extraction authority and must not fabricate
  missing source text.
- Any later AI statement/requirement interpretation consumes bounded extracted
  text as untrusted employer source, returns a reviewable proposal, and remains
  visibly separate from extraction success.
- A source record with missing, partial, stale, blocked, or failed extraction
  shows that truth plus retry/recovery; it cannot appear complete merely because
  the original link was retained.

## Direction contract

### Opportunity Home

The default signed-in landing surface presents current/recent opportunities,
**New opportunity**, and archive/history. Each opportunity may show title,
organization, last updated time, stage/progress, and an explicit **Continue
review** action. Navigation to the product root must never trap the member in a
prior review state.

### Autosave and history

- Continuously autosave the member's current working draft to their account.
- Show quiet, truthful state such as `Saving...`, `Saved just now`, or a useful
  failure/retry state. Do not add a ceremonial Save button.
- Keep the mutable current draft separate from meaningful immutable versions.
  Do not create a history entry on every keystroke.
- Candidate milestones are source captured, source confirmed, requirements
  confirmed, alignment reviewed, and member-saved completion.
- Provide per-opportunity history/archive with explicit restore behavior.
- Keep public preview/browser-only retention truth separate from signed-in,
  account-backed behavior.

### Bounded workbench

Reduce the dominant work area approximately 25-30 percent on large desktops and
allow the warm page background to remain visible. Treat that number as an
initial visual target, not a universal fixed width: source intake, requirement
review, comparison, and inspectors may need different bounded maxima.

## Decisions required before implementation

1. Multi-opportunity record and current-draft ownership model.
2. Cross-device autosave, conflict, offline, retry, and failure behavior.
3. Version milestone names, retention, restore, archive, delete, and recovery.
4. Whether restored history creates a new version rather than rewriting truth.
5. Stage-specific desktop widths and responsive collapse behavior.

## Acceptance gate

From Opportunity Home a member can deliberately start, continue, archive, and
inspect history without losing work or confusing a draft with a saved version.
The signed-in member can refresh and return on another supported device with
truthful state. A new visual lock and protected persistence design precede code.

The gate also requires the existing 2026-08-14 imported source to be diagnosed
non-destructively and the complete source-to-extracted-text-to-interpretation
chain to expose truthful success, partial, empty, blocked, timeout, retry, and
failure states.
