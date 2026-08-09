# Community Retention Decision v1.0 (Authenticated Audience)

**Status: APPROVED by Pete, 2026-08-08, as drafted — in force for the authenticated Community stage from the wall's release.**
**Prepared:** 2026-08-08 by Claude (Community auth-wall session); approved in the same session via explicit owner selection.
**Supersedes when approved:** the public-pilot retention decision, which Pete marked "alive for this update. We will readdress this when we hide this behind the signin experience."
**Package:** PS-COMMUNITY-AUTH-WALL-001 (proposed) — this reapproval is required before the sign-in wall releases.

## What changes and what doesn't

The Community audience changes from *anonymous public* to *signed-in PeerSlate members* (reads) with owner-only authoring. This document restates every retention duration for that authenticated audience. **No durations change** — the recommendation is to retain the current windows for the narrow authenticated stage. Only the audience language changes: every "public recipient" statement becomes an authenticated-recipient statement.

## Proposed retention terms (unchanged durations, authenticated audience)

| Item | Retention |
|---|---|
| Deleted post/contribution bodies and revisions | 30-day recovery window, then purge |
| Ready attachment delivery after removal | Revoked immediately |
| Removed attachment bytes | Targeted physical deletion within 1 hour |
| Restored text | Does **not** restore already-deleted files |
| Unattached uploads | Maximum 24 hours |
| Body-free audit events | 90 days |
| Processed outbox | 30 days |
| Resolved/abandoned outbox | No later than 90 days |
| Browser-local drafts | 30 days without edit |
| Raw Community search queries | Never retained |
| Blob soft-delete recovery | 7 days |
| SQL short-term recovery | 7 days |
| Long-term Community backup retention | None |

## Honest limits Pete is asked to acknowledge

1. **Recipients are now authenticated members, not the public** — but content a signed-in member has already seen, screenshotted, downloaded, or copied **cannot be recalled** by deletion, retention windows, or the sign-in wall itself.
2. Content that was public during the pilot may already exist in screenshots, downloads, caches, or third-party copies. The wall does not and cannot retract those.
3. **Legal hold limitation preserved:** deleted attachment *bytes* are physically removed on the schedule above and are not recoverable for a later legal hold; legal holds protect what the hold captured, not what deletion already destroyed.
4. Retention and media cleanup run independently of Community visibility — turning Community off does not stop already-owed cleanup.

## Conditions of approval

- This decision will be **dated and versioned** on approval and published in the authenticated Community policy page (`/the-slate/policy` or equivalent) — replacing the public-pilot policy, which is preserved as repository evidence.
- Behavior will be **reverified** against these terms (deletion, revocation, purge timing, hold behavior) as part of the wall package's release evidence, not assumed from the pilot's evidence.

## Approval

- [x] Approved as written (durations unchanged, authenticated-audience language)
- [ ] Approved with changes (note below)
- [ ] Not approved — revise

Pete's decision & date: Approved as drafted — 2026-08-08

*Prepared by AI as a proposal. Nothing here is in force until Pete approves; AI does not decide retention.*
