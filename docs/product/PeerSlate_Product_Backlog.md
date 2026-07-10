# PeerSlate Product Backlog

This is the durable registry of approved product concepts that are not yet fully implemented. Detailed feature specifications use stable IDs and separate blueprint files.

## Status Vocabulary

| Status | Meaning |
| --- | --- |
| Idea | Captured but not yet evaluated |
| Validated | Product direction approved; design or architecture discovery remains |
| Ready | Scope, dependencies, acceptance criteria, and implementation order are approved |
| In Progress | Active design or implementation work |
| Implemented | Released and verified |
| Deferred | Intentionally postponed with rationale |

## Feature Registry

| ID | Feature | Status | Priority | Dependencies | Next trigger | Specification |
| --- | --- | --- | --- | --- | --- | --- |
| PS-FEAT-001 | Living Résumé Ledger → Career Constellation + Voice Builder | Validated | Signature | Foundation C; structured career data; evidence provenance; tenant isolation | Approve combined scrolling architecture and dynamic data contract, then prototype six fixture profiles | `PS-FEAT-001_Living_Resume_Voice_Blueprint.md` |

## Backlog Rules

- Every approved concept receives a stable ID.
- Every Ready or In Progress item must have acceptance criteria and named dependencies.
- Design decisions belong in the Design Bible; feature-specific behavior belongs in the linked blueprint.
- Source code and commits should reference the stable feature ID.
- Pete-specific content is demo/fixture data, not product logic.
- A future conversation can resume an item by its ID without reconstructing the idea from memory.
