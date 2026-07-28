# PeerSlate Completion & Handoff Report - PS-SEC-EDGE-001

> **Recovery amendment, 2026-07-28:** The original release represented below
> caused a production outage and was fully reverted. The current recovery is on
> `work/2026-07-28-sec-edge-reland-001` from Azure `origin/main`
> `89a619a560f04ec3763016939361f64516aac6bf`. It restores the reviewed
> security/static/deployment subset while removing Flask-Compress, Brotli, all
> `COMPRESS_*` configuration, and compression-only tests. The reconstruction
> commit is `306840985fa781b676b1aa56fb66d8480410b036`; the safe implementation
> foundation is `16c656140d0b697eac803df5fa82b31e3feb4557`. Fresh independent
> review failed the original pushed recovery SHA; all six findings are
> corrected in the current candidate and the full local suite passes. The
> isolated Candidate environment is restored. Corrected exact
> `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd` received independent `Pass`,
> and Azure build 262 Candidate Build/Deploy/Smoke/Stop passed. Gate Candidate
> is `Pass`. This branch is not merged, deployed to production, or live.

## A. Status

- **Package:** PS-SEC-EDGE-001 - HTTP edge security, deployment package, and
  static asset delivery
- **Status:** Gate Candidate `Pass`; Azure PR / production Gate F authorized
- **Branch and commit:** `work/2026-07-28-sec-edge-reland-001`; base Azure
  `origin/main` at `89a619a560f04ec3763016939361f64516aac6bf`;
  exact assessed source
  `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`
- **PR / pipeline / environment:** No recovery PR. Historical PR 190/pipeline
  259 failed in production; PR 191/pipeline 260 reverted it and restored
  production. Recovery pipeline 261 was diagnostic: Build and
  CandidateDeploy passed, CandidateSmoke failed on an omitted non-secret
  Candidate build flag, and CandidateStop passed. After correction, exact
  build 262 (`20260728.4`) passed Build, CandidateDeploy, CandidateSmoke, and
  CandidateStop; both production stages skipped.
- **Production state:** Healthy on the revert; none of the recovery branch is
  deployed or live
- **Visual authority and status:** Not Applicable
- **Visual inspector:** Not Applicable
- **Approved-mockup fidelity evidence:** Not Applicable
- **Agent-run compare-refine pass count and mismatch register:** Not Applicable
- **Pete-run inspection record:** Not Applicable
- **Homepage product projection:** Not Applicable - no product function,
  hierarchy, theme, truth status, or visual finish changes, so the homepage
  parity check finds nothing to update
- **Pete / designated session manager visual acceptance:** Not Applicable
- **Designated session manager:** current ChatGPT Work/Codex task
- **Manager handoff status and next receiver:** Recovery implementation is
  verified; the fresh GPT-5.6 Sol High independent review failed original SHA
  `3d507e7f5f32299648153abbd00ae915825219c5`, all findings were corrected,
  and the reviewer passed exact `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`
- **Lane owner and self-managed authority:** Codex on the recovery branch
- **Self-certification:** Pass for the exact assessed Candidate
- **Complete-diff review:** Writer and independent complete-diff reviews are
  complete; the original independent result was `Fail`, all accepted findings
  are corrected, and the corrected exact-SHA result is `Pass`
- **Acceptance requested:** Azure PR / production Gate F

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
- Response compression is not part of the recovered package. The dependency,
  import, application configuration, initialization, and compression-only
  tests were removed after the Python 3.14 production boot failure.
- Static asset versioning: `_static_file_version` returns a 12-hex SHA-256
  content token, cached per `(st_mtime_ns, st_size)` so steady state costs one
  `os.stat`. An `@app.url_defaults` hook stamps `?v=<token>` onto every
  `url_for('static', ...)` for `.css`/`.js`, and skips when a caller supplied
  its own `v`. An `@app.after_request` hook marks a static response
  `public, max-age=31536000, immutable` only when the requested token equals
  the file's live hash, so a stale or hand-typed token can never pin an old
  version.
