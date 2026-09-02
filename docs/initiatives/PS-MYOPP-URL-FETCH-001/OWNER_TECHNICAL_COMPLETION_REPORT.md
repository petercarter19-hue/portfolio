# PS-MYOPP-URL-FETCH-001 — technical completion record

## Core record

- **Package/path:** `PS-MYOPP-URL-FETCH-001`, Protected; independent exact-SHA
  review required.
- **Writer:** `agent:codex/2026-09-02/myopp-c13-url-fetch-writer`.
- **Branch:** `work/2026-09-02-myopp-url-fetch-001`.
- **Activated from:** Azure `origin/main`
  `9813ef8caea9a4984481397daf2044dd1cf1d59e`; activation PR 857 passed build
  2280 and squash-merged as `a90414ddb9ae551223218b3067e65bccca77e1ad`.
- **Owner outcome:**
  `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/complete-everything-backend`.
- **Resolved architecture choices:** unreachable/refused/not-found use default A
  (three recoverable C13 pre-admission codes, no row); exactly the three named C10
  module-absence tests are retired; v1 admits only HTML/plain text; non-ASCII URLs
  and transcoding remain out; 2 MiB/5 s/12 s/3-redirect defaults apply.

## Repository outcome

Implemented the I/O-free C10 factory seam, per-call C2 guarded-fetch composition,
process-isolated and hard-deadline-bounded system DNS with child termination and
reap, numeric-address-pinned verified-TLS transport, absolute per-hop and total
deadlines, cap+1 streaming cutoff, strict URL/status/content/encoding/sniff gates,
closed refusal/error mapping, provenance handoff into C10's unchanged private
pipeline, and the C8 member-budget ledger contract. The fetch flag is not changed.

Changed implementation surfaces:

- `services/my_opportunities/member_url_fetch_service.py`
- `tests/test_my_opportunities_member_url_fetch.py`
- `tests/test_my_opportunities_member_import.py` (only three method removals)
- `docs/initiatives/PS-MYOPP-URL-FETCH-001/README.md`
- this record
- `docs/governance/PACKAGE_REGISTRY.json` (one future-finish row and matching
  counts)

The claim/receipt/evidence paths are lifecycle records. The registry path was
appended only after C11 closed, via claim-only PR 860; build 2287 passed and the
transition squash-merged as `1f455b8efaf2c70b5d0b9aeb66ed1f0fb6bd24b7`.
The implementation branch then refreshed from that exact main, passed a fresh
write preflight, and added exactly one alphabetized future-finish row.

## Verification and review state

- Focused C13 offline suite: **51/51 passed** after the self-review and first
  independent-review correction passes. The final additions prove a slow DNS
  child is terminated and reaped inside the deadline, success/failure children
  are reaped without content leakage, the three C10 stop-test removals are
  bound to an immutable main-reachable baseline and exact merged-tree diff
  digest, and a 1.8+ MiB deeply nested malformed HTML/entity bomb completes
  bounded through the real handoff with canaries removed.
- C2 deny-set/C13 classification probe: all 35 recorded address forms agreed on
  public versus denied; no C2-admitted address was classified denied by C13.
- Combined C13 + C10 member-import + C2 safe-outbound run: **211/211 passed**,
  with two platform/optional-library skips inherited from C10.
- Broader C2-C6 My Opportunities regression run: **322/322 passed**. Together
  with the seven safe-outbound tests in the combined run, this is the existing
  **329/329** supporting regression set.
- Package-registry integrity: **2/2 passed** after the one-row/count update.
- Complete-diff writer self-review: **pass** after refreshing from current main.
  The six implementation/registry/document paths match the extended claim; the
  C10 delta removes only the three named module-absence methods; URL/DNS/TLS/
  redirect/deadline/size/content/error/privacy/flag and no-live-network stops
  were rechecked against the architecture and executable proof.
- Independent review round one: **REVISE** on
  `8c6927962897814ad6da444e68d7e09c13d1dd0c` for unbounded synchronous DNS,
  moving-main stop-test proof, and the missing binding parser-bomb proof. All
  three were corrected; every other reviewed boundary passed.
- Independent delta/full review round two: **REVISE** on
  `9c061f9671a0b6f1a7aeff442d0576b70a74a23a` only because the corrected stop-test
  proof still named a feature-branch-only commit that would disappear after
  squash merge and source-branch deletion. DNS isolation/leak stress, the parser
  bomb, all suites, registry/scope, and preflight otherwise passed. The proof now
  depends only on a main-reachable baseline, the current tree, and a fixed exact
  diff digest.
- Independent final review round three: **ACCEPT**, zero findings, on exact
  candidate `8a9e48ce22da9fab8df3ca4d584cd81e976283ba`. The reviewer also passed a
  squash-only, garbage-collected, fresh-clone replay of the durable retirement
  proof.
- Azure PR 861 build 2290 then ran 5,550 tests with 24 inherited skips and one
  failure: an existing repository guard rejected the production identifier
  `ssl_context=` because that name is reserved for another service's test-only
  seam. C13's separate TLS-context factory was renamed without changing its
  verified-TLS behavior. The guard, 51-test focused suite, 211-test combined
  suite, 322-test broader regression suite, and two registry tests all pass after
  that bounded correction.
- Replacement candidate SHA/receipt/evidence: pending freeze and independent
  delta/full confirmation.
- Azure implementation PR/CI/merge: PR 861 remains open; a corrected full CI run
  and successful policy gates are required before merge.

## Release truth

Repository implementation is in progress. Nothing is deployed, enabled,
scheduled, migrated, configured, acquired from a live source, or operated against
production/staging. Merge will remain distinct from all of those states.

## Honest limitations / next action

The README's limitations are binding: no C8 route or budget wiring, HTML/plain
text only, no JavaScript rendering or transcoding, default-A failures create no
row, fake-socket transport proof only, per-process budget ledger, and inherited
C10 erasure/lockout limits.

Next: freeze and push the bounded Azure-compatibility correction; obtain fresh
independent exact-SHA delta/full confirmation; then add replacement
receipt/evidence only, pass merge preflight, let PR 861 rerun all policy gates,
merge only when green, close, and retire. The fetch flag stays off throughout.
