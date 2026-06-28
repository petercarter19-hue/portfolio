# Pete Carter Portfolio — Coding Guide, Legend, and Project Dictionary

This file is a living reference for the code, tools, file structure, and development practices used in this portfolio project.

Keep this file in the main project folder and update it as the website grows.

---

# 1. Project Purpose

This website is more than a personal homepage. It is the main platform for showing:

- Systems engineering experience
- Digital engineering and MBSE work
- Software automation projects
- AI integrations
- Technical documentation
- Architecture diagrams
- Testing and verification evidence
- Future engineering applications

The long-term professional direction is:

**Systems Engineer specializing in Digital Engineering, MBSE, Software Automation, and AI-Enabled Systems**

---

# 2. Current Technology Stack

## Python

Python is the main programming language used by the website backend.

Python is responsible for:

- Starting the website
- Running Flask
- Handling routes
- Processing data
- Connecting to APIs
- Reading files or databases
- Supporting future AI features

Typical Python file:

```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
```

---

## Flask

Flask is the Python web framework used to create the website.

A framework gives the project a structure for:

- Web pages
- URLs
- Templates
- Forms
- APIs
- Errors
- Authentication
- Databases

Flask connects the browser-facing files to the Python backend.

Example:

```python
@app.route("/")
def home():
    return render_template("index.html")
```

Meaning:

- `@app.route("/")` tells Flask which URL to respond to.
- `/` represents the homepage.
- `home()` is the Python function Flask runs.
- `render_template("index.html")` loads the HTML page.

---

## HTML

HTML controls the structure and content of each webpage.

HTML is used for:

- Headings
- Paragraphs
- Buttons
- Images
- Navigation menus
- Sections
- Forms
- Links

Example:

```html
<section class="hero">
    <h1>Pete Carter</h1>
    <p>Systems Engineer specializing in digital engineering and automation.</p>
</section>
```

HTML describes what appears on the page.

---

## CSS

CSS controls how the website looks.

CSS is used for:

- Colors
- Fonts
- Spacing
- Backgrounds
- Borders
- Layout
- Animation
- Responsive design
- Mobile behavior

Example:

```css
.hero {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
```

CSS selectors connect styling rules to HTML elements.

---

## JavaScript

JavaScript controls browser-side interaction.

JavaScript may eventually be used for:

- Opening menus
- Updating page content
- Calling APIs
- Form validation
- Animations
- Chatbot interfaces
- Real-time dashboard updates
- WebSocket connections

JavaScript runs in the visitor's browser.

Important security rule:

**Never place passwords, API keys, Home Assistant tokens, or other secrets in browser-side JavaScript.**

---

## Jinja

Jinja is Flask's HTML templating language.

Jinja lets HTML pages reuse shared layouts and display Python data.

Common Jinja syntax:

```html
{% extends "base.html" %}
```

This tells the page to use `base.html` as its shared layout.

```html
{% block title %}Pete Carter | Portfolio{% endblock %}
```

This replaces the title block defined in `base.html`.

```html
{% block content %}
    <h1>Homepage content</h1>
{% endblock %}
```

This inserts page-specific content into the main layout.

```html
{{ variable_name }}
```

Double curly braces display a value sent from Python.

Example:

```python
return render_template("project.html", project_name="Requirements Analyzer")
```

```html
<h1>{{ project_name }}</h1>
```

---

# 3. Typical Project Folder Structure

A Flask portfolio project will commonly look like this:

```text
portfolio-website/
├── app.py
├── requirements.txt
├── README.md
├── CODE_GUIDE.md
├── .gitignore
├── .env
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   ├── images/
│   │   ├── profile/
│   │   ├── backgrounds/
│   │   └── projects/
│   └── documents/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── about.html
│   ├── projects.html
│   ├── resume.html
│   └── contact.html
└── tests/
    └── test_routes.py
```

## File and Folder Dictionary

### `app.py`

The main Flask application.

It normally contains:

- Flask setup
- Website routes
- Error handlers
- Configuration loading
- Connections to other services

### `templates/`

Contains HTML files that Flask renders.

### `static/`

Contains files the browser loads directly.

Examples:

- CSS
- JavaScript
- Images
- Downloadable documents

### `static/css/style.css`

The main stylesheet for the website.

### `static/js/main.js`

The main browser-side JavaScript file.

### `requirements.txt`

