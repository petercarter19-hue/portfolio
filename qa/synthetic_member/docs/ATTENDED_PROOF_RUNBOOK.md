# Attended two-member proof runbook

This runbook is inert until Pete separately authorizes a deployed proof and
confirms that two suitable QA identities are available. The local candidate
does not grant that authority.

## Roles

- **Pete:** makes material owner decisions; authorizes spending, production
  actions, and irreversible identity deletion; and performs only genuinely
  physical-device-only actions. Except for the bounded sealed-broker exception
  below, Pete enters passwords, email or other login identifiers, verification
  or MFA codes, recovery information, and other credentials; and confirms
  which QA identity is in use.
- **Package manager:** prepares the neutral plan, calls out each structural
  observation, records only closed outcome codes, validates cleanup, and stops
  on a safety concern. If the manager lacks a browser tool, the manager assigns
  ordinary browser work to a browser-capable executor within this same task.
- **Browser-capable operator:** opens pages, navigates, clicks ordinary controls,
  manages tabs and refreshes, departs to and returns from public pages, clicks
  ordinary sign-out controls, performs the authorized visible item lifecycle,
  makes privacy-safe structural observations, and performs routine cleanup and
  visible residue checks.
- **Harness:** generates and validates local JSON only. It never opens or drives
  a browser and never reads identity or session material.
- **Sealed credential broker:** only when
  `PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-001` and a separate attended operation
  authorize it, runs as one local worker for exactly two run-scoped ordinary QA
  customer identities. It receives the operation authorization reference,
  approved PeerSlate auth issuer, controlled QA-mailbox seed, and External ID
  tenant issuer through non-echoing local prompts; derives the two login
  identifiers; generates passwords; obtains the active Graph token without
  passing any prompted value to Azure CLI; verifies the token tenant and Graph
  verified domain before any customer POST;
  creates the two customer objects; and drives the fixed sign-in and account
  switch flow in disposable no-capture contexts. The worker may never print,
  persist, return, or expose those values to Codex, a browser operator, the
  package manager, a terminal log, a manifest, or repository evidence.

Pete's retained actions do not make him the routine browser operator. Neither
the package manager nor the browser-capable operator asks Pete to disclose a
password, address, MFA code, recovery code, claim, header, cookie, token,
account key, browser profile, or session file.

### Browser observation boundary

The operator may observe the rendered application and closed structural
outcomes. Screenshots are optional, never the default retained proof, and must
be minimized to public UI or an approved synthetic structural state. They must
exclude credentials, MFA or recovery values, account identifiers, sentinel or
private item content, unrelated private data, and session material. Destroy any
transient privacy-safe screenshot before final validation unless separate
evidence authority explicitly permits retention. Never photograph, copy, or
export a suspected private exposure.

The operator never inspects, exports, records, or persists passwords, MFA codes,
cookies, tokens, claims, authentication headers, browser profiles, or private
session files. The operator never exports, records, or persists browser storage,
private network traces, or DOM/page content.

## Entry gate

Before starting, confirm all of the following without recording identity
details:

1. the exact deployed application commit and release are known;
2. the separately authorized feature surface is available and private;
3. Pete confirms that `member_a` and `member_b` refer to two dedicated ordinary
   QA members, not personal or owner/admin accounts;
4. the approved cleanup action exists for any item the journey will create;
5. a run-scoped, non-semantic synthetic sentinel is ready but will not be copied
   into retained evidence;
6. no private-member screenshot or broad database query is planned, and any
   optional structural screenshot meets the browser observation boundary; and
7. the evidence file is outside the repository and begins from a newly generated
   manifest.

If any entry condition is missing, stop. Do not substitute Pete's owner account,
another person's identity, production content, or a mocked result.

## Identity creation and retirement gate

