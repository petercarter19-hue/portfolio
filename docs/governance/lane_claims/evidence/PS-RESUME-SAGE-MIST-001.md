# Approved Sage Mist public resume release

Delivery path: Protected. Writer: session:01a0fea6-6252-7f92-9ce8-c14882af5a3a.
Base: ded9ee4f150f4e85fe06a3e0254c9f1fc46a43a4. Claim activation: Azure PR 1284,
current-target CI 4249 succeeded. Production is not deployed by activation.

Pete approved R12 and explicitly requested deployment, then reiterated checking
all sizes, fonts and spacing. Owner references:
session:01a0fea6-6252-7f92-9ce8-c14882af5a3a/event:evt-d57e1e9d-0f93-4d87-8376-e4c311b1468a
and evt-d753e41b-f4e0-4ac1-97f0-baa0fe8c2488. This approval locks the existing
direction; this package implements it and does not create a new visual direction.

Exact visual reference: C:/Users/peter/.codex/visualizations/2026/10/02/
01a0fea6-6252-7f92-9ce8-c14882af5a3a/resume-compositions.html,
SHA256 8eabf900126e3668787c1ef91d363dc93ab9ccff457ad4eb7390c4a6ea14ea4a.
Supporting R12 screenshots and validation remain in that same session directory.
Review controls, sample replies, inline mockup photos and sample phone numbers
are exploratory scaffolding and must not ship. Production uses its current data,
images, source contracts and connected AI controller.

Scope: the public resume2 composition, reusable overview partials within that
composition, one connected Ask Pete companion and associated checks. The newer
member publication reader, private onboarding, canonical content, AI provider,
identity, schema, feature flags and a future contact page remain outside scope.
The existing published member reader is a separate template and is not claimed
as updated by this release.

Jev checkpoint: skip. First eligible status observation
5b89f698-6028-425a-94f2-efa3d43bbe60 reported usable_now=false with
ongoing_paused_transport_failure. No inference, retries or settings changes.
The owner settled the visual direction and deployment. For transfer choices,
regression selection and review focus, use current source, locked R12 and the
required independent review. Focused existing route/template/AI checks plus a
browser matrix close the actual layout and conversation risks; no full-site
audit or unrelated onboarding work is introduced.

Local setup: the lifecycle-created durable checkout inherited sparse selection
from control. Task-bound write preflight passed before disabling sparse checkout
in this owned worktree. No source files changed. Startup readiness reported
command_unavailable; authority comes from successful delivery preflight. The
initial system runtime lacked a test-only provider placeholder and used
Werkzeug 3.1.8, causing existing IPv6 compatibility tests to fail. An external
isolated test runtime uses pinned Werkzeug 3.1.9 and Flask 3.1.3 with a dummy
test key. The unchanged-source focused baseline then passed all 97 tests.

Baseline evidence: X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/baseline.log.
Live-before screenshots in that directory capture the current 1440px layout;
the rail measured 331.26px. One live recruiter brief returned HTTP 200,
ask-pete-public-answer.v1, partially_supported, four claims and three public
source links. Live /healthz returned 200 with release 26c1898da674198beddb8fa1.
These are baseline facts, not proof of this candidate's deployment.

Implementation and self-review: the existing public reader now uses a bounded
main column and one 240px right rail (225px at narrow desktop). White background,
ivory/sage surfaces and gold actions follow R12. Entered employer case, approved
photos, authored content, detailed records and the career constellation remain.
Four displayed impact metrics do not change the canonical five; hero impact
buttons reveal their real source context. Optional approved public phone values
are supported without samples, private-record reads or schema changes. The current
public record has no phone. Internal overview previews retain their prior actions.

One grounded companion moves between central content, rail and mobile sheet.
Turns stay in page memory; earlier source buttons and show-all use their own
locators. Follow-up questions retain the existing independent-grounding request
contract; this is not a server-side conversational-memory change. Draft edits made
during a request survive its completion. Native contact and navigation disclosures,
balanced actual skill/impact rows and optional credential groups preserve space.

