# VS Code Tutorial for Pete Carter's Portfolio

This tutorial is written for working on the portfolio website in VS Code.
It is meant to be practical: open the project, make a safe change, run the
Flask website, check your work, and save the change with Git.

You do not need to memorize every command. The goal is to learn the repeatable
workflow.

---

# 1. What VS Code Does

VS Code is the main workspace for this project.

It lets you:

- Open the whole portfolio folder.
- Edit Python, HTML, CSS, JavaScript, and documentation files.
- Run the Flask website from the built-in terminal.
- Search the whole project.
- Track changes with Git.
- Use extensions that help catch mistakes.

For this project, VS Code is your workshop.

---

# 2. Open the Correct Folder

Always open the main portfolio folder, not just one file.

On Pete's Mac, the project folder is expected to be:

```text
/Users/petercarter/portfolio
```

In the current Codex workspace, the same project is located at:

```text
C:\Users\peter\Documents\portfolio
```

In VS Code:

1. Open VS Code.
2. Choose File > Open Folder.
3. Select the portfolio folder.
4. Confirm that the Explorer panel shows files like `app.py`, `templates`, `static`, and `docs`.

If you only open one file, VS Code will not understand the full project.

---

# 3. Learn the Main VS Code Areas

## Explorer

The Explorer is the file list on the left side.

Important folders:

- `templates` contains the HTML pages.
- `static/css` contains the visual styling.
- `static/js` contains browser-side JavaScript.
- `docs` contains project notes and learning guides.
- `docs/knowledge` contains approved source material for the chatbot.

Important files:

- `app.py` starts the Flask website and defines routes.
- `templates/base.html` contains shared page structure and navigation.
- `templates/index.html` contains homepage content.
- `static/css/style.css` contains most site styling.
- `static/css/chatbot.css` contains chatbot styling.
- `static/js/chatbot.js` controls chatbot browser behavior.
- `.env` contains secrets and must not be displayed, shared, or committed.

## Editor

The editor is the center area where files open.

Useful habits:

- Keep related files open in tabs.
- Save often with `Command + S` on Mac.
- Read nearby code before changing anything.
- Make small changes, then test.

## Terminal

The terminal runs commands without leaving VS Code.

Open it on Mac:

```text
Control + `
```

The backtick key is usually below Escape.

Use the terminal to activate the virtual environment, run Flask, check Git,
and install packages.

## Source Control

The Source Control icon shows Git changes.

It helps you see:

- Which files changed.
- Exactly what text changed.
- Which files are staged for commit.
- Whether your project is clean.

---

# 4. The Most Important Beginner Rule

Before changing a file:

1. Save anything already open with `Command + S`.
2. Read the section you are about to edit.
3. Make one small change.
4. Save again.
5. Refresh the browser.
6. Check whether the change worked.

Small changes are easier to understand and easier to fix.

---

# 5. Running the Website from VS Code

The portfolio is a Flask app, so run it from the terminal.

Do not use Live Server for the full Flask site. Live Server is useful for simple
static HTML pages, but this project needs Python and Flask.

## On Mac

From the project folder:

```bash
source venv/bin/activate
python3 app.py
```

## On Windows

From the project folder:

```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

When Flask starts, it should show an address like:

```text
http://127.0.0.1:5000
```

Open that address in the browser.

If the site is already running and you change HTML, CSS, or JavaScript:

1. Save the file.
2. Refresh the browser.
3. Use a hard refresh if needed.

Mac hard refresh:

```text
Command + Shift + R
```

---

# 6. Where to Make Common Changes

## Change Page Text

Look in:

```text
templates/
```

Examples:

- Homepage text is usually in `templates/index.html`.
- Shared navigation is usually in `templates/base.html`.

## Change Colors, Spacing, or Layout

Look in:

```text
static/css/style.css
static/css/chatbot.css
```

Examples:

- Navbar spacing is in CSS.
- Button colors are in CSS.
- Mobile layout changes are often inside `@media` sections.

## Change Chatbot Browser Behavior

Look in:

```text
static/js/chatbot.js
```

Examples:

- Opening and closing the chatbot.
- Sending a visitor question.
- Hiding suggested questions.
- Displaying the answer bubble.

## Change Chatbot Server Behavior

Look in:

```text
app.py
docs/knowledge/
```

Examples:

- The `/api/chat` route is in `app.py`.
- Approved chatbot knowledge is in `docs/knowledge`.
- Prompt and answer cleanup logic are in `app.py`.

Do not put API keys in JavaScript, HTML, CSS, or public documentation.

---

# 7. How to Search the Project

Search is one of the fastest ways to work.

Open project search:

```text
Command + Shift + F
```

Good searches:

```text
chatbot
navbar
LinkedIn
hero
api/chat
clean_chatbot_reply
```

Search helps you answer:

- Where is this text coming from?
- Which CSS class controls this section?
- Is this function used anywhere else?
- Did I spell the class name the same way in HTML and CSS?

---

# 8. Understanding File Types

## `.py`

Python backend code.

Example:

```text
app.py
```

Use Python for Flask routes, server logic, AI API calls, and reading knowledge files.

## `.html`

Page structure.

Example:

```text
templates/base.html
```

Use HTML for headings, paragraphs, links, forms, buttons, and page sections.

## `.css`

Visual styling.

Example:

```text
static/css/style.css
```

Use CSS for colors, fonts, spacing, sizing, layout, and mobile behavior.

## `.js`

Browser interaction.

Example:

```text
static/js/chatbot.js
```

Use JavaScript for clicks, dynamic page updates, browser API calls, and chatbot interaction.

## `.md`

Markdown documentation.

Example:

```text
docs/vscode_tutorial.md
```

