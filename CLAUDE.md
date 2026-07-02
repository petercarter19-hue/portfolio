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
