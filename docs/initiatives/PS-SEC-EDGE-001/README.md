# PS-SEC-EDGE-001 - HTTP edge security, deployment package, and static asset delivery

**Owner:** Pete
**Package-designated session manager:** Claude Code, self-managed under the
2026-07-24 owner decision recorded in `CLAUDE.md`
**Writer:** Claude Code on `work/2026-07-27-web-architecture-audit-001`
**Base:** Azure `origin/main` at
`141273fe51c0ac3c35e4ab15d96e34524b674d68`
**Upstream source:** the ad-hoc cloud session branch
`claude/website-architecture-audit-7l52z6` (GitHub mirror only), built on
`be7f857`, reconciled onto current Azure `main` in this package
**Status:** Implementation complete; merged through Azure PR 190
**Visual authority:** Not applicable - no composition, hierarchy, typography,
colour, or responsive interaction model changes
**Runtime authority:** HTTP response edge, deployment packaging, and static
asset delivery only

## 1. Why this package exists

The work was produced by a cloud agent session as a website architecture
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

**Private response caching.** Every route on the owner blueprint returns one
signed-in member's own data. The application default (`no-cache,
must-revalidate`) forces revalidation but still permits a shared cache to
store the body and the browser to restore it from the back/forward cache,
which could redisplay one member's private capture or Journal after sign-out
on a shared device. The blueprint now defaults to `private, no-store`, and
routes that set an explicit policy keep it.

**Identity issuer assertion.** The issuer inside the Easy Auth principal is
part of the identity key and was treated as advisory. When
`PEERSLATE_AUTH_ISSUER` is configured it is now required to match. See
section 5 - this is the finding that produced the new Gate Candidate blocker.

Delivery work in the same package: the deployment package no longer carries
evidence, tests, or design material; text responses are compressed; static
CSS and JS carry an automatic content-hash version; a partial
Content-Security-Policy is enforced; and fifteen superseded Bible and Roadmap
DOCX files leave the working tree.

## 3. Explicitly out of scope

No product feature, route, schema, migration, feature flag, audience or
publication control, AI behaviour, member capability, or visual design. No
change to authentication providers, App Service settings, DNS, monitoring, or
secrets. No enablement of any default-off capability.

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
section 5. The `PS-OPS-001` lane table entry still reserves that package's
governance records to the ChatGPT Work/Codex task on
`work/2026-07-26-responsive-site-audit-001`, a branch that has since merged
and been deleted from Azure. The `PS-OPS-001` manager should confirm the
amendment rather than treat it as a silent cross-lane edit.

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

## 6. Evidence

See `OWNER_TECHNICAL_COMPLETION_REPORT.md` in this directory.

Recovery reference for the removed DOCX files: Azure tag
`archive/2026-07-27/superseded-governance-docx` at
`1231ba44dec4ca9e26a3d92bb7c96b63aa975c2d`. All twenty-seven DOCX present
before the removal are recoverable from that commit's tree.

## 7. Follow-ups this package does not close

- `CURRENT_BASELINE.yaml` records
  `interview_studio_asset_signature: "studio-5a5c-4"`. No code references it
  now that static versioning is automatic; the record is orphaned. Owned by
  the lane holding that file.
- `CURRENT_STATE.md` still describes `PS-COMMUNITY-TABS-001` as unmerged. It
  is live in `app.py`. Owned by the lane holding that file.
- `Flask-Compress==1.24` pulls `backports.zstd` transitively. It is not
  pinned in `requirements.txt`; pip resolves it. Worth an explicit pin if the
  package standard requires a fully pinned tree.
- Rate limiting remains in-memory per worker. Correct keying does not make it
  correct across instances; Redis-backed storage is still the documented
  production answer and is untouched here.