Lists the Python packages required by the project.

Example:

```text
Flask==3.1.1
python-dotenv==1.1.0
```

### `.env`

Stores private environment variables.

Examples:

```text
SECRET_KEY=replace-this-with-a-private-value
OPENAI_API_KEY=replace-this-with-a-private-value
```

Never upload `.env` to GitHub.

### `.gitignore`

Tells Git which files not to track.

Typical contents:

```text
.env
venv/
__pycache__/
.DS_Store
*.pyc
```

### `README.md`

Explains the project to visitors, recruiters, and future developers.

### `CODE_GUIDE.md`

This file. It explains the code and terminology used throughout the project.

### `tests/`

Contains automated tests.

---

# 4. Base Template Pattern

A shared base template prevents repeated code.

Example `base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{% block title %}Pete Carter Portfolio{% endblock %}</title>

    <link
        rel="stylesheet"
        href="{{ url_for('static', filename='css/style.css') }}"
    >
</head>
<body>

    <nav class="navbar">
        <!-- Shared navigation -->
    </nav>

    <main>
        {% block content %}{% endblock %}
    </main>

    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
```

Other pages extend it:

```html
{% extends "base.html" %}

{% block title %}About | Pete Carter{% endblock %}

{% block content %}
<section class="about-section">
    <h1>About Me</h1>
</section>
{% endblock %}
```

---

# 5. Important HTML Terms

## Element

A complete HTML structure.

```html
<p>This is a paragraph.</p>
```

## Tag

The opening or closing marker.

```html
<p>
</p>
```

## Attribute

Additional information inside an opening tag.

```html
<img src="photo.jpg" alt="Pete Carter">
```

`src` and `alt` are attributes.

## Class

A reusable name used mainly by CSS and JavaScript.

```html
<section class="hero">
```

CSS:

```css
.hero {
    padding: 40px;
}
```

## ID

A unique name for one element.

```html
<h1 id="hero-title">Pete Carter</h1>
```

An ID should usually appear only once per page.

## Semantic HTML

HTML elements that describe their purpose.

Examples:

- `<header>`
- `<nav>`
- `<main>`
- `<section>`
- `<article>`
- `<footer>`

Semantic HTML improves accessibility, organization, and search-engine understanding.

## `aria-*`

Accessibility attributes used by screen readers and assistive technology.

Example:

```html
<section class="hero" aria-labelledby="hero-title">
```

This connects the section to the heading with `id="hero-title"`.

## `aria-hidden="true"`

Tells screen readers to ignore decorative content.

Example:

```html
<div class="background-glow" aria-hidden="true"></div>
```

---

# 6. Important CSS Terms

## Selector

Chooses which HTML element receives styling.

```css
.hero {
    padding: 40px;
}
```

`.hero` is the selector.

## Property

The style setting being changed.

```css
color: white;
```

`color` is the property.

## Value

The selected setting.

```css
color: white;
```

`white` is the value.

## Class Selector

Starts with a period.

```css
.navbar {
}
```

## ID Selector

Starts with a hash symbol.

```css
#hero-title {
}
```

## Element Selector

Targets every matching HTML tag.

```css
body {
}
```

## Universal Selector

Targets every element.

```css
* {
    box-sizing: border-box;
}
```

## Box Model

Every HTML element is treated like a box containing:

1. Content
2. Padding
3. Border
4. Margin

### Padding

Space inside the element.

```css
padding: 20px;
```

### Margin

Space outside the element.

```css
margin: 20px;
```

### Border

The visible edge around an element.

```css
border: 1px solid white;
```

## `box-sizing: border-box`

Makes width and height calculations easier.

```css
* {
    box-sizing: border-box;
}
```

Padding and borders are included in the specified width.

## Flexbox

A CSS layout system used to align items in rows or columns.

```css
.hero {
    display: flex;
    justify-content: center;
    align-items: center;
}
```

Common Flexbox properties:

- `display: flex`
- `flex-direction`
- `justify-content`
- `align-items`
- `gap`
- `flex-wrap`

## CSS Grid

A layout system for rows and columns.

```css
.project-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
}
```

## `position`

Controls how an element is positioned.

### `static`

Normal page behavior.

### `relative`

Keeps the element in normal flow and allows positioned child elements to use it as a reference.

```css
.hero {
    position: relative;
}
```

### `absolute`

Places the element relative to the nearest positioned parent.