- A central response policy defaults owner, authenticated API,
  viewer-personalized People & Interests, and Control Room blueprint responses
  to `private, no-store`. Any app route that resolves a member identity gets
  the same policy, closing the identity-personalized Slate Board path while
  preserving stricter explicit headers.
- A partial Content-Security-Policy limited to directives that cannot break
  rendering.

**`identity.py`** - the issuer must be present in the Easy Auth principal. When
`PEERSLATE_AUTH_ISSUER` is configured, that presented claim must equal it,
compared case-insensitively and ignoring a trailing slash; otherwise
`AuthenticationRequired` is raised before any account upsert.

**`owner_routes.py`** - `_is_same_origin_write` now requires a positive
same-origin signal instead of allowing the both-headers-absent case. A new
`@owner.after_request` hook defaults every owner response to
`Cache-Control: private, no-store` via `setdefault`, leaving explicit
per-route policies intact.

**`auth_routes.py`** - the flag-off owner workspace fallback and every
successful/error `/auth/session` result return `private, no-store`. Rendered
HTML bytes are unchanged.

**`azure-pipelines.yml`** - the deployment `CopyFiles@2` step excludes
`artifacts/**`, `tests/**`, `Design ideas/**`, `static/Background/**`,
`static/Mockup/**`, `.github/**`, and the root v1.x Bible DOCX. An inline
comment records what must *not* be excluded and why. The Candidate branch
selector now names this exact recovery branch.

**Candidate App Service** - the separate Linux B1 plan and
`peerslate-candidate` Web App are restored with no managed identity, connection
string, production credential, custom domain, or private feature. Its only app
settings are an inert import-time provider value and the non-secret
`SCM_DO_BUILD_DURING_DEPLOYMENT=true` platform build flag.

**`docs/governance/AI_DELIVERY_AUDIT_REGISTER.md`** - records the production
incident as an open Triggered audit with exact failed/revert SHAs, the bounded
scope, `Not Assessed` result, reviewer gap, and next action. It does not alter
the four-slice checkpoint count.

**`requirements.txt`** - no response-compression dependency is added.

**Templates** - hand-typed `?v=` tokens removed from CSS/JS links across 26
surviving rendered/package-owned templates so the automatic content hash
applies. One obsolete partial is deleted. No markup, structure, class, or
content changes.

**Deletions** - `static/css/story-cinematic.css` (529 lines) and
`templates/partials/life_values.html` (52 lines), both verified unreferenced.
Fifteen superseded Bible and Roadmap DOCX files.

**Tests** - new `tests/test_http_edge_security.py` covering the remaining edge
contracts; compression-only cases are removed. New
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

Separately, the deployment is smaller. Style sheets and scripts get a
fingerprint in their address so browsers can safely keep them for a year and
still pick up changes instantly, and roughly 300 MB of screenshots, tests, and
design material stops being copied onto the web server. Response compression
is deferred.

## D. What the website or member can do now

Nothing new, by design. No route, feature, page, permission, or member
capability changed. The same pages exist, look the same, and do the same
things. What changes is how the server responds: who a rate limit counts,
which requests are refused, what may be cached, how static assets are
versioned, and what is shipped to the server.

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
   work removes. A sweep of the rendered, package-owned templates confirmed no
   hand-typed `?v=` token remains there. The reserved, retired
   `templates/the_slate_people_interests.html` rollback file deliberately keeps
   its existing `?v=pi-board-17` tokens and is not rendered.

**Historical pre-incident automated tests** - Python 3.13 venv, placeholder
`ANTHROPIC_API_KEY`; these did not exercise Azure's Python 3.14 import branch:

| Check | Result |
|---|---|
| `pytest tests/` (full suite, reconciled base) | **1034 passed, 3 skipped, 501 subtests**, ~48s |
| `pytest tests/test_http_edge_security.py` | **35 passed, 32 subtests** before compression removal |
| `pytest tests/test_site_rules.py tests/test_governance_pointers.py` | **passed** (mandatory guardrails) |

**Current recovery verification** - Python 3.13.3 repository venv, placeholder
`ANTHROPIC_API_KEY`:

