# PS-SLATE-STUDIO-IA-001 — D1: Repository Assessment and Dispositions

**Date:** 2026-07-22. **Author:** Claude Code (program manager, under the
2026-07-22 owner delegation recorded in
[01 §2.5–2.6](01_OWNER_DIRECTION_RECORD.md)). All facts verified by direct
inspection or read-only reconnaissance on this date against `origin/main`
`e1272220f539f41810698855341b9399b14ebd73`.

## 1. Verified current state

**On `main` (e127222):** backend and flag infrastructure for all three
in-flight products — Journal API/service (`peerslate_api.py`,
`services/journal_service.py`), the finite `owner-home.v1` data contract
(`owner_routes.py`), Community routes and base templates — with
`PEERSLATE_JOURNAL_ENABLED` and `PEERSLATE_OWNER_HOME_ENABLED` both
defaulting **false**. No Journal frontend, no `owner_home.html`, no
Community-tabs package on main. Live production behavior is unchanged from
the July 21 release wave.

**On branches (all pushed to origin):**

| Branch | Ahead | Content |
|---|---|---|
| `work/2026-07-22-community-journal-home-milestone-integration` | 65 | Union of the three lanes + integration contract, manifest builder, integrity tests. Checkpoint `b02d4a1…`, handoff received 2026-07-22; being finished now via the Croatia pipeline |
| `work/2026-07-21-journal-frontend-j1-impl` | 25 | Journal J1 frontend (frozen source `099e8e1…`) |
| `work/2026-07-21-community-tabs-impl` | 15 | Community tabs (frozen source `a8c0496…`) |
| `work/2026-07-21-home-frontend-001-impl` | 6 | Owner Home frontend, flag-off (frozen source `f8c8826…`) |
| `work/2026-07-21-mandatory-visual-agent-workflow` | 4 | Governance hardening (visual/dual-review gates) |
| `work/2026-07-22-journal-migration-runner-registration` | 1 | J1 migration-runner registration |
| `work/2026-07-22-journal-query-normalization-j1x` | 1 | J1.x search trim fix |
| `work/2026-07-22-public-connective-001` | 1 | PS-PUBLIC-CONNECTIVE-001 stage-1 architecture (gated on mockup approval) |
| `work/2026-07-17-member-history-completion` | 1 | Interview story grounding commit |

**Governance record lag:** the pointer records (`CURRENT_BASELINE.yaml`,
`CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`) were reconciled 2026-07-21
covering through ~PR 125; main now carries PRs 126–160 (≈19 Journal, 4
Community, 2 Owner Home, 4 governance, 5 other). The milestone package is
intentionally absent from shared governance (owner exception, recorded
package-locally). A mini truth-reconciliation is required and is **staged**
by this package — applied only after the milestone lands, to avoid recording
a moving target.

## 2. Foundations the Workshop reuses (do not rebuild)

Identity/two-owner isolation (PS-AUTH-001); private text + Voice Capture;
canonical Moment confirmation (PS-MOMENT-001); exact-version Placement
references (PS-PLACEMENT-001, backend live, never had a UI — the Workshop
Build bench is its first consumer); the public résumé dataset and career
constellation; public Interview Studio 5A/5C (homepage parity closed); public
Ask Pete AI; Deep Navy Gold theme + accepted visual baseline PNGs; and — once
landed — the Journal J1 frontend, Community tabs, and `owner-home.v1`
frontend.

## 3. Missing prerequisites for Workshop wave 1 (the honest pantry check)

1. **Member-editable canonical professional record** (roles, bullets, skills
   as governed, placement-targetable data; no second résumé dataset —
   evolve the existing one). The largest true prerequisite.
2. **Ask Slate runtime** (PS-ASK-SLATE-AI-001 is architecture-only).
3. **Workshop shell** (persistent, deep-linkable, draft-preserving).
4. Signed-in practice persistence (today's Interview Studio is public,
   browser-local).
5. Photo/media intake beyond flag-off Photo (labeled by real availability).

## 4. Dispositions (delegated ruling, program manager, 2026-07-22)

