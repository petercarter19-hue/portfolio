# B0 Preferences and consents taxonomy / schema-fit decision

**Package:** `PS-SETTINGS-PREFERENCES-TAXONOMY-001`
**Delivery path:** Protected, documentation only
**Authority checkpoint:** `origin/main` `91bd8056045f7c3da16088f3893c6f4237e9ac0e`
**Scope:** a decision record for a future Settings B1; it does not activate B1
or B1-F, add a control, or change runtime or data.

## Decision in one sentence

Settings must not turn every account fact, product rule, or consequential
operation into a toggle. Future optional preferences are feature-specific
behavior with a working enforcement path; contextual consent is a separately
versioned, affirmative event; audience, appearance, and lifecycle operations
keep their own product contracts.

## Taxonomy: what belongs where

| Class | Meaning | B0 decision |
| --- | --- | --- |
| Product rule or current status | A current truth that applies without a member choice, such as Private by default, an unavailable capability, or signed-in account facts. | Show truthfully when appropriate; do not represent it as a saved setting or generic consent. |
| True optional preference | A member-selectable choice whose scope, default, persistence, and server-side effect are known and testable. | May become a B1 control only after the entry criteria below are met. No control ships merely because a column exists. |
| Contextual, versioned consent | An affirmative decision for a defined feature action and purpose under the exact version of the wording presented at that action. | Keep it at the feature action, not in a general Settings switchboard. Record an event only after the feature has a complete signed-in write contract. |
| Permissions and audience | Who may discover, view, contact, or otherwise act on a member's content or profile, and the authorization consequences. | Not a generic Settings preference. It needs the owning audience/relationship product contract and server authorization. Private and audience values must not be exposed as generic toggles. |
| Appearance and theme | Presentation choice whose accessible variants and application lifecycle are defined. | Separate appearance work. Theme is not a B1 preference until a real supported theme behavior exists; no generic theme toggle now. |
| Lifecycle and data operations | Export, retention, deletion, account closure, or other operations with data, provider, and recovery consequences. | Separate protected operations, never a preference. No data-action control, schema work, or promise is created by B0. |

The existing Settings and My Data shell remains the source of current status:
Private by default is a product rule, preferences and consents are upcoming,
and account-wide export, deletion, and closure are not available today. This
record does not alter that product truth.

## Schema fit at the current checkpoint

`PS-PLAT-004` is recorded as applied in
`docs/governance/PRODUCTION_SCHEMA_STATE.md` on 2026-07-12. That establishes
that the following database shapes exist; it does **not** prove a present
Settings behavior, a live notification system, or legal adequacy.

| Existing store | Current shape and observed runtime fit | B0 decision |
| --- | --- | --- |
| `dbo.user_consents` | History-shaped rows: `user_id`, `consent_code`, `policy_version`, `consent_status`, server-defaulted `recorded_at_utc`, optional `source_context`, and JSON-capable `evidence_json`. Its allowed status values are `accepted`, `declined`, and `withdrawn`; its history index is by user, code, and recorded time. No current Settings consent writer or reader was found. | **Conditionally reusable** as the one append-only signed-in consent ledger for future contextual feature consents. B1 must use insert-only event semantics; the table's existence alone does not enforce immutability, authorization, vocabulary ownership, evidence quality, or revocation effects. Do not create a second generic consent store. |
| `dbo.notification_preferences` | Per-`user_id` and `notification_type` rows with in-app/email flags and an optional quiet-hours pair. No governed notification-type catalog, notification-preference runtime, email sender, or quiet-hours evaluator was found. | **Not B1-ready; do not expose or repurpose now.** It can only be reconsidered with a feature-owned notification catalog and channel enforcement. Email toggles and quiet-hours controls are expressly excluded from B0 and B1 entry until that behavior exists. |
| `dbo.connection_preferences` | Per-user connection discovery/matching flags plus `discoverable_audience`, with constraints that couple private audience to disabled discovery flags. It is seeded by identity migration, but no current Settings runtime owns it. | **Not a generic preference store.** It is a future connection/audience authorization surface, to be evaluated with the relationship and audience domain. It must not supply generic Private, audience, or discovery toggles in Settings. |

The source evidence is the applied `PS-PLAT-004_connections_notifications.sql`
migration. Its values and constraints are architecture evidence only for this
documentation package; B0 makes no schema modification or data assertion.

## Future consent ledger contract

If a future signed-in feature needs a consent event, it must preserve one
canonical ledger: `dbo.user_consents` for that feature's consent history. The
feature still owns its action, copy, authorization, and effect; Settings does
not become the canonical source or a bulk-consent mechanism.

### Identity and authorization boundary

Before any consent write, the server must:

1. derive the signed-in principal from the authenticated server context, never
   from a form field, query value, client header, or caller-supplied user ID;
2. resolve that trusted principal's `user_key` server-side to the corresponding
   `dbo.app_users.id`, and fail closed when the mapping is missing, inactive,
   or otherwise not a single authorized account;
