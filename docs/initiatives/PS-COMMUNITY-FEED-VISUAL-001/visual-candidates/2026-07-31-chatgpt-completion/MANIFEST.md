# Community Feed missing-state candidate manifest

## Status

- **Creator:** ChatGPT visual-creation lane using the built-in image generation
  path
- **Custodian:** current Codex task
- **State:** candidate; not Pete-locked visual authority
- **Primary references:** the six immutable files in
  `PS-COMMUNITY-FEED-DIRECTION-001/visual-authority/2026-07-31-pete-lock/`
- **Owner decision:** pending exact-file review

## Candidate files

| File | Board purpose | Raster size | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `00-feed-availability-and-completion.png` | Feed availability and completion | 1536 x 1024 | 1175705 | `1BD5A05715BD8CA44F35F6EE6A6AB87C5B8E822C9C0F9ABB37FB79308005AAC7` |
| `01-composer-and-publication.png` | Composer and publication | 1536 x 1024 | 1373731 | `A87171E39DDB48B8546B5EAA73E97FAD80747DB9AAA9D5FB74FEFCE6D2BAF29F` |
| `02-search-shell-and-signed-out.png` | Search, shell, and signed-out truth | 1536 x 1024 | 1586986 | `3CB39702C05ABFA37EC4115AD50D47B50847031EBAB4944F3F569FCC1914BF2A` |
| `03-conversation-lifecycle-and-safety.png` | Conversation lifecycle and safety | 1448 x 1086 | 1198869 | `0A8B343C33102779C9AA7332DB9F846A96F766607F0C9660CAD3332B4F9923DC` |
| `04-visible-actions-and-messaging-truth.png` | Visible actions and messaging truth | 1536 x 1024 | 1590737 | `87360C9E084F20E814A03874132E4D22068A95671EF0D1187B952081CDA01A86` |
| `05-responsive-theme-and-mobile-modules.png` | Responsive, theme, and mobile module disposition | 1536 x 1024 | 1480767 | `6E9BAD74067FBDC7C890C17F571FA27E4A930B5F978829E55C1E8EB94A1D95DA` |

## Internal review and refinements

- Compared all six candidate boards with the six immutable primary-journey
  files after copying them into the workspace.
- Regenerated the search board once to remove an invented mobile bottom
  navigation bar; the final candidate preserves the locked header-only shell.
- Regenerated the action board once to remove an unrelated author menu from the
  active Respond state; Respond and menu permissions are now separate panels.
- Confirmed the set preserves one horizontal Replies & updates row, finite Feed
  behavior, Community-local rails, separate Break boundary, disabled messaging,
  and payload-negative unavailable/signed-out states.
- Confirmed no locked source file was overwritten or modified.

## State-family coverage

| State family | Candidate evidence | Established behavior that does not need a separate bespoke board |
| --- | --- | --- |
| Loading, empty, partial/full unavailable | Board 00 | Per-module variants reuse the same bounded skeleton, empty, unavailable, and retry patterns without changing layout. |
| Composer, audience, Spark, attachment, publish recovery | Board 01 | Gallery/video/document rows reuse the shown attachment lifecycle and the already locked full-media versus compact-cue distinction. |
| Search, signed-out, payload-negative failures | Board 02 | Permission denial reuses the payload-negative pattern in board 03. |
| Long conversation, pagination, edited/deleted/held/revoked truth | Board 03 | Other long names/files/content use the same semantic wrapping, truncation, expand, and tombstone components. |
| Respond, menus, Save recovery, messaging truth | Board 04 | In-flight/selected action variants use established button progress/selected states and never change hierarchy. |
| Mobile module disposition, 200% reflow, focus, theme, landscape/large text | Board 05 | Reduced motion means no auto-scroll, shimmer, carousel, or animated progress; keyboard order follows the semantic DOM defined by the architecture. |

The lean Visual Integrity Standard requires enough exact material to make the
journey and critical state behavior unambiguous, not a bespoke raster for every
data combination. Runtime evidence must still exercise every applicable state
listed in the direction package.

## Lock boundary

Generation does not equal approval. Pete must inspect the exact saved files.
After approval, the accepted bytes are copied to a separately named Pete-lock
directory with a final manifest; rejected candidates remain non-authoritative
evidence or are removed through a separately authorized cleanup.