```css
.hero-background {
    position: absolute;
    inset: 0;
}
```

### `fixed`

Keeps the element fixed to the browser window.

### `sticky`

Allows an element to remain visible after scrolling to a certain point.

```css
.navbar {
    position: sticky;
    top: 0;
}
```

## `z-index`

Controls which elements appear in front of others.

```css
.navbar {
    z-index: 100;
}
```

A higher value normally appears above a lower value.

## `overflow`

Controls what happens when content extends beyond an element.

```css
.hero {
    overflow: hidden;
}
```

## `background-size`

Controls how a background image fills an area.

```css
background-size: cover;
```

`cover` fills the entire area but may crop part of the image.

```css
background-size: contain;
```

`contain` displays the entire image but may leave empty space.

## `background-position`

Controls where the background image is centered.

```css
background-position: center;
```

## `background-repeat`

Controls whether the image repeats.

```css
background-repeat: no-repeat;
```

## Pseudo-class

Targets an element in a special state.

```css
.nav-link:hover {
    color: white;
}
```

Examples:

- `:hover`
- `:focus`
- `:active`
- `:first-child`

## Pseudo-element

Creates or styles part of an element.

```css
.hero::before {
    content: "";
}
```

Common pseudo-elements:

- `::before`
- `::after`

## Media Query

Changes styling for different screen sizes.

```css
@media (max-width: 768px) {
    .nav-links {
        display: none;
    }
}
```

This is used for responsive mobile design.

---

# 7. CSS Reset Used in the Project

A reset removes inconsistent browser defaults.

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
```

Meaning:

- Remove default outside spacing.
- Remove default inside spacing.
- Use predictable sizing.

---

# 8. Navigation Bar Terms

Typical navigation HTML:

```html
<nav class="navbar">
    <div class="nav-container">
        <a class="nav-logo" href="/">Pete Carter</a>

        <ul class="nav-links">
            <li><a href="/">Home</a></li>
            <li><a href="/projects">Projects</a></li>
        </ul>
    </div>
</nav>
```

## `nav`

Semantic container for navigation links.

## `ul`

Unordered list.

## `li`

List item.

## `a`

Anchor element used for links.

## `href`

The destination of a link.

---

# 9. Hero Section Terms

The hero section is the large opening section at the top of a webpage.

It normally contains:

- Name
- Professional identity
- Introductory statement
- Call-to-action buttons
- Profile image or collage
- Decorative background

Example:

```html
<section class="hero" aria-labelledby="hero-title">
    <div class="hero-content">
        <h1 id="hero-title">Pete Carter</h1>
        <p>Systems Engineer specializing in digital engineering.</p>
    </div>
</section>
```

## Hero Background

The large background behind the hero content.

Possible implementation:

```css
.hero {
    background-image: url("../images/backgrounds/circuit-background.jpg");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}
```

## Background Overlay

A translucent layer placed over a background image to improve readability.

```css
.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
}
```

## Full-Background Image

An image should be applied to the section itself when it needs to appear as the true background.

A normal `<img>` element placed over a background can look like a separate rectangle or picture.

## Transparent Image

A PNG or WebP image can have transparent areas.

This is useful for a collage that must blend into the page without its own visible rectangular background.

---

# 10. Image File Types

## JPG or JPEG

Best for photographs.

Advantages:

- Smaller file size
- Good for detailed photos

Disadvantages:

- Does not support transparency

## PNG

Best for images requiring transparency.

Advantages:

- Supports transparent backgrounds
- Good image quality

Disadvantages:

- Often larger than JPG or WebP

## WebP

Modern image format.

Advantages:

- Small file size
- Supports transparency
- Good image quality

## SVG

Vector image format.

Best for:

- Logos
- Icons
- Diagrams
- Simple illustrations

SVG images remain sharp at different sizes.

---

# 11. Image Path Examples

In normal HTML:

```html
<img
    src="{{ url_for('static', filename='images/profile/pete-collage.png') }}"
    alt="Collage representing Pete Carter's engineering background"
>
```

In CSS:

```css
.hero {
    background-image: url("../images/backgrounds/circuit-board.jpg");
}
```

The CSS path is relative to the CSS file.

If `style.css` is located in:

```text
static/css/style.css
```

Then this:

```css
url("../images/backgrounds/circuit-board.jpg")
```

moves up from `css` to `static`, then into `images/backgrounds`.

---

# 12. Python Terms

## Variable

Stores a value.

```python
project_name = "Requirements Traceability Tool"
```

## Function

A reusable block of code.

```python
def calculate_score():
    return 95
