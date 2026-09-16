# PS-DELIVERY-CONTRACTS-SAFE-CUSTODY-001 completion record

- Package and delivery path: `PS-DELIVERY-CONTRACTS-SAFE-CUSTODY-001`, Protected, repository authority through merge, production authority withheld.
- Immutable Candidate A: `93f906ce136332f1ba5aee3869a4551c440dcde6` on `work/2026-09-13-delivery-contracts-safe-custody-001`.
- Independent review: reviewer `agent:/root/p1_review`, model `gpt-5.6-sol`, effort Extra High, returned an unqualified `PASS` with no findings for exact candidate `2958ee1593f880b48f34d8967be7e27a8821410e` on 2026-09-15. Pete then supplied an external Grok independent-review `PASS` with no findings for exact candidate `93f906ce136332f1ba5aee3869a4551c440dcde6`, after the narrow package-registry integration. No external session identifier was provided or inferred.
- Review rounds: candidate `e6c4b9a4f66e963a476213578cd7ec091775b357` received five findings covering accepted-byte custody, actual-caller binding, reconciliation path integrity, migration proof/recovery, and prepared-main lineage. Candidate `9032fbb5f05fdc9c9b45cee19b4865d01d5362f8` closed those five and received one remaining finding covering semantic domain-authority reduction. Candidate `2958ee1593f880b48f34d8967be7e27a8821410e` closed the sixth finding and received the Sol Extra High PASS. Candidate `93f906ce136332f1ba5aee3869a4551c440dcde6` preserved all 17 original implementation paths byte-for-byte, added the accepted registry integration, and received the owner-supplied external Grok PASS.
- Architecture packet hashes: `ARCHITECTURE.md` `d6d49b31d17b3624e22d5332027649f718f7d89422d97b7e52b26d460c0b6a61`; `CHANGE_MAP_AND_COVERAGE.md` `4ce2f4bc4dc2ceb70691da82cc541ef4dafba5f266d82a4dbdd99cfeb8c5d550`; `INDEPENDENT_REVIEW.md` `9093be8e9035b43c615dc7b60d295b8b77b20dc9a1c63a388f00e0b8e5cded6b`; `IMPLEMENTATION_HANDOFF.md` `bfd9a5d9226bbb7076985a8bf8e29e923513c3da913993d819e75725d07b339f`.
- Validation: the first five corrections passed the full 444-test delivery/lifecycle/Control Room/governance regression in 859.866 seconds (captured log SHA-256 `abb6a4fa770d0562f49c29b10beb34294868351ec420bb0a5117e080aa5ff3c4`). The exact final correction passed 290 affected tests in 46.647 seconds (log `ad8d1074f71e1040e8e85e14db013f0584b61651ee7b6321dab96c4cda4095f5`) and a 40-test post-record check (log `17129a2701258f7eb080c6ecaabaa40e7a60360750cf8ecdfd9923d52f332dda`). The registry integration passed 32 registry/governance tests and 27 SafeCustodyClaimTests/SafeCustodyRegistryTests, Python compilation, diff checks, and Azure build 3056. The external reviewer noted that the validation directory retained the 444-, 290-, and 40-test logs but not the earlier 87-test log, and did not rerun the API-key-gated Control Room check or Protected write preflight. No provider, production, identity, billing, or database operation was performed.
- Candidate A outcome: delivery and routing instructions, deterministic early OpenCode session capture, dormant compatible Protected partial-release and main-reconciliation controls, safe-custody checks, adversarial regression coverage, and current-record projections are implemented. Dormant operations remain disabled unless their separate gates are satisfied.

## Reviewed local staging

The following six files were staged and independently reviewed but remained uninstalled at the immutable review point. The five existing destinations must match their approved original SHA-256 immediately before replacement, and the new test destination must remain absent. The reviewed staged and final installed bytes must match these target SHA-256 values.

| Destination | Approved original SHA-256 | Reviewed target SHA-256 |
| --- | --- | --- |
| `.codex/AGENTS.md` | `ce57a1562f42e8653e4f85586d3ad11e3d5aff7bb6eae87c7b4df355316c52f7` | `6baf5d6c014e6da0d268490e02752fcfabe9a7deb1f09c7c70fdb44bb8a03ae8` |
| `.codex/skills/opencode-package-worker/SKILL.md` | `634ec3e7ef0fca6fd772fbc5aca7db143ffb0c3af193411eaa53dc0d2b3f49be` | `9fadbb813c94abc9529250a840efbbb5dd61ebf5398978b18bd805a6ddde4e32` |
| `.config/opencode/AGENTS.md` | `6f9f30609e6ac9489383fecfefdcdff4369bb3135e2a2f0ef5904362f05e9bf` | `4ec537014c0d9583113451fdeac3fa1bc85b0f67e779019cd86af70181fa1533` |
| `.config/opencode/agents/package-worker.md` | `a3722188a7548ce3ffe7c5d57269ca05fbb13613ded0047fa2d3c073fc771913` | `089cf7df76e57194028d32a751989510941647e20a1b3a913de1599ed5be2eb8` |
| `.codex/skills/opencode-package-worker/scripts/Invoke-OpenCodePackage.ps1` | `6a7c0ad31d8ada139ffbe1bfdd48c8cfd5f377977efa9254fa20e59fcd381f11` | `fbd370fa948b264b5fe8d96a78320ff82ba97e78ac204d4547735b3a01c637dc` |
| `.codex/skills/opencode-package-worker/tests/Test-OpenCodePackage.ps1` | absent | `dbc5d52abf5373e215844ca7d428eb56988a43bf12a6ba23e89959d258f588b3` |

