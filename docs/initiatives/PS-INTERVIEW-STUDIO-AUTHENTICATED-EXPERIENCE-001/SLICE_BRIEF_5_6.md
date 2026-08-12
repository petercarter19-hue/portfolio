# Slice 5-6 Implementation Brief — Preserved Destinations + Responsive/Visual Finish

Same writer rules and visual authority as the earlier briefs. Architecture files 03 §3-5, 06, 07
govern. All work applies to the authenticated (flag-on) composition unless stated; flag-off stays
byte-comparable.

## Slice 5 — preserved destinations to the locks

1. **Interview AI** (visuals 07/08): heading "Explore a strong answer." + "See how a strong answer
   could be framed."; SOURCE selector as three radio cards `Best practice / My public profile /
   Compare` with the exact sublabels; info line "If approved public evidence is unavailable,
   PeerSlate keeps the result insufficient instead of inventing it."; generic result block
   labelled GENERIC BEST-PRACTICE EXAMPLE with WHY THIS WORKS three-up and the exact line "This
   is an illustrative example. It is not presented as your experience."; actions Practice This
   Answer (primary) / New question / `Follow-up isn't available yet` (disabled — the affordance
   renders but stays disabled while the `interview_followup_mode_provenance` finding is open;
   keep the token plumbing intact). Insufficiency lock (08): NOT ENOUGH APPROVED PUBLIC EVIDENCE
   composition with "Nothing was invented or borrowed from another person." and actions
   Use best practice / Change question / disabled follow-up.
   Server: grounded/Compare for a non-owner identity returns the insufficiency object (slice 2
   already scoped evidence); owner identity grounds on the petec fixture (Pete's Q-C decision).
2. **Video Practice** (visuals 09/10/15): eyebrow "VIDEO PRACTICE / Rehearse locally on camera.";
   status chips (`Camera ready`/`Microphone ready`; playback `Local recording ready · MM:SS`,
   `Video ready`/`Audio available`/`Local playback`); media truth line under the frame; actions
   Start recording / Turn camera off / Device settings; playback Play recording / Record another
   take / Discard recording (destructive red); CONTENT COACHING block with Add transcript /
   Dictate and the no-inference line "Video Practice does not analyze eye contact, appearance,
   confidence, emotion, personality, pace, or delivery."; recovery lock (15): "Camera access is
   unavailable." + "PeerSlate will not request permission again until you choose Try camera
   again." + "No recording was created. PeerSlate does not upload, save, or analyze video." +
   Use transcript instead (primary) / Try camera again / Camera help. FIX: `releaseMedia()` must
   revoke `media.playbackUrl` on every teardown path (JS :679-695 + call sites).
3. **Session Complete** (visual 11): centered SESSION COMPLETE composition, "You finished this
   practice session.", "N questions were practiced. N answers were reviewed in this browser.",
   three cards FROM THIS SESSION / NEXT FOCUS FROM THIS SESSION / QUESTIONS REVIEWED, the
   browser-truth info band, actions Practice the next focus / Start a new session / Open History.
   Completed rail state per slice 4.
4. **History** (visuals 12/16/17): "Your practice in this browser." + Start Interview Me button;
   three filters (All modes / All question families / Most recent); populated rows (icon, question,
   mode · family, date, Reviewed chip, View review, overflow menu); COMPARISON STATUS card with
   EXACT gate string "Not enough comparable practice yet." plus "More like-for-like reviewed
   answers are needed before PeerSlate shows a pattern." (gate: ≥2 reviewed attempts same
   family+mode — implementation constant, tested); FROM YOUR <date> REVIEW card labelled "This
   comes from one recent coaching review, not a cross-session trend."; BROWSER STORAGE card with
   truth + clearing consequence + Clear local History (destructive, confirmed). Empty lock (16):
   "Browser storage is available" ✓, "No reviewed answers yet.", NO Clear action, Start Interview
   Me / Change setup. Unavailable lock (17): "History is unavailable in this browser right now.
   Practice can continue without it.", "Practice records cannot be read or saved here right now.",
   "PeerSlate cannot read or write Drafts or History in this browser.", "Nothing was cleared or
   deleted.", Continue without History (primary) / Try History again / Storage help; rail warning
   variant. Filtered-empty is a distinct state (filters active, records exist).

## Slice 6 — responsive, accessibility, failure finish, visual comparison

1. Stress evidence per architecture 07: 320×568, 390×844, 1366×768, wide (~1672), 200% zoom
   one-dimensional reflow; keyboard-only walk; focus trap/return on dialogs; visible focus
   everywhere; live-region announcements (pending/success/failure/canceled/storage/dictation/
   media); reduced motion; no horizontal page scroll; no inner page scroller; nothing covers
   keyboard/caret/new consequence heading; 44×44 touch targets.
2. Long-content stress: 300-char question, 5,000-char answer/revision, 1,200-char confirmed
   context, five dimensions, four improvements, two long evidence suggestions, long setup labels,
   large History (100 records), filtered-empty, storage/AI/media failure.
3. **Side-by-side comparison against ALL 19 locked visuals.** Use headless Playwright
   (`venv` has it per project test environment; fall back to installing browsers via
   `python -m playwright install chromium` if needed) serving the app locally with the flag ON and
   a test identity (set `PEERSLATE_ALLOW_DEV_IDENTITY`/`PEERSLATE_DEV_USER_KEY` — the established
   dev-identity mechanism, app.py:211-214) — never against production. Reproduce each locked
   state (scripted DOM state injection is acceptable for provider-dependent states using the
   deterministic test fixtures), capture at the visual's native aspect, and iterate with the
   visual-parity method (depth/texture/density first) until each state reads the same. Archive
   screenshots to `artifacts/2026-08-11-interview-studio-authenticated/visual-comparison/`
   named after the corresponding lock file. Any state you cannot make read the same without a
   material composition change: STOP and report the exact mismatch.
4. Negative regression: the guard strings (no scores/STAR/rank/inference/cloud claims) all still
   pass; "for this account" allowed, "saved to your account" forbidden.

Definition of done: all suites green; comparison set archived and self-judged against every lock;
SLICE_NOTES complete with honest limitations; no push.
