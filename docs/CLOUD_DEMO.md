# Restricted fictional cloud browser demo

This runs the accepted onboarding pages in two independent cloud sites. Each
site has one restricted demo account, one server-owned fictional member and
its own process, password, sessions and saved snapshot. Grok and Muse can open
their site's HTTPS address in their own cloud browser. Pete's PC and browser
are not part of that connection.

Use fictional content only. The banner identifies cloud storage and unavailable
AI/speech. Type, upload a small document, edit manually, review and save a
draft. The existing application separates proposals, explicit confirmation,
private preview and deliberate publication. Files are limited to 4 MB and the
whole fictional snapshot to 16 MB for the existing small hosting plan. Private
preview and publishing remain inside the authenticated demo.

To start a fresh test, sign in and select **Reset this demo** from the fictional
Resume page. Review the confirmation and select **Reset this demo** there. The
site saves a recovery checkpoint before clearing its own fictional content.
The other demo, its password and the current sign-in are unaffected. A stale
confirmation is refused if content changed; open the reset page again. Recovery
of a prior checkpoint is an operator task, not a browser action.

Authentication uses a dedicated password hash and opaque expiring server-side
session. Host, origin and mutation checks apply before dispatch. Client identity
headers, fixture selector cookies and owner query selectors refuse. The wrapper
supplies the fictional principal only after authentication; Microsoft/Tailscale
and production identity are not inherited. A failed save restores the previous
in-memory state and preserves the last complete snapshot before responding.
Corrupt or incompatible saved state refuses startup; it never resets. A lifetime
file lock prevents a second writer process. Deploy one process/instance per site.

The fixture drops inherited environment credentials and refuses external sockets,
SQL and real provider transports. Upload bytes and typed state persist only in
the dedicated cloud snapshot. No private PC configuration, state, signing key,
provider allocation or accounting database is packaged or copied.

## Release operator

Use the owning registered package worktree and its normal Protected review/CI.
Commit the acceptance plan before implementation. `scripts/cloud_demo_release.py
package --source <exact-sha> --output <allocated-evidence-directory>` builds a
deterministic artifact from tracked Python, templates, static resources and the
required fixture code. Product code is nested under `source/`; there is no
unguarded root `app.py` fallback. Dependencies are exact source requirements plus
the pinned dedicated waitress overlay. `validate --manifest <json>` checks the
complete source inventory, file hashes, dependency overlay and dedicated startup.

After independent review, current-target CI and accepted merge, `bind-accepted
--source <accepted-sha> --manifest <frozen-candidate-json>` verifies every packaged
file against accepted Git and binds the same frozen archive without duplicating it.
Deployment requires accepted
Git ancestry, original independent receipt, reviewed code equality and an operator
identical to accepted source. Pass `deploy --manifest <json> --target grok|muse`.
Each deployment records its intent before ARM/ZipDeploy effects and refuses replay
of the same uncertain attempt. Creation/configuration occurs only on the fixed
existing Linux B1 plan, using explicit subscription arguments; no new plan or scale.
Production and the stopped candidate are verified and never changed.

The main site stays behind a deny-all Azure access restriction while its exact
package builds. The Linux app is enabled and started only after its dedicated
startup, fictional authentication settings and separate authenticated SCM access
are configured and verified. This lets Azure accept the upload without opening
the demo before deployment succeeds. `deployment-status
--target <target>` reads the actual build. `start --manifest <json> --target
<target>` requires the recorded successful request, its exact remote deployment
ID, unique completed successful build and actual source/owner setting. Missing
identity refuses start and keeps the main site blocked; a timestamp alone cannot
qualify a different build. Only a qualified `start` removes the deployment access
restriction after restarting the Linux container to load the completed package.
For reset-control updates, the operator requires both existing sites with their
original ownership tags and reuses their existing owner-local credential vault.
It cannot create a replacement site or issue new demo passwords. Before writing
a deployment intent or stopping either site, it compares the active site's
credential and namespace settings with that vault and refuses any mismatch.
Verify certificate-checked HTTPS, protected
routes, wrong/anonymous identity, two-site separation and ordinary browser paths.
Measure actual plan memory/CPU before admitting the second site. Stop new sites on
auth, state, capacity or release-identity failure; retain snapshots and artifact.
Never casually cancel an in-progress Oryx build or retry an uncertain deployment.

`stop --target <target>` is the initial release's rollback to unavailable access,
with data and artifact preserved. There is no pre-existing cloud release to claim
as a tested rollback target. `restart --manifest <json> --target <target>` retains
the same state/namespace; a compatible exact-source redeploy must also retain it.
Do not replace corrupt state with an empty fixture or rewind a saved generation.

## Credentials and receiver instructions

Passwords and signing keys are generated only in the owner's authorized Windows
environment. They are stored under `%LOCALAPPDATA%/PeerSlate/CloudDemo/` with owner
and SYSTEM access, encrypted using user-bound Windows DPAPI. Cloud settings contain
the password hash and signing key; no password appears in source, evidence, logs or
handoff text. To see/copy your demo credentials privately, run
`scripts/cloud_demo_release.py show-credentials --target grok|muse` using the
private Python runtime. The native dialog masks the password and copies it only
when you click its button. Paste sign-in directly into the receiving browser.

The final release evidence supplies the actual verified platform HTTPS URLs.
Give each receiver only its own URL/account credentials and this instruction:

> Use your own cloud computer and its browser to open the supplied PeerSlate
> fictional demo URL. Sign in with the separately supplied demo credentials.
> Use only fictional content. Check Type, a small text-file upload, manual editing,
> draft save and reload, and private preview. Keep proposals separate from facts;
> ask Pete before canonical confirmation, publishing or deletion. AI/speech inside
> this demo are unavailable; the manual editor should remain useful. Report the
> actual URL, routes, visible result and any browser/network limitation. Never use
> Pete's desktop browser or production/personal site.

Pete starts and signs into the vendor service. A successful deployment or local
test does not prove Grok/Muse connection; those actual sessions must verify it.
