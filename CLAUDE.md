# Pete & Danielle Carter — Portfolio Project Memory

## Who I'm working with
- **Pete Carter** — building his first website, beginner coder on Mac (MacBook Pro 14" M5)
- Email: petercarter19@gmail.com
- GitHub username: petercarter19-hue
- GitHub repo: https://github.com/petercarter19-hue/portfolio.git
- Location: Athens, AL

## The Project
**Personal Portfolio Website** — a Python Flask web app with AI features powered by the Claude API.

Two goals:
1. Demonstrate real, hireable tech skills
2. Create a live public-facing site to share with employers

## Pete's Credentials (to feature on the site)
- PMP certification
- PhD
- MBSE certification
- Work experience & career history
- Smart home & hobbies

## Planned Pages
1. **Home / About** — bio, intro
2. **Work Experience & Career**
3. **Skills & Certifications** (PMP, PhD, MBSE)
4. **Hobbies Showcase** — smart home projects
5. **Contact Form**
6. **Private Admin/Assistant Dashboard** — login required

## AI Features Planned
1. **Visitor Chatbot** — floating widget on all pages, visitors ask questions about Pete, answers from his resume/bio, streams responses
2. **AI Writing Tool** — takes bullet points, returns polished professional paragraphs (behind the scenes)

## Tech Stack
- **Backend**: Python + Flask
- **AI**: Anthropic Claude API
- **Frontend**: HTML/CSS/JavaScript (templates via Flask/Jinja2)
- **Version Control**: GitHub

## VS Code Setup (completed 2026-06-25)
- VS Code installed ✅
- Portfolio folder opened and trusted ✅
- Extensions installed: Live Server, Prettier, Auto Rename Tag, GitHub Pull Requests, PowerShell, Claude Code, and others ✅
- venv (Python virtual environment) created inside /Users/petercarter/portfolio ✅

## Current State of Project
- Portfolio folder: /Users/petercarter/portfolio
- Flask app is running from app.py with routes for home, about, work, skills, hobbies, and contact
- Site runs at http://127.0.0.1:5000 with 6 routes (home, about, work, skills, hobbies, contact)
- Chatbot MVP 1 is active: static/js/chatbot.js sends visitor questions to the Flask /api/chat route, and app.py calls the Anthropic Claude API
- Chatbot answers are intentionally short: 1 to 3 concise, polished sentences with the most impactful information first
- Chatbot answers should use plain text only: no Markdown, hashtags, bold markers, bullet lists, numbered lists, or salesy follow-up questions
- Chatbot responses can use a second short paragraph when an answer has more than one idea
- app.py includes clean_chatbot_reply() to remove display-only Markdown symbols before sending responses back to the browser
- app.py keeps knowledge files separated and uses build_knowledge_context() to send Claude only the most relevant knowledge files for each question
- Suggested chatbot questions now disappear after any visitor question, whether the user clicks a suggestion or types a custom question
- Knowledge base complete: docs/knowledge/ folder with 6 files
- chatbot.css uses white-space: pre-line so paragraph breaks from AI responses display inside chat bubbles
- anthropic and python-dotenv installed in venv
- .env file with ANTHROPIC_API_KEY exists on this Mac and must never be displayed, edited, or committed

## Immediate Next Steps
1. Continue testing MVP 1 chatbot answer quality with real recruiter-style questions
2. Consider creating a curated chatbot-specific knowledge file so responses rely on polished source material instead of long resume-style files
3. Add server-side logging of conversations
4. Build admin dashboard to view chat logs
5. Eventually: smarter retrieval, security hardening, and public deployment

## Recent Session Updates (2026-07-05/06 — PeerSlate redesign pulled, iPad-sizing attempt reverted, Mac, branch main)
- IMPORTANT: the Mac repo was 4 commits behind GitHub — a full "PeerSlate platform" redesign built elsewhere (tabbed profile shell, platform nav with Career Search/My Network/Explore Profiles/For Recruiters, 8 themes with gray-slate as the new default, slate photo backgrounds in static/images/slate-backgrounds/, mockups in static/images/background-templates/, app.py rewritten with flask-limiter + canonical-URL redirects). Pulled onto the Mac this session. Much of the theme/layout info in the sections below this one is now OUTDATED (blueprint-light is no longer the default, the old site-menu header is gone).
- .claude/launch.json gotcha: the pull brought the Windows python path (venv/Scripts/python.exe); switched back to venv/bin/python for Mac. This will flip-flop between machines until made smarter.
- Pete's ask: every screen from iPad Mini (744px) on up should show the desktop layout, not a stacked/blown-up mobile-style one.
- FIRST ATTEMPT (reverted — do not redo this): retargeted every tablet breakpoint in style.css/resume.css to max-width:743px (phone-only) and added a script to scale desktop browser windows down with CSS `zoom` between 744-1279px. This broke the profile header bar's background color: `.profile-header` (and `.profile-tabs`) use `background-attachment: fixed` so their stone-photo texture lines up seamlessly with the page behind them (see "Align profile band and tab strip stone crops on slate themes" in git log) — `zoom` moves an element visually but fixed-attachment backgrounds stay pinned to the true, un-zoomed browser viewport, so the header's texture no longer lined up with the page around it once zoomed (worse in Safari, which Macs default to). It ALSO broke `.platform-nav`: the nav's own 1180px breakpoint (nav links wrap to a second row once they don't fit) is load-bearing, not cosmetic — collapsing it to 743px too made the logo/nav-links/theme-dots/sign-in overlap at any width below ~1180px, since the header genuinely does not fit in one row below that. Lesson: don't assume every tablet breakpoint in a design is "mobile-style bloat" — check what each one actually does before retargeting it.
- FINAL STATE (2026-07-06): style.css and resume.css breakpoints are back to exactly what was pulled from GitHub (1180/1040/860/780/980/1240/900/1020/940px etc., all untouched) — confirmed identical via `git diff 2a39b72 -- static/css/style.css static/css/resume.css` (empty). Only base.html changed: the real-tablet part of the sizing script survives (swaps `<meta viewport>` to width=1280 on genuine touch devices ≥744px — native browser scaling, doesn't touch backgrounds, so it doesn't have the fixed-attachment bug). The desktop-browser-window zoom hack was removed entirely; resizing a desktop browser window into tablet widths now just uses the site's normal (original) responsive CSS.
- Practical implication: a real iPad Mini gets pixel-perfect desktop layout (via the viewport-meta trick). A desktop browser window manually narrowed to iPad-Mini width will NOT be pixel-identical to desktop — it'll gracefully reflow using the original tablet breakpoints (nav wraps to two rows around 1180px, hero/lifecycle stack around 1180px, full phone stacking still starts at 780px). This was a deliberate trade-off after the pixel-perfect approach proved incompatible with the slate-photo theme's fixed backgrounds.
- Verified in preview at 744px and 1000px (both screenshot cleanly: consistent header/page colors, no nav overlap, normal-sized buttons) and 1440px (DOM/bounding-box check only — the screenshot tool had an unrelated thumbnail-rendering glitch at that exact size that reproduced even on a fresh server with no code involved).

