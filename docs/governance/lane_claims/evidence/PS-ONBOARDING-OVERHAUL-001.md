# PS-ONBOARDING-OVERHAUL-001 acceptance evidence

Writer: `session:01a0fac2-1122-7ea2-91c8-06033862e354`.
Delivery path: Protected. Repository base: `90dfa8d9e503e75f592ec587e812257403a8029c`.
Activation: Azure PR1226, claim-only source `b15b0c186ab2bc47aca8e7cd87ad3d675a01a49d`, CI3971 passed all four jobs and all three required policies. Native read/activate/write preflights passed. Normal lifecycle ensure created this durable worktree and finalization released control.

## Pre-change observation

The first baseline invocation stopped at import because the app requires an Anthropic environment value even for isolated tests. No provider request occurred. The next invocation used the non-secret placeholder `ANTHROPIC_API_KEY=unused-onboarding-browser-fixture` and `PYTHONDONTWRITEBYTECODE=1`; it passed all 18 existing browser journeys in 35.231 seconds. The harness serves a separate local Flask app with in-memory owner stores and deterministic document/transcription seams. It is not the persistent private installation and proves neither real authentication, SQL nor a live provider.

Full output: `C:\Users\peter\Documents\Visual Intelligence\runs\run_20261002T041842Z_c64b7980\onboarding-browser-baseline.log`.
No product file had changed when the baseline ran. The evidence plan and criteria below are committed before implementation.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-ONBOARDING-OVERHAUL-001",
  "plan_sha": "37b712814d9b1a9bcc9e0b608d6ccded5b941628",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_resume_intake_browser -v",
      "exit_code": 1,
      "observation": "Pre-change import refused because ANTHROPIC_API_KEY was absent; no tests or provider calls ran."
    },
    {
      "command": "python -B -m unittest tests.test_resume_intake_browser -v",
      "exit_code": 0,
      "observation": "With a non-secret unused fixture key and bytecode disabled, all 18 existing browser journeys passed in 35.231 seconds on base90dfa8d9; deterministic seams and in-memory owner stores, no live provider or personal-profile mutation."
    }
  ],
  "criteria": [
    {
      "id": "welcome_composition",
      "expected": "The welcome explains the resume and personal-AI benefit before input; a single adaptive foreground guide keeps the real resume behind it and follows the selected typography, aligned buttons, satin texture, layers and shadows.",
      "verification": "Browser observations and captured desktop/phone states compared with the seven selected authority assets; inspect actual document placement and welcome copy."
    },
    {
      "id": "review_and_reveal",
      "expected": "AI/source suggestions appear in meaningful review groups with in-place corrections including date precision/currentness. Pending or rejected proposals never populate the resume; only acknowledged private saves refresh and clarify it, preserving untouched facts.",
      "verification": "Real browser-to-Flask-to-service journeys submit and correct proposals, inspect before/after canonical values and document state, and exercise rejection, parent requirements and date/status preservation."
    },
    {
      "id": "request_recovery",
      "expected": "Uncertain submissions and proposal decisions retain immutable request identities and payloads. Retrying does not duplicate saved facts, newer typing survives, and failed files or unacknowledged input remain available.",
      "verification": "Controlled response-loss and delayed-response browser journeys compare request IDs/payloads, persisted row counts and retained input, including newer edits made after the uncertain attempt."
    },
    {
      "id": "guided_voice",
      "expected": "Recording, stopping, transcription and transcript review report the actual supported state. Leaving the guide stops microphone tracks, explicit cancellation fences stale responses, and late transcripts never overwrite newer typing. Unsupported or refused recording leaves typing usable.",
      "verification": "Browser fake-device/deterministic-transcriber journeys verify actual recorder events, stop/cancel/return behavior, stale response suppression, retry identity and append semantics; do not call this physical microphone proof."
    },
    {
      "id": "contextual_nudges",
      "expected": "The foreground guide uses the existing owner-context interview endpoint on explicit member action for an optional contextual nudge, never as a canonical save. The active flow suppresses repeated skipped/answered questions and preserves input when AI is unavailable.",
      "verification": "Browser journeys with an isolated assistance seam verify current draft revision, explicit request timing, question presentation, skip behavior, unchanged canonical data and useful unavailable behavior."
    },
    {
      "id": "manual_finish",
      "expected": "Skip or close always reaches manual editing with existing fact-creation controls, and reopening preserves unfinished input. Optional story/media choices use existing supported controls. Finishing does not publish or alter visitor-AI permission and does not misstate a returning member's sharing state.",
      "verification": "Browser journeys exercise skip, manual creation, reopen, optional destinations and finish; compare source/canonical/private-draft/display/visitor-AI state before and after."
    },
    {
      "id": "responsive_access",
      "expected": "Desktop, 390px and 320px layouts and reduced-height/reflow conditions have readable text, aligned reachable controls and no horizontal overflow. Modal keyboard focus, Escape, visible focus and reduced-motion behavior work.",
      "verification": "Browser geometry/focus assertions and visual captures at the specified viewports, long-input and reduced-motion states; physical iPhone keyboard and screen-reader verification remain separately identified."
    },
    {
      "id": "provider_and_privacy",
      "expected": "No provider call occurs on page load and no suggestion is silently accepted. Existing owner-derived APIs, provider configuration/caps, canonical source/proposal separation, feature-flag fallback and publication boundaries remain authoritative; unrelated product surfaces are unchanged.",
      "verification": "Focused browser regression results, request/service observations, canonical/permission assertions, exact claimed-path diff and independent Protected review."
    }
  ],
  "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
  "checks": [
    {
      "criterion_id": "welcome_composition",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-correction-contract.json",
      "observed": "The exact candidate preserves all four rendering files from independently cleared4b3 and captured05133; all ten existing capture hashes and seven locked mockups remain verified through retained candidate-ci-contract.json. Real rendered desktop and narrow-phone views preserve foreground guide, benefit copy, resume behind, aligned controls, depth and adaptive layout. No new capture or installed-device proof is claimed.",
      "provenance": {
        "observer_ref": "session:01a0fac2-1122-7ea2-91c8-06033862e354",
        "captured_at": "2026-10-02T13:09:37Z",
        "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-correction-contract.json"
      }
    },
    {
      "criterion_id": "review_and_reveal",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Grouped review/correction journeys verify private canonical data stays unchanged until an acknowledged decision, rejected/pending suggestions do not reveal facts, date precision/currentness survive, education approximate/unknown ISO dates are accepted, and Impact parent selection survives Back/review and refresh. Unsaved manual editor text is preserved."
    },
    {
      "criterion_id": "request_recovery",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Response-loss, malformed acknowledgment and delayed-response journeys retain request identity and frozen payloads, prevent duplicate canonical writes, retain failed files and preserve newer typing through retries and late acknowledgments."
    },
    {
      "criterion_id": "guided_voice",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Real browser recorder events using a fake media device and deterministic transcription verify stop/cancel/return behavior, microphone track cleanup, immutable recording metadata, stale-response fences and append rather than overwrite. The UI says recording then transcription; no physical microphone or live provider claim."
    },
    {
      "criterion_id": "contextual_nudges",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Explicit contextual-question requests include current draft revision and isolated owner context, present one optional question, suppress repeated skipped/answered questions and preserve input on unavailable AI. Interview responses do not write canonical facts."
    },
    {
      "criterion_id": "manual_finish",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Skip/close/manual-create/reopen journeys preserve unfinished guide input and existing editor controls; optional Story/media destinations reuse supported controls. Finish remains explicit and private, clears the backdrop blur, changes no publication or visitor-AI permission and shows an unsent-input reminder only when applicable."
    },
    {
      "criterion_id": "responsive_access",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "Geometry and focus regressions pass at desktop, 390px, 320px, reduced-height/reflow and reduced-motion conditions. Captures show readable reachable controls, internal correction scrolling and no horizontal overflow; keyboard Escape/focus restoration work in Chrome. Physical iPhone keyboard and screen-reader acceptance remain unverified."
    },
    {
      "criterion_id": "provider_and_privacy",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "b03ce68425f07755ceece48751a64ff581f41f08",
      "source_ref": "file:C:/Users/peter/Documents/Visual Intelligence/runs/run_20261002T041842Z_c64b7980/onboarding-runtime-evidence/ci3992-corrected-full58.log",
      "observed": "All58 required integrated/intake browser journeys passed in116.959seconds with zero skips/errors/failures and zero live provider calls. The existing delayed-workspace journey reproduces the old readiness error and passes the correction. All58 method names and strict runner are unchanged; privacy, cancellation, newer-input, publication and source-removal assertions remain. Earlier195 source proof remains applicable to unchanged runtime/services/routes; all33 intake journeys including the corrected single receipt selector were re-executed in the58. Renewed independent Protected review passed exactb03; exact AzureCI and actual private installation remain separate."
    }
  ]
}
```

## Release boundary

Repository acceptance precedes the separately coordinated private installation. The installer owns runtime promotion and the selected `PS-ONBOARDING-FICTIONAL-WORKSPACE-001` dependency. Fictional mutation must use its accepted isolated context, never Pete's current saved profile. Public MVP enablement remains held. Native private-browser access, physical-device use and live-provider evidence must be reported honestly at release; prototype or deterministic browser results do not establish them.

## Transparent planning-history correction

The original pre-implementation commit `5635ae90a5ae84e72f305c283ede06ebff1b34c7` contained the fixed acceptance plan and the package README. The completion validator requires an evidence-only plan commit. The owner branch was reconstructed by splitting those exact original blobs, replaying only this writer's implementation commits, and updating `plan_sha`. Baseline observations and criterion content are unchanged; no reconstructed commit is claimed as a newly executed baseline. The full replayed tree matched original reviewed candidate `e0d3eac661370c525b9df03d2dfac829e3291765` before this evidence-only reference update. Original objects and the old-to-new mapping are preserved in `onboarding-original-history.bundle` and `onboarding-plan-history-repair.json` under the external evidence run.

## Earlier candidate review and validation before CI integration

The earlier clean, pushed implementation candidate was `05133ea7228cea636afa664e3cc8feaf4d7867f4`; the CI corrections below supersede its final-candidate binding. Read-only independent Protected reviewer `collaboration:/root/onboarding_independent_review` returned PASS with no remaining findings. The receipt uses the supported opaque reference `agent:/root/onboarding_independent_review` for that same actual reviewer, configured gpt-6.1-sol / xhigh; actual runtime model settings are not observable.

Both original P2 findings are resolved: education approximate/unknown ISO date precision no longer blocks supported correction, and selected Impact parent linkage survives Back/review and asynchronous refresh. The reviewer rechecked the integrated exact source, all 195 passing tests, ten final capture hashes, preserved seven-asset design authority, clean pushed state and reconstructed planning history. The full replayed source tree matched the earlier cleared candidate; the preserved original-history bundle SHA-256 is `21b05bb62a2c9f94495a84a761e72ea0afe5899e0b335332303540f5da135644`.

The necessary route-test path extension was accepted through PR1231 at main `9ae6eacbbdef5d904295e7565909f00a4c97138e`, after CI3983 and all three required policies passed. Normal lifecycle reconciliation preceded integrating the exact independently reviewed route adaptation (raw SHA-256 `08e86a22379d46ee4671d9a04cd6bab2edec719e62ee6302c4c801f05963484e`). Its typed-field and unsaved-editor assertions remain intact. This resolves the five stale-selector errors in the earlier broad run; those failures are retained in the original logs.

Candidate-bound validation: `python -B -m unittest tests.test_resume_intake_browser tests.test_resume_intake_service tests.test_resume_intake_runtime tests.test_resume_intake_routes tests.test_resume_intake_proposals tests.test_resume_editor_http -v` passed all 195 tests in 69.839 seconds. `node --check static/js/resume-intake.js` and `git diff --check` passed. The test log and `integrated-05133ea7/manifest.json` preserve exact candidate, time, command, capture hashes and limitations. Tests use an isolated Flask app, in-memory fictional owners, deterministic adapters and a fake media device. They do not establish SQL, real private identity, a live provider, physical microphone/iPhone or screen-reader acceptance.

Jev checkpoint: the current acceptance/release step follows the already settled required proof sequence. No unresolved investigation, evidence-priority, regression-selection or review-focus judgment with meaningful alternatives remains, so no additional inference call is appropriate. Earlier advisory attempt `a88f4792-fccd-4760-9bda-d3cad50e8c8e` and annotation `1c8df952-4883-43e6-81f0-47d9c71bb84a` remain the retained task checkpoint; no repeated call is claimed.

Only this fixed evidence file and the fixed review receipt change after the reviewed candidate. This record establishes repository acceptance evidence, not private installation, deployment, public enablement or physical-device validation. Those remaining release observations stay with the separately coordinated installation outcome.

## Required CI integration correction

Runtime PR1233 CI3987 failed at the strict integrated browser method-set admission before running those journeys: the runner pinned the earlier 18 intake names while the implementation supplied 33 expanded names. BuildJob also found the same runner collection error and one documentation-index mismatch. Its application/security discovery ran 7304 tests in 388.395 seconds with one failure, one error and 164 skips; this is retained failed evidence, not a passing release. The delivery-disposition artifact failure followed the failed prerequisite jobs.

The unchanged 25 integrated browser journeys were then run locally: five obsolete interactions failed and twenty passed in 200.283 seconds. Claim-only extension PR1234 was accepted at `901d2c6b62b5e190cf6a88f0afd17dc76bd88c9d` after CI3988 and all required policies passed. Normal finalization released control, and ordinary reconciliation produced `2c092d12ff465db70d0afe0d1c33ed255f2d0346` before tracked integration.

The independently reviewed adaptation preserves all 25 integrated method names and 20 AST-identical method bodies. Five journeys now enter the welcome/manual controls, follow each source-bound group explicitly, use acknowledged private saves and test the foreground dialog over the actual document. The manual section-navigation assertion remains before reopening the dialog. Privacy, publication, cross-owner source purge, canonical retention, cancellation, storage failure and scan rejection assertions are retained. The strict runner now pins all 33 current intake names plus the retained 25 integrated names (58 total); missing, changed, empty, skipped and failing suites remain failures. No loader, pipeline policy or required check is relaxed.

Prepared adaptation review passed on exact SHA-256 `561f259a8a5166c67f948006bb86b8bcc6d99af5afc274df853a1e723c984437` (integrated journeys) and `966e6e3568d140979288f6e4a1540d0d253c3fc00bc9a10ced03e61e8d759971` (runner). Five changed journeys passed in 27.698 seconds. Earlier preparation runs exposed an asynchronous assertion and separate recording-source group, then an obsolete navigation geometry check; those logs remain. `intake-coverage-map.json` maps all 18 previous intake journeys to current semantic coverage and was independently checked. Exact integrated candidate acceptance, the complete runner and current-target CI still follow this source commit.

The new initiative README was not yet on main and caused the documentation registry completeness failure. The global registry is reserved by paused `PS-OPPORTUNITY-SLATE-003`. Its bytes and ownership remain untouched. The complete README contract is consolidated below in this already-owned fixed evidence file, with only its surface count and relative acceptance link updated. Removing the unmerged README directory avoids introducing a second initiative location; it does not remove runtime code, visual authority, owner authorization, immutable criteria or source history. The claim still reserves the historical README path. The original complete file remains in Git and its byte hash/consolidation mapping are retained in `documentation-consolidation.json`.

Jev: the runner repair checkpoint was skipped because free status `4d7c0e87-c648-4760-922f-8fd15421cac0` returned ongoing cooldown; no inference or retry occurred. The separate documentation/custody decision used attempt `752b39f3-1cc8-41b8-aca8-47b06c876bd1`, question `documentation_repair`: consolidate owned documentation 1.0, coordinate registry owner 0, none 0; confidence 1.0 is model output, not verified accuracy. The writer followed consolidation subject to actual tests and independent review. Reported latency 1266 ms, 661 input/56 output tokens and USD0.000027762; provider billing/version unknown. Initial annotation `3ea7c31d-8006-448a-9ba2-dc3430e591bb` records pending outcome, and the exact decision was reported centrally. External `registry-documentation-jev.json` preserves the request, response and interpretation.

## Consolidated package contract

# AI-guided résumé onboarding

Owner-selected outcome: replace the confusing docked intake interface with one modern, adaptive foreground guide. The real résumé remains behind it, initially softened by bokeh and becoming clearer as confirmed information is saved. AI guidance and contextual nudges lead; manual editing is always reachable through Skip. Completion and sharing remain separate member choices.

Pete authorized the full discussed roadmap unattended in session `01a0fac2-1122-7ea2-91c8-06033862e354`, event `evt-602253a2-e814-4feb-8432-5efced0fa9a8` (human message `01a0fb02-e174-7c93-9be2-2560cbf7402d`, 2026-10-02T05:07:45.140Z). LinkedIn is deferred. The initial release target is the persistent private installation; public MVP enablement is held. The active claim names the actual writer and twelve exact mutable paths after accepted extensions PR1231 and PR1234.

## Product contract

- Explain the benefit upfront: the more PeerSlate knows the member, the more it can do for their résumé and personal AI; only chosen information is shared.
- Offer aligned Upload files and Start talking actions with a quieter type alternative. Keep a clearly reachable Skip to manual editing throughout.
- Use one softly rounded rectangular shell that changes size with purpose. Preserve geometric sans type, restrained pearl/satin texture, an inset content surface, layered edges, neutral shadows and depth. The résumé never moves into a side panel.
- Guide through input, truthful post-recording transcription, transcript review, grouped suggestion review and in-place correction. Confirmation is an explicit private save, not publication or visitor-AI permission.
- Refresh the existing real résumé only after an acknowledged save. Never manufacture facts, credentials, metrics, percentages or progress from elapsed time.
- Ask useful optional follow-ups using the existing owner-context AI service. Skip questions without creating a rigid numbered wizard. “Three-step simplicity” is a usability principle, not a literal step count.
- Preserve unfinished input during pause, retry, conflicts and unavailable AI. Stop microphone tracks on departure. Do not put sensitive drafts or audio in browser storage.
- Keep existing manual fact creation, Story/media choices and sharing review reachable. Finishing the guide does not modify sharing settings; returning members retain their real permissions.

## Locked visual references

Selected material authority and connected-state extensions are retained at:
`C:\Users\peter\Documents\Visual Intelligence\runs\run_20261002T041842Z_c64b7980\onboarding-mockups`.

| Selected file | SHA-256 |
| --- | --- |
| B-v5-aligned-portrait.png | 26de86f5972a75fe68296c43841f095283828f1989a51ce3a81e5bb653f46840 |
| desktop-welcome.png | a032d5006d26944e50fcd4b7ded98d97e9018e60fd3dc474537b7633ae938319 |
| review-v2-truthful.png | 4405e3fcb4c73cf2cc4b2d31d64cee653bbbcdf88ac3f99ef260dceb5b853c08 |
| voice-v2-truthful.png | 075fdd1152862e281b8c36b2d2f9619e8ba81130b30b334f70261e0dcf1120db |
| desktop-reveal-nudge.png | 0598b8483506621a237a89156015beff2fa3c712780e3d7b3a2d877f38346862 |
| phone-keyboard.png | 3688f285acd6120a383340c0ce03dded879484e3e1ec6e76eeb5aa6c5ee8bd90 |
| finish-v2-confirmed-only.png | 3e721f4dd0a69dc35a70e32f98fb837031278c298a9c78f198546849c804e30f |

The same run contains `onboarding-state-contract.md`, `onboarding-quality-review.md` and the explicitly fictional interactive prototype. Three completed design checks covered visual material/composition, truthful interaction/confirmation, and responsive keyboard/focus behavior. Superseded images with premature save wording, unsupported live transcription and invented background facts are excluded by `selected-authority.json`.

Implementation may correct contrast, reflow and accessibility while preserving this composition. It must adapt returning-member privacy copy to actual state. The prototype makes no upload, provider, microphone or canonical call; its results are not installation evidence.

## Implementation and validation

Reuse the current intake, proposal decision, recording, guide status and private interview APIs. Keep identity, service-owned conflict/version checks, source provenance and provider accounting intact. Only the claimed frontend/template/test surfaces change; any newly necessary backend path requires a supported scope extension first.

The fixed [acceptance evidence](#pre-change-observation) contains the pre-change baseline and immutable criterion IDs. Baseline browser command: `python -B -m unittest tests.test_resume_intake_browser -v`, with `ANTHROPIC_API_KEY=unused-onboarding-browser-fixture` and `PYTHONDONTWRITEBYTECODE=1`. This is a separate in-memory test app with deterministic seams, not the personal private installation.

Freeze and push the implementation candidate, obtain the required read-only independent Protected review, add only the fixed receipt/evidence tail, pass package acceptance and current-target merge preflight/CI, then coordinate the accepted private release through the site manager and existing installer. A merge is not a deployment.

## Implemented behavior and evidence limits

The foreground guide now uses the native dialog top layer and the existing private editor as its background. It explains the benefit before input, keeps recording distinct from post-recording transcription, reviews one source-bound group at a time, preserves local corrections, and refreshes the document only after an acknowledged save. Manual fact entry remains outside the dialog; saving it cannot submit unfinished guide words or attachments. Story and photo choices lead to the existing controls. Finish changes only the member's guide status.

Submission, recording, guide-choice and confirmation retries retain the original request identity and payload. A malformed success response is not an acknowledgement. Newer typing survives uncertain requests. Leaving capture stops microphone tracks and retains the local recording for explicit transcription on return; cancelled transcription cannot insert stale text. No sensitive draft is written to browser storage. Optional AI questions use the existing owner-context interview route with the current draft revision and never save returned candidates.

The expanded browser harness preserves date/currentness, status, owner-parent, file-byte, failed-item, retry, mobile and unsaved-input coverage from the pre-change baseline, and adds confirmation/reveal, in-place correction, manual/guide separation, real recorder events, keyboard focus, read-failure and contextual-question checks. Its providers and owner stores are deterministic fixtures. The retained runtime captures are under `onboarding-runtime-evidence` in the same evidence run as the locked mockups; they show actual rendered code, separately from the fictional prototype.

Five existing browser journeys in `tests/test_resume_intake_routes.py` now follow the new welcome and grouped-review navigation while preserving their typed-field and unsaved-editor assertions. The prepared, independently inspected adaptation was integrated only after claim extension PR1231 merged and normal main reconciliation completed. The runtime candidate requires final integrated validation, exact-candidate independent Protected review, required CI and coordinated private installation before release completion. Physical iPhone keyboard, physical microphone, private authentication, SQL and live-provider behavior are not established by the deterministic browser harness.


## Final corrected candidate acceptance

Final independent Protected review passed exact clean, pushed candidate `4b3fec5554ae8ff24fe1c6c23cd09b9133654f24`, with no remaining findings. Reviewer: `agent:/root/onboarding_independent_review` (same actual collaboration reviewer as the earlier reviews). The prepared exact test/runner adaptation, accepted claim extension, complete contract consolidation, immutable baseline/criteria, retained visual hashes and absence of unrelated registry edits were rechecked. Only this fixed evidence file and the fixed receipt change in the final tail.

The actual required command `python -B scripts/run_mvp1_acceptance_browser_tests.py` passed all 58 discovered/executed journeys in 118.532 seconds with zero skips, expected failures, errors, failures or unexpected successes. Its final machine-readable summary and full output are retained in `onboarding-runtime-evidence/final-integrated-runner.log`. The exact-collection and missing/empty/changed/skipped guard unit checks passed in 2.651 seconds (`final-runner-guards.log`). The source-bound `candidate-ci-contract.json` verifies the unchanged runtime/test bytes and all ten retained capture hashes, all 154 initiative registry entries against the exact candidate Git tree, the five unchanged pipeline browser-gate assertions against its exact blob, and complete contract retention with only the recorded count/link updates.

Sparse-checkout limits remain explicit: the filesystem registry test locally sees only five materialized initiative directories and fails for that reason, and the pipeline YAML is not materialized. The exact Git tree/blob checks above preserve the original assertions; they do not claim those filesystem checks ran successfully. Required Azure CI on the current combined target remains authoritative for the full checkout and must pass before merge. Earlier failed CI3987 and all preparation logs remain preserved. Current-source browser proof is local and isolated, not installed private identity/SQL/provider or physical-device acceptance. The original195-test source proof and selected mockups are retained; no new visual direction was introduced during CI correction.


## CI3992 browser timing correction (supersedes prior final-candidate status)

CI3992 evaluated tail `19b47be92d932862acecb03f0bb2b9eb9bf4ebc1` against main `901d2c6b62b5e190cf6a88f0afd17dc76bd88c9d`, synthetic `8cf8a77df328c1a113adac7b9392f8dbd5c1f0da`. Its application suite passed 7,304 tests in 396.974 seconds with 164 existing environment/optional skips. Its strict browser run executed all 58 methods with 55 passed, three errors and no skips in 189.715 seconds. The required build failed; it was not accepted or merged. Full evidence is retained in `onboarding-runtime-evidence/ci3992-final.json`, `ci3992-log-14.txt`, and `ci3992-log-39.txt`.

Two fresh-entry tests sampled the dialog-open count before asynchronous workspace/guide initialization and then attempted to click the launcher that had become hidden. The helper now distinguishes automatic fresh entry from an explicit return from manual editing, and waits for the actual open dialog before entering input. The existing cancellation journey delays the actual workspace service response with events and a bounded timer; application HTTP responses are not replaced. A red run of the old helper demonstrates premature return before initial workspace release, followed by a passing corrected run. The mixed-file test now checks its unique receipt container for the same pending-review text, preserving the requirement when both its headline and summary contain that text. No test method, canonical/private-data assertion, error-path assertion, runtime implementation, locked mockup, pipeline rule or strict collection rule is removed or changed.

Preparation retained honest failures: the first isolated test command had no fixture startup key and ran zero tests; a subsequent stress-test draft incorrectly assumed the launcher was hidden during loading and failed that setup assertion. It was corrected to the actual visible launcher state before the meaningful red/green run. Logs `ci3992-readiness-before-fix.log`, `ci3992-readiness-before-fix-confirmed.log`, `ci3992-readiness-red.log`, and `ci3992-three-corrections.log` preserve these distinctions. The three corrected journeys passed in 9.623 seconds. No live provider call was made.

Jev checkpoint `browser_regression`, attempt `5a5f9ce6-2ba7-4716-9a44-9e8eef5d0a13`, ranked controlled existing-test readiness stress plus full58 at 0.95, ordinary repeat-three plus full58 at 0.05, full58-only and none at 0; confidence 0.93 is advisory rather than verified accuracy. Followed, outcome pending; 1,087ms, 699 input/63 output tokens, reported USD0.000029358, provider version/transport/billing unknown. One local annotation schema rejection for a raw filesystem reference was corrected to safe evidence IDs; annotation `728f2b9a-9121-4135-9ae0-4d8da0cd25fd` records followed/pending. Full request/result and ID-to-file mapping: `onboarding-runtime-evidence/ci3992-timing-jev.json`.

Prior independent review and acceptance remain historical for their exact candidates. Current candidate/check bindings are cleared until this correction passes the required full browser command and renewed independent review. Private installation and public enablement remain unperformed here.

The corrected strict browser command subsequently passed all58 discovered/executed journeys in116.959seconds, with zero skips/errors/failures (`ci3992-corrected-full58.log`). Test method names and strict runner are unchanged. Renewed independent review and exact Azure CI remain required before merge.


## Reviewed corrected browser candidate

At `2026-10-02T13:10:20Z`, `agent:/root/onboarding_independent_review` returned Protected independent PASS with no actionable findings for exact clean, pushed `b03ce68425f07755ceece48751a64ff581f41f08`. The review verified readiness semantics, preserved cancellation/newer-input/privacy requirements, the unique receipt container assertion, unchanged58-method admission, hash-bound red/green evidence and full58pass116.959seconds. All four rendering files, route tests and strict runner are byte-identical to cleared4b3; prior P2 closures and locked direction remain valid. Only this fixed evidence and receipt change after review. CI3992's failed result is retained; a new required exact-tail Azure run must pass before accepted merge. Private install, physical-device, SQL, real-identity and live-provider evidence remain separate.
