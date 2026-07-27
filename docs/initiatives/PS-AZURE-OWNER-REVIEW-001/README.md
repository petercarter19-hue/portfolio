# PS-AZURE-OWNER-REVIEW-001 — Azure Owner Systems Review

## Status

- **Package state:** Planned and deferred
- **Planning package:** Complete
- **Operational review:** Not started
- **Priority:** Low; no immediate action required
- **Owner:** Pete
- **Planning manager:** Pete-authorized Codex task
- **Planning writer:** Codex
- **Planning branch:** `codex/2026-07-26-azure-owner-review-001`
- **Authoritative base:** Azure DevOps `origin/main` at
  `646b664330e15c57650e1b4fd08e8fdcbaf9866c`
- **Reserved files:** `docs/initiatives/PS-AZURE-OWNER-REVIEW-001/**`

This package defines a later, owner-facing walkthrough of PeerSlate's Azure
systems. It exists so Pete can understand what is running behind the product,
how the pieces connect, where data goes, and how the system is operated.

It is deliberately **not** a pull-request, merge, deployment, or release gate.
It does not block current delivery. No recurring review cadence begins merely
because this planning package exists.

## Why this review exists

PeerSlate's product authority requires the owner to understand the system well
enough to make informed product, privacy, cost, and operating decisions. Normal
code review and deployment evidence prove that a bounded change works; they do
not necessarily make the complete Azure system legible to a first-time owner.

This review creates a calm, read-only learning session at a point when enough
of the system is real and stable to make the walkthrough useful. It complements
the existing technical checkpoint and full-site audit cadence. It does not
duplicate or replace security review, compliance work, deployment verification,
incident response, or acceptance of individual features.

## When to activate it

The recommended first activation is the next useful architecture phase
boundary after all of the following are true:

1. The private Journal core has been deployed and production-verified.
2. The Azure foundations it relies on are stable enough to review as one
   coherent system, including identity, application hosting, SQL data, Blob
   Storage, deployment, and monitoring.
3. A facilitator can prepare a current resource map without exposing secrets
   or private member content.

The review should occur before broad beta or launch, and before a later major
expansion makes the Azure topology substantially harder to learn in one
session. Pete may request it sooner at any time.

After the first review, repeat only at a meaningful architecture phase boundary
or after a material change to Azure topology, identity, security boundaries,
data lifecycle, deployment, recovery, or operating cost. Do not schedule it
per pull request or per feature slice.

## Activation rule

The future designated manager activates the review by completing the
activation record in
[`01_ACTIVATION_AND_WALKTHROUGH_TEMPLATE.md`](01_ACTIVATION_AND_WALKTHROUGH_TEMPLATE.md).
Activation must identify:

- the exact authoritative commit and deployed environment being reviewed;
- the current resource inventory and architecture evidence;
- the facilitator and attendees;
- the date and expected duration;
- any unavailable evidence or known uncertainty; and
- where the final owner notes and follow-up actions will live.

Activation is an owner-learning checkpoint, not permission to change Azure
resources. Any resulting infrastructure change needs its own assigned
initiative, scope, authority, tests, and release evidence.

## Review format

Plan for a 60–90 minute read-only screen-share walkthrough, supported by a
short pre-read. Use the Azure Portal, Azure DevOps, and current architecture
evidence only as needed to explain the system.

The facilitator should:

- begin with a one-page system map and a plain-language glossary;
- follow one representative member action from browser to storage and back;
- distinguish verified live behavior from fixtures, flags, plans, and
  inference;
- show names, purposes, relationships, health, and access boundaries without
  revealing secret values, tokens, connection strings, or private content;
- pause for owner questions and record answers or evidence gaps; and
- finish with the deployment, rollback, monitoring, recovery, and cost views.

The existing owner Control Room may be used as a supporting pre-read. It is not
a substitute for inspecting the authoritative Azure and Azure DevOps evidence.

