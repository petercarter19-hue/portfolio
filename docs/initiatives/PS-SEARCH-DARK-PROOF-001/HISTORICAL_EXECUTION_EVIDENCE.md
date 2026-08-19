# Search 3F — Historical Execution Evidence Boundary

## Evidence identity

The source evidence remains read-only at:

`C:\Users\peter\Documents\PeerSlate Handoffs\2026-08-16 Search 3F Dark Proof`

The proof executed 2026-08-16 before the second review, on Pete's explicit
sequencing direction. Its runner hard-coded Azure AI Search REST API
`2024-07-01`. Execution-time repository main was recorded as
`30a6e4a37d9a1c622013030fd237cc9310fa5c6f`. V3 neither alters nor reruns it.

| Source file | Bytes | SHA-256 |
|---|---:|---|
| `EXECUTION_EVIDENCE.md` | 5,201 | `a2461f291401b6ed38a76fddc9d5aca1d49bbe05288adbe27870e1f50364b5ab` |
| `execution/battery_results.json` | 1,534 | `b04ec8b2037ae961c064284df7304eb7da9b8d02a36e86afd57c9b35dfe5a674` |
| `execution/final_battery_output.txt` | 947 | `9a0387e4710d66de02b01f3fe26f09060570f08db86e9e593a8b5840ba9e991b` |
| `execution/index_schema_as_created.json` | 8,796 | `a3002e8e493afca206e1507c6467d40a840157e87c1498a6a5203af419a2a94c` |
| `execution/request_census.json` | 3,920 | `1a5a7cdcf85b3a26ff7cdd2866787a3be79e7eb2d7199ec057b6ff2d8dcad95e` |
| `execution/CLEANUP_MANIFEST.redacted.json` | 2,301 | `7f9bc4551ffc0fdd165071007e26be152b2bfdba002da3a5ff8b1c708e04de64` |
| `ask_pete_pre_proof_baseline.json` | 934 | `9ab44897fbb2e6c4508e232f397452591b4adea38727603346cefef2d019cdd0` |
| `askpete_index_baseline.json` | 3,200 | `66988fbb1840cb0d7642fcbadac4624bd4182e2bc815a461badc6c1723e37d15` |

## Supported observations

- A Basic 1-replica/1-partition service accepted the 20-field lexical schema.
- The proof index held 20 synthetic documents and reported vector size zero.
- A rehearsal index was created, deleted, and observed absent.
- Two proof service principals had one recorded index-scoped role each.
- Query-principal upload and unauthenticated query were denied.
- The built-in publisher role could query; this is a separation limitation,
  not a passing publisher-query denial.
- Withdrawal closed in the in-process manifest fence and physical deletion was
  observed in 1.3 seconds. That is an observation, not a platform guarantee.
- The three Ask Pete counters were observed unchanged.
- The battery/result files agree on their historical `18/18` result.

## Unsupported or overstated historical claims

- The request census omitted POST bodies, so it did not prove every request
  lacked semantic/vector options.
- The Ask Pete schema digest was not computed by the runner.
- Two equal query responses did not prove deterministic ordering; the old sort
  assertion was logically dead.
- The shared service and inherited readers mean the index was not isolated.
- The fence and instant hide were operator-local, not deployed authorization.
- The runner's serializer copied Azure fields and was not the V3 serializer.
- Usage cost dollars were not assessed; only service capacity was unchanged.
- The evidence did not record the final canonical-document restore command.
- The historical cleanup helper did not remove role assignments, service
  principals, or application registrations and its redacted manifest exposed
  identifiers.
- The two prose-only withdrawal timings and the full F08 permission matrix were
  not independently instrumented.

## Standing-state statement

The other independent reviewer performed a read-only Azure check on
2026-08-18 and reported the proof index, 20 canonical fixtures, and two proof
assignments still standing, with the rehearsal index absent and Ask Pete's
three counters unchanged. This V3 writer did not re-query Azure. Treat that as
dated review evidence, not current live verification.

The retained-dark decision expires **2026-08-23 23:59 CDT**. Extra standing
time cannot strengthen the historical instruments. Teardown remains the
recommendation unless Pete separately records a new decision.
