# PS-SETTINGS-SCHEMA-STATE-REFRESH-001 review evidence

Routine, self-reviewed: the schema-state record refreshed after the
owner-authorized eight-migration batch, plus the production-tip pin it
necessarily moves.

- Ledger facts from the governed pipeline's own read at the batch's
  final apply (build 2149); registry side from current main, so
  `PS-SETTINGS-EXPORT-010` shows truthfully as pending (`gate: null`).
- The Workshop tip-pin regression moved with a dated rationale; its
  selector property is now tip-relative (stale-proof) and its W4->W3
  guarantee preserved family-scoped. Surface taken by a proper
  extend-surfaces transition (PR 829).

## Process breach, recorded

The writer's own closeout automation merged the implementation PR (827)
while merge preflight was failing "merge requires the package review
receipt": a receipt-tail commit had silently failed after a branch
rebuild, and the chain lacked an exit gate on merge-preflight failure,
so the Azure completion proceeded on CI-green alone. The merged bytes
are exactly the reviewed candidate `bb0ebc51`; the breach is the
receipt-before-merge ORDERING, not review substance. Remediated by this
receipt-tail follow-up, merged before close so the close gate's
receipt-on-main requirement is satisfied honestly rather than waved.
Root cause fixed in the chain template: merge preflight failure now
hard-stops before any PR completion call.

Nothing deployed; no schema, code, or claim-set change beyond the one
generated file and the one regression pin.
