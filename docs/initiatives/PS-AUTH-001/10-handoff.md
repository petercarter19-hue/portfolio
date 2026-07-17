# PS-AUTH-001 handoff

## Implemented

- Real Sign In entry point, protected `/app`, session status, and same-origin sign out.
- Issuer-aware Easy Auth principal validation and server-side tenant scoping.
- Production identity schema and private first-account provisioning.
- Security headers, trusted hosts, request-size limits, and CI test gate.

## Requires Azure configuration

- Create/select the Entra external tenant and production app registration.
- Enable email and Google in its user flow.
- Configure App Service Authentication to allow anonymous public pages.
- Set the trusted-header flag and issuer only after the edge provider works.

No credentials belong in the repository. Do not enable the trust flag before
App Service is confirmed to inject and protect the identity headers.