## Recent Session Updates (2026-07-05 — Blueprint Light theme, Mac, branch main)
- New "Blueprint Light" theme added and made the SITE-WIDE DEFAULT (base.html body data-theme + theme-preview.js defaultTheme both say blueprint-light; meta theme-color now #f4f9fc). Returning visitors with a saved theme in localStorage (key peerslateTheme) keep their old choice — clear localStorage to see the new default.
- Palette (from Pete's codex instructions file): pale blueprint-blue page (#f4f9fc) with a faint 48px grid, navy text (#08204a), teal/cyan primary (#0796b8 / #0ea5c6) mapped onto the existing --color-gold variable slots, blue secondary (#1f6feb), soft blue-gray borders (#cfe0eb), navy-tinted shadows.
- Amber (#f59e0b) is reserved for money metrics only: metrics_strip.html now wraps $36M+/$900M/$19.2M in <strong class="metric-money"> (both scrolling sets); the class is styled only under blueprint-light.
- Implementation: variable block sits with the other theme presets near the top of style.css; structural overrides live at the end of style.css's LIGHT THEME COMPATIBILITY section (mirrors the slate-light pattern); resume-page-specific overrides appended to resume.css (cache-buster bumped to ?v=blueprint-light-1); theme button added to the site-menu dropdown (5 themes now); theme-preview.js cache-buster bumped to ?v=theme-preview-2.
- Hardcoded-dark surfaces that needed explicit light overrides: .hero/.my-story-page/.work-page/.resume-page circuit banners, .work-hero-panel, .story-journey__layout, .fun-fact-card, .drive-card, .timeline-item__icon (+ its --light icon variant), lifecycle .cycle-arc--gold arrows + #arrow-gold SVG marker (teal in light mode), #chat-input, #chat-send, .resume-ai-panel/.resume-ai-suggestion/.resume-skill-button/.resume-skill-popover.
- Verified in preview on home, Projects, My Story, Resume, Contact + chat widget; no console errors. Left dark on purpose: .mock-sidebar and .mock-window--dark (app-screenshot mockups inside project cards).
- SLATE LIGHT THEME REMOVED (same session): dropdown button deleted from base.html, variable block + entire compatibility section deleted from style.css (~210 lines). theme-preview.js now validates the saved localStorage theme against the rendered theme buttons and falls back to the default if the saved name no longer exists (protects visitors who had slate-light saved); cache-buster bumped to ?v=theme-preview-3. Site now has 4 themes: command-gold, modern-blue, blueprint-light (default), secure-green.
- NOTE: Flask runs with debug off unless FLASK_DEBUG=true, so Jinja caches templates — template edits need a server restart to show up in the preview.
- MOBILE TYPE SCALE (same session): Pete flagged that the homepage and resume page looked "blown up" on phones vs My Story. My Story's phone hero (24px h1 at 375px wide) is now the reference scale: homepage .hero-copy h1 phone clamps reduced (780px block: clamp(1.6rem,5vw,2.3rem); 620px block: clamp(1.5rem,6.4vw,2.05rem)); .projects-copy h2 phone clamp reduced to clamp(1.55rem,6vw,1.9rem) — note the 620px block has TWO .projects-copy h2 rules, the later one wins; hero Interactive Resume button stays auto-width on phones (all other .btn stay full-width); resume-hero h1 phone clamp reduced from 12vw (45px!) to clamp(1.6rem,6.4vw,2.2rem) and .resume-hero__name to 1.02rem (resume.css cache-buster now ?v=mobile-scale-1). Rule of thumb going forward: phone headline sizes should match My Story's scale (~24px h1, ~24px section h2 at 375px).

## Recent Session Updates (2026-07-04 — interactive resume redesign, Mac, branch main)
- /petec/resume page rebuilt to match Pete's mockup: hero is now name headline (left) + "Ask Pete's AI Assistant" panel (right) with the shared search partial and 4 suggested-question chips (2x2) from resume_data.json suggested_ai_questions.
- Removed from the resume page: Recruiter Quick View track filtering (and all its JS), the full-width AI bar below the hero, the Skills to Evidence category filter buttons and skill front summaries, the Selected Engineering Impact case-study section, and the Download/Print/LinkedIn bar. resume_data.json itself was NOT changed — unused data (recruiter_tracks, case_studies, metrics 5-8) is still there if needed later.
- Impact strip now shows only the first 4 metrics from resume_data.json ($36M+, 16 to 0, 70%, 52%); cards still click through to the connected role evidence. Metric grid is 4-across / 2x2 at every width per the groups-of-4 rule.
- Skills: all 21 public skills as compact name-only cards, 7 across on desktop (3 rows), evidence popovers unchanged. Pete wants to fine-tune this grid later.
- resume.js rewritten slim (popovers, role selection, metric jumps, ask-AI buttons, suggestion chips). Cache-buster bumped to ?v=resume-redesign-5 on resume.css/resume.js.
- Career Experience and Education sections untouched.
- OBSERVED during testing: the chatbot answered a resume question with "two decades of experience," which does not match the career history (EE degree 2020). Knowledge-base/prompt quality issue to review.

## Recent Session Updates (2026-07-02 — header menu, Fun Facts, card polish; branch feature/my-story-page)
- Pete is now working on a Windows 11 machine (repo at C:\Users\peter\Documents\portfolio). venv activation is `venv\Scripts\activate`; .claude/launch.json points at venv/Scripts/python.exe. app.py reads the PORT env var (falls back to 5000).
- Site is planned to become a multi-tenant business (other people get their own portfolio sites). First step: top-left dropdown menu in the header (currently just "Homepage"); brand + nav links shifted right to make room.
- Header: LinkedIn icon now uses official brand colors (#0A66C2 + white); "Case Studies" nav renamed to "Projects" (still /work); Ask Pete AI buttons restyled — squared corners, gold fill/outline, uppercase.
- Homepage: "View Case Studies" hero button removed; "Interactive Resume" is now the single gold primary CTA (still "#" placeholder).
- Metrics strip is now a framed, rounded strip that stops at the content rail (no more edge-to-edge band on big screens); scrolling cards cut off cleanly at the frame ends.
- My Story: collage enlarged (up to 470px wide); hero text column stretches so the banner bottom-aligns with the collage (dead gap fixed); Let's Connect card removed; "Life Beyond the Work" expanded to 8 interests in a 4x2 grid; new FUN FACTS section shows 3 random facts per page load (pool lives in a script at the bottom of my_story.html) with a "Show Me More" shuffle button.
- PETS: Pete has two DOGS, Blazer and Falcon. The old "proud cat dad to Nala and Mochi" line was wrong and has been removed.
- Layout rule from Pete: any group of 4 items must display as 4-across or 2x2 at every screen width — never 3+1. Value chips, timeline, drive cards, and the interest grid all follow this now.
- Card hover rule from Pete: every card-style surface site-wide gets the project-card "pop out" hover (translateY(-4px) + border + shadow). Shared CSS rule covers .drive-card, .story-card, .fun-fact-card.
- KNOWN ISSUE to fix: homepage hero eyebrow still says "PhD Student" — violates the PhD wording rule below (admitted, starts January 2027). Ask Pete for preferred wording.

## Earlier Session Updates (2026-07-01 — My Story build, branch feature/my-story-page)
- New /my-story page (templates/my_story.html + route in app.py): hero with circular portrait placeholder, CURRENT FOCUS banner, journey timeline (2020 EE degree, 2021–2024 DoD/USAF, 2024–2025 L3Harris, 2025–Present Northrop Grumman — dates verified against docs/knowledge/career_history.md), values cards, three info cards, shared metrics strip.
- Header updated: "SYSTEMS ENGINEER" typo fixed; nav renamed to Case Studies / Expertise / My Story; Hobbies and About removed from nav (pages still exist at /hobbies and /about); LinkedIn icon button added (www.linkedin.com/in/pete-carter19); active-page gold underline added via aria-current="page"; phone nav links restored (were hidden under 620px).
- Metrics strip extracted into templates/partials/metrics_strip.html, included by both index.html and my_story.html, and made 15% thinner (66px min-height).
- Homepage hero headline changed to "Engineering better outcomes through technology, leadership, and systems thinking."; "Download Résumé" renamed to "Interactive Resume"; lifecycle box labels updated (Define / Requirements / Architecture / Implement & Integrate / Verify & Validate / Deploy & Sustain); blue inner arrows removed.
- Outstanding placeholders: real headshot for the My Story portrait; Résumé links still point to "#"; "View Full Timeline" temporarily links to /work.
- PhD wording rule: Pete is ADMITTED to the University of South Alabama Systems Engineering Ph.D. program with an expected January 2027 start — never describe him as a current PhD student before then.

## Earlier Session Updates
- Top navigation now stays sticky while scrolling on desktop/tablet screens, but scrolls away normally on phone screens.
- Chatbot suggestion buttons now disappear after the first submitted question.
- Chatbot prompt was improved for grammar, concise answers, plain text, short paragraphs, and stronger professional tone.
- Chatbot output cleanup was added on the server side to remove Markdown artifacts before responses reach the browser.
- Chatbot context selection was improved so Claude receives focused knowledge files based on the visitor's question instead of the entire knowledge base every time.

## Notes
- Pete is a complete beginner on Mac, limited PC experience too
- Prefers step-by-step, detailed explanations — no assumptions
- Using Cowork (Claude desktop app) to get help
- The venv folder must be activated before running Flask: `source venv/bin/activate`
- When code changes are made, explain the filename, actual line numbers, what the code was before, what it is now, and why the change works
- Add helpful comments directly in edited files when the change teaches an important concept or prevents future confusion
- Before editing files Pete may have open in VS Code, remind him to press Cmd+S
