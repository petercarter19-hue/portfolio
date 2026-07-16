# PeerSlate Community and Slate Board Audit — 2026-07-16

## Decision summary

The navigation and front-end structure are ready for the backend phase, with
one deliberate limitation: Community, Journal, Slate Board, and News still
need their protected production services before they can be called live
member features.

Voice and microphone work is explicitly out of scope for this change. It
remains owned by the parallel voice implementation.

## What changed

| Product surface | Current destination | Status |
| --- | --- | --- |
| Community Feed | `/the-slate` | Canonical Community page |
| News Feed | `/the-slate?view=news` | Second mode on the same page; honest empty state until a source service exists |
| Slate Board | `/petec/slate-board` | Single planning surface |
| Daily work | `#daily-check-in` on Slate Board | Merged into the Board as a private progress capture |
| Paths and milestones | `#paths-and-milestones` on Slate Board | Merged into the Board |
| People & Interests | Legacy URL redirects to Community | Retired and source/API/assets removed |
| Feed Preview | Legacy URLs redirect to Community | Retired as a destination and label |
| My Slate / Daily Slate | Legacy URLs redirect to relevant Board anchors | Retired as separate planning pages |

Community now exposes exactly two visible modes: **Feed** and **News Feed**.
The desktop right rail contains exactly one private, browser-saving **Journal
Note**. At tablet and mobile widths it moves below the Feed rather than
disappearing.

The Board now carries both former planning ideas: a **Today on your Slate**
check-in and a **Paths & milestones** entry point beneath the dominant Board.
A private Journal Note can be queued in Community and appears as a private
Board note when the Board opens in the same browser.

The old People & Interests source was removed rather than merely hidden. This
also removes a pre-backend privacy defect: its fixture-backed API could return
private-labelled posts without a member identity and expose its raw author
key.

## Verification completed

### Automated

- Full regression suite: **185 tests passed**.
- JavaScript syntax checks passed for Community and Slate Board scripts.
- Python compilation passed for `app.py`.
- Route sweep found no unexpected 5xx responses across the primary public
  pages, Community/Board legacy redirects, sitemap/robots, and protected API
  endpoints.
- Link crawl checked 42 first-party URLs rendered by the homepage, Community,
  Slate Board, résumé, and Interview Studio; none returned 4xx or 5xx.
- Redirects are one hop. The retired Community and planning routes point to
  Community or the appropriate Slate Board anchor.

### Browser audit

| Check | Result |
| --- | --- |
| Desktop Community at 1280 px | Feed and News Feed tabs render; Journal Note is visible to the right; no horizontal overflow |
| Tablet Community at 1024 px | Journal Note moves below Feed; no horizontal overflow |
| Mobile Community at 390 px | Feed tabs fit; Journal Note remains available below Feed; no horizontal overflow |
| News Feed | URL becomes `?view=news`; it states that no provider is connected instead of inventing headlines |
| Journal Note | Autosaves locally, then transfers to the Board as a private note in the same browser |
| Daily Slate replacement | Opens a private Board note with `Today` and `Progress update` preselected |
| Slate Board sharing | Opens an honest status panel: sharing, invitations, and publishing are not connected |
| Browser console | No warnings or errors observed during the Community/Board pass |

## Backend readiness findings

### P1 — resolve before a production member launch

1. **Canonical data and identity are still required.** Community posts,
   replies, responses, saves, Journal Notes, Board notes, and daily updates
   are browser-local or fixture-based. Build one authenticated record model
   with audience/placement metadata, then make Feed a projection of Journal
   records rather than a second store.

2. **News needs a product contract before implementation.** Select approved
   providers and define attribution, licensing, freshness, caching, failure
   behavior, moderation, and admin controls. The current empty state is
   intentional until those choices exist.

3. **CI deploys without running the test suite.** `azure-pipelines.yml`
   installs dependencies and deploys, but does not run unit tests, syntax
   checks, or a smoke test. It also targets Python 3.12 while this local audit
   ran under Python 3.14. Add a test stage on the deployment runtime before
   merging backend work.

4. **Rate limiting needs shared production storage.** Flask-Limiter currently
   uses in-memory storage. It will not be reliable across workers or instances;
   configure Redis or equivalent before exposing authenticated write and AI
   endpoints at scale.

5. **Security headers and global request limits are absent.** The audited HTML
   response has no CSP, HSTS, `X-Content-Type-Options`, clickjacking,
   Referrer-Policy, or Permissions-Policy header. There is also no global
   Flask request-size limit. Add these at the app and/or Azure edge before
   accepting uploads or public writes.

6. **Startup is coupled to the AI key.** `app.py` refuses to start without
   `ANTHROPIC_API_KEY`, even for static pages, and uses that key to derive the
   fallback interview-context signing secret. Decouple static startup from AI
   availability and require a dedicated signing secret in production.

### P2 — address during backend hardening

1. The generic `/api/chat` route has input limits and rate limiting but does
   not share the PeerSlate API blueprint's same-origin write guard. Consolidate
   the request-integrity policy across all mutating endpoints.

2. Board file attachment remembers a filename only; it does not upload a file.
   The Share panel is now honest and non-mutating, but real sharing requires
   authenticated permissions and audit records.

3. Some Board controls remain intentional non-backend states: redo is
   disabled, AI assistance is disabled, and voice/listening is not a recording
   implementation. Do not replace the parallel voice work; connect it only
   after the media/privacy contract is approved.

4. Protected PeerSlate API endpoints correctly return 401 without an identity.
   The optional living-resume database endpoints return 404 while their feature
   flag is off. Treat these as expected pre-backend states, not public-link
   failures.

## Release gate

**Safe to review visually and use as the front-end baseline:** yes.

**Safe to present as a live, multi-member Community or synced Board:** no,
until P1 items 1–6 are addressed. In particular, do not promise persistence,
sharing, publishing, news, file upload, or real audio capture until their
authenticated services are deployed and tested.

## Implementation notes

- The canonical Community route is `/the-slate`; do not add another Feed page.
- Preserve legacy redirects while shared bookmarks age out.
- Keep the Board dominant. Daily capture and milestone direction stay in or
  immediately beneath it.
- Preserve the `View As`/audience-security concept in future work. The retired
  term was **Feed Preview**, not a reason to remove audience checks.