## Walkthrough scope

The first review should cover only components that exist in the selected
environment:

1. **System map**
   - Azure subscription, resource groups, environments, regions, and naming
   - production versus non-production boundaries
   - which resources are live, planned, retired, or unknown
2. **Application runtime**
   - App Service or other compute, runtime configuration, deployment slots,
     health checks, scale settings, and feature flags
3. **Identity and access**
   - member sign-in, Entra External ID, sessions, managed identities, RBAC,
     administrator access, and least-privilege boundaries
4. **Azure SQL**
   - what canonical data belongs there, schema and migration flow, encryption,
     backup/restore, retention, and deletion responsibilities
5. **Blob Storage**
   - containers and their purposes, upload/download authorization, private
     access, lifecycle/retention, deletion, and recovery behavior
6. **Secrets and provider boundaries**
   - Key Vault or equivalent secret ownership, managed access, rotation
     responsibility, Speech/AI provider boundaries, and what data may leave
     PeerSlate
7. **Delivery and recovery**
   - Azure DevOps repository authority, pipeline stages, environments,
     approvals, deployment evidence, rollback, and incident ownership
8. **Observability**
   - Application Insights, logs, metrics, alerts, dashboards, health signals,
     diagnostic retention, and how failures are investigated
9. **Network and public edge**
   - domain, DNS, TLS, inbound/outbound paths, network restrictions, and any
     environment-specific exposure
10. **Cost and capacity**
    - major cost drivers, budgets/alerts, quotas, scaling risks, and the owner
      responsible for watching them
11. **End-to-end member data flow**
    - one representative flow across browser, identity, app, database, Blob
      Storage, providers, logs, and deletion/recovery paths

If a listed component does not exist, say so. Do not create it to make the
walkthrough appear complete.

## Required outputs

The activated review is complete when the durable review record contains:

- a current Azure resource and environment map;
- a verified end-to-end data-flow explanation;
- an identity, managed-identity, and RBAC ownership map;
- a data lifecycle, backup, restore, retention, and deletion summary;
- the deployment and rollback path;
- the monitoring, incident, quota, and cost overview;
- Pete's questions and the answers demonstrated during the session;
- every evidence gap or follow-up with an owner and target date; and
- the condition that should trigger the next owner review.

Mark each material assertion **Verified**, **Inferred**, or **Unknown**. Never
upgrade inference to verified truth without reproducible evidence.

## Review outcomes

Use one of these outcomes:

- **Owner-understood:** the planned walkthrough is complete and no material
  comprehension gap remains.
- **Follow-up required:** the walkthrough is complete, but named questions or
  evidence gaps need bounded follow-up.
- **Blocked by evidence gap:** the system cannot be explained responsibly
  because required authoritative evidence is missing or contradictory.

These outcomes describe owner comprehension. They are not security,
compliance, release, or production-health certifications.

## Privacy and safety boundaries

- Keep the session read-only unless another approved package explicitly owns a
  change.
- Never display or record secret values, tokens, credentials, connection
  strings, private member content, or unnecessary personal data.
- Use sanitized or synthetic examples for data-flow demonstrations.
- Do not treat portal visibility as authorization to change a resource.
- Do not report a resource, backup, alert, or data path as verified unless the
  exact selected environment provides reproducible evidence.
- Stop and escalate conflicting ownership, missing authority, unexplained
  production access, or an unexpected privacy/security boundary.

## Current exclusions

This planning package does not:

- inspect or modify Azure resources;
- change application code, configuration, pipelines, data, schemas, or access;
- register a merge or release policy;
- certify security, privacy, compliance, recovery, cost, or availability;
- begin the operational review; or
- reserve shared governance files.

Shared governance registration is intentionally deferred because another
active lane owns those mutable pointers. The future manager should register
this package in the then-current authoritative planning records when that
reservation clears and activation becomes timely. Until then, this directory
is the complete, bounded authority for the deferred review plan.
