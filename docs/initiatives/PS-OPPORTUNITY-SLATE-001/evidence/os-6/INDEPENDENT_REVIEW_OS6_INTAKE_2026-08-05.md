# Independent review — OS-6 document upload and public-link import

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort, across
  three adversarial rounds.
- Round 1 (`7a0cd7e`): **REFUSED** — four blocking defects, each reproduced
  with measurements: the import read loop crashed on Connection:close
  responses (making the size/time caps dead code); the wall-clock cap was
  unenforceable inside a single read (worker pinned >120s); DOCX zip guards
  trusted attacker-declared sizes (299KB archive → 301MB allocation); PDF
  extraction was unbounded (80KB file → 79s CPU, 2GB RSS). Root cause: every
  fetch test mocked the real connection class. The intake tile change was
  judged material.
- Round 2 (`ef8a676`): **REFUSED** — two residuals: Connection:close +
  Content-Length (the dominant real-server shape) still failed via EBADF, and
  the deadline never bounded the response-header phase (header dribble
  blocked at 300s vs a 10s deadline). Visual remediation accepted as
  non-material (tiles restored, disclosure grammar, no auto-submit).
- Round 3 (`a361510`): **APPROVED** — both residuals closed by one redesign:
  a deadline-aware `ssl.SSLSocket` subclass installed via `sslsocket_class`,
  making every real socket read deadline-bound (header dribble now aborts at
  10.00s; the handshake residual measured bounded at ≤5s per hop because
  CPython enforces the socket timeout as a total handshake deadline). All
  eight mutations red, including the two previously silent (TLS verification
  disabled; unbounded zip read). Five-shape response matrix green.
- Final tip `9445e83` deflaked the tampered-token test (measured 5.92% →
  0/4000) and corrected the completion record; integration merge with the
  live OS-5 produced `71f7393` with the full battery green (2,590 tests).

## What survived every attack from round 1 onward

The SSRF address guard: resolved-address validation with IP pinning defeated
decimal/hex/octal/fullwidth literals, IPv4-mapped/compatible, 6to4, Teredo,
NAT64, CGN, link-local and the Azure metadata endpoint, mixed resolutions,
redirect games across every hop, and CRLF injection.

## Release conditions and owner decisions

- Pete granted blanket approval on 2026-08-05 ("i approve it all you have
  full permissions to finish everything"), covering the intake-disclosure
  visual acceptance (judged non-material by the reviewer: tiles in their
  locked position, anonymous render equivalent to base, no auto-submit, the
  room's own disclosure grammar) and the release itself.
- Deploy-time dependency: pypdf 6.14.2 boot verification on the Azure App
  Service Python runtime — the post-deploy smoke covers the route; the
  requirements pin carries the flag.
- Recorded deferrals: no retention of original uploaded bytes (needs a future
  migration for a blob locator; nothing claims otherwise), no SOURCE_PROCESSING
  stage rail for upload (full-page POST, honest), hidden-text extraction note,
  and the 20s-per-upload PDF CPU budget at 6/min.
