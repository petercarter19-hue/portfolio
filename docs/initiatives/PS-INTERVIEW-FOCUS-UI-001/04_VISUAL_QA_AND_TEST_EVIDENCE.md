# Visual QA and Test Evidence

Date: 2026-07-29

## 1. Authority and frozen runtime

- Initiative: `PS-INTERVIEW-FOCUS-UI-001`
- Branch: `work/2026-07-28-ps-interview-focus-ui-001`
- Exact implementation base:
  `a85ffbc93a1def86f99db66df26702a59aff4cbc`
- Frozen runtime SHA:
  `0b2d5ffa6aac56dbb6736bbeb5cee13c8baffeb7`
- Controlling visual package:
  `source-authority/v3/`, revision `v3-all-modes-complete`
- V3 archive SHA-256:
  `7FF3187C7F7E62A29FFD15433454AA0742302308249B4AACA9ED8DBED809814F`
- Supplemental visual package:
  `source-authority/v2-white/`
- V2 archive SHA-256:
  `F968CEDF57CD064B748861472658FEAB87EF7C0603C277BAAAEDA2C2649B7E4D`
- Both package manifests verified 52 of 52 entries with zero failures before
  implementation.
- Pete approved the complete V3/V2 direction and then supplied one binding
  correction: multiline answer, transcript, and improved-draft fields must
  begin at about half the pictured height and grow automatically with content.

No new bitmap or production-intent artwork was required. The implementation
uses the approved packages, Pete's compact-height correction, and narrow
truth, accessibility, focus, and responsive adaptations. ChatGPT image
generation was not invoked.

## 2. Compare-refine record

The approved mockups and written contracts were reopened during every
visual-affecting cycle.

| Cycle | Compared scope | Correction and result |
|---|---|---|
| 1 | V3 screens 01-14, V3 AI/Video contracts, V2 white spacing | Reorganized all four Studio destinations into the approved focus-stage hierarchy while retaining the current routes, payloads, storage, media, and truth boundaries. |
| 2 | Ready, improve, transcript, restored-draft, and long-content states | Applied Pete's compact-height override, one shared auto-grow contract, hidden-field refresh, and no-clipping/no-max-height behavior. |
| 3 | Independent-review findings across desktop and mobile | Corrected state-specific rails, AI DOM order and workspace replacement, follow-up grounding continuity, transition focus, dictation/context-save ordering, hidden-field growth, contrast, and mobile camera safe areas. |
| 4 | Full state matrix against all V3 screens and written contracts | Regenerated ready, queue, processing, coaching, improve, AI, Video, History, failure, storage, reduced-motion, reflow, and homepage comparison evidence. |
| 5 | Shared-shell and route-capability review | Preserved route-specific Ask Pete AI access while preventing the global floating launcher from overlapping Interview Studio task controls. |
| 6 | Frozen-runtime browser review after responsive queue changes | Found and fixed an Escape focus-restoration race after desktop to mobile to desktop queue transitions. The final browser trace proves nonmodal desktop, modal mobile, nonmodal desktop return, Escape close, and focus restoration to the visible opener. |

The cycle-6 correction is the frozen runtime commit
`0b2d5ffa6aac56dbb6736bbeb5cee13c8baffeb7`.

All 14 V3 authority screens are mapped to exact final implementation captures
in `artifacts/interview-focus-ui/visual-authority-comparison.json`. Authority
and implementation dimensions match for every mapping. Every mapping is Pass.

Final mismatch register: empty.

The following are permitted adaptations, not open mismatches:

1. Multiline fields start shorter because Pete explicitly overrode the supplied
   empty-field geometry.
2. Long content grows the document instead of clipping or using fixed internal
   scrolling.
3. Current repository truth, provenance, permission, storage, and failure copy
   controls where illustrative package wording was broader.
4. Mobile and narrow layouts use one-column reflow and preserve fixed
   navigation safe areas.
5. The released shared shell remains authoritative. Route-specific Ask Pete AI
   access is retained, and the overlapping global floating launcher is hidden
   on this route.
6. Desktop question queue presentation is nonmodal and integrated into the
   rail. Narrow presentation is a modal bottom sheet.

## 3. Evidence inventory and integrity

Evidence root:
`artifacts/interview-focus-ui/`

The frozen-runtime evidence set contains:

- 103 PNG captures;
- 12 JSON evidence files; and
- 115 entries in `SHA256SUMS.txt`.

The manifest covers every PNG and JSON evidence file, including
`evidence-summary.json`, and excludes the manifest itself. Verification on
2026-07-29 found exactly 115 entries with zero missing, extra, or mismatched
files.

The 12 JSON evidence files are:

- `accessibility-focus-motion.json`
- `evidence-provenance.json`
- `evidence-summary.json`
- `layout-overlap-metrics.json`
- `queue-responsive-transition.json`
- `text-growth-metrics.json`
- `video-cleanup-lifecycle.json`
- `video-media-network-lifecycle.json`
- `video-route-load-permission-trace.json`
- `video-storage-before-after.json`
- `video-transcript-request-contract.json`
- `visual-authority-comparison.json`

`evidence-provenance.json` records all 103 captures, their requested viewport,
actual PNG dimensions, route and Studio state, theme, scroll dimensions, and
capture boundary. Its assertions pass:

- every PNG has provenance;
- every viewport PNG matches its requested dimensions;
- full-page PNGs preserve their requested width; and
- no captured Studio state has horizontal overflow.

