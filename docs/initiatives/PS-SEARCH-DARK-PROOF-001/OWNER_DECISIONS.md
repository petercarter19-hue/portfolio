# Search 3F V3 — Closed Owner and Architecture Decisions

These decisions supersede conflicting V1/V2 status blocks and residue labels
without rewriting their historical provenance.

| ID | Decision |
|---|---|
| V3-D01 | Historical execution is bound only to REST API `2024-07-01`. Future V3 builders pin `2026-04-01`. No rerun is authorized or claimed. |
| V3-D02 | The shared Basic service is not isolated. Synthetic-only content and index-scoped proof roles reduce harm; dedicated service remains the isolation recommendation. |
| V3-D03 | V3 is lexical only: `queryType=simple`, `searchMode=all`, no semantic/vector request or configuration. |
| V3-D04 | Query selection names all 20 canonical fields because the fence needs them; browser/public output is a separately constructed seven-field object. `select=*` is forbidden. |
| V3-D05 | `destination` is an allowed public opaque destination token and is constructed from the local canonical projection. Backend IDs are not public output. |
| V3-D06 | Paging is 20 candidates per request, 200 candidates maximum, and 6 public results. Order is score descending then document ID ascending. |
| V3-D07 | Normalization is NFC; query whitespace collapses; aliases are NFC-sorted for digest comparison; absent and null optional period values digest identically; title sort is NFC plus casefold; lowercase wire enums are canonical; unknown fields fail validation. |
| V3-D08 | Ask Pete historical evidence is limited to the three observed counters `118 / 3,120,907 / 355,380`. The stated schema digest was not instrumented and is not a V3 claim. |
| V3-D09 | Historical `18/18` and `25/25` are retained as historical labels, not V3 coverage totals. V3 uses the finite test file and `VERIFICATION_MATRIX.md`; `D-22`, `D-22a`, `SDP-OFF-*`, and the parallel V2 namespaces are closed as superseded accounting. |
| V3-D10 | All fields are truthfully `stored:true` and `retrievable:true` in the V3 schema. Privacy depends on explicit selection, a local authorization fence, and a local serializer—not a false storage flag. |
| V3-D11 | Cleanup covers two role assignments, one proof index, two service principals, and two application registrations. Fixed service/date checks, private-ID hashes, and read-only relationship preflight require exactly one matching row per target before deletion. Cleanup remains executable after expiry and cannot extend retention. |
| V3-D12 | The redacted historical cleanup manifest is evidence only and must not be committed because it exposes resource/app identifiers. The committed V3 template contains placeholders only. |
| V3-D13 | No member-facing search, deployed fence, relationship graph, route, UI, Azure mutation, teardown, merge, deployment, or live claim is part of this candidate. Gate L2 remains separate. |
| V3-D14 | Pete requires the detailed independent-review handoff after Search freezes. The later collision-aware lane policy is a separate post-handoff package and cannot change the Search SHA. |
