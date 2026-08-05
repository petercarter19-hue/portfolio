# PS-OPPORTUNITY-SLATE-001 — slice OS-6 completion report

**Slice:** OS-6 — guarded document upload (PDF/DOCX/TXT) and SSRF-guarded
public-link import, signed-in-only.
**Branch:** `work/2026-08-05-oppslate-os6-intake`
**Path:** Protected (shared infrastructure/security) — independent review
required by handoff §16, and received: the review REFUSED the first candidate
with four blocking defects (F1-F4), a coverage hole (F5) that explains why
they shipped, several non-blocking findings, and a visual-materiality
finding. This report is the record of that cycle and its remediation. Not
merged, not deployed, flag default off.

`services/opportunity_source_intake_service.py` cites this report by name for
the 60k/20k reconciliation below; this section is that citation's target.

---

## 1. Reconciling the handoff's "60k units" with the shipped 20,000-unit column

Handoff §11's upload bullet proposes a "hard output cap" of roughly 60,000
units on extracted text. The OS-1 migration's
`CK_opportunity_source_versions_original_length` CHECK constraint — and
`services/opportunity_slate_service.MAX_SOURCE_TEXT_UNITS`, which
`validate_source_text` enforces before any database round trip — cap
`original_text` at exactly 20,000 UTF-16 code units, uniformly across every
capture method, including `pasted`. That constraint predates this slice and
is not something an intake-and-extraction slice may change (a schema change
is a separate Protected path).

Extracting to 60k and then failing the save with `validate_source_text`'s
generic `too_long` field error would have produced a *rejection*, not a
*truncation* — and would have contradicted the failure-truth contract this
slice's own test brief requires ("output-cap truncation labeled truthfully").
`MAX_EXTRACTED_TEXT_UNITS` is therefore defined as
`= MAX_SOURCE_TEXT_UNITS` (20,000): every extraction path (PDF, DOCX, TXT,
imported HTML) truncates cleanly at that boundary — at a UTF-16 code-unit
edge, never splitting a surrogate pair — and reports the fact via a returned
`truncated` flag. The route layer turns a `True` flag into a one-time,
signed, 60-second-lived notice token appended to the post-save redirect
(`?notice=<token>`; see §7 below for why it is a token and not a bare
string), rendered as an honest banner on the next Review Source load and
never persisted anywhere.

## 2. Extraction dependency: `pypdf==6.14.2`, and why it is the only new pin

`pypdf` is added to `requirements.txt` only (not `requirements-sql.txt`):
`tests/test_site_rules.py::DependencyPinTests` requires shared pins between
the two files to *match*, not that every package appear in both, and
`requirements-sql.txt`'s own header says it is "local database-operations
tooling only" — every other web-only dependency in this repository
(`Pillow`, `azure-storage-blob`, `Flask-Limiter`, ...) follows the same
one-file convention.

Pin rationale: `pypdf` is a pure-Python, `py3-none-any` wheel with **zero**
declared dependencies (verified directly: `pip show pypdf` lists no
`Requires`) — no C extension, no compiled binary, nothing that could hit the
"passes-locally/dies-at-boot" failure class the handoff's OS-6 entry names
as this repository's own prior experience. It has no rendering engine and no
JavaScript interpreter, so a call to `page.extract_text()` structurally
cannot execute anything a malicious PDF embeds (`/OpenAction`, `/AA`,
embedded JavaScript names are never touched by this module).

**Outstanding, explicitly flagged dependency**: the handoff's own OS-6 entry
requires validating a new extraction dependency against the Azure App
Service **Python 3.14** runtime before the pin is trusted in production —
this sandbox's Python is 3.13, and no staging App Service exists to verify
3.14 boot behavior. `requirements.txt`'s comment next to the pin states this
explicitly. This is a genuine, unresolved deployment-config dependency, not
an oversight — flagging it here again for the release-path reader.

DOCX needed no new dependency: stdlib `zipfile` + `xml.etree.ElementTree`
only, hardened by refusing any `document.xml`/`[Content_Types].xml` carrying
a `<!DOCTYPE` (closes XXE/billion-laughs without a `defusedxml` pin that
nothing else in this repository uses) and, after the F3 fix below, by
bounding actual decompressed bytes rather than trusting declared sizes.

## 3. No ATS/employer domain allowlist for public-link import

Handoff §11: "v1 may additionally restrict to a supported ATS/employer
domain allowlist ... implementer proposes the list; independent review is
mandatory for this slice regardless." This is explicitly optional
(*"may additionally"*), and no allowlist is implemented: the SSRF contract
(§11's mandatory portion — https-only, public-unicast-only resolution, IP
pinning, redirect re-validation, size/time caps) is enforced regardless of
domain, and a hardcoded list of "acceptable" employer/ATS domains for a
demo-scale portfolio product would be arbitrary and would need constant
maintenance to stay useful. The independent review this slice received
evaluated the full general-import surface rather than a domain-restricted
one; a future decision to add an allowlist remains open and would tighten,
not loosen, what is already enforced.

## 4. `GET .../source/original` — not implemented (real schema gap)

The OS-1 migration's `opportunity_source_versions` table has exactly the
columns the TEXT extraction pipeline needs and no more: `capture_method`
already includes `'uploaded'`/`'imported'` in its CHECK constraint, and
`original_text` / `original_sha256` / `idempotency_key` are all
capture-method-generic and already used by every extraction path in this
slice unchanged. It has **no column** for a blob storage locator, no
original filename, and no original source URL. The established pattern for
retaining a private original in this codebase —
`dbo.capture_media_sources` (PS-CAPTURE-MEDIA-001) — is a *dedicated table*
carrying exactly those fields (`original_blob_name`, `original_content_type`,
`original_byte_length`, `original_sha256_digest`, ...), which this migration
does not have.

