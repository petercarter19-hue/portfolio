# PS-HISTORICAL-CHECKOUT-RETIREMENT-002 candidate evidence

## Authority and boundary

- Owner outcome: `session:01a07158-684b-74a2-a47e-7ca0e91889b7/owner-finish-2026-09-07`.
- Writer: `agent:/root/historical_writer`.
- Delivery: Protected, repository authority through accepted merge, production withheld, independent review required.
- This package replaces paused partial-transfer package
  `PS-HISTORICAL-CHECKOUT-RETIREMENT-001`. Package 001, its worktree, branch,
  refs, and untracked handoff file remain preserved until this package closes.
- The only cleanup targets are the 29 immutable tuples in the package allowlist.
  No ref deletion, force removal, raw recursive deletion, pruning, garbage
  collection, reset, clean, history rewrite, production, deployment, schema,
  identity, product, or visual action is admitted.

## Candidate behavior

- Adds `retire-historical`, which removes one exact allowlisted historical Git
  worktree through ordinary non-force `git worktree remove`.
- Requires the executing lifecycle script and shared lifecycle surfaces to be
  the independently reviewed bytes accepted on fetched main.
- Requires the package allowlist, active claim, and this evidence file to be
  ordinary Git blobs with identical bytes at the reviewed candidate, fetched
  main, and cleanup branch HEAD.
- Requires the accepted review receipt to be an ordinary identical blob on
  fetched main and cleanup HEAD, and retains that blob identity in the crash
  recovery proof without creating a circular candidate dependency.
- Re-proves exact grandfathered registry custody, canonical path, live
  worktree, attached branch, local ref, server tip, cleanliness including
  ignored files, nesting, reparse safety, protected-claim exclusions, and
  unique live path-or-branch custody, and terminal main/cleanup/target server
  state while holding the registry mutex.
- Preserves an immutable before/after registry proof and limits crash recovery
  to the same caller and reviewed request. It preserves a still-present target
  and publishes an absent target only from the retained journal.
- Coexists with the current control-custody transition history and monotonic
  lease-clock validation.

## Validation

- Fresh write preflight: pass at base
  `3e629e10c017ab14c698472cd7d7dcceeff6ea2a`; only 58 unrelated
  grandfathered observations were warnings.
- Allowlist revalidation: 29/29 targets passed against the current registry,
  Git worktree list, live branch and HEAD, local refs, server tips, strict
  tracked/untracked/ignored cleanliness, nesting, reparse, and protected-claim
  exclusions; 0 issues.
- Focused historical retirement tests: 12/12 passed in 189.344 seconds. These cover ref/tag/stash
  preservation, control registry coexistence, request and registry drift,
  tracked/untracked/ignored residue, nested/detached/reparse refusal,
  active/paused/superseded claims, local-ref and remote-tip drift, claim and
  evidence byte drift, main/cleanup receipt absence or byte drift,
  manifest/mechanism drift, duplicate JSON, duplicate path or branch custody,
  crash recovery, and journal/caller poisoning.
- Full lifecycle suite: 97/97 passed in 1272.265 seconds with
  `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_worktree_lifecycle`.
- Syntax parses passed for both lifecycle implementation and tests.
- `git diff --check`: pass.

## Completed retirements

Independent reviewer `agent:/root/historical_review` accepted exact candidate
`5209703d40da5cc6fd7889a62b717ac3cc7dad50` at
`2026-09-07T20:23:26Z` after the two initial P2 findings were resolved.
The accepted receipt was the only post-review path. PR 957 passed blocking CI
build 2633 and squash-merged at
`191684f80714b5e62164ed2d789e7490917d6bb8`. All reviewed lifecycle,
allowlist, claim, and evidence blobs matched the candidate on main; the receipt
matched its branch tail. The cleanup branch was then merged with accepted main
and pushed at `62ab120b45c70092da8406bf09ac482fac7fa05c`, with every
required blob exact on main and cleanup HEAD.

Pre-retirement measurement recorded 29 targets, 85,366 files, 9,707
directories, and 28,926,803,997 logical bytes. The first generated batch had a
PowerShell parser error before Python or the lifecycle command started; it made
zero repository, registry, or filesystem changes and is retained in the raw
evidence. The corrected batch invoked `retire-historical` once for every exact
allowlist tuple: 29 succeeded and 0 refused.

Post-retirement verification found all 29 paths absent from the filesystem and
Git worktree list, all 29 local branch refs and server tips unchanged at their
allowlisted SHAs, and all 29 registry records retired with valid exact custody
proofs. Registry pending is null, its lock is absent, and the live Git worktree
count fell from 84 to 55. Registry SHA-256 after verification is
`85bf3761498b53f924cd3d9f2d518000c6092bdaae548ad2a05f91592fe11ec4`.

