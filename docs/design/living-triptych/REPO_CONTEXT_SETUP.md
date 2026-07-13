# Shared Repository Context Setup

Place this package at:

`docs/design/living-triptych/`

Then add or merge the following guidance into the repository root.

## AGENTS.md

```md
# PeerSlate Agent Context

Before changing the Overview experience, read:

- `docs/design/living-triptych/LIVING_TRIPTYCH_VISION.md`
- `docs/design/living-triptych/KICKOFF_PROMPT_FOR_BOTH_AGENTS.md`
- all mockups in `docs/design/living-triptych/mockups/`

Codex and Claude Code are equal collaborators with no fixed role boundaries. Preserve decisions and findings under `docs/design/living-triptych/agent-notes/`.
```

## CLAUDE.md

```md
@AGENTS.md
```

If either file already exists, merge this context rather than overwriting existing repository guidance.

## Suggested Parallel Branches

- `experiment/living-triptych-codex`
- `experiment/living-triptych-claude`

These are not role assignments. They are isolated workspaces that allow both agents to explore any part of the implementation without overwriting one another.
