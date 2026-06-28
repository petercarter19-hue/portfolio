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
- Flask app fully built: app.py, templates/, static/ all exist
- Site runs at http://127.0.0.1:8080 with 6 routes (home, about, work, skills, hobbies, contact)
- Chatbot MVP 0 complete: floating widget, slide-in panel, mock responses, suggestion chips
- Knowledge base complete: docs/knowledge/ folder with 6 files
- chatbot.css and chatbot.js both built and committed
- anthropic and python-dotenv installed in venv
- .env file with ANTHROPIC_API_KEY exists on each machine (never committed to GitHub)

## Immediate Next Steps
1. Build MVP 1: Flask /api/chat route + real Claude API integration
2. Update chatbot.js to call /api/chat instead of getMockResponse()
3. Add server-side logging of conversations
4. Build admin dashboard to view chat logs
5. Eventually: RAG (smarter retrieval), security hardening, public deployment

## Notes
- Pete is a complete beginner on Mac, limited PC experience too
- Prefers step-by-step, detailed explanations — no assumptions
- Using Cowork (Claude desktop app) to get help
- The venv folder must be activated before running Flask: `source venv/bin/activate`
