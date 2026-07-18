# PS-PLACEMENT-001 — Security and Privacy Contract

## Authorization before retrieval

- Every procedure starts from the server-derived authenticated user key and resolves the owner profile inside SQL.
- Never accept `owner_profile_id`, user ID, or tenant identity from a browser/client payload.
- Verify ownership of the Moment, exact Moment version, placement, and target entity before returning protected metadata or performing a write.
- Cross-owner, absent, and inaccessible references fail closed without disclosing whether another member’s key exists.

## Private reference, not exposure

- A placement is private system metadata.
- It grants no viewing permission and changes no audience.
- It creates no access grant, publication record, public URL, feed item, profile item, or browser-local copy.
- A later consumer must independently authorize both the viewer and the projection.

## Content minimization

The placement table, procedure parameters/results, service logs, request fields, audit events, tests, and completion evidence must contain no:

- raw Capture body or correction text;
- Moment title, narrative, why-it-matters, or source body;
- target content or purpose-specific display wording;
- prompt, completion, embedding, generated answer, or AI interpretation;
- publication snapshot or audience payload.

Use opaque keys and bounded lifecycle metadata. Synthetic tests may use obvious sentinel strings solely to prove they never persist outside the canonical source tables; do not print any real member content.

## Explicit action and lifecycle

- Moment confirmation never creates a placement.
- Create/reactivate and remove are separate explicit owner actions.
- No AI or background job may invoke placement procedures in this package.
- Removal is placement-only. It never deletes or edits the Moment, source, target, or another reference.
- Reactivation requires the same current eligibility and concurrency checks as first creation.

## Destination eligibility

At placement time, the target must be owned by the same member and be active, approved, private, unpublished, and not deleted. This deliberately prevents PS-PLACEMENT-001 from becoming a hidden publication shortcut.

If the target later changes state, list results may report its current lifecycle metadata but must not expose its content. The placement does not force the target back to an earlier state.

## Failure and logging

- Use stable privacy-safe outcomes such as `created`, `reactivated`, `existing`, `removed`, `stale`, `not_found`, `not_confirmed`, and `target_unavailable`.
- Do not distinguish cross-owner existence from absence in client-visible behavior.
- Logs and audit metadata contain event name, opaque keys, version number, state, and timestamps only.
- Expected negative tests may log storage-unavailable messages but must not produce a false success event.

## Security stop conditions

Stop and return to ChatGPT Work if implementation would require:

- copying canonical or source text into a placement/destination;
- weakening tenant-composite integrity or target eligibility;
- changing authentication or accepting owner identity from the client;
- creating publication/access grants or downstream content;
- reading a protected Moment before authorization; or
- altering Capture/Moment deletion behavior beyond the approved tombstone contract.
