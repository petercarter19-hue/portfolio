# PS-WORKSHOP-FG-AUTHENTICATED-PROOF-TRUTH-002 evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed with no findings. This tail changes only this evidence file and its
matching receipt; it does not alter the reviewed baseline or test bytes.

## Truth recorded

- Deployed release: `de34c238cb406a6b8c5d4c08`; broker source:
  `295242f7e29c51f9e5a6922396a9ee82e5391231`.
- Final attempt run: `qa-20260830-01a04348b`, cutoff
  `2026-08-30T13:49:50Z`.
- The one sealed broker invocation exited 2 with structural result `refused`
  and reason code `production_oidc_metadata_unavailable`. No retry occurred.
- The refusal preceded MSAL or system-browser authentication, browser runtime,
  Graph calls or mutations, synthetic identity creation, SQL mappings,
  Workshop items, and private-data work. The authenticated Workshop F/G proof
  therefore remains `pending` / `not_done`.
- With mutation never begun, identity, mapping, and item residue was zero. The
  temporary User Administrator assignment was removed and server-refreshed
  absent while Global Administrator remained.
- Replacement no-secret public client
  `4e5fd52b-5c0b-4f7c-8266-f571284a31f1` was deleted from active registrations,
  permanently deleted from Deleted applications, and verified absent in both.
- The disposable pinned MSAL runtime was moved to Trash and no
  `peerslate-sealed` browser temporary roots remained. No secret, token,
  subject, or private content is retained in this structural record.

## Refusal diagnosis

A separate header-only curl diagnosis of the exact production CIAM metadata
endpoint returned HTTP 200 at the same effective URL with no redirect. The
broker's Python 3.14 standard-library `urllib` request instead returned
`URLError` with `SSLCertVerificationError`, SSL reason
`CERTIFICATE_VERIFY_FAILED`, and detail `unable to get local issuer
certificate`. The recorded root cause is a local Python TLS trust-store
refusal, not a Microsoft metadata outage. No metadata body or sensitive value
is retained here.

## Independent review and verification

- Base: `295242f7e29c51f9e5a6922396a9ee82e5391231`.
- Reviewed candidate: `81a7918d41824bf01b720a81c40adb1385bd14d6`.
- Reviewer: `agent:/root/sealed_broker_writer/child_runtime_protocol_review`.
- Reviewed at: `2026-08-30T14:05:28Z`.
- Result: Pass; findings: none.

The reviewer verified the exact two-path remote candidate and PR merge parents,
pending/not-done conclusion, single final exit-2 invocation with no retry,
zero pre-mutation activity, separated curl-versus-Python TLS diagnosis, exact
cleanup, and absence of sensitive material. YAML, diff, focused regression,
secret scan, and the 880-word control-plane limit passed. Required build 2012
succeeded for PR 777 and the exact reviewed candidate.

Writer validation passed the focused truth and control-plane gates (2/2), full
operational-readiness suite (29/29), Python compilation, YAML parse,
`git diff --check`, and the clean task-bound write preflight.

## Boundaries

The repository work performed no new live operation, authentication, Graph,
browser, SQL, identity, Workshop, client, role, deployment, configuration,
schema, or retry. External cleanup and diagnostic facts are recorded
structurally from the separately authorized operation. A repository merge does
not authorize another live operation.

This post-review tail is limited to this fixed evidence file and its receipt.
The claim remains active until its separately governed close transition merges.
