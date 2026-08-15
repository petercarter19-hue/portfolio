# PS-INTERVIEW-STUDIO-EXPERIENCE-POLISH-001 - Interview Me and Video Practice polish

**Status:** Planned - not active.
**Dependency:** The separately owned Interview Me inline strong-answer
restoration is released. Inspect the current live surface before any new visual
or functional decision.
**Authority placement:** Visual/interaction follow-up; it does not own AI answer
restoration or Ask My Slate.
**Runtime status:** No Interview code, layout, device, or release change is
authorized.

## Owner outcome

Interview Me becomes a comfortably bounded answer canvas. Video Practice looks
like a purposeful rehearsal tool rather than a giant empty banner surrounded by
duplicated status and oversized controls. The left rail has one consistent
rhythm.

## Owner-reported interaction intake - 2026-08-14

Pete reports that the left sidebar/rail still has awkward dropdown placement
and spacing, and that **New Session** behaves inconsistently or does not do what
the interface promises. Pete also challenged the session concept itself: the
next review must not preserve sessions or their restrictions by assumption.

Before visual work, compare two explicit product models:

1. a real session object with a clear purpose, lifecycle, resume behavior, and
   History relationship; or
2. a simpler question -> attempt -> review -> History model in which a member
   can begin anywhere without artificial session restrictions.

Prefer the simpler model unless sessions provide a demonstrated learning,
privacy, recovery, or organization benefit. Removing or migrating session
state is functional/data work and therefore belongs in a separately activated
package after the decision; this polish charter records the question but does
not authorize code changes.

## Interview Me composition

Use the existing `What the interviewer is listening for` measure as a visual
anchor and test an approximately 740-820px central answer plane on desktop.
The exact width is a visual-lock decision and must adapt responsively. This
package does not add a permanent right rail or change Claude's inline answer
flow.

## Focused interview window decision - owner-required 2026-08-14

Pete asked the next Interview Me review to determine whether the initial
written interview should be able to open in a cleaner pop-out window, and
whether that would feel classier and more focused than keeping the entire
experience inside the ordinary Studio page. This is an open comparison, not an
accepted visual direction or runtime choice.

Compare three honest alternatives before implementation:

1. the complete same-page Studio experience;
2. an in-page or same-tab **Focus mode** that temporarily removes secondary
   Studio chrome; and
3. a member-initiated dedicated browser window with only the question, useful
   role/context cues, answer composer, dictation, review action, recovery, and
   a clear return to Studio.

Judge the options on more than appearance. Record whether each one improves
attention, calm, interview realism, readable answer width, control hierarchy,
and movement between answering, coaching, retrying, and History. Also record
the costs: popup blocking, iPad/Safari opening a tab rather than a true window,
phone behavior, authentication/cookie continuity, duplicate windows, stale or
conflicting drafts, refresh and crash recovery, closing the focused view,
keyboard and screen-reader focus, zoom/reflow, and the member losing context
when returning to Studio.

The dedicated window, if selected later, must be progressive enhancement:

- It opens only from an explicit member action and never as an automatic
  popup.
- The same-page path remains complete and first-class when the browser blocks
  or cannot support a separate window.
- The member can return, stop, resume, change the role or question scope, skip,
  or move elsewhere at any time. A focused view must not recreate `New
  Session`, a fixed question count, or an artificial session object.
- One authoritative draft/history record prevents duplicate or divergent
  answers across windows. Closing either view cannot silently discard work.
- On phones and constrained tablet states, prefer the strongest usable
  same-page Focus mode unless real-device evidence shows a separate window is
  clearer.
- A pop-out cannot be used to conceal an early responsive collapse or a broken
  Studio layout. Preserve the desktop composition until measured content
  pressure requires reflow, and make the ordinary page work at every supported
  width.

The decision gate requires side-by-side owner review of the same realistic
question and long-answer flow on desktop plus real iPad portrait/landscape and
phone evidence. Select a dedicated window only if it produces a meaningfully
better focused experience without weakening continuity, accessibility,
recovery, or member freedom. ChatGPT supplies any materially revised visual
direction and Pete locks the selected authority before a later implementation
package is activated.

## Video Practice correction

- Bound the camera stage to a true 16:9 composition; initial desktop targets are
  approximately 920x518 or 960x540 rather than full available width.
- Center the unavailable state in the actual stage. Current inspection suggests
  the outer frame and unavailable layer use different widths, creating the
  visible off-center result.
- State camera/microphone failure once, in the stage, with one primary recovery
  action and a secondary transcript fallback.
- Move detailed permission/device guidance behind a quiet Help action.
- Keep privacy truth visible: local recording is not uploaded, saved, or
  analyzed unless a later protected decision explicitly changes that.
- Attach compact Record/Stop/timer controls to or over the stage. Avoid large
  buttons floating far below what they control.
- Make transcript practice progressive: reveal it when chosen instead of
  permanently stacking a second large workspace under the camera.

## Left-rail rhythm

Create shared tokens for selectable item height, row gap, icon alignment, and
section gap. Test an initial rhythm near 40px items, 8px row gaps, and 20px
section gaps, then lock it visually across mode navigation, Current Session,
and Session Tools.

Include dropdown trigger placement, expanded/collapsed states, long labels,
empty and many-item states, focus return, and the interaction between Current
Session and Session Tools. Test real iPad/tablet behavior in addition to desktop
and phone emulation.

## Acceptance gate

After Claude's release, capture current 390px, 768px, and desktop states; create
a fresh ChatGPT visual direction; obtain Pete's acceptance; then validate live
camera, denied permission, no-device, keyboard, screen-reader, reduced-motion,
and transcript-fallback paths without weakening product truth.

The gate also requires an owner-accepted decision on whether **New Session** and
the session object remain, plus functional evidence that the accepted model is
consistent across refresh, repeated starts, unfinished attempts, History,
second tab, sign-out/sign-in, and failure recovery.
