# FAILED SAFE / NOT ACCEPTED — C5 Gate 10 account export live proof

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-GATE-10-001`
**Owner authorization:**
`pete-chat-2026-09-02/settings-account-export-gate-10-enable-and-proof`
**Repository authority:** governance evidence through merge
**Production authority at closeout:** withheld
**Verdict:** **FAILED SAFE / NOT ACCEPTED**

Gate 10 did not earn acceptance. An earlier bounded run advanced exactly two
disposable synthetic members through successful sign-in and account-export
generation, and SQL later confirmed exactly two jobs in `ready`, each with a
final-artifact reference. The controller then refused during its combined
post-ready browser isolation/download phase. Because that phase did not identify
the failed assertion, the run does not prove download, bidirectional isolation,
or the rest of the Gate 10 browser matrix.

A later, independently reviewed V4 one-shot did not recreate those members or
jobs. It failed closed earlier, in a coarse `browser_preflight` phase, with zero
accounts and zero jobs. V5 improved offline observability only and did not grant
another live attempt. This record supports closing the package as an accurate
unsuccessful proof record; it does not recast either run as a Gate 10 pass.

## Evidence boundary

This closeout uses only the previously captured, content-free operator records
and frozen local manifests. No application-production Azure, browser, identity,
firewall, schema, deployment, grant, job, feature-flag, or production call was
made to prepare this document. Consequently, all live-state statements below
are explicitly historical and time-bounded. They must not be read as a fresh
assertion about current production state.

No password, address, directory object identifier, token, archive content, or
member content is retained here. The temporary passwords used by the earlier
run existed only in its process memory. No personal account was used.

## Earlier bounded partial run

The earlier run's content-free records establish the following sequence on
2026-09-02 UTC:

1. Precreation and exact-absence checks passed. Exactly two new disposable
   identities were created, and four isolated browser clients were active.
2. Both synthetic members completed the CIAM sign-in flow, including declining
   session persistence. The application created exactly two distinct export
   jobs.
3. The controller exited 2 with:

   ```json
   {"accounts_created":2,"error_type":"RuntimeError","jobs_created":2,"phase":"browser_isolation_download","reason":"closed_refusal","stage":"failed"}
   ```

4. A bounded SQL check then returned:

   ```json
   {"artifact_references":2,"backdated_exact":2,"cleanup_states":["pending"],"jobs":2,"result":"pass","states":["ready"]}
   ```

   This proves export generation reached SQL `ready` for both synthetic jobs.
   It does not identify or satisfy the failed post-ready browser assertion.
5. The exact cleanup path returned:

   ```json
   {"cleaned_artifacts":2,"domain_rows_deleted":60,"download_metadata_refusals":2,"expired_jobs":2,"job_rows_deleted":2,"mapping_retirement":{"counts":{"disallowed_references":0,"eligible_members":2,"identity_mappings":2,"member_profiles":2,"workshop_items":0},"result":"pass","state":"retired"}}
   ```

6. The final bounded database check reported zero active application users,
   zero active identity mappings, zero active profiles, zero export jobs, and
   zero export-domain rows. It also reported two closed application users, two
   retired identity mappings, and two inactive profiles.
7. The exact two directory identities were **soft-retired only**. The final
   structural directory check found each absent from the active directory and
   present once in Deleted applications. They were not permanently deleted.
8. At the final historical containment check, the export flag was absent, the
   signed-out export route returned 404, health returned 200, the four browser
   contexts were closed, no bounded export artifacts remained in the live
   namespace, and the SQL firewall rules were exactly
   `AllowAllWindowsAzureIps` and `Home Internet Address`.
9. The disposable local controller, state, browser-runtime, and SQL-environment
   roots were moved to Trash. That was a recoverable local retirement, not a
   claim that the user's Trash was emptied or the files were irreversibly
   destroyed.

The cleanup evidence is a terminal record for that run, not proof that these
conditions remain current after 2026-09-02.

## EXPORT-010 rollback-window disposition

The repository contract for `PS-SETTINGS-EXPORT-010` states that
`dbo.usp_CompleteAccountExportWithDomains` inserts the canonical 30 domain rows
and transitions the parent job to `ready` in one transaction. The bounded run
subsequently observed two `ready` jobs and deleted exactly 60 bounded domain
rows during cleanup.

Under the accepted Gate 10 rule that the rollback window closes when the first
real member export completes, those two ordinary synthetic-member completions
close the **EXPORT-010 rollback window**. This is a rule-based governance
inference from the recorded job and ledger facts; it is not an inference that
Gate 10 passed, that either browser download succeeded, or that any personal
member account was exercised. Later cleanup of the bounded rows does not reopen
the governance window.

## Later V4 one-shot: failed before identity creation

The exact V4 integration manifest had SHA-256
`7cb10762891a9834766ced5f5ba638d287a3256a8add03c79ff2036f65ed62c1`.
`agent:/root/owner_home_retirement` independently returned CLEAR at
`2026-09-03T01:46:57Z` for that exact frozen integration candidate.

The one allowed V4 invocation used run id `ps-exp-g10-20260903-v4`, consumed
its canonical attempt marker before remote preflight, exited 2, and emitted:

```json
{"accounts_created":0,"jobs_created":0,"phase":"browser_preflight","reason":"closed_refusal","stage":"failed"}
```

V4 therefore created no password, identity, application mapping, export job, or
canonical containment-state file. It performed no hard deletion. Its CLEAR
review means the frozen controller matched its reviewed fail-closed contract;
it does not turn the failed live result into acceptance.

The canonical attempt marker remains immutable at
`/private/tmp/peerslate-gate10-live-attempt-PS-SETTINGS-ACCOUNT-EXPORT-GATE-10-001.json`:
mode `0600`, 192 bytes, SHA-256
`32daa75617474476b113196c8ed1441e12d2c4c8c6dedefa42d7de5a34c8fbcc`,
status `consumed_before_remote_preflight`. The canonical V4 state file was
absent because the failure preceded identity creation.

### Truthful V4 cause boundary

V4's `browser_preflight` label covered six operations: authority resolution,
browser-session preparation, browser proof, context binding, baseline
construction, and exact baseline verification. Its output cannot establish
which operation refused.

An offline adapter environment/residue preflight passed without launching a
browser. Two later structural baseline samples differed only at these field
names:

- `worker_job.secretless_msi_sql`
- `maintenance_job.secretless_msi_sql`
- `sql.web_owner_execute_grants`
- `schema.migration_ids`

Those names are repeatable mismatch observations, not causal attribution. No
missing migration identifier, grant count, job environment entry, production
value, browser fact, or credential fact is inferred from them.

## Diagnostic firewall incident

Two post-V4 diagnostic calls mistakenly treated `collect_pre_context` as a
read-only helper. Each call briefly added and removed the exact bounded SQL
firewall rule `CodexGate10BoundedProbe20260902`. This was an unintended
diagnostic mutation and is recorded rather than hidden.

Immediately after the second cycle, the firewall was verified restored to
exactly `AllowAllWindowsAzureIps` and `Home Internet Address`, and all remote
diagnosis stopped. No identity, export job, feature flag, deployment, schema,
grant, content, or hard-delete mutation occurred in those two cycles.

## V5 offline observability correction

The V5 integration manifest had SHA-256
`e91f9b0266297a5ab1d85d9b7e5409fa118add1ac01711fb9ec47d91dcd49337`.
`agent:/root/owner_home_retirement` independently returned CLEAR at
`2026-09-03T02:07:14Z` for observability and evidence only.

V5 replaced the coarse preidentity phase with fixed content-free labels for
authority preflight, browser-session preparation, browser proof, context
binding, and baseline preflight. Its isolated integration suite passed 29/29,
and its dry bootstrap passed with `live_actions=0`. It changed no acceptance,
credential, identity, production-mutation, or cleanup rule. V5 was never run
live and supplied no retry authority.

## Last verified V4 containment state

The following is the last recorded V4 containment state, verified on
2026-09-03 UTC against repository commit
`41541b46fce6db20ca9812f94d1fe253252a1426`; it is not a fresh live check:

- `PEERSLATE_ACCOUNT_EXPORT_ENABLED`: absent/off.
- SQL firewall: exact two-rule baseline named above.
- Gate 10 or browser processes: zero.
- Sealed browser/probe roots: zero.
- V4 and V5 cache roots: absent.
- Canonical V4 state: absent; V4 created no identities.
- Canonical V4 attempt marker: present and unchanged as recorded above.
- Repository: clean at that historical commit.

This V4 containment record is separate from the earlier partial run's exact
soft-retirement record.

## Gate 10 acceptance matrix

| Required outcome | Evidence disposition |
| --- | --- |
| Exactly two disposable ordinary synthetic members | **Partial run proven:** exactly two were created and signed in. V4 created zero. |
| Four fresh isolated browser clients | **Partial run setup proven:** four clients were active and later closed. Full isolation outcome not proven. |
| Exactly two export requests/jobs | **Partial run proven:** two distinct jobs were created. |
| Status reaches `ready` | **Partial run proven:** SQL returned exactly two `ready` jobs with two final-artifact references. |
| Request eligibility and rate behavior | **Not proven by the retained terminal evidence.** |
| Successful member download | **Not proven.** The controller refused inside the combined post-ready isolation/download phase. |
| Bidirectional member isolation | **Not proven.** The failed combined phase does not identify which assertion failed. |
| Foreign-reference refusal | **Not proven as a complete browser criterion.** Two cleanup-time download-metadata refusals do not substitute for the required browser matrix. |
| Deterministic archive/manifest truth | **Not proven end to end.** Reaching `ready` and observing ledger rows is insufficient. |
| Expiry and maintenance | **Partial cleanup proven:** the two exact jobs were backdated, maintenance succeeded, both jobs expired, and two artifacts were cleaned. The complete accepted Gate 10 sequence remains unproven. |
| Content-free logs under the accepted live flow | **Not proven.** |
| Live release, flag, jobs, grants, private storage, schema, and signed-out boundary re-proved together | **Not proven as one accepted baseline.** Historical preflight/cleanup observations cannot be promoted to a fresh current proof. |
| Disable on material failure | **Historically proven for the partial run:** flag absent/off and export route 404 at final containment. V4 also failed before identity creation. |
| Retire the two application identities | **Proven for the partial run:** mappings revoked/closed/inactive with zero active mappings. |
| Irreversible directory deletion | **Not performed and not authorized.** The partial-run identities were soft-retired and remained in Deleted applications at the last exact check. |
| First completed export / EXPORT-010 rollback disposition | **Window closed by rule-based inference** from two `ready` jobs and 60 domain-ledger rows; this is not Gate 10 acceptance. |
| Overall Gate 10 | **FAILED SAFE / NOT ACCEPTED.** |

## Preserved evidence hashes

- Sanitized failed-attempt checkpoint:
  `3170d769041a4ac3f02e9f0c7cb0360e1e4e08d0327ca69f03aa5215c44e973d`
- V4 root-cause boundary:
  `9ace116ad668d2f99fc3b6c66a1c5c928646a9ca668e7087ea9f8e4937586f2f`
- Final offline handoff:
  `ebe541a89476fcb55c119507b94642a66a02b409c44a502f5b4ea0ca68cdf7cc`
- Repository evidence proposal:
  `60bd31fbf741829fe446ff116684b0bd7657759afaad3c875771239c14db3d1e`

These hashes preserve the exact local source records used for closeout; they do
not make `/private/tmp` a durable repository artifact.

## Terminal disposition

Gate 10 remains unaccepted. There is no authority in this package for another
live attempt, reuse or removal of the consumed attempt marker, flag enablement,
new identities or jobs, firewall mutation, deployment, schema or grant changes,
or hard deletion. Any future attempt requires a new claim, a new independently
reviewed one-shot contract, and fresh action-specific production authority.
