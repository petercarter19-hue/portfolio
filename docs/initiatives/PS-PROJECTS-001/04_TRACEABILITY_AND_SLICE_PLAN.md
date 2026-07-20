# PS-PROJECTS-001 - Traceability and slice plan

## Product chain

| Member need | Requirement | Architecture allocation | First evidence |
| --- | --- | --- | --- |
| Keep a real endeavor together over time | PS-PROJ-FR-001, FR-003 | Project aggregate, Slate entity registration, Project query service | Two owners create and independently retrieve Projects |
| Connect updates without rewriting them | PS-PROJ-FR-002, FR-005; DATA-003 | Existing Moment versions and Placement service | Exact-version link/unlink and no-text-copy tests |
| Understand contribution and movement | PS-PROJ-FR-003, FR-006; UX-001 | Owner-authorized Project Ledger read model | Long/short/empty Project usability tasks |
| Keep control of status and history | PS-PROJ-FR-004; DATA-004; NFR-001 | Lifecycle state graph, row version, transactions | Stale-write, transition, archive/restore/delete tests |
| Reuse Project context safely | PS-PROJ-FR-009; DATA-002 | Projection adapters referencing canonical records | Later connected-view integration tests |
| Choose what others see | PS-PROJ-FR-007, FR-008; SEC-004 | Separate projection revision, audience preview, publication service | Later preview-versus-real-viewer parity tests |
| Receive help without losing authority | PS-PROJ-AI-001 through AI-004 | Authorized proposal service plus deterministic commands | AI-offline and no-auto-change negative tests |
| Use Projects accessibly | PS-PROJ-UX-002 through UX-005 | Semantic ledger, responsive composition, accessible controls | Keyboard, screen reader, touch, zoom, reduced-motion evidence |

## Sequence

### Slice 0 - Direction registration - this package

- Adopt Bible and Roadmap direction.
- Register `PS-PROJECTS-001` as planned, not active.
- Record requirements, experience direction, architecture, gates, and honest
  current-production boundary.
- Make no runtime or schema change.

### Slice 1 - Product and visual authority

- Choose the first primary member scenario and Project types.
- Validate Project versus Work versus Slate Board boundaries.
- Create the full Project Workspace state set.
- Select one exact production-intent visual authority.
- Obtain Pete and designated-manager V0/V1 approval.

### Slice 2 - Project foundation

- Implement canonical private Project aggregate and Slate entity registration.
- Add owner-authorized create/list/detail/update/lifecycle service contracts.
- Prove migration/rollback, two-owner isolation, concurrency, data rights, and
  privacy-safe telemetry.
- Keep UI minimal only if the separately approved visual package authorizes it;
  no hidden or internal-preview exception is assumed.

### Slice 3 - Project Workspace and Moment links

- Implement the accepted Project Ledger.
- Reuse Placement to link/unlink confirmed Moment versions.
- Render long/empty/restricted/deleted-source histories truthfully.
- Complete desktop/mobile/accessibility/visual comparison and owner acceptance.
- Release and verify the authenticated owner product.

### Slice 4 - Connected reuse

- Add Project context to Work first through canonical references.
- Authorize Story, Resume, Studio/Moment Lab, Replay, and export integrations as
  separate bounded consumers.
- Each consumer keeps its own purpose-specific draft and approval boundary.

### Slice 5 - Project Projection

- Define projection curation, exact audience preview, revision pinning,
  publication, revocation, correction/deletion propagation, and public route.
- Select a visual authority for the audience-facing case-study experience.
- After the real projection is accepted and live, assess and implement any
  dedicated homepage Projects section through the parity contract.

### Slice 6 - Collaboration, only if later approved

- Define collaborator roles, invites, grants, co-edit conflicts, removal,
  attribution, moderation, notification, and revocation.
- Do not infer this slice from current Connections or public Project ideas.

## Dependencies

| Dependency | Required state before Slice 2/3 |
| --- | --- |
| Identity / owner isolation | Released and preserved |
| Capture lifecycle | Released and preserved |
| Canonical Moment | Released and preserved |
| Placement reference | Released and reused for Moment-to-Project |
| Owner shell / viewer boundary | Authenticated route and context approved for the slice |
| Visual integrity | Exact Project authority and complete state evidence accepted |
| Journal | Not a blocker; UI remains on hold unless separately restarted |
| Capture Media | Not required for text/Moment-first Project slice; media links remain separately gated |
| Interview Studio | Active lane must not be interrupted; later consumer only |

## Roadmap placement

Projects sit in Phase 10 beside Work and connected views. The private owner
foundation can begin only when the next package gate chooses it and the owner
shell/route boundary is ready. Public Project Projections remain downstream of
the private product and broader public visual convergence rules.

This direction does not move Projects ahead of the active Interview Studio or
Capture Media lanes and does not restart Journal.
