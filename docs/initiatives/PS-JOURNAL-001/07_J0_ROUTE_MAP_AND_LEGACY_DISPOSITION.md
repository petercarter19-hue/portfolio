# PS-JOURNAL-001 — J0 Route Map and Legacy Disposition

**Author:** Claude Code (Fable), architect/manager · 2026-07-21
**Status:** **APPROVED — owner decision, Pete, 2026-07-21** ("Options A. Close
all three"). Option A route names are the approved J1 route map; the
`/app/capture` → composer-opening 302 transition is approved for the J1
frontend release wave; and the legacy prompt-journal API remains untouched
until its own package. This satisfies §5 and closes the PS-JRN-IA-002 route
gate for the J1 slice: the approval locks the collision-audited J1 route
paths. The desktop/mobile navigation-placement map remains an explicit later
decision per site rule 69 and IA-002's map clause. Routes beyond this slice
still require their own approval.

## 1. Current inventory (audited on `main` @ 9d2efe3)

| Surface | Route(s) | What it is today |
|---|---|---|
| Owner capture page | `/app/capture` (GET/POST) + voice/photo/moment sub-routes | The released owner Capture page (PS-CAPTURE-001/002); today capture is a *place* |
| Moment review | `/app/moments/<key>/review` + save/confirm/discard | The released 3-step proposal flow |
| Legacy journal API | `/api/journal/today`, `/api/journal/history`, `/api/journal/responses` | The OLD daily-prompt feature (`usp_GetTodayJournalPromptForUser`, `usp_GetUserJournalHistory`, `usp_SaveJournalResponse`). Not the one-Journal |
| New J1 API (specified, not yet implemented) | `/api/journal/moments` (GET/POST, flag-off) | Derived-Journal read + one-step Save Moment per the J1 backend brief |
| Owner workspace | `/app` (logged-out → sign-in redirect; authenticated → owner_workspace "My PeerSlate"; Owner Home backend flag-off) | The signed-in shell the Journal will live inside |

## 2. Proposed target routes (Pete picks/edits)

**Recommended: Option A.**

| Concern | Option A (recommended) | Option B |
|---|---|---|
| The one Journal (owner) | **`/app/journal`** | `/app/my-journal` |
| Moment detail | **`/app/journal/moments/<moment_key>`** | `/app/moments/<key>` (reuse) |
| Journal data API | **`/api/journal/moments`** (specified in the J1 backend brief; not yet implemented) | `/api/v1/owner/journal` |
| Capture | **No route.** The composer is an in-context action in the owner shell; no `/app/capture` in target IA | Keep `/app/capture` as a redirect/opener only (never a standalone Capture page) |

Why A: `/app/journal` reads naturally, sits inside the authenticated `/app`
shell, does not collide with the public `/the-slate` world, and honors
"Capture is an action, not a place."

## 3. Legacy disposition (proposal)

| Legacy | Disposition | When |
|---|---|---|
| `/app/capture` page | Keep working during J1 (it is the released owner surface). After the universal composer ships in the shell (J1 frontend accepted), `/app/capture` becomes a **302 → `/app/journal`** that auto-opens the composer — a migration-period compatibility affordance per `PS-JRN-IA-006`, not a target-IA feature. Under any option, `/app/capture` never persists as a standalone Capture destination page; keeping the redirect permanently (vs. time-boxing it) is itself an owner decision | J1 frontend release wave |
| 3-step proposal routes (`/app/moments/*`) | Keep. They remain the review/edit surface for existing captures; the new one-step `usp_SaveMomentForOwner` covers the composer path. Consolidation is a later, separate decision | No change in J1 |
| `/api/journal/today\|history\|responses` (daily-prompt) | Keep serving, **rename internally as "prompt journal (legacy)"** in comments only. Do not extend it. Retirement (with data reconciliation per the migration rules in doc 03) is its own later package — the old responses may hold member text that must be offered a one-time review path, never silently converted | Separate future package |
| Public fixture `/the-slate/daily` "Daily Slate" | Unchanged — it is the public sample world, not the member Journal | No change |

## 4. Non-collision guarantees

- New API path `/api/journal/moments` does not overlap the three legacy
  `/api/journal/*` paths.
- The J1 backend lane touches no existing route; that lane will add flag `PEERSLATE_JOURNAL_ENABLED`
  (default false), so `/app` behavior stays unchanged until the visual gate passes.
- The Owner-Home frontend lane (PS-HOME-FRONTEND-001, Codex) owns the `/app`
  shell files; the Journal frontend must reserve files only after that lane's
  state is checked at its own J1-frontend entry gate.

## 5. Gate closure record (was: what Pete needs to say)

All three were approved verbatim by Pete on 2026-07-21:

1. ✔ "Option A" for the route names.
2. ✔ The `/app/capture` → composer deep-link transition (302 after the
   frontend ships).
3. ✔ Leaving the legacy prompt-journal API alone until its own package.
