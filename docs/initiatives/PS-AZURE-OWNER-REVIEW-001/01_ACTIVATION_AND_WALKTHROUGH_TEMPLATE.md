# Azure Owner Systems Review — Activation and Walkthrough Record

Use this document when `PS-AZURE-OWNER-REVIEW-001` is activated. Copy it to a
dated evidence record inside this initiative package rather than overwriting
the template.

## 1. Activation record

- Activation date:
- Review date:
- Expected duration:
- Pete:
- Designated manager:
- Facilitator:
- Additional attendees:
- Authoritative repository and base commit:
- Deployed environment:
- Exact deployment/pipeline evidence:
- Reason this is the right phase boundary:
- Final evidence-record path:

### Activation prerequisites

- [ ] The private Journal core is deployed and production-verified, or Pete
      explicitly requested an earlier review.
- [ ] The selected environment and exact deployed commit are known.
- [ ] The current Azure resource inventory is available.
- [ ] The current architecture and data-flow evidence is available.
- [ ] The session can remain read-only.
- [ ] Screens and examples can be shown without secret values or private member
      content.
- [ ] Shared governance ownership permits any required package registration.

If a prerequisite is false, record whether it is a harmless scope exclusion or
a stop condition:

## 2. Pre-read

Provide a concise pre-read at least one working day before the walkthrough when
practical:

- [ ] one-page Azure system map
- [ ] plain-language glossary
- [ ] resource inventory labeled Live / Planned / Retired / Unknown
- [ ] production versus non-production boundary
- [ ] representative member data flow
- [ ] known evidence gaps and questions

Pre-read location:

## 3. Walkthrough

### A. Orient the system

- Which subscription, resource groups, regions, and environments exist?
- What is production, and what cannot affect production?
- Which deployed commit and pipeline run are we looking at?
- Who owns each material resource?

Evidence and owner questions:

### B. Follow one member action

Choose a sanitized representative action. Trace it across:

1. browser and public edge;
2. identity and session;
3. application runtime;
4. Azure SQL;
5. Blob Storage;
6. Speech/AI or other external providers, if involved;
7. logs and monitoring; and
8. retention, deletion, recovery, and rollback paths.

For every step, record:

| Step | Component | Data received | Data returned/stored | Authorization boundary | Evidence status |
|---|---|---|---|---|---|
| 1 |  |  |  |  | Verified / Inferred / Unknown |

### C. Inspect each Azure concern

| Concern | What Pete should understand | Evidence shown | Status |
|---|---|---|---|
| Runtime | Hosting, configuration, health, scale, and flags |  | Verified / Inferred / Unknown |
| Identity | Sign-in, sessions, managed identity, RBAC, and admin access |  | Verified / Inferred / Unknown |
| Azure SQL | Canonical data, migrations, encryption, backup, restore, retention, and deletion |  | Verified / Inferred / Unknown |
| Blob Storage | Containers, access, lifecycle, deletion, and recovery |  | Verified / Inferred / Unknown |
| Secrets/providers | Ownership, access, rotation, and external data boundaries |  | Verified / Inferred / Unknown |
| Delivery | Repository authority, pipeline, environments, approvals, deployment, and rollback |  | Verified / Inferred / Unknown |
| Observability | Logs, metrics, alerts, dashboards, diagnostic retention, and investigation |  | Verified / Inferred / Unknown |
| Network/edge | Domain, DNS, TLS, network paths, and restrictions |  | Verified / Inferred / Unknown |
| Cost/capacity | Cost drivers, budgets, alerts, quotas, and scaling risks |  | Verified / Inferred / Unknown |

### D. Practice the operating paths

Explain or demonstrate read-only evidence for:

- [ ] finding the exact version in production
- [ ] finding the pipeline that deployed it
- [ ] checking current application health
- [ ] locating a failed request without exposing member content
- [ ] identifying database and Blob backup/recovery expectations
- [ ] explaining rollback ownership and sequence
- [ ] finding budget, cost, or quota signals
- [ ] identifying who can access or change each critical system

## 4. Owner questions and decisions

| Question or decision | Answer/evidence | Status | Follow-up owner | Target date |
|---|---|---|---|---|
|  |  | Answered / Open / Blocked |  |  |

## 5. Gaps and actions

| Gap or risk | Why it matters | Required action | Owner | Target date | Separate initiative |
|---|---|---|---|---|---|
|  |  |  |  |  | Yes / No |

Do not make infrastructure changes during the walkthrough. Route every material
change through its own assigned authority.

## 6. Closeout

- Review outcome: Owner-understood / Follow-up required / Blocked by evidence gap
- Pete's plain-language summary of how the system works:
- Material uncertainties still open:
- Security/privacy concerns escalated:
- Follow-up evidence location:
- Next review trigger:
- Pete acknowledgement and date:
- Designated manager closeout and date:

### Required output check

- [ ] current Azure resource and environment map
- [ ] end-to-end data-flow explanation
- [ ] identity, managed-identity, and RBAC ownership map
- [ ] data lifecycle, backup, restore, retention, and deletion summary
- [ ] deployment and rollback path
- [ ] monitoring, incident, quota, and cost overview
- [ ] owner Q&A record
- [ ] gaps with owners and target dates
- [ ] next review trigger
- [ ] every material assertion labeled Verified / Inferred / Unknown
