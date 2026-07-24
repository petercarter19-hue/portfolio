# ChatGPT Codex — Session Startup Prompt for PeerSlate

Paste everything below the line into Codex at the start of a session.

This file is a launcher, not an authority. It never overrides `START_HERE.md`,
`docs/governance/CURRENT_BASELINE.yaml`, the current Bible and Roadmap, or
`docs/AI_WORKFLOW.md`. When this file disagrees with any of those, they win and
the conflict should be reported.

---

You are working on **PeerSlate**, a reusable multi-user product built as a Python
and Flask web application. It is not a single person's personal website. Pete
Carter's profile is fixture content used to demonstrate the product; it is never
product logic. Do not hardcode one person, profile, career, tenant, or story
into shared behavior.

## Before you do anything

Open and follow **`START_HERE.md`** in the repository root. It is the mandatory
pre-work gate for every session. In order, it requires you to:

1. synchronize from the authoritative remote and inspect the checkout;
2. read `docs/AI_WORKFLOW.md`, `docs/governance/CURRENT_BASELINE.yaml`,
   `docs/governance/CURRENT_STATE.md`, `docs/governance/ACTIVE_INITIATIVES.md`,
   and the Bible and Roadmap versions named by the baseline;
3. read `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md` and
   `docs/governance/OWNER_STORY_COMPOSITION_STANDARD.md`; and
4. confirm the package, designated session manager, branch owner, reserved
   files, and entry gate before writing.

`docs/governance/DOCUMENT_CONTROL.md` decides precedence when an older document
conflicts with the current Bible or Roadmap. Do not infer the current version
from memory, from this file, or from a document's own title — read the baseline.

Stop and report rather than guess when authority, ownership, scope, or the
current document version is unclear.

## Environment — do not assume a machine

Pete works from more than one computer, and agent sessions also run in cloud
containers. **Never hardcode an absolute path.** Determine the repository root
at the start of the session and work relative to it.

```bash
pwd
git rev-parse --show-toplevel
```

A Python virtual environment is expected but is **not** in version control, so a
fresh clone or a second computer will not have one. Creating a venv on a machine
that lacks one is correct and expected:

```bash
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows PowerShell
pip install -r requirements.txt
```

If a venv already exists, activate it rather than recreating it. The shell
prompt should show `(venv)` before you run the app or the tests.

`.env` is also excluded from version control and must exist locally with
`ANTHROPIC_API_KEY` set, or `app.py` raises a `RuntimeError` on import. Use
`.env.example` as the template. **Never display, copy, commit, or ask for the
contents of `.env`.**

Run the app and the tests from the repository root:

```bash
python app.py
python -m pytest tests/ -q
```

## Git rules — these are non-negotiable

`docs/AI_WORKFLOW.md` is the controlling authority. The rules that matter most:

- **Never commit or push directly to `main`.** Not on any remote, ever.
- Start each task from current `origin/main` on a short-lived branch named
  `work/YYYY-MM-DD-short-task-name`.
- One branch has exactly one active writer. Do not continue another agent's
  branch without an explicit handoff naming the branch and the exact full SHA.
- Merge through an **Azure DevOps pull request using squash merge**, then delete
  the task branch. Azure Pipelines is the only production deployment path.
- GitHub is a backup mirror and an inbox for cloud-agent branches. It is never a
  merge target or a deployment path. GitHub Actions deployment is intentionally
  disabled; do not enable it.
- Verify which remote you are on before pushing. In a local clone `origin` is
  Azure DevOps; in a cloud agent session `origin` may be GitHub. Check, do not
  assume:

  ```bash
  git remote -v
  ```

- Stage specific paths and inspect the staged patch before committing. Never
  commit `.env`, `venv/`, credentials, publish profiles, or machine-local
  configuration such as `.claude/launch.json`.
- Preserve unrelated and unfinished work. Never discard it to make a checkout
  look clean.
- Never run a destructive Git operation — `reset --hard`, `clean -fd`,
  `branch -D`, force-push, history rewrite — without a verified recovery
  reference and Pete's explicit confirmation.

## Product invariants that apply to every change

- User content is private by default. Identity and ownership are server-derived,
  and authorization is checked before protected data is returned or changed.
- Canonical user truth, source evidence, AI proposals, and derived projections
  are different data classes. Do not silently collapse one into another.
- AI proposes; people decide. AI output must never silently save, publish, send,
  delete, apply, or become canonical truth.
- The core experience must remain understandable and useful when AI is
  unavailable.
- Never present fixture, seeded, demo, locally inferred, or flag-disabled
  behavior as verified live behavior.
- Meet WCAG 2.2 AA: keyboard use, visible focus, semantic structure, contrast,
  motion preferences, and responsive behavior.

## Security

- Never commit secrets, and never place them in HTML, CSS, or JavaScript.
- Never discuss classified information, internal program names, or proprietary
  employer details.
- Treat user-facing copy as a truth surface: do not claim a capability is live,
  stored, transmitted, or private unless the code actually does that.

## Working style

- Explain what you are doing and why, not just the command.
- Comment non-obvious code so it stays readable later.
- Ask before creating new files, adding dependencies, or widening scope.
- Report failures honestly. A merge is not a deployment, and a passing test is
  not production verification.
- Close out material work with
  `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md`, reporting base and
  final SHAs, changed files, tests with results, pipeline and production status,
  and anything deferred.
