# PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-001 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed baseline or test bytes.

## Truth recorded

- Deployed release: `de34c238cb406a6b8c5d4c08`.
- Run: `qa-20260830-01a04348`, cutoff `2026-08-30T10:57:34Z`.
- The one sealed broker invocation exited 2 with structural result `refused`
  and reason code `production_oidc_authority_mismatch`. No retry occurred.
- The refusal preceded MSAL or system-browser authentication, Graph calls or
  mutations, synthetic identity creation, SQL mappings, Workshop items, and
  private-data work. The authenticated Workshop F/G proof therefore remains
  `pending` / `not_done`.
- The temporary User Administrator assignment was removed and verified absent;
  Global Administrator remained. Dedicated no-secret public client
  `peerslate-synthetic-qa-graph-operator`
  (`d28e3e11-8cfa-465c-bc77-1811caf902b5`) was deleted from active
  registrations, permanently deleted from Deleted applications, and verified
  absent in both.
- The disposable pinned MSAL runtime was moved to Trash, no
  `peerslate-sealed` browser temporary roots remained, and no PAT was used.
  No secret, token, subject, or private content is retained in this record.

## Refusal diagnosis

A separate read-only diagnostic found that the installed Homebrew Azure CLI's
`webapp auth show` response uses top-level ARM keys including `properties`.
The safe exact query reported `properties.platform.enabled == true` and
`properties.identityProviders.azureActiveDirectory.registration.openIdIssuer`
equal to the fixed production CIAM discovery authority. The broker used the
legacy top-level `enabled` and `issuer` fields, received null for both, and
refused before mutation. This is an Azure CLI output-shape compatibility defect
in the broker; production authentication itself was enabled. This truth package
does not modify the broker.

## Independent review and verification

- Base: `33bf02252df55c6e81f699b2b15393519eddf27b`.
- Reviewed candidate: `fe369cefb197a501def4cb433588b67eaf5d9a63`.
- Reviewer: `agent:/root/sealed_broker_writer/child_runtime_protocol_review`.
- Reviewed at: `2026-08-30T11:27:18Z`.
- Result: Pass; findings: none.

The reviewer verified the exact two-path candidate, clean read preflight,
diff, YAML, the 878-word control-plane limit, Gitleaks, exact refusal boundary
and cleanup fields, and absence of overclaim or sensitive data. Required build
1987 succeeded and was current for PR 767; all PR policies were approved.
Merge preview `7f6ef5b4dd28a31bdbd56d1776e1d09c8008d52c` had exact base and candidate
parents.

Writer validation passed the exact governance regression (1/1), operational
readiness suite (29/29), focused refusal regression (1/1), Python compilation,
YAML parse, `git diff --check`, and the clean task-bound write preflight.

## Boundaries

The repository work performed no deployment, authentication, Graph, browser,
SQL, identity, Workshop, configuration, schema, role, or other production
operation and did not retry the refused attempt. The external cleanup facts are
recorded structurally from the separately authorized operation. A repository
merge does not authorize another live operation.

This post-review tail is limited to this fixed evidence file and its receipt.
The claim remains active until its separately governed close transition merges.
