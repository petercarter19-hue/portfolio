# Independent Protected Review Brief — PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001

You are a fresh-context independent reviewer (Claude Fable, extra-high effort). You did not
write this code. Your job is to try to REJECT the candidate: find real defects, not to
rubber-stamp. Protected risk areas: identity, authorization, browser-record privacy,
consequential AI truth.

Candidate: branch `work/2026-08-11-interview-studio-authenticated-experience-001` at the exact
SHA given to you, in worktree `C:\Users\peter\Documents\portfolio-interview-studio-auth-20260811`.
Read-only: you change nothing; you report findings.

Authority stack to review against:
1. `C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\Interview Studio Claude
   Architecture Deliverable 2026-08-11\` (accepted architecture, esp. 02/03/04/07 and
   OWNER_ACCEPTANCE_2026-08-11.md).
2. The 19 locked visuals + VISUAL_QA_LEDGER in the handoff package
   (`...\Interview Studio Claude Architecture Handoff 2026-08-11\02_VISUAL_AUTHORITY\`).
3. The lane record in `docs/governance/CURRENT_LANES.json` (surfaces/exclusions).
4. `docs/initiatives/PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001/SLICE_NOTES.md`
   (the writers' own record — verify its claims, don't trust them).

Required passes (report P0-P3 findings per pass; each finding: file:line, failure scenario,
severity, suggested fix):

A. Diff-boundary audit: `git diff 24f0acb...HEAD --name-only` — every changed path must be in
   the lane's writable surfaces (plus the two architect-recorded governance commits). Any stray
   path is P0.
B. Access boundary: flag-off byte-comparability (run the test AND reason about the template
   conditionals yourself); flag-on gates on both HTML routes and all four APIs — try to
   construct a bypass (direct POST, HEAD, legacy redirect paths, ?mode coercion, history view,
   /api/interview/coach, entitlement-disabled combinations); safe-return hostile shapes; JSON
   401 vs redirect split; headers (X-Robots-Tag/no-store) on every response class; robots/
   sitemap; rate keying (verify the key function cannot touch the DB — trace it); same-origin
   fail-closed logic.
C. Storage isolation: scope derivation, v3 prefixing, any code path that could read/write the
   public v2/v1 keys while scoped (adoption bug), cross-account leak via stale tab reasoning,
   PII in keys, forged-slug hardening (server ignores client profile_slug when flag on; fixture
   never reaches non-owner responses — trace every response field incl. profile names in the
   four APIs AND the page render).
D. Consequence-stack truth: structural immutability (editor genuinely removed, not readOnly),
   append-only discipline, completed-action states, marker gate (client AND server; try to
   defeat the server pattern with crafted answers both directions: false positive on "[sic]"/
   "M[1-9]", false negative on a surviving coach marker), request-binding drops per element,
   duplicate submission, one-retry rule.
E. AI provenance: generic gets no member evidence; grounded/Compare fail closed for non-owner;
   owner grounds on petec fixture only; follow-up affordance visibly unavailable; no invented
   insufficiency content; no blended provenance in Compare rendering.
F. Media truth: no blob/URL in any payload; revocation on every teardown path (enumerate them);
   no permission on arrival; no inference strings.
G. History/Complete truth: four states distinct; comparison gate exact string + threshold; no
   false saved/cleared claims; scoreless.
H. Visual fidelity sampling: open at least 6 of the 19 comparison screenshots in
   `artifacts/2026-08-11-interview-studio-authenticated/visual-comparison/` side-by-side with
   their locks and judge composition/hierarchy/state truth (not pixel identity). Flag any
   material mismatch as P1.
I. Test honesty: every rewritten test in SLICE_NOTES — was anything weakened? Run the six named
   suites yourself and the full discover; reconcile the failure set against the four inherited
   items named in SLICE_NOTES.
J. Copy truth: the exact locked strings present; no forbidden claims ("saved to your account",
   scores, STAR, inference, cloud sync).

K. Opus-finding closure verification (this pass is mandatory and comes first): the first
   independent review (Opus, against SHA 81d8f21) returned REJECT with: P1-1 clearLocalData
   null-crash leaving a false uncleared-state UI; P1-2 material lock divergence (green .is__card
   gradient bleed into complete/history cards; lock 08 dominant action disabled + missing card
   container; lock 09 truth-line order inversion + missing caption/chip dots; lock 11 missing
   COMPLETED QUESTIONS rail group, icon badges, gold rule; lock 12 native filter selects);
   P2-1 marker gate rejecting first-attempt member brackets; P2-2 client not consuming the
   server confirmations[] list; P2-3 missing lock-09 no-inference line + stale "public" copy;
   P3 legacy-redirect robots headers. For each: verify the closure ACTUALLY lands (live probe
   where Opus probed live — repeat its exact repros: seeded clear-history click; first-attempt
   answer "I built the pipeline. [I can share the architecture diagram if useful.]"; a
   confirmations-listed [TBD] placeholder blocking the gate), and check the fix introduced no
   new regression in its file. A closure that only updates SLICE_NOTES without the behavior
   changing is a P0.
   Context fact for pass A: commit 65651b4 (the Opportunity Slate lane activation) is part of
   origin/main's own history that this branch rebased onto — it is NOT part of this candidate's
   diff against main and needs no action.

Verdict: APPROVE (zero unresolved P0/P1) or REJECT with the finding list. Report as structured
data. Do not fix anything yourself.
