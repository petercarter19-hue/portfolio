# Current state (audited 2026-07-16, main @ 1002383a)

## Repository / delivery
- `origin` = Azure DevOps (production source of truth); `github` = mirror.
- Azure Pipelines (`azure-pipelines.yml`, pipeline id 1) deploys `main` to
  the `peerslate-pete` App Service. GitHub Actions deployment disabled.
- Working tree clean; untracked: local Bible docx copies only.
- Tests: 188 passing (`python -m unittest discover -s tests`).

## Route map (public — the whole site is currently logged-out-facing)
- Marketing/product: `/` (new three-scene homepage), `/experience` (old
  homepage, rollback), `/peerslate` (About PeerSlate marketing page).
- Pete public profile: `/petec/my-story` (+`/my-story`), `/petec/skills`
  (the **Evidence** page), `/petec/slate-board`, `/petec/resume` (+ ledger
  redirects), `/petec/projects` (+`/work`, `/projects`), `/petec/contact`,
  `/petec/hobbies`, `/petec/about`.
- Community: `/the-slate` (People & Interests corkboard = landing),
  `/the-slate/my-slate`, `/the-slate/daily`, `/the-slate/pulse`,
  `/the-slate/break`, legacy `/slate-feed*` redirects.
- Feed design preview: `/feed-living-stream` (+`/states`), labeled preview.
- Interview Studio: `/interview-studio` (+aliases) with real AI endpoints
  `/api/interview/{review,improve,model-answer,coach}`.
- AI: global chat launcher via `/api/chat` (grounded in approved public
  sources) — present in the header on EVERY page, including Community.
- Internal previews: `/_internal/design-system`, `/_internal/living-resume-v2`.

## Navigation today
- Global header (base.html): logo → `/`; Pete's Slate → `/petec/resume`;
  Community → `/the-slate`; Interview Studio; **About PeerSlate** (v1.2:
  must move to footer/marketing menu); header search; **Ask AI** button;
  Sign In (inert `href="#"`).
- Profile sub-header (all non-`/` pages): My Story / **Evidence** /
  Slate Board / Resume + Ask Pete AI (v1.2: Evidence must leave nav).
- Community in-page tabs: People & Interests / News Feed (soon) /
  Feed Preview.

## v1.2 term inventory (user-facing)
- **Evidence / evidence-backed / proof** in: `partials/profile_tabs.html`
  (nav tab), `skills.html` (page identity, ~12 uses), `resume2.html`
  ("Evidence-backed public profile", metric/proof labels),
  `partials/profile_shell.html`, `base.html` (search records: "Evidence —
  Skills backed by proof"), `interview_studio.html` ("Proof you may have
  missed — Optional approved evidence"), homepage partials
  (`_voice_hero.html` "Skill Evidence"; `_living_resume_scene.html`
  "Skills backed by evidence", "Evidence-backed" chip, "Strongest approved
  proof", "See the evidence", step 2 "Evidence — Inspect the proof"),
  `the_slate_daily.html`, `the_slate_feed.html` (retired template),
  `experience.html` (old homepage, kept as-is for rollback),
  `peerslate.html`, `design_system_preview.html` (internal preview).
- **Encourage** in: `feed-living-stream.js` (Feed preview action),
  `feed_living_stream_states.html`, `the_slate_people_interests.html`
  (comment actions in detail modal).
- **About PeerSlate**: header nav (base.html:158) + `/peerslate` page copy.
- **Feed Preview**: Community tab + header-search record (kept — it is a
  real labeled preview; naming stays until PS-FEED-002 replaces it).
- Job-related content: none found (no job routes/cards/listings). ✔
- **Original transcript**: `feed-living-stream.js` review dialog label.

## Community modules (fixture-driven, `static/data/people_interests_feed.json`)
- Left rail: people_moving, saved_notes, circles, topics.
- Right rail: **pick_me_ups (quote card)**, goal_checkin, **challenge**
  ("Weekend Challenge … 1,248 people joined" — fabricated count),
  **poll (Community poll)**, share_good — rules 26/33 ban quote rails,
  challenges, polls, and decorative engagement furniture. The board's
  reaction system is REACTION_TYPES = Applaud/Celebrate/Inspired/Rooting
  for you (+ goal "I'm in") in `services/people_interests_feed.py`
  (validated server-side; per-browser persistence only).
- Feed preview page (`/feed-living-stream`): Encourage/Comment/Save with
  simulated publish flow; clearly labeled sample data.

## Journal / Feed data reality
- No Journal exists (Pete: held for the private phase). The corkboard
  posts and Feed preview posts are fixtures; no duplication of a
  canonical record because no canonical record store exists yet.
- Daily Slate composer stores per-browser (localStorage) preview cards,
  honestly labeled.

## Resume / Constellation / PDF
- `resume_data.json` is the approved public résumé source (metrics,
  roles, skills+evidence_items, education, case studies). Career
  Constellation renders roles as anchors (partial: no project/
  achievement/promotion node types yet). PDF is a static file at
  `static/files/pete-carter-resume.pdf` (no Resume Creator).

## Interview Studio
- Real Claude-backed endpoints for review/improve/model-answer/coach.
- Copy uses "Proof you may have missed … approved evidence" (v1.2
  violation). No Best-practice/Use-my-history mode control yet; no
  session/history persistence (no auth); answers not stored server-side.

## AI boundaries
- `/api/chat` grounded in approved public portfolio sources; no private
  stores exist yet. Ask Pete AI appears inside Community via the global
  header/floating launcher (v1.2 rule 30 violation on Community routes).

## Auth / storage maturity
- `identity.py` decodes Azure Easy Auth principals (`get_current_identity`)
  and dev-identity env flags exist (`PEERSLATE_ALLOW_DEV_IDENTITY`) — the
  scaffolding for the private phase exists, but no login UI, no
  enforcement, no owner records, no private storage, no migrations.
  Azure SQL access exists behind `PEERSLATE_DATABASE_UI_ENABLED` seams.

## Color tokens
- `style.css` `:root`: `--ps-ink-950 #0a1b36`, `--ps-cloud-white #f6f8fc`,
  `--ps-product-indigo #4f5bd5`, `--ps-connection-azure #4ea3ff`,
  `--ps-ai-cyan #2ec8d3`, etc. (Foundation C blues). Page CSS files also
  hardcode blues (cinematic.css, people-interests.css, homepage-scenes.css,
  feed-living-stream.css, interview-studio.css…). No Iris Foundry tokens
  (`--ps-canvas #F7F4EE`, `--ps-primary #5A2D82`, bronze, teal) exist yet.

## Existing defects noted, out of scope here
- Sign In button is inert (`href="#"`) — becomes real in the auth phase.
- Site-wide `body{overflow:hidden auto}` + smooth scroll makes
  programmatic scrolling flaky in emulated browsers (cosmetic/dev-only).