Pre-candidate verification: 149 focused tests pass, including 6 real Chrome
interaction tests and 4 content tests. Browser variants cover 320, 390, 900, 1024,
1440 and 2560px, 1024x500 and 1280x500, effective 200-percent reflow, long intro,
no story/photos, education alone and skill counts 1/15/16/17. Composer geometry,
one AI instance, history/draft relocation, older evidence, reduced motion, keyboard
impact/contact/navigation, cancellation and unavailable/insufficient recovery
pass. Controlled responses establish browser behavior, not live AI/provider or
private-message delivery. Test-only fixtures and captures are outside production
data. External evidence: X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/
pre-candidate-tests.log and production-local screenshots. Initial browser harness
errors (an invalid fixture claim kind and a Python locator typo) were corrected;
the final run passes. Physical devices remain untested.

Release remains pending independent exact-candidate review, current-target CI,
merge, manual exact-main-SHA deployment and live verification.

Independent first review of e7527c9d980b8c57ba0d14f7df2d2ca3ee5c8eb0 requested
two contrast corrections: footer child text inherited blue with 1.001:1 contrast,
and small gold headline/attribution measured 4.407:1 and 4.216:1. The revised
candidate gives the footer span ivory and small gold text a darker gold while
preserving the approved sizes. The reviewer independently passed 52 focused
checks and verified visual fidelity and browser geometry. One cancellation-test
cleanup race attempted the backend with a forced dummy key and returned
provider_unavailable; no successful inference is evidenced. The browser harness
now blocks the backend adapter too and aborts pending routes before unroute,
preventing provider access even during cleanup. Review evidence is external
reviewer-*.png and reviewer logs in the same package evidence directory. No
private-message sends, production config or provider contracts changed.

