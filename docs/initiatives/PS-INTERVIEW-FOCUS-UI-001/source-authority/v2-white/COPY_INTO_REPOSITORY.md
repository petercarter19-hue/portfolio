# Copy This Package Into the Repository

## Recommended destination

Copy the entire extracted folder into the controlling PeerSlate repository as:

```text
docs/initiatives/PS-INTERVIEW-FOCUS-UI-001/
```

Do not scatter the PNGs or specification documents across unrelated folders. Keeping the package intact preserves relative paths used by the prompts and manifests.

## Before Codex planning

1. Confirm the controlling repository and branch from the repository's own governance documents. Do not assume GitHub is authoritative if Azure DevOps remains the source of truth.
2. Confirm the package folder contains exactly fourteen files under `visual-authority/`.
3. Confirm `README.md`, `00_CODEX_START_HERE.md`, and `manifest.yaml` open correctly.
4. Commit the initiative package separately only if the repository's documentation process requires it. Do not mix implementation edits into the documentation-import commit.
5. Start with `10_CODEX_ASK_MODE_PROMPT.md`. Do not jump directly to implementation before Codex maps the real route, state, storage, and file architecture.

## Suggested documentation-only commit

```text
docs(interview-studio): add Focus Stage white-authority handoff
```

## What Codex must not do with this package

- Do not copy the static prototype HTML into production.
- Do not replace the current route with the prototype.
- Do not hardcode the illustrative Pete Carter answer, score, or history entries.
- Do not create a new framework because the mockups look componentized.
- Do not treat static dimensions as fixed production heights.
- Do not use the retired beige/ivory/gold visuals from earlier conversation artifacts.
- Do not add a fifteenth product screen. Failure recovery is a runtime state governed by the written contract.

## Attachment-only alternative

When Codex cannot read repository-local initiative files, attach the ZIP and instruct it to extract/read the package in the same order. Repository-local placement is preferred because it produces a durable decision record and lets future reviewers trace the implementation back to the approved authority.
