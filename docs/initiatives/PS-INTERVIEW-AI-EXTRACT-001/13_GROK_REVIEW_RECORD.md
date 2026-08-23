# PS-INTERVIEW-AI-EXTRACT-001 — external Grok review record (PASS) and response

_Recorded 2026-08-23 by the former Extract completion manager AFTER the lane was relinquished to PS-DELIVERY-CONTROL-SIGNIN-001 (owner order, "absolute authority"). Nothing in the released lane was touched; this file lives in `artifacts/` so the record survives without reopening the lane._

## Verdict

**PASS** on `main a474e5ca86b057f139fc29d0519b47c3423c93db` (read-only; `d066d255` inspected for the rolled-back runtime). Rollback judged the right call and safely executed. Keep schema, roles, DENYs, retention flag, release-set setting and logging in place.

## Findings and responses

| # | Grok finding | Response | Owner / where it lands |
|---|---|---|---|
| F1 (high, next runtime) | Boot lock vs deploy layout mismatch; the 29 violated identities were never logged; disabling Oryx alone may not help if `.python_packages` is not on `sys.path`, or duplicates remain. | **Accepted.** The "Oryx rebuilds on 3.14" story is directionally supported but not proven. The next runtime package must deploy the same artifact to the candidate slot, log the full `lock_violations` list plus `sys.version`, `sys.path` and `dist.locate_file('')` for several locked names, and compare against `antenv` vs `.python_packages` — before any production change. Also log the violation identities at WARNING in `release.py`. | Next package (runtime closure fix). |
| F2 (medium, record) | Schema apply, App Service settings and the runtime deploy all happened while `release_allowed_for` was `[]` and blocked actions listed production deploy/config; the closeout names merge-admission debt but not this release-authority hole. | **Accepted — understated in the closeout.** Plain statement: under Pete's explicit override, production deployment and configuration proceeded with the ledger's `release_allowed_for` empty; the ledger cannot stop an automatic `ProductionWebDeploy` once a non-`[skip ci]` merge lands. | Fold into the control-ledger update by PS-DELIVERY-CONTROL-SIGNIN-001 and into the Interview record when that lane is next written. |
| F3 (low, proof) | `expect_error_sql` still passes on any exception for the older role-isolation checks; `community_identity_not_bound` is vacuous on a throwaway. | **Accepted.** Tighten to SQL 229 like the DENY probes; make the community check assert on a stand-in or mark it production-only. | Next package (proof tightening, together with residuals N1–N6). |
| F4 (low, closeout) | `12_COMPLETION_AND_POSTMORTEM.md` points to `11_…EVIDENCE.md` §5a for residuals N1–N6, which are not there. | **Accepted — my error.** N1–N6 exist only in the round-2 reviewer output and my notes. They are reproduced below so they are findable. | Correct the pointer when the Interview record is next written. |

## Residuals N1–N6 (from the round-2 independent review of `8ba76255`), reproduced

- **N1** `verify()` checks the application principal is present, not that it is `EXTERNAL_USER` (production principal was confirmed `EXTERNAL_USER` by catalogue read). Add an expected-type parameter.
- **N2** No statement timeout on the administrator connection.
- **N3** Two statements outside the content-free guards (`SELECT DB_NAME()` right after connect; `rollback()` inside `except`).
- **N4** Preserved role-isolation checks accept any exception (same as Grok F3).
- **N5** GRANT-verb test regex is case-sensitive.
- **N6** Forward-migration header wording "the application identity holds EXECUTE on the append procedure only" describes the role, not the real identity.

## Grok's process additions (agreed)

1. CI verified a different directory (`.python_packages` via `--target`) than boot verifies (the running interpreter's `importlib.metadata`).
2. The lock failed closed and discarded its evidence (count only).
3. `merge_allowed_for` plus automatic `ProductionWebDeploy` makes `release_allowed_for: []` unenforceable; only `[skip ci]` or not merging can hold a release.

## State confirmation at review time

- Reviewed SHA = checkpoint SHA = merged `main`: `a474e5ca86b057f139fc29d0519b47c3423c93db`.
- Remote Interview branch tips (all squash-merged, all clean, nothing unpushed): authority-split `8ba76255`, dark-infrastructure `f30311be`, runtime-projection `297d6a2f`, rollback `552b4be2`, closeout `53656ce6`.
- Live `/healthz`: `9a511ab87a776da231f56217` (= derived rollback identity; legacy Interview runtime).
- Lane status: relinquished (PS-INTERVIEW-AI-EXTRACT-001 and `azure-pipelines.yml`) to PS-DELIVERY-CONTROL-SIGNIN-001 before this review, on the owner's order. No Interview surface was written after that.
