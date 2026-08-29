# PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001 review evidence

Runtime-inert review-tail record for replacement package 4 — the FINAL
content reader — of the accepted 2026-08-29 reader topology. Paired
receipt:
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001.json`.

- **Boundary:** Protected, independent review, repository authority through
  merge, production authority withheld. Four read-only readers over the
  member's durable saved slate ONLY (`opportunity_slates`,
  `opportunity_saved_results`, `opportunity_saved_qualifications`,
  `opportunity_saved_evidence`); all fifteen OS-1/OS-2/OS-3 and
  PS-OPPSLATE-004 working tables proven cascade-purged and deliberately
  not read. Directive hard-exclusions: third-party posting text, evidence
  links, responses, AI/model provenance. Nothing wired, nothing live.
- **Delivered candidate:** `9f1e4bdc309b1bb7aeed2c152c1438bbff0af254` on
  `work/2026-08-29-settings-account-export-oppslate-reader-001`, base
  `c2b03489` (activated from main `5d433cc3`). Custody: writer commits
  (agent:claude-code/settings-os-reader-writer, Sonnet, final
  `15ea7c2c`), one manager gate commit `7426af65` executing the COMPLETE
  three-artifact lockstep in a single commit (registry seal +
  placeholder-test replacement + the report's Gate state section), one
  manager correction-round commit `9f1e4bdc` (the review findings plus a
  full re-gate, all three artifacts moved again in the same commit), and
  the review-round records commit.
- **Gate proofs (two full-pass runs, both first-try):** run 1 on
  disposable `ps-migration-path-20260829-os` sealed
  `f283c79f9423892f4987fe88a6a01f642030a7e327a7719a7a88ca9b45eae8f7`;
  after the review-directed `saved_analysis_key` exclusion changed the
  forward file's executable content, run 2 on disposable
  `ps-migration-path-20260829-os2` re-sealed
  `3db5eff29654109f35e3c5a8ef1df0d442a316258d82b41fe1fff1868be2ed80`
  (`gated_at_utc 2026-08-29T18:21:30Z`, `verified = 1`, rollback
  rehearsed, throwaway deleted). Run 1 is superseded, not erased; both
  are recorded in the CR4 report's Gate state.
- **Independent review (fresh Opus, read-only, no-fetch brief with
  supplied release state):** `7426af65` → CONDITIONAL. The package's
  central durability judgment was independently re-derived from the
  migration files and CONFIRMED (four OS-4 tables durable; all fifteen
  excluded tables provably purge-cascaded, including PS-OPPSLATE-004's
  three via `DELETE ... JOIN ... @ExpiredSessions`); 8/8 mutation probes
  caught; zero correctness/isolation/privacy/release-safety defects.
  Findings: F1 stale gate-state passages (MEDIUM, records), F2
  `saved_analysis_key` kept on a factually wrong premise (MEDIUM — it IS
  an id, a generation-run `uniqueidentifier` inside AI_MODEL_PROVENANCE's
  "Model names/ids" definition; excluded in the correction round as
  directive execution), F3 two misquotations of schema-author intent
  (LOW/MEDIUM, records), F4 verify detail-string branch overclaim (LOW,
  corrected BEFORE run 2 so the standing seal executed the corrected
  script), F5 directive-column miscount (LOW; now sixteen), F6 fixture
  realism (INFO, acknowledged unchanged by design). `9f1e4bdc` →
  **CONFIRMED**: all five resolutions verified surface-by-surface, seal
  recomputed independently, reversal-pin probe and four others caught
  (5/6; the sixth is a pre-existing program-wide verify-scan
  characteristic, not introduced by this round), suites 288 passed /
  2102 subtests exit 0 under both runners, secret scan clean, zero
  mutations both rounds.
- **Standing forward notes:** (a) program-wide test gap recorded by the
  reviewer for whoever next touches shared test conventions: assert every
  `DIRECTIVE_CATEGORY_COLUMNS` entry appears in its reader's
  verify-script forbidden-scan block (the verification script carries no
  digest protection); (b) the `visibility = 'private'` predicate cuts the
  opposite way in an export reader — the CR4 contract's own forward note
  binds whichever package relaxes `CK_opportunity_slates_visibility`;
  (c) any future PS-OPPSLATE-004 R2+ durable-save mechanism needs a
  FRESH durability judgment; (d) grants remain paper-only until C4.
