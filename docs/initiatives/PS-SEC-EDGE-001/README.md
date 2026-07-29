# PS-SEC-EDGE-001 - HTTP edge security, deployment package, and static asset delivery

**Owner:** Pete
**Package-designated session manager:** current ChatGPT Work/Codex task,
continuing from the 2026-07-28 incident handoff
**Writer:** Codex on `work/2026-07-28-sec-edge-reland-001`; documentation
closeout on `work/2026-07-28-sec-edge-closeout-001`
**Base:** Azure `origin/main` at
`89a619a560f04ec3763016939361f64516aac6bf`
**Upstream source:** the ad-hoc Claude session branch
`claude/website-architecture-audit-7l52z6` (GitHub mirror only), built on
`be7f857`, reconciled onto current Azure `main` in this package
**Status:** **Complete, released, and verified live.** Safe subset
reconstructed after the PR 190 outage and revert;
compression is removed at
`16c656140d0b697eac803df5fa82b31e3feb4557`. A fresh independent review
failed the original recovery SHA, and all six findings are corrected. The
corrected exact SHA received independent `Pass`; full local verification and
Azure build 262 Candidate Build/Deploy/Smoke/Stop pass. Gate Candidate is
`Pass` for exact
`a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`. Azure PR 192 squash-merged at
`9445d63f12067997395206a8cfb504013c247158`; automatic pipeline 263
(`20260728.5`) and independent live verification passed. Production release
`524cb04dc5b5aa82a58c8b2a` is live, and the temporary Candidate resources
are removed.
**Visual authority:** Not applicable - no composition, hierarchy, typography,
colour, or responsive interaction model changes
**Runtime authority:** HTTP response edge, deployment packaging, and static
asset delivery only

## 1. Why this package exists

The work was produced by a Claude agent session as a website architecture
audit, with no initiative package and no roadmap slot. It reached Pete as a
branch on the GitHub mirror with an open pull request that could not deploy,
because GitHub is a mirror and an inbox, never a merge target or a deploy
path.

Pete directed on 2026-07-27 that the work be recorded as a package before it
merged, so the change would not land as an orphan with no governance record.
This package is that record. It is written after implementation and describes
what was actually built and verified, not a forward plan.

## 2. Scope

Five bounded areas, all at the HTTP edge or in delivery. None of them change
product behaviour, member-visible function, routes, schema, migrations,
feature flags, or visual design.

**Rate limiting identity.** The limiter was keyed on `request.remote_addr`.
Behind Azure that is the platform edge address and is identical for every
visitor, so the AI endpoint limits applied to the entire internet as a single
bucket: one visitor could exhaust the limit for everyone, and an attacker
spreading requests would never be limited individually. The key is now the
rightmost `X-Forwarded-For` entry, which is the one Azure appends and which a
forged header can prepend to but never replace. The ephemeral source port is
stripped, because keying on `address:port` would make every request look like
a new client.

**Cross-site calls to the public AI endpoints.** `/api/chat` and its siblings
had no origin check. A shared helper now refuses a caller that identifies
itself as cross-site or presents a foreign `Origin`. A request carrying
neither header is still allowed, because these routes are public, anonymous,
and must remain usable by non-browser clients. This is abuse control, not
CSRF defence.

**Owner write authorization.** `_is_same_origin_write` returned true when both
`Origin` and `Sec-Fetch-Site` were absent. That failed open: a cross-site form
post that stripped both headers reached `POST /app/capture`, which requires no
unguessable token, and could write into a signed-in member's private capture
list. A positive same-origin signal is now required. These routes carry real
no-JavaScript HTML form posts, so they cannot demand a custom header the way
the JSON APIs do.

**Private response caching.** The application default (`no-cache,
must-revalidate`) forces revalidation but still permits storage and
back/forward-cache restoration. The owner, authenticated API, personalized
People & Interests, and Control Room blueprints now default to `private,
no-store`; so does any app route that resolves a member identity. Successful
`/auth/session` responses are explicitly non-storable. Routes that set an
explicit stricter policy keep it.

**Identity issuer assertion.** The issuer inside the Easy Auth principal is
part of the identity key and was treated as advisory. When
`PEERSLATE_AUTH_ISSUER` is configured it is now required to match. See
section 5 - this is the finding that produced the new Gate Candidate blocker.

Delivery work in the same package: the deployment package no longer carries
evidence, tests, or design material; static CSS and JS carry an automatic
content-hash version; a partial
Content-Security-Policy is enforced; and fifteen superseded Bible and Roadmap
DOCX files leave the working tree.

HTTP response compression is deliberately excluded from this recovery. Azure
App Service's Python 3.14 image could not import Flask-Compress 1.24 because
the image lacks the `_zstd` extension required by `compression.zstd`. That
module-load failure prevented every Gunicorn worker from booting and caused
the PR 190 production outage. Compression is now a separate future change that
must be proven on the real production-like runtime before release.

## 3. Explicitly out of scope

No product feature, route, schema, migration, feature flag, audience or
publication control, AI behaviour, member capability, or visual design. No
change to authentication providers, **production** App Service settings, DNS,
monitoring, or secrets. The separate non-production Candidate App Service is
restored under `PS-OPS-001`; no default-off capability is enabled.

## 4. Files another lane owns, deliberately untouched

- `docs/governance/CURRENT_BASELINE.yaml`, `docs/governance/CURRENT_STATE.md`,
  and `CODEX_PROMPT.md` - the Interview Studio audio/video lane holds these.
