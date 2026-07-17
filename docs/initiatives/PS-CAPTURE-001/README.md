# PS-CAPTURE-001 - Universal Capture, slice 1

**Status:** Azure SQL applied and verified; PR 56 release verification in progress

**Branch:** `work/2026-07-17-owner-capture`

**Product baseline:** PeerSlate Company and Product Bible v1.4

This package adds the first real Universal Capture surface: a signed-in member
can save a text note as a private canonical intake record and review their own
recent captures. It is a prerequisite for later Journal, Project, Story, Work,
Resume, and Feed placement, but it does not implement any of those destinations.

| Document | Purpose |
| --- | --- |
| `01-requirements.md` | Accepted scope and acceptance criteria |
| `02-current-state.md` | Inspect-first baseline and identified gaps |
| `03-architecture.md` | Request, identity, and storage flow |
| `04-data-model.md` | Capture table and stored-procedure contracts |
| `05-security-privacy.md` | Ownership, visibility, and audit boundaries |
| `06-test-plan.md` | Automated and release verification plan |
| `07-implementation-plan.md` | Ordered delivery plan |
| `08-decisions.md` | Material implementation decisions |
| `09-verification.md` | Commands and evidence |
| `10-handoff.md` | Working, deferred, and release status |