The governed raw evidence directory is
`X:\\CodexData\\maintenance\\evidence\\x_maintenance\\PS-HISTORICAL-CHECKOUT-RETIREMENT-002\\historical-retirement-completion\\03fdd9e1f61b`:

- `pre_retirement_measurements.json`: SHA-256 `F6711ECD20E17886A13B1397A45FD8EED8D3597984FE8D4F70AFDAA042C534E3`.
- `retirement_results.json`: SHA-256 `FBFD7C009E5612D553DE16DBE7E9A14E62C2476E55B2117E06BDA6949F46185A` (pre-command parser error only).
- `retirement_results_attempt2.json`: SHA-256 `9A7BCAE2FEF58CDA366E19E408E2705E650590AAEA6FBE2FD044D8D28007DD11`.
- `post_retirement_verification.json`: SHA-256 `A3508E94209390D02B8FFA473A19F94EEB004418B2686A20050C4632675776AC`.

| # | Path | Preserved branch | Preserved HEAD | Logical bytes | Recorded at | Proof SHA-256 |
|---:|---|---|---|---:|---|---|
| 1 | `C:\Users\peter\.codex\worktrees\c86c\portfolio` | `work/2026-07-28-api-foundation-gate-0-001` | `bd96ee1d23e0e1198fb98f02c1f80f19d7b928f4` | 612218309 | 2026-09-07T20:37:47Z | `e37fd089d93e9bc30fe59e3d566da2f5ec8b71e62a4dd67c2bc80ae64aee5d89` |
| 2 | `C:\Users\peter\Documents\Codex\2026-08-17\referenced-chatgpt-conversation-this-is-an\work\peerslate-ai-workflow-close` | `work/2026-08-17-delivery-pause-portable-session-manager-002-one-file` | `6c955d05828a503e1194597ddaec774ed219104e` | 956252139 | 2026-09-07T20:38:02Z | `2bb599f533f17cd6abb92e70322ca1cdae829561d099d76fe0a68d5efad754ef` |
| 3 | `C:\Users\peter\Documents\Codex\2026-08-17\referenced-chatgpt-conversation-this-is-an\work\peerslate-ai-workflow-one-file` | `work/2026-08-17-portable-session-manager-002-one-file` | `cd0bef14a7dee423c184dced7c7d5f700b0f0197` | 956251830 | 2026-09-07T20:38:17Z | `f6ffdd1316007ae967da07263a0e7c9afb87f2b8cb07e669f02e9008f0106a5a` |
| 4 | `C:\Users\peter\Documents\Codex\2026-08-17\referenced-chatgpt-conversation-this-is-an\work\peerslate-portable-manager-activation` | `work/2026-08-17-delivery-activation-portable-session-manager-002-one-file` | `815db282832d7b9c5724d38a0f69b3b92a0f50f7` | 956251633 | 2026-09-07T20:38:33Z | `fcbd983021e01e523c993a5349890e5005d8b42acd824034dfb7bcb760eb5290` |
| 5 | `C:\Users\peter\Documents\Codex\2026-08-17\referenced-chatgpt-conversation-this-is-an\work\peerslate-portable-manager-pause` | `work/2026-08-17-delivery-pause-portable-session-manager-002` | `538cec97847467da0da0ba07d97b08adfb207be3` | 956253282 | 2026-09-07T20:38:48Z | `d2838cf79365462d9ec8d81e2b330f581fa6a43b63af861ecdab6e870488954b` |
| 6 | `C:\Users\peter\Documents\portfolio-connect-002-anchor-repair-20260813` | `work/2026-08-13-delivery-activation-connect-002-merge-admission-anchor` | `c4399ddfd564310512a241f6390ba142b5b76f22` | 1053053903 | 2026-09-07T20:39:04Z | `4334bbded78c1cba968e0adb5b4452a9e126539d150366ce75611967fcc9bb6f` |
| 7 | `C:\Users\peter\Documents\portfolio-connect-002-profile-relationships-20260813` | `work/2026-08-13-connect-002-profile-relationships` | `db20e2285f82c0f61baa73c49cd6f0bee0771620` | 1044414914 | 2026-09-07T20:39:20Z | `ef9d8e1be88c93bb5dc5e2ddcbaff440bae65d3c4273bfa5ad79f25539bfbd7e` |
| 8 | `C:\Users\peter\Documents\portfolio-connect-002-provider-merge-20260813` | `work/2026-08-13-connect-002-provider-merge-001` | `f6b0e0809ef2fd21afc764162e9f0962911b3dcb` | 1053187242 | 2026-09-07T20:39:36Z | `ccc62a5add3b172c5943ae77b65c523aab8cb75a884d0004c7461f8c0c87ebad` |
| 9 | `C:\Users\peter\Documents\portfolio-delivery-activation-profile-experience-20260810` | `work/2026-08-10-delivery-activation-profile-experience-001` | `015a5f17a8fd1fdf3315f9f8c113c2209ab8a8ab` | 1029473061 | 2026-09-07T20:39:51Z | `917054933fbc8d70f04e4cee0671ded1ca5b941bc5a08bfb5435d125a35e45e4` |
| 10 | `C:\Users\peter\Documents\portfolio-delivery-activation-workshop-retirement-20260811` | `work/2026-08-11-delivery-activation-workshop-experience-retirement` | `8b0c29facfe1ff8468c6baa550dc80000e9f093c` | 1029462715 | 2026-09-07T20:40:06Z | `518d080a8b5d1dc4538a55f6dcdf94d7aa8fe457f2f0504b3f149d3c95cee30c` |
| 11 | `C:\Users\peter\Documents\portfolio-delivery-pause-control` | `work/2026-08-22-delivery-pause-delivery-control-signin` | `dd1f5434c7033d552e801c5ae8867c8924ed5950` | 964819742 | 2026-09-07T20:40:22Z | `d6720eafe74c8ec24adca29dcb213623e3b0129552fc30094d6c8455668b9af0` |
| 12 | `C:\Users\peter\Documents\portfolio-delivery-pause-signin` | `work/2026-08-22-delivery-pause-signin-member-arrival` | `05f12ba02f308a6e11b20d7a89c68c80d1caa48d` | 964817934 | 2026-09-07T20:40:39Z | `bce07c33618f96c2f6cf7c1f733cfd385a985681a4b834a7011d070fa958cf3f` |
| 13 | `C:\Users\peter\Documents\portfolio-interview-enablement-20260812` | `work/2026-08-12-interview-studio-enablement` | `61af32da46bba07463669d33293f29eae4348c8d` | 1043482098 | 2026-09-07T20:40:55Z | `64a67fb55bb7b44a95b801a3bb851c1afa84959170da2cee1b4c595f741dd0cf` |
| 14 | `C:\Users\peter\Documents\portfolio-member-feedback-direction-20260815` | `work/2026-08-15-member-feedback-direction` | `9e5391a5519e4fa6dd9dbab8db140d3690ac746d` | 955585180 | 2026-09-07T20:41:11Z | `7d236235bb86a98cf34bb86fae862a1a88e8f17c525d5c1352ce520a1cf57f2f` |
| 15 | `C:\Users\peter\Documents\portfolio-profile-core-activation-20260812` | `work/2026-08-12-delivery-activation-profile-core-001` | `530887b6ffebb081d26c72f06af2d07ea24c6061` | 1043780974 | 2026-09-07T20:41:26Z | `12e2f02add80671121916d9eb37fa54c610c66eb8fa1961ed102b9ed7ca97f47` |
| 16 | `C:\Users\peter\Documents\portfolio-profile-core-foundation-20260812` | `work/2026-08-12-profile-core-foundation-001` | `aa1fc7e889fa63e31a432074da5c5040698f4aea` | 1043935967 | 2026-09-07T20:41:42Z | `2115b024221e1914bfc1ecb46c974861fd3c96fa4dcd9789669b431fa764919f` |
| 17 | `C:\Users\peter\Documents\portfolio-profile-core-grant-20260812` | `work/2026-08-12-delivery-grant-profile-core-integration-001` | `fcd32ce7e87ab84bedb9ee681d1470774ea393f0` | 1043894844 | 2026-09-07T20:41:55Z | `8ffdfcebecbc93c26e56afc98de12ddf48da5333b5aba853682a1ea6b10f909a` |
| 18 | `C:\Users\peter\Documents\portfolio-profile-direction-activation-20260811` | `work/2026-08-11-delivery-activation-profile-direction` | `65c97cb61a23cef6f922825e965e668b4d795fe9` | 1029518395 | 2026-09-07T20:42:11Z | `eeb507a33cec8d400e0383183982807863e714999983a801ceda602ab966c234` |
| 19 | `C:\Users\peter\Documents\portfolio-profile-direction-close-20260812` | `work/2026-08-12-delivery-close-profile-experience-001` | `0b52090542b43564e6c17b4c1b43c8d8d1d889ed` | 1029796355 | 2026-09-07T20:42:27Z | `c0af4aa7b05ba1089b0510eed770a73306c628c4c1cd8cd5edc07c63793ce366` |
| 20 | `C:\Users\peter\Documents\portfolio-profile-direction-grant-20260812` | `work/2026-08-12-delivery-grant-profile-experience-001` | `78dc8e5afabf3f47b9613e3679deb0c54c1a2825` | 1029657532 | 2026-09-07T20:42:45Z | `0c7b927db74c9ba24047298263010215cbb2540eb3117c713915646affe96dc6` |
| 21 | `C:\Users\peter\Documents\portfolio-profile-experience-build-20260812` | `work/2026-08-12-profile-experience-build-001` | `78b0203fb8fbbbedefa9de499427755d02ac6fa2` | 1044164562 | 2026-09-07T20:43:01Z | `9c876c6eaffe2c60765474c4fdd5e1a9c2b3ca02cf7628864bbf73937b511e30` |
| 22 | `C:\Users\peter\Documents\portfolio-profile-experience-direction-20260811` | `work/2026-08-11-profile-experience-direction-001` | `7790e2684ad5a65a0371338f8b94f878276f36c7` | 1029642293 | 2026-09-07T20:43:17Z | `e5128b5a751bc4dedc90d36d9622e64f1509aa6e8df449e8cc100630e57783e2` |
| 23 | `C:\Users\peter\Documents\portfolio-site-audit-package-queue-20260813` | `work/2026-08-13-site-audit-package-queue-001` | `1b2b20808e20bd99af07e657622502cc7605bcb9` | 1053019438 | 2026-09-07T20:43:34Z | `4492fe35410dab0c51ebd6054f0db6cf2ab5b44e1644ed89ecc2e4d53acd83b9` |
| 24 | `C:\Users\peter\Documents\portfolio-site-audit-package-queue-pause-20260813` | `work/2026-08-13-delivery-pause-site-audit-package-queue` | `1a641331c7d45a388462e89c00f36981b621b106` | 1053019788 | 2026-09-07T20:43:51Z | `ee8a5318972876db0937812ee5444622a89cedc7ec6cbffedf6d6b88a31c1df3` |
| 25 | `C:\Users\peter\Documents\portfolio-site-audit-packages-activation-20260813` | `work/2026-08-13-delivery-activation-site-audit-packages` | `824c27aba19ddc8172dc10bd0239f2958a3ff197` | 1052990542 | 2026-09-07T20:44:09Z | `c75a4568c9c01e5eb8440fea612a5cb39b5372899e52aa052296cdcb6380d6e8` |
| 26 | `C:\Users\peter\Documents\portfolio-trust-safety-direction-20260815` | `work/2026-08-15-trust-safety-direction` | `41086bdde7b05e603ad915f9fe802579d41275f5` | 955620215 | 2026-09-07T20:44:27Z | `ac183a1d024fdc52692f3489e6ab04b7380243cc016a0834ca088401d8c02088` |
| 27 | `C:\Users\peter\Documents\portfolio-workshop-experience-001` | `work/2026-08-09-workshop-experience-001` | `553535478705f7fa3ff6bcd3725b8d08b9ebdb26` | 1031045365 | 2026-09-07T20:44:43Z | `236a31bf5a6cd16b9c2629be013a23222e3cdd74a9003f100e100a3cdca31dba` |
| 28 | `C:\Users\peter\Documents\portfolio-worktrees\portable-session-manager-002` | `work/2026-08-16-portable-session-manager-002` | `37c5a04414edb0b1cef5412ed3278a3ac1418d12` | 955602156 | 2026-09-07T20:44:58Z | `dafe823c713c6744c4544175c57f9f52e89be914e16e1ff84aa3b6d5dacff2c7` |
| 29 | `C:\Users\peter\Documents\portfolio-worktrees\portable-session-manager-002-activation` | `work/2026-08-16-delivery-activation-portable-session-manager-002` | `049f742d7cc895c7c4b18d57c454922f05f77d0c` | 955591589 | 2026-09-07T20:45:13Z | `035599a3ff4b5de73943dc7289dc6f4789e439f87cc0d5df9af547cd54cededd` |

The excluded and non-allowlisted inventory was untouched. Paused replacement
source package `PS-HISTORICAL-CHECKOUT-RETIREMENT-001` remains at checkpoint
`cd17e72a2e8e65c2a234439e6bfbc71943d99721` on branch
`work/2026-09-05-historical-checkout-retirement-001`, with its preserved
untracked `GROK_STATUS.md`. No branch, tag, ref, stash, history, object, raw
path, production, deployment, schema, identity, product, or visual state was
deleted or rewritten.

<!-- evidence-errata-authorization: session:01a07158-684b-74a2-a47e-7ca0e91889b7/owner-finish-2026-09-07 -->