| # | Package / lane | Disposition |
|---|---|---|
| 1 | PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001 | **Finish now** via the Croatia pipeline (in flight). Lands J1 + Community tabs + Owner Home frontend, flags false |
| 2 | PS-JOURNAL-001 | J1 lands with the milestone; Journal-as-destination **stops expanding after J1** (owner ruling 3). Small J1.x branches (`…migration-runner-registration`, `…query-normalization-j1x`) held; reconciled as follow-up PRs after the milestone merges |
| 3 | PS-COMMUNITY-TABS-001 | Lands with the milestone; lane closes at release |
| 4 | PS-HOME-FRONTEND-001 | Lands with the milestone, flag-off. Owner Home's evolution (into or beside the Workshop opening surface) is decided in D3 with priced options |
| 5 | PS-SHELL-001 | **Held for D3 ruling.** Lean: absorb into the Workshop shell — one shell effort, not two |
| 6 | PS-RESUME-STUDIO-001 (candidate) | **Absorbed** into the Workshop Build bench (wave-1 candidate, per owner ruling 4) |
| 7 | PS-ONBOARD-001 (candidate) | **Absorbed** into Workshop wave 1 (fused onboarding = the import/transform loop) |
| 8 | PS-RETURN-VALUE-001 | Universal (no-history) sparks pulled forward under owner ruling 1; grounded items remain staged behind real member history. `03_REVISIT_REGISTER.md` remains the canonical idea register |
| 9 | PS-ASK-SLATE-AI-001 | Becomes the Workshop's AI layer; remains a separate package with its own gates; activation sequenced in D5/D6 |
| 10 | PS-STORY-COMPOSER-001 | Unchanged planned; any Build-canvas Story work inherits `OWNER_STORY_COMPOSITION_STANDARD.md` wholesale |
| 11 | PS-PROJECTS-001 | Unchanged planned (Phase 10); boundaries respected by the IA |
| 12 | PS-CAPTURE-MEDIA-001 | Unchanged; Photo enablement gates unaffected; Workshop intake labels media types by real availability |
| 13 | PS-ASK-PETE-AI-001 | Unchanged public-only surface |
| 14 | `work/2026-07-21-mandatory-visual-agent-workflow` | **Review before any Croatia governance edit applies** — potential collision on governance files. Program manager reviews content post-milestone and recommends merge/supersede to Pete |
| 15 | `work/2026-07-22-public-connective-001` | Parked at stage 1 as its own README states (gated on mockup approval); no collision with Croatia |
| 16 | `work/2026-07-17-member-history-completion` | Orphan single commit; evaluate post-milestone (small PR or archive tag) — flagged to Pete with a recommendation then |
| 17 | Closed packages (Interview, Voice, Photo lifecycle, parity, etc.) | Untouched |

## 5. Conflicts and truth-state corrections required

1. `CURRENT_BASELINE.yaml` `next_gate` (staff the PS-JOURNAL-001 private
   core) is superseded by owner ruling 3 — rewrite staged, applied via
   governance post-milestone.
2. Pointer records lag PRs 126–160 (§1) — mini-reconciliation staged.
3. PS-RETURN-VALUE-001 staging rule vs. owner ruling 1 — amendment staged
   (universal-spark subset only).
4. Milestone package docs name a superseded review chain (Codex/Terra/Sol);
   re-routing to the Croatia pipeline is being recorded package-locally by
   the milestone writer (dated note), not by rewriting history.
5. Governance-hardening branch (row 14) must be dispositioned before this
   package touches any shared governance file.

## 6. Next actions for this package

1. Receive the milestone writer's P/E handoff → Pete visual gate → Opus
   review → Claude Code audit → Pete-authorized release (flags false).
2. Draft D4 (candidate idea inventory) from the three tracked inputs.
3. D3 IA package: Workshop shell/areas, Owner Home model decision, shell
   ruling (row 5), Ask Slate integration points.
4. Post-milestone: apply staged governance edits (next_gate rewrite +
   mini-reconciliation + Bible v2.9/Roadmap v2.8 proposals) after the row-14
   review.
5. D6/D7 against Pete's accepted Workshop mockups.

## 7. Owner refinements after the assessment (2026-07-23)

Recorded by Codex at Pete's direction. These decisions refine the target IA and
future package sequence; they do not change the verified 2026-07-22 repository
facts above and authorize no runtime work.

1. **Build Your Future combines Build and Future.** Slate Board is its central
   canvas rather than a separate Slate Studio destination. The Board's spatial
   character is retained, while direct résumé/Work/Story/Project development,
   grounded directions, skills, and experiments operate in one private room.
2. **The public Living Résumé and My Story remain.** They may receive later
   visual-alignment reviews after Slate Studio is locked, but this package does
   not replace their routes, datasets, content, behavior, or product purpose.
3. **Interview Studio is a provisional current name.** The current public
   product remains unchanged, while a later governed package defines one
   broader practice/rehearsal/review/coaching system with Interview as a
   scenario family, a meaningful feedback-and-retry loop, sensitive-workplace
   safeguards, and one final umbrella name.
4. **Bible/Roadmap placement is staged, not applied here.** The proposed Bible
   update belongs in the Slate Studio product definition and invariants. The
   proposed Roadmap gate follows IA acceptance and precedes any rename, route
   transition, visual alignment, or new practice-scenario implementation.
5. **Ambient Community pulse is a Revisit candidate.** A future desktop/tablet
   edge rail may show a few authorized Connection updates, but it is excluded
   from current mockups and wave 1 pending distraction, privacy, responsive,
   accessibility, and product-value testing.