- `templates/the_slate_people_interests.html` - `PS-COMMUNITY-TABS-001`
  reserves the People & Interests frontend. The upstream branch stripped this
  template's hand-typed `?v=` token; that change was reverted here. `app.py`
  keeps the template on disk only for rollback and the route redirects, so it
  never renders and the strip would have changed nothing at runtime.

One reserved file *was* edited, under direct owner instruction:
`docs/initiatives/PS-OPS-001/README.md`, to add the Gate Candidate blocker in
section 5. The current ChatGPT Work/Codex `PS-OPS-001` manager has now reviewed
and confirmed that amendment during the 2026-07-28 recovery. This confirmation
did not grant a Candidate `Pass`; the later exact decision is recorded
separately in `CANDIDATE_EVIDENCE_2026-07-28.md`.

## 5. The finding that produced a new gate

`identity.py` now enforces that the issuer presented in the Easy Auth
principal equals `PEERSLATE_AUTH_ISSUER`. The upstream branch shipped this
with a test comment asserting *"Production currently leaves this unset; the
change must be inert then."*

That was false. The `peerslate-pete` App Service defines
`PEERSLATE_AUTH_ISSUER`, so the enforcement was live on deploy, not inert.

The setting had never been validated against reality, and could not have
been: until this change it was only a fallback used when a principal carried
no issuer claim, so a wrong value had no observable effect. Making it
load-bearing meant a mismatch would refuse **every** member's sign-in, with no
test able to detect it because the test environment supplies its own value,
and no staging App Service to catch it because `peerslate-candidate` no longer
exists.

The value was read from production before merge and matched exactly:

```
https://peerslatemembers.ciamlogin.com/b6cac548-9b4b-43da-b366-e95be960ec2f/v2.0
```

It was correct. It was also unverified, and the release would have shipped
either way. Pete directed that the general case become a gate; it is recorded
as a Gate Candidate automatic blocker under "Newly load-bearing
configuration" in `docs/initiatives/PS-OPS-001/README.md`.

## 6. Incident and recovery state

Azure PR 190 squash-merged the original package at
`e07c6a0f4085de92b1181678ad5e30ac2c1ce971`. Pipeline 259 deployed it, then
failed its production-smoke stage after the application could not boot.
Azure PR 191 reverted the complete package at
`89a619a560f04ec3763016939361f64516aac6bf`; pipeline 260 passed and restored
production.

The current recovery branch reverses that revert and then removes:

- `Flask-Compress==1.24` and `brotli==1.2.0`;
- the `flask_compress.Compress` import and all `COMPRESS_*` configuration; and
- compression-only test imports and cases.

Recovery reconstruction commit:
`306840985fa781b676b1aa56fb66d8480410b036`. Compression-removal and safe
implementation tip: `16c656140d0b697eac803df5fa82b31e3feb4557`.

The fresh independent review failed the original pushed recovery
`3d507e7f5f32299648153abbd00ae915825219c5` for an issuer-claim bypass, a
stale Candidate branch selector, cacheable member/session/API responses, a
cacheable identity-personalized Slate Board, and one inaccurate evidence
claim. The current candidate corrects all six findings and passes the full
local suite.

Azure pipeline 261 is diagnostic only: Build and CandidateDeploy passed, its
CandidateSmoke failed because the newly recreated app initially lacked the
non-secret `SCM_DO_BUILD_DURING_DEPLOYMENT=true` platform flag, and
CandidateStop passed. The flag and its `PS-OPS-001` documentation are now
corrected.

The fresh reviewer passed exact corrected
`a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`. Azure build 262
(`20260728.4`) then passed Build, CandidateDeploy, CandidateSmoke, and
CandidateStop; both production stages were skipped and the Candidate App
Service was stopped. Gate Candidate is `Pass`.

Azure PR 192 then squash-merged the recovery at
`9445d63f12067997395206a8cfb504013c247158`. Automatic pipeline 263
(`20260728.5`) passed Build, production Deploy, and exact public-boundary
smoke. Independent live checks confirmed release
`524cb04dc5b5aa82a58c8b2a`, canonical routes, security/cache headers,
cross-site refusal, and immutable current assets. The temporary Candidate App
Service and separate B1 plan were removed after production verification.

## 7. Evidence

See `OWNER_TECHNICAL_COMPLETION_REPORT.md` and
`CANDIDATE_EVIDENCE_2026-07-28.md` in this directory for the promotion gate.
See `PRODUCTION_EVIDENCE_2026-07-28.md` for the exact merge, production
pipeline, live verification, and cleanup record.

Recovery reference for the removed DOCX files: Azure tag
`archive/2026-07-27/superseded-governance-docx` at
`1231ba44dec4ca9e26a3d92bb7c96b63aa975c2d`. All twenty-seven DOCX present
before the removal are recoverable from that commit's tree.

## 8. Follow-ups this package does not close

- `CURRENT_BASELINE.yaml` records
  `interview_studio_asset_signature: "studio-5a5c-4"`. No code references it
  now that static versioning is automatic; the record is orphaned. Owned by
  the lane holding that file.
- `CURRENT_STATE.md` still describes `PS-COMMUNITY-TABS-001` as unmerged. It
  is live in `app.py`. Owned by the lane holding that file.
- Response compression remains deferred. Do not reintroduce Flask-Compress,
  Brotli, zstd, or another compression library without production-like runtime
  proof and a separate bounded package.
- Rate limiting remains in-memory per worker. Correct keying does not make it
  correct across instances; Redis-backed storage is still the documented
  production answer and is untouched here.