3. authorize the feature action for that resolved account and compute the
   ledger `user_id` on the server; and
4. insert the event through a narrow, feature-authorized write path that does
   not let the caller select another account, code, version, status, or
   evidence payload.

No future feature may treat an authenticated browser claim as sufficient to
write an arbitrary `user_id`, or trust the client to identify the policy
version it saw.

### Vocabulary, evidence, and withdrawal semantics

No consent code is activated by B0. A future feature must register a bounded,
feature-scoped vocabulary before it writes. A code names one concrete purpose,
for example `<feature>.<specific-purpose>`; broad names such as `settings`,
`privacy`, `email`, or `all_features` are not an acceptable substitute for a
purpose. Each code has an owning feature, a purpose, a permitted status set,
and a documented effect for accept, decline, and withdrawal.

`policy_version` identifies the immutable version of the exact feature wording
shown to the member. The server selects and stamps that value. A changed
purpose or material wording change requires a new version rather than
overwriting history.

`evidence_json`, when used, is minimized server-produced evidence: the
registered code/version, feature surface or source context, affirmative action,
server receipt time or correlation identifier, and any versioned display
reference needed to reproduce what was presented. It must not become a dump of
credentials, raw identity claims, or unnecessary member content. The event
timestamp remains server-recorded; client-provided timestamps and proof are
not authoritative.

`withdrawn` means a member has rescinded an earlier accepted instance for the
same feature purpose. It is a new ledger event, never an update or deletion of
the earlier event. The future feature must define and enforce its prospective
effect before offering withdrawal: what behavior stops, what already-completed
processing cannot be reversed, and the truthful member message. `declined` is
not an accepted consent; if it is recorded, it is likewise an event and never
a default inferred from silence. These recording rules are product and
engineering requirements only; they do **not** claim legal sufficiency,
retention adequacy, or a particular jurisdictional interpretation.

## Existing feature-scoped precedent

`PS-ASK-PETE-DIRECT-001` demonstrates the property B1 should preserve without
creating a cross-feature abstraction: the feature owns a server-stamped,
versioned consent value (`ask-pete-direct-consent.v1`), requires an exact
affirmative value before storage, and independently enforces that boundary in
its procedure. It is an anonymous/public interaction with its own storage
contract, not a `dbo.user_consents` implementation and not authority to copy
its shape into every feature. The relevant precedent is feature scope,
server-selected versioning, affirmative action, and defense in depth.

## B1 entry criteria

B1 may be activated only with a new exact owner outcome and claim after all of
the following are true for the selected, narrow feature:

1. The owner has identified one real optional behavior or contextual action,
   its default, its member-facing purpose, and why it is neither a product rule
   nor a lifecycle operation.
2. The owning feature has working server-side behavior to enforce the choice;
   a stored value without an effect is insufficient.
3. The feature has a controlled vocabulary, exact displayed wording/version,
   source context, evidence minimization policy, and explicit accept/decline/
   withdrawal effect.
4. Signed-in identity is derived and resolved server-side from `user_key` to
   `app_users.id`, with authorized negative paths and no caller-selected
   account or policy metadata.
5. A read/write contract preserves the applicable canonical store and proves
   append-only history for `user_consents` when consent is involved.
6. The relevant schema-fit decision is revalidated against current migration
   and runtime evidence. `notification_preferences` additionally needs a
   governed type catalog, in-app/email channel behavior, a sender where email
   is offered, quiet-hours/time-zone evaluation where applicable, and tests.
7. Audience/connection work is separately defined with relationship and
   authorization owners; appearance work is separately defined with accessible
   rendered behavior; lifecycle/data operations have their own protected
   authority and operational proofs.
8. Protected review plans cover authorization, cross-account refusal,
   version/evidence integrity, truthful unavailable behavior, and a rollback
   path. The claim must still withhold deployment and production operations
   unless separately authorized.

## Decisions still required

This record deliberately leaves these decisions to Pete and, where applicable,
privacy, legal, security, accessibility, and operational professionals:

- which future feature actions need consent rather than a product rule,
  contract notice, or ordinary optional preference;
- the approved vocabulary owner, member wording, versioning and evidence
  retention policy, and which withdrawal effects are feasible and truthful;
- notification categories, channel policy, sender/provider, quiet-hours time
  zone semantics, delivery failure behavior, and whether any member control is
  appropriate;
- the relationship/audience product model before any discovery or audience
  state is surfaced;
- supported theme choices and accessibility behavior before appearance can be
  persisted; and
- the retention schedule, provider commitments, export, deletion, and account
  closure contracts before any lifecycle/data operation is offered.

## Explicit exclusions and rollback

B0 adds no UI, route, runtime, service, test behavior, data or provider call,
schema/migration, configuration, dependency, deployment, enablement, email
toggle, quiet-hours control, generic Private/audience/theme toggle, or B1/B1-F
activation. It changes no existing consent precedent. Rollback is a repository
revert of this documentation record and its paired completion report; there is
no data, schema, or production rollback.
