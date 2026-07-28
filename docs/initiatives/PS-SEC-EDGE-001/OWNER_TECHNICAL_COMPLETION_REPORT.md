# PeerSlate Completion & Handoff Report - PS-SEC-EDGE-001

## A. Status

- **Package:** PS-SEC-EDGE-001 - HTTP edge security, deployment package, and
  static asset delivery
- **Status:** Complete
- **Branch and commit:** `work/2026-07-27-web-architecture-audit-001`; base
  Azure `origin/main` at `141273fe51c0ac3c35e4ab15d96e34524b674d68`;
  implementation tip `ad07bf2d208e652ff43486529f41c7c515450804` plus this
  package record
- **PR / pipeline / environment:** Azure PR 190 into `main`. Pipeline and
  production results are recorded in section F; rows marked pending at the
  time of writing were completed after merge and reported to Pete directly.
- **Production state:** Not deployed at time of writing; release verification
  in section F
- **Visual authority and status:** Not Applicable
- **Visual inspector:** Not Applicable
- **Approved-mockup fidelity evidence:** Not Applicable
- **Agent-run compare-refine pass count and mismatch register:** Not Applicable
- **Pete-run inspection record:** Not Applicable
- **Homepage product projection:** Not Applicable - no product function,
  hierarchy, theme, truth status, or visual finish changes, so the homepage
  parity check finds nothing to update
- **Pete / designated session manager visual acceptance:** Not Applicable
- **Designated session manager:** Claude Code, self-managed
- **Manager handoff status and next receiver:** Package record and this report
  prepared for the ChatGPT Work/Codex manager lane
- **Lane owner and self-managed authority:** Claude Code under the 2026-07-24
  owner decision in `CLAUDE.md`
- **Self-certification:** Pass
- **Complete-diff review:** Passed - issues found and corrected, listed in F
- **Acceptance requested:** technical report and release

## B. What changed technically

Reconciliation, not a fresh implementation. Seven commits produced by a cloud
agent session on `claude/website-architecture-audit-7l52z6`, built on
`be7f857`, were merged onto Azure `main` at `141273f` - thirteen commits and
194 changed files later. The cloud session could not reach Azure at all, so
its test results described a base that was no longer current. Everything below
was re-run on the reconciled base.

**`app.py`**
- `_client_rate_limit_key` replaces `get_remote_address` as the limiter key
  function. Parses `X-Forwarded-For`, takes the rightmost entry, strips an
  `address:port` suffix while leaving bracketed and bare IPv6 intact,
  validates the result with `ipaddress.ip_address`, and falls back to
  `get_remote_address()` when no usable entry exists.
- `_cross_site_refusal(subject)` centralises the origin check for the four
  public AI endpoints, preserving each endpoint's existing message wording.
- Flask-Compress configured over an explicit text-only MIME list (`text/html`,
  `text/css`, `text/plain`, `text/xml`, `text/javascript`,
  `application/javascript`, `application/json`, `image/svg+xml`) at gzip 6 /
  brotli 5, 500-byte floor. Images and audio are absent from the list and are
  not compressed.
- Static asset versioning: `_static_file_version` returns a 12-hex SHA-256
  content token, cached per `(st_mtime_ns, st_size)` so steady state costs one
  `os.stat`. An `@app.url_defaults` hook stamps `?v=<token>` onto every
  `url_for('static', ...)` for `.css`/`.js`, and skips when a caller supplied
  its own `v`. An `@app.after_request` hook marks a static response
  `public, max-age=31536000, immutable` only when the requested token equals
  the file's live hash, so a stale or hand-typed token can never pin an old
  version.
- A partial Content-Security-Policy limited to directives that cannot break
  rendering.

**`identity.py`** - when `PEERSLATE_AUTH_ISSUER` is configured, the issuer in
the presented principal must equal it, compared case-insensitively and
ignoring a trailing slash; otherwise `AuthenticationRequired` is raised before
any account upsert. Unset preserves prior behaviour exactly.

