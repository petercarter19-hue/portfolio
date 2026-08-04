# Disposable x64 SQL CI Diagnostic Architecture Amendment

- **Initiative:** `PS-COMMUNITY-PUBLIC-PILOT-001`
- **Path:** Protected
- **Status:** Diagnostic classification authority for one bounded correction
- **Scope:** Content-free failure localization for the existing disposable SQL proof

## Run 339 remains immutable failure evidence

Azure DevOps run `339` at exact source
`14f8ebe85ff8a4c6f8ab56fe221fced7fc01da1c` remains a truthful failed proof.
Its sealed record reported `external_command_failed`, no completed database
proof step, and exact cleanup success. Its downloaded evidence remains under
`evidence/2026-08-02-disposable-sql-proof/run-339/`; it must not be replaced,
rewritten, reclassified as a pass, or used as migration runtime evidence.

Run 339 proved the manual source/branch/agent guard, content-free evidence
sealing, artifact upload, and job-owned cleanup. It did not prove SQL image
identity, client construction, SQL readiness, any forward migration,
idempotency, verification, rollback, or database cleanup. An absent step means
not assessed, not that the step did not execute.

## Finite outer-command classification

Every checked outer command must supply one boundary from this table. Command
failure may produce only the three codes shown for that boundary.

| Boundary | Checked operation | Allowed failure codes |
|---|---|---|
| `source_head` | Read checked-out `HEAD` | `source_head_unavailable`, `source_head_timeout`, `source_head_nonzero` |
| `source_status` | Confirm the worktree is clean | `source_status_unavailable`, `source_status_timeout`, `source_status_nonzero` |
| `docker_info` | Read Docker server identity | `docker_info_unavailable`, `docker_info_timeout`, `docker_info_nonzero` |
| `sql_image_pull` | Pull the pinned SQL tag for digest resolution | `sql_image_pull_unavailable`, `sql_image_pull_timeout`, `sql_image_pull_nonzero` |
| `sql_digest_inspect` | Inspect SQL repository digests | `sql_digest_inspect_unavailable`, `sql_digest_inspect_timeout`, `sql_digest_inspect_nonzero` |
| `client_image_build` | Build the isolated client from its pinned base | `client_image_build_unavailable`, `client_image_build_timeout`, `client_image_build_nonzero` |
| `client_image_inspect` | Resolve the built client content ID | `client_image_inspect_unavailable`, `client_image_inspect_timeout`, `client_image_inspect_nonzero` |
| `network_create` | Create the job-private internal network | `network_create_unavailable`, `network_create_timeout`, `network_create_nonzero` |
| `sql_container_start` | Start the pinned SQL container | `sql_container_start_unavailable`, `sql_container_start_timeout`, `sql_container_start_nonzero` |
| `sql_container_identity` | Inspect the SQL container ID | `sql_container_identity_unavailable`, `sql_container_identity_timeout`, `sql_container_identity_nonzero` |
| `sql_container_network` | Inspect the SQL container network binding | `sql_container_network_unavailable`, `sql_container_network_timeout`, `sql_container_network_nonzero` |
| `client_proof` | Execute the immutable client artifact | `client_proof_unavailable`, `client_proof_timeout`, or the client-report rules below |

The SQL readiness loop retains its bounded retry semantics. Failure to execute
the readiness command is `sql_readiness_unavailable`; an individual command or
the overall bounded readiness window expiring is `sql_readiness_timeout`.
Existing contract failures such as digest mismatch, unexpected container
identity, and SQL readiness failure keep their specific content-free codes.

The implementation must never derive a diagnostic code from command text or
output. It selects the boundary before invocation and maps file-not-found,
timeout, and nonzero exit to the fixed suffixes above.

## Safe client failure preservation

The client container must be invoked without automatically discarding a
nonzero result. On nonzero exit, the outer harness may parse stdout only as a
bounded UTF-8 JSON object and may preserve only
`inside_<allowlisted_code>`. The JSON must have exact allowlisted keys, report
`status=fail`, `contains_member_data=false`, and `production_action=false`, and
contain one code from this finite child allowlist:

- `mode_requires_container`
- `mode_requires_ci`
- `community_flag_must_remain_false`
- `preexisting_sql_connection_forbidden`
- `sql_host_not_job_local`
- `proof_id_invalid`
- `sql_machine_binding_invalid`
- `sql_network_binding_invalid`
- `source_sha_invalid`
- `proof_environment_invalid`
- `migration_runner_import_failed`
- `sql_job_local_name_resolution_failed`
- `sql_job_local_address_mismatch`
- `sql_source_files_unreadable`
- `sql_tcp_unreachable`
- `sql_connect_failed`
- `sql_connect_failed_tls_only`
- `sql_identity_query_failed`
- `sql_machine_identity_mismatch`
- `sql_build_or_edition_unexpected`
- `preflight_unexpected`
- `database_setup_unexpected`
- `empty_forward_unexpected`
- `empty_forward_ps_plat_001` … `empty_forward_ps_plat_007`,
  `empty_forward_ps_auth_001`, and
  `empty_forward_ps_community_public_pilot_001` — one code per forward
  migration file, derived only from the public repository filename prefix, so
  a failed forward pass names the exact file (2026-08-03 amendment after run
  392 reached `empty_forward` and the single bucket could not say which of
  nine files failed)
