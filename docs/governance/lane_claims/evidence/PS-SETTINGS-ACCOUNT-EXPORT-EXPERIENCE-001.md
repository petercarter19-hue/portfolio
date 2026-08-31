# PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001 review evidence

Runtime-inert review-tail record for C3 of the account-export program: the
member's own request, status, and authenticated proxy download. Paired
receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001.json`.

- **Boundary:** Protected, independent privacy/access review, repository
  authority through merge, production authority withheld. Three owner-scoped
  routes, a route-layer experience service, one new read path on the storage
  adapter, the member screen, the Settings change, and the procedure
  allowlist — all behind `PEERSLATE_ACCOUNT_EXPORT_ENABLED`, default false.

- **What was certified:** that a signed-in member can obtain their own export
  and cannot, by any input or sequence, obtain or learn about anybody else's.
  This is the first member-facing surface capable of returning an entire
  account in one response.

- **Delivered candidate:** `f16169716a9c6d57a9a1fa8cbaa08a2c3c37c51e` on
  `work/2026-08-31-settings-account-export-experience-001`. Base: activation
  merge `3c43269f` (PR 789); surfaces extended by PR 793 (`8c53b81b`) **before**
  the two pinned tests were touched.

## Review, two rounds

Round one on `cde354f2` returned **REVISE** with two IMPORTANT findings, both
reproduced by the writer before being accepted:

1. The deletion row's reassurance that downloading does not delete rendered
   unconditionally, directly beneath flag-off copy stating no export exists —
   a contradiction on the page whose whole purpose is telling members the
   truth, and pinned in by the settings regression.
2. The containment claim "merging changes nothing a member can reach" was
   false. Settings copy changes with the flag off, and `settings()` called
   `domain_summary()` unconditionally outside the try — handing Settings a new
   failure mode for every member, including those who cannot reach the
   feature at all.

Round two on `f1616971` returned **PASS**, verified against the diff.

The privacy core was attacked and held in round one, by re-derivation rather
than trust: all-pairs indistinguishability converging on a single refusal
site; locator containment across all six download outcomes over body and
every header value; the identical refusal code path for
exists-but-not-yours versus does-not-exist; the malformed-key fast path
adjudicated sound; the session job-key hint not weaponisable because
ownership is re-proved in SQL on every read; `read_final` reachable from one
call site downstream of that proof; the allowlist exactly the three
owner-scoped procedures and none of the five system-wide worker ones.

## Reviewer provenance, disclosed

The round-one deep pass ran in a **fresh reviewer with no coordination
history with the writer**, deliberately, because the adjudicating session and
the writer had collaborated extensively the same day. Findings were verified
and adjudicated by that session, and the re-freeze confirmed directly against
the diff.

## Honest limitations carried forward

1. **Enabling the flag would not produce a working export.** The worker that
   assembles an archive runs nowhere — no host, no schedule, no identity. A
   request would sit at `queued` indefinitely.
2. **Expiry is not deletion.** Nothing schedules `usp_ExpireAccountExportJobs`
   or `cleanup_final`, so the owner-approved seven-day window is enforced in
   the ledger and **not on disk**: an expired job correctly refuses to
   download while its archive remains in storage indefinitely. This is the
   most consequential open item and must close before real members are
   enabled.
3. **No live proof of anything.** Every test uses fake cursors and fake
   storage. The owner-filtering that enforces the whole guarantee lives in the
   C1 SQL procedures, which have never executed against a real database. At
   this SHA the guarantee is proven by construction and reading, not by
   execution.
4. **Timing residual.** The structural mitigation is asserted, but the
   database lookup's own timing is untested and needs a real database and a
   statistical harness.
5. **Member-facing language.** `DOMAINS` reasons reach members verbatim,
   including internal package codes. Accurate, from the single source of
   truth, and not plain language — routed to the owner rather than
   paraphrased, because paraphrasing means editing another package's surface
   or keeping a drift-prone second copy.
6. **No rate limit** on the buffering download proxy. Authorization is
   unaffected; an availability and memory note for deployment sizing.

## Not deployed

Repository merge only. No deployment, schema apply, container, worker
identity, or production operation is claimed or performed here.
