# PeerSlate handoff — 2026-07-21 FINAL (Claude Code session cutover)

Source of truth: `origin` (Azure DevOps). Chat memory is never the authority;
this file, the repo documents it names, and the Azure branches are.
All build loops were stopped at owner request; in-flight work was committed
and pushed as clearly labeled WIP salvage. Active writer is relinquished on
every lane below — the successor may take ownership from the exact SHAs here.

`main` at handoff: `9940a78f5653d2aa81da2fa34971baffb12601e2`

## Roles and tiers for the successor (owner-defined)

- Manager/architect: top reasoning tier at extra-high.
- Implementer: second tier at extra-high.
- Reviewer: TOP reasoning tier at extra-high — review gets the best brain.
- Review rules (binding, from doc 15 §7): per-item pass/fail against the
  accepted mockups, MEASURED (pixel/proportion), each item cited on desktop
  AND mobile AND dark, no "close enough" category, and two consecutive
  failed reviews escalate back to the architect with the full delta history.
- Pete is the final visual gate on everything user-facing.

## Lane 1 — Journal J1 frontend (INCOMPLETE, highest priority)

- Branch: `work/2026-07-21-journal-frontend-j1-impl`
- HEAD: `e7ed2d5afcf099d0f966677d1c71684a143f37f7` (pushed: yes)
- Status: full bound-book rebuild landed at `1e0fad1`; a 60-item owner
  punch-list fix pass was stopped mid-flight; its partial edits are the WIP
  salvage commit at HEAD. UNAUDITED — treat no item as closed.
- Spec: `docs/initiatives/PS-JOURNAL-001/15_VISUAL_FINISH_ADDENDUM_IDENTICAL_BAR.md`
  §5–6e = all 60 owner items (timeline, composer, saved state, empty state,
  Moment detail, Manage) + §7 escalation. Accepted mockups:
  `docs/initiatives/PS-JOURNAL-001/visual-authority/accepted/`.
- Next action: finish the 60 items on this branch, run the measured per-item
  audit, produce desktop+mobile+dark screenshot sets, then Pete visual review.
- Held unmerged; `PEERSLATE_JOURNAL_ENABLED` stays false.
- Self-certification: Conditional (incomplete by owner stop order).

## Lane 2 — Owner Home frontend (INCOMPLETE)

- Branch: `work/2026-07-21-home-frontend-001-impl`
- HEAD: `e4377ced0c88fbb35100c5cf2a8cbd0c55ae69a3` (pushed: yes)
- Status: build complete through fix round 1 (`2650b3b`); audits 1 and 2
  returned NO-GO; fix round 2 was stopped mid-flight — partial edits are the
  WIP salvage commit at HEAD. UNAUDITED.
- Authority: `docs/governance/approved_owner_visual_baseline/01_owner_home_interface_mockup.png`
  + `artifacts/ps-owner-home-viewer-gate-001/authority-candidate-31864e4/`
  (~20 accepted screens) + `docs/initiatives/PS-OWNER-HOME-VIEWER-GATE-001/`
  (finite nine-object contract and Sonnet implementation brief).
- Next action: finish fix round 2 against the authority set, re-audit
  (measured, per-item), screenshots, then Pete visual review.
- Held unmerged; `PEERSLATE_OWNER_HOME_ENABLED` stays false.
- Self-certification: Conditional (incomplete by owner stop order).

## Lane 3 — Community tabs (COMPLETE, awaiting acceptance)

- Branch: `work/2026-07-21-community-tabs-impl`
- HEAD: `936d08dcb85fbb86da181600475aab398f68f979` (pushed: yes)
- Status: reviewer-CERTIFIED GO round 1 — navy pixel-matched `#203767`,
  791 tests green, every `/the-slate/*` URL preserved, People & Interests
  retired via 302 redirects. Review zip already delivered to Pete.
- Next action: Pete's visual verdict + successor visual second-review →
  Azure PR → squash merge → pipeline → production verification.
- Self-certification: Pass.

## Successor's first assignment: visual second-review

Review finished work per-item against the accepted authorities (numbered
punch list; measured; desktop+mobile+dark; no "close enough"):
1. Community tabs (ready now — screenshots on the branch / Pete's zip).
2. Journal and Owner Home when their remaining fixes land.

## Open investigation: login "not set up" nag

Signed-in owner sees a "not set up" style nag. Pete will supply a screenshot
plus the sign-in email used. Owner allowlist in production is
`peerslate19@gmail.com` — a different email is the likely cause. Auth code:
`auth_routes.py`. Small fix expected; coordinate with the Home lane's
`auth_routes.py` reservation.

## Merged and live this session (verified)

Sample-community honesty labels; signed-in Sign out control; Journal J1
backend + accent-insensitive search (flag off; SQL proposed-only — migration
gate runbook is `docs/initiatives/PS-JOURNAL-001/12_MIGRATION_GATE_RUNBOOK.md`
and has NOT been run); community package activation records; this handoff.

## Owner's own checklist

- GitHub mirror: run `git push github main --follow-tags` from the main
  checkout, then the mirror record can be updated.
- Send the login-nag screenshot + which email was used to sign in.
- Give the Community verdict from the delivered review zip.

## Standing owner rules (short form)

Pixel rule — the accepted mockups' sampled pixels are the palette AND
typography authority; no substitution with site tokens. Fixtures mirror the
mockup's exact rows/dates/counts (doc 15 item 51). Empty-state quote is
signed with the member's own profile name, dynamically (doc 15 item 37).
Sample data stays honestly labeled. One writer per branch; work branches
squash-merge via Azure PR; never push `main` directly; GitHub Actions stays
disabled; flags stay false until the migration gate, Pete's acceptance, and
explicit go. Deferred by owner: AI bill protection, navigation route-map,
rail R2 résumé restyle, PS-SHELL-001 (needs generated visual authority),
PS-ONBOARD-001, PS-RESUME-STUDIO-001, multi-tenant question.

## Local machine notes (primary Mac)

Superseded local worktrees/branches from earlier Journal iterations remain
under `/Users/petercarter/portfolio/.claude/worktrees/` (`j1-punchlist-close`,
`j1-visual-finish-continue`, `j1-visfinish-cont-wf2e3ac`, `journal-j1-continue`,
`fix-round-1`, and the stopped loop worktrees). They are superseded history —
do not resume them; safe to remove after a preservation glance. Long-lived
review worktrees under `~/Documents/Website/` (member-history etc.) are
preserved pending review per the garage-cleanout record.
