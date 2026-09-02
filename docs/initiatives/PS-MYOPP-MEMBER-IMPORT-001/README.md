# PS-MYOPP-MEMBER-IMPORT-001 — C10 member paste/upload import path

This Protected child implements the accepted My Opportunities C10 outcome:
the permanent private `member_import` path — deterministic paste and
document-upload intake under the shipped bounded-intake discipline
(PDF/DOCX/plain text, magic-byte sniff, streaming cutoff), a deterministic
sanitize/extract pipeline that records the doc 06 §2 closed outcome states
per stage (never AI), provenance held only inside the owner-scoped record,
identical not-found owner isolation, export and member delete via
body-removal tombstones, dual retention (member lifecycle plus rights at
point of use), content-free audit (host class + reason code only), the
API/UI seams C8 integrates against, the prebuilt **disabled** service-level
URL-fetch port, and the additive governed `PS-MYOPP-006` migration with
rollback, verifier, and registry entry. This is the tenth child of the My
Opportunities program (doc 14 "### C10").

This document records the accepted scope and plan. The service module, test
suite, and `PS-MYOPP-006` SQL trio were built three-wide from the shared
`C10_ARCHITECTURE.md` blueprint by three parallel writers in this worktree
and are committed on this branch (implementation commit `18e49f75`, "Implement
PS-MYOPP-MEMBER-IMPORT-001 (C10): member import service, PS-MYOPP-006 trio,
docs"). A subsequent self-review scan found and corrected three defects
against that commit (a PDF content-stream-bomb memory bound that materialized
the full decoded stream before checking it, `sanitized_text` not being
HTML-escaped despite its name implying that guarantee, and this pair of docs
having gone stale relative to the committed candidate); the corrections are
staged in this worktree, not yet committed, pending the writer's freeze pass.
`OWNER_TECHNICAL_COMPLETION_REPORT.md` in this directory carries the current,
honestly-marked state, including exactly what remains **TO BE COMPLETED**
(the disposable gate proof, the `SQL FIles/Migrations/registry.json` entry
append, and the final frozen SHA plus independent-review outcome) versus what
is now true and verified.

## Outcome

Per the activated claim (`docs/governance/lane_claims/PS-MYOPP-MEMBER-IMPORT-001.json`)
and the implementation blueprint, this package delivers:

- `services/my_opportunities/member_import_service.py` — the closed
  vocabulary (intake methods, the nine doc 06 §2 outcome states, closed
  reason-code pairings, record states, body-removal reasons, rights
  obligation classes, non-identifying host classes), the record shapes
  (`MemberImport`, `ImportStageOutcome`, `ImportReceipt`, `ValidatedUpload`,
  `FetchResult`, `MemberImportAuditEvent`), the `MemberImportRepository` /
  `RightsObligationReader` / `FetchAdapter` / `AuditSink` Protocols and their
  in-memory reference implementations, the pure decode/parse/extract
  pipeline functions, `MemberImportService` (paste/upload intake, the
  disabled fetch port, owner reads, delete, export, idempotency purge), and
  the doc 09 §4 unknown-outcome blind-retry lockout.
- `tests/test_my_opportunities_member_import.py` — groups A-J: the doc 16
  §3 unconditional rows, pipeline outcome truth per closed state·reason
  pair, the fetch port's downstream proof via an injected test double
  (C13 pre-proof), idempotency, cross-member negative proofs, export/
  delete/dual-retention, the unknown-outcome write discipline, a
  content-free audit sweep, migration file-content byte-equality checks,
  and structural stops (no Flask/requests/anthropic import, no
  `member_url_fetch_service.py` file, no C2-C6 file touched).
- The additive, governed `PS-MYOPP-006` migration
  (`dbo.myopp_member_imports`, `dbo.myopp_member_import_stage_outcomes`,
  `dbo.myopp_member_import_idempotency` and their guard triggers), its
  fail-closed rollback, its catalog verifier, and the repository registry
  entry (pre-proof, `"gate": null`) — see "Known limitations" for the
  surface-claim status of `SQL FIles/Migrations/registry.json` itself.

## Scope exclusions (hard)

- **No HTTP route.** `POST /my-opportunities/import/url`, its
  `app.py`/config/rate-limit rows, `_allow_bounded_document_upload`
  registration, the flag-gated URL affordance, and every template are C8
  surfaces (doc 14 "### C10"). C10 owns no HTTP route; the six public
  service commands plus the closed `_failure_message` map and outcome-state
  rendering rule are the seam contract C8 binds against without touching
  C10 files. **`MemberImport.sanitized_text` is plain text that is already
  HTML-escaped** (`html.escape()` applied after tag-stripping, before the
  truncation cap — a 2026-09-01 self-review correction; see the
  `OWNER_TECHNICAL_COMPLETION_REPORT.md`); C8 must still apply its own
  render-time output-escaping discipline when displaying it — escaping at
  write time is defense in depth, not a license to treat this field as
  pre-vetted "safe" markup to insert raw.
- **No fetch capability, no `member_url_fetch_service.py` file.** That
  module is reserved for the distinct future child C13
  (`PS-MYOPP-URL-FETCH-001`, doc 14). Per REC-08 (doc 15 §2, "architecture
  accepted; enablement deferred," accepted 2026-08-24): if Pete ever enables
  member-URL fetch, it arrives only as C13 — a service-only late
  integration through C10's prebuilt disabled port and C2's `safe_outbound`
  validator, gated by the proposed `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED`
  alongside the parent surface flag `PEERSLATE_MY_OPPORTUNITIES_ENABLED`,
  reopening no closed ownership, and staying separate from the Slate's
  existing link intake. C10 ships this port **disabled**: it resolves
  `member_url_fetch_service.create_fetch_adapter()` only when both flags
  are true and the module imports and exposes that callable; in every other
  case — either flag off, or the module absent/unresolvable — it raises the
  truthful, recoverable `url_fetch_unavailable` outcome with reason
  `surface_flag_off` / `fetch_flag_off` / `adapter_absent`, and the URL
  itself is never recorded or audited on refusal. A structural test asserts
  `member_url_fetch_service.py` is absent at the C10 candidate; C10 must
  never create it — claiming or creating that module would recreate the
  closed-ownership collision REC-08's accepted design exists to avoid.
- **No promotion of any import to shared inventory** (doc 02 §3 invariant
  8): "Member imports never become inventory. A `member_import` never
  produces a shared receipt, listing, version, canonical opportunity, index
  document, or any cross-member-visible content... No pipeline, correction,
  or operational action may promote one." This is a tested stop control,
  not only a design statement.
- **No change to any C2-C6 file**: `canonical_service.py`,
  `criteria_service.py`, `interpretation_service.py`,
  `retrieval_service.py`, `search_worker.py`, `index_projection.py`,
  `index_fence.py`, `qualification_service.py`, `evidence_port.py`,
  `relationships_service.py`.
- **No deployment, enablement, or production/staging schema action.** The
  `PS-MYOPP-006` migration, rollback, verifier, and registry entry are
  repository candidate artifacts only; merge will not apply schema, deploy,
  enable, or contact a provider. A disposable migration-gate database
  proof runs under Pete's recorded C4-C9 envelope authorization, which is
  not this file's authority.

Domains: `runtime:my-opportunities:member-import`,
`schema:my-opportunities:member-import`,
`privacy:my-opportunities:member-import`,
`governance:initiative:my-opportunities:member-import`,
`governance:package-registry:my-opportunities:member-import`. No
`consequential-ai:` domain — extraction is deterministic tooling, never AI
(doc 06 §2; doc 08 §1 matrix row).

## Authorities

- Doc 06 §§1-4, 6 — network boundary (if fetching is ever enabled),
  parsing/sanitization and the nine closed outcome states, provenance/
  retention/authorization, useful non-fetch and error behavior, proof
  obligations
- Doc 02 §1 (object catalog), §3 invariant 8 (member imports never become
  inventory), §4 (retention and cleanup ownership — the `member_import` row:
  "member lifecycle **and** content rights at point of use"), §6 (storage
  and migration ownership, REC-02-gated)
- Doc 08 §§1, 2, 4, 5, 7 — owner/record/action matrix, authorization-before-
  retrieval, content-free audit exclusions, retention/export/delete, the
  negative multi-member proof obligation (explicitly named for C10)
- Doc 09 §§3-4 — bounded async/idempotency pattern, the uniform failure
  anatomy, and the "distinguish known refusal from unknown outcome" blind-
  retry lockout
- Doc 12 §3 — budgets/ceilings as the enforcement-point authority for the
  per-member active-import ceiling (the value itself is a writer-level
  default, below)
- Doc 14 "### C10" — outcome, reservations, risks, stop controls, and the
  completion rule
- Doc 15 §2 REC-08 (accepted 2026-08-24, "architecture accepted; enablement
  deferred") — the design-B fetch-port shape, and the safe-deferrals row
  naming whether member-URL fetch is enabled at all, permitted source
  classes, and retention rights as C13-activation-gated, not C10's to
  decide
- Doc 16 §3 traceability rows: oversized/mislabeled content, parsing
  failure/parser bombs, sanitized source display, the direct/manual path
  green when import or company context is unavailable, and URL import
  unavailable (C10's service-level port + C8's route/UI + C13's enable/
  rollback proof)
- Precedent mirrored throughout: C5 (`qualification_service.py`, the closed
  `PS-MYOPP-003` trio), C6 (`relationships_service.py`, the closed
  `PS-MYOPP-005` trio, `docs/initiatives/PS-MYOPP-RELATIONSHIPS-001/`), and
  the shipped v2 bounded document-intake convention
  (`services/my_opportunities/opportunity_source_intake_service.py`)
- Implementation blueprint: `C10_ARCHITECTURE.md` (§§1-7), prepared against
  Azure `origin/main` `a9fb5f613015c82d0fe9c2e83d17c9797665975a`; the
  activated claim's `activated_from_main`
  (`fe3a9d2087097d47d3c65b55876c0db643928f3a`) is later, reflecting the
  intervening C6 close and Settings domain-ledger package the blueprint
  named as C10's activation preconditions (see "Known limitations" for what
  that package's close did and did not hand back to this claim)

## How to run the tests

```bash
python3 -m unittest tests.test_my_opportunities_member_import -v
python3 -m unittest tests.test_my_opportunities_relationships tests.test_my_opportunities_retrieval tests.test_my_opportunities_qualification tests.test_my_opportunities_criteria tests.test_my_opportunities_canonical tests.test_my_opportunities_ingestion tests.test_my_opportunities_safe_outbound -v
```

The first command is this package's own suite; the second is the existing My
Opportunities regression set it must not break. Both were run directly
against the corrected candidate in this worktree: this package's own suite
is 127 tests, 1 skipped (`RegistryEntryTests.test_registry_entry_shape_and_requires_chain`
— honest, not a defect: the `PS-MYOPP-006` entry has not yet been appended to
`SQL FIles/Migrations/registry.json`, per "Known limitations" item 7 below;
every other Group I test runs for real against implementer B's already-landed
SQL trio, not merely against the blueprint text) and 0 failures; the
regression set is 329 tests, 0 failures. Exact tallies, per-group counts, and
the self-review correction detail belong in
`OWNER_TECHNICAL_COMPLETION_REPORT.md`, updated there first-hand rather than
duplicated here.

## Approved writer-level defaults (recorded as decisions)

Per the blueprint's owner-decision review (§6): none of C10's implementation
needed a new owner decision — REC-08 already settled the fetch shape, and
everything else is implementation under already-accepted architecture.
Three operational values are recorded here as **writer-level defaults, not
owner questions**:

1. **Per-member active-import ceiling: 200, env-tunable**
   (`MYOPP_IMPORT_MAX_ACTIVE_PER_MEMBER`). The enforcement point is fixed by
   doc 12 §3; the value is operational. Exhaustion refuses truthfully
   (`import_limit_reached`), never silently drops a submission.
2. **20,000 UTF-16-unit paste and extraction cap**
   (`MAX_PASTE_UTF16_UNITS` / `MAX_EXTRACTED_TEXT_UNITS`), reusing the
   shipped v2 bounded-intake discipline's existing `MAX_SOURCE_TEXT_UNITS`
   convention verbatim rather than inventing a new limit.
3. **Member delete is tombstone, not hard delete.** Dictated by doc 02 §4's
   tombstone discipline for `member_import`: deleted with the member and
   individually deletable at any time, with retention honoring both the
   member-lifecycle driver and content-rights-at-point-of-use. Full row
   erasure awaits a governed erasure migration — see "Known limitations"
   item 1.

If the independent reviewer disagrees with any of these three, that is
review correction, not an owner gate (blueprint §6).

## Known limitations and forward obligations

Recorded truthfully; none may be silently forgotten.

1. **Erasure-path gap continues** (the same recorded limitation as C5's and
   C6's tables, extended to C10). All three `PS-MYOPP-006` tables
   (`myopp_member_imports`, `myopp_member_import_stage_outcomes`,
   `myopp_member_import_idempotency`) are designed delete-blocked with no
   erasure carve-out, while doc 08 §5 requires member-side deletion on
   account deletion. Member-initiated delete is body-removal tombstoning
   only; full row erasure awaits the same future governed erasure package
   already recorded against the C4/C5/C6 tables, expected before real
   member data exists in any of them (C9 era).
2. **Rights-obligation source is unbuilt.** The point-of-use enforcement
   seam (`RightsObligationReader`) ships with a none-reader that always
   answers `RIGHTS_NONE`; no real content-rights obligation source exists
   yet. The enforcement *point* is C10's; the obligation *source* is a
   later package's obligation.
3. **The verifier attests schema shape, not behavior** (C4/C5/C6 wording,
   restated) — behavioral proof is the disposable migration-gate database
   run plus the P-1 suite.
4. **No HTTP surface.** The route, UI, upload-override row, rate-limit
   rows, and flag-gated URL affordance (no dead chrome) are C8 surfaces,
   proven at C8, not here.
5. **The account-export reader for this domain is a separate later claim.**
   The Settings-ledger export family will need to read `member_import`
   records into the account-wide export payload; C10 ships only the
   service-level `export_imports()` payload it will need, not that reader.
6. **The doc 09 §4 unknown-outcome lockout is per-process in-memory state**
   on the service instance — carried forward because the blueprint's
   `_check_not_locked`/`_lock_unknown_outcome`/`_clear_unknown_outcomes`
   helper trio is copied verbatim in semantics from C6 (this is the same
   limitation C6's README records as its own item 13). A single-process
   deployment behaves exactly as documented: a failed write locks that
   `(user_key, idempotency_key)` pair until a successful owner read clears
   it. In a multi-worker deployment, a lock armed on one worker is
   invisible to the others. Threading a shared-store lockout through this
   mechanism remains a C8/C9 composition-era obligation, not something
   this package's reference implementation or SQL schema currently
   provides.
7. **Registry-entry-pending: two registry surfaces are not yet claimed by
   this package.** `docs/governance/PACKAGE_REGISTRY.json` is not in the
   activated claim's `surfaces` list — per the blueprint (§1.1) and the
   C5/C6 precedent, its `"PS-MYOPP-MEMBER-IMPORT-001"` entry (in
   `categories.future_finish`) is added only at freeze, through the
   separate extend-surfaces control transition, exactly as C6 extended for
   the same file (`docs/governance/lane_claims/PS-MYOPP-RELATIONSHIPS-001.json`,
   commit history "Extend PS-MYOPP-RELATIONSHIPS-001 surfaces:
   PACKAGE_REGISTRY.json"). More notably, **`SQL FIles/Migrations/registry.json`
   itself is also absent from this claim's activated `surfaces` list**,
   even though the blueprint's §1.1 explicitly names it as a C10 surface
   and §4.4 drafts the exact entry this package needs to append. The file
   was held by the just-closed `PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001`
   package (the "Settings domain-ledger package" the blueprint's activation
   checklist names as a C10 precondition) and is free on `origin/main` as
   of this writing, but this claim does not yet list it as a surface it may
   write. Appending the `PS-MYOPP-006` entry to it will need the same kind
   of extend-surfaces control transition as `PACKAGE_REGISTRY.json`. RESOLVED:
   both surfaces were added via extend-surfaces control transitions after the
   Settings domain-ledger package released the migration registry; the
   `PS-MYOPP-006` entry (with its recorded disposable-gate proof) and the
   `PACKAGE_REGISTRY.json` line are on the frozen candidate.

8. **BINDING pre-enablement obligation — verify the child memory cap enforces
   on Linux (independent review round 5).** Untrusted PDF/DOCX parsing runs in
   an isolated child process; the parent worker's memory is bounded
   unconditionally (a runaway child lives in its own address space, reclaimed
   on exit, and its death maps to a truthful refusal). The child additionally
   caps its own footprint via `RLIMIT_AS`/`RLIMIT_DATA` (256 MiB) — which
   enforces on the Azure App Service **Linux** runtime but **not** on a macOS
   dev host (a Darwin limitation, verified and disclosed). Because the
   parent-isolation guarantee holds without rlimit, this is not a merge gate,
   but before the feature flag is enabled for real members, CI on the Linux
   runtime MUST prove a child exceeding 256 MiB is killed and mapped to
   `parser_resource_bounds` — otherwise a malicious upload can transiently
   pressure host memory (child footprint, not the worker). This obligation
   belongs on the PS-OPS enablement checklist alongside the erasure-path gap
   (item 1) and the shared-store lockout (item 6).

9. **Concurrency/operational footprint (for C8 route wiring and PS-OPS).**
   Each PDF/DOCX upload spawns a subprocess (up to 256 MiB on Linux) and
   blocks the calling worker up to the wall-clock deadline (~70 ms typical
   for a real document). Weigh the concurrency footprint and the
   worker-model (gevent/threaded) interaction when C8 wires the route, and
   ensure the child interpreter has `pypdf` available (a missing dependency
   fails closed to a refusal, never a crash).
