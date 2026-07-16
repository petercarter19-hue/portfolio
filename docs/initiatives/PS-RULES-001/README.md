# PS-RULES-001 — Repository rules and product guardrails

Delivered 2026-07-16.

**What landed**
- `docs/PEERSLATE_SITE_RULES.md` — the approved 85-rule document, verbatim.
- `docs/PEERSLATE_V12_IMPLEMENTATION_INSTRUCTIONS.md` — the approved v1.2
  package program (owner-supplied), verbatim.
- `PeerSlate_Company_and_Product_Bible_v1.2.docx` — the authoritative Bible
  (owner's July 16 edition), now tracked at the repo root.
- Root `CLAUDE.md` + `AGENTS.md` point to the v1.2 governance before any
  product work.
- `docs/INITIATIVE_CHECKLIST.md` — the per-package/PR checklist.
- `tests/test_site_rules.py` — automated guardrails: no auto-deploying
  GitHub workflow, no hardcoded owner IDs in reusable code, no job-listing
  routes, no secret names in client JS, governance docs present.
- `.github/workflows/main_peerslate-pete.yml` — push trigger removed so a
  repository-settings change can never silently re-enable GitHub
  deployment (Azure Pipelines remains the only path; file kept as history).

**Decisions**
- Evidence-in-navigation and About-in-navigation checks land WITH
  PS-BRAND-NAV-001 (which removes those labels) so the suite is never
  deliberately red between packages.
- Word checks target UI/navigation surfaces, not documentation or
  migration notes (per the "no brittle word-ban" instruction).

**Verification**: full suite green (see PR); guardrail tests pass.
**Handoff**: checklist answers — docs-only + one inert workflow edit; no
canonical objects, audiences, or AI behavior affected; nothing mocked.
