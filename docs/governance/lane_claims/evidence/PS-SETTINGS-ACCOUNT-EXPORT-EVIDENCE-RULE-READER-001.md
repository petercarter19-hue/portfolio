# PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001 review evidence

Runtime-inert review-tail record for the CLOSING reader package of the
account-export topology — the third and last decision-spawned package of
the accepted 2026-08-30 seven-export-decisions ruling (Papers 4–7).
Paired receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001.json`.

- **Boundary:** Protected, independent review, repository authority
  through merge, production authority withheld. One read-only reader
  over `dbo.career_skill_links` applying the owner's
  safe-references-only evidence rule for the first time (skill linkage
  resolved to `skill_key` via an owner-predicated join; a derived
  `evidence_linked` bit; `source_entity_id`, `evidence_item_id`, and
  every id/actor column excluded), plus the four remaining owner
  rulings written durably into five `DOMAINS` reason strings, each
  pinned by tests. Nothing wired beyond `DOMAINS`.
- **Delivered candidate:** `e2a5069463fd0b98ef9937da7e18df55c680c6a2`
  on `work/2026-08-30-settings-account-export-evidence-rule-reader-001`,
  base `17ca74ad` (the activation merge). Custody: seven writer commits
  (agent:claude-code/settings-er-reader-writer, Sonnet, final
  `c98b6c47`; no surface extension was needed — both cross-package test
  files were claimed from activation and the writer's sibling-pin sweep
  found no pins elsewhere), the manager's gate-lockstep commit
  `cbde91e9` (registry seal + placeholder replacement + Gate state +
  the gate-round scan-sanction fix), the review-directed correction
  commit `e2a50694`, and the review-round records commit.
- **Gate proof (two runs; run 1's refusal was the system working):**
  run 1 on disposable `ps-migration-path-20260830-er` was REFUSED by
  the verification script's OWN forbidden-column scan — which, as the
  writer first wrote it, contradicted the reader's own disclosed
  `evidence_linked` design (the derivation mentions
  `link.evidence_item_id` in select-list text to test `IS NOT NULL`;
  the value never leaves; offline tests parse output names, so only the
  engine's text-level check exposed the contradiction). The fix is
  scan-side and makes the sanction explicit: assert the exact
  derivation present exactly once, neutralize exactly it, then scan
  strictly. The forward migration never changed; run 2 on fresh
  `ps-migration-path-20260830-er2` passed in full and sealed digest
  `09c900119191c2379007aae85eeee06523675351437fca868d35b880bdbdd678`
  (`gated_at_utc 2026-08-30T11:37:04Z`) — the writer's authoring-time
  computation, and the program's first INSERT exercise of both
  `career_skill_links` and `evidence_items`.
- **Independent review (fresh Opus, read-only, no-fetch brief with
  supplied release state):** `cbde91e9` → CONDITIONAL, substance sound:
  seal recomputed offline and proven stable across every commit;
  included ⊎ excluded = the DDL exactly; no double export vs the
  living_resume skill reader; the soft-delete back door verified from
  the verify script's actual execution flow; the "no writer anywhere"
  premise of the publication rulings re-verified by the reviewer's own
  repo-wide scan; six adversarial probes against the scan sanction
  (plain re-add REFUSED; deletion REFUSED; duplication REFUSED — and
  also caught offline, better than assumed; subquery smuggle REFUSED).
  Findings: F1 stale gate-commit figures (fixed, vintages attributed);
  F2 the neutralization marker deadening the alias-presence assertion
  (no exposure — two offline tests catch the alias drop; ACCEPTED as a
  carried obligation rather than a post-seal verify edit, per the
  reviewer's own recommendation); F3 a header "SIX"/"FOUR" miscount
  (fixed comment-only; digest re-verified unchanged by the reviewer
  both before and after); F4 bracket-quote evasion recorded as a
  shared-conventions note. `e2a50694` → **CONFIRMED**: digest
  recomputed at the final content and equal to the seal; all figures
  and vintages checked; battery re-run 521 passed / 3860 subtests exit
  0 both runners; the reviewer's final flag (the forward-note sentence
  preceding this very file's existence) is resolved by this file.
- **Standing forward notes:** (a) **BOUND OBLIGATION on the next
  package that touches the EXPORT-009 verify scan** — the first real
  evidence reader, where the `file_evidence_metadata` ruling already
  routes: change the neutralization marker to a token-free string
  (e.g. "(sanctioned derivation)") so the alias-presence assertion at
  the scan's tail regains force; (b) bracket-quoted identifiers evade
  both text-level forbidden-column checks program-wide (refused twice
  over regardless: exact-order allowlist offline, capture-table arity
  at gate) — a shared-conventions item alongside the integration
  review's verify-scan completeness note; (c) the five ruling reason
  strings are owner rulings pinned by tests — changing one requires a
  fresh owner decision on the record; (d) grants remain paper-only
  until C4.
