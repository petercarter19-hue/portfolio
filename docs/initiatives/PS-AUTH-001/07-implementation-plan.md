# PS-AUTH-001 implementation plan

1. Keep public routes anonymous and add a protected `/app` owner route.
2. Trust App Service identity headers only behind an explicit production flag.
3. Require provider, issuer, and stable subject; reject malformed or oversized principals.
4. Add the identity migration after PS-PLAT-006 and PS-PLAT-007.
5. Provision one opaque account UUID, private profile, and opt-out discovery defaults in one SQL transaction.
6. Add two-user, returning-user, anonymous, logout, open-redirect, header, and pipeline tests.
7. Configure the external tenant and Google/email methods in Azure without committing credentials.
8. Verify Pete and Danielle in separate browser sessions before enabling database-backed owner features.

Rollback: disable `PEERSLATE_TRUST_EASYAUTH_HEADERS`, revert the application,
and use the reviewed migration rollback only before real identity mappings exist.
Once real accounts exist, preserve/export identity mappings instead of dropping them.