```

## Parameter

A named input defined by a function.

```python
def greet(name):
    return f"Hello, {name}"
```

`name` is the parameter.

## Argument

The actual value passed to a function.

```python
greet("Pete")
```

`"Pete"` is the argument.

## List

Stores an ordered group of values.

```python
skills = ["Systems Engineering", "MBSE", "Python"]
```

## Dictionary

Stores key-value pairs.

```python
project = {
    "name": "Requirements Analyzer",
    "status": "In Progress"
}
```

## Boolean

A value that is either:

```python
True
False
```

## Conditional

Runs code only when a condition is met.

```python
if project_complete:
    print("Ready for portfolio")
else:
    print("Still in progress")
```

## Loop

Repeats code.

```python
for skill in skills:
    print(skill)
```

## Import

Loads code from another Python package or file.

```python
from flask import Flask
```

## Exception

An error that occurs while code is running.

```python
try:
    result = risky_operation()
except Exception as error:
    print(error)
```

---

# 13. Flask Terms

## Application Instance

```python
app = Flask(__name__)
```

Creates the Flask application.

## Route

Connects a URL to a Python function.

```python
@app.route("/projects")
def projects():
    return render_template("projects.html")
```

## View Function

The Python function connected to a route.

```python
def projects():
```

## Template

An HTML file rendered by Flask.

```python
render_template("projects.html")
```

## Static File

A file that Flask serves without processing.

Examples:

- CSS
- JavaScript
- Images
- PDFs

## Request

Information sent from the browser to the server.

## Response

Information sent from the server back to the browser.

## GET

Used to retrieve a page or data.

## POST

Used to send data, such as a contact form submission.

Example:

```python
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        return "Form submitted"

    return render_template("contact.html")
```

## Debug Mode

```python
app.run(debug=True)
```

Debug mode automatically reloads code changes and provides detailed errors.

Do not use debug mode in a public production deployment.

---

# 14. Frontend and Backend

## Frontend

The part users see and interact with.

Includes:

- HTML
- CSS
- JavaScript
- Images
- Buttons
- Forms

## Backend

The server-side part users do not directly see.

Includes:

- Python
- Flask
- Databases
- Authentication
- API calls
- AI processing
- Security rules

## Full Stack

A project containing both frontend and backend work.

---

# 15. API Terms

## API

An Application Programming Interface allows software systems to communicate.

Example future website use:

1. Visitor asks the portfolio chatbot a question.
2. Browser sends the question to Flask.
3. Flask calls an LLM API.
4. The API returns an answer.
5. Flask sends the approved answer back to the browser.

## Endpoint

A specific API URL.

Example:

```text
/api/chat
```

## REST API

A common API style based on HTTP methods such as:

- GET
- POST
- PUT
- PATCH
- DELETE

## JSON

A structured data format commonly used by APIs.

Example:

```json
{
    "question": "What is Pete's MBSE experience?",
    "answer": "Pete has experience with SysML and Cameo Systems Modeler."
}
```

## Authentication

Proves who or what is making a request.

## Authorization

Determines what an authenticated user is allowed to do.

## API Key

A secret value that allows an application to use an external service.

Never put an API key in:

- Public GitHub repositories
- HTML
- CSS
- Browser-side JavaScript
- Screenshots
- Public documentation

Store API keys in `.env`.

---

# 16. Environment Variables

Environment variables store configuration outside the code.

Example `.env`:

```text
FLASK_SECRET_KEY=replace-with-a-private-random-value
OPENAI_API_KEY=replace-with-your-private-key
```

Python example:

```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
```

Benefits:

- Protects credentials
- Separates configuration from code
- Makes deployment easier
- Prevents accidental GitHub exposure

---

# 17. Git and GitHub

## Git

Git tracks changes to project files.

Git allows you to:

- Save development checkpoints
- Review changes
- Undo mistakes
- Work from multiple computers
- Create branches
- Collaborate

## GitHub

GitHub stores Git repositories online.

It is used for:

- Backup
- Version control
- Portfolio evidence
- Collaboration
- Issues
- Releases
- GitHub Actions

## Repository

The project tracked by Git.

## Commit

A saved checkpoint containing project changes.

## Branch

A separate line of development.

Common branch:

```text
main
```

Future example:

```text
feature/chatbot
```

## Remote

The online GitHub copy of the repository.

Typical remote name:

```text
origin
```

---

# 18. Common Git Commands

Check project changes:

```bash
git status
```

Add all changed files:

```bash
git add .
```

Commit changes:

```bash
git commit -m "Improve hero background and portfolio collage"
```

Upload commits to GitHub:

```bash
git push origin main
```

Download new commits from GitHub:

```bash
git pull origin main
```

Copy a repository to another computer:

```bash
git clone REPOSITORY_URL
```

See commit history:

```bash
git log --oneline
```

Create a branch:

```bash
git switch -c feature-name
```

Return to the main branch:

```bash
git switch main
```

---

# 19. Recommended Save-to-GitHub Workflow

Use this sequence after completing a meaningful change:

```bash
git status
git add .
git commit -m "Describe the change clearly"
git push origin main
```

Good commit messages:

```text
Add responsive hero section
Improve collage transparency
Fix navigation spacing
Create project card layout
Add portfolio code guide
```

Weak commit messages:

```text
stuff
changes
update
fix
```

A commit message should explain what changed.

---

# 20. VS Code Terms

## Explorer

Shows project files and folders.

## Editor

The area where code is written.

## Terminal

Runs commands without leaving VS Code.

Open the terminal using:

```text
Control + `
```

