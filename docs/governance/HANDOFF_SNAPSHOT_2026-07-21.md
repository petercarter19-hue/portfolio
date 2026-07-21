# PeerSlate Handoff Snapshot — 2026-07-21 (living document)

**Purpose:** continuity insurance. If the current Claude Code session ends
mid-flight, this + the repo is everything a successor (ChatGPT Work session or
a fresh Claude session) needs. Chat memory is never the authority; this file,
`docs/initiatives/PS-JOURNAL-001/15_VISUAL_FINISH_ADDENDUM_IDENTICAL_BAR.md`
(the 60-item owner punch ledger + escalation rules), and the Azure branches are.

## Roles (owner-defined)
Architect/manager ("Fable-tier") → strongest reasoning model, extra-high.
Implementer ("Sonnet-tier") → extra-high. Reviewer ("Opus-tier") → strongest
reasoning at extra-high — REVIEW GETS THE BEST BRAIN. Review rules: per-item
pass/fail vs the accepted mockups, MEASURED (pixel/proportion), desktop AND
mobile AND dark cited per item, no "close enough" category; two consecutive
NO-GOs escalate to the architect with full delta history. Owner (Pete) is the
final visual gate on everything.

## Lane states (as of this snapshot — verify tips with `git fetch origin`)

1. **Journal J1 frontend** — branch `work/2026-07-21-journal-frontend-j1-impl`
   (last pushed tip at snapshot: 1e0fad1 rebuild). A 60-item owner punch-list
   fix pass was in flight (doc 15 §5–6e). If its commit is present on the
   branch, continue from it; else re-run the fix per doc 15, then the measured
   audit. HELD UNMERGED until: audit GO → Pete visual acceptance → ChatGPT
   visual second-review. Flag `PEERSLATE_JOURNAL_ENABLED` stays false.
2. **Owner Home frontend** — branch `work/2026-07-21-home-frontend-001-impl`
   (tip at snapshot: 2650b3b, fix round 1). Audits 1 and 2 = NO-GO; fix round
   2 was in flight. Authority: `approved_owner_visual_baseline/
   01_owner_home_interface_mockup.png` + `artifacts/ps-owner-home-viewer-gate-001/
   authority-candidate-31864e4/` (~20 screens) + FINITE_HOME_CONTRACT (nine
   objects). Same held-unmerged rule; `PEERSLATE_OWNER_HOME_ENABLED` false.
3. **Community tabs** — branch `work/2026-07-21-community-tabs-impl` @
   936d08d, **Opus-CERTIFIED GO round 1** (791 tests). Awaiting Pete's visual
   verdict (review zip delivered) + ChatGPT visual second-review. Then PR +
   squash merge (public change — Pete acceptance REQUIRED first).
4. **Journal backend + search** — MERGED (PRs 129/140), flag off. SQL is
   proposed-only; the migration gate runbook is
   `docs/initiatives/PS-JOURNAL-001/12_MIGRATION_GATE_RUNBOOK.md` (run the
   trio live + two-owner verify before any flag-on; collation now CI_AI per
   owner). J1.2 queued: detail-narrative read + voice-source playback linkage.

## Open items for the successor
- ChatGPT VISUAL REVIEW of finished sets (Community now; Journal + Home when
  their loops land): side-by-side vs the accepted PNGs in
  `docs/initiatives/PS-JOURNAL-001/visual-authority/accepted/` and the Home
  authority above; return findings as a numbered punch list.
- "Not set up" login nag: diagnose from Pete's screenshot + sign-in email
  (owner allowlist in prod = peerslate19@gmail.com). Fix likely small;
  coordinate with the Home lane's auth_routes reservation.
- PS-SHELL-001 (staged): needs ChatGPT-generated visual authority (two-tone
  shell, consistent header/width, type scale, room silhouettes) → Pete
  accepts → then implementation via the standard loop.
- Migration gate → flag-on → Pete+Danielle pilot (after Journal acceptance).
- Deferred by owner: navigation route-map package, AI bill protection, rail
  R2 résumé restyle, PS-ONBOARD-001 / PS-RESUME-STUDIO-001 (planned).
- GitHub mirror: Pete pushes `git push github main --follow-tags` himself;
  then update the baseline mirror record.

## Standing owner rules
Pixel rule (accepted mockups' sampled pixels are the palette/type authority —
no substitution); mockup-exact fixtures (doc 15 item 51); dynamic member-name
quote signature (item 37); typography override (mockup type IS the spec);
sample-data honesty labels everywhere; one writer per branch; squash-merge via
Azure PR; never push main directly; flag-off until Pete accepts + gates pass.
