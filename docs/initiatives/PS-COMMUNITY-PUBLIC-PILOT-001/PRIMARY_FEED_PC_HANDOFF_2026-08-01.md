# PeerSlate Community primary Feed PC handoff

## Handoff state

- Owner/receiver: Pete Carter on his PC.
- Visual decision: approved by Pete on 2026-08-01 after the compact response
  picker and comment-entry corrections.
- Scope: primary `/the-slate` Feed page only.
- Branch: `codex/2026-08-01-community-primary-feed-sol-ultra`.
- Working-tree HEAD: `3210e4030fae30bd45fb05f4ce8351b26c4ee3f1`.
- Authoritative `origin/main` and merge base:
  `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`.
- Release state: local only; unstaged, uncommitted, unpushed, feature-default-off.

## PC continuation and Mac receipt

The transfer was restored on Pete's PC with the exact HEAD, patch, overlay,
status paths, and SHA-256 hashes verified. Pete then instructed that lane to
continue the package. The original Mac-to-PC transfer facts remain historical
provenance; they are not a release claim.

Pete's subsequent PC review rejected the expanded Voice activation panel below
the compact comment row. The corrected primary Feed retains only the compact
microphone and Send controls in that row; the microphone remains truthfully
unavailable. No Community Voice endpoint, service, recording controller, or
secondary Voice panel is part of this handoff state.

Pete later froze the PC lane and transferred sole active-writer ownership back
to this Mac task using the checksum-verified continuation ZIP recorded in
`PC_TO_MAC_COLLISION_MATRIX_2026-08-01.md`. The Mac accepted the PC-only and
PC-newer source truth after a 17-file SHA-256 comparison found no Mac-newer or
unresolved collision. The PC remains frozen; the Mac continuation does not
change the local-only release state.

The iCloud ZIP contains a Git bundle for the starting checkpoint, a binary Git
patch for tracked changes, an exact source overlay containing every changed or
new file, the package authorities needed to understand the slice, test and
Git metadata, screenshots, and SHA-256 manifests.

## Restore on the PC

1. Copy the ZIP to a local folder and verify its adjacent `.sha256` file.
2. Extract it and open `README_FIRST.md`.
3. Use the included Git bundle to restore the exact starting checkpoint if the
   branch is not already available locally.
4. Apply `patch/community-primary-feed-working-tree.patch`, then copy
   `source-overlay/` over the repository root to add the untracked files and
   guarantee byte-for-byte parity with the handoff manifest.
5. Confirm the repository is still on the branch and HEAD above. Run the
   focused verification commands recorded in the package before making new
   changes.

Do not treat this file transfer as a commit, push, PR, merge, deployment,
Candidate activation, or live/public Community state.

## Work explicitly not begun

- Full-post modal or full conversation page.
- Nested reply branches or full-conversation reply composer behavior.
- Voice states A-H, microphone permission, recording, transcription, and
  failure handling.
- SQL migration, Azure Blob/Speech, retention, Break, or Candidate work.
- PR, merge, deployment, feature-flag activation, or any live/public claim.

The receiving writer must re-open `START_HERE.md` and current governance on the
PC before any new implementation or release action.