Do not create either customer identity until all entry-gate checks pass, the
identity-retirement tool is independently accepted and merged, and the
operator is running that exact merged source. The proof application release is
still pinned separately by the normal entry gate; this operator tool is not an
application feature flag or runtime endpoint.
Immediately before creation, establish a run-scoped exact UTC cutoff. The
normal path remains Pete's direct credential input. The sealed-broker exception
is available only when the exact broker candidate is independently accepted and
the attended operation separately authorizes its execution. The local worker
first validates all confirmations and then accepts the controlled mailbox seed
and tenant issuer through non-echoing local prompts. It derives exactly two
same-inbox identifiers and creates exactly two ordinary customer objects through
the fixed Microsoft Graph endpoint only after a token tenant plus Graph
organization/verified-domain check matches the prompted External ID issuer. Its
Graph token, generated credentials, and External ID object IDs remain only in
worker memory.

The sealed worker uses three disposable, no-capture contexts: one for each
member arrival plus one switch context that completes A-to-B and B-to-A. It
never enables screenshots, trace/video, downloads, browser-profile persistence,
storage-state export, DOM/page capture, or network capture. Browser engines may
create unavoidable non-persistent cache/profile files only in one explicit,
run-scoped temporary root with no inherited sensitive worker environment. The
worker refuses pre-existing broker residue; it closes every context, destroys
that root, and verifies removal before it reports success. Any root or context
cleanup failure is indeterminate. If the Graph creation is partial or ambiguous,
a browser operation cannot establish the required exact pair, or a context
cannot be destroyed, it returns only an indeterminate closed code and does not
delete, retry blindly, search for unrelated identities, or start the retirement
path.

For the normal manual-credential path, the browser-capable operator opens the
identity flow and uses its ordinary controls. Before Pete enters a login
identifier or credential, the operator stops issuing
browser commands and suspends all capture and observation. Pete controls the
visible input and says only `ready` when ordinary browser operation may resume;
he does not disclose the entered value. Pete confirms which QA identity is in
use. Exactly two same-inbox customer identities are created, and Pete privately
retains the two External ID subjects only long enough to complete the attended
operation.

After operator control resumes, ordinary UI may unavoidably render a login
identifier or account label. Incidental visibility is not evidence and is not
an identity mismatch. The operator must not intentionally inspect, transcribe,
export, capture, record, or retain that detail and refers to the identities only
as `member_a` and `member_b`. If any secret, code, or credential is rendered unmasked,
stop without capture. The package manager receives only the aliases
and closed structural outcomes when not also serving as the browser-capable
operator. The proof record always receives only aliases and closed structural
outcomes.

After application-item cleanup and before either External ID customer object is
permanently deleted, the normal path is a separately authorized operator running
this order:

1. set the current authoritative `PEERSLATE_AUTH_ISSUER` value in process memory
   without displaying or saving it;
2. run `plan` with the exact creation cutoff and current operation-authorization
   reference; Pete privately enters and confirms `member_a` and `member_b`
   subjects at the non-echoing prompts so the operator never inspects a claim;
3. run `retire` with the same inputs and all three retirement confirmations;
4. run `verify-retired`; and
5. only after verification passes and Pete gives action-time authorization for
   irreversible identity deletion, the browser-capable operator carries out the
   previously established Entra retirement path; Pete enters any credential or
   MFA value and confirms each QA identity if prompted.

```powershell
python scripts/run_synthetic_qa_identity_retirement.py plan `
  --authorization-ref <CURRENT-OPAQUE-AUTHORIZATION> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF>

python scripts/run_synthetic_qa_identity_retirement.py retire `
  --authorization-ref <CURRENT-OPAQUE-AUTHORIZATION> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF> `
  --confirm-exact-two-synthetic-members `
  --confirm-workshop-cleanup-complete `
  --confirm-retire

python scripts/run_synthetic_qa_identity_retirement.py verify-retired `
  --authorization-ref <CURRENT-OPAQUE-AUTHORIZATION> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF>
```

If retirement was mistaken and neither External ID object has been permanently
deleted, the separately authorized recovery operation is:

```powershell
python scripts/run_synthetic_qa_identity_retirement.py recover `
  --authorization-ref <CURRENT-OPAQUE-RECOVERY-AUTHORIZATION> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF> `
  --confirm-exact-two-synthetic-members `
  --confirm-external-identities-not-permanently-deleted `
  --confirm-recover
```

