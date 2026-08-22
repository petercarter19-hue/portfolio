# PS-INTERVIEW-AI-EXTRACT-001 — rollback and release-ordering evidence

## Application code: prior-artifact rollback, telemetry retained (C9)

Ordinary application rollback deploys the prior known-good application
artifact/commit — it never touches the database. Existing telemetry rows
**stay in place** and the 90-day purge keeps operating; telemetry recorded
under a retention promise is never deleted early by a code rollback.
Nothing else on the site imports `services/interview_ai`, so the revert
carries no cross-feature coupling. The parity fixtures prove the extracted
and legacy implementations are byte-equivalent on every member-visible
surface, so the switch is behaviour-neutral for members in both
directions.

## Configuration rollback: D8 only

A configuration-only rollback may select only a prior recorded release set
whose `runtime_core_digest`, `guardian_set_version`, and
`contracts_version` match the running system. Resolution enforces exactly
those conditions against recomputed bytes and current constants, so an
incompatible prior entry is unreachable by construction — adversarially
tested in `tests/interview_ai/test_release_resolution.py`
(`test_configuration_only_rollback_compatibility_is_enforced`). If the
configuration must be withdrawn entirely, unsetting it is fail-closed: the
four Interview AI endpoints answer the frozen 503 with zero provider
dispatch and zero spend while the rest of the site is untouched.

## First-deploy ordering (C8) — for the separately authorized release gate

**Deploying this candidate with `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET`
absent, malformed, unknown, or incompatible is an Interview AI outage by
fail-closed design** — all four Interview AI endpoints answer 503 until
the configuration resolves. The release plan therefore requires, at its
future separately authorized gate, in order:

1. Telemetry schema applied, role permissions bound, and the independent
   purge path ready (migration apply + identity binding + enablement are
   their own governed operations).
1a. Runtime-lock congruence verified (B3): the deployed artifact carries
   the vendored, staged-verified closure, and the operator confirms the
   App Service resolution order serves those verified bytes — the boot
   check fails Interview closed on any drifted, substituted, or
   Oryx-resolved distribution that differs from the lock.
2. The exact candidate and release-set identity verified (byte-lock
   recomputation against the deployed source).
3. Set `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET` to the exact full 64-hex
   recorded release-set id **while the legacy runtime is still deployed**
   — the legacy runtime safely ignores the unknown setting, so this step
   changes nothing observable.
4. Deploy the matching candidate.
5. Verify boot compatibility and the provider-free Interview smoke:
   resolution succeeds, a pre-provider refusal answers exactly as before,
   and the rest of the site is untouched.

This candidate authorizes none of those steps; recording the release set
in `registry.json` (`activated_at: null`) is the only release fact it
creates.

## Schema: gated proposal with a retention-safe rollback (C9)

- `PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql` is registered and **gated**
  (disposable-database proof recorded in `SQL FIles/Migrations/registry.json`;
  gate database `ps-interview-extract-gate-20260820`, deleted after the
  proof). Nothing in this slice applies it, and the application tolerates
  its absence indefinitely (the bounded append fails content-free and the
  member response is unaffected — verified by
  `test_append_failure_never_changes_the_response`).
- The rollback file is **guarded by an empty-table condition**: it refuses
  — loudly, transactionally — to drop a telemetry table that holds any
  rows, naming the retention promise in its error. It may complete only
  against an empty table (a disposable proof database, or an apply that
  was never exercised). Retiring a nonempty production table requires its
  own separately authorized retention-safe schema operation. Both guard
  branches are executably proven in `05_SQL_DISPOSABLE_PROOF.json`
  (`rollback_refuses_nonempty_table`,
  `rollback_completes_against_empty_table`,
  `forward_reapplies_after_rollback`).

## Telemetry after a code revert

Rows already appended simply age out under the 90-day retention; no
rollback path needs to read, rewrite, or delete them (append-only by
design, and nothing member-facing reads the table).

## Consolidated B3 addendum: boot-frozen state and the C8 ordering

The release state is now frozen once per process at boot. This does not
change the C8 configuration-before-deploy ordering — it strengthens it:
setting `PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET` on App Service restarts
the process, the boot initializer re-verifies everything (guarded
manifest, fragments, runtime lock, evaluation manifest), and the process
comes up either `ready` or fail-closed `service_not_configured`. Rolling
back configuration is the same operation in reverse; no running process
ever changes release mid-flight.
