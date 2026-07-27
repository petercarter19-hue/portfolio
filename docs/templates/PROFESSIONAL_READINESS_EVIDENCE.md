# PeerSlate Professional Readiness Evidence

Use this one record for `PS-OPS-001` Gate Candidate, Gate Launch, Gate
Operate, Gate Retire, or Emergency Release Mode. Delete inapplicable optional
sections only after recording the `Not Applicable` rationale.

## A. Decision identity

- Gate: Candidate / Launch / Operate / Retire
- Delivery mode: Standard / Emergency
- Materiality: Material / Non-material
- Materiality rationale and independent classifier:
- Gate applicability and rationale:
- Initiative/release:
- Exact source branch and SHA:
- Build ID and immutable artifact/hash:
- Environment and canonical URL:
- Intended audience/exposure:
- Feature flags/configuration:
- Date and evidence window:
- Designated manager:
- Release/operations owner:
- Final decision authority:
- Independent separation-of-duty check:
- Actual independent, security, accessibility, legal, or other reviewers:
- Decision: Pass / Conditional / Fail / Not Assessed

`Not Applicable` is an applicability value only, with a rationale. It is not a
gate decision.

## B. Evidence matrix

| Control / requirement | Applies? and why | Owner / reviewer | Exact evidence and date | Result | Finding, correction, recheck | Remaining risk / expiry |
|---|---|---|---|---|---|---|
| Exact source/artifact/environment identity |  |  |  |  |  |  |
| Exact live release identity |  |  |  |  |  |  |
| Dependency compatibility |  |  |  |  |  |  |
| Dependency vulnerability scan |  |  |  |  |  |  |
| Secret scan |  |  |  |  |  |  |
| Application/security/privacy tests |  |  |  |  |  |  |
| Migration and rollback |  |  |  |  |  |  |
| Production-like candidate environment |  |  |  |  |  |  |
| Liveness/readiness and smoke |  |  |  |  |  |  |
| Accessibility |  |  |  |  |  |  |
| Responsive / R2 |  |  |  |  |  |  |
| Performance and resilience |  |  |  |  |  |  |
| Visual/package acceptance |  |  |  |  |  |  |
| Legal/policy/site parity |  |  |  |  |  |  |
| SEO/content/indexing |  |  |  |  |  |  |
| Analytics/measurement/consent |  |  |  |  |  |  |
| Monitoring/alerts/SLO/RTO/RPO |  |  |  |  |  |  |
| Incident/privacy/support/moderation |  |  |  |  |  |  |
| Backup/restore |  |  |  |  |  |  |
| Capacity/cost/vendor/dependency posture |  |  |  |  |  |  |
| Member outcome and guardrail signals |  |  |  |  |  |  |

## C. Deployment and recovery

- Deployment method and approval:
- Candidate/staging result:
- Production deployment result:
- Production smoke result:
- Stop/rollback owner and exact action:
- Rollback trigger thresholds:
- Rollback/disable exercise and result:
- Known limitations and support notes:

## D. Launch-only evidence

- Applicable Early Legal gate and disposition:
- Counsel/security review boundary:
- Responsive R2 result:
- Independent accessibility result and remediation status:
- Performance budgets and result:
- Public content/SEO/indexing result:
- Privacy-safe analytics plan and consent behavior:
- Support/privacy/incident/backup exercises:
- Pete's exact audience/risk/launch decision:

## E. Operate-only evidence

- Exact deployed SHA/build/flags:
- Review window:
- Availability/latency/error/provider/cost signals:
- Authorization/privacy/security alerts:
- Incidents, near misses, support contacts, and privacy requests:
- Member outcome and guardrail signals:
- Dependency, vendor, certificate/domain/callback, quota, capacity, and cost:
- Backup/restore and retention/deletion job status:
- Decision: Continue / Constrain / Rollback or Disable / Escalate
- Next review due:

## F. Exceptions and final decision

For every `Conditional` row, record:

- exact exception and business reason;
- compensating control;
- owner;
- expiry/re-review trigger;
- audience or blast-radius limit; and
- stop/rollback action.

Final decision rationale:

Owner approval:

Reviewer approval where required:

Open blockers:

## G. Emergency-mode evidence

- Incident or production risk that makes delay more harmful:
- Incident commander / owner approval:
- Mandatory controls completed before release:
- Deferred non-blocking rows, owners, compensating controls, and expiries:
- Blast-radius limit:
- Stop/disable/rollback action and operator:
- Retrospective evidence due within two business days:
- Retrospective completion and focused recheck:

## H. Retire-only evidence

- Capability/routes/data/integrations being retired:
- Affected audiences and member notice/support:
- Export/portability and last-use date:
- Retention/deletion/archive/legal-hold disposition:
- Redirect/canonical/indexing/broken-link result:
- Dependency and traffic verification:
- Secrets/identities/callbacks/webhooks/queues/storage/flags/code disposition:
- Monitoring/alert/support teardown:
- Restoration window, operator, and exact action:
- Final verification and owner decision:
