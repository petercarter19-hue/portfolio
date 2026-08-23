@AGENTS.md
@docs/AI_WORKFLOW.md

> **MANDATORY PRE-WORK GATE**
> Follow [`START_HERE.md`](START_HERE.md) before a write, migration,
> deployment, or product decision. Fetch Azure `origin/main`, read
> `CURRENT_BASELINE.yaml` and `DOCUMENT_CONTROL.md`, choose Routine, Bounded
> or Protected, and read the package claim. Before implementation edits, pass
> the exact `delivery_preflight.py --intent write --fetch --require-clean`
> command. For a control-only activation/state transition, run `--intent read`
> before editing, commit only the exact claim on its dedicated control branch,
> then pass the matching control intent before PR; do not edit implementation
> surfaces in that control commit.

`DOCUMENT_CONTROL.md` identifies the governing Constitution and
Roadmap. Historical documents remain evidence, not extra gates.

# Claude / Claude Code instructions

Claude Code may own an explicitly assigned branch and claimed surfaces. An
implementation assignment normally continues through implementation,
validation, review correction, Azure PR, and accepted merge. A review-only or
narrower assignment does only what it says. Independent reviewers are
read-only and need no writer claim.

The writer validates and completes one self-review. A manager handoff occurs
only for a real ownership transfer, conflict, risk trigger, package rule, or
owner request.

There is no fixed writer count. Proceed when branches, paths, and hierarchical
domains are disjoint; stop on an actual collision. Preserve other work and use
the generic claim authorize, transfer, pause, resume, and close transitions when
state changes. Keep a paused branch and its exact checkpoint intact, and retain
the reviewed remote implementation branch until claim close.
Handoffs use package, task reference, branch, exact pushed SHA, and explicit
relinquishment. They do not require a person's or account's identity.

For protected data, identity, privacy, authorization, migration, deletion,
publication, consequential AI, shared infrastructure, or materially revised
visual direction, follow the named package and specialist authority. ChatGPT
creates materially revised production-intent visual authority; Claude
implements the accepted authority.

Azure DevOps is repository authority. Never push directly to `main`. A merge
does not deploy: production deployment is manual-only and requires an exact
main SHA plus Pete's explicit authorization reference. Never stage secrets,
credentials, `.env`, or `.claude/launch.json`.