Full Azure CI 4251 ran 7555 tests and found one older preview assertion that
still required the PDF link intentionally removed by the approved composition.
The assertion now requires its absence; other preview behavior remains intact.
Control PR 1286 extended this same package by the exact existing preview test
file, passed current-target CI 4254, and merged as
5cb51eaccb5d74f1de25e1a43a3d46732580924c. The lifecycle journal reconciled that
accepted main into the owned checkout as b247ecb394addb0725d4c3b59cbeedb5c45b52e0.
Fresh write preflight passes. No additional runtime change or visual direction
was introduced. The resulting candidate requires its own affected checks,
exact-SHA delta review and current-target CI before merge.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-RESUME-SAGE-MIST-001",
  "plan_sha": "806ba94328c859e8e34c9a65cd0d914dd11ac93c",
  "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
  "baseline": [
    {
      "command": "test-runtime/python -B -m unittest tests.test_resume2 tests.test_member_overview_public_integration tests.test_member_overview_renderer tests.test_member_overview_accessibility tests.ask_pete.test_resume_evidence_companion tests.ask_pete_direct.test_companion_answer_order (test-only key, Flask 3.1.3, Werkzeug 3.1.9)",
      "exit_code": 0,
      "observation": "97 unchanged-source route, overview, accessibility and companion tests passed after matching pinned framework versions."
    }
  ],
  "criteria": [
    {
      "id": "approved_composition",
      "expected": "Implement locked R12 Sage Mist: bounded main plus one compact right rail, white background, ivory and sage surfaces, gold accents, coordinated compact type, bold job titles and entered employer case, short story action, contact details in responsive collapsible placement, six section destinations and no PDF navigation or duplicate overview achievements.",
      "verification": "Compare browser captures and computed style/geometry against R12 and assert production template destinations and content."
    },
    {
      "id": "connected_ai",
      "expected": "One real companion starts centrally and moves to rail or a mobile sheet with draft and transcript preserved. Two opening prompts, no opening evidence preview, busy glow, visible follow-up composer, scrollable turns, compact inspectable evidence and truthful unavailable/insufficient-information paths. Direct messages require existing explicit consent/send; no mock replies or persistence changes.",
      "verification": "Browser requests with controlled structured responses exercise opening, working, answer, evidence, repeated turns, relocation, resize, cancellation and insufficient/unavailable recovery; existing AI and direct-message contract tests remain green."
    },
    {
      "id": "responsive_accessibility",
      "expected": "No unintended horizontal overflow or clipped panel/composer at 320, 390, 900, 1024, 1440 and 2560px or short 1024x500 and 1280x500 windows. Maintain readable matched text, visible scroll affordances, keyboard controls, reduced motion, logical landmarks/headings, focus and 200-percent zoom/reflow.",
      "verification": "Real-browser dimension matrix, opening/scrolled screenshots, geometry/font checks and keyboard/reduced-motion/zoom interaction tests."
    },
    {
      "id": "adaptive_content",
      "expected": "Optional photos/story/credential groups release their space. Long intro/contact content wraps without clipping. Featured impact display caps at four without canonical edits; impact flips reveal real supporting text. Ungrouped skills balance rows and remain compact for counts 1, 15, 16 and 17. Credential groups reflow when only education remains.",
      "verification": "Controlled production-renderer fixtures and browser variants for missing and long content, skill counts and impact interaction; no fabricated filler cells."
    },
    {
      "id": "source_contracts",
      "expected": "Preserve existing authored content and approved images, route/fallback behavior, source locator targets, skills/experience/credentials and career constellation interactions. No backend/provider/identity/schema/flag/private-publication edits, fixture leaks, sample phone data or automatic contact sends.",
      "verification": "Focused existing regressions, content/source-path diff inspection and browser navigation/source-opening checks, followed by an independent exact-candidate review."
    }
  ],
  "checks": [
    {
      "criterion_id": "approved_composition",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
      "source_ref": "X:\\PeerSlate\\Claude\\reviews\\2026-10-08_sage-mist-compact-review.md",
      "observed": "The approved Sage Mist composition is unchanged outside the short-window rail: the independent reviewer compared screenshots and found the 1440x900 answered rail and the 390x844 phone sheet pixel-identical to the base. The only visible changes are inside the compact rail at 1024x500 and 1280x500 (answer heading and text in view, source-note line hidden visually, two-line input). Rebound to release-record candidate 7b820a94: every claimed runtime and test surface is byte-identical to 559d91f1 (git diff empty), the candidate changes only CURRENT_BASELINE.yaml and its pointer test, and production run 4451 serves those exact bytes (sha256 match in X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/live-proof.json).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-07/allowance-reviewer",
        "captured_at": "2026-10-08T22:15:06Z",
        "source_ref": "X:\\PeerSlate\\Claude\\reviews\\2026-10-08_sage-mist-compact-review.md"
      }
    },
    {
      "criterion_id": "connected_ai",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-RESUME-SAGE-MIST-001\\claude-compact-correction-2026-10-08\\comparison-summary.json",
      "observed": "One companion keeps its history, unsent draft, focus and sources across rail, sheet and resize. All 9 Sage Mist browser tests pass normally and in 12 of 12 runs under 4x parallel load on the merged tree, including relocation/draft/historical-source, cancellation/recovery and the three new short-rail tests (resize route, opened directly short, reader viewing earlier messages). The new tests fail on the shipped code, and the reader test fails with the reader guard removed. Browser requests use controlled responses with the provider boundary blocked. Rebound to release-record candidate 7b820a94: every claimed runtime and test surface is byte-identical to 559d91f1 (git diff empty), the candidate changes only CURRENT_BASELINE.yaml and its pointer test, and production run 4451 serves those exact bytes (sha256 match in X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/live-proof.json)."
    },
    {
      "criterion_id": "responsive_accessibility",
      "result": "pass",
      "kind": "browser",
      "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-RESUME-SAGE-MIST-001\\claude-compact-correction-2026-10-08\\screenshots\\1-1024x500-after-resize.png",
      "observed": "At 1024x500 and 1280x500 after relocation to the rail and a resize with an unsent draft, the transcript grows from 22px to 130px and from 55px to 148px (measured against the shipped code), with the latest answer heading and its first lines visible beside the full draft; at 1440x900 and in the 390x844 sheet the layout is unchanged. The status line keeps aria-live=polite and the input keeps aria-describedby for the visually hidden source note; the independent reviewer verified that keyboard focus is never scrolled away by the re-alignment after any user input, with no loop. No physical-device or screen-reader run is claimed. Rebound to release-record candidate 7b820a94: every claimed runtime and test surface is byte-identical to 559d91f1 (git diff empty), the candidate changes only CURRENT_BASELINE.yaml and its pointer test, and production run 4451 serves those exact bytes (sha256 match in X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/live-proof.json).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-08/sage-mist-compact",
        "captured_at": "2026-10-08T16:17:31Z",
        "source_ref": "X:\\PeerSlate\\evidence\\PS-RESUME-SAGE-MIST-001\\claude-compact-correction-2026-10-08\\screenshots\\1-1024x500-after-resize.png"
      }
    },
    {
      "criterion_id": "adaptive_content",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
      "source_ref": "X:\\PeerSlate\\evidence\\PS-RESUME-SAGE-MIST-001\\claude-compact-correction-2026-10-08\\full-discover-on-559d91f1.log",
      "observed": "Optional photos, story and credential groups still release their space and skill counts 1/15/16/17 still balance without filler: test_optional_groups_long_copy_and_balanced_skill_counts passes in the 9/9 browser suite and the 149 focused non-browser tests pass. This correction changes no content, template or balancing code, only the compact-rail AI layout. Rebound to release-record candidate 7b820a94: every claimed runtime and test surface is byte-identical to 559d91f1 (git diff empty), the candidate changes only CURRENT_BASELINE.yaml and its pointer test, and production run 4451 serves those exact bytes (sha256 match in X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/live-proof.json)."
    },
    {
      "criterion_id": "source_contracts",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "7b820a94fbd0513cf35e6cf7d85b8e019b9eba45",
      "source_ref": "X:\\PeerSlate\\Claude\\reviews\\2026-10-08_sage-mist-compact-review.md",
      "observed": "Independent exact-SHA review PASS with no findings. The change is three files within the claim (rail stylesheet, companion script, browser test); no backend, provider, identity, schema, flag, private-publication or content change and no sample data. In the full repository run 47 tests do not pass; every one also fails on untouched main da2e34fd except one slow worktree-lifecycle test that was not compared on base. Onboarding intake changes on main stay dormant while the intake flags are unset. Rebound to release-record candidate 7b820a94: every claimed runtime and test surface is byte-identical to 559d91f1 (git diff empty), the candidate changes only CURRENT_BASELINE.yaml and its pointer test, and production run 4451 serves those exact bytes (sha256 match in X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/live-proof.json).",
      "provenance": {
        "observer_ref": "agent:claude/2026-10-07/allowance-reviewer",
        "captured_at": "2026-10-08T22:15:06Z",
        "source_ref": "X:\\PeerSlate\\Claude\\reviews\\2026-10-08_sage-mist-compact-review.md"
      }
    }
  ]
}
```

Prior runtime-reviewed candidate: 892636e8af8e36cad3b6f667036589b8cf756fd6. All 150 focused checks pass.
Independent reviewer agent:sage_mist_final_review returned PASS on that exact SHA;
2 delta Chrome checks independently pass and prior 52-check review remains
applicable. Both P2 contrast findings resolved (footer 4.530:1, small headline
6.081:1, career attribution 5.817:1). Test teardown provider isolation is verified.
Reviewer configured gpt-6.1-sol / xhigh; effective runtime settings and exact
package usage telemetry are unavailable. No claim of physical-device testing or
private-message delivery.

Completion remains pending current-target PR CI, accepted merge, manual
exact-main-SHA production deployment and live proof. Final release and custody
results will be recorded under X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/
release-closeout.json. Authorization never implies completion.

Final reviewed candidate: 4c65fc7ad32583ade256ff98b07868fad179610f. Independent exact-SHA delta review PASS;
5 preview tests pass independently with provider boundary blocked and zero calls.
All 155 focused tests pass, including seven Chrome interaction/contrast checks.
Runtime files match the previously accepted visual candidate exactly.
Current-target product CI, merge, manual production deploy and live proof remain
pending. This post-review tail changes only fixed acceptance evidence and receipt.

## Compact-window correction round (2026-10-08)

Writer `agent:claude/2026-10-08/sage-mist-compact` (Claude Code; Opus 5.5 for diagnosis, Sonnet 5.5 for implementation and merge steps; effective effort is not inspectable from inside the session and is reported unverified). Custody arrived by the voluntary delivery-transfer from `session:01a0fea6-6252-7f92-9ce8-c14882af5a3a` (Azure PR 1300, main da2e34fd), on Codex's pushed WIP checkpoint b0fba01c, whose three files matched the handoff snapshot hashes. Main da2e34fd was merged into the branch as 7898d91c; it touched no claimed surface. Write preflight passed with this writer's own reference and registered caller context. Owner decision reference: `agent:claude/2026-10-07/peerslate-manager/owner-decision/2026-10-08-sage-mist-compact-to-claude`. Package scope is unchanged; this is a bounded usability correction, not a new visual direction.

Defect: with the AI relocated to the right rail in a short desktop window (1024x500, 1280x500) the transcript had 22px and 55px, and the latest answer stayed scrolled out of view. Per-frame recording showed the one-time reveal ran before the rail finished settling, and the unfinished local test waited on a selector (`data-ask-pete-caption`) that does not exist.

Correction (candidate 559d91f1629cb71e48b9bc538369eef7e8203487): in the compact rail only, the latest answer is re-aligned whenever the transcript or answer changes size, until the reader scrolls, clicks or tabs into the transcript. The compact answered dock hides the repeated status and source-note lines visually (both stay in the accessibility tree) and sizes the input for two lines. Result: the transcript is 130px at 1024x500 and 148px at 1280x500, with the heading and first answer lines visible beside the full draft. The unfinished test was replaced by three tests that wait on real layout conditions; two load-timing races in the new reader test were fixed in the test (the wheel scroll had not yet been applied), not by loosening it.

Verification: 9/9 Sage Mist browser tests pass normally and in 12 of 12 runs under 4x parallel load; the reader test passed 20 of 20 under 5x load; 149 focused non-browser tests pass. The full `unittest discover` ran 7496 tests with 47 not passing (11 failures, 36 errors, 13 skipped). A rerun of the failing files on untouched main da2e34fd (13 files, 386 tests, 49 not passing) reproduces every one of them. The causes are this machine's missing azure.storage, packaging, PDF parser and Unix-only resource module, Windows file permissions, Mac-only sealed-browser tests, and the three dark-theme browser tests on /petec/resume that expect the pre-Sage-Mist navy ink. One test, `test_worktree_lifecycle.WorktreeLifecycleTests.test_ephemeral_invocation_lease_blocks_concurrent_retirement`, was among the 47 but is **not compared on base** (the file takes too long to rerun); it concerns worktree lease handling and no file in this change. The machine-readable summary and logs are in the external evidence folder named in the checks.

Independent review: `agent:claude/2026-10-07/allowance-reviewer` returned PASS on exactly 559d91f1 with no findings (report X:\PeerSlate\Claude\reviews\2026-10-08_sage-mist-compact-review.md): the reader guard has no loop and never fights user input; the visually hidden text keeps aria-live and aria-describedby; 1440x900 and 390x844 are pixel-identical to the base; tests use real waits. Non-blocking follow-up: after a resize a keyboard-focused control can sit below the shrunken visible area; consider keeping a focused element in view on resize. Release note: `static/js/resume-editor.js` from onboarding round 3 is not intake-gated, so readable card dates ride along wherever the editor is enabled; cosmetic.

Release scope (read-only check against main, 2026-10-08): the résumé-intake and onboarding code on main stays dormant in production while `PEERSLATE_RESUME_INTAKE_ENABLED` and the editor flag are unset; the production app settings were observed read-only with both unset. No public résumé, Ask Pete, authentication or schema code outside this package changes. Re-check what ships immediately before any production run, because main will carry later onboarding rounds.

Limits: all browser proof uses controlled public-answer fixtures and installed Chrome with the provider boundary blocked; no live provider, physical device or screen-reader run is claimed. Merge, deployment and live verification are separate states and are still pending; nothing is deployed by this evidence.

## Release, record and incident (2026-10-11)

Writer `agent:claude/2026-10-11/sage-mist-release-owner` (Claude Code, Opus 5.5). Custody arrived by owner reassignment (PR 1332, main 24a2be07) from the retired, unavailable session `agent:claude/2026-10-08/sage-mist-compact`, on its exact pushed checkpoint 3adf12ee, using Pete's first-hand release decision `agent:claude/2026-10-08/sage-mist-compact/owner-decision/2026-10-10T0234Z-pete-yes-sage-mist-release` (kept valid by his D1 rule; Pete gave no separate writer-replacement decision). Before preparation, two stale generated `services/__pycache__/*.pyc` files in the old checkout were deleted because the tool refused on that residue; nothing else in it changed. The surface extension for the release record is PR 1335 (main 3f712a24), after Codex released `tests/test_operational_readiness.py` (PR 1334).

Scope check before release: since e350b9a5 (the source of the failed run 4417 that Pete approved), main gained only claim files (943f26b7, 24a2be07); nothing visitor-visible.

Release: manual production run 4451 (20261011.10) on main 24a2be074bed391a76e0dcac4184d8defbbb8c18, forceProductionDeploy=true, schemaAction=none, the reference above; queued 03:47Z with no other run active, succeeded 04:05:50Z. The service-connection step that failed in 4417 passed after Codex's workload-identity repair. Live proof (GET only, nothing typed into Ask AI): /healthz moved from f4e77a0ff29a68053e2b4b2e to 6d0ddde1dbaab328719487cc, which equals `release_id_for_build(24a2be07, 4451)`; /petec/resume returns 200 and serves `ask-pete-evidence-companion.js`, `resume-sage-mist.css` and `resume-sage-mist.js` byte-identical to main (contains `keepCompactAnswerInView`; absent before the release); homepage 200; /auth/sign-in redirects to the members sign-in. Records: `X:/PeerSlate/evidence/PS-RESUME-SAGE-MIST-001/release-4451/` (live-proof.json, run-4451.json). No browser screenshot, physical device or provider call is claimed.

Release record: candidate 7b820a94 changes only CURRENT_BASELINE.yaml (846 words) and tests/test_operational_readiness.py in lockstep. Independent review `agent:claude/2026-10-11/sage-mist-record-reviewer`: PASS at 2026-10-11T15:50:54Z, no findings (scope, run facts, release id, note wording, word cap; 140 pointer/registry/site-rules/control-room tests OK). Focused resume suites on 7b820a94: 106 tests ran with 11 subtest failures, all in `tests.test_member_overview_renderer.IPv6LoopbackCompatibilityTests`. They come from this machine's Werkzeug 3.1.8, where requirements pin 3.1.9. Those test bytes are identical on main, so the failures don't come from this change (log: release-4451/focused-on-7b820a94.log).

Incident: an unauthorized production run, 4468, was queued at 2026-10-11T15:33:26Z, on the same source and with this package's authorization reference. A helper's script imported this writer's leftover scratchpad `queue.py`, which queued a run at import time. It was cancelled during Build, the production deploy stage was skipped, and it finished canceled at 15:46:24Z; live stayed 6d0ddde1 (record: release-4451/run-4468.json). `queue.py` is disarmed, and this writer's other scratchpad scripts were renamed to inert `.txt` files. In future, scripts act only under `if __name__ == "__main__"` with explicit arguments, and they run from a unique subfolder, never from the shared scratchpad root.
