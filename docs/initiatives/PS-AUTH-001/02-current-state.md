# PS-AUTH-001 current-state and security audit

Audit date: July 16, 2026. Baseline: Azure `origin/main` at `b41dc2460449606b799a958ab9be787df4173477`.

## PS-AUTH-F1 — External provider is not configured

- Rule ID: FLASK-PROXY-001 / PS-AUTH-001
- Severity: High
- Location: Azure App Service runtime; `auth_routes.py:25-78`
- Evidence: `https://peerslate.com/.auth/me` returned the Flask 404 page, while the Sign In control on the baseline was inert.
- Impact: Nobody can create or resume a real PeerSlate account.
- Fix: Configure App Service Authentication with an Entra external tenant, allow anonymous public traffic, then set `PEERSLATE_TRUST_EASYAUTH_HEADERS=true` and the expected issuer.
- Mitigation: The application fails closed and `/api/dashboard` returns 401.
- False positive notes: Recheck after Azure provider configuration; code alone cannot prove the edge setting.

## PS-AUTH-F2 — Legacy external identity was not issuer-aware

- Rule ID: PS-AUTH-IDENTITY-001
- Severity: High
- Location: `identity.py:91-151`; `SQL FIles/Migrations/PS-AUTH-001_identity_foundation.sql:57-263`
- Evidence: The baseline keyed `app_users` by provider plus subject and had no `user_identities` table or account UUID.
- Impact: Tenant issuers could collide, account linking could not be made explicit, and external identifiers leaked into the internal key.
- Fix: Implemented issuer + subject mapping, SHA-256 fingerprint uniqueness, opaque account UUIDs, and no email-based merge.
- Mitigation: Existing fixture users remain mapped as legacy identities.
- False positive notes: None; the production schema was inspected read-only before migration.

## PS-AUTH-F3 — First sign-in did not create privacy defaults

- Rule ID: PS-AUTH-PROVISION-001
- Severity: High
- Location: `SQL FIles/Migrations/PS-AUTH-001_identity_foundation.sql:180-263`
- Evidence: The baseline `usp_UpsertAppUserFromAuth` inserted only `app_users`.
- Impact: A new user could authenticate without receiving a tenant profile or opt-out discovery settings.
- Fix: Implemented transactional user, identity, private profile, candidate slug, and connection-preference provisioning.
- Mitigation: Database constraints keep profile visibility private and discovery off.
- False positive notes: None; the live two-user transaction test passed and rolled back.

## PS-AUTH-F4 — Deployment did not run tests

- Rule ID: FLASK-SUPPLY-001
- Severity: Medium
- Location: `azure-pipelines.yml:33-38`
- Evidence: The baseline pipeline installed requirements and packaged immediately.
- Impact: Authentication or tenant-isolation regressions could deploy to production.
- Fix: Implemented the full unittest gate before packaging.
- Mitigation: Azure deployment still requires successful Build.
- False positive notes: Pipeline execution must be confirmed after merge.

## PS-AUTH-F5 — No Content Security Policy

- Rule ID: FLASK-HEADERS-001 / JS-CSP-001
- Severity: Medium
- Location: `templates/base.html` and current production response headers
- Evidence: No CSP is emitted, and the site still contains numerous inline scripts.
- Impact: A future stored or DOM XSS defect would have a larger blast radius after private account data exists.
- Fix: Move inline scripts to static files, then deploy a nonce/hash-based CSP in a separate compatibility package.
- Mitigation: This slice adds trusted-host validation, `nosniff`, frame denial, referrer policy, permissions policy, HSTS, and bounded request bodies.
- False positive notes: Verify whether an Azure edge policy is later added; none was visible in the live response.

Official configuration basis: [Microsoft Entra authentication for App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-provider-aad) and [App Service authentication behavior](https://learn.microsoft.com/en-us/azure/app-service/overview-authentication-authorization).