On a Mac, the backtick key is normally below Escape.

## Extension

An add-on that gives VS Code new features.

Useful extensions:

- Python
- Pylance
- GitHub Copilot
- GitLens
- HTML CSS Support
- Prettier
- Error Lens
- Live Server for simple HTML projects

Flask projects should normally be run through Python rather than Live Server.

## Command Palette

Opens VS Code commands.

Mac:

```text
Command + Shift + P
```

## Integrated Source Control

The Git interface built into VS Code.

---

# 21. Virtual Environment

A virtual environment keeps project packages separate from the rest of the computer.

Create one:

```bash
python3 -m venv venv
```

Activate it on macOS:

```bash
source venv/bin/activate
```

Deactivate it:

```bash
deactivate
```

Install Flask:

```bash
pip install Flask
```

Save installed packages:

```bash
pip freeze > requirements.txt
```

Install packages from an existing project:

```bash
pip install -r requirements.txt
```

---

# 22. Running the Flask Website

Common command:

```bash
python3 app.py
```

Flask may display an address similar to:

```text
http://127.0.0.1:5000
```

Open that address in a browser.

`127.0.0.1` means the website is running locally on your computer.

---

# 23. Responsive Design

Responsive design allows the website to work on:

- Desktop computers
- Laptops
- Tablets
- Phones

Common practices:

- Use flexible widths
- Use `max-width`
- Use Flexbox or Grid
- Use media queries
- Avoid fixed heights when possible
- Test multiple screen sizes

Example:

```css
.container {
    width: min(1100px, 90%);
    margin: 0 auto;
}
```

This keeps the content centered and prevents it from becoming too wide.

---

# 24. Accessibility

Accessibility makes the website usable by more people.

Important practices:

- Add useful `alt` text to images
- Use semantic HTML
- Use proper heading order
- Ensure text has enough color contrast
- Make buttons keyboard-accessible
- Add visible focus states
- Label form inputs
- Avoid relying only on color
- Hide purely decorative elements from screen readers

Good image example:

```html
<img
    src="{{ url_for('static', filename='images/profile/pete.png') }}"
    alt="Pete Carter, systems engineer"
>
```

Decorative image example:

```html
<img src="circuit-pattern.svg" alt="" aria-hidden="true">
```

---

# 25. Website Security Rules

## Never expose secrets

Do not publish:

- API keys
- Passwords
- Home Assistant tokens
- Internal IP addresses
- Alarm information
- Smart-lock controls
- Camera feeds
- Private device names
- Occupancy information

## Keep private controls separate

The public portfolio may include a simulated Home Assistant dashboard.

The live dashboard should be:

- Protected
- Private
- Authenticated
- Server-side
- Separate from public portfolio pages

## Validate input

Never trust information sent by a browser.

Forms and API requests should be checked before processing.

## Use least privilege

Give accounts and API keys only the permissions they need.

## Keep dependencies updated

