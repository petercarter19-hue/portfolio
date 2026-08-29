# PS-SYNTHETIC-SEALED-GRAPH-DELETION-CORRECTION-001 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed implementation candidate.

## Reviewed candidate and reconciliation

- Original correction base: f4b8bb023063e8b1e14f7c2443cc253dc9afb016
- Current origin/main at tail creation: c2b03489f6b399123fff416ff9a2bba9a482f4f4
- Reconciliation merge: f90084de7a9489ef82d582c2f4b82ccfdbe5eba9
  - parents: 3750c3a86579c2f194f3672d9be0bfc101cbd29e and
    f0a919d05db7983329fc1eff1fdf00c76540c2ec
- Reviewed candidate: 9460179df08e34167adac5dfd9c22cb00232b82b
- Reviewer: agent:/root/graph_deletion_reviewer
- Reviewed at: 2026-08-29T17:44:36Z
- Result: Pass; findings: none

The reconciliation preserved the accepted local hardening while removing the
untrusted correction-package receipt, evidence, and completion-report
artifacts. It retained only claimed, source-truth routing, registry, runbook,
broker, and focused-test surfaces. Current-main drift was disjoint.

The first fresh review of f90084de7a9489ef82d582c2f4b82ccfdbe5eba9 failed
with one High finding: the broad Workshop metadata locator sees five rows, but
the former exact-description guard required one. Candidate 9460179d corrects
that guard and receives the independent Pass recorded above; no review was
transferred between changed bytes.

## Corrected scope and validation

Candidate 9460179d changes only:

- qa/synthetic_member/sealed_credential_broker/__init__.py
- tests/synthetic_member_qa/test_sealed_credential_broker_attended.py
- tests/synthetic_member_qa/test_sealed_workshop_evaluator.py

The named production evaluator now processes the actual five-row metadata
collection, selects exactly one row with direct dt value Downstream use,
and requires exactly one direct same-row dd value Not used elsewhere. It
retains same-task canonical/document-owner checks and refuses nested-only,
split-row, duplicate-row, hostile-owner, port, userinfo, and redirect-race
fixtures. The evaluator regression executes the exact production JavaScript
against a generic fake-only DOM fixture derived from the template; the fixture
supplies data and does not replace the production guard.

Writer validation passed:

- focused broker, attended, and evaluator tests: 26/26;
- prior Graph-deletion tests: 13/13;
- complete synthetic-member discovery: 95/95;
- package registry, governance pointers, and delivery-preflight tests: 149/149;
- Python AST and JSON parsing, git diff --check, and no-bytecode checks.

The governed write preflight passed with the exact writer task reference.

## Inadmissible history and boundaries

PRs 721 and 722 were abandoned. The overlapping remote input and the
unproven reviewer agent:/root/sealed_graph_exact_sha_reviewer_r2, including
its correction-package receipt and evidence, were inadmissible and are not
review evidence for this candidate.

No deployment, qualified runtime proof, live browser, Azure, Graph, SQL,
identity, retirement, deletion, schema, configuration, role, licensing,
billing, or other production operation occurred. Repository merge does not
authorize a live operation.

This post-review tail is limited to the receipt and this fixed evidence file.
It still requires normal PR policy/CI acceptance and merge; the claim remains
active until the separately governed close transition is merged.