Use Markdown for notes, tutorials, requirements, and project documentation.

---

# 9. A Safe Practice Change

Use this exercise when you want to practice without touching important code.

1. Open `docs/session_log_2026-06-27.txt`.
2. Read a few lines.
3. Close it without editing.
4. Open this file: `docs/vscode_tutorial.md`.
5. Add one short note under the practice section.
6. Save with `Command + S`.
7. Open Source Control and confirm only this tutorial changed.

If you do not like the change, use Undo:

```text
Command + Z
```

---

# 10. A Safe Website Change Workflow

Use this sequence for normal website edits:

1. Decide exactly what you want to change.
2. Find the likely file.
3. Save open files.
4. Make a small edit.
5. Save.
6. Refresh the browser.
7. Test desktop and phone-sized views if the layout changed.
8. Check Source Control to review the changed lines.
9. Commit only after the change works.

Example:

```text
Goal: Change the homepage headline.
Likely file: templates/index.html
Test: Refresh http://127.0.0.1:5000
Commit message: Update homepage headline
```

---

# 11. Using Git in VS Code

Git is the project history system.

Before starting work, check the Source Control panel. If there are already
changes, understand what they are before adding more.

Common terminal commands:

```bash
git status
git add .
git commit -m "Describe the change clearly"
git push origin main
```

In VS Code Source Control:

1. Open the Source Control icon.
2. Review changed files.
3. Select a changed file to view the before-and-after diff.
4. Stage the files you want to include.
5. Write a clear commit message.
6. Commit.
7. Push to GitHub.

Good commit messages:

```text
Add VS Code tutorial
Improve chatbot answer cleanup
Fix mobile navigation spacing
Update recruiter FAQ knowledge
```

Weak commit messages:

```text
stuff
changes
fix
update
```

---

# 12. Reading Errors Without Panic

Errors are normal. Treat them as clues.

## Browser Shows Old Content

Try:

1. Save the file.
2. Refresh the browser.
3. Hard refresh with `Command + Shift + R`.
4. Confirm Flask is still running.
5. Confirm you edited the correct file.

## Flask Terminal Shows an Error

Look for:

- The filename.
- The line number.
- The last few lines of the error.

Common Python mistakes:

- Missing colon.
- Wrong indentation.
- Misspelled variable.
- Missing quote.
- Package not installed.

## CSS Change Does Not Work

Check:

- Did you save?
- Is the class name spelled the same in HTML and CSS?
- Is another CSS rule overriding it?
- Is the rule inside a media query for a different screen size?
- Did you miss a closing brace?

## JavaScript Feature Does Not Work

Open browser developer tools:

```text
Command + Option + I
```

Check the Console tab for red error messages.

---

# 13. VS Code Extensions Used in This Project

Helpful installed extensions include:

- Python
- Pylance
- GitHub Pull Requests
- PowerShell
- Prettier
- Auto Rename Tag
- Live Server

Important note:

Live Server is not the normal way to run this Flask app. Use the VS Code terminal
and run `app.py` through Python.

---

# 14. Beginner Shortcut Sheet

Mac shortcuts:

| Action | Shortcut |
|---|---|
| Save file | `Command + S` |
| Undo | `Command + Z` |
| Redo | `Command + Shift + Z` |
| Find in current file | `Command + F` |
| Search whole project | `Command + Shift + F` |
| Open Command Palette | `Command + Shift + P` |
| Open terminal | `Control + Backtick` |
| Hard refresh browser | `Command + Shift + R` |
| Browser developer tools | `Command + Option + I` |

Windows shortcuts:

| Action | Shortcut |
|---|---|
| Save file | `Control + S` |
| Undo | `Control + Z` |
| Redo | `Control + Y` |
| Find in current file | `Control + F` |
| Search whole project | `Control + Shift + F` |
| Open Command Palette | `Control + Shift + P` |
| Open terminal | `Control + Backtick` |
| Browser hard refresh | `Control + F5` |
| Browser developer tools | `F12` |

---

# 15. Daily Portfolio Coding Routine

Use this checklist each time you work on the site:

1. Open the portfolio folder in VS Code.
2. Open the terminal.
3. Activate the virtual environment.
4. Start Flask with `python3 app.py` on Mac or `python app.py` on Windows.
5. Open `http://127.0.0.1:5000`.
6. Make one small change.
7. Save.
8. Refresh and test.
9. Review changes in Source Control.
10. Commit when the change works.
11. Push to GitHub when ready.

---

# 16. Safety Rules

Never commit:

- `.env`
- API keys
- Passwords
- Private addresses
- Internal employer information
- Classified or proprietary information
- Private Home Assistant controls

Before sharing the site publicly, review content for:

- Confidential work details.
- Private family information.
- Exact home address or phone number.
- Security-sensitive smart home details.
- Unsupported claims about experience or credentials.

---

# 17. What to Practice Next

Recommended practice path:

1. Open and close files from the Explorer.
2. Search for a word across the project.
3. Run the Flask website from the VS Code terminal.
4. Change one sentence in a documentation file.
5. Change one visible line of homepage text.
6. Adjust one CSS spacing value.
7. Use Source Control to review what changed.
8. Commit a documentation-only change.

This sequence builds confidence without jumping straight into risky edits.

---

# 18. Final Mental Model

Think of the project in four layers:

```text
Browser
HTML, CSS, and JavaScript
Flask app.py
Approved docs and private environment settings
```

When something changes:

- Text usually starts in HTML or approved docs.
- Appearance usually starts in CSS.
- Click behavior usually starts in JavaScript.
- Server behavior usually starts in Python.
- Secrets belong only in `.env`.

That map will solve a lot of beginner confusion.