Outdated packages may contain known security problems.

---

# 26. AI Chatbot Architecture Terms

The portfolio chatbot should eventually use only approved information.

## LLM

Large Language Model.

It generates text based on instructions and context.

## Prompt

Instructions sent to the model.

## System Prompt

High-priority instructions controlling the chatbot's behavior.

## Retrieval-Augmented Generation

Usually abbreviated as RAG.

RAG lets the chatbot search approved portfolio documents before answering.

Basic RAG flow:

1. User asks a question.
2. The application searches approved documents.
3. Relevant information is retrieved.
4. The information is sent to the language model.
5. The answer includes supporting citations.

## Embedding

A numerical representation of text used to compare meaning.

## Vector Database

A database designed to store and search embeddings.

## Hallucination

When an AI produces unsupported or inaccurate information.

The portfolio chatbot should refuse to invent information.

## Guardrail

A rule or control that limits unsafe or unsupported behavior.

## Rate Limiting

Restricts how many requests a user can make during a period.

Rate limiting helps control:

- Abuse
- API cost
- Server load

## Token

A small unit of text processed by an AI model.

API charges are often based partly on token usage.

---

# 27. Project Status Language

Use accurate status labels.

## Planned

The feature has not been built yet.

## In Progress

Development has started but the feature is not complete.

## Prototype

An early version used to test a concept.

## MVP

Minimum Viable Product.

The smallest working version that provides useful value.

## Completed

The feature exists, works, and has been verified.

## Deployed

The feature is available in a hosted environment.

Do not describe a planned feature as completed.

---

# 28. Engineering Project Documentation Pattern

Every major portfolio project should eventually document:

1. Problem and users
2. Requirements and constraints
3. Architecture and technology choices
4. Interfaces and data flow
5. Security considerations
6. Implementation
7. Testing and verification
8. Problems encountered
9. Results and measurable improvements
10. Future enhancements

This pattern demonstrates systems-engineering thinking instead of only showing code.

---

# 29. Priority Portfolio Project Ideas

Projects that fit the professional direction include:

- Requirements traceability tool
- Verification planning application
- Test-log analyzer
- FRACAS dashboard
- Reliability analysis dashboard
- MBSE report generator
- Model-data extraction tool
- Interface-management application
- AI-assisted requirements review tool
- Requirements-to-test evidence tracker
- Home Assistant private dashboard
- Portfolio information chatbot

---

# 30. Code Comment Style

Comments explain why code exists.

HTML comment:

```html
<!-- Main hero section -->
```

CSS comment:

```css
/* Keeps the navigation visible while scrolling */
```

Python comment:

```python
# Loads environment variables from the local .env file
```

JavaScript comment:

```javascript
// Opens the mobile navigation menu
```

For project code, comments should be placed beside meaningful code when practical.

Example:

```css
.navbar {
    position: sticky;      /* Keeps the navigation visible while scrolling */
    top: 0;                /* Positions the sticky navigation at the top */
    z-index: 100;          /* Keeps it above normal page content */
}
```

Comments should explain purpose, not merely repeat the code.

Weak comment:

```python
name = "Pete"  # Sets name to Pete
```

Better comment:

```python
name = "Pete"  # Used as the display name throughout the portfolio
```

---

# 31. Naming Conventions

Use clear, descriptive names.

Good HTML and CSS names:

```text
hero-content
project-card
nav-container
contact-form
resume-download-button
```

Weak names:

```text
thing
box1
stuff
test2
newdiv
```

Python uses snake_case:

```python
project_name
load_resume_data
validate_contact_form
```

JavaScript commonly uses camelCase:

```javascript
projectName
loadResumeData
validateContactForm
```

CSS classes normally use lowercase words separated by hyphens:

```css
.project-card
.hero-background
.nav-link
```

---

# 32. Common Troubleshooting Checklist

When a change does not appear:

1. Save the file.
2. Confirm the correct file was edited.
3. Refresh the browser.
4. Perform a hard refresh.
5. Check the browser developer console.
6. Check the Flask terminal for errors.
7. Confirm the CSS file is linked correctly.
8. Confirm the class name matches exactly.
9. Check for missing braces, quotes, or closing tags.
10. Confirm the image path and filename.
11. Check capitalization.
12. Confirm the virtual environment is active.
13. Restart Flask if necessary.

Mac hard refresh:

```text
Command + Shift + R
```

