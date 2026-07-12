# PeerSlate SQL Foundation Plan v0.1

**Status:** Implemented as additive migration scripts; production execution requires the verification sequence below
**Date:** July 12, 2026
**Scope:** Site-wide data foundations only; no page-specific Resume, Slate Board, Feed, Interview, or recruiter schema

## 1. Purpose

PeerSlate already has a useful Azure SQL foundation for authenticated users, the Break Feed, saved boards, polls, challenges, journals, Slate Spaces, progress, achievements, and badges. The next database work must support the product as a multi-user, evidence-backed platform without coupling the schema to one page or to Pete's fixture content.

This plan adds the shared trust and relationship layer required by future product features:

- repeatable migration history;
- immutable security and administrative auditing;
- member profiles separated from authentication identities;
- stable cross-product entity identifiers;
- tenant-owned relationships and explicit access grants;
- publication snapshots and audience boundaries;
- evidence, provenance, and protected file metadata;
- reviewable AI proposals;
- opt-in connections and user-safety controls;
- notifications and notification preferences.

## 2. Live baseline inventory

Read-only inspection of `peerslate-database` on July 12, 2026 found:

- 22 application tables;
- 200 columns;
- 31 foreign-key relationships;
- 39 indexes;
- 33 stored procedures;
- two check constraints, both for progress percentages;
- no migration ledger, audit table, profile table, publication model, evidence model, AI proposal model, connection model, consent model, asset registry, or notification model.

The current tables and procedures remain unchanged by these migrations.

## 3. Migration package

### PS-PLAT-001 — Governance

Adds:

- `dbo.schema_migrations`;
- `dbo.audit_events`;
- `dbo.usp_AppendAuditEvent`;
- an immutability trigger preventing ordinary update or delete operations on audit records.

Reason: later changes need a reliable execution ledger and a tamper-resistant record of sensitive actions.

### PS-PLAT-002 — Profiles, entities, access, and publication

Adds:

- `dbo.member_profiles`;
- `dbo.slate_entities`;
- `dbo.slate_entity_relations`;
- `dbo.entity_access_grants`;
- `dbo.entity_publication_versions`.

Reason: profile-owned records need stable ownership, consistent privacy, explicit sharing, and controlled publication across every PeerSlate experience.

`slate_entities` is a registry and relationship spine, not an entity-attribute-value content store. Page-specific fields remain in focused domain tables.

### PS-PLAT-003 — Evidence, files, and AI proposals

Adds:

- `dbo.file_assets` for metadata only;
- `dbo.evidence_items`;
- `dbo.evidence_links`;
- `dbo.ai_proposals`;
- `dbo.ai_proposal_changes`.

Reason: evidence must retain provenance and visibility, while AI output must remain a reviewable proposal rather than an automatic edit.

Binary files remain outside SQL in protected object storage. SQL stores ownership, storage references, checksums, scan state, and access metadata.

### PS-PLAT-004 — Connections, safety, and notifications

Adds:

- `dbo.connection_preferences`;
- `dbo.connection_requests`;
- `dbo.member_connections`;
- `dbo.user_blocks`;
- `dbo.user_reports`;
- `dbo.notifications`;
- `dbo.notification_preferences`.

Reason: matching must be opt-in and visibility-aware, nobody may be auto-connected, and block/report controls must exist before cross-user discovery becomes real.

### PS-PLAT-005 — Tenant integrity

Adds composite ownership constraints across entity relations, evidence, protected assets, and AI proposal targets.

Reason: a normal foreign key proves that a record exists. The composite constraints additionally prove that linked records belong to the same profile, preventing accidental cross-tenant relationships at the database boundary.

## 4. Trust rules enforced in SQL

- Every profile-owned row points to a tenant-owned profile or user.
- New profiles and entities default to private.
- AI proposals default to `proposed` and cannot represent an approved or published edit by themselves.
- Connection discovery defaults off.
- Connection requests require explicit acceptance before a connection record exists.
- Publication has a separate version record and audience.
- JSON-bearing columns reject invalid JSON.
- Visibility, status, access, evidence, scan, connection, report, and notification values use check constraints.
- Stable public-facing keys use UUIDs while internal joins use numeric keys.
- Foreign-key and tenant lookup paths receive supporting indexes.
- Audit records are append-only.

## 5. Intentionally deferred

These remain page or capability-specific and should be designed when their contracts are approved:

- Living Resume experiences, education, credentials, projects, achievements, skills, and timeline tables;
- Slate Board note presentation fields beyond the current tables;
- Interview sessions, recordings, coaching scores, and retakes;
- feed ranking and recommendation models;
- recruiter searches and saved candidate lists;
- messaging, teams, and organization accounts;
- billing and subscriptions;
- production file-storage containers and malware-scanning integration;
- AI model orchestration and prompt content.

## 6. Deployment and rollback sequence

Forward order:

1. `PS-PLAT-001_platform_governance.sql`
2. `PS-PLAT-002_profiles_entities_access.sql`
3. `PS-PLAT-003_evidence_ai.sql`
4. `PS-PLAT-004_connections_notifications.sql`
5. `PS-PLAT-005_tenant_integrity.sql`
6. `peerslate_platform_foundation_verify.sql`

The repository helper prints the plan by default and applies only with an explicit flag:

```powershell
python -m pip install -r requirements-sql.txt
python scripts/apply_sql_migrations.py
python scripts/apply_sql_migrations.py --apply
```

`requirements-sql.txt` is operational tooling only. It is separate from the web application's production dependency file and is not installed by the deployment pipeline.

Rollback is the reverse order and must not be used after application code begins writing production data without an export and reviewed retention decision.

Each forward script:

- uses `XACT_ABORT` and an explicit transaction;
- performs compatibility preflight checks;
- is idempotent for matching objects;
- records its stable migration ID;
- appends an audit event after governance is installed.

## 7. Verification gates

Before production application code uses these tables:

1. Run all four migrations against the configured Azure SQL database.
2. Run the read-only foundation verification script.
3. Confirm all migration IDs are present exactly once.
4. Confirm every new foreign key is trusted.
5. Confirm all check constraints and required indexes exist.
6. Confirm audit update/delete attempts fail inside a rollback-only test.
7. Confirm profile tenant A cannot be referenced by tenant B procedures when those procedures are introduced.
8. Run the Flask unit and security test suite.
9. Keep current database-backed UI flags unchanged until corresponding APIs are deliberately implemented.

## 8. Application impact

The migrations are additive and do not change current routes, templates, CSS, JavaScript, existing stored procedures, or existing table definitions. Current webpages continue to use their existing fixture and database paths. The new tables have no visible effect until future backend code explicitly reads or writes them.
