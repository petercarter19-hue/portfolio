# PS-SETTINGS-ACCOUNT-EXPORT-MEMBER-REASONS-001 review evidence

Runtime-inert review-tail record for CR9: plain-language member-facing
reasons for the 18 non-included export domains. Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-MEMBER-REASONS-001.json`.

- **Boundary:** Protected, independent review, presentation only. A
  `_DOMAIN_REASONS` map plus one line in `domain_summary()`; `DOMAINS`
  untouched and byte-identical to main throughout. No route, template,
  flag, schema, worker, or deployment change.

- **Review, two rounds.** Round one on `0820115f` returned REVISE with
  five blocking findings — most importantly the missing drift guard,
  which the reviewer proved by mutating a ledger reason to an opposite
  ruling while every guard stayed green. Round two confirmed PASS on
  `ba500d9c`; three optional wording notes were then taken and the final
  candidate `9069ce50` was diff-confirmed by the same reviewer.

- **The drift pin.** Every sentence is bound by digest to the exact
  ledger reason it paraphrases; a changed ledger reason breaks the suite
  and forces re-wording. **Honest limit, recorded at the reviewer's
  instruction:** the pin detects *ledger* drift, not *sentence* drift — a
  future sentence edit passes it silently. Acceptable only because any
  sentence edit is a Protected-surface change that receives its own
  review.

- **The canary.** No mapped sentence may carry a package id (hyphen or
  underscore form), `dbo.` name, `usp_` name, governance reference,
  V-number, "domain matrix", "reader", assorted internal vocabulary, or
  any snake_case identifier. **Honest limit:** it is a tripwire, not a
  proof of plain language.

- **A records correction inside this package:** the first frozen
  completion report asserted independent review in the past tense before
  any review existed. Caught by that review; corrected with the
  correction itself recorded.

## Per-sentence verdict table (owner veto-reading artifact)

Issued verbatim by the independent reviewer at `ba500d9c`; rows 1, 10,
11 and 15 subsequently received wording-only refinements (comma pair for
dashes; "search" dropped; "operational data about how the service runs";
"this part of PeerSlate") that the reviewer diff-confirmed at
`9069ce50`. **The verdicts are unchanged: 18 truthful, 0 overclaims, 0
underclaims.** The owner has not personally read all 18; his veto
stands on any of them.

1. AI proposals — truthful (open-ended like the internal reason; covers the real destinations, all exported)
2. Ask Pete messages — truthful ("never" = "must never surface")
3. Public Ask Pete — truthful (near-verbatim)
4. Audit history — truthful (promises nothing)
5. Interview history stored in your browser — truthful (clearest in the set)
6. Community posts you wrote — truthful ("we plan" = "queued")
7. Connections — truthful (decision genuinely open)
8. File evidence details — truthful
9. Home — truthful (carries the "where included" qualifier)
10. Indexes, caches and backups — truthful
11. Interview telemetry — truthful
12. Journal — truthful (both halves kept)
13. My Opportunities — truthful
14. Notifications inbox — truthful
15. Your publication versions — truthful
16. Profile publication — truthful
17. Projects — truthful (verified: living resume exports career projects)
18. Workshop save requests — truthful (narrower than source, cannot overclaim)

Machinery verified alongside the wording: each sentence digest-pinned to
its exact internal reason (mutation-proven on three domains); a future
domain without a sentence fails the suite; a domain becoming included
with a leftover sentence fails the suite; unmapped domains render the
internal wording verbatim through the real page path; no behaviour
change — same 12 of 30 included, same order, same responses.

## Not deployed

Repository merge only. The export feature remains OFF; the worker still
runs nowhere. This package changes only what members will read once the
feature exists.
