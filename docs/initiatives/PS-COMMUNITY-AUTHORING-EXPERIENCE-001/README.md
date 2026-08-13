# PS-COMMUNITY-AUTHORING-EXPERIENCE-001 - Compact, focused Community authoring

**Status:** Planned - not active.
**Authority placement:** Proposed material revision to the current Community
direction; the existing accepted visual authority controls until superseded by
a new ChatGPT-created, Pete-accepted lock.
**Runtime status:** No composer, audience, attachment, rail, or feed change is
authorized.

## Owner outcome

Creating a new post becomes a focused overlay rather than a large form inserted
into the feed. The surface borrows the interaction grammar visible in Pete's
Facebook references while retaining PeerSlate's brand, truth, privacy, and
attachment model.

The references show a **new-post launcher and modal**, not Facebook comments.
PeerSlate comments should remain compact and inline unless a later decision
establishes a separate reason for a comment modal.

## New-post direction

- Clicking `What's on your mind?` opens a centered modal over a dimmed/mildly
  blurred but recognizable Community page.
- Initial desktop target: approximately 560-620px wide; use a sheet or
  full-screen composition where mobile space requires it.
- Header: `Create post` and one accessible X. Escape closes; focus is trapped;
  the background is inert; focus returns to the launcher.
- Show avatar/name and a compact **labeled** audience pill near the author.
- Provide one clean writing plane and a compact attachment row for File, Photo,
  and Video. Voice follows the shared dictation package and creates text, not a
  public audio attachment.
- Use one **Post** button. Remove the redundant Cancel button because X exists.
- Remove `Response posture` from the composer for now while preserving any
  stored/default value required by current data truth.
- Remove the `Public audio` placeholder.

## Audience and publication truth

Do not turn Audience into an unlabeled mystery icon or pretend choices exist.
If the actual destination is only Community, show a labeled `Community` pill.
If multiple audiences are implemented later, the selector must expose real,
authorized choices and the chosen audience must remain unmistakable.

`Review public post` may become a single `Post` action only after the package
decides whether that action is consequential public publication. Removing an
extra screen must not remove informed publication truth or create a fake safety
claim.

## Rails

Review rails by job and responsive breakpoint, not by a specific 24-inch
monitor. Preferred direction to test:

- left rail = stable destinations that genuinely exist;
- center = bounded feed and authoring launcher;
- right rail = live context backed by real queries.

Potential destinations or modules such as Following, My posts, Saved, Drafts,
Sparks, people, or active conversations must not be rendered as fake routes or
empty scaffolding.

## Draft and accessibility decisions

Decide what X does to a non-empty draft, whether reopening restores it, and how
attachment upload failure is shown. The modal must meet keyboard, focus,
screen-reader, reduced-motion, mobile keyboard, and scroll-lock expectations.

## Explicit closeout

The existing single genuine test post is accepted. This package must not seed
fake posts, recreate missing test content, or diagnose a closed feed issue.