---

# 33. Browser Developer Tools

Developer Tools help inspect and troubleshoot webpages.

Open on Mac:

```text
Command + Option + I
```

Useful sections:

## Elements

Inspect HTML and CSS.

## Console

View JavaScript errors.

## Network

See which files and API requests loaded.

## Application

Inspect browser storage and cookies.

## Responsive Device Mode

Test phone and tablet screen sizes.

---

# 34. Common Error Types

## Syntax Error

The code is written in an invalid format.

Examples:

- Missing bracket
- Missing quote
- Missing colon
- Unclosed HTML tag

## Runtime Error

The program starts but fails while running.

## 404 Not Found

The requested page or file does not exist at that path.

## 500 Internal Server Error

The backend encountered an error.

## CSS Not Applying

Possible causes:

- Wrong selector
- Wrong file path
- More specific rule overriding it
- Browser cache
- Missing closing brace

## Image Not Loading

Possible causes:

- Wrong filename
- Wrong folder
- Incorrect capitalization
- Wrong extension
- Incorrect relative path

---

# 35. Development Workflow

A practical workflow for adding a feature:

1. Define the feature.
2. Identify user needs.
3. Write simple requirements.
4. Sketch the layout or data flow.
5. Create a small implementation.
6. Test locally.
7. Fix errors.
8. Test on mobile.
9. Review accessibility.
10. Review security.
11. Commit the change.
12. Push to GitHub.
13. Update documentation.

---

# 36. Example Feature Requirement

Feature:

Portfolio project card.

User requirement:

A recruiter should be able to understand the purpose, status, technology, and engineering value of each project.

Possible acceptance criteria:

- Each card displays a project name.
- Each card displays a status.
- Each card displays a short problem statement.
- Each card displays key technologies.
- Each card links to a case-study page.
- The layout works on desktop and mobile.
- The card can be used with a keyboard.
- No confidential program information is displayed.

---

# 37. Testing Terms

## Unit Test

Tests one small function or component.

## Integration Test

Tests multiple parts working together.

## System Test

Tests the complete application.

## Regression Test

Confirms a new change did not break an existing feature.

## Acceptance Test

Confirms the feature meets its requirements.

## Test Case

A documented input, action, and expected result.

Example:

```text
Test ID: NAV-001
Action: Select the Projects navigation link.
Expected Result: The browser opens the Projects page.
```

---

# 38. Deployment Terms

## Local Development

The website runs only on your computer.

## Hosting

A service makes the website available online.

## Production

The live version used by visitors.

## Domain

The website address.

Example:

```text
petecarter.com
```

## HTTPS

Encrypts traffic between the visitor and the website.

A production website should use HTTPS.

## Build

The process of preparing the application for deployment.

## CI/CD

Continuous Integration and Continuous Deployment.

CI/CD can automatically:

- Run tests
- Check formatting
- Scan for security issues
- Deploy approved changes

GitHub Actions can eventually provide CI/CD.

---

# 39. Home Assistant Dashboard Architecture

The public portfolio should never connect directly to private Home Assistant controls.

Recommended future structure:

```text
Browser
   |
   v
Protected Flask Server
   |
   v
Home Assistant API
```

The Flask server should:

- Store secrets securely
- Authenticate users
- Validate commands
- Restrict permissions
- Log failures safely
- Return only approved data

A public demo should use:

- Simulated data
- Sanitized device names
- No private addresses
- No camera feeds
- No lock or alarm controls

---

# 40. Interview Explanation Pattern

For each project, be ready to explain:

- What problem did it solve?
- Who was the user?
- What requirements did you define?
- Why did you choose the architecture?
- How did data move through the system?
- What security risks existed?
- How did you test it?
- What failed during development?
- What did you improve?
- What would you build next?

The goal is to show ownership of the engineering process, even when AI-assisted development tools were used.

Recommended wording:

**Designed and developed using AI-assisted engineering tools while retaining ownership of requirements, architecture, implementation, integration, verification, security, and deployment.**

---

# 41. Current Project Conventions

Use these conventions unless there is a specific reason to change them:

- Flask for the backend
- Jinja templates for shared page structure
- One main CSS file while the site is still small
- Separate image folders by purpose
- Descriptive class names
- Semantic HTML
- Responsive layouts
- Environment variables for secrets
- Git commits after meaningful changes
- GitHub as the remote project backup
- Clear comments beside meaningful code where practical
- Planned, in-progress, and completed features labeled accurately
- Public and private systems kept separate

