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
