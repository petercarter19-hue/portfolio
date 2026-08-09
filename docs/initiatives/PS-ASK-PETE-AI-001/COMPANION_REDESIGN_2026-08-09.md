# Ask Pete companion redesign — owner-directed revision (2026-08-09)

**Visual authority.** This is a MATERIAL, owner-directed revision of the
accepted Concept H companion. Direction came from Pete verbatim (design
round recorded 2026-08-09); he reviewed the fixture-backed local preview
side-by-side the same day and accepted it ("this is good... let's stick
with this"), which closes the visual-authority loop for this revision.

**What changed for a visitor.** One answer now fits one rail view (fixture
measure: ~439px against ~5,400px live before): summary and a single
answer-level trust badge; the required boundary claim folded to one quiet
sentence under the summary (server quality contract unchanged); evidence
folded behind "N claims · <source summary> · See the evidence" with claim
cards that expand to the exact quote and one open-on-resume action each;
badges retained only where support is NOT established (plus a quiet
Interpretation tag); the suggested-questions block removed; one compact
"Ask Pete directly" entry replacing the three overlapping contact entries;
the composer docked always-visible with the restored gold focus treatment.

**Also shipped in the same PR (both pre-tested).** The rule-10 refusal
wording replacement in prompts/ask_pete/grounded_public_v1.md (tested
against the live provider 2026-08-09: 3/3 refusals clean, 4/4 answer types
unaffected, no internal machinery named, no implied future scoring) and the
hidden-tab scroll fix (instant jump when document.visibilityState is
hidden, one re-reveal on return; proven live before building).

**Branch and SHAs.** work/2026-08-09-companion-redesign-001 from a7a0328,
three commits (54467de redesign, e8d0f4e fixes, cfa620c harness checks),
merged to main as aa4a4ec via PR 365.

**Changed paths.** templates/partials/ask_pete_evidence_companion.html,
static/js/ask-pete-evidence-companion.js,
static/css/ask-pete-resume-evidence.css,
prompts/ask_pete/grounded_public_v1.md, tests/ask_pete_direct/ (tests and
preview harness), tests/ask_pete/test_resume_evidence_companion.py.

**Verification.** 370 unit tests pass; run_direct_preview.py --check passes
all 37 checks including new browser assertions for each redesign decision
(fold collapsed by default, one trust line, no badge on established claims,
no boundary card, composer docked). Live after run 722: /healthz release
689d0be742c2c8d02c585827; the live resume page serves the docked companion
markup and the folded-evidence script.

**Limits / next.** The live pass was a smoke (markup, script, idle panel) —
no paid provider question was asked on production. The panel's slight
translucency over busy page content predates this change and is left for
Pete's taste review. Pete's post-release review is the next step under the
2026-08-09 ship-to-live default.
