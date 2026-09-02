# PS-MYOPP-URL-FETCH-001 — C13 private member URL fetch

This Protected package implements the optional service-level URL-fetch adapter
behind C10's already-shipped import port. It lets a future C8 route hand a
member-supplied link into the same private deterministic sanitize/extract
pipeline used by paste. It does not add a route or UI, and it remains unusable
unless both `PEERSLATE_MY_OPPORTUNITIES_ENABLED` and
`PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` are true. This package does not
set either flag; the URL-fetch flag stays off.

Owner build authority is
`session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/pete-chat-2026-09-01/complete-everything-backend`.
Merge, deployment, schema, configuration, and enablement are separate states.

## Delivered contract

`services/my_opportunities/member_url_fetch_service.py` exposes the no-argument,
I/O-free `create_fetch_adapter()` factory C10 resolves. A call to the returned
adapter:

1. refuses anything except a printable-ASCII `https` URL with no userinfo,
   fragment, or non-443 port;
2. delegates every connection to C2's unchanged `SafeOutboundClient`, which
   revalidates DNS and the complete address set at every hop, pins one validated
   numeric address, denies private/non-global/metadata space, follows at most
   three revalidated redirects, sends only its fixed `Accept` and `User-Agent`
   headers, and enforces the total wall-clock and response-size bounds; production
   system DNS runs in a disposable spawned child bounded by the smaller of the
   per-hop allowance and remaining total deadline, and every child is terminated
   if overdue and reaped before the call returns;
3. uses a stdlib-only TLS transport that connects to the pinned numeric address,
   verifies TLS/SNI against the URL hostname with TLS 1.2 or newer, ignores proxy
   environment variables, follows no redirect itself, reads at most the cap plus
   one byte, and applies an absolute per-hop deadline across connect, handshake,
   headers, and body reads;
4. admits only status 200 with `text/html` or `text/plain`, refuses every
   `Content-Encoding`, and independently sniffs the first 4 KiB for PDF, ZIP,
   ELF, executable, or NUL-bearing binary content;
5. returns C10's `FetchResult` with the wire bytes, submitted/final URL, final
   pinned address, UTC fetch time, and content-free `public` host class.

The transport sends no Cookie, Authorization, proxy authorization, Referer, or
caller headers. The adapter has no logger, cache, retry, provider dependency,
credential input, AI, browser, or module-level network activity. DNS answers and
per-hop responses are held only in per-call recorders and then discarded.

## Pipeline handoff

C2 currently admits only HTML and plain text. Both are handed to C10 as the
pipeline-admitted type `text/plain`; this is intentional. C10 then strict-UTF-8
decodes the original wire bytes and runs its hardened markup tokenizer, which
drops script/style/head/noscript/template/iframe/object/embed content, ignores
attributes, converts block tags to line breaks, escapes the extracted text, and
applies the 20,000 UTF-16-unit output ceiling. The stored
`declared_content_type` is therefore the pipeline-admitted type, not the remote
server header. `byte_count` and `content_hash` still describe the wire bytes.

PDF and DOCX URLs truthfully refuse as `blocked · content_mismatch`; the member
must download and use C10's existing upload path. The C10 isolated PDF/DOCX
parser remains unchanged and unreachable from URL fetch in v1.

## Truthful closed outcomes

Guarded refusals use only C10's already-migrated vocabulary:

| Condition | Result |
|---|---|
| unsupported URL, credentials, fragment, port, non-ASCII/control input | `blocked · scheme_refused` |
| private, loopback, link-local, metadata, CGNAT, ULA, or other non-global address | `blocked · denied_address` |
| unsafe, malformed, missing, or over-budget redirect | `blocked · redirect_refused` |
| wrong/missing type, compression, binary sniff, or non-200 non-source status | `blocked · content_mismatch` |
| per-hop or total deadline | `timeout · fetch_deadline` |
| more than the configured cap | `refused · fetch_too_large` |

Open question 1 is resolved to architecture default A: DNS/TCP/TLS/protocol
failure uses recoverable `source_unreachable`; 401/403/407/429/451 and other
4xx/5xx source refusals use `source_refused`; 404/410 uses `source_not_found`.
These are C13-owned pre-admission `MemberImportServiceError` codes with neutral
member copy offering paste/upload. They create no row or idempotency receipt, so
a later retry re-runs. Adding visible failed-attempt rows would require a separate
additive schema/reason-vocabulary package.

Member-facing copy for `denied_address` must be identical to the unsupported-URL
copy so the UI does not become a useful internal-network oracle. Audit remains
content-free: it receives only C10's closed reason and host-class fields, never a
URL, host, address, query, body, hash, or DNS answer.

## Budget seam for C8

`FetchBudgetPolicy`, `BudgetVerdict`, `FetchBudgetLedger`, and
`InMemoryFetchBudgetLedger` define the route-level seam C8 must call before the
C10 port. Defaults are one concurrent fetch and 50 reservations per UTC day per
member (`MYOPP_URL_FETCH_DAILY_BUDGET_PER_MEMBER`). Verdicts are `allowed`,
`fetch_in_progress`, and `fetch_budget_exhausted` with a retry-after value when
refused. Counters are isolated by server-derived member key.

