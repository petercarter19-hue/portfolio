# PeerSlate Product Backlog

This registry records approved product concepts that are not fully implemented. Use stable feature IDs and separate specifications for detailed behavior.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Idea | Captured but not evaluated |
| Validated | Direction approved; design or architecture discovery remains |
| Ready | Scope, dependencies, acceptance criteria, and implementation order are approved |
| In Progress | Active design or implementation work |
| Implemented | Released and verified |
| Deferred | Intentionally postponed with rationale |

## Feature registry

| ID | Feature | Status | Priority | Dependencies | Next trigger | Specification |
| --- | --- | --- | --- | --- | --- | --- |
| PS-FEAT-001 | Living Resume Ledger to Career Constellation plus Voice Builder | Validated | Signature | Foundation C; structured career data; evidence provenance; tenant isolation | Approve scrolling architecture and multi-profile data contract | `PS-FEAT-001_LIVING_RESUME_VOICE.md` |

## Backlog rules

- Read this document before beginning a new PeerSlate product feature.
- Every approved concept receives a stable ID.
- Every Ready or In Progress item has acceptance criteria and named dependencies.
- Design decisions belong in the Design Bible; feature behavior belongs in its specification.
- Source code and commits reference stable feature IDs when feature work begins.
- Pete-specific content is demo/fixture data, not product logic.
