# 06 — Untrusted import and company-context boundary

Two separate questions with one shared discipline: everything that arrives
from outside — member-supplied URL, redirect target, remote address, header,
document, HTML body, provider payload — is untrusted input.

**Ownership:** the permanent private paste/upload path is implemented by the
unconditional child **C10 — `PS-MYOPP-MEMBER-IMPORT-001`** (doc 14): storage,
sanitization/extraction, provenance, authorization, export/delete, dual
retention, API/UI seams, schema/rollback, and negative tests. It does not
depend on URL fetching in any way.

**Standing product decision (open):** whether My Opportunities may fetch
member-supplied remote URLs *at all* is an owner decision not made here
(doc 15 §3). Fetching is the **distinct, Pete-gated future child C13 —
`PS-MYOPP-URL-FETCH-001`** (doc 14): its own proposed claim after C10
closes, delivered as a **service-only late integration** — C10 ships a
prebuilt disabled **service-level** fetch port inside
`member_import_service.py` (returning the truthful `url_fetch_unavailable`
outcome; C10 owns no HTTP route), C8 later owns and registers the
`POST /my-opportunities/import/url` route with its config/rate-limit rows
and the flag-gated URL affordance (the route exists from C8 onward and
surfaces the refusal with paste/upload offered), and C13 supplies only the
adapter module behind the fixed seam, gated by
`PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` alongside the parent surface
flag (both proposed keys, not deployed truth); optional and skippable
forever, reopening no closed ownership. This section defines the boundary
that child must satisfy, and the always-available non-fetch behavior. It is
deliberately distinct from Opportunity Slate's existing public-link intake
(`opportunity_slate.import_source`, `opportunity_slate_v2.import_source`)
and from the continuation package's extraction diagnosis — P0 changes
neither.

**Site Rules §3 governs every member upload/import:** a privately uploaded
external job description may support private Qualification Alignment, but it
is never published, indexed, recommended, or converted into a listing.
Concretely: member-imported material is stored **only** as the owner-scoped
`member_import` object (doc 02) with its own private pipeline — submit
(paste/upload/fetch-if-ever-enabled) → sanitize → store → member-controlled
use and deletion. It never becomes a shared `source_receipt` or
`source_listing`, never enters the shared connector/ingestion pipeline
(doc 05 §1), never enters any discovery index, never appears in another
member's results, and is excluded from `canonical_opportunity` creation. It
exists only as that member's private source material, readable by exactly
that member's `user_key`.

## 1. Network boundary (SSRF defense), if fetching is ever enabled

- **Schemes**: `https` only. No `http`, `file`, `ftp`, `data`, `gopher`,
  custom schemes, or userinfo (`user:pass@`) URLs.
- **Address validation**: resolve DNS, then validate **every** resolved
  address against the deny set, then connect to the validated address
  (pin the resolved IP for the request — revalidate on every connection, not
  once per hostname, to close DNS-rebinding).
- **Deny set**: loopback (`127.0.0.0/8`, `::1`), RFC1918 (`10/8`,
  `172.16/12`, `192.168/16`), link-local (`169.254.0.0/16`, `fe80::/10`),
  CGNAT (`100.64/10`), unique-local (`fc00::/7`), unspecified/broadcast,
  IPv4-mapped IPv6 forms of any of these, and cloud metadata endpoints
  (`169.254.169.254` and platform equivalents). Deny by address after
  resolution — hostname allowlists are not a defense.
- **Redirects**: budget ≤ 3; each hop re-runs scheme + DNS + address
  validation; cross-scheme downgrade refused.
- **Budgets**: connect/read timeouts; total fetch deadline; response size cap
  enforced while streaming (not after buffering); one concurrent fetch per
  member; per-member daily fetch budget.
- **Content**: `Content-Type` allowlist (HTML, plain text, and the document
  types the intake service supports); declared-vs-sniffed mismatch is a
  refusal; oversized or mislabeled content is a named failure, never a
  partial parse.
- **Request hygiene**: no member cookies or PeerSlate credentials attached;
  fixed identifying User-Agent; no proxy of arbitrary responses back to the
  browser (fetch → sanitize → store → render from storage).