The adapter itself cannot enforce a per-member budget because C10's
`FetchAdapter.fetch(url)` protocol deliberately receives no identity. C8 must
reserve/release around the import call and also enforce its route rate limit. The
reference ledger is per-process; a durable multi-worker ledger is a C9/PS-OPS
obligation.

## Configurable bounds

- `MYOPP_URL_FETCH_HOP_TIMEOUT_SECONDS`: 5 seconds
- `MYOPP_URL_FETCH_TOTAL_DEADLINE_SECONDS`: 12 seconds
- `MYOPP_URL_FETCH_MAX_BYTES`: 2 MiB
- `MYOPP_URL_FETCH_DAILY_BUDGET_PER_MEMBER`: 50
- redirects: at most 3, fixed by the C2 contract
- port: public HTTPS 443 only

Invalid non-positive settings make the factory unavailable rather than silently
opening an unbounded path. Operational retuning requires evidence; it is not an
enablement grant.

## Tests

`tests/test_my_opportunities_member_url_fetch.py` is recorded/offline P-1 proof.
Its module-level guard makes `socket.getaddrinfo`, `socket.create_connection`,
and `socket.socket.connect` fail if any test accidentally reaches a real network.
Fakes cover admission, every denied address family, mixed DNS, rebinding and
redirect re-resolution, bounded DNS child success/failure/timeout and reap,
fixed headers, address pinning, TLS SNI, streaming cap+1, deadline behavior,
status/content mapping, a deep malformed HTML/entity bomb through the real
pipeline handoff, provenance, cross-member isolation, content-free
audit/exceptions, flag rollback, budget isolation, and structural stops.

Open question 2 is also resolved to its architecture default: C13 removes exactly
the three C10 tests whose only assertion was that this module did not yet exist.
Their C13-era truths now live in `SeamContractTests` and `NoNetworkGuardTests`.
The exact removal proof compares the merged tree with C13's immutable,
main-reachable activation base and checks a fixed diff digest plus current
absence, so it remains valid after squash merge and source-branch deletion. No
C10 service or C2 file changes.

Run:

```bash
python3 -m unittest tests.test_my_opportunities_member_url_fetch -v
python3 -m unittest tests.test_my_opportunities_member_import tests.test_my_opportunities_safe_outbound -v
python3 -m unittest tests.test_my_opportunities_canonical tests.test_my_opportunities_criteria tests.test_my_opportunities_ingestion tests.test_my_opportunities_qualification tests.test_my_opportunities_relationships tests.test_my_opportunities_retrieval -v
python3 -m unittest tests.test_package_registry -v
```

## Hard exclusions

No route, `app.py`, template, JavaScript, CSS, browser, migration, schema,
provider contact, spend, live network acquisition, retry queue, scheduling,
deployment, flag mutation, production/staging operation, identity operation, or
promotion to shared inventory. A `member_import` remains private to its owner and
never produces a shared receipt, listing, version, canonical opportunity, index
document, or cross-member-visible object.

`docs/governance/PACKAGE_REGISTRY.json` was deliberately omitted at activation
because C11 held that exact surface. After C11 closed and released it, C13 added
the path through the governed `extend-surfaces` transition (PR 860, build 2287,
merge `1f455b8e`) and then added exactly one future-finish row. The fresh write
preflight proved the extended current-main claim before that edit.

## Honest limits and enablement prerequisites

1. Merge does not make this usable. C8 must add the route/affordance and wire the
   rate and member-budget controls; both feature flags must then be separately
   enabled.
2. v1 reads HTML/plain text only. PDF/DOCX uses upload; JavaScript-only pages may
   truthfully land empty; non-UTF-8 pages refuse `could_not_decode`.
3. Unreachable/refused/not-found attempts leave no row under default A.
4. The real transport is tested on fake sockets only. No test performs live
   acquisition. The production DNS process mechanism is tested with offline
   child workers; no test resolves a live hostname.
5. The in-memory budget ledger is per-process and is not yet wired by a route.
6. A runtime enablement smoke must verify the App Service CA trust store and
   public HTTPS egress without a proxy, confirm C8 rate/budget wiring, and confirm
   C10's Linux parsing-isolation gate. That smoke is PS-OPS work, not this package.
7. The reduced internal-network oracle still has theoretical DNS/timing
   differences between pre-DNS and post-DNS refusal. Member copy reveals no class;
   the content-free audit does retain the denied family class.
8. C10's existing erasure-path and per-process unknown-outcome-lock limitations
   remain unchanged.

Rollback after any later enablement is configuration-only: turn
`PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` off. C10 refuses the next call as
recoverable `url_fetch_unavailable · fetch_flag_off` before inspecting the URL or
touching DNS. Removing or breaking the adapter factory yields the same closed
`adapter_absent` behavior.
