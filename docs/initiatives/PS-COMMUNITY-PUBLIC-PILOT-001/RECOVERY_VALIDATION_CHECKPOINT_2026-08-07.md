# Community recovery validation checkpoint — 2026-08-07

This is a pre-candidate recovery checkpoint, not a live claim, release
completion, or permission to skip independent review.

## Source and scope

- Worktree: `/Users/petercarter/portfolio-community-revival-safety-v1`
- Branch: `work/2026-08-07-community-revival-safety-v1`
- Base: `819d348928f73ac3b526801f43dd370b1b6b06c1`
- Community visibility: production flag remains disabled.
- Community maintenance: production control remains disabled/unconfigured.
- Visual scope: no template, CSS, JavaScript, fixture, or locked-authority
  change was made by this recovery.

## Disposable schema proof

The additive `PS-COMMUNITY-REVIVAL-001` plan passed prerequisite, forward,
idempotent reapply, verifier, rollback rehearsal, and forward-after-rollback
checks on disposable Azure SQL database
`ps-community-revival-gate-20260807c`. The database was then deleted and its
absence verified.

- Executable digest:
  `f572fc6f835ae860a304b0f36184ac680110d3ee734c4da94d49bc5fb972360e`
- Gate time: `2026-08-07T14:03:42Z`
- Production schema changed: no

## Automated validation

- Focused recovery and Community suite: 132 passed before identity separation;
  the corrected dedicated-identity/runner/Community subset then passed 120.
- Full relevant Community, Voice, media, migration, provider-boundary, and
  operational-readiness suite: 489 passed.
- Repository-wide suite after installing the repository-pinned local test
  prerequisites: 2,901 passed, 5 intentionally skipped. A prior parallel pytest
  rendering also passed 2,891 tests, 5 skips, and 3,608 subtests.
- Python compilation: passed.
- JavaScript syntax (`static/js/community-v1.js`): passed.
- Dependency integrity: passed.
- Migration registry and gate digests: passed; 27 registered, 15 gated and
  matching.
- Immutable applied baseline comparison: the restored
  `PS-COMMUNITY-PUBLIC-PILOT-001_community.sql` is byte-equivalent to applied
  source commit `0a53edb`.
- Diff whitespace: passed.
- Full working-directory secret scan: passed with no finding.
- Maintenance command default-off result: `{"status":"disabled"}`.
- Explicit enabled dry-run result:
  `{"status":"dry_run","would_run":["media","content","audit","outbox"]}`.
- Wrong or absent production schema state: the deployment gate returned a
  generic blocked result and performed no deployment.
- Dedicated SQL and Blob maintenance authority remains unprovisioned and the
  maintenance gate remains closed; no grant or Blob mutation has occurred.
- Least-privilege plans: one dedicated workload identity with no Azure
  management role or SQL role, exactly five direct janitor-procedure `EXECUTE`
  grants, and one container-scoped `Storage Blob Data Contributor` role; no
  table grant, owner-scoped request procedure, storage-account role, or
  Blob-owner role.
- Hard runtime bounds: the process alarm interrupted an in-flight sweep;
  pinned mssql-python 1.11 cursor propagation, the defensive cursor contract,
  and Blob connection/read/server timeouts passed.

Expected negative-path logs from mocked provider/database failures were
present. No failing test was waived.

## Real-browser evidence

The truthful Pete-only local fixture at `http://127.0.0.1:5075/the-slate` used
the real Community template, CSS, JavaScript, and static assets without
persistence.

Desktop at 1536 x 1024:

- 748px primary Feed, two 234px rails, and 1,248px grid.
- 12 equal-height Motion cards in one horizontally scrollable row; 716px
  visible of a 1,956px extent.
- Five compact emoji Respond choices.
- Respond selection and removal passed.
- Comment submit, count increment from 12 to 13, and input reset passed.
- Voice controls were present; no idle expanded Voice panel appeared.
- No document overflow and no browser console warning/error.

Narrow at 390 x 844:

- 374px fluid primary Feed.
- Desktop rails collapse to the approved mobile tools.
- 12 Motion cards at 96 x 132px in one 346px horizontal viewport.
- `documentElement.scrollWidth == clientWidth == 390`.
- No idle expanded Voice panel.

