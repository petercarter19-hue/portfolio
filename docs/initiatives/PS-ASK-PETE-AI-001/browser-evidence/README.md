# Local browser verification evidence

These files are local implementation evidence for `PS-ASK-PETE-AI-001`,
rendered on 2026-08-07. They are not production, deployment, provider, or
live-service evidence.

## Current deterministic evidence set

Run the package-local harness from the repository root or a linked `.wt`
worktree. This resolves the worktree-local project interpreter when it exists,
then the configured primary-checkout interpreter, before falling back to a
`python` command on `PATH`:

```powershell
$worktreeContainer = Split-Path -Parent $PWD.Path
$primaryCheckout = Split-Path -Parent $worktreeContainer
$pythonCandidates = @(
    (Join-Path $PWD.Path "venv\Scripts\python.exe"),
    (Join-Path $primaryCheckout "venv\Scripts\python.exe")
)
$python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) { $python = (Get-Command python -ErrorAction Stop).Source }
& $python tests\ask_pete\run_recruiter_evidence_browser.py
```

The harness starts one temporary, flag-gated localhost Flask process and closes
it in all cases. It intercepts only `POST /api/chat` with deliberately
synthetic, schema-valid `ask-pete-public-answer.v1` responses. It never calls
an AI provider, production endpoint, private data source, or persistent store.

A passing run creates exactly these six current captures:

- `master-answer.png` - 1536 x 1024 recruiter brief in the answer-first wide
  rail.
- `source-open.png` - exact source navigation, selected evidence marker, and
  focus on the corresponding resume record.
- `contextual-mbse.png` - Skills -> MBSE context with an editable, unsubmitted
  prefilled question.
- `narrow-side-sheet.png` - 1435 x 1096 non-modal side sheet.
- `mobile-bottom-sheet.png` - 390 x 844 mobile bottom sheet.
- `critical-states.png` - a clearly labelled seven-state, test-only evidence
  board: Loading, Partially supported, Not established, Needs clarification,
  Temporarily unavailable, Human handoff, and Source focus. Each tile copies
  an asserted runtime treatment; it is not one simultaneous production
  interface.

The harness also asserts generated answer-heading ownership, compact citation
expansion, 44 px interaction targets, stale-marker cleanup, exact Show All
mapping without broad Skills/Credentials highlights, returned-context
validation, source-target visibility below the sticky header, focus restoration,
mobile source navigation that closes the sheet without obscuring the focused
target, and the actual wide-rail loading and slow feedback text, live-region
semantics, and visible geometry within the one-screen rail before it creates
any test-only critical-state material.

Its response matrix covers `429` wait, `502`/malformed/unverifiable, network,
structured-unavailable, validation, and timeout recovery states; each retains
resume, PDF, and direct-contact paths. It separately proves stale-response
suppression and the slow/cancel lifecycle with controlled in-page fetch and
timer overrides. Those checks are deterministic state waits rather than
retry-based assertions.

The evidence demonstrates the local visual and interaction contract only. It
does not represent a live provider answer, a private-message delivery, or a
production release check.
