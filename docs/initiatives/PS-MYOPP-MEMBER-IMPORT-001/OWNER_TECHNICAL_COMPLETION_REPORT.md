# PS-MYOPP-MEMBER-IMPORT-001 — technical completion record

**This record states truthfully what is and is not true right now.** It was
first drafted mid-implementation (before the three parallel writers had
committed) and is rewritten here against the frozen candidate: implementation,
the self-review correction pass, the recorded disposable-gate proof, and the
registry surfaces are all committed. The remaining gaps are the independent
exact-SHA review and everything downstream of it (receipt, merge, close).

## Core record

- **Task/package and delivery path:** `PS-MYOPP-MEMBER-IMPORT-001`,
  Protected.
- **Outcome and member/site effect:** the permanent private `member_import`
  path — deterministic paste/upload intake under the bounded-intake
  discipline (PDF/DOCX/plain text, magic-byte sniff, streaming cutoff), a
  sanitize/extract pipeline recording the doc 06 §2 closed outcome states per
  stage (never AI), owner-scoped provenance, identical not-found owner
  isolation, export and member delete via body-removal tombstones, dual
  retention (member lifecycle plus rights at point of use), content-free
  audit, the C8 integration seam, the prebuilt **disabled** service-level
  URL-fetch port, and the additive `PS-MYOPP-006` migration trio, are
  implemented and committed. There is no route, UI, or member-visible site
  effect — C10 owns no HTTP surface (that is C8's).
- **Package manager:** Not separately identified as a distinct role in this
  task; the same claim's assigned writers performed the blueprint-bound
  implementation and documentation work directly.
- **Writer:** the claim's recorded `writer_ref` is
  `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/myopp-member-import-writer`.
  Implementation was built three-wide under that claim: "Implementer A"
  authored `services/my_opportunities/member_import_service.py` and
  `tests/test_my_opportunities_member_import.py`; "Implementer B" authored
  the `PS-MYOPP-006` SQL trio; "Implementer C" authored this initiative's
  `README.md` and this record. All three landed together in implementation
  commit `18e49f75` ("Implement PS-MYOPP-MEMBER-IMPORT-001 (C10): member
  import service, PS-MYOPP-006 trio, docs"). A subsequent self-review scan
  found defects against that commit and corrected them in commit `e8e4f10f`
  (the PDF bounded-decode blocker, the HTML-safe sanitizer, and truthful
  docs) — see "Self-review corrections" below.
- **Branch and base:** `work/2026-09-01-myopp-member-import-001`, confirmed
  via `git branch --show-current`. `git log` shows the implementation commit
  `18e49f75` sitting directly on this branch's tip, descended from merge
  commit `abbbdb6e` ("Merge pull request 836 from
  work/2026-09-01-delivery-activation-myopp-member-import-001 into main") —
  this branch's activation control commit.
- **Candidate SHA:** the frozen candidate is the tip of
  `work/2026-09-01-myopp-member-import-001` at review routing (implementation
  `18e49f75`, self-review corrections `e8e4f10f`, the recorded gate proof and
  registry surfaces in the freeze commit). Its exact 40-character SHA is
  recorded in the review receipt and, at close, in
  the claim's `merged_sha` lineage.
- **Changed paths (across the three-wide implementation pass and this
  self-review correction pass):**
  - `services/my_opportunities/member_import_service.py` (new at `18e49f75`;
    corrected in this pass — see below)
  - `tests/test_my_opportunities_member_import.py` (new at `18e49f75`;
    corrected/extended in this pass — see below)
  - `SQL FIles/Migrations/PS-MYOPP-006_member_import.sql` (new at `18e49f75`)
  - `SQL FIles/Migrations/PS-MYOPP-006_member_import_rollback.sql` (new at
    `18e49f75`)
  - `SQL FIles/Verification/PS-MYOPP-006_member_import_verify.sql` (new at
    `18e49f75`)
  - `docs/initiatives/PS-MYOPP-MEMBER-IMPORT-001/README.md` (new at
    `18e49f75`; corrected in this pass to describe the committed state
    truthfully instead of the pre-commit "nothing exists yet" state it was
    drafted against)
  - `docs/initiatives/PS-MYOPP-MEMBER-IMPORT-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`
    (new at `18e49f75`; rewritten here, same reason)

  `SQL FIles/Migrations/registry.json` was **not** touched by this claim as
  of this writing — its `PS-MYOPP-006` entry append remains outstanding; see
  "Known limitations" item 7 in the README, unchanged and still accurate.
  `docs/governance/PACKAGE_REGISTRY.json` was likewise not touched. No C2-C6
  file (`canonical_service.py`, `criteria_service.py`,
  `interpretation_service.py`, `retrieval_service.py`, `search_worker.py`,
  `index_projection.py`, `index_fence.py`, `qualification_service.py`,
  `evidence_port.py`, `relationships_service.py`) was touched by any of the
  three implementation passes or this correction pass — confirmed directly
  by `git status --short` (showing only this claim's own files) and by
  `StructuralStopTests.test_no_c2_through_c6_file_is_modified_relative_to_origin_main`,
  which diffs each of those files' on-disk content against
  `origin/main` and passes.
- **Verification performed and result:** run directly against the corrected
  candidate in this worktree.
  - `python3 -m unittest tests.test_my_opportunities_member_import -v` —
    **127 tests, 0 failures, 1 skipped.** The one skip
    (`RegistryEntryTests.test_registry_entry_shape_and_requires_chain`) is
    was honest during the build; the `PS-MYOPP-006` registry entry (carrying
    the recorded gate proof) is now appended and that test passes — the full
    Group I migration suite runs green against the SQL trio.
  - Regression: `python3 -m unittest tests.test_my_opportunities_relationships
    tests.test_my_opportunities_retrieval tests.test_my_opportunities_qualification
    tests.test_my_opportunities_criteria tests.test_my_opportunities_canonical
    tests.test_my_opportunities_ingestion tests.test_my_opportunities_safe_outbound -v`
    — **329 tests, 0 failures.**
  - `__pycache__`/`*.pyc` cleaned after each run.
- **Release state:** repository-only. The branch is committed, frozen, and
  the registry surfaces are on main via the extend-surfaces PR; no PR
  completion, deployment, schema apply, enablement, or live verification has
  happened. The independent review outcome, PR, and merge SHA post-date this
  frozen candidate and are recorded in the receipt and evidence file. Merge
  alone will not apply schema, deploy, enable, or contact a provider (README
  "Scope exclusions").
- **Known limits / owner decision needed:** No owner decision is outstanding
  per the blueprint's own review (`C10_ARCHITECTURE.md` §6: "None."; REC-08
  already settled the fetch-port shape, and the three operational defaults
  recorded in the README's "Approved writer-level defaults" section are
  writer-level, not owner questions). Procedural items remain, honestly
  marked:
  - the self-review correction pass is committed (`e8e4f10f`) — DONE;
  - the disposable migration-gate proof for `PS-MYOPP-006` under the recorded
    C4-through-C9 owner envelope: DONE (attempt a2 recorded verified = 1;
    attempt a1 proved soundness but was not recorded due to an operator
    output-capture error, its database deleted with ResourceNotFound
    confirmed; both throwaway databases deleted, temporary firewall rule
    removed, no production or staging action) — the proof block is in the
    `PS-MYOPP-006` registry entry;
  - the extend-surfaces transition appending `SQL FIles/Migrations/registry.json`
    and `docs/governance/PACKAGE_REGISTRY.json` to this claim: DONE (merged);
  - reconciliation against current Azure `origin/main` before freeze: DONE
    (merged clean, write/merge preflight passed on the frozen tip);
  - the required independent exact-SHA review (Protected) — **TO BE
    COMPLETED**;
  - correction and re-freeze if that review returns REVISE — **TO BE
    COMPLETED, conditional**;
  - the generic review receipt and the fixed, runtime-inert
    `docs/governance/lane_claims/evidence/PS-MYOPP-MEMBER-IMPORT-001.md`
    file — **TO BE COMPLETED**;
  - merge preflight, the Azure PR, and an accepted merge — **TO BE
    COMPLETED**.
- **Next action:** the writer commits this self-review correction pass on
  `work/2026-09-01-myopp-member-import-001`, re-verifies every fact this
  record states (branch, base, the 127/329 tallies above) is still current,
  reconciles against then-current `origin/main`, then proceeds to freeze →
  independent review → correction (if any) → receipt/evidence →
  extend-surfaces for `PACKAGE_REGISTRY.json` and `registry.json` → merge
  preflight → Azure PR → merge. The disposable `PS-MYOPP-006` gate proof
  under the recorded C4-C9 envelope authorization is a separate, still-open
  step (not required before merge per the C4/C5/C6 precedent's `"gate":
  null` pattern, but required before this package can be considered fully
  closed).

## Independent review round 4 (candidate 5842db84) — the in-process approach abandoned for OS isolation

Round 4 falsified BOTH round-3 defenses: the raw-structure scan has PDF-tokenizer
blind spots (an indirect /Filter reference makes a stream look unfiltered; a >>
byte inside a (...) string literal in a stream dict makes the scanner mis-find
the dict boundary and skip the whole object — 151 MiB and 559 MiB respectively),
and the tracemalloc watchdog is outrun by linear accumulation to 1+ GiB across
pypdf's un-checkpointed object resolution before its coarse per-page poll fires.
The decisive lesson across four rounds: an untrusted PDF parser cannot be safely
policed from OUTSIDE — a regex cannot re-derive the structure the real parser
interprets, and Python-level polling cannot bound C-level burst allocation.

The fix is architectural: ALL untrusted document parsing (PDF and DOCX) now runs
inside a short-lived isolated CHILD PROCESS, spawned via subprocess.run of a fresh
interpreter (never os.fork from the request worker), bytes in / JSON out, no
network/DB. The child sets a hard memory ceiling (RLIMIT_AS then RLIMIT_DATA,
256 MiB) and a wall-clock deadline at its own startup; the parent maps any child
timeout, nonzero exit, signal-kill, or malformed output uniformly to a truthful
refused parser_resource_bounds (persisted row + content-free audit, child stderr
never surfaced). The ~700 lines of failed in-process bounding (bounded-inflate,
per-page/document font-aux walks, raw-structure scan, tracemalloc watchdog) were
REMOVED; the DOCX zip-bomb bounds and magic-byte admission remain as fast
pre-filters on top of isolation, never instead of it.

GUARANTEE and its honest boundary: the parent worker's resident memory (measured
via resource.getrusage RSS, not tracemalloc) is bounded UNCONDITIONALLY on every
bomb class and both round-4 blind spots (delta < ~3 MiB; the 1.2 GiB-scale case
refused by wall-clock at 12s) — the child is a separate address space reclaimed
on exit, so whatever it allocates never touches the worker, and if the OS
OOM-kills the child the parent simply returns a refusal. The hard rlimit ceiling
adds a clean fast refusal on Linux (the Azure App Service production target, where
RLIMIT_AS is the standard mechanism); it is NOT enforced on the macOS dev sandbox
(a documented Darwin limitation for a process capping its own address space,
verified directly and disclosed) — on macOS a sub-pypdf-cap accumulation completes
inside the isolated child rather than being refused, still without touching the
parent. Cases exceeding pypdf's own ~75 MiB single-call cap or the wall-clock are
refused platform-independently. Positive controls (base-14, DOCX, 10-font/15-page,
FontFile2, legitimate ObjStm-based PDF) all extract with exact round-trip text
parity through the boundary. Per-upload subprocess overhead: ~70 ms (PDF), ~48 ms
(DOCX). 26 new isolation/mapping/mechanism tests including a parser-independent
proof that the parent mapping never inspects what the child was parsing. Final
suite: member_import 150/150, package_registry + regression 331/331 green.

## Independent review round 3 (candidate 8ee329e1) — the class closed structurally

Round 2's document-wide font-auxiliary budget was comprehensive for its class
(the reviewer attacked it five more ways and it held), but a third evasion
remained in a different decompression PATH: pypdf decompresses /Type/ObjStm
object streams and /XRef cross-reference streams during object resolution,
outside any role-based walk (12 ObjStm pages -> 405.8 MiB from a 361 KiB PDF).
The pattern across all three rounds: bounding by stream ROLE keeps missing
sites. The fix stops chasing roles and closes the class two ways:

1. PRIMARY — a parser-INDEPENDENT raw-structure pre-scan
   (_check_pdf_raw_structure_bounds) that enumerates every literal
   stream/endstream object in the file's own bytes (scanning to endstream,
   never trusting a lying /Length) and bounded-inflates each into ONE
   document-wide decoded-bytes budget (4 MiB/stream, 64 MiB total, 4096
   streams), refusing before PdfReader is ever constructed. By PDF spec 7.5.7
   a stream object cannot be packed inside another stream, so a byte-level
   scan is structurally COMPLETE for FlateDecode — no role can hide. Covers
   content, font-aux, ObjStm, and XRef streams in one place. Honest trade-off,
   documented: empty-password-encrypted PDFs with compressed streams now
   refuse parser_failure (best-effort feature; uncompressed-stream encrypted
   PDFs still extract).
2. BACKSTOP — a tracemalloc-polled memory-ceiling watchdog (200 MiB, 20 ms
   poll) wrapping the whole pypdf parse+extract window, converting any
   allocation the pre-scan misses into a truthful parser_resource_bounds
   rather than a crash/OOM. resource.setrlimit(RLIMIT_AS) was evaluated and
   rejected (fails in this environment; forking from a live request worker is
   operationally unsafe on App Service); the watchdog suffices because pypdf
   caps any single decompress call to ~75 MiB, so every large peak came from
   accumulation a 20 ms poller catches.

All six bomb classes now refuse under ~8.5 MiB peak (8-font, single-huge,
XObject-nested, cross-page, ObjStm-multiplication, XRef). 16 new tests
including a backstop proof that fires on an allocation the pre-scan is
deliberately bypassed for. Final suite: member_import 152/152 (stable across
repeated threaded runs), package_registry + regression 331/331 green.

## Independent review round 2 (candidate f9987594) — two evasions, closed by a strategy change

The re-review attacked round 1's new per-page bound and found the same
memory-bomb class evaded two more ways: fonts nested in Form XObjects
(bypassing the page-direct scan → 728 MiB from a 607 KiB PDF) and per-page
limits summing across 400 pages (→ multi-GiB). Rather than patch two more
paths, the fix changed strategy to a DOCUMENT-WIDE decompression budget: a
single shared byte+count accumulator across all pages, over a recursive
walk of the full /Resources/XObject Form graph (cycle-protected by
indirect-object identity), pre-screened once before any extract_text().
Budgets raised to realistic document totals (64 MiB / 4096 streams, 4 MiB
per single stream) so legitimate multi-page multi-font documents are never
over-refused, with positive-control tests proving it. All four bomb cases
now refuse under ~16 MiB peak (8-font 15.52, single-huge 8.40 no-crash,
20-XObject-nested 15.98, 40-page bounded). Eight new
PdfDocumentWideAuxiliaryStreamBoundTests including the reviewer's exact
reproductions, a 25-level nested chain, a cyclic graph, and legitimate
controls. Final suite: member_import 142/142, package_registry + regression
331/331 green.

## Independent review round 1 (candidate 76c72c3c) — one blocker, fixed

A fresh adversarial independent reviewer, executing crafted malicious uploads
under memory measurement, found that the self-review's PDF fix had bounded
only the `/Contents` FlateDecode path: `page.extract_text()` also decompresses
font auxiliary streams (`/ToUnicode` CMaps, embedded `/Encoding`) with no bound
and no exception guard. Proven: eight fonts carrying 30 MiB ToUnicode CMaps
each turned a 244 KiB PDF into a 367.8 MiB peak with extraction succeeding, and
a single 180 MiB ToUnicode stream crashed uncaught out of `submit_upload`.

Fixed (both halves): a new aggregate bound (`_check_pdf_page_auxiliary_stream_bounds`,
`MAX_PDF_AUX_STREAM_BYTES` 8 MiB / `MAX_PDF_AUX_STREAM_COUNT` 64, env-tunable)
pre-screens every font auxiliary stream through the same capped-decompress
discipline and refuses `parser_resource_bounds` on the running SUM (closing the
multiplication gap), deliberately never touching `/FontFile*`; and
`_extract_pdf` now wraps `extract_text()` so any pypdf exception becomes a
truthful `parser_resource_bounds`/`parser_failure` outcome, never a crash.
Measured after: the 8-font case 367.8 -> 23.74 MiB refused; the single-huge
case 150.8 MiB+crash -> 16.40 MiB refused with a persisted refusal row and
audit event. The reviewer's DOCX amplification MINOR was also taken (a
dedicated 5 MiB `document.xml` cap). Six new binding tests
(`PdfAuxiliaryStreamBoundTests`) build real Type0/CIDFontType2 font structures.
Final suite: member_import 134/134, package_registry + C2-C6 regression
331/331, all green.

## Self-review corrections (this pass)

Found against implementation commit `18e49f75`; all three are fixed and
covered by passing tests in the 127-test tally above.

1. **PDF content-stream bomb exhausted memory before the size bound could
   fire.** The original pre-screen in `_parse_pdf` called
   `page._get_contents_as_bytes()`, which fully decompresses a page's
   FlateDecode content stream into memory before this module ever measures
   its length. Measured directly against the unmodified call: a 153 KiB
   on-disk PDF whose stream decodes to 50 MiB peaked at 121.7 MiB RSS,
   entirely ignoring the configured 2 MiB page-content-bytes cap until after
   the full inflation had already happened; at the 15 MiB upload cap, a
   crafted single page could force a multi-GB peak, a worker-OOM risk. Fixed
   by reading the stream object's RAW, still-compressed bytes directly
   (`._data`) and inflating them through a hard-capped
   `zlib.decompressobj().decompress(data, max_length)`, so decoded output
   past the bound is never materialized — proven by
   `PdfPageContentBoundMemoryTests` (tracemalloc-measured; a 100 MiB decode
   target under the real 2 MiB default cap now peaks under 20 MiB, refusing
   `parser_resource_bounds`). Non-FlateDecode filters and a page's `/Contents`
   being an array of multiple stream objects (cumulative bound) are also
   handled; see `_bounded_inflate` / `_check_pdf_page_content_bounds` in
   `member_import_service.py`.
2. **`sanitized_text` was not actually HTML-safe.** The markup sanitizer
   (`HTMLParser(convert_charrefs=True)`) decodes entity references in the
   same pass it strips tags, without re-tokenizing the decoded output — so
   an entity-encoded or split-nested payload (e.g.
   `&lt;scr&lt;script&gt;ipt&gt;...`, which decodes in one pass to a string
   containing the literal substring `<script>`) could leave a genuinely
   tag-shaped substring in the stored field, despite its name and
   `SANITIZER_VERSION` implying a stronger guarantee. C10 renders nothing
   itself, so this was not live-exploitable within this package's own
   scope, but the field's contract overpromised. Fixed by HTML-escaping the
   final assembled text (after tag-stripping, before the UTF-16 truncation
   cap so an entity is never split in half) in `_extract`; `sanitized_text`
   is now plain text that is already HTML-escaped. The README's C8
   seam-contract section now states this, and that consumers must still
   apply their own render-time output-escaping discipline regardless
   (escaping at write time is defense in depth, not a license to skip it at
   read time). Covered by new canary tests reproducing both of the
   coordinator's exact example payloads, plus a positive control proving
   legitimate `&`/`>` content survives (escaped, not dropped or corrupted).
3. **This pair of docs was stale relative to the committed candidate.** Both
   files were drafted by Implementer C before the other two writers'
   commits landed, and said so honestly at the time ("not yet committed...
   nothing exists"). That was true when written and false once `18e49f75`
   landed; both files are rewritten here to describe the current, committed
   (plus now-corrected) state. The erasure-path gap and the two pending
   registry-surface obligations (README "Known limitations" items 1 and 7)
   were already stated correctly and are unchanged.

Two minor items from the same scan, also fixed: a stray `"adapter_absent"
if False else "url_fetch_unavailable"` dead-code construction in one test
assertion, replaced with the literal string it always evaluated to; and a
one-line comment added to `ImportStageOutcome` noting that a future
SQL-backed repository must synthesize `sequence_number` itself (the schema's
`UQ(myopp_member_import_id, sequence_number)` has no Python-side
counterpart in this in-memory-only reference implementation, which preserves
trail order structurally via list-append order instead).

## Protected additions

- **Privacy and authorization (verified):** every `MemberImportService`
  member-facing method is owner-scoped (`_require_user_key` first,
  `_owner_key_or_not_found` guarding every opaque import-key lookup), with
  cross-owner and truly-absent keys returning the identical `not_found`
  shape (blueprint matrix row 20; doc 08 §7) — confirmed directly by
  `CrossMemberIsolationTests` (get/delete/stage_outcomes cross-owner vs.
  absent, list/export never leaking across members, deleting one member's
  import leaving another's intact) in the 127-test tally above.
- **AI / consequential automation (verified):** the module makes no
  provider call and has no AI proposal seam — the decode/parse/extract
  pipeline is deterministic tooling only (doc 06 §2), and the module is
  route-free, Flask-free, and provider-free by design. Confirmed by
  `StructuralStopTests.test_no_forbidden_provider_or_web_framework_import`
  (an AST walk of the module's own imports, asserting none matches
  flask/requests/anthropic/openai/werkzeug).
- **Migration and rollback (verified, gate proof outstanding):**
  `PS-MYOPP-006` is additive, requires `PS-MYOPP-001` through
  `PS-MYOPP-005` (family serial convention), and carries a fail-closed
  rollback (refuses on a later recorded ledger row or any existing C10
  member data) and a catalog verifier — confirmed by
  `MigrationFileContentTests`, which reads all three SQL files as text and
  checks table/trigger declarations, the closed-vocabulary literal set,
  prerequisite guards, drop order, and THROW-number range/uniqueness
  (55840-55899, repo-wide collision-checked) directly against the landed
  files. **TO BE COMPLETED:** the disposable-database gate proof (the
  registry entry's `"gate": null` reflects this honestly, matching the
  C4/C5/C6 precedent) and confirmation that the registry-entry append lands
  under a claim that authorizes it (README "Known limitations" item 7).
- **Status: implementation committed and self-review corrected; freeze,
  gate proof, and independent review remain ahead.** This document states
  the current true state; it is not a claim that this package has closed.
