# Claude Fable catch-up and review prompt

You are joining the existing PeerSlate redesign project.

First, read:
- `CLAUDE.md`
- imported `AGENTS.md`
- the four source-of-truth documents under `docs/peerslate/`
- `docs/peerslate/IMPLEMENTATION_HANDOFF.md`
- the approved visual references
- any Codex preflight and first-pass reports under `docs/implementation-reports/`

Then respond with only:

1. A concise statement of the approved Foundation C direction.
2. The approved Living Résumé architecture.
3. The approved Slate Board architecture and Add-to-Board flow.
4. The non-negotiable multi-user, privacy, evidence, and voice rules.
5. The branches/worktrees Codex created and what each currently contains.
6. Any conflict between the repository implementation and the approved documents.
7. The three highest-priority review items for Pete.

Do not redesign the pages, write code, merge branches, or infer missing requirements during this catch-up step.

After Pete confirms your summary, use plan mode to review Codex's implementation. Preserve existing production pages and distinguish fixture UI from real backend functionality.
