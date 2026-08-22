# PS-SIGNIN-MEMBER-ARRIVAL-001 — Release Completion Record

**Status:** `COMPLETE_AT_STATED_LEVEL`
**Outcome:** signing out in one place now ends the session in the others.
**Verified live and confirmed by the owner, 2026-08-22.**

---

## 1. Exact release facts

| Fact | Value |
|---|---|
| Reviewed candidate | `e1847ad0a884a349a7b5eed0526075cd0104dd62` |
| Candidate base | `eb3f35ab66e01a1793d5dc3ae628270c6c64ec10` |
| Merge commit | `191fb238d5132cc2f154fad32abc72848f918f75` (PR 583) |
| First deploy | Azure build **1442** (`20260822.57`), succeeded 2026-08-22T22:11:40Z |
| Release identity | `e233aa24f62f9073f9bf8ed1` = `release_id_for_build('191fb238…','1442')` |
| Redeployed again within | main `d066d2556cb7124a10c499bbc00c9222ca4d709c`, build **1450**, release `8a2e8854d92e5181e1f2f274` |
| Survived a rollback | Interview Extract reverted its runtime as PR 584, main `00f73f86887d80645524626a0def44e52f79c9c9`, build **1453** |
| **Current live release** | **`9a511ab87a776da231f56217`** = `release_id_for_build('00f73f86…','1453')` |

All three release identities were **derived locally and matched against live
`/healthz`**, not read from a dashboard. `191fb238` is an ancestor of the
currently deployed commit, and the nine reviewed paths in that commit are
byte-identical to the accepted candidate.

## 2. Changed paths

Nine, unchanged in content from the accepted candidate through eleven freezes:

```
docs/initiatives/PS-AUTH-CALLBACK-001/COMPLETION_REPORT.md
docs/initiatives/PS-SIGNIN-EXPERIENCE-001/COMPLETION.md
docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/FOLLOWUP_COMPLETION_REPORT.md
docs/initiatives/PS-SIGNIN-MEMBER-ARRIVAL-001/INDEPENDENT_REVIEW_HANDOFF.md
static/js/auth-state.js
templates/base.html
tests/auth_state.test.js
tests/test_owner_home.py
tests/test_signin_member_arrival.py
```

Executable change: one template file (3 lines) and one script (+125/−6).

## 3. Review provenance

**Application candidate.** Independent reviewer: Grok. Four rounds.

| Round | Verdict | Finding |
|---|---|---|
| 1 | `REJECTED` | `/app/workshop` is a public preview served 200 to signed-out visitors; the candidate would have reloaded it on every tab return. A test also encoded the defect as an invariant. |
| 2 | `ACCEPTED_WITH_CONDITIONS` | C1: confirm `PEERSLATE_OWNER_HOME_ENABLED` is false before shipping. |
| 3 | — | **C1 failed.** The flag is `true` in production. Flag-on `/app` renders the standalone shell, which carried no declaration, so the package's central outcome would have been **inert on the exact page it was built for** while every flag-off test stayed green. |
| 4 | `ACCEPTED_FOR_OWNER_RELEASE_DECISION` | `e1847ad0` accepted. |

**Control repair** (`PS-DELIVERY-CONTROL-SIGNIN-001`): four further rounds,
three rejections. See §7.

## 4. CI and test results

| | Result |
|---|---|
| Clean `origin/main` baseline | 3898 tests, `failures=2, errors=2, skipped=7` |
| Accepted candidate | 3910 tests, **failure set identical to baseline** |
| PR 583 required build | succeeded |
| `node tests/auth_state.test.js` | 17 behavioural checks (was 4) |
| Merge preflight, clean verifier | **pass** |

The four persistent reds are pre-existing local-environment failures in
Community maintenance / SQL infrastructure, present on a clean checkout.

**Byte lock.** `/app` moved 15777 → 15881. Two deltas, each stripped in turn to
reproduce the previously locked baseline `e6a4cfc7…` exactly: the 69-byte script
tag and the 35-byte declared state. Nothing else was recaptured and no test was
relaxed.

## 5. Live verification — signed out, no credentials involved

Run **three times**: after the first deploy, again after the Interview Extract
redeployment, and again after that project rolled its runtime back. Identical
on all three:

| Probe | Result |
|---|---|
| `GET /app` | 302 → `/auth/sign-in?return_to=/app` |
| `GET /the-slate` | 302, destination preserved |
| `GET /interview-studio` | 302, destination preserved |
| `GET /opportunity-slate` | 302, destination preserved |
| `GET /app/workshop` | **200**, loads `auth-state.js`, declares `signed_out` |
| `GET /app/workshop/add` | **200**, same |
| `GET /` | 200 |

