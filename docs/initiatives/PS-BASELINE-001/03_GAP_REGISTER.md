# PS-BASELINE-001 — Gap and Dependency Register

| Gap found | Resolution in this package | Remaining dependency |
|---|---|---|
| Governance records still called PS-GOV-001 pending after PR 59 merged | Reconciled baseline, state, initiative, and completion records | Keep synchronized on future package transitions |
| No controlled conflict order | Added `DOCUMENT_CONTROL.md` | Manager must report new conflicts |
| Manager tool assignment not recorded as owner decision | Added decision log and lane records | None |
| Active product packages had only short kickoff text | Added controlled Capture and résumé initiative packages | Writers must accept from fresh `origin/main` |
| Guardrail checked file presence but not active-package coherence | Expanded dependency-free tests | Azure CI remains final release evidence |
| Older v1.3/Iris language could be mistaken for current authority | Corrected startup files and Site Rules status | Historical documents remain intentionally present |
| GitHub mirror is behind Azure | Recorded as backup-only and push-on-hold | A future owner-authorized mirror sync package |
| Local Windows environment has no project virtual environment | Relied on dependency-free checks locally and Azure for full suite | Product writers must use a configured test environment or CI |

## Stop conditions for the next wave

- Do not start from the pre-baseline SHA after this package merges.
- Do not start if another writer has already claimed the proposed branch.
- Stop if the actual schema or authorization boundary contradicts the Capture package.
- Stop if résumé work requires changes outside its reserved files or changes the meaning/source data.
