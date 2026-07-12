# PeerSlate Remaining Operations Plan v0.1

**Status:** Review required before production or schema changes
**Date:** July 10, 2026

## 1. Purpose

This plan covers the work that cannot be safely completed through local application code alone: production authentication, administrator content tools, test-data reset, repeatable migrations, production deployment, and the PS-FEAT-001 structured career model.

No item in this document has been executed against production.

## 2. Production Authentication Gate

1. Configure Azure App Service Authentication with the approved identity provider.
2. Require authentication for member routes.
3. Confirm the application cannot be reached through a path that bypasses Easy Auth.
4. Verify `X-MS-CLIENT-PRINCIPAL` contains a stable subject claim, email, and display name.
5. Confirm `usp_UpsertAppUserFromAuth` returns one tenant-owned `user_key` per provider subject.
6. Test first sign-in, repeat sign-in, changed display name, disabled user, and missing-claim behavior.
7. Verify one member cannot retrieve or mutate another member's data.

## 3. Admin Content Tools Gate

Do not create an admin UI that writes directly to `content_items`, `poll_options`, `challenge_details`, or `daily_feed_cards`.

Required first:

- approve admin roles and assignment policy;
- add stored procedures for listing, creating, updating, activating, and deactivating content;
- add an audit table and immutable audit procedure;
- define validation for each content type;
- define preview and publish scheduling behavior;
- require server-side `user_role='admin'` authorization on every admin route;
- add CSRF, rate limits, and re-authentication for sensitive actions.

Only after those contracts are reviewed should an alternate, non-navigation admin route be built.

## 4. Test Data and Seed Gate

Before creating a reset script, inventory every foreign key referencing `app_users`, `content_items`, `user_boards`, `slate_spaces`, and `slate_items`.

The reviewed reset procedure should:

1. accept only an explicitly allowed fixture key such as `test-user-1`;
2. reject production-shaped identities;
3. run in one transaction;
4. delete child records in foreign-key order;
5. reseed fixture data idempotently;
6. report row counts before and after;
7. support a dry-run mode;
8. require an environment guard proving development or staging.

Shared feed seeds must remain separate from member-owned fixture activity.

## 5. Migration Process Gate

Every migration should include:

- a stable migration ID and description;
- preflight existence and compatibility checks;
- forward SQL;
- rollback or restore strategy;
- transaction boundaries;
- idempotency behavior;
- expected row-count and object-count changes;
- backup/export confirmation;
- development verification before staging;
- explicit approval before production.

Maintain a schema-migrations ledger rather than relying on manual Query Editor history.

## 6. PS-FEAT-001 Migration Proposal

The Living Resume blueprint is still **Validated**, not **Ready**. Before SQL creation, approve the exact data contract for:

- profiles;
- experiences;
- education;
- credentials;
- projects;
- achievements;
- skills and skill links;
- evidence items and provenance;
- timeline events;
- AI suggestions;
- private voice drafts and approval history.

Every owned row must include a tenant key, stable identifier, visibility, approval state, timestamps, and source/provenance fields. Voice drafts default to private. Publishing remains a separate action.

Required migration review artifacts:

1. entity relationship diagram;
2. column-level data dictionary;
3. index and uniqueness plan;
4. tenant-isolation test matrix;
5. visibility and publication transition rules;
6. retention policy for transcript and proposed wording;
7. six stress-test fixture profiles;
8. rollback and backup plan.

## 7. Azure App Service Deployment Gate

Deployment remains prohibited until separately approved.

Before deployment:

- add `AZURE_SQL_CONNECTIONSTRING` as an App Service setting or adopt managed identity after review;
- enable Easy Auth and require authentication;
- keep development identity and temporary test-route flags off;
- decide whether `PEERSLATE_DATABASE_UI_ENABLED` is ready for the target environment;
- configure production rate-limit storage;
- confirm Azure SQL networking permits only required paths;
- run the read-only health script;
- run unit, integration, tenant-isolation, accessibility, and mobile checks;
- verify logs contain no credentials or raw connection strings;
- prepare rollback to the previous application version.

## 8. Final Release Checklist

- [ ] Approved route and access map
- [ ] Approved identity provider and tenant policy
- [ ] Easy Auth configured and bypass tested
- [ ] Admin stored procedures and audit policy approved
- [ ] Seed/reset procedure reviewed in dry-run mode
- [ ] Migration ledger and backup process established
- [ ] PS-FEAT-001 data contract promoted from Validated to Ready
- [ ] Unit and integration tests pass
- [ ] Cross-tenant negative tests pass
- [ ] WCAG 2.2 AA checks pass
- [ ] Desktop and mobile screenshots approved
- [ ] Temporary test routes disabled
- [ ] Development identity disabled
- [ ] Secrets stored only in platform settings
- [ ] Deployment and rollback separately approved