Never recover after Entra permanent deletion. A refusal, nonzero residue count,
mapping mismatch, unexpected role, missing/untrusted foreign key, or update
count other than two is a hard stop. Do not work around it with SQL, a feature
flag, or a production configuration change. Do not enable SQL-driver debug
logging, ODBC tracing, a network recorder, or any other parameter capture; the
tool refuses known mssql-python diagnostic logging.

An `indeterminate` result is also a hard stop. It can mean the database commit
succeeded but connection cleanup did not. Never repeat `retire` or `recover`
from that result; obtain authority for a read-only state verification first.

The sealed broker uses the same accepted retirement core programmatically rather
than repeating the two subjects at a prompt. It passes the two in-memory Graph
object IDs only after both customer objects were provisioned, both arrival and
switch checks completed, and the attended action supplied all broker
confirmations. The core retains its existing serializable exact-two checks,
ordinary-role/private-profile requirements, residue refusal, and closed output.
The broker reports `retired_pending_external_deletion` only after that core
commits. It never performs External ID permanent deletion; that remains Pete's
separate action-time decision and is not evidence of a successful broker run.

The broker command contains only safe run metadata. It never accepts an
authorization reference, identity, mailbox, password, token, subject, issuer,
or browser-profile path as an argument. Its normal structural plan is:

```powershell
python scripts/run_synthetic_sealed_credential_broker.py plan
```

Only within a separately authorized attended operation may the local worker run:

```powershell
python scripts/run_synthetic_sealed_credential_broker.py run `
  --run-id <SAFE-RUN-ID> `
  --created-after-utc <EXACT-UTC-CREATION-CUTOFF> `
  --execute `
  --confirm-exact-two-synthetic-members `
  --confirm-no-production-proof `
  --confirm-retirement-handoff
```

The worker prompts only locally and without echo for its operation authorization
reference, approved PeerSlate auth issuer, External ID tenant issuer, and
controlled mailbox seed. It passes no authorization reference, credential,
member identity, issuer, or PeerSlate auth issuer in Azure CLI or Chromium child
environments, command arguments, or output. Azure CLI provides only its active
pre-authorized Graph token; the worker rejects it before mutation unless its JWT
tenant and authenticated Graph organization/verified domain match the sealed
issuer. A missing pre-existing Graph grant, tenant-binding mismatch,
capture/debug environment, noninteractive terminal, malformed pair, duplicate
Graph object ID, stale engine-root residue, or any partial state returns a
closed refusal or indeterminate result; neither code authorizes a retry,
recovery, or deletion.

## Client arrangement

The browser-capable operator prepares four independent contexts without
importing a profile, cookies, storage, cache, extensions, or saved sessions:

- **Client A:** dedicated to `member_a`;
- **Client B:** dedicated to `member_b`;
- **Signed-out control:** never signed in;
- **Switch client:** used first by one member, signed out through an ordinary
  control by the browser-capable operator, then used by the other member without
  copying or inspecting browser storage.

Clients A and B stay open simultaneously for the paired isolation checks. The
switch client tests ordinary product account switching before its final
destruction. A fresh replacement switch context may then confirm the clean
baseline. The harness does not create, reset, or inspect any context.

## Run sequence

1. Generate the canonical plan with `plan --json` and initialize the sanitized
   manifest outside the repository with the exact deployed source, release, and
   browser version. Initialization refuses an existing destination.
2. The browser-capable operator uses the signed-out control to verify that
   protected navigation discloses no private payload.
3. The browser-capable operator opens each sign-in flow and handles ordinary
   controls. Pete confirms the intended QA identity and enters only login
   identifiers, passwords, verification or MFA values, recovery information,
   and other credentials. Record only whether both members arrive privately and
   whether the application visibly treats them as distinct. Do not record how
   the identities are named or mapped.
4. The browser-capable operator establishes an owner-scoped pre-run item count
   for both aliases through the separately authorized member surface. Retain
   counts only.
