<!-- GENERATED FILE. Do not edit by hand. Regenerate with: python scripts/govern_sql_migrations.py report --expect-database <name> --write-state -->

# Production schema state: `peerslate-database`

This file is the repository's record of which schema migrations the named database carries. It is **generated from a live read of `dbo.schema_migrations`** by the governed migration path, never written by hand, and `--check-state` re-renders it and compares byte-for-byte. If you are reading a claim about database schema anywhere else in this repository -- a migration header, a completion report, a package README -- that claim is prose and this file is the record.

- Database: `peerslate-database`
- Server: `peerslate`
- Read at: `2026-08-05T02:47:47Z` UTC
- Pipeline source version: `879d0d715dc94dbc2adc4b832145264dc510342a`
- Pipeline build: `528`

## Applied (22)

In registry order.

| # | Migration | Applied (UTC) | Registered |
| --- | --- | --- | --- |
| 1 | `PS-PLAT-000` | 2026-08-04T13:54:12.8881482 | yes |
| 2 | `PS-PLAT-001` | 2026-07-12T17:20:58.0652279 | yes |
| 3 | `PS-PLAT-002` | 2026-07-12T17:20:58.1468095 | yes |
| 4 | `PS-PLAT-003` | 2026-07-12T17:20:58.2260809 | yes |
| 5 | `PS-PLAT-004` | 2026-07-12T17:20:58.3160277 | yes |
| 6 | `PS-PLAT-005` | 2026-07-12T17:23:05.8579613 | yes |
| 7 | `PS-PLAT-006` | 2026-07-17T00:04:22.6115748 | yes |
| 8 | `PS-PLAT-007` | 2026-07-17T00:04:22.6815521 | yes |
| 9 | `PS-AUTH-001` | 2026-07-17T00:05:49.0647696 | yes |
| 10 | `PS-CAPTURE-001` | 2026-07-17T19:47:26.5171866 | yes |
| 11 | `PS-CAPTURE-002` | 2026-07-18T19:49:37.9334478 | yes |
| 12 | `PS-MOMENT-001` | 2026-07-18T23:01:15.1212428 | yes |
| 13 | `PS-PLACEMENT-001` | 2026-07-19T00:29:34.8508893 | yes |
| 14 | `PS-VOICE-001` | 2026-07-19T13:17:12.7083616 | yes |
| 15 | `PS-CAPTURE-MEDIA-001` | 2026-07-20T02:28:44.3821451 | yes |
| 16 | `PS-HOME-001` | 2026-07-20T11:16:08.0376217 | yes |
| 17 | `PS-WORKSHOP-001` | 2026-08-02T15:29:49.9868441 | yes |
| 18 | `PS-OPPSLATE-001` | 2026-08-04T00:39:49.9854805 | yes |
| 19 | `PS-OPPSLATE-002` | 2026-08-05T02:47:45.8475524 | yes |
| 20 | `PS-COMMUNITY-PUBLIC-PILOT-001` | 2026-08-04T12:13:38.9428360 | yes |
| 21 | `PS-COMMUNITY-RETENTION-001` | 2026-08-04T12:13:39.0945281 | yes |
| 22 | `PS-COMMUNITY-RESTORE-001` | 2026-08-04T12:13:39.1616332 | yes |

## Registered but not applied (2)

| Migration | Gate proof | Summary |
| --- | --- | --- |
| `PS-JOURNAL-001` | **none or stale** | Derived private Journal read, idempotent Save Moment, and deterministic owner-authorized search. |
| `PS-PLAT-008` | **none or stale** | People and Interests feed domain. Never approved for any database; see the file header. |

## Machine-readable record

```json
{
  "applied": [
    {
      "applied_at_utc": "2026-07-17T00:05:49.0647696",
      "id": "PS-AUTH-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-17T19:47:26.5171866",
      "id": "PS-CAPTURE-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-18T19:49:37.9334478",
      "id": "PS-CAPTURE-002",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-20T02:28:44.3821451",
      "id": "PS-CAPTURE-MEDIA-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-04T12:13:38.9428360",
      "id": "PS-COMMUNITY-PUBLIC-PILOT-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-04T12:13:39.1616332",
      "id": "PS-COMMUNITY-RESTORE-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-04T12:13:39.0945281",
      "id": "PS-COMMUNITY-RETENTION-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-20T11:16:08.0376217",
      "id": "PS-HOME-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-18T23:01:15.1212428",
      "id": "PS-MOMENT-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-04T00:39:49.9854805",
      "id": "PS-OPPSLATE-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-05T02:47:45.8475524",
      "id": "PS-OPPSLATE-002",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-19T00:29:34.8508893",
      "id": "PS-PLACEMENT-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-04T13:54:12.8881482",
      "id": "PS-PLAT-000",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-12T17:20:58.0652279",
      "id": "PS-PLAT-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-12T17:20:58.1468095",
      "id": "PS-PLAT-002",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-12T17:20:58.2260809",
      "id": "PS-PLAT-003",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-12T17:20:58.3160277",
      "id": "PS-PLAT-004",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-12T17:23:05.8579613",
      "id": "PS-PLAT-005",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-17T00:04:22.6115748",
      "id": "PS-PLAT-006",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-17T00:04:22.6815521",
      "id": "PS-PLAT-007",
      "registered": true
    },
    {
      "applied_at_utc": "2026-07-19T13:17:12.7083616",
      "id": "PS-VOICE-001",
      "registered": true
    },
    {
      "applied_at_utc": "2026-08-02T15:29:49.9868441",
      "id": "PS-WORKSHOP-001",
      "registered": true
    }
  ],
  "database": "peerslate-database",
  "generated_at_utc": "2026-08-05T02:47:47Z",
  "pending": [
    "PS-JOURNAL-001",
    "PS-PLAT-008"
  ],
  "pipeline_build_id": "528",
  "pipeline_source_version": "879d0d715dc94dbc2adc4b832145264dc510342a",
  "registry_version": 1,
  "server": "peerslate",
  "unregistered_in_ledger": []
}
```
