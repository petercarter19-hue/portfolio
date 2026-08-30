# PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001 review evidence

Runtime-inert review-tail record for the second decision-spawned reader
package of the accepted 2026-08-30 seven-export-decisions ruling
(Paper 2: preferences included with truthful dormant labeling; Paper 3:
the member's own consent history, evidence_json excluded whole). Paired
receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001.json`.

- **Boundary:** Protected, independent review, repository authority
  through merge, production authority withheld. Three read-only readers
  over `connection_preferences`, `notification_preferences`, and
  `user_consents` — the program's first readers over user_id-keyed
  tables, served through the program's single byte-identical identity
  header (readers filter `user_id = @UserId`). Both preferences readers
  emit the owner-ruled dormant label
  (`feature_status = 'dormant_not_yet_enforced'`) as an explicit
  projection-truth column; `evidence_json` excluded whole with a
  genuine planted-JSON canary; `recruiter_questions` appears nowhere in
  executable SQL (test-enforced). Nothing wired beyond `DOMAINS`.
- **Delivered candidate:** `723b6a327a52aa13f8039e0644b5d04b5612197d`
  on `work/2026-08-30-settings-account-export-preferences-consent-reader-001`,
  base `0a5438db` (the activation merge). Custody: six writer commits
  (agent:claude-code/settings-pc-reader-writer, Sonnet, final
  `835e187e`; no surface extension was needed — the cross-package
  integration test file was claimed from activation, and the writer's
  sibling-pin sweep found none), the manager's gate-lockstep commit
  `8913ca55`, the review-directed correction commit `723b6a32`, and the
  review-round records commit.
- **Gate proof:** FIRST-RUN full pass on disposable
  `ps-migration-path-20260830-pc` (deleted after): digest
  `b92a301e0d3616b3baedb1236eedea4d45a74430c84ad5e2e9b3adfde5eccd94`
  (`gated_at_utc 2026-08-30T09:36:34Z`), identical to the writer's
  authoring-time computation; three reader procedures; `verified = 1`;
  rollback rehearsed. The first INSERT exercise of
  `notification_preferences`' and `user_consents`' constraint sets
  anywhere in this program; the EXPORT-007 DEFAULT-vs-NULL lesson was a
  named brief item and held — the program's fourth first-run pass in
  six gated reader packages.
- **Independent review (fresh Opus, read-only, no-fetch brief with
  supplied release state):** `8913ca55` → **PASS** with four LOW
  documentation/test-fidelity findings. The reviewer reproduced every
  gate fact offline (digest recomputed; forward file proven
  single-commit), audited included ⊎ excluded = the DDL exactly on all
  three tables, verified exactly one identity-header variant across all
  30 program readers, closed the adversarial identity question negative
  (signup creates app_user + active profile atomically; no deactivation
  path exists, so no member data can hide behind the profile
  requirement), confirmed the dormant label truthful over the full
  tracked tree, verified the consent ORDER BY total via the PK
  tiebreak with an engine-exercised identical-timestamp fixture, and
  **independently ruled the `source_context` exclusion CORRECT** ("a
  disclosure decision should be made against real content, not a
  column name"), endorsing its provisional shape. Probes: 10/11 caught
  offline; the 11th (post-seal verify-fixture edit) is the disclosed
  program-wide unpinned-verify property, moot here (verify file
  single-commit since the gate). Findings F1–F4 (empty-test cursor
  shape; five→six tally; line counts; three post-Gate-state stale
  passages) corrected in `723b6a32`; the reviewer then **CONFIRMED
  723b6a32**, proving F1's fix substantive with a discriminating
  regression that only the corrected test catches, and re-verifying the
  seal intact at the final content.
- **Recorded non-blocking observation (deliberately not re-churned, on
  the reviewer's own advice):** two line counts in the report's
  changed-paths list are self-referentially stale by the correction
  commit's own edits (test file 1018, contract 454 at the final SHA); a
  pre-commit author cannot know post-commit counts, and another round
  would re-stale them.
- **Standing forward notes:** (a) `source_context` re-judgment triggers
  the moment a future package adds `user_consents`' first real writer;
  (b) the dormant label must be revisited by whichever package first
  makes either preferences table runtime-consumed; (c) grants remain
  paper-only until C4.