**`owner_routes.py`** - `_is_same_origin_write` now requires a positive
same-origin signal instead of allowing the both-headers-absent case. A new
`@owner.after_request` hook defaults every owner response to
`Cache-Control: private, no-store` via `setdefault`, leaving explicit
per-route policies intact.

**`auth_routes.py`** - the flag-off owner workspace fallback returns
`private, no-store`. Rendered bytes are unchanged.

**`azure-pipelines.yml`** - the deployment `CopyFiles@2` step excludes
`artifacts/**`, `tests/**`, `Design ideas/**`, `static/Background/**`,
`static/Mockup/**`, `.github/**`, and the root v1.x Bible DOCX. An inline
comment records what must *not* be excluded and why.

**`requirements.txt`** - `Flask-Compress==1.24`, `brotli==1.2.0`.

**Templates** - hand-typed `?v=` tokens removed from CSS/JS links across 28
templates so the automatic content hash applies. No markup, structure, class,
or content changes.

**Deletions** - `static/css/story-cinematic.css` (529 lines) and
`templates/partials/life_values.html` (52 lines), both verified unreferenced.
Fifteen superseded Bible and Roadmap DOCX files.

**Tests** - new `tests/test_http_edge_security.py` (565 lines). New
`DeploymentPackageTests` and `DependencyPinTests` in `tests/test_site_rules.py`.
Assertions on hand-typed version tokens across six existing suites replaced
with content-hash regex assertions.

## C. What this means in plain English

Four ways the site was weaker than it looked, all fixed.

The abuse limit on the AI features was counting everyone as one person,
because behind Azure every visitor appears to arrive from the same address.
One heavy user could use up the limit for the whole site. Now each visitor is
counted separately.

Anyone's website could quietly post into a signed-in member's private capture
list, if it stripped the right headers on the way. The site used to allow a
request that gave no evidence of where it came from. Now it requires that
evidence.

Private pages could be stored by a shared cache or brought back by the browser
after sign-out - so on a shared computer, one person's private material could
reappear. Those pages now say plainly that they must not be stored.

The site also checks who issued a sign-in against a configured value. That
check is now enforced rather than advisory.

Separately, the site got faster and the deployment smaller. Pages and
stylesheets are compressed in transit, style sheets and scripts get a
fingerprint in their address so browsers can safely keep them for a year and
still pick up changes instantly, and roughly 300 MB of screenshots, tests, and
design material stopped being copied onto the web server.

## D. What the website or member can do now

Nothing new, by design. No route, feature, page, permission, or member
capability changed. The same pages exist, look the same, and do the same
things. What changed is how the server responds: who a rate limit counts,
which requests are refused, what may be cached, how much is transferred, and
what is shipped to the server. A member's only observable difference should be
faster loading.

## E. How this connects to PeerSlate

This serves the always-on trust invariants in `AGENTS.md` rather than any
product initiative: user content private by default, authorization checked
before protected data is returned or changed, and the least destructive
implementation that meets the scope. The private-caching and owner-write fixes
protect the private-by-default boundary directly. Nothing here touches the
canonical Capture-to-Moment model, the Journal or My Story boundary, audience
or publication controls, or any AI-proposes-people-decide surface.

Roadmap position: no reserved slot was found for HTTP-edge or delivery
hardening. The package is recorded on its own and its one generalisable
lesson is folded into `PS-OPS-001` Gate Candidate.

## F. Verification and validation

**Complete-diff review.** The full diff `141273f..HEAD` was inspected file by
file. Three issues were found and corrected:

1. *A false statement about production.* The upstream test comment claimed
   production leaves `PEERSLATE_AUTH_ISSUER` unset so the new enforcement
   would be inert. `peerslate-pete` defines it. The comment was rewritten to
   record the real state and the condition that must hold. This is the finding
   that produced the new Gate Candidate blocker.
2. *A reserved file edited.* The upstream branch stripped the `?v=` token from
   `templates/the_slate_people_interests.html`, which `PS-COMMUNITY-TABS-001`
   reserves. Reverted to `main`'s version; the template never renders.
