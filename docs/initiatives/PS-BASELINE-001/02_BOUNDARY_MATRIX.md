# PS-BASELINE-001 — Route, Data, and Lane Boundaries

| Area | Real now | Active package may change | Explicitly excluded |
|---|---|---|---|
| Public résumé | Canonical route, redirects, shared data, download and AI hooks | Claude Code may refine hierarchy/disclosure in reserved résumé files | second dataset, backend fork, private data, global nav/theme |
| Interview Studio | Public browser-local practice slice | none in the active wave | private history claims, route/auth redesign, bundling into résumé branch |
| Owner Capture | Auth-protected create/list over `dbo.captures` | Codex may add lifecycle, migration, backend tests, and minimal protected Capture controls | public templates, Journal UI, Moment, placement, auth rewrite |
| Identity | Existing external identity and owner boundary | consume current server-derived owner identity | profile-ID parameters, forged-header trust, replacement auth |
| Canonical Moment | Not implemented | none until PS-CAPTURE-002 closes | treating corrected Capture text as published/canonical automatically |
| Placement | Not implemented | none until PS-MOMENT-001 closes | copying raw Capture text into résumé/community/job surfaces |
| Governance | v2.3 authority and Azure workflow | ChatGPT Work only | product writers silently changing lane ownership or package order |

## Parallel-safety conclusion

PS-CAPTURE-002 and PS-RESUME-PUBLIC-REFINE-001 share no writable product files. They may run in parallel after this baseline merges, provided both writers create fresh branches from the same current `origin/main` and preserve the reservations in their package READMEs.
