# PS-VOICE-CAPTURE-MANAGER-001 - Voice Capture Activation

## Assignment

- Manager and writer: ChatGPT Work
- Owner/reviewer: Pete
- Branch: `work/2026-07-18-voice-capture-manager-001`
- Domain: governance and orchestration only

## Outcome

Record Pete's decision to make private Voice Capture the next backend package and prepare a bounded `PS-VOICE-001` implementation contract for ChatGPT Codex.

## Scope

- Activate `PS-VOICE-001` in the current authority records.
- Define the member experience, architecture, privacy, infrastructure, migration, test, rollback, release, and handoff gates.
- Reserve the exact owner-Capture files Codex may change.
- Keep the public Interview Studio design lane independent.

## Out of scope

- No application route, template, JavaScript, stylesheet, service, migration, dependency, Azure resource, or production behavior is changed by this manager package.
- No Voice Capture implementation begins on this branch.
- No Moment, Placement, Journal, public page, theme, navigation, or authentication behavior changes.

## Exit gate

- Governance and Site Rules guardrails pass.
- The complete configured test suite passes.
- Azure PR squash-merges from the exact manager commit.
- The matching Azure Build and Deploy stages pass.
- The resulting current `origin/main` is the required base for the Codex package.