- `forward_idempotency_unexpected`
- `two_owner_verifier_unexpected`
- `empty_rollback_unexpected`
- `populated_rollback_refusal_unexpected`
- `database_cleanup_unconfirmed`

The outer evidence code prefixes the accepted child code once, for example
`inside_empty_forward_unexpected`. Missing, oversized, malformed, additional,
or non-allowlisted client output becomes
`client_proof_invalid_failure_record`; raw output is discarded. A zero client
exit still requires the existing complete passing evidence contract.

**Amendment, 2026-08-03 (Claude, Community writer).** Runs 344, 351, and 382
all sealed `inside_preflight_unexpected`, which proved only that *something*
in preflight raised a non-allowlisted exception. That bucket spans three
materially different conditions — unreadable reviewed SQL files, a driver
load/TCP/TLS/authentication failure, and a failed server-identity read — so a
failed preflight could not be diagnosed without guessing. Each now carries its
own content-free code (`sql_source_files_unreadable`, `sql_connect_failed`,
`sql_identity_query_failed`). The exception detail is discarded in every case;
only the finite token is recorded. `preflight_unexpected` remains for anything
still unclassified.

The sealed failure code is additionally echoed to the build log by the seal
step. A PipelineArtifact download requires a personal access token, so the one
value each run exists to produce was unreadable to the operator diagnosing it.
The code is finite, content-free, and already inside the sealed evidence, so
printing it discloses nothing further.

**Amendment, 2026-08-03 (second): bounded message tokens for the
empty-forward stage only.** Six runs sealed codes that could not identify the
failing statement inside the 1,786-line Community migration; every finite
refinement (per-file codes, allowlisted error numbers, THROW-message mapping,
engine phrases, exception classes) was exhausted. For the `empty_forward`
stage only, the per-file code may append `_m_<token>`, where the token is the
driver message lowercased, reduced to `[a-z0-9_]`, and truncated so the whole
code stays within 80 characters. This is sound because at that stage the
database is empty: no member content, synthetic content, credential,
environment value, or connection string exists that a server message could
carry — the message can only derive from the public repository DDL being
applied. The outer parser accepts the `_m_` family only when prefixed by a
known per-file forward code; all other stages remain strictly finite.

Unexpected child exceptions must bind to exactly one finite proof stage:
`preflight`, `database_setup`, `empty_forward`, `forward_idempotency`,
`two_owner_verifier`, `empty_rollback`, or
`populated_rollback_refusal`. Database and container cleanup remain
unconditional. A cleanup failure remains authoritative and cannot be hidden by
an earlier diagnostic.

## Privacy and evidence boundary

Diagnostics may contain only the finite code, existing pass/fail step records,
bounded durations, and already approved source/image/agent identities. They
must never record or print command arguments, stdout, stderr, environment
values, credentials, connection strings, synthetic content, member content,
database results, container logs, paths to private environment files, or raw
exception text.

The current source binding, pinned images, private internal network, no-port,
no-mount, synthetic-only execution, feature-default-off rule, evidence
allowlisting and hashing, and exact unconditional cleanup remain unchanged.
Focused tests must cover every outer mapping, safe nonzero client-report
preservation, every unexpected child-stage binding, malformed-report refusal,
and the absence of command output or secrets from evidence.

## Authorized second-run gate

Pete's 2026-08-02 “go” authorizes exactly this sequence:

1. implement only the diagnostic mappings and focused tests defined here;
2. complete local validation and Protected review;
3. commit and push one clean, reviewed exact SHA on the existing Community
   feature branch; and
4. queue exactly one new manual, source-bound execution on the existing
   triggerless disposable proof definition, then download and verify its sealed
   evidence.

The queued branch, `--commit-id`, `expectedSourceSha`, checkout `HEAD`, and
reported evidence SHA must all equal that one reviewed SHA. Stop before queueing
if local tests or review fail. Stop after the single run whether it passes or
fails; a third run is not authorized. Do not delete the existing pipeline
definition or alter run 339 evidence.

This amendment authorizes no change to SQL, migrations, schema, verifier
meaning, proof sequence, pipeline topology, image pins, network isolation,
feature flags, service connections, providers, retention, Candidate,
production data or resources, PR, merge, release, or deployment behavior.