Verified directly (not assumed): `services/photo_capture_service.py`'s blob
names are server-generated random hex, matched against a strict regex
(`^photo/v1/[0-9a-f]{2}/[0-9a-f]{32}(?:-preview)?\.(?:jpg|png)$`) and
*stored*, not derived from a sequential row ID — confirming the established
pattern genuinely requires a stored locator column, not something this slice
could reconstruct without a schema change.

`GET .../source/original` is therefore **not implemented**, and no blob is
written for an uploaded file's original bytes. `templates/partials/
opportunity_slate/_review.html` still carries its OS-1-era comment noting
"'Open original' served a retained uploaded file ... upload arrives with
slice OS-6" — that comment remains accurate as a forward pointer to a
still-unbuilt capability, not a broken promise this slice silently walked
back. `tests/test_opportunity_slate_intake.py
::OriginalRouteDeliberatelyUnimplementedTests` locks this decision in as
visible and intentional. Recommended next step: a follow-up additive schema
slice (e.g. `PS-OPPSLATE-004`) adding a `opportunity_source_originals`-shaped
table mirroring `capture_media_sources`, after which the route becomes
buildable against the same private-blob-storage pattern.

## 5. No client-side processing stage rail (named deferral)

Handoff §7 names truthful stage names for upload
("Upload complete → Extracting employer wording → Preparing source review")
and implies a client-rendered rail, matching the existing AI-step stage rail
(`static/js/opportunity-slate.js`'s `setStage` idiom, used for `review_source_
wording`/`interpret_requirements`). Upload and import in this slice are
implemented as a single synchronous request/response/redirect cycle (a plain
HTML form POST, working with JavaScript disabled, per the room's stated
baseline) — a real server-side processing "stage" split (upload received,
then extraction begins, then extraction ends) does not exist as separate
request boundaries the way AI-step polling does, so there is nothing genuine
for a rail to represent between the browser's own "form submitting" UI and
the final redirect. Adding a purely decorative client-side rail for a single
round trip would have been exactly the kind of "invented partial result" §7
itself prohibits elsewhere in this room. This is a named, deliberate scope
cut — not an oversight — made under time constraints during a Protected
security-first slice; a genuine future enhancement (e.g. client-side
`fetch()` + `AbortController` wrapping the same three named phases as
optimistic UI, matching the `set_source` baseline as the no-JS fallback)
remains open.

## 6. ORCHIDv2 gap in the public-unicast classifier — fixed in the third review pass

`services/opportunity_source_intake_service._is_public_unicast` combines
Python's `ipaddress.IPv4Address/IPv6Address.is_global` (which alone
correctly rejects Carrier-Grade NAT space, 100.64.0.0/10 — not covered by
`is_private` — verified directly) with the individually-named
`is_private`/`is_loopback`/`is_link_local`/`is_multicast`/`is_reserved`/
`is_unspecified` checks as defence in depth. Measured directly on this
interpreter (CPython 3.11.15): `2001:20::1` (RFC 7343 ORCHIDv2, a
cryptographic-hash-based, non-traditionally-routed identifier space,
2001:20::/28) is classified `is_global = True` by this Python version and was
not separately excluded by any of the named checks either, so it passed this
guard prior to this fix.

**This is now fixed** (third review pass, §7.6 below): rather than
special-casing ORCHIDv2 alone, the whole IANA "IETF Protocol Assignments"
block that contains it, `2001::/23`, is excluded via one added named check
(`ip in _IETF_PROTOCOL_ASSIGNMENTS_V6`) beside the pre-existing named
properties. The function's docstring previously described this as an
accepted residual gap; it has been rewritten to describe the actual current
guard instead of continuing to describe a gap that no longer exists — the
independent reviewer's own phrasing for why this mattered: stale documentation
here would otherwise go on "claiming a guard that wasn't there."

## 7. Independent review cycle — blocking defects, fixes, and proof

The first candidate (`7a0cd7e`) was reviewed and **refused** with four
blocking defects, all reproduced with measurements, plus a coverage hole
that explains why the test suite that shipped with it did not catch them,
plus a visual-materiality finding. Every one is fixed in this branch; every
fix has a red→green test.

### F1 — `connection.sock` is `None` after `getresponse()` on `Connection:
close` responses

> **Superseded, §11.1.** The narrower fix described here (capture the socket
> reference once, before `getresponse()`) was itself found, on re-review, to
> still crash on one specific response shape (`Content-Length` +
> `Connection: close` — R1). It has been replaced, not patched again, by the
> deadline-wrapper redesign in §11.1/§11.2, which removes every manual
> `settimeout()` call from `guarded_fetch_html` entirely. The mechanism
> description below is kept as the historical record of the defect this fix
> originally targeted, not as a description of the code as it exists today.

**Mechanism.** `http.client.HTTPConnection.getresponse()` calls
`self.close()` (nulling `self.sock`) whenever the response `will_close` —
which every request this module sends always is, because it sends its own
`Connection: close` header. `guarded_fetch_html`'s body-read loop called
`connection.sock.settimeout(remaining)` on every iteration, which raised an
uncaught `AttributeError` for exactly this (common) response shape, turning
a guarded-and-refused fetch into a raw, undignified 500 — and, because the
crash happened before the size/deadline checks in that loop ever ran, those
checks became dead code for every `Connection: close` response.

**Reproduction** (before the fix, against a real local self-signed-cert TLS
server built for this investigation): `AttributeError: 'NoneType' object has
no attribute 'settimeout'`, raised deterministically on the very next line
after a normal 200 response with `Connection: close` was received and its
headers parsed.

**Fix.** The socket reference used for every `settimeout()` call in
`guarded_fetch_html` is now captured exactly once, immediately after
`connection.connect()` and *before* `connection.getresponse()` — never
re-read from `connection.sock` afterward. `AttributeError` is also now
caught alongside the existing `OSError`/`ssl.SSLError`/
`http.client.HTTPException` family as defence in depth.

**Proof (at the time, second pass).** `tests/test_opportunity_slate_intake_tls.py
::RealTLSFetchTests::test_connection_close_response_is_read_without_crashing`
and `::test_eof_delimited_response_is_read_to_completion` (the same
underlying `will_close` mechanism, triggered without an explicit header)
against a real local TLS server. Verified red→green directly: `git stash`
of only `services/opportunity_source_intake_service.py` back to the
pre-fix candidate, full integration suite run (all 9 tests fail — the
`ssl_context` test seam itself is part of the fix, so the pre-fix API
surface does not even accept the call shape these tests need), `git stash
pop` to restore the fix, suite green again (9/9). These two tests did not
happen to cover the `Content-Length` + `Connection: close` shape that R1
found still crashed (§11.1); both have since been superseded by, and their
coverage subsumed into, the five-shape matrix in §11.1.

### F2 — the total wall-clock deadline is not enforced *within* a single
`response.read()` call (chunked/EOF-delimited slowloris)

> **Superseded, §11.2.** The per-call `settimeout()`/`IMPORT_STALL_TIMEOUT_
> SECONDS` mechanism described below was found, on re-review, to still leave
> `getresponse()`'s internal status-line/header reads unbounded (R2 — this
> loop never ran during that phase at all). It has been replaced by the
> `_DeadlineSSLSocket` wrapper in §11.2, which covers the status line,
> headers, and body uniformly; `IMPORT_STALL_TIMEOUT_SECONDS` no longer
> exists in the code. `response.read1(n)` (not `response.read(n)`) is still
> the call used for the body — that part of this fix stands — but the
> deadline enforcement it describes below is not how the current code works.

**Mechanism.** `io.BufferedReader.readinto()` — what `http.client.
HTTPResponse.read(n)` calls internally for a non-chunked body — issues
*multiple* underlying raw reads to fill the requested `n` bytes, looping
until it succeeds or hits EOF. A server that sends one byte every fraction
of a second, each individual `recv()` comfortably inside the socket's
per-call timeout, keeps that inner loop satisfied indefinitely: the outer
per-chunk deadline check in `guarded_fetch_html`'s loop never runs again,
because the single `response.read(IMPORT_READ_CHUNK_BYTES)` call it was
waiting on never returns.

**Reproduction.** A `response.read(65536)` call against a real local TLS
server dribbling one byte every 0.05s, with the socket's own timeout set to
10s, did not return within a 120-second hard test timeout (the harness
process was killed at the 120s mark, mid-call) — the observable shape of the
reviewer's "chunked/EOF bodies loop internally in http.client ... server
dribbling bytes keeps each `recv()` inside the socket timeout while
`read()` never returns" finding.

**Fix.** The body-read loop now calls `response.read1(n)` instead of
`response.read(n)` — `read1()` is documented, and verified directly against
a real server (both a `Content-Length` body and a `Transfer-Encoding:
chunked` one — `read1()` correctly decodes chunk framing, it is not a
raw-bytes bypass), to issue **at most one** underlying raw read per call, so
every call is bounded by whatever socket timeout is in force at that
moment. That per-call timeout is now recomputed and set immediately before
every `read1()` call, capped at the smaller of a fixed
`IMPORT_STALL_TIMEOUT_SECONDS` (5s default) and the remaining overall
deadline — never the whole remaining budget handed to one call — so a
server that goes silent partway through the body is caught within a bounded
window, not only once the entire request deadline elapses.

**Proof.** `tests/test_opportunity_slate_intake_tls.py::RealTLSFetchTests
::test_chunked_slowloris_aborts_within_the_deadline`: a real server sending
`Transfer-Encoding: chunked` bytes every 0.5s (a schedule that would take
~100s to finish on its own) against a 2-second total deadline; the fetch
aborts with `code="timeout"` in under 5 seconds (deadline + margin), not
anywhere near the ~100s the slow schedule would otherwise take, and not the
"aborted only once the whole HTTP request timed out" shape the bug produced.
Red→green confirmed via the same stash/pop cycle as F1 (same file).

### F3 — DOCX zip guards trusted attacker-declared central-directory sizes

**Mechanism.** `_safe_zip_member_names`'s size and compression-ratio checks
read `ZipInfo.file_size`/`compress_size` — both come straight from the
archive's own central directory, which the archive's bytes fully control.
The actual reads, `archive.read("[Content_Types].xml")` and
`archive.read("word/document.xml")`, were unbounded — `ZipExtFile.read()`
with no size argument decompresses the entire member regardless of what the
central directory claims about it.

**Reproduction and an honest correction of the exact mechanism.**
Investigating this empirically (documented in
`tests/test_opportunity_slate_intake.py
::test_a_docx_zip_bomb_style_entry_is_rejected_before_decompression`'s own
docstring, not left implicit) surfaced that CPython's `zipfile.ZipExtFile`
*also* uses the central directory's declared `file_size` as its own
internal output-truncation bound (`self._left = zipinfo.file_size`) and
raises `BadZipFile("Bad CRC-32 ...")` once truncated output stops matching
the stored (honest, untouched) CRC — meaning a pure "declare the size small"
lie is *also* caught by the stdlib itself, for this exact archive shape,
before this module's own fix even has to act. That is a genuine, verified
finding and is recorded rather than glossed over. It does not weaken the
case for the fix below: this module must not depend on an interpreter
implementation detail (`ZipExtFile`'s internal truncation-then-CRC-check
behavior, unlikely to be guaranteed API, and not shared by e.g. `ZIP_STORED`
entries or a different zip-reading library) as its own safety boundary.

A directly-reproducing, honest-declaration construction (no header lie
needed at all) confirms the underlying risk is real: a 2MB-on-disk archive
built with ordinary `ZIP_DEFLATED` on highly repetitive bytes, honestly
declaring its true ~200MB decompressed size, handed to the *old*
`archive.read(name)` (no bound) call.

**Fix.** `_bounded_zip_read(archive, name, limit)` reads via
`archive.open(name).read(limit + 1)` and refuses (`too_large`) if more than
`limit` bytes actually arrive — verified directly that this genuinely
bounds real decompression work regardless of declared size (a 2MB-on-disk
archive honestly declaring a 2GB member: the bounded read returned in
0.072s, producing exactly `limit + 1` bytes, nowhere near the declared
size). The declared-size pre-filter in `_safe_zip_member_names` is kept as
a cheap, fast pre-reject for obviously-oversized claims, explicitly
re-documented as a pre-filter only, never the safety boundary.
`_reject_doctype`'s scan window was also widened from a fixed 4KB prefix
(a long XML prolog comment could push a DOCTYPE declaration past it) to the
entire (already `_bounded_zip_read`-bounded) byte string.

**Proof.** `tests/test_opportunity_slate_intake.py
::test_bounded_zip_read_never_returns_more_than_the_limit_plus_one`
(the direct, honest-declaration mechanism test — asserts refusal in under
2 seconds against a real 200MB-decompressed bomb) and
`::test_a_docx_zip_bomb_style_entry_is_rejected_before_decompression`
(the reviewer's exact "lying header" shape, built via raw zip-format byte
patching of both the local file header and the central directory record —
asserts the observed byte count never exceeds `limit + 1` regardless of
which safe mechanism — this module's or the stdlib's own — refuses it, and
that refusal is fast). Both pass; both are genuine reproductions, not
declared-size-only assertions (the sham the first candidate shipped).

### F4 — PDF extraction had no time or memory bound

**Mechanism.** `page.extract_text()` (pypdf's own content-stream tokenizer)
has no size or time bound of its own. Decompressing a content stream
(`get_data()`) is cheap regardless of decoded size; *tokenizing* it for
text is what is slow, and nothing in the original `_extract_pdf_text` loop
checked either before calling `extract_text()`.

**Reproduction.** A 123KB-on-disk, single-page PDF whose content stream
honestly FlateDecodes to ~42MB of repeated `BT ... Tj ET` text-showing
operators (no header lie needed — DEFLATE's own ratio on repetitive
operator text is sufficient) hung past a 60-second hard test timeout when
handed directly to `page.extract_text()`. (A non-text-operator content
stream of similar decoded size, tried first during this investigation,
returned instantly — the specific shape that reproduces the cost is
text-showing operators, and the fix and its tests use that shape.)

**Fix, two parts, both required.** (a) A per-page pre-screen: before
calling `extract_text()`, `page._get_contents_as_bytes()` (which handles
both a single content stream and a `/Contents` array, decoding — the cheap
step) is called and its length checked against `MAX_PDF_PAGE_CONTENT_BYTES`
(2MB default), refusing (`too_large`) without ever tokenizing an oversized
page. This bound was calibrated, not assumed: the reviewer's own
illustrative "8MB, far above any real job posting" figure was tested
directly and measured at ~18 seconds of tokenization time for one page —
not an acceptable synchronous-route bound — so 2MB (~2-3s worst case on
this hardware) is used instead, still enormously more content-stream text
than any real single-page job posting or resume would contain. (b) A
wall-clock deadline (`PDF_EXTRACTION_TIMEOUT_SECONDS`, 20s default) across
the whole multi-page loop, checked between pages (not able to preempt an
already-in-flight single call — Python cannot safely interrupt a pure-CPU
call from outside without a signal/subprocess mechanism this codebase does
not use elsewhere, e.g. gunicorn's own `SIGALRM` use makes `signal.alarm`
an unsafe reuse here) — the backstop for a legitimately-shaped document
whose page count alone adds up to too long.

**Proof.** `tests/test_opportunity_slate_intake.py::PdfExtractionBoundTests`
— the exact 42MB-decoded/123KB-on-disk reproduction refused in ~0.15s
(measured, asserted `< 5.0s`) with peak RSS around 125MB (not the
reviewer's ~2GB), a test proving the guard checks the *decoded* size (not a
declared/compressed-size proxy a bomb is specifically shaped to keep
small), a boundary test confirming content just under the cap is still
accepted, and a pinned-assumption test recording that decompression alone
stays cheap even at ~20MB (the calibration fact the whole fix depends on).

### F5 — the coverage hole: no test ever executed the real connection class

**Finding.** Every SSRF/fetch test in `tests/test_opportunity_slate_intake.py`
replaces `_PinnedHTTPSConnection` with a fake, so `connect()` (the DNS-pin
mechanism, the entire point of that class) and the TLS handshake were never
executed by that suite — the reviewer's mutation probe (removing the pin,
or disabling TLS verification) would have left it green. This is *why* F1
and F2 shipped: both bugs live specifically inside real `http.client`
behavior the fakes never exercise.

**Fix.** A new module, `tests/test_opportunity_slate_intake_tls.py`, runs a
real self-signed-certificate TLS server (`cryptography`, already a
transitive dependency of the pinned `azure-identity`, generates the
throwaway cert/key in-memory per test run) on `127.0.0.1` in a background
thread, and drives the REAL `_PinnedHTTPSConnection` class and the REAL
`guarded_fetch_html` orchestration against it end to end: happy path,
`Connection: close`, EOF-delimited (no length header, no chunking), an
oversize stream, a chunked slowloris against a short deadline, and a
redirect that is independently re-resolved and re-pinned on the new host
(one physical server dispatching on the `Host:` header models two distinct
upstream hosts, proving `_resolve_public_ip` is called again — a fresh
call, for the new hostname — and a fresh connection/TLS handshake happens
for the second hop). Two direct unit tests execute the real `connect()`
against a mocked `socket.create_connection`, asserting it dials the pinned
numeric IP (never the hostname) and presents the original hostname as TLS
SNI. A final sanity test proves the test seam itself is not a hole: a
client context that does *not* trust the test's self-signed CA still fails
the handshake, confirming `_PinnedHTTPSConnection` performs real
certificate verification rather than the seam having quietly disabled it.

**The test seam.** `_PinnedHTTPSConnection.__init__` and
`guarded_fetch_html` now accept an optional `ssl_context` parameter,
documented at both definitions as test-only: every production caller
(`extract_imported_link`) leaves it `None` and gets a real
`ssl.create_default_context()` (full verification); only
`test_opportunity_slate_intake_tls.py` supplies one, and it adds exactly
one throwaway, freshly-generated, in-memory CA as an additional trusted
root — it never disables hostname checking or certificate verification.
`IMPORT_ALLOWED_PORT` (a plain module constant, already read at call time)
is monkeypatched per-test to the test server's ephemeral port, so this
suite never needs the privileged port 443 or root.

## 8. Non-blocking findings, fixed in this pass

- **Missing `Content-Type` bypassed the `text/` check.** An absent header
  no longer skips the check — it is refused (`unsupported_content_type`),
  matching the "HTML-to-text only" contract's intent that a server which
  will not say what it sent gets no benefit of the doubt.
- **Transport compression was never refused.** `Accept-Encoding: identity`
  is now sent explicitly, and any response declaring a non-identity
  `Content-Encoding` is refused rather than handed to the text extractor
  as if it were already plain bytes (previously, a gzipped body would have
  decoded to mojibake wherever it was later treated as UTF-8 text).
- **`_reject_doctype`'s 4KB scan window.** See F3 above — now scans the
  entire (already size-bounded) document.
- **Control-character/bidi hygiene was TXT-only.** A shared
  `_reject_hostile_characters` check (NUL/C0 controls excluding
  tab/newline/CR, DEL, and the nine Unicode bidirectional
  override/isolate characters — the "Trojan Source" set, named only by
  numeric code point in source, never typed as a literal character) is now
  applied, as the last step, by *every* extraction path: PDF, DOCX, TXT,
  and imported HTML alike, not only the upload/TXT path. Refused rather
  than silently stripped, for the same reason a truncation is labeled
  rather than silently applied — a member's captured source is never
  quietly altered by this module, including to remove something hostile.
- **A single shared idempotency key across three forms.** The paste,
  upload, and import forms now each mint (and post) their own idempotency
  key (`room.idempotency_key` / `upload_idempotency_key` /
  `import_idempotency_key`), so a retried paste and a subsequent upload on
  the same page load can no longer collide against the same
  `(owner_profile_id, idempotency_key)` ledger row.
- **The truncation notice was a bare, replayable query value.** `?notice=`
  is now a short-lived (60s), signed token (`itsdangerous.
  URLSafeTimedSerializer`, its own salt, never replayable against the
  anonymous-session serializer's tokens) minted only at the moment of a
  real truncated save and verified — silently ignored if missing, tampered,
  expired, or not one of the two known kinds — on the next room load. A
  bookmarked or history-replayed URL can no longer resurface a stale
  truncation claim.
- **Keyboard focus on the (then-)hidden file input.** Resolved structurally
  by the visual remediation below: the file input is no longer visually
  hidden at all (it lives inside a native `<details>` disclosure body, a
  real, visible control with its own default browser focus ring), and the
  disclosure's `<summary>` trigger already has a `:focus-visible` rule in
  the shared stylesheet (`.os summary:focus-visible`) from the pattern this
  slice reuses — no new CSS was needed.

## 9. Visual-materiality remediation

The independent review judged the first candidate's intake-screen change
material for three reasons, and this branch corrects all three rather than
waiting on a separate visual round:

1. **The tile region had moved below the footer/primary action.** Restored
   to its original DOM position — between the field-error message and the
   info note, exactly where the locked visual set and the V6 owner visual
   review placed it. A `<form>` cannot legally nest inside another `<form>`,
   so the paste form now closes at that same point (rather than after the
   footer) and its primary "Review source" submit button, still rendered in
   the footer at the bottom in its original visual position, is
   re-associated to it by the standard HTML `form="os-paste-form"`
   attribute — a DOM-order/structural change only; the button still submits
   the same form, from the same visual position it always occupied.
2. **A bare URL field had entered the tile grammar directly.** Removed. The
   tile's badge/title/body are unchanged from the locked set; the former
   static state pill is now a `<details>`/`<summary>` disclosure trigger
   using the room's *existing* disclosure grammar verbatim
   (`.os-disclosure` / `.os-disclosure__summary` / `.os-disclosure__body` /
   `.os-disclosure__actions` — the exact classes `_review.html`'s
   "Correct the wording" disclosure already uses) — no new interaction
   language, a reused one. The URL field (and, for upload, the file input)
   live inside the disclosure body, revealed only once opened.
3. **File choice auto-submitted.** Removed entirely, along with its JS
   (`wireUploadAutoSubmit` deleted from `static/js/opportunity-slate.js`).
   Both tiles now require an explicit, named submit button inside the
   disclosure body ("Upload document" / "Import link") — the member decides
   when to submit; nothing submits itself on change.

The one genuinely new visual element this slice still introduces is a
single-line URL text field (`.os-tile__link-field`) — no existing
single-line input style exists elsewhere in this room to reuse (every other
field is the multi-line `os-editor__field`), so it borrows that same
border/focus treatment (`--os-line`/`--os-focus`/the room's existing
box-shadow focus ring) rather than inventing a new visual language. This is
flagged explicitly for the reviewer's/owner's judgment rather than asserted
as automatically non-material.

Anonymous mode's tile markup is byte-for-byte the same three-line
badge/title/body/state-pill card the locked set always rendered — untouched
by any of the above; only the signed-in branch changed.

## 10. Full validation (this branch, after every fix in §7-§9)

See the session's final report for exact counts, tip SHA, and command
transcripts. Summary: the two new/existing intake test modules plus the new
real-TLS integration module all pass; the full existing
`test_opportunity_slate*.py` suite passes unchanged; the repository-wide
`unittest discover` run has only the two pre-existing, unrelated PowerShell
environment failures; `compileall`, the SQL migration governance check
(25 registered / 12 gated, `SQL FIles` untouched), and `git diff --check`
are all clean.

## 11. Third review pass — R1, R2, and test-strength findings

The second candidate (`ef8a676`, §7-§9 above) was re-reviewed and **refused**
on two residuals the reviewer reproduced directly, plus five test-strength
items. The reviewer prescribed the exact mechanisms for R1/R2; both are
implemented as prescribed, not as variants. Every fix below has a red→green
proof; every named mutation was re-run and reported (§11.8).

### 11.1 R1 — `Connection: close` + `Content-Length` still crashed, on the
exact byte that used to be safe

**Mechanism.** F1's fix (§7) captured `raw_sock = connection.sock` once,
before `getresponse()`, and F2's fix called `raw_sock.settimeout(remaining)`
on every iteration of the body-read loop, *before* checking whether the
previous `read1()` call had returned empty. For a `Connection: close` response
that also declares a `Content-Length`, `HTTPResponse` closes the underlying
file object itself — `_close_conn()` — the instant `self.length` reaches zero,
which happens *during* the `read1()` call that returns the final body bytes,
not after. The loop's next iteration then called `settimeout()` on that
now-closed fd, raising `OSError` (`EBADF`), caught by the generic
`OSError`/`ssl.SSLError`/`http.client.HTTPException` handler and surfaced as
an undifferentiated `fetch_failed` — precisely the response shape F1's own
fix was written to make safe, broken by a one-call timing gap the second
pass's tests did not happen to exercise.

**Fix.** The narrow, per-call `settimeout()` mechanism is retired entirely,
not patched. See R2 below — the same redesign fixes both findings at once.
With no manual `settimeout()` call left anywhere in the body loop, there is
nothing left in `guarded_fetch_html` that can be called against a socket
`getresponse()`/`read1()` may have already closed.

**Proof — the five-shape matrix.** `tests/test_opportunity_slate_intake_tls.py
::RealTLSFetchTests` now round-trips a real 200 response through five
distinct close/length shapes against a real local TLS server, asserting each
returns its body intact with no crash:

| Shape | Test | Result (fixed) | Result (pre-fix, `git stash`) |
|---|---|---|---|
| `Content-Length` + `Connection: close` (the exact R1 trigger) | `test_shape_cl_close_content_length_and_connection_close` | pass | **fail** (`EBADF`) |
| `Connection: close`, no length (EOF-delimited) | `test_shape_close_nocl_connection_close_no_length` | pass | pass |
| `Content-Length` only, no explicit close header | `test_shape_cl_only_content_length_no_explicit_close_header` | pass | pass |
| No length, no close header (EOF-delimited) | `test_shape_eof_no_length_no_close_header` | pass | pass |
| `Transfer-Encoding: chunked` + `Connection: close` | `test_shape_chunked_close_transfer_encoding_and_connection_close` | pass | pass |

Only the exact R1 shape fails pre-fix, confirming both that the fix targets
the real mechanism and that the other four shapes were never actually broken
(the second pass's coverage hole was specific to this one combination).

### 11.2 R2 — the deadline did not bound `getresponse()`'s internal
status-line/header reads

**Mechanism.** `getresponse()` reads the status line and every header line via
repeated internal `readline()` calls, entirely before `guarded_fetch_html`'s
own body loop — and its deadline checks — ever run. A server that dribbles
response headers one byte at a time, each individual `recv()` comfortably
inside the per-call socket timeout, can hold `getresponse()` open
indefinitely; nothing in the second pass's design bounded that phase.

**Reproduction.** A handler that sends the HTTP status line and headers one
byte at a time with a 0.2s sleep between bytes (roughly 12.6s to deliver in
full) was fetched with the deadline patched to 2.0s.

**Fix — the prescribed mechanism, implemented directly.** A `_DeadlineSSLSocket`
(`ssl.SSLSocket` subclass) is installed via `ssl.SSLContext.sslsocket_class`
before `wrap_socket()` is called in `_PinnedHTTPSConnection.connect()` — a
customization point verified, empirically, to survive `wrap_socket()`
(directly disproving the first, more obvious approach of subclassing plain
`socket.socket` before wrapping: `wrap_socket()` was verified to discard that
subclass entirely and return a fresh, un-subclassed `ssl.SSLSocket`, with zero
calls ever reaching the custom methods). The wrapper is armed with the whole
fetch's shared absolute deadline exactly once, immediately after the
handshake completes, and its `recv`/`recv_into`/`read` overrides each check
that deadline (raising `_DeadlineExceeded`, an `OSError` subclass caught
alongside the existing transport-failure family) before delegating to the
real implementation — covering the status line, every header line, and every
body chunk uniformly, whichever `http.client`-internal call chain reaches
them. `response.read1(n)` (not `response.read(n)`) is still used in the body
loop; see §11.6/N-column below for why a behavioral test can no longer prove
that choice matters, and what pins it instead.

**One verified, documented limitation, corrected upward per the reviewer's own
measurement:** the TLS handshake itself does not call any Python-level
`recv`/`recv_into`/`read` method at all — it operates below that layer — so it
is not bounded by `_DeadlineSSLSocket`. This is not, however, merely "bounded
the ordinary way by the per-connection socket timeout" in the weaker,
reset-per-syscall sense F2's original bug depended on. CPython's own
`do_handshake()` (the C-level `_ssl` implementation the socket's
`timeout` parameter drives) computes its blocking deadline once, at the start
of the call (`_PyDeadline_Init`), and enforces that SAME deadline as a TOTAL
budget across every internal retry the handshake needs — it is not reset on
each partial read the way the pre-fix body-read loop's per-call
`settimeout()` effectively was. A handshake-dribbling server (bytes trickled
in slowly enough to keep any single underlying `recv()` inside the socket
timeout) is therefore still cut off at, at most, the connect timeout per hop
— measured directly: **5.01s**, against `IMPORT_CONNECT_TIMEOUT_SECONDS`'s
5s default, comfortably inside `IMPORT_TOTAL_TIMEOUT_SECONDS`'s 10s
whole-chain budget. The handshake phase is real, bounded, and was already
safe against this exact attack shape before `_DeadlineSSLSocket` existed; the
narrower true statement is that it is bounded by a different, already-correct
mechanism (CPython's own total-deadline handshake timeout), not by
`_DeadlineSSLSocket`.

**Proof.** `test_header_dribbling_server_aborts_within_the_deadline`: against
the byte-dribbling handler above with the deadline patched to 2.0s, the fetch
aborted with `code="timeout"` in **2.19s measured elapsed** (well inside the
`deadline_seconds + 3.0` = 5.0s bound the test asserts, and nowhere near the
~12.6s the handler's own schedule would otherwise take to finish delivering
headers). Verified red→green: `git stash` of only the service module
reproduces the hang (harness-bounded, did not return within the test's own
timeout — see §11.8 for how long-running red mutants are handled), `git
stash pop` restores the fix, green again.

### 11.3 N1 — the wrong-CA test could not distinguish "verification
correctly rejected" from "verification silently off, failed for an unrelated
reason"

**Fix.** The untrusting-client test's server handler now serves a genuinely
valid, well-formed 200 response (so a client that was NOT actually verifying
the certificate would succeed and the test's assertion would have something
real to catch), and the test now asserts the specific exception type behind
the failure: `error.exception.__cause__` must be an
`ssl.SSLCertVerificationError`, not merely "some `OpportunitySourceIntakeError`
was raised for some reason."

**Mutation-verified.** A temporary source patch injecting
`context.check_hostname = False; context.verify_mode = ssl.CERT_NONE`
immediately after context creation in `connect()` was applied, the test was
re-run (`AssertionError: OpportunitySourceIntakeError not raised` — the
now-unverifying client succeeded against the untrusted cert, exactly the
failure mode this strengthening exists to catch), and the source file was
then restored from a pre-mutation backup and re-verified passing.

### 11.4 N2 — the bounded-zip test's timing bound sat inside measurement
noise

**Fix.** `test_bounded_zip_read_never_issues_an_unbounded_read_call` (new,
alongside the original timing-based test, which is kept as a secondary
signal) wraps `zipfile.ZipExtFile.read` to record the `n` argument passed on
every call while `_bounded_zip_read` processes a genuine 200MB-decompressed
zip bomb, then asserts every recorded call was bounded (`n is not None`,
`n != -1`, `n <= limit + 1`) — detecting an `archive.read(name)`-style
unbounded-read regression by what happened, not by how long it took.

**Mutation-verified.** `_bounded_zip_read`'s `member.read(limit + 1)` was
changed to `member.read()` (no bound); the new test failed
(`AssertionError: ZipExtFile.read(-1) decompresses the entire member —
unbounded` — the spy recorded the unbounded call directly), confirming the
mutation is caught independent of timing. Source restored and re-verified
passing.

### 11.5 N3 — a future pypdf release could silently break the F4 pre-screen

**Fix.** `test_pypdf_still_exposes_the_private_prescreen_method` asserts
`hasattr(pypdf._page.PageObject, "_get_contents_as_bytes")` at the class
level. `_extract_pdf_text` already fails closed (refuses every PDF, rather
than silently skipping the pre-screen) if this private method disappears in
a future pypdf version — this sentinel turns that into a red CI test instead
of a wave of production user reports as the first signal.

### 11.6 N7 — nothing enforced that `ssl_context` stays test-only

**Fix.** `ProductionCallerNeverPassesSslContextTests` (grep-idiom guardrail,
matching the style already used in `tests/test_site_rules.py`) walks every
`.py` file in the repository (excluding `tests/` and the intake service
module's own definition site) and fails if any line passes `ssl_context=`.
A second test asserts `extract_imported_link`'s signature is exactly
`(url)` — even if some future caller tried to pass `ssl_context` through the
one function production code actually calls, it structurally could not reach
`guarded_fetch_html`.

**Mutation-verified.** `opportunity_slate_routes.py`'s
`extract_imported_link(source_url)` call was temporarily changed to
`extract_imported_link(source_url, ssl_context=None)`; the guardrail failed
(`['opportunity_slate_routes.py:2611'] != []`), confirming detection. File
restored, confirmed clean (`git diff` empty), test re-verified passing.

**A related, unprescribed addition:** re-running the full targeted suite
after the R1/R2 redesign surfaced that `read1`-vs-`read` in the body loop is
no longer distinguishable by any existing behavioral/timing test — because
the deadline is now enforced one layer below either call (§11.2). Rather
than leave that mutation silently uncaught,
`BodyReadMechanismSourcePinTests::test_body_loop_reads_via_read1_not_read`
pins the literal source text (`response.read1(IMPORT_READ_CHUNK_BYTES)`).
Verified red (mutated to `response.read(...)`, the assertion failed with the
mutated source substring absent) and green (restored).

### 11.7 N4 — the action tile's disclosure fell into the 32px badge column
at the phone breakpoint

**Mechanism.** `.os-tile--action .os-disclosure` (base rule: `width: 100%`,
no `grid-column`) had no explicit placement inside the `@media (max-width:
640px)` tile grid (`grid-template-columns: 32px minmax(0, 1fr)`). CSS grid
auto-placement fills row-major "holes" left by the explicitly-placed
badge/title/body/state elements ahead of it in DOM order; the first such hole
is column 1 — the 32px badge track — so the disclosure (and, once opened, its
file/URL field and submit button) was squeezed into 32px instead of the
tile's full width.

**Fix.** `.os-tile--action .os-disclosure { grid-column: 1 / -1; }` added to
the same breakpoint, spanning both columns explicitly so no auto-placement
hole is left for it to fall into.

### 11.8 Mutation set — full re-run, this pass

Re-run directly against this branch's tip, each via a temporary source
mutation, full or targeted suite run, and restore-and-reverify cycle
(`git diff --stat` confirmed the restored file matches the pre-mutation diff
size after every cycle):

| Mutation | Result | Caught by |
|---|---|---|
| DNS pin removed (`connect()` dials `self.host` instead of `self._pinned_ip`) | **red** | `RealConnectMechanicsTests::test_connect_dials_the_pinned_ip_not_the_hostname` |
| TLS verification disabled (`check_hostname=False; verify_mode=CERT_NONE` injected in `connect()`) | **red** | `test_a_wrong_ca_is_still_rejected_verification_is_not_silently_off` (§11.3) |
| `read1` → `read` in the body loop | **red** | `BodyReadMechanismSourcePinTests::test_body_loop_reads_via_read1_not_read` (source-pin, added this pass — see §11.6 for why the behavioral tests no longer catch this) |
| Zip bound removed (`member.read(limit + 1)` → `member.read()`) | **red** | `test_bounded_zip_read_never_issues_an_unbounded_read_call` (§11.4) |
| PDF pre-screen removed (`_get_contents_as_bytes` size check deleted, falls straight to `extract_text()`) | **red** | `test_a_small_on_disk_pdf_with_a_huge_decoded_content_stream_is_refused_fast` — the mutated run was bounded at 200s (well past the test's own 5s pass bound) and killed still mid-tokenization, never reaching a result; a slowloris-class mutant that does not return within a bound well past its passing time is treated as caught, per this pass's own instruction, rather than awaited unboundedly |

### 11.9 Full validation, this pass

Targeted suites (`test_opportunity_slate.py`, `test_opportunity_slate_ai.py`,
`test_opportunity_slate_intake.py`, `test_opportunity_slate_intake_tls.py`):
339 passed. Full `unittest discover -s tests`: 2574 tests, 2 failures (the
same pre-existing, environment-only PowerShell-availability failures noted in
§10, unrelated to this slice) — one additional pre-existing, unrelated
test (`test_a_tampered_notice_token_is_ignored`, OS-1 notice-token code this
slice does not touch) was observed to fail once, non-reproducibly, in a
single full-suite run and passed cleanly on five immediate isolated re-runs
and the next full-suite run — recorded at the time as an apparent
pre-existing flake, not a regression. The reviewer subsequently pinned the
exact mechanism and measured a 5.92% real rate; fixed in the pre-release
pass, §11.10. `compileall`: clean. SQL migration governance check: 25
registered / 12 gated, unchanged. `git diff --check`: clean.

### 11.10 Pre-release pass — deflake and two documentation corrections

Final review APPROVE at `a361510` came with two small pre-release items.

**Deflake `test_a_tampered_notice_token_is_ignored`.** The test's tamper
step flipped the token's LAST character (`"A" if token[-1] != "A" else
"B"`) — the final character of the base64url-encoded HMAC signature. A
base64url string's final character encodes fewer than 6 real bits whenever
the digest's bit length is not a multiple of 6 (true of every common hash
size); Python's `base64` decoder silently discards the unused low bits
rather than validating them are zero. `"A"`/`"B"`/`"C"`/`"D"` all share the
same real-bit value in that discarded-bits equivalence class, so whenever
the real token happened to already end in one of those four characters, the
old fallback logic (`"A"` unless already `"A"`, else `"B"`) landed on a
DIFFERENT character encoding the SAME real signature bytes — the "tampered"
token was not actually tampered, and still verified. Measured by the
reviewer at a 5.92% real rate — a property of the token, not the test
runner. **Fixed** by flipping a MIDDLE character of the signature instead:
every non-final character of a base64url string encodes a full 6 real bits
(the discarded-bits effect is specific to the string's last character), so
changing one is a mathematically guaranteed byte-level change, not a
probabilistic one. Independently corroborated in this session, mint+verify
against the real `_read_notice_token` in a tight loop of 4000 tokens:
**0/4000 false-passes**, matching the reviewer's own measurement. The test
itself was run 50 times in a loop: **50/50 passed, zero flakes**.

**Handshake residual, corrected upward.** §11.2's documented handshake
limitation previously understated how bounded the handshake phase already
is. Corrected in place (§11.2): CPython's `do_handshake()` computes its
blocking deadline once, at the start of the call (`_PyDeadline_Init`), and
enforces that same deadline as a TOTAL budget across every internal retry —
not reset per partial read — so a handshake-dribbling server is cut off at,
at most, the connect timeout per hop (measured **5.01s** against the 5s
`IMPORT_CONNECT_TIMEOUT_SECONDS` default), comfortably inside the 10s
`IMPORT_TOTAL_TIMEOUT_SECONDS` whole-chain budget. The handshake was already
safe against a slow-dribble attack before `_DeadlineSSLSocket` existed, via
CPython's own already-correct mechanism, not merely "the ordinary socket
timeout" in the weaker sense the original wording could be read as.

**Extraction behavior note.** `_VisibleTextExtractor` (`html_to_text`)
skips only a fixed set of tag names (`script`/`style`/`noscript`/
`template`/`svg`/`head`/`iframe`/`object`/`embed`); it has no CSS awareness
and does not check the HTML `hidden` attribute, so text hidden via
`display: none`/`visibility: hidden` or a `hidden` attribute on an
otherwise-ordinary element (e.g. `<div>`) is extracted the same as visible
text. This is accepted, not a defect: the extractor's job is text
extraction, not rendering, and the member reviews every extracted result at
Review Source before anything is saved as canonical — human-in-the-loop
review is the mitigation, not a parser-level CSS/attribute check.

**Release notes.** PDF extraction's whole-document wall-clock CPU budget is
**`PDF_EXTRACTION_TIMEOUT_SECONDS`, 20 seconds per upload** (§7 F4) — the
backstop for a legitimately-shaped, multi-page document whose page count
alone adds up to too long, checked between pages (not able to preempt an
already-in-flight single page's tokenization). Flag remains default off;
not merged, not deployed as of this pass.
