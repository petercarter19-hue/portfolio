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

## Recent Session Updates
- Top navigation now stays sticky while scrolling on desktop/tablet screens, but scrolls away normally on phone screens.
- Mobile/tablet nav spacing was tightened so "Pete Carter" sits closer to the navigation links.
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
