# Search 3F V3 — Prior Review Resolution

Status values: **fixed** means enforced in V3 code/docs/tests; **bounded** means
the claim is narrowed to its evidence; **separate** means intentionally outside
this non-production package.

| Prior finding | Status | V3 disposition |
|---|---|---|
| Executed API pin contradicted V2's only normative pin | fixed | Historical evidence is explicitly `2024-07-01`; future code is explicitly `2026-04-01`; no V3 execution claim. |
| Census could not see POST bodies | fixed | Pre-dispatch recursive body-key and body-shape census; semantic/vector keys fail before recording/dispatch. |
| Ask Pete digest was hard-coded/not instrumented | bounded | Claim reduced to the three observed counters; schema digest named unverified. |
| Bundle path broke after repository landing | fixed | Paths resolve from repository root; generated fixtures/schema land under the initiative. |
| Default `status` contacted Azure | fixed | Default `plan` and non-executing `teardown` make no HTTP/process call. |
| `select=*`, no public filter, unpinned query type | fixed | Explicit 20-field select, audience/schema filter, `simple/all`, fixed search fields/order. |
| No adaptive over-fetch | fixed | Bounded 20-page/200-candidate paging until six fence survivors or exhaustion. |
| Fence omitted canonical checks | fixed | Owner, local publication, audience, schema, enum, all 19 non-digest fields, and digest equality are enforced. |
| Serializer copied Azure candidate and leaked by subset semantics | fixed | Exact seven-key equality; values constructed only from local manifest. |
| Determinism assertion was dead/two-run only | fixed | Explicit sort plus 50 shuffled-repeat test. |
| README claimed isolated and publisher query 403 | fixed | README states shared exposure and publisher-read limitation. |
| V2 status said no Azure action after execution | fixed | V3 status and evidence distinguish authored history, execution, repository candidate, and live state. |
| Stale PSM registry/lane blocker | fixed | Fresh activation/registry flow used from controlled-idle main. |
| F08 permission matrix incomplete | bounded | No isolation claim; dedicated service remains recommendation. Full estate permission proof is required only for a later isolation claim. |
| D-22/D-22a and SDP-OFF namespaces contradicted totals | fixed | One V3 decision table and finite test matrix supersede the parallel V2 registers. |
| Historical cleanup manifest exposed IDs | fixed | It is not copied; only hashes and an identifier-free template are committed. |
| Cleanup deleted only the index | fixed | Exact plan includes roles, index, service principals, and app registrations; fixed-date/hash binding and successful read-only relationship checks precede deletion; absence checks cannot pass on a generic CLI error. |
| Expiry check could block teardown after doing a GET | fixed | No default GET; cleanup timing has no upper refusal and no non-cleanup mutation path. |
| Request counters reset per invocation | fixed | Manifest-bound persistent state survives invocations. |
| `MAX_INDEX_BYTES` unused | fixed | Request bytes are projected and enforced before dispatch. |
| Import created evidence directories | fixed | Imports write nothing; files are written only by explicit builder/execute paths. |
| Bytecode and missing schema polluted bundle | fixed | No bytecode is committed or selected for deployment; complete generated schema is committed. |
| Proof scripts shipped in deployment artifact | fixed | Both exact script sources plus generated `__pycache__` and `.pyc` output are excluded in `azure-pipelines.yml`. |
| `stored:true` contradicted architecture | fixed | V3 records `stored:true` truth and relies on selection/fence/serializer. |

## V3 independent-review correction

| Review finding | Status | Resolution |
|---|---|---|
| Successful empty relationship lists could pass teardown preflight | fixed | Every role assignment, service principal, and application must resolve to exactly one matching row before the first delete. Empty and duplicate matches fail closed; the complete-sequence test supplies the expected principal/application/role relationships. |
| Fifty-shuffle coverage exercised only equal scores | fixed | The shuffle test now varies scores while retaining ties and asserts score-descending, document-ID-ascending order across 50 shuffles. |
| `searchFields` was emitted but not asserted by the request contract | fixed | The contract now pins the exact five-field lexical list and rejects drift. |
| Deployment exclusion was not proven from a produced Azure ZIP | bounded | The CopyFiles exclusions and post-compile artifact-selection regression prove the repository contract. A produced pipeline ZIP is separately verified as release evidence and is not claimed by this non-deployed candidate. |
| Wall-clock ceiling is invocation-local; import-write test was shallow | bounded | Architecture now says the wall-clock limit is invocation-local, while request/byte/document counters persist. The import test now launches both scripts in a clean temporary working directory and proves they create no files there. |
| Restore of canonical 20 was not evidenced | bounded | Historical omission is retained; no restore claim is added. |
| Two withdrawal timings were prose-only | bounded | Not used as V3 evidence or threshold proof. |
| Cost stated too strongly | bounded | V3 says capacity unchanged historically; usage dollars not assessed. |
| Member block/disconnect and deployed authorization absent | separate | Future member-facing Gate L2 package must implement server-derived identity and relationship authorization. |
| Keys enabled, CMK noncompliant, semantic service setting, Ask Pete knowledge source | separate | Existing shared-service facts; V3 neither changes them nor calls them proof of public-search isolation. |
| Alias endpoint incompatible with 2024 pin | separate | V3 uses no alias contract and makes no alias evidence claim. |

## V3 R2 independent-review correction

| Review finding | Status | Resolution |
|---|---|---|
| Scoped Azure CLI role queries combined `--scope` with incompatible `--all` | fixed | Both preflight and absence-verification commands now use the valid exact-scope form, and the complete teardown regression pins all four command vectors exactly. |
| Compile-before-copy could select proof-tool `.pyc` files | fixed | CopyFiles excludes all `__pycache__` directories and `.pyc` files. The regression compiles both proof tools, applies the pipeline selection patterns, and proves neither source nor generated bytecode is selected. |

No declared defect is treated as rediscovered novelty. The unresolved items are
either honestly bounded historical limitations or separate prerequisites for a
future member-facing/isolated service package; neither is silently called Pass.
