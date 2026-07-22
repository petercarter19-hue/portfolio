# PS-JOURNAL-001 J1 Visual Finish — Correction-Round Evidence Report

## Status

- Capture-source commit: `eec7f5ff44d5894ad0d112f9dbff5090eefd3b08` on `work/2026-07-21-journal-frontend-j1-impl`.
- Evidence: 62 local Flask/Chrome viewport captures. The manifest audit is exact: 62 PNGs, 62 capture-log entries, 62 manifest entries, and 62 distinct SHA-256 hashes. See `artifacts/ps-journal-001-j1-frontend/EVIDENCE_MANIFEST.json`.
- “Pass” means the listed rendered evidence and regression test support the implementation. It is not a Pete/session-manager acceptance decision.
- No merge, PR, deployment, feature-flag change, database change, or public-route expansion occurred. The production Journal flag remains off.

## Correction-round measurements

| Check | Measured result | Exact proof |
| --- | --- | --- |
| Hero identity | Desktop headline 307×78px; mobile 186×55px; italic and no more than two lines | `timeline-desktop-light-1440.png`, `timeline-mobile-light-390.png`, browser test `test_hero_headline_is_italic_and_remains_a_two_line_identity` |
| Type/Speak stage | Desktop Type 502×320px and Speak 502×336px; 390px Type 342×148px and Speak 342×258px | `composer-type-desktop-light-1440.png`, `composer-speak-desktop-light-1440.png`, `composer-type-mobile-light-390.png`, `composer-speak-mobile-light-390.png` |
| Mobile annotation | Full no-wrap `Proud of this one` line, visible star, card-content placement, and viewport containment at 390/320 light/dark | `timeline-mobile-light-390-entries-a.png`, `timeline-mobile-dark-390-entries-a.png`, browser test `test_mobile_achievement_annotation_stays_in_content_flow_with_visible_star` |
| Detail composition | Title 512×76px; audio 448×66px; photo 216×122px (1.77:1); audio/photo center delta 0px | `detail-desktop-light-1440.png`, capture log, browser detail geometry test |
| Empty intro | Illustration 168px; visual illustration-to-headline gap 16.8px | `empty-desktop-light-1440.png`, capture log, browser empty-geometry test |
| Mobile Save/footer | 20px pencil within the required 18–22px; details end before in-flow footer after Type, save failure, and voice failure at 390/320 light/dark | composer 390/320 captures and browser mobile-composer test |
| Reduced motion | Canonical static Type image remains `composer-type-mobile-light-390.png`; the redundant identical image was removed. Browser test confirms reduced-motion media preference and no mic transition. | `composer-type-mobile-light-390.png`, `test_reduced_motion_preserves_the_canonical_mobile_type_view_without_transitions` |

## Binding doc-15 audit (1–60)