5. The browser-capable operator uses the minimal approved synthetic sentinel to
   create an item for each member. Keep any returned handles only in the
   ephemeral cleanup ledger.
6. With both clients open, the browser-capable operator proves owner-only
   visibility and runs list, read, update, delete, export, and forged-reference
   checks from A toward B and from B toward A. A safe neutral denial is required;
   no private peer content may be used as evidence.
7. The browser-capable operator verifies that browser-local state is isolated
   by observing the rendered application result, without inspecting or exporting
   browser storage, cookies, claims, or session files.
8. The browser-capable operator performs A-to-B and B-to-A switch journeys in
   the switch client. Pete confirms the intended QA identity and enters any
   required credential or MFA values. After each operator-clicked sign-out and
   next sign-in, verify that the previous member's private or browser-local state
   is absent.
9. The browser-capable operator performs refresh, second-tab, public-return,
   sign-out, cross-tab sign-out, and—only when the environment makes it
   controllable—expired-session journeys for each alias. Report uncontrollable
   expiry or unreconciled cross-tab behavior as Conditional using the approved
   note code.
10. The browser-capable operator deletes or archives every created item through
    the same authorized application contract and verifies zero active residue
    for both aliases. Record only created and residue counts plus the truthful
    soft-delete or retention classification.
11. The browser-capable operator signs out and destroys Clients A, B, the
    signed-out control, and the switch client. Pete participates only if a
    credential, MFA, identity-confirmation, or physical-device action is
    genuinely required. Record only the destruction status.
12. Repeat the clean-start check. Run final validation. Pending steps, fewer
    than one created item for either alias, active residue, or failed client
    destruction prevent Pass.

## Recording commands

Record a normal Pass:

```powershell
python scripts/run_synthetic_member_qa.py record-journey `
  --manifest <SANITIZED-EVIDENCE-PATH> `
  --journey member_a_cannot_read_member_b `
  --status pass
```

Record a known limitation without free text:

```powershell
python scripts/run_synthetic_member_qa.py record-journey `
  --manifest <SANITIZED-EVIDENCE-PATH> `
  --journey member_a_expired_session_safe `
  --status conditional `
  --note-code session_expiry_not_controllable
```

Record count-only cleanup:

```powershell
python scripts/run_synthetic_member_qa.py record-cleanup `
  --manifest <SANITIZED-EVIDENCE-PATH> `
  --pre-run-baseline pass `
  --created-member-a <COUNT> `
  --created-member-b <COUNT> `
  --residue-member-a 0 `
  --residue-member-b 0 `
  --retention-disclosure <APPROVED-CODE> `
  --client-a-destroyed pass `
  --client-b-destroyed pass `
  --signed-out-control-destroyed pass `
  --switch-client-destroyed pass
```

## Stop and containment rules

Stop immediately and record Fail when private peer information appears, the two
members map to the same application account, signed-out access returns a private
payload, a switch exposes prior-member state, or active synthetic residue remains.
The approved safety codes cannot be recorded as Conditional; the validator
requires Fail. Conditional is reserved for bounded proof limitations that did
not expose private state or invalidate account isolation.

Do not capture the exposed information. The browser-capable operator closes the
affected view, preserves only the safe failure code, signs out through ordinary
controls, destroys the affected contexts, and returns the defect to the package
manager as an identity/privacy blocker. Pete participates only for a required
credential, MFA, identity-confirmation, authorization, or physical-device action.

If application deletion succeeds but retention cannot be established, record
Conditional. Do not claim permanent deletion. If cleanup itself fails, stop
further runs until the residue is contained under separate authority.

## Retained proof

The retained bundle is limited to the final validated JSON, the exact source and
release labels already present in it, and a package-level summary of Pass,
Conditional, or Fail. Do not retain the ephemeral cleanup ledger, sentinel text,
DOM/page content, browser history, screenshots, network traces, database rows,
identity inventory or identifiers, credentials, tokens, session material,
cookies, claims, authentication headers, browser profiles, or private session
files. Any transient privacy-safe screenshot is destroyed before this retained
bundle is finalized unless separate evidence authority explicitly changes that
boundary.
