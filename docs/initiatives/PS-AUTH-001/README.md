# PS-AUTH-001 — External identity

**Status:** Application and SQL foundation implemented; Entra External ID provider configuration pending.

## Accepted slice

- Microsoft Entra External ID through Azure App Service authentication.
- Public pages remain anonymous; `/app` is the protected owner route.
- Server-derived issuer and subject map to one opaque PeerSlate account UUID.
- New accounts receive a private profile and discovery defaults off.
- Returning sign-in resolves to the same account; different identities stay separate.
- Sign-in, sign-out, unavailable, malformed identity, and two-user paths are tested.

## Explicit boundary

Google and email are sign-in methods inside the external tenant. Google Drive,
Photos, GitHub, or other source access requires separate later consent and is
not part of authentication.