| Item | Result | Exact proof |
| --- | --- | --- |
| 1 | Pass | `timeline-desktop-light-1440.png`, `timeline-desktop-dark-1440.png`, `timeline-mobile-light-390.png`, `timeline-mobile-dark-390.png` |
| 2 | Pass | `timeline-desktop-light-1440.png`, `timeline-desktop-dark-1440.png` show the numbered chapter rail. |
| 3 | Pass | `capture-log.json`: Reflections top 955px = May 19 top 955px; flourish top 1339px / May 13 top 1340px. |
| 4 | Pass | `timeline-desktop-light-1440.png`, `timeline-mobile-light-390.png`. |
| 5 | Pass | `timeline-desktop-light-1440.png`, `timeline-desktop-dark-1440.png`. |
| 6 | Pass | Route-render test plus `timeline-mobile-light-390.png`, `timeline-mobile-dark-390.png`. |
| 7 | Pass | `timeline-desktop-light-1440.png`, `timeline-desktop-dark-1440.png`, `timeline-mobile-light-390.png`, `timeline-mobile-dark-390.png`; italic/two-line browser measurement. |
| 8 | Pass | `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`. |
| 9 | Pass | `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`, `timeline-mobile-light-390-entries-c.png`, `timeline-mobile-dark-390-entries-c.png`. |
| 10 | Pass | `timeline-desktop-light-1440-entries.png`, `timeline-mobile-light-390-entries-a.png`, `timeline-mobile-dark-390-entries-a.png`. |
| 11 | Pass | Voice waveform/duration only: `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`, `timeline-mobile-light-390-entries-a.png`, `timeline-mobile-dark-390-entries-a.png`. |
| 12 | Pass | Ordered May 20, 19, 18, 13 plus Load more: `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`, `timeline-mobile-light-390-entries-a.png`, `timeline-mobile-light-390-entries-b.png`, `timeline-mobile-light-390-entries-c.png`, `timeline-mobile-light-320-entries-c.png`. |
| 13 | Pass | `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`, `timeline-mobile-dark-390-entries-b.png`, `timeline-mobile-dark-390-entries-c.png`, `timeline-mobile-dark-320-entries-c.png`. |
| 14 | Pass | `timeline-desktop-light-1440.png`, `timeline-desktop-dark-1440.png`, `timeline-mobile-light-390.png`, `timeline-mobile-dark-390.png`. |
| 15 | Pass | `timeline-desktop-light-1440-entries.png`, `timeline-desktop-dark-1440-entries.png`. |
| 16 | Pass | `timeline-mobile-light-390-entries-a.png`, `timeline-mobile-dark-390-entries-a.png`, `timeline-mobile-light-320-entries-b.png`, `timeline-mobile-dark-320-entries-b.png`, `timeline-mobile-light-320-entries-c.png`, `timeline-mobile-dark-320-entries-c.png`. |
| 17 | Pass | `composer-type-desktop-light-1440.png`, `composer-speak-desktop-light-1440.png`, `composer-type-desktop-dark-1440.png`, `composer-speak-desktop-dark-1440.png`, `composer-type-mobile-light-390.png`, `composer-speak-mobile-light-390.png`, `composer-type-mobile-light-320.png`, `composer-speak-mobile-light-320.png`. |
| 18 | Pass | `composer-type-desktop-light-1440.png`, `composer-speak-desktop-light-1440.png`, `composer-type-mobile-dark-390.png`, `composer-speak-mobile-dark-390.png`. |
| 19 | Pass | `composer-type-desktop-dark-1440.png`, `composer-speak-desktop-dark-1440.png`, `composer-type-mobile-dark-320.png`, `composer-speak-mobile-dark-320.png`. |
| 20 | Pass | `composer-type-mobile-light-390.png`, `composer-type-mobile-dark-390.png`, `composer-type-mobile-light-320.png`, `composer-type-mobile-dark-320.png`. |
| 21 | Pass | `composer-speak-mobile-light-390.png`, `composer-speak-mobile-dark-390.png`, `composer-speak-mobile-light-320.png`, `composer-speak-mobile-dark-320.png`. |
| 22 | Pass | `composer-mobile-save-failure-390.png`, `composer-mobile-save-failure-dark-390.png`, `composer-mobile-save-failure-light-320.png`, `composer-mobile-save-failure-dark-320.png`. |
| 23 | Pass | `composer-mobile-voice-failure-390.png`, `composer-mobile-voice-failure-dark-390.png`, `composer-mobile-voice-failure-light-320.png`, `composer-mobile-voice-failure-dark-320.png`. |
| 24 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`; browser focus test confirms no outline or box-shadow card. |
| 25 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`. |
| 26 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`. |
| 27 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`. |
| 28 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`. |
| 29 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`. |
| 30 | Pass | `saved-desktop-light-1440.png`, `saved-desktop-dark-1440.png`, `saved-mobile-light-390.png`, `saved-mobile-dark-390.png`; browser focus test also covers 320px dark. |
| 31 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 32 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 33 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`; illustration is measured at 168px. |
| 34 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 35 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 36 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 37 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 38 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`. |
| 39 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`. |
| 40 | Pass | `empty-desktop-light-1440.png`, `empty-desktop-dark-1440.png`, `empty-mobile-light-390.png`, `empty-mobile-dark-390.png`; browser geometry test confirms 10–22px visual gap. |
| 41 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`, `detail-mobile-light-390.png`, `detail-mobile-dark-390.png`. |
| 42 | Pass | `detail-mobile-light-390.png`, `detail-mobile-dark-390.png`; mobile-spine browser assertion also covers 320px. |
| 43 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`; title is measured at 512×76px. |
| 44 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`, `detail-mobile-light-390.png`, `detail-mobile-dark-390.png`. |
| 45 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`; audio/photo center delta 0px and photo 216×122px. |
| 46 | Pass | `detail-mobile-light-390-lower.png`, `detail-mobile-dark-390-lower.png`. |
| 47 | Pass | `detail-mobile-light-390-lower.png`, `detail-mobile-dark-390-lower.png`. |
| 48 | Pass | Lifecycle/history/privacy footer: `detail-mobile-light-390-lower.png`, `detail-mobile-dark-390-lower.png`. |
| 49 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`, `detail-mobile-light-390-lower.png`, `detail-mobile-dark-390-lower.png`. |
| 50 | Pass | `detail-desktop-light-1440.png`, `detail-desktop-dark-1440.png`, `detail-mobile-light-390.png`, `detail-mobile-dark-390.png`; browser rail test asserts Timeline current / Voice false on desktop and mobile. |
| 51 | Pass | TESTING-guard tests; `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`, `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`. |
| 52 | Pass | `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`, `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`. |
| 53 | Pass | `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`. |
| 54 | Pass | `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`, `manage-mobile-light-390.png`, `manage-mobile-dark-390.png`. |
| 55 | Pass | All six lower rows: `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`. |
| 56 | Pass | Count/footer: `manage-mobile-light-390-footer.png`, `manage-mobile-dark-390-footer.png`. |
| 57 | Pass | Server and JS re-render tests enforce May 20/18 Voice waveform+duration only, May 19/15 Text with no thumbnail, and May 17 Photo / May 16 Video thumbnails only; visual proof is `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`. |
| 58 | Pass | `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`, `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`. |
| 59 | Pass | `manage-mobile-light-390-lower.png`, `manage-mobile-dark-390-lower.png`, `manage-mobile-light-390-footer.png`, `manage-mobile-dark-390-footer.png`. |
| 60 | Pass | `manage-desktop-light-1440.png`, `manage-desktop-dark-1440.png`, `manage-mobile-light-390-footer.png`, `manage-mobile-dark-390-footer.png`. |

## Validation executed

- Python compile: `owner_routes.py`, `scripts/capture_ps_journal_j1_evidence.py`, and `tests/test_journal_frontend.py` — `OK`.
- JavaScript: Chrome-backed Journal browser tests loaded and executed `static/js/journal.js` across Timeline, composer, Manage re-render, and detail flows — `OK`.
- `git diff --check` — `OK`.
- Focused Journal route/service/frontend suite: 112 tests in 45.747s — `OK`.
- Full suite: 817 tests in 49.041s — `OK (skipped=2)`.
- Manifest integrity: 62 actual PNGs = 62 capture-log entries = 62 manifest entries = 62 unique SHA-256 hashes — `OK`.

## Product limits retained truthfully

- Production list reads still do not expose full narrative/context or a playable capture-source key; Detail uses only authorized fields and voice playback remains visibly disabled.
- Photo/video attachment creation remains staged as “Coming later”; fixture media are TESTING-only evidence, not a new production upload capability.
- No deployment or human visual acceptance occurred in this task.
