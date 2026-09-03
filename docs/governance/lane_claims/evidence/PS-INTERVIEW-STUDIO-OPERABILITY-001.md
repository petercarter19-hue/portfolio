# PS-INTERVIEW-STUDIO-OPERABILITY-001 — candidate evidence

## Scope and authority

Pete authorized this package under
`session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`.
This is a Protected repository package with authority through merge.
Production authority is withheld. No deployment, feature enablement, live
browser or member proof, identity, provider, schema, migration, grant,
configuration, or production operation is part of this record.

## Governance lineage

- Claim-only activation candidate
  `958c9635b87fc58aa80afb25680d9c6083b52c53` was independently accepted;
  PR 881 / build 2339 merged it at
  `df37a13d293c42a4ad3f4b0ba350bad207b0a306`.
- Pre-registry candidate
  `1faa082b77adfcaa3f8a491e566f32d260e1b6f3` was revised because native
  no-JavaScript mode links incorrectly carried tab-only `aria-selected`.
  Corrected candidate `b384ad729cd846959ce42780975830337eb5e728`
  was provisionally accepted and remains evidence only.
- Deferred Package Registry surface-extension candidate
  `8832141c3515d85b1975ed0b4a01a40df4fe8264` was independently accepted
  with zero findings at `2026-09-03T07:48:28Z`; PR 889 / build 2358 merged
  exactly the one-file claim change at
  `33b58c2e118cec2421fe3d183a9182ef6c0efccd`.
- The implementation branch merged that exact current main while preserving
  the provisional candidate in history, then added only the claimed Registry
  row and documentation refresh before final validation and review.

## Candidate outcome

Exact candidate `2477b4555746028b22a2128688d0de0b758bee7a`
against current-main base `33b58c2e118cec2421fe3d183a9182ef6c0efccd`
changes exactly eight claimed paths: the Package Registry, two initiative
documents, the Interview Studio template, page-local CSS, page-local
JavaScript, the existing focused test, and one new browser test.

Authenticated Interview Studio has one visible H1, one canonical guarded
History destination, one responsive Session setup launcher, and one Studio
settings launcher for the existing local dialog. JavaScript-only launchers are
hidden until handlers are installed. Real mode and History links remain
functional without JavaScript. Focus entry and return, Escape, backdrop,
expanded state, Tab containment, new-session consequence copy, draft/video
guards, 44px targets, narrow reflow, forced colors, reduced motion, and text
spacing are explicitly tested.

The final accessibility correction ensures a server-rendered History view and
the enhanced History transition expose only History—not a fallback practice
mode—as the current Interview Studio destination. Mode links use native
`aria-current` before enhancement and tab semantics only after enhancement.

The Registry adds `PS-INTERVIEW-STUDIO-OPERABILITY-001` exactly once under
`current_protect`, locally alphabetized between the existing Integration and
Visual Fidelity entries. `current_protect` changes from 72 to 73 and total
from 140 to 141; no unrelated Registry row or category changes.

Public and flag-off rendering, browser-local storage keys and records, APIs,
payloads, provider behavior, authentication and safe return, no-store/noindex,
Quiet Preview, robots, sitemap, and default-off flags remain unchanged. The
candidate does not edit `app.py`, the shared shell, authentication, schema,
providers, Profile, Workshop, Settings, deployment, configuration, identities,
live data, or production.

## Validation

- Interview Studio route/unit suite: **310 passed**.
- Package Registry suite: **2 passed**.
- Combined Interview Studio and Registry selection: **312 passed**.
- Local Playwright operability suite: **8 passed** using isolated local
  fixtures only.
- Inherited shared-shell, navigation, home, sign-in, auth, search, site-rule,
  owner-settings, Workshop-checkpoint, Community-replacement, and member-arrival
  regression selection: **613 passed**.
- Exact requirements-only Python 3.12 full suite: **5,564 passed, 34 inherited
  skips, zero failures** in 247.250 seconds.
- JavaScript syntax, exact changed-path and claimed-path checks, static control
  counts, Registry counts, and `git diff --check`: pass.
- Strict fetched, clean, task-bound write preflight: pass; exact head
  `2477b4555746028b22a2128688d0de0b758bee7a`, current main
  `33b58c2e118cec2421fe3d183a9182ef6c0efccd`, eight changed paths, ahead 6 /
  behind 0.
- Current-tree Gitleaks scanned approximately 49.37 MB with zero findings;
  exact current-main range Gitleaks scanned five commits / approximately
  48.71 KB with zero findings. The independent reviewer also confirmed its
  all-fetched-ref scan had zero findings.

## Browser and capture evidence

