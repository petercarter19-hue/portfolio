# Pete & Danielle Carter — Portfolio Project Memory

## Who I'm working with
- **Pete Carter** — systems engineer at Northrop Grumman, beginner coder
- Email: carterfamily1009@gmail.com
- GitHub username: petercarter19
- Location: Athens, AL

## The Project
**Personal Portfolio Website** — a Python Flask web app with AI features powered by the Claude API.

Two goals:
1. Demonstrate real, hireable tech skills
2. Create a live public-facing site to share with employers

## Pete's Credentials (to feature on the site)
- PMP certification
- PhD
- MBSE certification (Cameo/MagicDraw, SysML, IBM DOORS)
- Work experience at Northrop Grumman, L3Harris, U.S. Air Force/DoD
- Smart home & hobbies

## Computers Pete Uses
Pete works across two machines. Setup differs between them.

### MacBook Pro 14" M5 (primary dev machine)
- Portfolio folder: `/Users/petercarter/portfolio`
- Activate venv: `source venv/bin/activate`
- Run Flask: `python app.py` → site at http://127.0.0.1:8080
- Python interpreter in VS Code: `./venv/bin/python`

### Windows PC (secondary)
- Portfolio folder: `C:\Users\peter\Documents\portfolio`
- Activate venv: `.\venv\Scripts\activate`
- Run Flask: `python app.py` → site at http://127.0.0.1:8080
- Python interpreter in VS Code: `.\venv\Scripts\python.exe` (NOT .venv)
- Port 8080 used because Windows reserves port 5000

## Tech Stack
- **Backend**: Python + Flask
- **AI**: Anthropic Claude API (claude-haiku-4-5-20251001 for chatbot)
- **Frontend**: HTML/CSS/JavaScript (templates via Flask/Jinja2)
- **Version Control**: GitHub (repo: petercarter19/portfolio)
- **Key libraries**: python-dotenv, anthropic

## Project File Structure
```
portfolio/
├── app.py                    # Main Flask app — all routes live here
├── .env                      # API key — NOT in GitHub, create manually on each machine
├── .gitignore
├── CLAUDE.md
├── CODE_GUIDE.md
├── venv/                     # Virtual environment — NOT in GitHub
├── docs/
│   ├── knowledge/            # AI knowledge base files
│   │   ├── professional_summary.md
│   │   ├── career_history.md
│   │   ├── technical_skills.md
│   │   ├── accomplishments.md
│   │   ├── recruiter_faq.md
│   │   └── portfolio_projects.md  (empty — to be filled)
│   ├── chatbot_requirements.md
│   ├── approved_and_prohibited.md
│   └── session_log_2026-06-27.txt
├── static/
│   ├── css/
│   │   ├── style.css         # Main site styles
│   │   └── chatbot.css       # Chatbot widget styles
│   ├── js/
│   │   └── chatbot.js        # Chatbot widget behavior
│   └── images/
│       └── hero-collage3.png
└── templates/
    ├── base.html             # Shared layout — chatbot widget lives here
    ├── index.html
    ├── about.html
    ├── work.html
    ├── skills.html
    ├── hobbies.html
    └── contact.html
```

## Planned Pages
1. **Home / About** — bio, intro ✅ (built)
2. **Work Experience & Career** ✅ (built)
3. **Skills & Certifications** ✅ (built)
4. **Hobbies Showcase** ✅ (built)
5. **Contact Form** ✅ (built)
6. **Private Admin/Assistant Dashboard** — not started

## AI Chatbot — MVP Status

### MVP 0 — COMPLETE ✅
Fully styled chatbot widget with mock responses. No real AI.
- Floating "💬 Ask Pete AI" pill button, bottom-right, all pages
- Slide-in chat panel with navy/gold styling
- 4 suggested question chips
- Mock keyword-based responses in chatbot.js
- Mobile responsive

### MVP 1 — IN PROGRESS 🔄
Real AI responses via Claude API.
- [x] Anthropic account created, API key obtained
- [x] .env file created on Windows PC (must also create on Mac — see below)
- [x] python-dotenv installed
- [x] anthropic library installed
- [ ] Update app.py — add /api/chat route
- [ ] Update chatbot.js — replace getMockResponse() with fetch('/api/chat')
- [ ] Test with the 10 recruiter questions in chatbot_requirements.md

### MVP 2 — Not started
RAG-based retrieval — only send relevant knowledge chunks per question.

### MVP 3 — Not started
Rate limiting, prompt injection protection, admin dashboard.

## CRITICAL — .env Setup on Each Machine
The `.env` file holds the Anthropic API key. It is gitignored and never goes to GitHub.
You must create it manually on every machine you develop on.

**File location:** root of portfolio folder (same level as app.py)
**File contents:**
```
ANTHROPIC_API_KEY=your-key-here
```
Get the key from: https://console.anthropic.com/settings/keys

## Starting a New Session (checklist)
1. Open VS Code in the portfolio folder
2. Open terminal → activate venv (Mac: `source venv/bin/activate` / Windows: `.\venv\Scripts\activate`)
3. Pull latest from GitHub: `git pull origin main`
4. Confirm `.env` file exists with the API key
5. Run the server: `python app.py`
6. Site is at http://127.0.0.1:8080

## Git Workflow
- `main` branch = stable, working code
- Always pull before starting work: `git pull origin main`
- Commit at end of every session and push to GitHub
- Never commit: `.env`, `venv/`, `__pycache__/`, `.DS_Store`

## Notes
- Pete is a beginner — always explain the why, step by step, no assumptions
- Using Cowork (Claude desktop app) to get help
- VS Code Python interpreter on Windows must point to `venv` (not `.venv`)
- CRLF warnings from git on Windows are normal and harmless
