# PS-AUTH-001 — Azure Auth Diagnosis Checkpoint

**Date:** 2026-07-16
**Session role:** Coordinator / diagnostician for remaining Azure auth configuration (no code redesign, no PS-OWNER-001).
**Method:** Read-only Azure CLI inspection + browser tests. Nothing was changed.

---

## HEADLINE

**The reported blocker is RESOLVED.** Azure App Service Authentication ("Easy Auth") with
Microsoft Entra External ID now correctly intercepts `/.auth/login/aad` on **both** the default
Azure hostname **and** `peerslate.com`, and redirects to the PeerSlate Members sign-in page.

The earlier symptom (Flask 404 at `/.auth/login/aad`, "Sign in is not configured yet" at `/app`)
was almost certainly a **pre-activation timing issue** — those tests were run before the Microsoft
identity-provider configuration finished saving/activating. It is active now.

**Status: PS-AUTH-001 = CONDITIONAL** (unchanged). The infrastructure works, but no live sign-in
has completed yet, so it is not COMPLETE.

---

## WHAT WAS INSPECTED (read-only)

- `az account show` — confirmed active subscription/tenant
- `az webapp list` — found the app, resource group, default hostname, run state
- `az webapp auth show` — full Easy Auth configuration
- Browser: `GET /.auth/login/aad?post_login_redirect_uri=/app` on both hostnames

## WHAT WAS CONFIRMED (evidence)

| Item | Value |
|---|---|
| Subscription | Azure subscription 1 — `bd0ecf48-6940-4fd3-9687-3eaf72469d67` |
| Tenant (hosting) | Default Directory — `93892ed5-b7f5-472a-b78b-1be9bc57a7d2` (`peerslate19gmail.onmicrosoft.com`) |
| App Service | `peerslate-pete` — **Running** |
| Resource group | `peerslate` |
| Default hostname | `peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net` |
| Easy Auth enabled | **true** (configVersion v2) |
| Identity provider | Microsoft / Entra External ID |
| Issuer | `https://peerslatemembers.ciamlogin.com/b6cac548-9b4b-43da-b366-e95be960ec2f/v2.0` |
| Client ID | `a3f7a4d3-67c1-4c86-8653-dca3de75c99a` |
| Client secret setting | `MICROSOFT_PROVIDER_AUTHENTICATION_SECRET` (name only — value never exposed) |
| Token store | enabled |
| Unauthenticated action | **AllowAnonymous** (correct — public pages stay public) |
| Allowed client apps | `[a3f7a4d3-...]` (itself) |

### Browser test results
- **Default hostname** → `/.auth/login/aad` redirected to the External ID sign-in page.
  Callback = `…azurewebsites.net/.auth/login/aad/callback`. Title: "Sign in to your account". ✅
- **peerslate.com** → `/.auth/login/aad` redirected to the External ID sign-in page.
  Callback = `https://peerslate.com/.auth/login/aad/callback`. Title: "Sign in to your account". ✅

## WHAT CHANGED

**Nothing.** All actions were read-only. No Azure settings, no app registration, no code modified.

## WHAT WAS DELIBERATELY NOT DONE

- Did **not** complete a sign-in or create an account (that is Pete's acceptance test; entering
  credentials / creating accounts is out of scope for the agent).
- Did **not** configure Google (email/password must work end-to-end first).
- Did **not** begin PS-OWNER-001.
- Did **not** modify app code or Azure config.

## WHAT REMAINS UNKNOWN (must be tested live)

1. Whether email/password **sign-up** completes and returns Pete to `/app`.
2. Whether the app registration has **peerslate.com's callback** registered as a redirect URI.
   If not, sign-in from the custom domain may fail with **AADSTS50011 (redirect URI mismatch)**.
   The default-host callback is usually auto-registered; the custom-domain callback often must be
   added manually. **This is the most likely next gotcha.**
3. Whether, after sign-in, the Flask app reads the identity (`X-MS-CLIENT-PRINCIPAL`) and shows
   `/app` instead of the "Sign in is not configured yet" fallback.
4. Returning sign-in maps to the **same** internal PeerSlate UUID.
5. Two-user isolation (Pete vs Danielle — separate UUIDs, no cross-access).

---

## RESUME ON THE MAC — do these in order

1. **Pull latest from Azure** so the Mac has PS-AUTH-001 (PRs 50 & 51):
   `git pull origin main`
2. **First live acceptance test:** open `https://peerslate.com/app` (or the sign-in URL),
   create Pete's email/password account, and see whether you land on `/app`.
   - If you hit **AADSTS50011 / redirect mismatch** → add
     `https://peerslate.com/.auth/login/aad/callback` (and the `www` variant if used) to the
     app registration's **Redirect URIs** in the PeerSlate Members tenant (portal or Codex/CLI).
   - If sign-in succeeds but `/app` still says "Sign in is not configured yet" → the Flask app
     isn't reading the Easy Auth identity headers; investigate the identity code + any config flag.
3. **Record results** against the acceptance-test checklist in the handoff.

---

## CROSS-MACHINE NOTES

- **GitHub remote is currently flagged.** Azure DevOps (`origin`) is the working source of truth
  and is up to date. The "push everything to GitHub" step is on hold until the flag clears.
- This PC has **untracked, local-only files** not in git and will NOT travel to the Mac unless
  committed + pushed: mockup PNGs under `static/images/mockups/`, and
  `artifacts/2026-07-14-resume-consolidation/`. (Not needed for the auth task.)
- The ~168 "modified" files git reported on this PC were **line-ending noise (CRLF vs LF), not real
  edits** — confirmed identical content. No real work is uncommitted from this PC.
