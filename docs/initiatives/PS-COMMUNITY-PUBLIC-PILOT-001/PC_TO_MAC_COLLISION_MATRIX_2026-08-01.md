# Community PC-to-Mac continuation collision matrix

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`  
**Audit date:** 2026-08-01  
**Mac worktree:** `/Users/petercarter/.codex/worktrees/6be8/portfolio`  
**Branch:** `codex/2026-08-01-community-primary-feed-sol-ultra`  
**HEAD:** `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1`  
**Authoritative `origin/main` and merge base:**
`2494aa73ed95bfbe97d8cf42f712b9929759e0b2`

## Package verification

- ZIP:
  `/Users/petercarter/Library/Mobile Documents/com~apple~CloudDocs/ChatGPT/PeerSlate-Community-PC-to-Mac-Continuation-2026-08-01.zip`
- Expected and verified ZIP SHA-256:
  `be06e6efade43a3e0c73176930fb63f2e3a4f7ba714bb9cc9819348ac219666e`
- ZIP integrity: **PASS** (`unzip -t`).
- Payload integrity: **PASS**, all 59 entries in `PACKAGE_MANIFEST.sha256`.
  The Windows-authored manifest uses CRLF line endings, so verification used a
  temporary LF-normalized copy on macOS; no package file was altered.
- Binary patch inspection: complete. Applying it wholesale was intentionally
  rejected because the Mac worktree already contained the overlapping handoff
  state. Reconciliation is file-by-file.

## Source-overlay matrix

`PC-NEWER` means the PC file contains a strict continuation of the overlapping
Mac handoff state. `PC-ONLY` means the file was absent on the Mac. No
`MAC-NEWER` or unresolved `COLLISION` item was found.

| Repository-relative path | PC SHA-256 | Mac SHA-256 at audit | Result | Material difference | Recommended action | Final action |
| --- | --- | --- | --- | --- | --- | --- |
| `docs/initiatives/PS-COMMUNITY-FEED-VISUAL-001/visual-authority/2026-08-01-pete-voice-first-lock/MANIFEST.md` | `404233bee2a4c1d4516bcb1983894b1098c60a91d2b54a2614a4dc9d022911c7` | `163fefb2316742d112c1bc3f51ecff8d6d1345cce30694968e249d8d0633bff3` | PC-NEWER | Records Pete's compact emoji rail, comment row, single unavailable Voice affordance, and final 500px card correction. | Adopt, then append later owner corrections without rewriting the lock. | Manually reconciled. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRIMARY_FEED_ARCHITECTURE_AMENDMENT_2026-08-01.md` | `bf98dbb61da755cc3d3935f030911006febbd92f2db165b16b7beccf322e19d6` | `26a33ad20e85046e5e79b98031fc199d7a628f2ee09e6b3b406cf307a88160fd` | PC-NEWER | Adds the compact response/comment/Voice placement contracts. | Adopt and update the post-local shelf mapping for the Mac continuation. | Manually reconciled. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRIMARY_FEED_PC_HANDOFF_2026-08-01.md` | `e1822c5c4e1c8c8a1cbdaa95050980237b29d0bc87b8057c0a71fea6ca05d55b` | `6a8d1ce7e18e8b0ac1ec73d94549d7a92d033eba4b411abf57c003586c7e29e2` | PC-NEWER | Adds final PC width and Voice-correction evidence. | Preserve as historical transfer evidence and append the Mac receipt state. | Manually reconciled. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/PRIMARY_FEED_REVIEW_CHECKPOINT_2026-08-01.md` | `487ebb2217618d7e37c876e699f2883f1aec9293d21aeb8bdc941e712d1d2efc` | `cc741332e0aac86b22a30ba55bc4db9826c3c0ac343ced97842453999be6bf5f` | PC-NEWER | Adds final 500px desktop evidence and PC validation. | Adopt as historical evidence; append a separate Mac continuation checkpoint after fresh validation. | Adopted; retained as PC checkpoint. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/README.md` | `1c24296eb0c0c09d1748ea0d1d256a29b47d98e0a9c1c30360e5d794c93a573e` | `e3e5d7e20a8645addcfaf146a660ad653bdd8088df94ecc4bc95dd2dc8d4d86b` | PC-NEWER | Correct branch and PC continuation/Voice truth. | Adopt facts and record transfer back to the Mac sole writer. | Manually reconciled. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-approved-current-browser.png` | `5c358d2dcf3219c7ff2af9aebad8e36f6f926bba1d32b950318d5c72e34391bc` | same | MATCH | None. | Retain Mac copy. | Retained. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-comment-entry-mobile-320x1101.png` | `16dfac3493b8d48eb53ca0f843a29d1bd2fae90a6f97874a43e87101c556f672` | same | MATCH | None. | Retain Mac copy. | Retained. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-desktop-1536x1024.jpg` | `b98ba68440aa958c33cd3bd358afe105bcb8d2eaa930edb1cc7fbf313776591a` | same | MATCH | None. | Retain Mac copy. | Retained. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-final-desktop-1536x1024.png` | `d3954053a4662ffda5e262485963805fd9c4df2dfdd355573b832e35b6a8ff1f` | MISSING | PC-ONLY | Final PC desktop top-of-page evidence. | Preserve as PC evidence, not as fresh Mac proof. | Adopted. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-final-desktop-lower-1536x1024.png` | `0cebf4956d0882488f818a6300c95fcae1e1e1b4dc432c1557991898fe40bfac` | MISSING | PC-ONLY | Final PC desktop lower-page evidence. | Preserve as PC evidence, not as fresh Mac proof. | Adopted. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-final-respond-and-comment-desktop-1536x1024.png` | `20791dc5d06ef70efccfb7203fe33dc78a9692c0ee908687b42be340eb4b31c9` | MISSING | PC-ONLY | Final PC compact Respond/comment evidence. | Preserve as PC evidence, not as fresh Mac proof. | Adopted. |
| `docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/evidence/2026-08-01-primary-feed-respond-rail-desktop-1536x1024.png` | `d17dad38ec854ebf8c96b6c03cc4a2426b6eacd029815b598a13cbc10d0349c7` | same | MATCH | None. | Retain Mac copy. | Retained. |
| `scripts/preview_community_primary_feed.py` | `b016b3efe5ae00c6defa9f95945a65e9c16763d30a017b7e8871f6e50f3c3e04` | same | MATCH | None at transfer. | Retain, then extend only with truthful in-memory shelf fixtures. | Retained and continued. |
| `static/css/community-v1.css` | `1d900719be2b61a87952607d7fc299ca70c2423ce24f4e870c8c8f4487fc20d9` | `3c4aa10d3cb5f2f48a9c1446cde66d2b1b3257f5461c2114539a1d7bcdbebf72` | PC-NEWER | Final 500px Feed width and typography corrections. | Adopt, then reconcile the locked rails/shelf and Pete's later restrained-color correction. | Manually reconciled. |
| `static/js/community-v1.js` | `4ebc5ac37ec2bf7a0a54b12d68ff0df9c1c2fb6d1fd25585c2d75f027d09ed9e` | `063d4b8a2a5910414bb799c9868623d8dae3c743329fcef096258153cddb8f18` | PC-NEWER | Removes the incorrect boolean `aria-haspopup` from the compact Respond rail. | Adopt and reconnect the already-built post-local shelf renderer. | Manually reconciled. |
| `templates/community_feed.html` | `d5626fd048189a163f6833c38a6bbc92ae207bfbc438a7eda9f791dde26119ec` | same | MATCH | None. Existing left/right rail markup is preserved. | Retain. | Retained. |
| `tests/test_community_public_pilot.py` | `a90f378541a70941ee095fae7cac19021e07220a180e53e9c4e4254804ab291b` | `16f085edeac8a0812ddf7ad3f559d16c2a90ecf0d90f10350154690b6df20153` | PC-NEWER | UTF-8 portability, 500px sizing, Respond semantics, and typography assertions. | Adopt and update focused contracts for the reconnected shelf and rails. | Manually reconciled. |

## Mac-only preserved evidence

`COMMUNITY_VOICE_VERTICAL_SLICE_ARCHITECTURE_AMENDMENT_2026-08-01.md` is
preserved unmodified as collision evidence. The PC package explicitly did not
adopt it as active authority, and this continuation does not implement a Voice
runtime. The compact microphone remains the sole unavailable Voice affordance
on the primary comment row.

## Ownership conclusion

The frozen PC lane formally relinquished `PS-COMMUNITY-PUBLIC-PILOT-001`.
Pete designated this Mac task as the sole active writer. No competing mutable
Community lane was found in this 17-file overlay, and reconciliation can
continue without deleting, stashing, cleaning, rebasing, committing, pushing,
merging, deploying, migrating, or enabling the default-off feature flag.
