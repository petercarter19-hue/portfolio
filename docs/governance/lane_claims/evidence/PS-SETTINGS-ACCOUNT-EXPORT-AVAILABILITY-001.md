# PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001 review evidence

Runtime-inert review-tail record for Package B: bounded availability
protection for the account-export routes, retiring the second of C3's two
recorded gaps. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001.json`.

- **Boundary:** Protected, independent review, production withheld. Rate
  limits on the three export routes via the house PLANNED_RATE_LIMITS
  idiom, and the `read_final` pre-read memory guard (refusal from
  provider-reported size BEFORE any blob read; post-read checks
  byte-identical). Written by a dedicated writer agent; frozen and
  stopped at the review gate per protocol.

- **Candidate:** `e4ce9a4d` after one REVISE round on `8d343cea`.

- **The REVISE round's HIGH, worth remembering:** HEAD requests bypassed
  the download budget entirely while executing the full buffering path,
  and the guard test was written so it could not notice -- found by the
  reviewer measuring, not reading (100 HEADs, zero refusals). The fix
  restored the house idiom (bare specs bind every served verb) and added
  a positive HEAD-burn proof.

- **The budget ruling:** 30/hour stands over the scouted 6/hour. The
  writer proved 6/hour breaks the closed experience suite's own
  choreography before deviating; the reviewer's decisive reasoning is
  recorded in the receipt -- per-address fixed-window limiting is not the
  instance-survival control at either number, and 6/hour would tax honest
  members. Burst truth disclosed: fixed window permits all 30
  back-to-back, ~2.93 GiB peak concurrent buffering per address.

- **Honest limitations:** limits key on network address, not member
  identity (member-keying recorded as a future refinement; the shared key
  function was deliberately not touched); the 429 body is JSON on HTML
  routes (content-free, house-consistency cosmetic); none of this is the
  defence against a rotating hostile client -- the per-request size cap
  and platform capacity are.

## Not deployed

Repository merge only. The export feature remains OFF; nothing here is
reachable until the flag-on gate.
