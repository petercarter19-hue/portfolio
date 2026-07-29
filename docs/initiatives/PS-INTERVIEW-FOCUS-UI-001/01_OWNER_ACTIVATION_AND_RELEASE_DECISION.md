# Owner Activation and Release Decision

Date: 2026-07-28

## Accepted direction

Pete approved the supplied Interview Studio mockups and activated implementation.
V3 is the controlling all-modes authority. V2 remains valid supplemental visual
evidence. The white, deep-navy, cobalt, and teal direction is retained; beige,
ivory, and cream are not fallback directions.

## Binding correction

Pete rejected the pictured empty composer heights. Initial answer, transcript, and
improved-draft boxes must be about half as tall, remain readable, and expand
automatically when their content needs more room. Content must never extend beyond
its field or be clipped by fixed geometry.

This correction controls corresponding dimensions in both supplied packages.

## Narrow AI follow-up adjudication

The approved V3 contract requires follow-up output to retain the selected evidence
basis. The released frontend instead forced all follow-ups to `member_history`,
which could silently change a `best_practice` or `compare` result's provenance.
This initiative may correct that mismatch by reusing the currently selected,
already-supported `mode` value on follow-up requests. The API endpoint, payload
schema and fields, accepted enum values, signed context, backend implementation,
prompts, rubrics, provider/model configuration, and response contract remain
unchanged.

## Release authorization

Pete later gave explicit owner authorization to complete, merge, and deploy the
approved implementation tonight while he sleeps, with live touch-ups permitted
afterward. This instruction supersedes the handoff manifest's earlier `merge: false`
and `deploy: false` release gate. It does not broaden product scope beyond the
approved UI reorganization or waive validation, review, exact-SHA, rollback, or live
verification requirements.

## Backup requirement

Before merge, create and verify an Azure-hosted rollback pointer at the exact
pre-change main SHA:

- branch:
  `backup/2026-07-28-pre-interview-focus-ui-001-a85ffbc9`
- verified remote SHA:
  `a85ffbc93a1def86f99db66df26702a59aff4cbc`

The immutable Git history, retained source packages, task branch, PR, merge commit,
and production pipeline evidence are all part of the recovery record. No existing
branch, worktree, stash, artifact, or Claude reference may be deleted.

## Image-generation boundary

Pete requires any genuinely missing or materially changed visual authority to be
created through ChatGPT image generation. No new bitmap is currently needed: V3,
V2, written state contracts, and this compact-height correction cover the bounded
work. If that changes, the affected state pauses for generated visual authority.