## 2. Parsing and sanitization

- Deterministic fetch/decode/normalize/extract tooling with explicit failure
  states — an LLM is never the extraction authority and must not fabricate
  missing source text (preserved continuation direction).
- HTML is parsed with a hardened parser; scripts/styles/handlers stripped;
  output is text + minimal safe structure. Documents go through the bounded
  document-intake path (v2's `upload_source` size discipline is the
  convention). Rendered source display is sanitized output only, never raw
  bytes.
- Every stage (fetched, decoded, parsed, extracted, empty, partial, blocked,
  timeout, refused) is a distinct recorded outcome; a source record with
  failed extraction shows that truth plus retry — it cannot appear complete
  because the link was retained (the 2026-08-14 lesson, preserved).

## 3. Provenance, retention, authorization

- Import provenance: submitted URL, final URL after redirects, resolved
  address, fetch timestamp, content hash, sanitizer version — recorded on the
  member's private `member_import` record (doc 02).
- Member imports are owner-scoped private records under the member's data
  rights (export/delete). Retention honors **both** drivers (doc 02 §4):
  the member lifecycle — deleted with the member, individually deletable at
  any time — **and** content rights at point of use: any applicable
  source-content obligation (for example a takedown class) is checked when
  the content is used and, where required, satisfied by targeted body removal
  under the doc 02 §4 tombstone discipline. Restricted content is never
  silently kept in use.
- Authorization before everything: the import belongs to the requesting
  member's `user_key`; access is resolved through server-derived identity
  before any read, AI use, or rendering; no cross-member visibility of
  imported material, ever.

## 4. Useful non-fetch and error behavior

Paste-the-text and upload-the-document remain first-class permanent paths
(both Slate implementations already model this). Every fetch failure ends in
a truthful, specific member state — `unsupported URL`, `could not reach`,
`blocked by the source`, `too large`, `could not read the page` — each with
the paste/upload alternative offered inline. No silent retry loops; no
degraded guess.

## 5. Company-context boundary

Company context is a restrained, source-linked decision aid — not a company
intelligence product, rating, or score (rejected directions preserved).

- **Every claim is a `company_context_claim`**: text, class (facts like
  size/industry/locations; officially published statements; licensed data
  classes), exact source reference, `source_policy` reference, `as_of` date,
  limitation label. **No sentiment, culture, reputation, or any company claim
  may appear without permitted source-linked evidence** — rendering walks the
  provenance chain or shows nothing.
- **Absent**: render "No company context available", not filler.
  **Stale**: render with explicit `as_of` age. **Contradictory** (two
  permitted sources disagree): render both with attribution or neither —
  never a silent synthesis; the display rule is fixed at C1 with the provider
  rights. **Provider unavailable**: the opportunity remains fully usable;
  company context degrades independently of search/qualification.
- No member data ever feeds company context. No employer prediction, hiring
  likelihood, or "company fit" derivation exists.
- Permitted source classes (employer sources, official registries/SEC,
  licensed data) and permissible claim types per provider are C1
  owner-decision outputs. The runtime (ingestion, validation, persistence,
  read API, removal) is the decision-gated child **C12 —
  `PS-MYOPP-COMPANY-CONTEXT-001`** (doc 14); the truthful absent state ships
  in C8 independently, so the product is complete and honest without C12.
  Broader company-risk intelligence and a standalone company destination
  remain separate future owner-approved packages, if ever.

## 6. Proof obligations (adversarial, before any live importer)

Offline/integration tests covering: every §1 deny-set family (loopback,
RFC1918, link-local, CGNAT, ULA, metadata, mapped-IPv6); DNS-rebinding
(resolve-then-swap); redirect chains crossing into denied space; scheme and
userinfo refusals; oversized streaming cutoff; mislabeled content; parser
bombs (deeply nested/malformed HTML); sanitizer bypass attempts; empty/
partial extraction truth states; and the §4 fallback paths. These are the
activation gate tests of the C13 fetch child when (and only when) Pete
enables fetching — C1 designs the policy; C13 proves it; the deny-set
validator itself is a reusable shared component candidate.