3. *An incomplete conflict resolution.* `templates/resume2.html` conflicted
   because `main` had added `member-overview.css` with a hand-typed token
   after the branch point. Resolved by keeping all three stylesheets and
   stripping all three tokens. Keeping any token would have silently opted
   that file out of the immutable-cache path, which is the exact drift this
   work removes. A repository-wide sweep confirmed no hand-typed `?v=` token
   remains in `templates/` or `static/`.

**Automated tests** - Python 3.13 venv, placeholder `ANTHROPIC_API_KEY`:

| Check | Result |
|---|---|
| `pytest tests/` (full suite, reconciled base) | **1034 passed, 3 skipped, 501 subtests**, ~48s |
| `pytest tests/test_http_edge_security.py` | **35 passed, 32 subtests** |
| `pytest tests/test_site_rules.py tests/test_governance_pointers.py` | **passed** (mandatory guardrails) |

**Independent verification of claims.** The upstream branch's own figures were
not taken on trust:

- `static/css/style.css` measured at 382,386 bytes raw, 73,609 bytes brotli
  quality 5, 81,031 bytes gzip 6. The compression claim holds.
- The newly excluded paths were checked for runtime readers directly. The only
  hits for `static/Mockup` are two CSS *comments* in `style.css`; there is no
  `url()` reference to any excluded path from any CSS, template, or script.
  Both deleted files are unreferenced repository-wide.
- Deployment package size: the excluded paths measure roughly 314 MB on this
  worktree (`artifacts` 292 MB dominating), plus about 60 MiB of removed DOCX.
  The upstream figure of 530 MB reducing to 294 MB was **not** independently
  reproduced and should not be quoted as verified; the reduction is
  substantial and dominated by `artifacts/`.

**Security and privacy checks.** No secret, credential, `.env`, publish
profile, or machine-local `launch.json` appears in the diff. No change to App
Service settings, identity providers, or DNS. The issuer value was read from
the target environment and matched before merge - see the package README
section 5.

**Not verified, stated honestly.** No independent fresh reviewer ran against
this diff; the lean-delivery triggers for authorization and shared
infrastructure are met, so a reviewer would be defensible and was not
available. No staging environment exists (`peerslate-candidate` is gone), so
production is the first real environment this code meets. No responsive,
accessibility, or visual evidence was captured, because no user-facing surface
changed; template edits are token removals only.

## G. Known gaps, risks, and exclusions

- **Rate limiting is still in-memory per worker.** Correct keying does not fix
  cross-instance accounting. Redis-backed storage remains the documented
  production answer and is out of scope here.
- **The owner-write check could refuse a very old browser.** Requiring a
  positive `Origin` or `Sec-Fetch-Site` signal is safe on current browsers,
  which send at least one on a same-origin form post. A sufficiently old
  client sending neither would now be refused on the no-JavaScript form path.
  This is a deliberate fail-closed choice on a private surface.
- **`backports.zstd` is unpinned**, arriving transitively via Flask-Compress.
- **CSP is deliberately partial.** Only directives that cannot break rendering
  are enforced; this is not a complete policy.
- **The two governance records in section 7 of the README remain stale**, both
  in files other lanes own.

## H. Clear next step

Merge, confirm the Azure pipeline passes Build and Deploy for the exact merge
commit, verify the live site, and hand the package record to the ChatGPT
Work/Codex manager lane so the `PS-OPS-001` amendment is confirmed and the two
stale governance records are corrected by the lanes that own them.

## I. What Pete needs to do or decide

1. **Confirm the `PS-OPS-001` amendment.** A Gate Candidate automatic blocker
   was added under direct owner instruction, in a package whose lane table
   entry still reserves its governance records to the Codex lane on a branch
   that has since merged and been deleted. The `PS-OPS-001` manager should
   acknowledge it rather than discover it.
2. **Decide who corrects the two stale governance records** - the orphaned
   `interview_studio_asset_signature` and the `PS-COMMUNITY-TABS-001` status.
   Both sit in files this package deliberately did not touch.
3. **Decide whether HTTP-edge and delivery hardening earns a standing roadmap
   slot**, or stays ad-hoc. No reserved allocation was found.