## 4. Visual and state coverage

The PNG set covers:

- Interview Me ready, queue, processing, coaching failure, coach review,
  improve, listening, keyboard focus, reduced motion, dark theme, long content,
  and short/desktop/tablet/mobile/landscape/reflow viewports;
- Interview AI ready, loading, initial failure, approved-public-history result,
  best-practice result, compare, insufficient grounding, long answer, long
  sources, follow-up drafting, follow-up generation, follow-up result,
  follow-up failure, mobile states, and dark theme;
- Video Practice camera-off, permission requesting, permission denied, device
  unavailable, device-settings re-request, preview, recording, finalizing,
  playback, retake, discard, transcript drafting, transcript processing,
  transcript review, transcript failure, desktop/mobile/landscape states, and
  dark theme;
- History empty, populated, storage unavailable, written-attempt detail,
  video-metadata-only detail, desktop/mobile states, and dark theme; and
- logged-out homepage Interview scene at 1440 x 900 and 390 x 844.

The 14 direct V3 mappings are:

- desktop light screens 01-08 at 1440 x 900;
- desktop dark screens 09-10 at 1440 x 900; and
- mobile screens 11-14 at 390 x 844.

## 5. Measured layout, focus, and accessibility

### Compact fields and natural growth

From `text-growth-metrics.json`:

| Viewport | Empty | Short | Medium | Long | Improved draft |
|---|---:|---:|---:|---:|---:|
| Desktop 1440 x 900 | 144 px | 144 px | 401 px | 1451 px | 176 px |
| Mobile 390 x 844 | 160 px | 160 px | 1205 px | 3371 px | 176 px |

For the long answer, client height equals scroll height at both viewports, so
there is no internal clipping. Reset returns the field to its compact minimum.
The full-page captures measure 1440 x 2609 and 390 x 4873 and preserve exact
requested widths without horizontal overflow.

### Queue responsiveness and Escape focus

`queue-responsive-transition.json` proves the final browser-discovered
correction:

- desktop opens the queue as nonmodal;
- resizing to mobile keeps it open and makes it modal;
- returning to desktop keeps it open and returns it to nonmodal;
- Escape closes it; and
- focus returns to the visible Up next opener.

All five assertions pass at the frozen runtime SHA.

### Focus, motion, and safe areas

`accessibility-focus-motion.json` records 11 passing assertions:

- review submission focuses Cancel;
- cancel returns to the answer;
- successful review focuses feedback;
- improve focuses the improve panel;
- Back to Feedback returns to feedback;
- video preview focuses Start;
- recording focuses Stop;
- playback focuses Retake;
- denial focuses Enable Camera;
- reduced-motion rules apply; and
- the captured keyboard state has a visible focus ring.

`layout-overlap-metrics.json` records eight passing assertions, including no
horizontal overflow, mobile dock clearance above navigation, route Ask access,
no dock/Ask overlap, correct desktop and narrow queue modality, and fitting
320-pixel controls.

## 6. Privacy and media truth evidence

The deterministic local browser harness used the real template, CSS,
JavaScript, routes, storage logic, event handlers, and state transitions. It
supplied non-sensitive responses and browser-only media, speech, storage, and
motion conditions. No capture claims a live provider response or a physical
camera or microphone.

The JSON evidence proves:

- no camera or microphone request occurs on route load;
- exactly one media permission request occurs after the explicit Enable Camera
  action and requests both audio and video;
- the local recording lifecycle sends no API request and no write-method
  network request;
- no media request body is created;
- camera and microphone tracks stop;
- the local object URL is created and revoked;
- browser storage contains one metadata-only video record after playback,
  contains no media bytes or blob URL, and removes the record on discard; and
- transcript coaching makes one JSON-only request to the existing written
  review endpoint, with exact contract keys and no media fields.

All assertion groups in all 11 evidence-detail JSON files pass.

## 7. Automated checks

Focused suite:

```text
147 passed, 1 warning, 32 subtests passed
```

Full repository suite:

```text
1074 passed, 3 skipped, 19 warnings, 537 subtests passed
```

JavaScript syntax validation: Pass.

`git diff --check`: Pass.

The focused warning is the expected local Flask-Limiter in-memory-storage
warning. The full-suite warnings are the same warning plus 18 existing Pillow
`Image.getdata` deprecation warnings.

## 8. Review and release boundary

At this evidence checkpoint:

- the runtime independent review is Pass at
  `0b2d5ffa6aac56dbb6736bbeb5cee13c8baffeb7`, as recorded in
  `evidence-summary.json`;
- the release-readiness audit final verdict remains pending in
  `evidence-summary.json`;
- Candidate deployment and smoke are pending;
- Azure PR and squash merge are pending;
- production is unchanged; and
- no live behavior is claimed.

These statuses must be updated only from exact reviewer, pipeline, PR, and live
verification evidence.

## 9. Homepage parity disposition

The current homepage Interview scene remains truthful and functional. It:

- links to `/interview-studio`;
- labels itself as an illustrative walkthrough;
- captures no visitor input;
- makes no AI request;
- stores no answer or practice data; and
- remains responsive without horizontal overflow in the captured desktop and
  mobile states.

Its visual hierarchy and professional parity with the newly accepted Studio
direction remain open under
`PS-HOME-INTERVIEW-FOCUS-PARITY-001`. The older
`PS-HOME-INTERVIEW-PARITY-001` package remains closed historical authority and
is not rewritten.