Lifecycle allocation `39b3cbe826af773d8a9202a7` retains the bounded local
evidence under
`/Users/petercarter/Documents/PeerSlateEvidence/x_maintenance/PS-INTERVIEW-STUDIO-OPERABILITY-001/browser-proof/d5a9c57de4b7`.
The manifest binds all 11 captures to exact candidate
`2477b4555746028b22a2128688d0de0b758bee7a`; its SHA-256 is
`66525dd09a9afbcad27a93607b24ff62ea34e1f31eed3f39d78e74a84a4592ee`.
All recorded file sizes and hashes were recomputed successfully; total capture
bytes are 1,712,962. Chromium was `152.0.7977.65`. JavaScript was enabled
unless the capture name says no-JavaScript.

| Capture | Viewport | Fixture | Captured UTC | Bytes | SHA-256 |
|---|---:|---|---|---:|---|
| authenticated-no-javascript.png | 320x568 | local-isolated-authenticated-member | 2026-09-03T08:27:10.245050+00:00 | 113063 | `7963dfe5aae97508ac60910d88b6c78d603534b0a76c39d85a32ca860f5acd50` |
| public-flag-off-no-javascript.png | 390x844 | public-flag-off | 2026-09-03T08:27:10.929169+00:00 | 488033 | `1d08fcad89f624cbced78c6e14dcfa29ccd03243e1a46145e68d4a52dc763016` |
| session-setup-keyboard-focus.png | 390x844 | local-isolated-authenticated-member | 2026-09-03T08:27:11.333819+00:00 | 183854 | `e7cef28c18b13c1255b4c85328ad85be5ef6ae0fead5da2fe12d738d60f8d228` |
| studio-settings-keyboard-focus.png | 768x1024 | local-isolated-authenticated-member | 2026-09-03T08:27:12.129013+00:00 | 153704 | `a8694253a8083ca5117ce473100ed6eeecf95d4acd65b832a8ad02c50251495d` |
| authenticated-desktop.png | 1440x900 | local-isolated-authenticated-member | 2026-09-03T08:27:12.737735+00:00 | 171893 | `422a21901aeb4236771c5a5170e23c8f3020ba242c6017dff21d722d12c63f36` |
| authenticated-tablet.png | 768x1024 | local-isolated-authenticated-member | 2026-09-03T08:27:13.087096+00:00 | 106618 | `cca501c5be4bde42aed0a8892502c015b65cb0a93cad204219025fc893cca50a` |
| authenticated-phone-390.png | 390x844 | local-isolated-authenticated-member | 2026-09-03T08:27:13.416121+00:00 | 102020 | `7a45e10b3bee022fbebba47a7db5c14f8ed74f6c7363f47598970accc2a3c403` |
| authenticated-phone-320.png | 320x568 | local-isolated-authenticated-member | 2026-09-03T08:27:13.794769+00:00 | 97030 | `496161fdda132c20515e498d8beb2b85fe685df308781513f6f5682afcd7533c` |
| authenticated-text-spacing-400-percent-reflow.png | 320x568 | local-isolated-authenticated-member | 2026-09-03T08:27:14.160156+00:00 | 103690 | `75824b6664eb3a8c6bd884499b8093e2fed57239bc6d1af1b321a3c94b2c7797` |
| authenticated-forced-colors.png | 390x844 | local-isolated-authenticated-member | 2026-09-03T08:27:14.520097+00:00 | 86712 | `79884af0bbc7ba8e0a8443ca071cc50771c25d9ecaec270b5304799cf01cbaba` |
| authenticated-reduced-motion-200-percent-reflow.png | 640x900 | local-isolated-authenticated-member | 2026-09-03T08:27:14.834730+00:00 | 106345 | `e701d807c69e5c95cb8be9f64329cac1c5461eae38b0e5aaf5f03315e9816a12` |

Every screenshot has a corresponding DOM or interaction assertion in the
eight-test browser suite; screenshots are supplementary, not the sole proof.
No live browser profile, cookie, credential, identity, provider, or production
connection was used.

## Independent review

Independent final review first revised candidate
`9ed548f58a32d3b6761686b8e56dd67473c78375` because History retained a
fallback mode's current-page state. Candidate
`4e2b47b08817edb4199df88c7dcf40cb6c4054e0` corrected the code and tests;
review confirmed that defect fixed, then requested only correction of the
route/unit count in the completion report from 309 to 310.

Independent final delta review ACCEPTed exact candidate
`2477b4555746028b22a2128688d0de0b758bee7a` against current main
`33b58c2e118cec2421fe3d183a9182ef6c0efccd` with zero remaining findings.
Reviewer: `agent:/root/profile_d1_writer`; reviewed at
`2026-09-03T08:29:18Z`. The review verified the one-line final delta, every
non-report blob from the corrected candidate, exact Registry entry/counts,
truthful test totals, exact capture binding, strict preflight, diff, and secret
scans. Acceptance authorizes repository merge only.

## Release truth

This evidence binds an immutable repository candidate. It does not state or
imply that the Interview Studio change is deployed, enabled, production-ready,
or live-proven. Any deployment, feature configuration, or authenticated live
proof requires a separate claimed package and explicit action-specific
authority.
