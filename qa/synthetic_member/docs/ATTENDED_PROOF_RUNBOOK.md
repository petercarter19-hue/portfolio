# Attended two-member proof runbook

This runbook is inert until Pete separately authorizes a deployed proof and
confirms that two suitable QA identities are available. The local candidate
does not grant that authority.

## Roles

- **Pete:** provisions or retires both QA identities; controls every login,
  sign-out, MFA, and account-selection action; visually checks identity context.
- **Package manager:** prepares the neutral plan, calls out each structural
  observation, records only closed outcome codes, validates cleanup, and stops
  on a safety concern.
- **Harness:** generates and validates local JSON only. It never opens or drives
  a browser and never reads identity or session material.

The package manager must not ask Pete to disclose a password, address, MFA code,
recovery code, claim, header, cookie, token, account key, browser profile, or
session file.

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
6. no private-member screenshot or broad database query is planned; and
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
Immediately before creation, establish a run-scoped exact UTC cutoff. Pete then
creates exactly two same-inbox customer identities and privately retains the
two External ID subjects only long enough to complete the attended operation.
The package manager never sees or records an address, subject, object ID,
credential, code, claim, token, or account-selection detail.

After application-item cleanup and before Pete permanently deletes either
External ID customer object, a separately authorized operator runs this order:

1. set the current authoritative `PEERSLATE_AUTH_ISSUER` value in process memory
   without displaying or saving it;
2. run `plan` with the exact creation cutoff and current operation-authorization
   reference; Pete privately enters and confirms `member_a` and `member_b`
   subjects at the non-echoing prompts;
3. run `retire` with the same inputs and all three retirement confirmations;
4. run `verify-retired`; and
5. only after verification passes, Pete permanently deletes the two External
   ID customer objects using the previously established Entra retirement path.

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

## Client arrangement

Pete prepares four independent contexts without importing a profile, cookies,
storage, cache, extensions, or saved sessions:

- **Client A:** dedicated to `member_a`;
- **Client B:** dedicated to `member_b`;
- **Signed-out control:** never signed in;
- **Switch client:** used first by one member, signed out by Pete, then used by
  the other member without copying or inspecting browser storage.

Clients A and B stay open simultaneously for the paired isolation checks. The
switch client tests ordinary product account switching before its final
destruction. A fresh replacement switch context may then confirm the clean
baseline. The harness does not create, reset, or inspect any context.

## Run sequence

1. Generate the canonical plan with `plan --json` and initialize the sanitized
   manifest outside the repository with the exact deployed source, release, and
   browser version. Initialization refuses an existing destination.
2. In the signed-out control, verify that protected navigation discloses no
   private payload.
3. Pete signs `member_a` into Client A and `member_b` into Client B. Record only
   whether both arrive privately and whether the application visibly treats
   them as distinct. Do not record how the identities are named or mapped.
4. Establish an owner-scoped pre-run item count for both aliases through the
   separately authorized member surface. Retain counts only.
5. Use the minimal approved synthetic sentinel to create an item for each
   member. Keep any returned handles only in the ephemeral cleanup ledger.
6. With both clients open, prove owner-only visibility and run list, read,
   update, delete, export, and forged-reference checks from A toward B and from B
   toward A. A safe neutral denial is required; no private peer content may be
   used as evidence.
7. Verify that browser-local state is isolated. The package manager may observe
   the rendered application result but must not inspect or export browser
   storage, cookies, claims, or session files.
8. Pete performs A-to-B and B-to-A switch journeys in the switch client. After
   each sign-out and next sign-in, verify that the previous member's private or
   browser-local state is absent.
9. Pete performs refresh, second-tab, public-return, sign-out, cross-tab
   sign-out, and—only when the environment makes it controllable—expired-session
   journeys for each alias. Report uncontrollable expiry or unreconciled
   cross-tab behavior as Conditional using the approved note code.
10. Delete or archive every created item through the same authorized application
    contract. Verify zero active residue for both aliases. Record only created
    and residue counts plus the truthful soft-delete or retention classification.
11. Pete signs out. Pete destroys Clients A, B, signed-out control, and switch
    client. Record only the destruction status.
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

Do not capture the exposed information. Close the affected view, preserve only
the safe failure code, ask Pete to sign out and destroy the affected contexts,
and return the defect to the package manager as an identity/privacy blocker.

If application deletion succeeds but retention cannot be established, record
Conditional. Do not claim permanent deletion. If cleanup itself fails, stop
further runs until the residue is contained under separate authority.

## Retained proof

The retained bundle is limited to the final validated JSON, the exact source and
release labels already present in it, and a package-level summary of Pass,
Conditional, or Fail. Do not retain the ephemeral cleanup ledger, sentinel text,
browser history, screenshots, network traces, database rows, identity inventory,
or login/session material.