The staging-manifest verification log hashes to `5828a17dd9138e59e13bed4c8f2683f526b25db7fc728480454df49fa0540178`; the reviewed fake-process/no-provider test log hashes to `c9854b061eec8a3224486f9a379eaf66a6e415844d1844e9a13537825dcc01bb`.

## Deferred boundaries and rollback

Candidate B remains deferred: no live machine-registry migration, lifecycle-registry schema cutover, or `CURRENT_LANES.json` schema-4 cutover is included here. Candidate A acceptance does not complete or close Candidate B; the active package retains future cutover custody until a separately authorized, staged, reviewed, and accepted transition. Production, product-package, identity, billing, provider, and deployment authority remain withheld.

Repository rollback is a normal revert of the accepted Candidate A merge. Local-file installation is separately gated by exact original-byte checks and preserves recoverable originals and installation evidence; it must stop without overwrite on any drift.

## Candidate B and final P1 report review: later status

The preceding Candidate A staging, deferred-boundary, and rollback sections
record that candidate's review-time state. They are not claims about the later
installation or Candidate B cutover. Candidate A was accepted in PR 1046 as
main `1485b3d2bc98547654a8f2d08b527c84e4ae86ba`, and the six reviewed
local OpenCode files were subsequently installed with original-byte and final
reviewed-byte checks. The retained
`P1_LOCAL_INSTALL_20260916T010957Z/installation-manifest.json` records those
hashes and recoverable originals; the fake-process test made no provider call.
The existing machine registry was separately qualified and migrated to schema
2 with its deterministic backup. The independently reviewed schema-4 index
cutover was accepted in PR 1073 as main
`7fd5c19c3877f48865b832ecd80283c4af09e373`, and its dependency claim
was closed. The accepted claim-path repair in PR 1078, main
`17926f436d60f203db8ad5b7b5e31c12867686cc`, was also closed before the
original P1 claim resumed. None of these actions deployed to production.

The original P1 branch reconciled through completed journal operation
`e63886d994d4667e4759961a884cf843fc13c7d5310ac19812fd6eaa6cb0e2bf`
from preserved C `8345307b00eeab5370df6b183c1c17e8098556dc` to pinned M
`10bcfeb345040c9de727b5ea180f9fedd73af4b8`. Result R
`01df08ddc47c00c9e24d077e70f1d394cde867b4` was pushed, clean, and
tree-identical to M. The later substantive delivery-report candidate
`c5e0c8776fd0a9bc12d653e27bba98d4a206daee` changes only this package's
claimed README and owner technical completion report relative to M; accepted
code, tests, index, and claim bytes remain unchanged.

Independent reviewer `agent:/root/p1_final_review`, manager-reported as
`gpt-5.6-sol` Extra High, returned PASS with no findings on exact candidate
`c5e0c8776fd0a9bc12d653e27bba98d4a206daee`. The reviewer had also
returned PASS on the preceding report candidate
`545e99e8fd410c98537406e93288030f27b410bd`; the final candidate only
time-anchors status wording in those same two non-evidence paths. The
reviewer confirmed that this substantive path delta permits ordinary
Protected close after the fixed review tail, accepted PR/CI/merge, and
claim-only close. The matching receipt's required `reviewed_at` value
`2026-09-16T22:24:37Z` is this writer's UTC receipt-recording time, not an
invented reviewer execution or completion timestamp.

After R, 421 delivery/lifecycle/governance-pointer/package-registry tests
passed in 915.171 seconds, and 51 Control Room tests passed separately using a
process-local placeholder key with no provider call. The initial combined
import without that key ran zero tests and is not counted as a pass. The final
report-wording change passed 32 focused governance-pointer/package-registry
tests, `git diff --check`, and fetched Protected write preflight. This fixed
receipt/evidence tail is not part of the reviewed substantive SHA; it changes
no implementation behavior. At this recording point Protected PR, CI, merge,
and P1 claim close still remain, with production authority withheld.
