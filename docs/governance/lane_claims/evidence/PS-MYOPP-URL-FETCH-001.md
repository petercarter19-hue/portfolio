# PS-MYOPP-URL-FETCH-001 review evidence

Runtime-inert review-tail record for the Protected C13 private member URL-fetch
package. The paired receipt is
`docs/governance/lane_claims/receipts/PS-MYOPP-URL-FETCH-001.json`.

## Scope and authority

- **Package boundary:** the optional service-level adapter behind C10's disabled
  URL-import port; printable-ASCII public HTTPS admission; process-bounded DNS;
  per-hop address validation and pinning through C2; verified TLS; redirects,
  deadlines, size and content gates; closed failure mapping; private C10 handoff;
  the future C8 member-budget seam; exactly three obsolete C10 stop-test
  removals; initiative records; and one package-registry row.
- **Authority:** `repository_authority: through_merge` and
  `production_authority: withheld`. This evidence confers no route, schema,
  migration, provider, credentials, spend, live network acquisition, browser,
  deployment, scheduling, configuration, feature enablement, shared-inventory,
  staging, or production authority.
- **Owner outcome:**
  `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/complete-everything-backend`.
  Architecture choice 1 used default A: unreachable/refused/not-found are three
  recoverable pre-admission errors with no row or idempotency receipt.
  Architecture choice 2 removed exactly the three specified C10 module-absence
  methods. The URL-fetch flag remains off.

## Frozen candidate and independent result

Independent reviewer `agent:/root/shell_nav_prep`, with no C13 authorship,
reviewed exact pushed candidate
`410ae3b4272095173096b68b283155ed630d5693` read-only against current-main base
`1f455b8efaf2c70b5d0b9aeb66ed1f0fb6bd24b7` and prior accepted candidate
`8a9e48ce22da9fab8df3ca4d584cd81e976283ba`. The implementation writer is
`agent:codex/2026-09-02/myopp-c13-url-fetch-writer`; writer and reviewer are
distinct. The replacement exact-SHA delta/full review returned **ACCEPT** with
zero findings at `2026-09-02T22:42:15Z`.

The final six-path candidate delta is limited to the service module, its offline
test module, three method removals in C10's test module, the README, technical
completion record, and the package-registry row/count update. The earlier
claim-only surface transition is already on main from PR 860/build 2287/merge
`1f455b8efaf2c70b5d0b9aeb66ed1f0fb6bd24b7`.

## Review history and corrections

- Candidate `8c6927962897814ad6da444e68d7e09c13d1dd0c` was **REVISE**:
  synchronous system DNS could outlive the advertised total deadline; the
  exact-three retirement test compared against moving `origin/main`; and the
  binding deep/malformed HTML parser-bomb proof was absent.
- Candidate `9c061f9671a0b6f1a7aeff442d0576b70a74a23a` bounded production DNS in a
  disposable spawned process using the smaller of the hop allowance and total
  remaining time, with termination/reap and content-free IPC; added offline
  spawn success/error and slow-timeout/no-child-leak proofs; and added the
  1.8+ MiB, 180,000-tag malformed HTML/entity bomb through the real handoff.
  Review passed those corrections but returned **REVISE** because the retirement
  proof still named a feature-branch-only commit that an Azure squash merge and
  source-branch deletion would make unreachable.
- Candidate `8a9e48ce22da9fab8df3ca4d584cd81e976283ba` removed that dependency. The
  proof compares the merged tree with main-reachable activation base
  `9813ef8caea9a4984481397daf2044dd1cf1d59e`, asserts current absence, and binds
  exact full-index diff digest
  `0688dd6575367d9491a9636cd148c498cd89b1f2a7bf814c4a174bbcb81bd06a`.
  Independent review returned **ACCEPT** with zero findings after also passing a
  squash-only, garbage-collected, fresh-clone replay.
- PR 861 build 2290 then ran 5,550 repository tests and exposed one compatibility
  stop: an existing guard reserves the production identifier `ssl_context=` for
  another service's test-only seam. Replacement candidate `410ae3b4...` only
  renames C13's separate constructor seam and internal attribute to
  `tls_context_factory`, updates exactly two offline test call sites, records the
  CI correction, and removes the stale prior review tail. The independent
  reviewer confirmed that TLS context construction, certificate and hostname
  verification, SNI, numeric-address pinning, and all other accepted security
  behavior are byte-for-byte identical.

## Verification

- Final focused C13 recorded/offline suite: **51/51 passed**.
- Final C13 + C10 member-import + C2 safe-outbound run: **211/211 passed**, with
  two inherited platform/optional-library skips.
- Broader C2-C6 My Opportunities regression run: **322/322 passed**. Together
  with the seven C2 safe-outbound tests above, the supporting set is **329/329**.
- The focused transport tests passed **5/5** and the repository's coupled
  production-SSL-context guard passed **2/2** after the identifier correction.
- Package-registry integrity: **2/2 passed**; C13 occurs once in alphabetic
  `future_finish`, whose count is 33, and total is 135.
- The 35-address C2/C13 classification probe found no C2-admitted address that
  C13 labels denied.
- `git diff --check`, Python AST parse, exact clean remote-tip proof, and the
  current-main implementation write preflight passed at the candidate SHA.
- Azure PR 861 replacement build 2292 was bound to source candidate
  `410ae3b4272095173096b68b283155ed630d5693` and base
  `1f455b8efaf2c70b5d0b9aeb66ed1f0fb6bd24b7`; it passed all pipeline tasks and
  all **5,550/5,550** application/security tests with 24 inherited skips.

## Boundaries and post-review tail

No focused test used a live hostname, socket, provider, credential, account,
browser, database, deployment, or production/staging operation. DNS process
behavior was proven with offline child workers; transport behavior was proven
with fake sockets. No route or feature flag is changed. The module imports no
logger, credential channel, provider SDK, browser, `requests`, or proxy-aware URL
client.

The only files added after frozen candidate
`410ae3b4272095173096b68b283155ed630d5693` are this evidence record and its
matching receipt. No reviewed implementation, test, README, completion report,
package registry, or claim byte changed in the post-review tail. Merge preflight
and PR 861 remain bound to the exact reviewed candidate SHA.
