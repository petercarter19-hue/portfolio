# PS-OPPORTUNITY-SLATE-001 OS-3 schema-first completion record

Status: **Conditional** until this schema-only branch passes PR validation,
merges, and the governed manual-main apply is approved and verified against
production. It contains no OS-3 route, AI orchestration, or member-facing UI.

## Core record

- **Task/package and delivery path:** PS-OPPORTUNITY-SLATE-001 slice OS-3,
  schema-first **Protected** release through PS-OPS-001.
- **Outcome and member/site effect:** Adds the four OS-3 analysis/response
  tables and four owner-scoped procedures before application code can call
  them. Existing OS-1/OS-2 route behavior is unchanged. The procedure names
  are added to the database allowlist, but the current service remains pinned
  to its thirteen OS-1/OS-2 calls until the OS-3 application PR lands.
- **Branch, base SHA, final SHA, and changed paths:**
  `work/2026-08-04-oppslate-os3-schema-release`, based on governed-path merge
  `98d1565641b6476a85c7a58ff06ec54951c075a9`; final pushed SHA is recorded in
  the PR handoff. Changed paths are the Opportunity Slate forward migration,
  rollback, owner-isolation verifier, migration registry gate proof,
  `services/database_service.py`, the schema-first migration tests, this
  record, and `evidence/os-3/sql-gate-governed.json`.
- **Verification performed and result:** Disposable Basic-tier database
  `ps-oppslate-os3-gate-20260804` on server `peerslate`, production-matching
  collation. Governed gate passed six steps: all ten prerequisites; exact
  forward apply creating 186 objects; idempotent re-apply; verifier returning
  `verified = 1`; rollback of all 186 objects; clean forward re-apply. Exact
  executable SHA-256:
  `752812bd7d290a0d092b9910f44643577f4a2947fc8887627ca2c7639e463a0f`.
  Focused OS-3/path/integration tests: **124 passed, 3 skipped; 299 subtests
  passed**. Repository-wide test run excluding the Windows-inapplicable POSIX
  mode assertion: **2,322 passed, 9 skipped, 1 deselected; 3,106 subtests
  passed**. The unfiltered run produced the same passing body plus the single
  known Windows `0o600` assertion failure; it also exposed an older OS-3
  allowlist snapshot, which was corrected additively and covered by the final
  focused and broad passes.
  Registry check: **23 registered, 11 gated and hash-matched; pass**.
  `git diff --check`: pass.
- **Release state:** Local schema-only branch; production unchanged. The
  disposable gate database was deleted after proof and its absence verified.
- **Protected-path correction after merge:** PR 274 merged the schema at
  `d3af4793734a11502375434b47f5e3b37cd7ee01`. Run 497 exposed invalid CLI
  option ordering before any connection and PR 276 corrected it at
  `304a5ecdd49afc52f7496440b1afdfa64593639e`. Corrected run 501 then reached
  connection establishment and failed closed because a plain hosted-agent
  shell had no usable Entra credential; its log showed
  `DefaultAzureCredential` exhausting every provider. No migration SQL was
  claimed or evidenced as applied. The follow-up change runs only the three
  connected actions inside the existing approved Azure service connection;
  it does not add a password, broaden the SQL firewall, or change migration
  bytes. The service principal client id
  `8948ceff-6f5c-4f88-91cd-aefc6e99fc32` is now mapped to the contained user
  `peerslate-ado-schema`, which was verified as `db_ddladmin` with database
  definition visibility, object-scoped ledger DML, and object-scoped audit
  procedure execution only. It is not a member of a member-data reader/writer
  role or `db_owner`. Final PR, run, and production ledger evidence remain
  pending.
- **Known limits, deferred work, or owner decision needed:** One of the three
  focused skips is deliberate and temporary: the OS-3 service-payload
  assertion cannot run before the service ships. The OS-3 application branch
  removes that skip and restores exact equality between all seventeen
  procedure calls and the allowlist. The other skips are separately
  credentialed engine/path tests.
- **Next action:** Open and merge the schema-only PR, queue a governed
  `schemaAction=apply` run expecting `PS-OPPSLATE-001`, approve the protected
  environment after reviewing the exact plan, then verify the production
  ledger and objects before opening the OS-3 application PR.

## Protected additions

- **Data/privacy/authorization:** Every new procedure derives the owner from
  `@UserKey`, reasserts `owner_profile_id` in its predicates, and accepts no
  caller-supplied owner id. The verifier exercised two-owner negative paths and
  left no residue. No model call or member content was read from production.
- **Migration/rollback proof:** The governed gate used the exact committed
  migration, verifier, and rollback bytes; the updated registry proof matches
  them. Rollback was rehearsed before re-apply. The throwaway database was
  created solely for this gate and permanently deleted afterwards.
- **AI:** OS-3's semantic false-positive limitation was reviewed by Pete on
  2026-08-04 and accepted for the current small, unpromoted demo audience.
  That decision changes no schema guarantee and does not claim the anonymous
  route is access-restricted.
- **Actual handoff:** Pete is release approver. The OS-3 application remains
  on `work/2026-08-04-opportunity-slate-os3`; it must not merge until the
  production schema result is verified.
