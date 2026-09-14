# PS-MVP1-MY-DATA-INTAKE-AI-001: Private Intake and Luna Extra High

Protected package. Repository authority through accepted merge. Production
authority withheld: no deployment, no schema application, no live provider
use, no feature enablement.

## Outcome

Server-persisted cross-device composer drafts with 30-day inactivity expiry
and truthful conflict recovery. Typed, selectable-text document (PDF, DOCX,
TXT, 10,000,000 bytes each), and English voice input (180 seconds per
recording, several per draft) through the accepted intake lifecycle. Private
inspectable and separately deletable sources. GPT 5.6 Luna at reasoning
effort `xhigh` with strict structured extraction and semantic comparison.
Exact-then-semantic member-scoped matching with new, equivalent,
additional-detail, contradiction, and uncertain outcomes. Targeted proposals
and private-by-default canonical saves. Manual recovery during provider
failure. No AI authority over ownership, permissions, publication, deletion,
or canonical writes. No public-effect claim.

## What changed

- `services/my_data_extraction_adapter.py` (new): configured to request Luna
  extraction and comparison behind an injected provider, plus a deterministic
  fake. Closed outcome vocabulary, recursively strict schema, exact span and
  quote validation, listed-match references only, no model or effort fallback.
  Live Luna execution is not proven.
- `services/ai_foundation/contracts.py`: additive `ExtractionPurpose`,
  `REASONING_EFFORT_XHIGH`, `StructuredRequest`, `StructuredResult`.
  Existing answer contracts untouched.
- `services/ai_foundation/azure_foundry.py`: additive `respond()` sending
  `reasoning.effort xhigh` with a strict JSON-schema `text.format` envelope
  for the Responses API. `answer()` behavior unchanged.
- `services/resume_intake_service.py`: extraction adapter wiring with a
  truthful retryable manual path on provider failure, equivalent quiet
  duplicates with one independently bound keep-as-separate action per
  extracted text, document, or recording equivalent, exclusion-aware member
  shortlists, unsubmitted draft lifecycle using owner-scoped draft CAS that
  mutates only the drafts map, and duplicate-aware receipts. Extracted
  candidates live in mutable source-version-bound storage; immutable receipts
  contain identifiers only, and source purge redacts and invalidates every
  pending action. Owner-scoped mutation guards make purge mutually exclusive
  with candidate validation, consumption, canonical write, and intake commit,
  so a purge winner cannot be restored by a stale keep-separate snapshot.
  The proposed SQL adapter fails this action closed until a separately
  authorized transaction can enforce the same boundary across workers.
  Additional-detail
  and contradiction extraction outcomes resolve a listed `match_reference`
  through the owner-scoped catalog and bind that item as the proposal
  target.
- `services/resume_intake_repository.py`: `drafts` snapshot section,
  per-store `supports_drafts` flags, in-memory `with_drafts` CAS, and
  command-commit preservation of the live draft map so an acknowledged newer
  draft cannot be replaced by a stale whole-owner snapshot. SQL
  draft rows remain unavailable. No procedure or schema change.
- `resume_intake_routes.py`: `GET`, `PUT`, `DELETE`
  `/api/resume-intake/me/draft`.
- `static/js/my-data.js`: draft load bound to the originating server
  version, delayed-load safety, debounced save, two-version recovery
  choice before overwrite, duplicate receipts, extracted and structured
  keep-as-separate actions including one rendered action per equivalent,
  organizer-down notice, reattach descriptors. A successful keep-separate
  removes only its own action; other equivalents, pending proposals, and the
  unfinished server draft remain available.
  Ordinary draft-save success updates `draftVersion` only and does not
  empty the shared proposal host. No template change: the draft URL
  derives from the existing submit URL.
- Tests: `test_my_data_intake_ai.py`, `test_my_data_drafts.py`,
  `test_my_data_intake_sources.py` (new); extended intake route tests, My
  Data browser journeys including draft autosave visibility, reopen and
  delayed-GET conflict recovery, extracted keep-as-separate, updated
  runner method set.

## Boundaries kept

- Reuses entry policy, intake repository, proposal, source, document,
  transcription, job, and receipt mechanisms. No second fact store.
- Drafts never enter matching, resume use, visitor AI, or private assistance.
- Excluded entries never reach the provider: unwired or unreadable exclusion
  sources compare nothing.
- Read-only use of `services/my_opportunities/member_import_service.py`,
  `services/voice_capture_service.py`, and the resume draft services.
- Media Integration, Opportunity Slate, database, migration, pipeline, and
  resume-editor surfaces untouched. Claim-only control PR 1028 admitted the
  package registry, and this candidate adds only the truthful
  `current_protect` initiative entry and matching counts.

## Deferred with honesty

- Draft SQL procedure and table work (separately authorized schema package).
- Expiry worker hosting (reads already enforce expiry).
- Production wiring of the adapter and exclusion source in `app.py`
  (owned surface).
- Live provider, SQL engine, deployment, and public-consumer proof.
- The outbound Responses `text.format` envelope and closed extraction schema
  are asserted locally; they do not prove a live Foundry deployment ran.
- Member-facing copy avoids dash punctuation throughout.

## Verification

Unit, route, repository-adapter, registry-agreement, and desktop/mobile Flask
browser suites are green (see the evidence file). Deterministic fakes only.
Independent Codex Astra High returned PASS on the exact product-code candidate;
the later registry and completion-record delta does not change product code.
No implementation merge is claimed.