Evidence:

| File | SHA-256 |
|---|---|
| `evidence/2026-08-07-community-revival/community-feed-desktop-viewport-1536x1024-artifact-983x1024.jpg` | `8bb8028b5a1f0c55690965db3e42c7122674c64e9d61f39d69ef5896ddfcb461` |
| `evidence/2026-08-07-community-revival/community-feed-narrow-viewport-and-artifact-390x844.jpg` | `04a194338496c4d9dbe3b8dd7d62d306043489510617679834298581f88c557f` |
| `evidence/2026-08-07-community-revival/superseded/community-feed-desktop-browser-transport-983x1024-original.jpg` | `6cbfee7b054dbf8e65535ee6c4e087cca30257b85499e818f89e388ca863dcd2` |
| `evidence/2026-08-07-community-revival/superseded/community-feed-narrow-browser-transport-390x844-original.jpg` | `54bfa25c5cec7ec365d5327c3c0c690c395165e838cdc47a40304e72d256ae90` |

The browser transport encodes screenshots as JPEG. The desktop viewport was
measured at 1536 x 1024 with DPR 1 and no overflow; its transport artifact is
downsampled to 983 x 1024. The narrow artifact remains 390 x 844. Every file is
now named for both the measured viewport and actual JPEG artifact dimensions.
The two earlier captures are retained byte-for-byte under `superseded/` and are
not used as exact-pixel proof.

## Independent-review correction

The first exact-SHA Protected review of `b32c236b` correctly required changes:
the scheduled identity lacked SQL/Blob data-plane authority, maintenance did
not validate `DB_NAME()`, release order allowed deployment before schema,
the command budget was soft, and the new migration was in the frozen legacy
directory. The corrected source now supplies narrow protected authorization
plans and runtime verification, exact target refusal, a pre-deploy schema
gate, a hard process alarm plus Blob/SQL bounds, and the governed root
migration location. mssql-python 1.11 source inspection also proved that its
public `Connection.cursor()` passes `connection.timeout` to
`Cursor(..., timeout=...)`; the runtime now checks that pinned contract before
executing. A second review then found that `77b1258c` still reused the
deployment/schema principal, could commit SQL grants before post-grant
verification, and mislabeled browser artifacts. The current source separates a
dedicated no-role maintenance identity, verifies the complete SQL/Azure
authority boundary, rolls back any failed SQL authorization, and retains all
evidence under truthful JPEG names. Review of `fc04ddb3` then found a
nonexistent Azure CLI group-membership command, scheduled SQL verification that
could impersonate rather than require the active narrow identity, omission of
the contained user's direct `CONNECT`, and a pre-merge schedule-order gap. The
current source uses the supported Microsoft Graph transitive-membership route,
preflights Azure authority before mutation with exact compensating removal,
requires the scheduled connection itself to be the dedicated SQL user, includes
the exact direct `CONNECT` grant, and supplies a no-Azure disabled schedule path
plus pre-merge WIF metadata ordering. A fresh exact-SHA review is still
required.

## Security incident and containment

A read-only Azure App Service inspection returned the existing Community
signing key in tool output. The key was immediately rotated without printing
the replacement. Only replacement length, unchanged Community-disabled state,
and healthy `/healthz` on the unchanged production release were verified. No
candidate source, schema, Community flag, data, or public behavior changed.
This incident is retained for final security/debug reporting and the exposed
value must never be repeated.

## Remaining gates

1. Commit the corrected exact candidate and obtain fresh independent Protected
   review.
2. Close every accepted finding and rerun affected checks.
3. Create the passwordless dedicated identity, WIF service connection, and
   nonsecret pipeline metadata with maintenance explicitly false and no data
   authority.
4. Satisfy Candidate admission, isolated deploy/smoke/stop, and Azure PR policy.
5. Merge through Azure; verify the automatic deployment fails closed before
   schema.
6. Apply only the exact additive migration through the governed path, then
   apply and verify the narrow SQL/Blob maintenance authority.
7. Deploy only the exact merged SHA through a separate forced run.
8. Enable and verify maintenance before enabling Community visibility.
9. Perform exact-source production owner/signed-out, Voice, media, lifecycle,
   health, latency, log, and rollback-readiness checks before any live claim.