| Check | Result |
|---|---|
| Application import after compression removal | **passed** |
| `python -m pip check` | **passed**; no broken requirements |
| Final focused edge/Slate/API/auth/feed suite | **100 passed, 36 subtests** |
| `python -m compileall -q app.py auth_routes.py identity.py owner_routes.py scripts` | **passed** |
| `pytest tests -q` after all independent-review corrections | **1035 passed, 3 skipped, 503 subtests** |
| `git diff --check` | **passed** |
| Compression runtime/dependency scan | **passed**; no Flask-Compress, `flask_compress`, `Compress`, `COMPRESS_*`, Brotli, or `backports.zstd` reference in runtime, requirements, tests, or pipeline |

Read-only production checks after the revert returned HTTP 200 for `/`,
`/healthz`, `/petec/resume`, and `/experience`; `/healthz` reported release ID
`5f2e58344f1457d368abfce1`. This confirms the reverted production baseline is
healthy. It is not evidence that the recovery branch is deployed.

**Independent verification of claims.** A fresh GPT-5.6 Sol High reviewer
assessed exact original recovery
`3d507e7f5f32299648153abbd00ae915825219c5` and returned `Fail` with five
release-blocking code/infrastructure findings and one low evidence-accuracy
finding:

1. a missing issuer claim incorrectly fell back to the configured expected
   issuer before comparison;
2. the Candidate branch selector still named the prior responsive-audit
   branch;
3. successful `/auth/session` JSON was storable;
4. authenticated/member-personalized API JSON was storable;
5. the identity-personalized Slate Board HTML was storable; and
6. the manual static-token sweep claim failed to name the reserved retired
   rollback-template exception.

All six are corrected with focused regressions. The reviewer passed exact
corrected `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd` and reported no
remaining critical, high, or medium security/privacy/shared-infrastructure
blocker.

The upstream branch's own figures were not taken on trust:

- The compression measurements were accurate on Python 3.13 but are no longer
  release evidence because compression is excluded from the recovery.
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
profile, or machine-local `launch.json` appears in the diff. No change to
production App Service settings, identity providers, or DNS. The separate
Candidate receives only the two documented non-production settings. The
production issuer value was read from the target environment and matched
before merge - see the package README section 5.

**Not verified, stated honestly.** The branch is not merged, deployed to
production, or live. No responsive, accessibility, or visual evidence was
captured, because no visual surface changed; template edits remain token
removals only.

## G. Known gaps, risks, and exclusions

- **Rate limiting is still in-memory per worker.** Correct keying does not fix
  cross-instance accounting. Redis-backed storage remains the documented
  production answer and is out of scope here.
- **The owner-write check could refuse a very old browser.** Requiring a
  positive `Origin` or `Sec-Fetch-Site` signal is safe on current browsers,
  which send at least one on a same-origin form post. A sufficiently old
  client sending neither would now be refused on the no-JavaScript form path.
  This is a deliberate fail-closed choice on a private surface.
- **Response compression is deferred.** The failed Flask-Compress/Brotli/zstd
  path is absent from the recovery.
- **CSP is deliberately partial.** Only directives that cannot break rendering
  are enforced; this is not a complete policy.
- **The restored Candidate plan incurs temporary Basic B1 cost.** It remains
  separate from production compute, is stopped outside automated smoke, and
  must be removed after verified production release under `PS-OPS-001`.
- **The two governance records in section 7 of the README remain stale**, both
  in files other lanes own.

## H. Clear next step

Create the required Azure PR, complete the squash merge after policy checks,
monitor the exact main pipeline, verify the live production identity and
canonical routes, and roll back immediately on a mandatory failure.

## I. What Pete needs to do or decide

Pete delegated the remaining bounded recovery and release work end to end. No
additional Pete action is required for the authorized Azure PR, production
Gate F, live verification, or bounded rollback.
Out-of-scope owner decisions remain:

1. **Decide who corrects the two stale governance records** - the orphaned
   `interview_studio_asset_signature` and the `PS-COMMUNITY-TABS-001` status.
   Both sit in files this package deliberately did not touch.
2. **Decide whether HTTP-edge and delivery hardening earns a standing roadmap
   slot**, or stays ad-hoc. No reserved allocation was found.