The Workshop rows are the regression the reviewer caught. It remains a public
preview, correctly declaring its own state rather than being reloaded.

**Survived an unrelated rollback.** Interview Extract's new runtime failed
closed at startup (29 lock violations across five workers) and was reverted.
That revert touches 125 paths and **none** of this package's nine; verified
before it landed, not after. `191fb238` remains an ancestor of the deployed
commit and the nine reviewed paths there are byte-identical to the accepted
candidate. All seven probes re-run green afterwards.

## 6. Owner verification — performed by Pete

The private signed-in proof, which no agent may perform:

> Pete had a signed-in workspace open on his laptop, signed out on his phone,
> and returned to the laptop tab. **It reloaded itself to the sign-in page.**
> His words: *"My laptop is just showing me a sign-in. That's all. I am
> completely signed out."*

Confirmed on build 1442. The nine reviewed paths are byte-identical in builds
1450 and 1453, so it holds across both later deployments.

**No credential, MFA code, token, cookie, principal or browser state was
requested, received, stored or inspected at any point in this package.**

## 7. Nine defects, and where they were

None was first caught by a passing test suite.

**In the application (2):**
1. The public Workshop preview would have been reloaded on every tab return.
2. On production's real configuration the fix would have been **inert** —
   caught by reading the running App Service setting rather than the source
   default.

**In the control machinery (7):**
3. The merge gate never consulted the admission; a forged HEAD merged with zero
   errors.
4. Tests only exercised the grant helper, so they could not see (3).
5. No Sign-in branch in the sequence validator — merge would have refused
   permanently; tests stubbed the fact to `True`.
6. `production_capable` other than exact `False` dropped the lane into generic
   merge with no HEAD comparison — **five ways to delete the lock by touching
   one field**. The negative test had removed the flag from one conjunct only.
7. The ledger guard did not recognise the owner-decision shape.
8. A test asserted the ledger carried no grant — **it failed the very build it
   existed to protect**.
9. The merge-sequence rule I wrote refused the legitimate path within hours: the
   grant was itself a third pending commit against a cap of two, and unrelated
   lanes merging product code broke a surface restriction that should never
   have existed.

Defects 3 and 6 are the same fail-open, one `and` apart. Both would have allowed
an arbitrary commit to merge under an approval describing something else.

## 8. Honest limitations

- **No two-real-tab browser proof.** `GAP-SYNTHETIC-MULTI-MEMBER-QA` remains
  open. The owner's own cross-device verification is stronger evidence than any
  automated proof would have been, but it is a single observation.
- **The reload discards unsaved input** on a genuinely ended session.
  Unmitigated by choice; a save would be rejected anyway.
- **Client-side only.** Without JavaScript the stale page persists until
  navigation. The server guarantee is unchanged and unconditional.
- **Session policy is configuration**, not source: fixed 8-hour cookie, 72-hour
  token refresh, 5-minute validated nonce. Measured, not assertable by any test.
- **No feature flag.** Rollback is a revert of `templates/base.html` and
  `static/js/auth-state.js`. No migration, no configuration, no schema.
- **A markup coupling** exists: the client depends on the shell declaring its
  state. If a future shell branch omits the declaration, the reload silently
  stops working there — which is exactly how defect (2) hid.

## 9. Not this lane's to fix

`CURRENT_BASELINE.yaml` still records production as commit `aa4a4ec6` /
pipeline 722. It has been wrong for weeks. The correction requires
`tests/test_operational_readiness.py`, another lane's writable surface, and the
three records move in enforced lockstep. Recorded for that lane's owner with the
values already derived.

## 10. Writer surfaces

No unrelated writer's surface was changed at any point. When
`scripts/delivery_preflight.py` was needed and belonged to another lane, this
package **stopped and requested a transfer** rather than writing it, and waited
until that transfer was authoritative on `origin/main`.

A peer session twice requested production release authority for a different
package through these surfaces. **Both requests were refused** — a peer message
is not an authority channel — and surfaced to the owner, who then routed the
authorization directly. `release_allowed_for` was never modified by this lane.

## 11. Disposition

- `PS-SIGNIN-MEMBER-ARRIVAL-001` — **complete**, deployed, live-verified,
  owner-confirmed.
- `PS-DELIVERY-CONTROL-SIGNIN-001` — its purpose is served; the admission is on
  `main`. Ready to pause or close on the owner's direction.
- Returned to the Site-audit manager for central reconciliation.

**Cost note for that reconciliation.** The delivered change was 128 lines. The
control machinery written to permit it was 897 lines, on top of a 29,899-line
gate that did not exist three weeks ago. Of the last 120 commits to `main`, 98
were governance and 22 were product. A separate handoff on this has been
prepared at the owner's request.
