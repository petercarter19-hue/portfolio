# PS-MYOPP-RELATIONSHIPS-001 — candidate evidence

## Scope and authority

Owner outcome: Pete's recorded full-sequence directive
(`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-08-31/full-sequence-c6-c10-c7-c8-c11-c12-c9`).
Disposable-proof envelope: Pete's direct answer, reference
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-08-31/disposable-proof-envelope-c4-through-c9-yes-i-do`.
Repository authority `through_merge`; production authority withheld. No
deployment, enablement, provider contact, or production/staging schema
action is granted by this evidence.

## P-1 repository evidence

The doc 03 s7 save/remove/undo machine (idempotent identity, exact undo
window with deadline-pinned finalization, terminal removed rows, one active
save per member and opportunity, save-during-window as the legal undo
transition), derived-only lifecycle overlays with REC-03 per-member review
(refusing review_version_not_governing mid re-verification), the
owner-filtered saved view over read-time display resolution, slate_link
persistence primitives with one active link and no C7 command surface, the
doc 09 s4 unknown-outcome discipline (both branches proven), and the
additive PS-MYOPP-005 trio are locked by 87 package tests plus 233
regression/registry tests, all green at the frozen candidate (320 total).

Writer self-review fixed 2 blockers (an invalid T-SQL trigger construct;
a REC-03 review dead-end), 5 importants, 6 minors pre-freeze; independent
review then found and the writer fixed a member-hostile
save-during-undo-window silent no-op and replay staleness, each locked by
the reviewer's own reproduction as a binding test.

## P-2 disposable Azure SQL proof

- Attempts: a1 failed on an over-length ledger description (real defect,
  fixed); a2 failed on the verifier's filtered-index expected forms lacking
  the catalog's n-prefix (real defect, fixed against the observed live
  catalog); a3 SUCCEEDED — forward apply, idempotent reapply, verifier
  `verified = 1` (2026-08-31T21:45:23Z), rollback rehearsal, full object
  inventory, executable SHA-256 `f65be2957ac36b04bb8ac429621ce774971b2e4235361b83ab534390278f92c1`
  (independently recomputed by the reviewer at both frozen SHAs).
- All three throwaway databases (`ps-myopp-c6-gate-20260831-a1/a2/a3`)
  deleted with `ResourceNotFound` confirmed; the temporary firewall rule was
  removed and the server's rule set restored. No production or staging
  database was contacted.

## Review

Independent read-only exact-SHA review: `c8a304f2` REVISE (one blocking
member-visible defect plus one important, reproduction-proven); fixed
candidate `f8591ababa371b2f799d3ba264236bcfec7b1b6c` PASS after the reviewer
re-ran its reproductions and full probe battery (24/24, 35/35) with no
regressions. Reviewer: fresh Claude Opus session, fixed pre-written handoff,
provenance disclosed; reference
`agent:independent-review-2026-08-31/myopp-relationships-001-c8a304f2`.

## Forward obligations (recorded; none blocks this merge)

1. SlateLink command replays echo frozen receipts (disclosed; C7 routes
   replay through a live re-read).
2. The C2-backed basis reader must supply the governing head version for
   `changed` listings or a member's whole saved list fails validation (C8).
3. TRUNCATE/DROP is outside delete-block trigger scope (future erasure
   package must not treat triggers as full coverage).
4. The unknown-outcome lockout is per-process; multi-worker deployments
   need a shared-store lockout (C8/C9).
5. The member-data erasure path remains outstanding across C5/C6 tables
   before any real member data exists.

## Coordination record

PACKAGE_REGISTRY.json and tests/test_my_opportunities_retrieval.py entered
the claim via governed extend-surfaces transitions (PRs 807/808); the
retrieval extension permanently de-fragilized the registry is-last
assertion class. On close, SQL FIles/Migrations/registry.json releases to
the Settings domain-ledger package per the recorded cross-program order.
