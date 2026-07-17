# Decisions

## D1 - Follow the actual user-key contract

Use `@UserKey nvarchar(300)`, matching `app_users.user_key`, identity service,
and existing procedures. The onboarding brief's `uniqueidentifier` type would
break the current auth contract.

## D2 - Capture is canonical private intake

The capture row owns the authoritative source text. Later placement must
reference it; this package does not create Journal entries or destination
copies.

## D3 - No session/flash dependency

Validation and success redirects use fixed `error`/`saved` tokens that map to
server-owned text. This provides accessible feedback without adding a Flask
session secret only for this route or reflecting user text into the URL.

## D4 - Prove isolation in SQL

Mocked route tests verify application calls, not row-level database behavior.
The release verification therefore creates two synthetic owners and captures,
calls the real list procedure for each, asserts isolation/private state, and
rolls back the outer transaction.

## D5 - Atomic, body-free audit

Capture insert and audit event are one transaction. Audit metadata contains
type and visibility, never the body.

## D6 - Safe optional-migration runner

The runner uses an explicit allowlist and `--migration` selection, so applying
PS-CAPTURE-001 does not rerun the eight foundation files. Plan-only mode opens
no environment file or database connection.

## D7 - One length contract across browser, Flask, and SQL

HTML `maxlength`, SQL `nvarchar`, and the Flask guard all use the same 8,000
UTF-16 code-unit boundary. This avoids an emoji-heavy value passing Flask but
failing at persistence. The procedure independently rejects space, tab, and
line-break-only bodies.
