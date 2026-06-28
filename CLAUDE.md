# Pete & Danielle Carter — Portfolio Project Memory

## Who I'm working with
- **Pete Carter** — building his first website, beginner coder on Mac (MacBook Pro 14" M5)
- Email: carterfamily1009@gmail.com
- GitHub username: petercarter19-hue
- GitHub repo: https://github.com/petercarter19-hue/portfolio
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
6. **Private Home Assistant Dashboard** — login required, connects to Pete's Home Assistant smart home system

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
- venv folder exists — Flask is installed inside it
- app.py ✅ — complete with all 6 routes (Pete typed with Claude's help)
- templates/base.html ✅ — complete shared layout (Pete typed)
- .gitignore ✅ — excludes venv, __pycache__, .DS_Store, .env
- GitHub connected ✅ — code pushed, branch: main
- Still needed: static/css/style.css, index.html, about.html, work.html, skills.html, hobbies.html, contact.html

## GitHub Info
- Repository: https://github.com/petercarter19-hue/portfolio
- To push future changes: git add . → git commit -m "message" → git push

## Immediate Next Steps
1. Create static/ folder and static/css/style.css — Pete types it (CSS visual styling)
2. Create templates/index.html — Pete types it (home page)
3. Create remaining page templates one at a time — Pete types each
4. Fill in real content (PhD, PMP, MBSE, work history, hobbies)
5. Eventually: add Claude API chatbot widget (floating, streams responses)
6. Eventually: add private Home Assistant dashboard (login required)

## Teaching Approach — IMPORTANT
- Pete is a complete beginner on Mac, limited PC experience too
- ALWAYS explain every step in detail — never assume prior knowledge
- ALWAYS explain what type of code we are writing (Python, HTML, CSS, etc.) and why
- ALWAYS explain what each line of code does before Pete types it
- Pete types all the code himself — Claude should NEVER create files without walking Pete through it first, line by line
- Using Cowork (Claude desktop app) to get help
- The venv folder must be activated before running Flask: `source venv/bin/activate`

## Session Notes (2026-06-25)
- Files app.py, templates/base.html, templates/index.html, static/css/style.css were created BY Claude (not Pete) — delete these and rebuild together so Pete learns properly
- Flask ran successfully at http://127.0.0.1:5000 — confirmed working
- VS Code is fully set up with extensions: Live Server, Prettier, GitHub Pull Requests, PowerShell, Claude Code, Python, and others
- venv is activated and Flask is installed and working