---

# 42. Useful Terminal Commands

Show the current folder:

```bash
pwd
```

List files:

```bash
ls
```

List hidden files:

```bash
ls -la
```

Move into a folder:

```bash
cd folder-name
```

Move up one folder:

```bash
cd ..
```

Create a folder:

```bash
mkdir folder-name
```

Create a file:

```bash
touch filename.md
```

Clear the terminal:

```bash
clear
```

Check Python version:

```bash
python3 --version
```

Check Git version:

```bash
git --version
```

Check GitHub CLI version:

```bash
gh --version
```

---

# 43. Markdown Guide

Markdown is used for documentation files such as this one.

Heading:

```markdown
# Main Heading
## Section Heading
### Smaller Heading
```

Bold:

```markdown
**Bold text**
```

Bullet list:

```markdown
- Item one
- Item two
```

Numbered list:

```markdown
1. First step
2. Second step
```

Code:

````markdown
```python
print("Hello")
```
````

Link:

```markdown
[GitHub](https://github.com)
```

Image:

```markdown
![Description](path-to-image.png)
```

---

# 44. Documentation Files to Add Later

Possible future documentation:

```text
README.md
CODE_GUIDE.md
ARCHITECTURE.md
SECURITY.md
TEST_PLAN.md
CHANGELOG.md
CONTRIBUTING.md
DEPLOYMENT.md
```

## `ARCHITECTURE.md`

Explains major components and data flow.

## `SECURITY.md`

Explains security decisions and reporting procedures.

## `TEST_PLAN.md`

Defines testing strategy and verification evidence.

## `CHANGELOG.md`

Records important version changes.

## `DEPLOYMENT.md`

Explains how to deploy and maintain the website.

---

# 45. Living Glossary

Add new terms here as the project grows.

| Term | Meaning |
|---|---|
| Backend | Server-side application logic |
| Frontend | Browser-facing interface |
| Flask | Python web framework |
| Jinja | Flask HTML templating language |
| Route | URL connected to a Python function |
| Template | HTML page rendered by Flask |
| Static file | CSS, JavaScript, image, or document served directly |
| API | Interface that allows software systems to communicate |
| Endpoint | Specific API URL |
| JSON | Structured data format |
| Environment variable | Configuration value stored outside source code |
| Repository | Project tracked by Git |
| Commit | Saved Git checkpoint |
| Branch | Separate line of development |
| Deployment | Publishing an application to a hosted environment |
| Responsive design | Layout that adapts to different screens |
| Semantic HTML | HTML elements that describe their purpose |
| Accessibility | Designing software for users with different abilities |
| Authentication | Proving identity |
| Authorization | Deciding permitted actions |
| RAG | AI pattern that retrieves approved information before answering |
| Embedding | Numerical representation of text meaning |
| Guardrail | Rule limiting unsafe or unsupported AI behavior |
| Rate limit | Restriction on request frequency |
| MVP | Smallest useful working version |
| CI/CD | Automated testing and deployment workflow |
| WebSocket | Persistent connection for real-time communication |
| Database | Structured storage for application data |
| SQL | Language used to work with relational databases |
| PostgreSQL | Professional open-source relational database |
| Docker | Tool for packaging an application and its dependencies |
| GitHub Actions | GitHub automation service |
| Unit test | Test of a small isolated component |
| Integration test | Test of connected components |
| Regression test | Test ensuring old behavior still works |
| Acceptance criteria | Conditions that define when a requirement is satisfied |

---

# 46. How to Maintain This File

Update this guide whenever the project adds:

- A new programming language
- A new framework
- A new folder
- A new API
- A database
- Authentication
- AI retrieval
- Docker
- GitHub Actions
- Testing tools
- Deployment services
- Home Assistant integration
- Security controls

Suggested update commit:

```bash
git add CODE_GUIDE.md
git commit -m "Update coding guide with new project concepts"
git push origin main
```

---

# 47. Final Reminder

The goal is not to memorize every command.

The goal is to understand:

- What each part does
- Why it is needed
- How the parts connect
- What risks exist
- How the feature is tested
- How the result supports the portfolio's engineering story

This file should grow alongside the website and become a reference you can use while coding, troubleshooting, documenting, and preparing for interviews.
