# ChatGPT Codex — Session Startup Prompt for Pete Carter's Portfolio

Copy and paste everything below this line into Codex at the start of every session.

---

You are helping Pete Carter build and maintain a personal Flask portfolio website on a Mac (MacBook Pro 14" M5). Pete is a beginner coder. Explain everything clearly and step by step. Never make assumptions about his setup.

---

## CRITICAL RULES — Read Before Doing Anything

These rules prevent mistakes that have already broken the project once. Follow them without exception.

1. **The project folder is `/Users/petercarter/portfolio`.** Never cd to any other location. There is no `Documents/Website/portfolio` or any similar path. If you are ever unsure, ask Pete to confirm the folder before running commands.

2. **Never create a new virtual environment.** A working venv already exists at `/Users/petercarter/portfolio/venv`. It has Flask, anthropic, and python-dotenv installed. Never run `python3 -m venv` or `python -m venv` under any circumstances.

3. **Always activate the existing venv with exactly this command:**
   ```
   source venv/bin/activate
   ```
   Never use `.venv`, `env`, or any other name. If the terminal prompt does not show `(venv)` at the start, the venv is not active. Do not run Flask until it is.

4. **The site runs at `http://127.0.0.1:5000`.** The port in `app.py` is set to 5000. Do not change it.

5. **Never touch, modify, or create a `.env` file.** The `.env` file contains Pete's private Anthropic API key. It already exists on this machine. Never display, copy, commit, or ask for its contents.

6. **Never commit `.env`, `venv/`, or `__pycache__/` to GitHub.** These are already excluded in `.gitignore`. Never change `.gitignore`.

7. **Always use `git commit -m "your message here"` with the `-m` flag.** Never run `git commit` without `-m`. It opens a Vim editor that is confusing for a beginner.

8. **Before editing any file Pete has open in VS Code, tell him to press Cmd+S first.** This prevents VS Code save conflicts.

---

## Who Pete Is

- Pete Carter — Systems Engineer at Northrop Grumman
- Beginner coder, learning Python and web development
- Mac user (MacBook Pro 14" M5), using VS Code
- Email: petercarter19@gmail.com
- GitHub username: petercarter19-hue
- GitHub repo: https://github.com/petercarter19-hue/portfolio.git

---

## The Project

A personal portfolio website built with Python and Flask. It showcases Pete's engineering career and demonstrates his AI and software skills to recruiters.

**Two goals:**
1. Show real, hireable tech skills
2. Create a live public site to share with employers

**Tech stack:**
- Backend: Python + Flask
- AI: Anthropic Claude API (claude-haiku-4-5-20251001 model)
- Frontend: HTML, CSS, JavaScript (Jinja2 templates)
- Version control: GitHub

---

## Exact Folder Structure

```
/Users/petercarter/portfolio/
├── app.py                          ← Main Flask app, all routes defined here
├── .env                            ← API key — NEVER touch this
├── .gitignore                      ← NEVER change this
├── AGENTS.md                       ← Project memory for Cowork (Claude desktop app)
├── CLAUDE.md                       ← Project memory for Cowork (Claude desktop app)
├── CODE_GUIDE.md                   ← General coding reference
├── CODEX_PROMPT.md                 ← This file
├── docs/
│   ├── chatbot_requirements.md
│   └── knowledge/                  ← Knowledge base files for the chatbot
│       ├── professional_summary.md
│       ├── career_history.md
│       ├── technical_skills.md
│       ├── accomplishments.md
│       ├── recruiter_faq.md
│       └── portfolio_projects.md
├── static/
│   ├── css/
│   │   ├── style.css               ← Main site styles
│   │   └── chatbot.css             ← Chatbot widget styles
│   ├── js/
│   │   └── chatbot.js              ← Chatbot widget behavior
│   └── images/
├── templates/
│   ├── base.html                   ← Shared layout used by every page
│   ├── index.html                  ← Home page
│   ├── about.html
│   ├── work.html
│   ├── skills.html
│   ├── hobbies.html
│   └── contact.html
└── venv/                           ← Python virtual environment — NEVER recreate this
```

---

## How to Start a Session

Run these commands in the VS Code terminal at the start of every session:

```bash
cd /Users/petercarter/portfolio
source venv/bin/activate
python app.py
```

The terminal will show:
```
* Running on http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in a browser to see the site.

To stop Flask: press `Ctrl+C` in the terminal.

---

## Current State of the Project

**Completed:**
- Flask app with 6 working routes: `/`, `/about`, `/work`, `/skills`, `/hobbies`, `/contact`
- Shared base template (`base.html`) used by all pages
- Main CSS (`style.css`) with navy/gold color scheme, responsive layout, sticky header
- Chatbot widget MVP 0 complete: floating button, slide-in panel, suggestion chips, mock responses
- Knowledge base: 6 Markdown files in `docs/knowledge/` with Pete's professional background
- `anthropic` and `python-dotenv` packages installed in venv
- `.env` file with `ANTHROPIC_API_KEY` already exists on this machine

**Next step — MVP 1 (real Claude API):**
- Add `/api/chat` POST route to `app.py`
- Load knowledge base files as context for Claude
- Replace `getMockResponse()` in `chatbot.js` with a `fetch()` call to `/api/chat`

---

## app.py — Current Contents

```python
import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/work')
def work():
    return render_template('work.html')

@app.route('/skills')
def skills():
    return render_template('skills.html')

@app.route('/hobbies')
def hobbies():
    return render_template('hobbies.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## Git Workflow

After making changes, save them to GitHub with:

```bash
git add .
git commit -m "Brief description of what changed"
git push origin main
```

To check current status before committing:
```bash
git status
```

To pull changes from GitHub (e.g., work done on another computer):
```bash
git stash
git pull origin main
git stash pop
```

---

## Installed Python Packages (inside venv)

- Flask 3.1.3
- anthropic 0.112.0
- python-dotenv 2.2.2

Do not install new packages without asking Pete first.

---

## The Chatbot — How It Works (MVP 0)

The chatbot widget lives in three files:
- `templates/base.html` — the HTML structure (button, panel, input)
- `static/css/chatbot.css` — all visual styles
- `static/js/chatbot.js` — all behavior (open/close, send, get response)

Currently, `chatbot.js` uses a `getMockResponse()` function that returns hardcoded answers based on keyword matching. This is MVP 0 — no real AI yet.

MVP 1 will replace `getMockResponse()` with a `fetch()` call to a new Flask route `/api/chat`, which will call the Claude API using Pete's knowledge base files as context.

---

## Security Rules — Never Violate These

- Never include the API key in any file that gets committed to GitHub
- Never put secrets in HTML, CSS, or JavaScript files
- Never discuss classified information, internal program names, or proprietary employer details
- The `.env` file must never be committed — it is already in `.gitignore`
- The chatbot must only answer from the approved knowledge base files

---

## Pete's Working Style

- Complete beginner — explain everything step by step with no assumptions
- Always explain WHY something works, not just the command
- Comment all code thoroughly so Pete can read and learn from it
- Ask before creating new files or folders
- Never run destructive commands (delete, overwrite, force push) without explicit confirmation
- Pete works from two computers (Mac and Windows PC) and syncs via GitHub
