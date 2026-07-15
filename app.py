# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page,
# and handles the AI chatbot API in MVP 1.

import os                                       # Lets us read file paths and environment variables
import glob                                     # Lets us find all files matching a pattern (e.g. all .md files)
import json                                     # Lets us read structured resume content from JSON
import re                                       # Lets us clean Markdown symbols out of chatbot replies
from datetime import datetime, timedelta        # Lets the Slate Feed compute live "2h ago" labels and week ranges
from flask import Flask, render_template, request, jsonify, url_for, redirect, abort  # Added: request (reads incoming data), jsonify (sends JSON back)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import anthropic                                # The Claude AI client library
from dotenv import load_dotenv                  # Reads our secret API key from the .env file
from db import get_connection, fetch_all_result_sets
from peerslate_api import peerslate_api
from people_interests_api import people_interests_api
from services.people_interests_feed import (
    GOAL_REACTION,
    POST_BODY_MAX,
    REACTION_TYPES,
    people_interests_feed,
)

# Load the .env file so ANTHROPIC_API_KEY is available to this app.
# This must happen before we create the Anthropic client below.
load_dotenv()

# Keep oversized prompts from consuming API budget or making the chat feel broken.
MAX_CHAT_MESSAGE_LENGTH = 1000

# Interview Workspace (Concept 1): request-size guards for the structured
# review endpoint. Answers are longer than chat messages by design.
MAX_INTERVIEW_ANSWER_LENGTH = 5000
MAX_INTERVIEW_QUESTION_LENGTH = 300

# Pete's verified slate evidence — FIXTURE data for the single-profile MVP.
# Passed to the Concept 1 template and injected into the review prompt in
# "My History" mode so the coach can only cite verified items. When real
# multi-user profiles arrive, this comes from the profile's evidence store.
INTERVIEW_SLATE_EVIDENCE = [
    {'id': 'ev-36m-cor', 'metric': '$36M+', 'label': 'Contract oversight as COR across engineering services', 'tag': 'Leadership'},
    {'id': 'ev-4-6m-nav', 'metric': '$4.6M', 'label': 'Navigation modernization led end to end as government POC', 'tag': 'Impact'},
    {'id': 'ev-70-repair', 'metric': '70%', 'label': 'Repair and test improvement across depot and supply chains', 'tag': 'Impact'},
    {'id': 'ev-cameo', 'metric': 'Cameo', 'label': 'SysML/MBSE modeling for navigation and avionics programs', 'tag': 'Technical'},
    {'id': 'ev-52-missing', 'metric': '52%', 'label': 'Missing-part reduction via systemic process redesign', 'tag': 'Impact'},
    {'id': 'ev-19m-flight', 'metric': '$19.2M', 'label': 'Redesign projects led with a 30+ engineer flight', 'tag': 'Leadership'},
]

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        'ANTHROPIC_API_KEY is not set. Add it to your .env file locally or your hosting environment variables in deployment.'
    )

# Create the Flask app
app = Flask(__name__)
# Azure terminates HTTPS before forwarding the request to Gunicorn. Trust the
# single platform proxy hop for the original scheme so external URLs, canonical
# tags, and Open Graph metadata stay HTTPS in production while localhost keeps
# its native HTTP scheme.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.config.update(
    PEERSLATE_ALLOW_DEV_IDENTITY=(
        os.environ.get('PEERSLATE_ALLOW_DEV_IDENTITY', 'false').lower() == 'true'
    ),
    PEERSLATE_DEV_USER_KEY=os.environ.get('PEERSLATE_DEV_USER_KEY'),
    PEERSLATE_ENABLE_DB_TEST_ROUTES=(
        os.environ.get('PEERSLATE_ENABLE_DB_TEST_ROUTES', 'false').lower() == 'true'
    ),
    PEERSLATE_DATABASE_UI_ENABLED=(
        os.environ.get('PEERSLATE_DATABASE_UI_ENABLED', 'false').lower() == 'true'
    ),
    PEERSLATE_LIVING_RESUME_DB_ENABLED=(
        os.environ.get('PEERSLATE_LIVING_RESUME_DB_ENABLED', 'false').lower() == 'true'
    ),
    PEERSLATE_TRUST_EASYAUTH_HEADERS=(
        os.environ.get('PEERSLATE_TRUST_EASYAUTH_HEADERS', 'false').lower() == 'true'
    ),
)

# MVP note: in-memory rate limiting is acceptable for local testing and early MVP.
# For production with multiple workers/instances, configure Redis-backed storage.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

# Create the Anthropic client.
# The API key stays on the server and is never exposed to browser JavaScript.
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
app.register_blueprint(peerslate_api)
app.register_blueprint(people_interests_api)


@app.after_request
def prevent_stale_html(response):
    """Always revalidate HTML pages so a design change (like the homepage
    move from peerslate.html to the Experience page) can't stick in a
    visitor's browser cache. Versioned static assets (?v=...) are left
    cacheable — only text/html is marked no-cache."""
    if response.mimetype == 'text/html':
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response


# -------------------------------------------------------
# SHARED NAVIGATION LINKS
# @app.context_processor means Flask runs this function before
# rendering ANY template, and every key in the dict it returns
# (like portfolio_resume_url) becomes a variable every template can
# use directly - that's how base.html can write things like
# {{ portfolio_resume_url }} without each route passing it in by hand.
#
# This exists because the same portfolio lives at more than one
# address: locally at /petec/..., and in production Pete's site
# is reachable both as its own path (peerslate.com/petec/...) and
# through the pete.peerslate.com subdomain. This function figures
# out, for the current request, what the correct link should be.
# -------------------------------------------------------

@app.context_processor
def shared_navigation_urls():
    # Flask's request.host can include a port (like "localhost:5000"),
    # so split it off and lowercase the rest for a clean comparison.
    clean_host = request.host.split(':', 1)[0].lower()
    is_platform = is_platform_hostname(request.host)

    portfolio_base_url = '/petec'
    if clean_host == 'pete.peerslate.com':
        portfolio_base_url = 'https://peerslate.com/petec'

    # Builds a full profile link by joining the base URL with a page name,
    # e.g. portfolio_url('resume') -> "/petec/resume".
    def portfolio_url(path=''):
        if not path:
            return portfolio_base_url

        return f'{portfolio_base_url}/{path.lstrip("/")}'

    return {
        # One central brand value keeps the public platform name easy to
        # change later if Pete decides between PeerSlate and PureSlate.
        'platform_brand_name': 'PeerSlate',
        'is_platform_site': is_platform,
        'portfolio_url': portfolio_url,
        # This app serves the platform homepage itself wherever it runs
        # (localhost, Azure, peerslate.com), so the brand/footer links always
        # point at this deployment's own "/" instead of an external domain.
        # (Previously any unrecognized host — like the Azure URL — sent
        # visitors to https://peerslate.com/, which isn't Pete's live site.)
        # The marketing/"How PeerSlate Works" page moved off the root when
        # the Experience page became the homepage; keep this pointing at
        # the page that actually hosts the #how-it-works anchor.
        'peerslate_home_url': url_for('peerslate_home'),
        'portfolio_home_url': portfolio_url('resume'),
        'portfolio_experience_url': f'{portfolio_url("resume")}#experience',
        'portfolio_skills_url': portfolio_url('skills'),
        'portfolio_story_url': portfolio_url('my-story'),
        'portfolio_resume_url': portfolio_url('resume'),
        'portfolio_contact_url': portfolio_url('contact'),
        'portfolio_hobbies_url': portfolio_url('hobbies'),
        'is_portfolio_path': request.path == '/petec' or request.path.startswith('/petec/'),
    }


RETIRED_PORTFOLIO_PATHS = {
    '/petec': '/petec/resume',
    '/portfolio': '/petec/resume',
    '/pete': '/petec/resume',
    '/overview': '/petec/resume',
    '/petec/overview': '/petec/resume',
    '/resume': '/petec/resume',
    '/resume2': '/petec/resume',
    '/petec/resume2': '/petec/resume',
    '/resume-ledger': '/petec/resume#experience',
    '/petec/resume-ledger': '/petec/resume#experience',
    '/work': '/petec/resume#experience',
    '/petec/work': '/petec/resume#experience',
    '/projects': '/petec/resume#experience',
    '/petec/projects': '/petec/resume#experience',
    '/atrium': '/',
    '/petec/atrium': '/',
}


# -------------------------------------------------------
# KEEP VISITORS ON THE CANONICAL URL
# @app.before_request runs this check before every single page
# load, on every route, before Flask decides which view function
# to call. It exists so that no matter how a visitor typed the
# address, they always end up on the one "correct" URL for that
# page - which keeps bookmarks, search engines, and old links
# consistent instead of showing the same page at multiple addresses.
# -------------------------------------------------------

@app.before_request
def keep_portfolio_on_canonical_path():
    clean_host = request.host.split(':', 1)[0].lower()

    # Case 1: someone visits the old pete.peerslate.com subdomain.
    # Permanently point them at the peerslate.com/petec/... version instead.
    if clean_host == 'pete.peerslate.com':
        project_match = re.fullmatch(r'/(?:petec/)?work/([^/]+)', request.path)
        if project_match:
            projects = _load_profile_projects('petec') or []
            project = next(
                (item for item in projects if item.get('slug') == project_match.group(1)),
                None,
            )
            if (
                project is None
                or not project.get('details_ready')
                or not project.get('publish_detail')
                or not project.get('case_study_sections')
            ):
                abort(404)
            target_path = '/petec/resume#experience'
        else:
            target_path = RETIRED_PORTFOLIO_PATHS.get(request.path)
        if target_path is None and request.path == '/':
            target_path = '/petec/resume'
        elif target_path is None:
            target_path = request.path
            if not target_path.startswith('/petec'):
                target_path = f'/petec{target_path}'

        return redirect(f'https://peerslate.com{target_path}', code=302)

    # Case 2: only the main peerslate.com domain needs the next checks
    # below (renamed/removed paths). Any other host (like localhost
    # during local testing) skips straight through unchanged.
    if not is_platform_hostname(request.host):
        return None

    # Case 3: old URLs from before the site was renamed/reorganized.
    # Anyone who still has one of these bookmarked gets sent to today's
    # equivalent page instead of hitting a dead link.
    if request.path in RETIRED_PORTFOLIO_PATHS:
        return redirect(RETIRED_PORTFOLIO_PATHS[request.path], code=302)

    # /skills is a real page again (the Skills profile tab), so it now
    # canonicalizes to /petec/skills like every other portfolio section.
    section_paths = {'/about', '/contact', '/hobbies', '/interview-me', '/my-story', '/skills', '/slate-board'}

    if request.path in section_paths:
        return redirect(f'/petec{request.path}', code=302)

    # No redirect needed - let Flask handle the request normally.
    return None


# -------------------------------------------------------
# LOAD KNOWLEDGE BASE
# Read all the Markdown files in docs/knowledge/ and keep
# them separated by filename. This lets the chat route send
# only the most relevant files instead of overwhelming Claude
# with the entire knowledge base on every question.
# We do this once at startup so it's fast on every request.
# -------------------------------------------------------

def load_knowledge_files():
    # Build the path to the knowledge folder, relative to this file
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'docs', 'knowledge')

    knowledge_files = {}

    # Find all .md files in that folder, sorted alphabetically
    for filepath in sorted(glob.glob(os.path.join(knowledge_dir, '*.md'))):
        filename = os.path.basename(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # Skip empty files (e.g. portfolio_projects.md which hasn't been filled in yet)
        if not content:
            continue

        # Store each file separately so we can choose the best sources for each question
        knowledge_files[filename] = content

    return knowledge_files

# Load the knowledge files once when Flask starts up
KNOWLEDGE_FILES = load_knowledge_files()


# -------------------------------------------------------
# CHOOSE RELEVANT KNOWLEDGE
# The full knowledge base is large and resume-like. For
# cleaner answers, this function picks the most useful files
# for the visitor's actual question.
# -------------------------------------------------------

def build_knowledge_context(user_message):
    question = user_message.lower()

    selected_files = ['professional_summary.md']

    # Route common topics to the files that contain the best supporting detail.
    if any(word in question for word in ['job', 'role', 'career', 'work', 'experience', 'employer', 'northrop', 'l3', 'dod', 'air force']):
        selected_files.append('career_history.md')

    if any(word in question for word in ['skill', 'tool', 'technology', 'mbse', 'cameo', 'doors', 'sysml', 'jira', 'python', 'ai', 'automation']):
        selected_files.append('technical_skills.md')
        selected_files.append('skills_evidence.md')

    # "How many instances of leadership...", "how is that backed up", etc. —
    # route to the evidence-count summary so the numbers on the skill badges
    # can be verified and supported with examples.
    if any(word in question for word in ['how many', 'how much', 'instances', 'number of', 'evidence', 'backed', 'verify', 'count', 'leadership', 'project management', 'sustainment', 'requirements']):
        selected_files.append('skills_evidence.md')
        selected_files.append('accomplishments.md')

    if any(word in question for word in ['certification', 'certifications', 'degree', 'education', 'school', 'pmp', 'phd', 'award', 'accomplishment']):
        selected_files.append('accomplishments.md')

    if any(word in question for word in ['recruiter', 'hire', 'candidate', 'fit', 'target', 'industry', 'clearance', 'available']):
        selected_files.append('recruiter_faq.md')

    # Personal-story questions (the My Story page invites these) route to
    # the approved story chapter file so answers stay grounded.
    if any(word in question for word in ['story', 'chapter', 'pizza', 'domino', 'healthcare', '36', 'back to school', 'pandemic', 'covid', 'run', 'running', '100 miles', 'skydiv', 'travel', 'countries', 'dog', 'blazer', 'falcon', 'danielle', 'family', 'hobby', 'hobbies', 'life', 'personal', 'hiking', 'baseball']):
        selected_files.append('personal_story.md')

    # Keep source order stable and remove duplicates.
    selected_files = list(dict.fromkeys(selected_files))

    context_parts = []
    for filename in selected_files:
        content = KNOWLEDGE_FILES.get(filename)
        if content:
            context_parts.append(f"---\nSource: {filename}\n\n{content}")

    return "\n\n".join(context_parts)


# -------------------------------------------------------
# SYSTEM PROMPT
# This is the instruction we give Claude before every
# conversation. It tells Claude who it is, what it can
# discuss, what it must never discuss, and gives it
# selected knowledge files as context.
# -------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are Pete Carter's professional portfolio assistant. You answer questions from recruiters, hiring managers, and other visitors to Pete's portfolio website.

IMPORTANT RULES:
- Only answer based on the knowledge base provided below. Do not invent, guess, or embellish facts about Pete.
- Keep answers concise and professional — 1 to 3 short sentences is ideal.
- Be warm and helpful in tone.
- Use plain text only. Do not use Markdown, hashtags, headings, bold text, bullets, numbered lists, or asterisks.
- If asked something outside your approved topics, politely say you can't help with that and suggest the visitor use the Contact page to reach Pete directly.
- For recruiter or resume questions, make the answer evidence-grounded. Give the answer first, then include a short source sentence such as "This is based on Pete's resume and career-history sources." Add a short limitation when the sources do not fully answer the question.

RESPONSE STYLE:
- Write in complete, polished sentences suitable for a professional portfolio website.
- Answer the visitor's question directly in the first sentence.
- Prioritize the most impressive or decision-useful information instead of listing every detail.
- Use a second short paragraph when the answer needs more than one idea.
- Do not copy raw resume bullets or fragments from the knowledge base.
- Do not end with salesy follow-up questions like "Would you like to know more?"
- If the question asks for a count, give the count first, then briefly explain it.

APPROVED TOPICS:
- Pete's job titles, responsibilities, and the systems and programs in his knowledge base
- Tools and technologies (Cameo, DOORS, Jira, Python, Flask, Claude API, etc.)
- Education, certifications (PMP, Ph.D. program), and accomplishments
- Career goals and target roles
- This portfolio website and the projects it showcases
- General location (Athens, Alabama)
- The fact that Pete holds an active U.S. Secret security clearance
- Pete's public hobbies (smart home, technology)

TOPICS TO NEVER DISCUSS:
- Security clearance details beyond "Pete holds an active U.S. Secret security clearance"
- Colleagues' names or personal information about others
- Pete's home address, phone number, or date of birth
- Financial or medical information
- Anything not explicitly in the knowledge base below

PETE'S KNOWLEDGE BASE:
{knowledge_context}"""


# -------------------------------------------------------
# CLEAN CHATBOT REPLIES
# Claude sometimes returns Markdown formatting like **bold**
# or numbered lists. The chat bubble displays plain text, so
# this removes those symbols before sending the answer back.
# -------------------------------------------------------

def clean_chatbot_reply(reply):
    reply = re.sub(r'(?m)^\s{0,3}#{1,6}\s*', '', reply)   # Remove Markdown heading markers like ### Title
    reply = re.sub(r'\*\*(.*?)\*\*', r'\1', reply)        # Remove Markdown bold markers like **text**
    reply = re.sub(r'__(.*?)__', r'\1', reply)            # Remove alternate bold markers like __text__
    reply = re.sub(r'`([^`]*)`', r'\1', reply)            # Remove inline code backticks
    reply = re.sub(r'(?m)^\s*[-*]\s+', '', reply)         # Remove bullet markers without changing the words
    reply = re.sub(r'(?m)^\s*\d+\.\s+', '', reply)        # Remove numbered-list markers without changing the words
    reply = re.sub(r'[ \t]+', ' ', reply)                 # Collapse extra spaces without deleting paragraph breaks
    reply = re.sub(r'\n{3,}', '\n\n', reply)              # Keep paragraph breaks, but prevent giant blank gaps

    return reply.strip()


# -------------------------------------------------------
# EXISTING PAGE ROUTES (unchanged)
# -------------------------------------------------------

# True only when this request's domain is the real production site
# (peerslate.com), so the redirect rules above don't accidentally run
# during local testing on 127.0.0.1/localhost.
def is_platform_hostname(hostname):
    clean_host = hostname.split(':', 1)[0].lower()
    return clean_host in {'peerslate.com', 'www.peerslate.com'}

# The root URL ("/") is the cinematic Experience page (2026-07-10):
# it won the side-by-side comparison against the old marketing homepage.
# The previous marketing page remains reachable at /peerslate.
@app.route('/')
def home():
    return render_template('experience.html')

@app.route('/petec')
@app.route('/portfolio')
@app.route('/pete')
@app.route('/overview')
@app.route('/petec/overview')
def portfolio_home():
    return redirect('/petec/resume', code=302)

@app.route('/peerslate')
def peerslate_home():
    return render_template('peerslate.html')

# EXPERIENCE (2026-07-08): the new cinematic homepage candidate. It lives
# at its own address (linked as "Experience" in the header) so Pete can
# compare it side-by-side with the current homepage at / before deciding
# which one wins. Nothing about the old homepage changes.
@app.route('/experience')
def experience():
    return render_template('experience.html')


@app.route('/atrium')
@app.route('/petec/atrium')
def atrium():
    return redirect(url_for('home'), code=302)


@app.route('/_internal/design-system')
def design_system_preview():
    """Render Foundation A without exposing an unfinished page publicly.

    The preview is available automatically on local development hosts. A
    deployed review environment can opt in explicitly with
    ENABLE_DESIGN_SYSTEM_PREVIEW=1; production remains closed by default.
    """
    preview_enabled = os.environ.get('ENABLE_DESIGN_SYSTEM_PREVIEW') == '1'
    clean_host = request.host.split(':', 1)[0].lower().strip('[]')
    is_local = clean_host in {'127.0.0.1', 'localhost', '::1'}

    if not (is_local or preview_enabled):
        abort(404)

    return render_template('design_system_preview.html')

@app.route('/about')
@app.route('/petec/about')
def about():
    return render_template('about.html')

@app.route('/my-story')
@app.route('/petec/my-story')
def my_story():
    # The four-act cinematic story page renders entirely from structured
    # fixture data so the same templates work for any profile's story.
    story_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'story_data.json')

    with open(story_path, 'r', encoding='utf-8') as f:
        story = json.load(f)

    return render_template('my_story.html', story=story)

# PROJECTS EXHIBITION (2026-07-13): the Projects page is now a cinematic
# three-panel exhibition (Concept 1 of the master hybrid brief in
# docs/design/projects-experience/). Projects are profile-scoped data from
# the profile's resume fixture — never hardcoded into templates — so the
# same components render any profile's projects.
def _load_profile_projects(profile_slug):
    """Return the profile's ordered, publishable project list."""
    resume_data = _load_resume_profile(profile_slug)
    if resume_data is None:
        return None
    projects = [dict(p) for p in resume_data.get('projects', [])]
    projects.sort(key=lambda p: p.get('display_order', 99))
    return projects


# Projects Board registry (2026-07-13): the /petec/work page was rebuilt from
# the "too much" cinematic exhibition into a simple card grid + detail modal.
# Its data is a profile-scoped, editor-friendly view model kept in its own file
# so an owner (or a future edit UI) can add/change projects without touching
# the template. Mirrors RESUME_PROFILE_FILES so it stays multi-tenant ready.
PROJECT_BOARD_FILES = {
    'petec': 'projects_board.json',
}


def _load_project_board(profile_slug):
    """Load one profile's Projects Board view model (board meta + projects)."""
    data_filename = PROJECT_BOARD_FILES.get(profile_slug)
    if data_filename is None:
        return None

    board_path = os.path.join(
        os.path.dirname(__file__),
        'static',
        'data',
        data_filename,
    )
    try:
        with open(board_path, 'r', encoding='utf-8') as board_file:
            board_data = json.load(board_file)
    except (OSError, ValueError):
        return None

    data_slug = board_data.get('profile_slug')
    if data_slug and data_slug != profile_slug:
        return None

    # Graceful image fallback: a project may reference a photo whose file has
    # not been uploaded yet (an owner points at images/projects/home-gym.jpg
    # before dropping the file in). Rather than render a broken image, degrade
    # that visual to its themed illustration until the asset exists — so the
    # card "just works" the moment the file appears, with no code change.
    static_dir = os.path.join(os.path.dirname(__file__), 'static')

    def _resolve_visual(visual):
        if isinstance(visual, dict) and visual.get('kind') == 'photo':
            src = visual.get('src') or ''
            file_path = os.path.join(static_dir, *src.split('/')) if src else ''
            if not file_path or not os.path.isfile(file_path):
                return {
                    'kind': 'illustration',
                    'theme': visual.get('fallback_theme', 'platform'),
                    'alt': visual.get('alt', ''),
                }
        return visual

    for project in board_data.get('projects', []):
        _normalize_board_project(project)
        project['card_image'] = _resolve_visual(project.get('card_image'))
        detail = project['detail']
        detail['hero_device'] = _resolve_visual(detail.get('hero_device'))

    return board_data


def _normalize_board_project(project):
    """Fill in a safe, complete shape so a partially-authored project (e.g. an
    on-deck card captured before its detail is written, or a record from a
    future edit UI) renders instead of 500-ing the whole page. The template
    reaches deep into detail.actions/info/team, and Jinja raises on chained
    access through a missing object — so every nested object gets a default."""
    project.setdefault('tags', [])
    project.setdefault('status', 'active')
    project.setdefault('status_label',
                       (project.get('status') or 'active').replace('-', ' ').title())
    project.setdefault('title', 'Untitled project')
    project.setdefault('summary', '')

    detail = project.get('detail')
    if not isinstance(detail, dict):
        detail = {}
    project['detail'] = detail

    detail.setdefault('about', '')
    detail.setdefault('latest_update_ref', 0)
    for key in ('updates', 'milestones', 'media', 'links', 'notes',
                'key_features', 'tech_stack'):
        if not isinstance(detail.get(key), list):
            detail[key] = []

    logo = detail.get('logo')
    if not isinstance(logo, dict):
        logo = {'kind': 'illustration', 'theme': 'platform'}
    logo.setdefault('alt', project.get('title', ''))
    detail['logo'] = logo

    actions = detail.get('actions') if isinstance(detail.get('actions'), dict) else {}
    for key in ('view_live', 'github', 'roadmap'):
        action = actions.get(key) if isinstance(actions.get(key), dict) else {}
        action.setdefault('enabled', False)
        action.setdefault('url', '')
        actions[key] = action
    detail['actions'] = actions

    info = detail.get('info') if isinstance(detail.get('info'), dict) else {}
    for key in ('category', 'type', 'status', 'visibility', 'created'):
        info.setdefault(key, '—')
    team = info.get('team') if isinstance(info.get('team'), dict) else {}
    team.setdefault('note', '—')
    info['team'] = team
    detail['info'] = info
    return project




@app.route('/work')
@app.route('/petec/work')
@app.route('/projects')
@app.route('/petec/projects')
def work():
    return redirect('/petec/resume#experience', code=302)


@app.route('/<profile_slug>/work')
def profile_work(profile_slug):
    """Serve any registered profile's board (multi-tenant). Unknown profiles
    404 rather than falling back to another tenant's data."""
    _load_resume_profile(profile_slug)
    return redirect(f'/{profile_slug}/resume#experience', code=302)


@app.route('/petec/work/<slug>')
def project_case_study(slug):
    """A project's documentary-style case study. Only projects whose record
    is ready AND approved for publishing get a detail page — incomplete and
    demonstration projects intentionally 404 here rather than rendering
    invented content."""
    projects = _load_profile_projects('petec') or []
    project = next((p for p in projects if p.get('slug') == slug), None)
    if (
        project is None
        or not project.get('details_ready')
        or not project.get('publish_detail')
        or not project.get('case_study_sections')
    ):
        abort(404)
    return redirect('/petec/resume#experience', code=302)

@app.route('/slate-board')
@app.route('/petec/slate-board')
def slate_board():
    # "My Slate Board" - Pete's goals, progress, badges, and shareable
    # wins/thoughts. MVP is a fully designed static preview: the entries,
    # goal percentages, and badges live in the template as sample content.
    # A future pass adds real storage plus the draft/private/public flow.
    return render_template(
        'slate_board.html',
        database_ui_enabled=app.config['PEERSLATE_DATABASE_UI_ENABLED'],
    )


@app.route('/interview-me')
@app.route('/petec/interview-me')
def interview_me():
    # INTERVIEW WORKSPACE (2026-07-13): the page is now a three-mode working
    # application (Interview Me / Interview You / Video Me) wrapped around
    # the original practice studio — every original control keeps its id so
    # static/js/interview.js runs unchanged; static/js/interview-workspace.js
    # adds the workspace chrome. All AI calls still hit the same /api/chat.
    #
    # Entitlement hooks (server-side, not browser-decided): the workspace
    # will eventually sit behind a paywall. These flags come from the
    # environment so a deployment can gate tiers without code changes.
    # Nothing here fabricates billing — defaults keep today's behavior.
    entitlements = {
        'written_practice': True,   # current free behavior
        'model_answers': True,      # current free behavior
        'mock_interviews': True,    # current free behavior
        'video_studio': os.environ.get(
            'INTERVIEW_VIDEO_STUDIO', 'preview'
        ),  # preview | enabled | locked
        'progress_history': os.environ.get(
            'INTERVIEW_PROGRESS_HISTORY', 'preview'
        ),  # preview | enabled | locked
    }

    # CONCEPT 1 (2026-07-15): the Focused Coaching Workspace redesign runs
    # behind a flag until parity is verified (docs: the
    # PeerSlate_Interview_Concept1 handoff). ?concept1=1 previews the new
    # page, ?classic=1 forces the current one, and INTERVIEW_CONCEPT1=on
    # flips the default for a deployment without a code change.
    concept1_default = os.environ.get('INTERVIEW_CONCEPT1', 'on') == 'on'
    wants_concept1 = request.args.get('concept1') == '1' or (
        concept1_default and request.args.get('classic') != '1'
    )
    if wants_concept1:
        return render_template(
            'interview_concept1.html',
            interview_entitlements=entitlements,
            interview_evidence=INTERVIEW_SLATE_EVIDENCE,
        )
    return render_template('interview_me.html', interview_entitlements=entitlements)


@app.route('/skills')
@app.route('/petec/skills')
def skills():
    # The Skills profile tab now has its own page. It reuses the same
    # resume_data.json the resume page reads, so the skill cards and their
    # evidence popovers only ever need updating in one place.
    resume_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'resume_data.json')

    with open(resume_path, 'r', encoding='utf-8') as f:
        resume_data = json.load(f)

    return render_template('skills.html', resume=resume_data)


# -------------------------------------------------------
# THE SLATE (platform hub) + SLATE FEED layers
# "The Slate" is the main product experience: one page with four
# internal tabs — Slate Feed / My Slate / Daily Slate / Slate
# Paths (from Pete's four 2026-07-08 mockups). The old separate
# top-level "Slate Feed" and "Slate Board" nav links now live
# inside it. The feed's deeper layers (Progress / Pulse / Break)
# kept their own pages and simply moved under /the-slate/*; the
# People layer is the hub's landing view. Old /slate-feed URLs
# redirect so no bookmark or shared link ever breaks.
#
# The feed is built to aggregate events from EVERY member's
# slate — each item in static/data/slate_feed.json names its
# author, so when other profiles exist their events join the
# same feed automatically. Today the only profile is Pete's, so
# every card is pulled from his real Slate Board content and
# links back to it.
# -------------------------------------------------------


@app.route('/the-slate')
def the_slate():
    # THE SLATE LANDING = the People & Interests living board (2026-07-14,
    # Pete): the approved corkboard feed replaced the old Slate Feed landing
    # at this address. The previous landing template (the_slate_feed.html)
    # stays on disk for easy rollback, and its hub links (Slate Board /
    # My Slate / Daily Slate) now live in the board's feed strip.
    return _render_people_interests_board()


@app.route('/the-slate/my-slate')
def the_slate_my():
    # Tab 2 — My Slate: the user's personal goal map. Static preview
    # content in the template (same convention as the Slate Board MVP).
    return render_template('the_slate_my.html')


@app.route('/the-slate/daily')
def the_slate_daily():
    # Tab 3 — Daily Slate: the daily return hook ("What did you move
    # forward today?"). The composer posts a real card (the-slate.js,
    # stored per-browser) so the page demonstrates the loop end-to-end.
    return render_template(
        'the_slate_daily.html',
        database_ui_enabled=app.config['PEERSLATE_DATABASE_UI_ENABLED'],
    )


@app.route('/the-slate/paths')
def the_slate_paths():
    # Slate Paths merged INTO My Slate (2026-07-08): the goal map, paths,
    # daily check-in, and people/progress now live on one dashboard. This
    # route redirects so old links (and url_for('the_slate_paths')) keep
    # working.
    return redirect(url_for('the_slate_my'), code=302)

def relative_time_label(iso_timestamp, now):
    # Turns a stored timestamp like "2026-07-02T09:15:00" into the live
    # feed label a visitor expects ("2h ago", "5d ago"), computed fresh
    # on every request — this is what keeps the feed feeling alive.
    event_time = datetime.fromisoformat(iso_timestamp)
    seconds = max(0, (now - event_time).total_seconds())

    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{max(1, minutes)}m ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"

    days = hours // 24
    if days < 7:
        return f"{days}d ago"

    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"

    # Older than about a month: show the calendar date instead.
    # (event_time.day avoids strftime's %-d, which breaks on Windows.)
    return f"{event_time.strftime('%b')} {event_time.day}"


def load_slate_feed():
    feed_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'slate_feed.json')

    with open(feed_path, 'r', encoding='utf-8') as f:
        feed = json.load(f)

    now = datetime.now()

    # Newest events first, like any real activity feed.
    feed['items'] = sorted(feed['items'], key=lambda item: item['timestamp'], reverse=True)

    for item in feed['items']:
        item['time_label'] = relative_time_label(item['timestamp'], now)
        # Swap the author key ("petec") for the full author object so the
        # template can read item.author.name / item.author.avatar directly.
        item['author'] = feed['authors'][item['author']]

    # Weekly Review: percent + the current Monday-to-Sunday range are
    # computed here, not stored, so the card is always this week's.
    review = feed['weekly_review']
    review['percent'] = round(100 * review['actions_done'] / review['actions_planned'])
    week_start = (now - timedelta(days=now.weekday())).date()
    week_end = week_start + timedelta(days=6)
    review['range_label'] = (
        f"{week_start.strftime('%b')} {week_start.day} – "
        f"{week_end.strftime('%b')} {week_end.day}"
    )

    keep_building = feed['keep_building']
    keep_building['percent'] = round(100 * keep_building['done'] / keep_building['total'])

    return feed


@app.route('/the-slate/progress')
def slate_feed():
    # Progress merged INTO the feed landing (People & Progress) on
    # 2026-07-08. Endpoint name stays "slate_feed" so every url_for()
    # keeps working; it now redirects to the combined landing.
    return redirect(url_for('the_slate'), code=302)


@app.route('/api/slate-feed')
def slate_feed_api():
    # The same feed as JSON — this is the seam where the page's data layer
    # already works like a real multi-profile feed service.
    return jsonify(load_slate_feed())


@app.route('/the-slate/pulse')
def slate_feed_pulse():
    # The Pulse view — the community's momentum at a glance: this-week
    # stats, trending skills, rising goals, and what's moving right now.
    # Static preview content for the MVP (no live cross-member data yet).
    return render_template('slate_pulse.html')


@app.route('/the-slate/break')
def slate_feed_break():
    # The Break view — the "step back and recharge" tab: an encouragement
    # panel, recharge ideas, community shout-outs, and a daily spark. Keeps
    # the platform human, not just a metrics grind. Static preview for now.
    return render_template(
        'slate_break.html',
        database_ui_enabled=app.config['PEERSLATE_DATABASE_UI_ENABLED'],
    )


# PS-FEAT-002: the People & Interests living board — the corkboard-style
# continuous social feed built from Pete's two approved mockups. Approved on
# 2026-07-14 to BE The Slate landing (the_slate() above). The board is
# rendered by static/js/people-interests.js from /api/feed/people-interests
# (cursor pagination); the supporting rails render server-side from the same
# fixture file. Every non-Pete author is a representative sample member.
def _render_people_interests_board():
    return render_template(
        'the_slate_people_interests.html',
        initial_feed=people_interests_feed.get_page(limit=16),
        feed_authors=people_interests_feed.authors,
        left_rail=people_interests_feed.left_rail,
        right_rail=people_interests_feed.right_rail,
        reaction_types=list(REACTION_TYPES),
        goal_reaction=GOAL_REACTION,
        post_body_max=POST_BODY_MAX,
    )


@app.route('/the-slate/people-interests')
def the_slate_people_interests():
    # The board launched at this address (2026-07-13) and became The Slate
    # landing the next day — forward so any shared link keeps working.
    return redirect(url_for('the_slate'), code=302)


# Old /slate-feed addresses: everything moved into The Slate on
# 2026-07-08, so these permanently forward to the new homes. The old
# People view (slate_people.html) was superseded by the hub's People
# layer — its URL lands on The Slate itself.
@app.route('/slate-feed')
def slate_feed_legacy():
    return redirect(url_for('slate_feed'), code=302)


@app.route('/slate-feed/pulse')
def slate_feed_pulse_legacy():
    return redirect(url_for('slate_feed_pulse'), code=302)


@app.route('/slate-feed/break')
def slate_feed_break_legacy():
    return redirect(url_for('slate_feed_break'), code=302)


@app.route('/slate-feed/people')
def slate_feed_people():
    # Keeps old links alive AND keeps url_for('slate_feed_people')
    # working anywhere it still appears.
    return redirect(url_for('the_slate'), code=302)


# -------------------------------------------------------
# PLATFORM PLACEHOLDER PAGES
# These four pages back the global PeerSlate header links.
# They are intentionally simple "coming soon" pages: the goal
# is showing where the platform is headed (career search,
# networking, profile discovery, recruiter tools) before those
# features actually exist. All four share one template.
# -------------------------------------------------------

@app.route('/career-search')
def career_search():
    return render_template(
        'platform_page.html',
        page_title='Career Search',
        page_kicker='Platform Preview',
        page_lead='Search openings matched to verified skill evidence instead of keyword-stuffed resumes.',
        page_points=[
            'Roles matched against evidence-backed skills, not just titles',
            'Filters for clearance, certifications, and engineering domain',
            'Save searches and get notified when matching roles appear',
        ],
    )


@app.route('/my-network')
def my_network():
    return render_template(
        'platform_page.html',
        page_title='My Network',
        page_kicker='Platform Preview',
        page_lead='Build a professional network around demonstrated work, endorsements, and shared projects.',
        page_points=[
            'Connect with engineers, mentors, and hiring teams',
            'Endorsements tied to specific evidence, not one-click badges',
            'Follow profiles to see new projects and milestones',
        ],
    )


@app.route('/explore-profiles')
def explore_profiles():
    return render_template(
        'platform_page.html',
        page_title='Explore Profiles',
        page_kicker='Platform Preview',
        page_lead='Browse evidence-driven professional profiles like Pete’s, each with its own AI assistant.',
        page_points=[
            'Every profile pairs claims with verifiable career evidence',
            'Ask each profile’s AI assistant recruiter-style questions',
            'Compare candidates on outcomes instead of buzzwords',
        ],
    )


@app.route('/for-recruiters')
def for_recruiters():
    return render_template(
        'platform_page.html',
        page_title='For Recruiters',
        page_kicker='Platform Preview',
        page_lead='Screen faster with AI answers grounded in approved, verifiable candidate evidence.',
        page_points=[
            'Ask candidate AI assistants the questions you would ask in a phone screen',
            'Every answer cites the approved source it came from',
            'Shortlist, compare, and reach out from one place',
        ],
    )

@app.route('/hobbies')
@app.route('/petec/hobbies')
def hobbies():
    return render_template('hobbies.html')

@app.route('/contact')
@app.route('/petec/contact')
def contact():
    return render_template('contact.html')

RESUME_PROFILE_FILES = {
    # Fixture registry only. Reusable components read all profile-owned
    # content from the selected structured data source.
    'petec': 'resume_data.json',
}


def _load_resume_profile(profile_slug):
    """Load one allowlisted public profile without cross-tenant fallback."""
    data_filename = RESUME_PROFILE_FILES.get(profile_slug)
    if data_filename is None:
        abort(404)

    resume_path = os.path.join(
        os.path.dirname(__file__),
        'static',
        'data',
        data_filename,
    )
    with open(resume_path, 'r', encoding='utf-8') as resume_file:
        resume_data = json.load(resume_file)

    data_slug = resume_data.get('profile', {}).get('slug')
    if data_slug and data_slug != profile_slug:
        abort(404)

    return resume_data


def _render_living_resume(
    profile_slug='petec',
    template_name='resume2.html',
    resume_version=2,
    is_internal_preview=False,
):
    """Build either résumé composition from one shared structured model."""
    resume_data = _load_resume_profile(profile_slug)

    role_by_id = {item['id']: item for item in resume_data['career_roles']}
    education_by_id = {item['id']: item for item in resume_data['education']}
    metric_by_id = {item['id']: item for item in resume_data['metrics']}
    skill_by_id = {
        item['id']: item
        for item in resume_data['skills']
        if item.get('public_display')
    }

    events = []
    for event_config in resume_data['living_resume']['events']:
        event = dict(event_config)
        is_role = event['source'] == 'role'
        record = role_by_id[event['source_id']] if is_role else education_by_id[event['source_id']]

        if is_role:
            event.update({
                'title': record['employer'],
                'subtitle': record['title'],
                'summary': record['summary'],
                'accomplishments': record['accomplishments'],
                'responsibilities': record['responsibilities'],
                'focus_tags': record['focus_tags'],
                'skills': [
                    skill_by_id[skill_id]
                    for skill_id in record['related_skill_ids']
                    if skill_id in skill_by_id
                ][:8],
            })
        else:
            event.update({
                'title': record['credential'],
                'subtitle': record['institution'],
                'summary': record['detail'],
                'status': record['status'],
                'accomplishments': [],
                'responsibilities': [],
                'focus_tags': [],
                'skills': [
                    skill_by_id[skill_id]
                    for skill_id in event.get('featured_skill_ids', [])
                    if skill_id in skill_by_id
                ],
            })

        event['metrics'] = [
            metric_by_id[metric_id]
            for metric_id in event.get('featured_metric_ids', [])
            if metric_id in metric_by_id
        ]

        # Every experience chapter shows exactly five "key outcome" cards:
        # start with the featured metrics, then fill from accomplishment
        # bullets (skipping ones a metric already represents) so shorter
        # roles read as full as the flagship one. Education/credential
        # chapters carry no bullets, so they fall back to their summary.
        outcomes = []
        used_evidence = set()
        for metric in event['metrics']:
            evidence_id = metric.get('highlight_evidence_id')
            outcomes.append({
                'value': metric['value'],
                'label': metric['label'],
                'context': metric.get('context'),
                'evidence_id': evidence_id,
            })
            if evidence_id:
                used_evidence.add(evidence_id)
        for accomplishment in event['accomplishments']:
            if len(outcomes) >= 5:
                break
            if accomplishment.get('id') in used_evidence:
                continue
            outcomes.append({
                'label': accomplishment.get('short_label', 'Impact outcome'),
                'text': accomplishment['text'],
                'evidence_id': accomplishment.get('id'),
            })
        event['outcomes'] = outcomes[:5]

        event['timeline_detail'] = (
            event.get('timeline_detail')
            or (record['institution'] if event['kind'] in {'Education', 'Future'} else event['display_period'])
        )
        events.append(event)

    ledger_events = [event for event in events if event.get('show_in_ledger')]
    constellation_events = [event for event in events if event.get('show_in_constellation')]
    role_event_by_id = {
        event['source_id']: event
        for event in events
        if event.get('source') == 'role'
    }

    # Give each timeline node a distinct jewel color (and remember the
    # role colors/icons so the experience cards can echo them). The
    # palette cycles, so any profile length still renders a pleasant
    # left-to-right spectrum.
    orb_palette = ['#7c5cff', '#3f6fe0', '#2aa8e6', '#2fc38d', '#2456c9', '#e0a52e', '#2bc0c6']
    role_orb = {}
    for index, event in enumerate(ledger_events):
        color = orb_palette[index % len(orb_palette)]
        event['orb_color'] = color
        if event['source'] == 'role':
            role_orb[event['source_id']] = (color, event.get('icon', 'briefcase'))

    living_resume = resume_data['living_resume']
    career_highlight_metrics = [
        metric_by_id[metric_id]
        for metric_id in living_resume['career_highlight_metric_ids']
        if metric_id in metric_by_id
    ]
    resume2_impact_metrics = []
    resume2_impact_icons = living_resume.get('resume2_impact_metric_icons', {})
    for metric_id in living_resume.get('resume2_impact_metric_ids', []):
        metric = metric_by_id.get(metric_id)
        if not metric:
            continue
        impact_metric = dict(metric)
        related_role_ids = metric.get('related_role_ids', [])
        impact_metric['source_role_id'] = related_role_ids[0] if related_role_ids else None
        impact_metric['resume2_icon'] = resume2_impact_icons.get(metric_id, 'chart')
        resume2_impact_metrics.append(impact_metric)
    career_highlight_skills = [
        skill_by_id[skill_id]
        for skill_id in living_resume['career_highlight_skill_ids']
        if skill_id in skill_by_id
    ]
    constellation_skills = [
        skill_by_id[skill_id]
        for skill_id in living_resume['constellation_skill_ids']
        if skill_id in skill_by_id
    ]
    constellation_evidence_metrics = [
        metric_by_id[metric_id]
        for metric_id in living_resume['constellation_evidence_metric_ids']
        if metric_id in metric_by_id
    ]
    constellation_outcome_metrics = [
        metric_by_id[metric_id]
        for metric_id in living_resume['constellation_outcome_metric_ids']
        if metric_id in metric_by_id
    ]
    degree_ids = {
        event['source_id']
        for event in living_resume['events']
        if event['source'] == 'education' and event['kind'] == 'Education'
    }

    # Education card lists degrees most-recent first. Parse the "Month YYYY"
    # date for sorting; anything undated sorts last so a missing date never
    # crashes the page.
    def _degree_sort_key(item):
        raw = (item.get('date') or '').strip()
        if raw:
            try:
                return datetime.strptime(raw, '%B %Y')
            except ValueError:
                pass
        return datetime.min

    resume_degrees = sorted(
        (item for item in resume_data['education'] if item['id'] in degree_ids),
        key=_degree_sort_key,
        reverse=True,
    )
    # Development gathers forward-looking growth (upcoming/in-progress
    # non-degree items). A profile can also pin an already-earned credential
    # here with "show_in_development": true — e.g. the PMP, which was moved off
    # the timeline into this card — so earned status alone no longer excludes
    # it.
    _earned_statuses = {'Certified', 'Completed', 'Earned', 'Obtained'}
    # Earned professional certifications (non-degree, already earned) now get
    # their own Certifications card — e.g. the PMP.
    resume_certifications = [
        item
        for item in resume_data['education']
        if item['id'] not in degree_ids
        and item.get('status') in _earned_statuses
    ]
    _certification_ids = {item['id'] for item in resume_certifications}
    # Development gathers forward-looking growth (in-progress / upcoming
    # non-degree items). Earned certs live in the Certifications card instead.
    resume_development = [
        item
        for item in resume_data['education']
        if item['id'] not in degree_ids
        and item['id'] not in _certification_ids
        and (
            item.get('status') not in _earned_statuses
            or item.get('show_in_development')
        )
    ]
    # Recognition / awards from the profile's own achievements list.
    resume_achievements = resume_data.get('achievements', [])
    featured_resume_skills = [
        item
        for item in resume_data['skills']
        if item.get('featured') and item.get('public_display')
    ]

    resume_experience = list(reversed(resume_data['career_roles']))
    for role in resume_experience:
        color, icon = role_orb.get(role['id'], ('#2456c9', 'briefcase'))
        role['orb_color'] = color
        role['orb_icon'] = icon

    # The canonical Living Resume presents a non-retired public proof set.
    # The full filtered list ships to the template: collapsed cards show
    # a short preview slice, and the expanded chapter view shows all of
    # them (DoD has 13, L3Harris 9, Northrop 5 after filtering).
    resume2_experience = []
    for chapter_index, role in enumerate(resume_experience, start=1):
        resume2_role = dict(role)
        resume2_role['resume2_accomplishments'] = [
            item
            for item in role['accomplishments']
            if 'micap' not in item['text'].lower()
        ]
        role_event = role_event_by_id.get(role['id'], {})
        resume2_role['chapter_number'] = f'{chapter_index:02d}'
        resume2_role['chapter_marker'] = role_event.get('marker', role['employer'][:2].upper())
        resume2_role['resume2_featured_metrics'] = role_event.get('metrics', [])

        selected_impacts = []
        accomplishments_by_id = {
            item['id']: item
            for item in resume2_role['resume2_accomplishments']
        }
        for preview_ref in role.get('resume2_preview_refs', []):
            source_type = preview_ref.get('source_type')
            source_id = preview_ref.get('source_id')
            source = None
            if source_type == 'metric':
                source = metric_by_id.get(source_id)
            elif source_type == 'skill':
                source = skill_by_id.get(source_id)
            elif source_type == 'accomplishment':
                source = accomplishments_by_id.get(source_id)
            if not source:
                continue

            default_value = (
                source.get('value')
                or source.get('display_name')
                or source.get('short_label')
            )
            default_label = source.get('label') or 'Approved public evidence'
            value = preview_ref.get('value', default_value)
            label = preview_ref.get('label', default_label)
            if not value or not label:
                continue
            selected_impacts.append({
                'value': value,
                'label': label,
                'kind': source_type,
                'source_id': source_id,
            })
            if len(selected_impacts) == 2:
                break

        if not selected_impacts:
            selected_impacts = [
                {
                    'value': metric['value'],
                    'label': metric['label'],
                    'kind': 'metric',
                    'source_id': metric['id'],
                }
                for metric in resume2_role['resume2_featured_metrics'][:2]
            ]
        if len(selected_impacts) < 2:
            for skill_id in role.get('related_skill_ids', []):
                skill = skill_by_id.get(skill_id)
                if not skill:
                    continue
                selected_impacts.append({
                    'value': skill['display_name'],
                    'label': 'Evidence-backed capability',
                    'kind': 'skill',
                    'source_id': skill_id,
                })
                if len(selected_impacts) == 2:
                    break
        resume2_role['resume2_selected_impacts'] = selected_impacts
        resume2_role['resume2_ai_context'] = '; '.join(
            f"{impact['value']} {impact['label']}"
            for impact in selected_impacts
        )
        expanded_impacts = [
            {
                'value': metric['value'],
                'label': metric['label'],
                'kind': 'metric',
                'source_id': metric['id'],
            }
            for metric in resume2_role['resume2_featured_metrics']
        ]
        expanded_impact_keys = {
            (impact['value'], impact['label'])
            for impact in expanded_impacts
        }
        for impact in selected_impacts:
            impact_key = (impact['value'], impact['label'])
            if impact_key in expanded_impact_keys:
                continue
            expanded_impacts.append(impact)
            expanded_impact_keys.add(impact_key)
        resume2_role['resume2_expanded_impacts'] = expanded_impacts

        full_record = [item['text'] for item in resume2_role['resume2_accomplishments']]
        for responsibility in role.get('responsibilities', []):
            if responsibility not in full_record:
                full_record.append(responsibility)
        resume2_role['resume2_full_record_bullets'] = full_record
        resume2_experience.append(resume2_role)

    resume2_skill_groups = []
    resume2_featured_skill_ids = living_resume.get('resume2_featured_skill_ids', [])
    resume2_skill_icons = living_resume.get('resume2_featured_skill_icons', {})
    for group_config in living_resume.get('resume2_skill_categories', []):
        group_skills = []
        for skill_id in resume2_featured_skill_ids:
            skill = skill_by_id.get(skill_id)
            if not skill:
                continue
            if skill.get('category_id') not in group_config['source_category_ids']:
                continue
            resume2_skill = dict(skill)
            resume2_skill['resume2_evidence_items'] = [
                item
                for item in skill.get('evidence_items', [])
                if 'micap' not in item['text'].lower()
            ]
            resume2_skill['icon'] = resume2_skill_icons.get(skill_id, 'shield')
            if resume2_skill['resume2_evidence_items']:
                group_skills.append(resume2_skill)
        if group_skills:
            resume2_skill_groups.append({
                'id': group_config['id'],
                'label': group_config['label'],
                'skills': group_skills[:3],
            })

    # Resume 2 uses an explicitly ordered fixture list so the reusable card
    # component never hardcodes Pete-specific skills. Every public card must
    # retain one or more approved evidence records from the selected profile.
    resume2_featured_skills = []
    for skill_id in living_resume.get('resume2_featured_skill_ids', []):
        skill = skill_by_id.get(skill_id)
        if not skill:
            continue
        resume2_skill = dict(skill)
        resume2_skill['resume2_evidence_items'] = [
            item
            for item in skill.get('evidence_items', [])
            if 'micap' not in item['text'].lower()
        ]
        # Presentational icon comes from the fixture's featured-skill icon map
        # so the reusable card component never hardcodes a per-skill glyph.
        resume2_skill['icon'] = resume2_skill_icons.get(skill_id, 'shield')
        if resume2_skill['resume2_evidence_items']:
            resume2_featured_skills.append(resume2_skill)

    education_order = {
        event.get('source_id'): index
        for index, event in enumerate(living_resume.get('events', []))
        if event.get('source') == 'education'
    }

    def _credential_item(item):
        credential_item = dict(item)
        credential_item['related_skills'] = [
            skill_by_id[skill_id]
            for skill_id in item.get('related_skill_ids', [])
            if skill_id in skill_by_id
        ]
        credential_item['supporting_metrics'] = [
            metric_by_id[metric_id]
            for metric_id in item.get('related_metric_ids', [])
            if metric_id in metric_by_id
        ]
        return credential_item

    credential_records = sorted(
        resume_data.get('education', []),
        key=lambda item: education_order.get(item['id'], 999),
    )
    credential_categories = [
        {
            'id': 'education',
            'title': 'Education',
            'icon': 'graduation',
            'summary': 'Academic foundations and advanced study that shaped the engineering path.',
            'items': [
                _credential_item(item)
                for item in credential_records
                if item.get('credential_category') == 'education'
            ],
        },
        {
            'id': 'certifications',
            'title': 'Certifications',
            'icon': 'award',
            'summary': 'Professional certifications supporting disciplined execution and leadership.',
            'items': [
                _credential_item(item)
                for item in credential_records
                if item.get('credential_category') == 'certifications'
            ],
        },
        {
            'id': 'development',
            'title': 'Professional Development',
            'icon': 'direction',
            'summary': 'Forward-looking learning supporting the next phase of the career.',
            'items': [
                _credential_item(item)
                for item in credential_records
                if item.get('credential_category') == 'development'
            ],
        },
        {
            'id': 'recognition',
            'title': 'Recognition & Achievements',
            'icon': 'sparkles',
            'summary': 'Awards and selections recognizing leadership, engineering, and team impact.',
            'items': [
                {
                    'id': item['id'],
                    'credential': item['title'],
                    'institution': item.get('org', ''),
                    'status': 'Recognition',
                    'date': item.get('year', ''),
                    'detail': item.get('detail', ''),
                    'related_skills': [],
                    'supporting_metrics': [],
                }
                for item in resume_data.get('achievements', [])
            ],
        },
    ]
    for category in credential_categories:
        count = len(category['items'])
        category['count_label'] = f'{count} public record' + ('' if count == 1 else 's')

    profile_name = resume_data['profile']['name'].strip()
    profile_first_name = profile_name.split()[0] if profile_name else 'Profile'
    resume_path = url_for('profile_resume', profile_slug=profile_slug)
    if is_platform_hostname(request.host):
        # Azure serves the public request to Flask over an internal HTTP hop
        # without a forwarded-proto header. Pin public metadata to the one
        # canonical HTTPS hostname instead of leaking that internal scheme.
        canonical_resume_url = f'https://peerslate.com{resume_path}'
    else:
        canonical_resume_url = url_for(
            'profile_resume',
            profile_slug=profile_slug,
            _external=True,
        )

    return render_template(
        template_name,
        resume=resume_data,
        living_resume=living_resume,
        ledger_events=ledger_events,
        constellation_events=constellation_events,
        career_highlight_metrics=career_highlight_metrics,
        resume2_impact_metrics=resume2_impact_metrics,
        career_highlight_skills=career_highlight_skills,
        constellation_skills=constellation_skills,
        constellation_evidence_metrics=constellation_evidence_metrics,
        constellation_outcome_metrics=constellation_outcome_metrics,
        resume_experience=resume_experience,
        resume2_experience=resume2_experience,
        resume_degrees=resume_degrees,
        resume_development=resume_development,
        resume_certifications=resume_certifications,
        resume_achievements=resume_achievements,
        featured_resume_skills=featured_resume_skills,
        resume2_skill_groups=resume2_skill_groups,
        resume2_featured_skills=resume2_featured_skills,
        resume2_credential_categories=credential_categories,
        skill_lookup=skill_by_id,
        profile_slug=profile_slug,
        profile_first_name=profile_first_name,
        canonical_resume_url=canonical_resume_url,
        resume_version=resume_version,
        is_internal_preview=is_internal_preview,
    )


@app.route('/resume')
def resume():
    """Send legacy resume bookmarks to the canonical Living Resume page."""
    return redirect(url_for('profile_resume', profile_slug='petec'), code=302)


@app.route('/<profile_slug>/resume')
def profile_resume(profile_slug):
    return _render_living_resume(
        profile_slug,
        template_name='resume2.html',
        resume_version=2,
    )


@app.route('/<profile_slug>/resume2')
def profile_resume2(profile_slug):
    _load_resume_profile(profile_slug)
    return redirect(url_for('profile_resume', profile_slug=profile_slug), code=302)


@app.route('/_internal/living-resume-v2')
def living_resume_v2():
    """Local-first review route for the same public Living Résumé render."""
    preview_enabled = os.environ.get('ENABLE_DESIGN_SYSTEM_PREVIEW') == '1'
    clean_host = request.host.split(':', 1)[0].lower().strip('[]')
    if clean_host not in {'127.0.0.1', 'localhost', '::1'} and not preview_enabled:
        abort(404)

    return _render_living_resume(
        'petec',
        template_name='resume2.html',
        resume_version=2,
        is_internal_preview=True,
    )


@app.route('/<profile_slug>/resume-ledger')
def profile_resume_ledger(profile_slug):
    """Retain old Ledger bookmarks without keeping a second public résumé."""
    _load_resume_profile(profile_slug)
    return redirect(f'/{profile_slug}/resume#experience', code=302)


# -------------------------------------------------------
# MVP 1 — AI CHAT ROUTE
# This is the new endpoint the chatbot calls.
# The browser sends a POST request with a JSON body
# like: { "message": "What is Pete's MBSE experience?" }
# Flask calls the Claude API and sends back:
# { "response": "Pete is proficient in..." }
# -------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
@limiter.limit('10 per minute')
def chat():
    # Read the JSON body sent by the browser
    data = request.get_json()

    # Make sure we actually received a message
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    user_message = data['message'].strip()

    # Reject empty messages
    if not user_message:
        return jsonify({'error': 'Message was empty'}), 400

    if len(user_message) > MAX_CHAT_MESSAGE_LENGTH:
        return jsonify({
            'error': 'Message is too long. Please keep questions under 1000 characters.'
        }), 400

    try:
        # Build a focused prompt for this question instead of sending every knowledge file.
        # This usually produces cleaner answers because Claude sees fewer competing details.
        knowledge_context = build_knowledge_context(user_message)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(knowledge_context=knowledge_context)

        # Call the Claude API
        # - model: claude-haiku is fast and affordable, perfect for a chatbot
        # - max_tokens: keeps answers short so the chat feels quick and high-impact.
        # - system: our instructions + the most relevant knowledge files for this question
        # - messages: the visitor's actual question plus a style reminder.
        #   This keeps answers polished even when the knowledge base contains resume-style bullets.
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=320,
            system=system_prompt,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        f"Visitor question: {user_message}\n\n"
                        "Answer in polished plain English using only the most impactful details. "
                        "Use 1 to 3 short complete sentences. If the answer has two ideas, split them into two short paragraphs. "
                        "For recruiter or resume questions, end with one brief source and limitation sentence. "
                        "Use no Markdown, no bullets, "
                        "no numbered lists, and no follow-up sales question."
                    )
                }
            ]
        )

        # Extract the text from Claude's response and clean display-only Markdown symbols
        reply = clean_chatbot_reply(response.content[0].text)

        # Send the answer back to the browser as JSON
        return jsonify({'response': reply})

    except Exception as e:
        # If anything goes wrong (network issue, API error, etc.),
        # return a friendly error message instead of crashing
        print(f"Claude API error: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500


# -------------------------------------------------------
# INTERVIEW WORKSPACE — CONCEPT 1 structured coach endpoints
# (2026-07-15). The review endpoint returns a SCHEMA-VALIDATED
# structured review so the browser never renders a malformed or
# partial score. The coach endpoint is the scoped Answer Workshop
# chat (not the general Ask Pete assistant). Both keep the API key
# on the server, exactly like /api/chat.
# -------------------------------------------------------

INTERVIEW_REVIEW_DIMENSIONS = ('relevance', 'structure', 'specificity', 'evidence', 'impact')
INTERVIEW_ANNOTATION_TYPES = ('strong', 'needs-specificity', 'missing-evidence', 'clarity')


def _clamp_score(value):
    """Coerce a model-provided score to an int in 0-100 or raise ValueError."""
    score = int(value)
    if score < 0 or score > 100:
        raise ValueError('score out of range')
    return score


def _strip_md(text):
    """Remove markdown emphasis the model sometimes sneaks into plain text."""
    return re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', str(text)).strip()


def _string_list(value, max_items):
    """Validate a list of non-empty strings, trimmed and capped."""
    if not isinstance(value, list):
        raise ValueError('expected a list')
    items = [_strip_md(item) for item in value if _strip_md(item)]
    return items[:max_items]


def validate_interview_review(raw, answer_length):
    """Validate + normalize the model's review JSON.

    Returns a clean dict the browser can trust, or raises ValueError.
    Invalid annotations are DROPPED (the page then shows a general
    review) — an offset pointing at the wrong text is worse than none.
    """
    if not isinstance(raw, dict):
        raise ValueError('review is not an object')

    review = {
        'overallScore': _clamp_score(raw.get('overallScore')),
        'verdict': _strip_md(raw.get('verdict', ''))[:80],
        'encouragement': _strip_md(raw.get('encouragement', ''))[:300],
        'strengths': _string_list(raw.get('strengths', []), 4),
        'improvements': _string_list(raw.get('improvements', []), 4),
        'improvedAnswer': str(raw.get('improvedAnswer', '')).strip()[:MAX_INTERVIEW_ANSWER_LENGTH],
        'changesExplained': _string_list(raw.get('changesExplained', []), 6),
    }
    if not review['verdict']:
        raise ValueError('verdict missing')

    dimensions = raw.get('dimensions')
    if not isinstance(dimensions, list):
        raise ValueError('dimensions missing')
    clean_dimensions = []
    seen_keys = set()
    for dim in dimensions:
        if not isinstance(dim, dict):
            continue
        key = dim.get('key')
        if key not in INTERVIEW_REVIEW_DIMENSIONS or key in seen_keys:
            continue
        clean_dimensions.append({
            'key': key,
            'score': _clamp_score(dim.get('score')),
            'rationale': _strip_md(dim.get('rationale', ''))[:400],
            'nextAction': _strip_md(dim.get('nextAction', ''))[:300],
        })
        seen_keys.add(key)
    if len(clean_dimensions) != len(INTERVIEW_REVIEW_DIMENSIONS):
        raise ValueError('incomplete dimensions')
    order = {key: i for i, key in enumerate(INTERVIEW_REVIEW_DIMENSIONS)}
    review['dimensions'] = sorted(clean_dimensions, key=lambda d: order[d['key']])

    missing = []
    for item in (raw.get('missingEvidence') or [])[:3]:
        if not isinstance(item, dict):
            continue
        opportunity = _strip_md(item.get('opportunity', ''))
        if not opportunity:
            continue
        missing.append({
            'opportunity': opportunity[:400],
            'suggestedUse': _strip_md(item.get('suggestedUse', ''))[:400],
            'evidenceId': str(item.get('evidenceId', '')).strip()[:60],
        })
    review['missingEvidence'] = missing

    annotations = []
    for i, item in enumerate((raw.get('annotations') or [])[:12]):
        try:
            start = int(item.get('start'))
            end = int(item.get('end'))
            ann_type = item.get('type')
            if ann_type not in INTERVIEW_ANNOTATION_TYPES:
                continue
            if start < 0 or end <= start or end > answer_length:
                continue
            annotations.append({
                'id': 'ann-%d' % i,
                'start': start,
                'end': end,
                'type': ann_type,
                'label': str(item.get('label', '')).strip()[:60],
                'explanation': _strip_md(item.get('explanation', ''))[:300],
            })
        except (TypeError, ValueError, AttributeError):
            continue
    review['annotations'] = annotations

    return review


def _extract_json_object(text):
    """Pull the first JSON object out of a model reply (fences tolerated)."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end <= start:
        raise ValueError('no JSON object in reply')
    return json.loads(cleaned[start:end + 1])


@app.route('/api/interview/review', methods=['POST'])
@limiter.limit('6 per minute')
def interview_review():
    data = request.get_json(silent=True) or {}
    question = str(data.get('question') or '').strip()
    answer = str(data.get('answer') or '').strip()
    level = str(data.get('level') or 'mixed').strip()
    basis = str(data.get('basis') or 'my-history').strip()

    if not question or not answer:
        return jsonify({'error': 'Both the question and your answer are required.'}), 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH:
        return jsonify({'error': 'That question is too long.'}), 400
    if len(answer) > MAX_INTERVIEW_ANSWER_LENGTH:
        return jsonify({'error': 'Please keep answers under 5,000 characters.'}), 400
    if basis not in ('my-history', 'example-candidate'):
        basis = 'my-history'
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'mixed'

    if basis == 'my-history':
        evidence_lines = '\n'.join(
            '- [%s] %s — %s' % (item['id'], item['metric'], item['label'])
            for item in INTERVIEW_SLATE_EVIDENCE
        )
        grounding = (
            'GROUNDING (My History): the ONLY verified evidence you may reference or suggest is listed below. '
            'Never invent metrics, employers, titles, project names, dates, or outcomes. '
            'If no listed evidence fits, say so in the missingEvidence opportunity instead of inventing one.\n'
            + evidence_lines
        )
    else:
        grounding = (
            'GROUNDING (Example Candidate): suggestions may use realistic illustrative examples, '
            'but every invented metric or example must be phrased as clearly illustrative '
            '(for example: "an illustrative metric such as..."). Never imply it is the candidate\'s real history.'
        )

    system_prompt = (
        'You are the PeerSlate interview coach: direct, specific, encouraging. '
        'Praise must cite the actual behavior that earned it; criticism must include a fix; never shame a weak answer. '
        'You score a candidate\'s interview answer against a transparent rubric and respond with JSON ONLY — '
        'no prose before or after, no markdown fences.\n\n'
        'The candidate is practicing at the "%s" experience level. Calibrate rubric expectations and coaching language to that level.\n\n'
        '%s\n\n'
        'Respond with exactly this JSON shape:\n'
        '{"overallScore": <int 0-100>, "verdict": "<short phrase, max 6 words>", '
        '"encouragement": "<1-2 encouraging but honest sentences>", '
        '"dimensions": [{"key": "relevance|structure|specificity|evidence|impact", "score": <int 0-100>, '
        '"rationale": "<plain-language reason for the score>", "nextAction": "<one concrete improvement step>"}] '
        '(exactly these five keys, each once), '
        '"strengths": ["<max 4 short bullets>"], "improvements": ["<max 4 short bullets>"], '
        '"missingEvidence": [{"opportunity": "<what verified evidence would strengthen this and why>", '
        '"suggestedUse": "<a sample sentence the candidate could close with>", "evidenceId": "<id from the list or empty>"}] (max 2), '
        '"annotations": [{"start": <int>, "end": <int>, "type": "strong|needs-specificity|missing-evidence|clarity", '
        '"label": "<2-4 words>", "explanation": "<one short sentence>"}] (max 6, character offsets into the EXACT answer text, non-overlapping), '
        '"improvedAnswer": "<the answer rewritten in the candidate\'s own voice and first person — a credible 60-120 second spoken answer, '
        'no corporate polish. STRICT: build it ONLY from facts already in the submitted answer plus the verified evidence list; '
        'do not add new events, conversations, people, or outcomes. Where a detail is missing, leave a bracketed prompt like '
        '[describe how the team responded] instead of inventing one>", '
        '"changesExplained": ["<max 4 bullets: what changed and why>"]}\n\n'
        'Keep it tight so the JSON never truncates: rationales under 25 words, bullets under 15 words, '
        'improvedAnswer under 160 words. Output must be complete, valid JSON.'
    ) % (level, grounding)

    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2400,
            system=system_prompt,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        'Interview question: "%s"\n\n'
                        'The candidate\'s submitted answer (score THIS exact text; '
                        'annotation offsets are character positions into it):\n%s'
                    ) % (question, answer),
                }
            ],
        )
        raw_reply = response.content[0].text
        review = validate_interview_review(_extract_json_object(raw_reply), len(answer))
        return jsonify({'review': review})
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        # Never render a partial or malformed score as real feedback.
        app.logger.warning('Interview review validation error: %s', e)
        return jsonify({'error': 'The coach returned an unreadable review. Please try again.'}), 502
    except Exception as e:
        app.logger.error('Interview review API error: %s', e)
        return jsonify({'error': 'The coach is unavailable right now. Please try again.'}), 500


@app.route('/api/interview/coach', methods=['POST'])
@limiter.limit('10 per minute')
def interview_coach():
    data = request.get_json(silent=True) or {}
    question = str(data.get('question') or '').strip()[:MAX_INTERVIEW_QUESTION_LENGTH]
    answer = str(data.get('answer') or '').strip()[:MAX_INTERVIEW_ANSWER_LENGTH]
    message = str(data.get('message') or '').strip()
    basis = str(data.get('basis') or 'my-history').strip()
    keep_voice = bool(data.get('keep_voice', True))
    review_summary = str(data.get('review_summary') or '').strip()[:120]

    if not message:
        return jsonify({'error': 'Ask the coach a question first.'}), 400
    if len(message) > 400:
        return jsonify({'error': 'Please keep coach questions under 400 characters.'}), 400
    if not question or not answer:
        return jsonify({'error': 'The coach needs the question and your answer for context.'}), 400

    if basis == 'my-history':
        evidence_lines = '\n'.join(
            '- %s — %s' % (item['metric'], item['label']) for item in INTERVIEW_SLATE_EVIDENCE
        )
        grounding = (
            'You may reference ONLY this verified evidence; never invent metrics, employers, or outcomes:\n'
            + evidence_lines
        )
    else:
        grounding = 'Any example you offer must be phrased as clearly illustrative and fictional.'

    voice_rule = (
        'Preserve the candidate\'s own voice and phrasing; suggest the smallest change that fixes the problem.'
        if keep_voice else
        'You may rephrase more freely, but keep first person and factual ownership.'
    )

    system_prompt = (
        'You are the PeerSlate Interview Coach inside the Answer Workshop — specialized in interview strategy, '
        'scoring, and confidence. You are scoped to ONE question and ONE submitted answer. '
        'Be direct, specific, and encouraging; criticism always comes with a fix. %s\n\n%s\n\n'
        'Context — interview question: "%s"\n'
        'Candidate\'s submitted answer: "%s"\n%s'
    ) % (
        voice_rule,
        grounding,
        question,
        answer,
        ('Coach review verdict: %s' % review_summary) if review_summary else '',
    )

    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            system=system_prompt,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        f'{message}\n\n'
                        'Answer in plain text, no markdown, at most 4 short sentences. '
                        'If you suggest wording, quote the exact sentence to use.'
                    ),
                }
            ],
        )
        return jsonify({'response': _strip_md(clean_chatbot_reply(response.content[0].text))})
    except Exception as e:
        app.logger.error('Interview coach API error: %s', e)
        return jsonify({'error': 'The coach is unavailable right now. Please try again.'}), 500


# -------------------------------------------------------
# FRIENDLY ERROR PAGES
# Without these, a bad URL shows Flask's bare white "Not Found"
# page. These render a small branded page (templates/error.html)
# that keeps the site header/footer and offers a way back home.
# -------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        'error.html',
        error_code=404,
        error_title='Page not found',
        error_message="That address doesn't exist on this site. It may have moved during a redesign, or the link had a typo.",
    ), 404


@app.errorhandler(500)
def server_error(e):
    return render_template(
        'error.html',
        error_code=500,
        error_title='Something went wrong',
        error_message='The server hit an unexpected error building this page. Please try again in a moment.',
    ), 500


# -------------------------------------------------------
# SEARCH-ENGINE BASICS
# robots.txt tells crawlers they're welcome; sitemap.xml lists the
# public pages so search engines find everything. Both are built
# here (not static files) so the sitemap always uses the visitor's
# own host and stays in sync with the routes.
# -------------------------------------------------------

@app.route('/robots.txt')
def robots_txt():
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Sitemap: {request.url_root.rstrip("/")}/sitemap.xml',
    ]
    return app.response_class('\n'.join(lines) + '\n', mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    # The canonical public pages worth indexing (redirect-only and
    # API routes are deliberately left out).
    public_paths = [
        '/', '/experience',
        '/petec/my-story', '/petec/skills', '/petec/resume',
        '/petec/slate-board', '/petec/interview-me', '/petec/about',
        '/petec/hobbies', '/petec/contact',
        '/the-slate', '/the-slate/my-slate', '/the-slate/daily',
        '/the-slate/pulse', '/the-slate/break',
        '/career-search', '/my-network', '/explore-profiles', '/for-recruiters',
    ]
    base = request.url_root.rstrip('/')
    urls = ''.join(f'<url><loc>{base}{path}</loc></url>' for path in public_paths)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    )
    return app.response_class(xml, mimetype='application/xml')


# -------------------------------------------------------
# TEMPORARY LOCAL DATABASE TEST ROUTES
# These prove the Flask-to-Azure-SQL connection and dashboard
# stored procedure. Remove or restrict them before deployment.
# -------------------------------------------------------

@app.route('/api/db-test')
def db_test():
    """Confirm that PeerSlate can connect to Azure SQL."""

    if not app.config['PEERSLATE_ENABLE_DB_TEST_ROUTES']:
        abort(404)

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    DB_NAME() AS database_name,
                    (SELECT COUNT(*) FROM dbo.content_items) AS content_item_count;
                """
            )
            row = cursor.fetchone()

        return jsonify(
            {
                'success': True,
                'message': 'PeerSlate connected to Azure SQL successfully.',
                'database_name': row[0],
                'content_item_count': row[1],
            }
        )

    except Exception as error:
        app.logger.exception('Azure SQL connection test failed.')
        return jsonify(
            {
                'success': False,
                'message': 'PeerSlate could not connect to Azure SQL.',
            }
        ), 500


@app.route('/api/dashboard/test')
def dashboard_test():
    """Load the PeerSlate dashboard for the temporary test user."""

    if not app.config['PEERSLATE_ENABLE_DB_TEST_ROUTES']:
        abort(404)

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'EXEC dbo.usp_GetPeerSlateUserDashboard @UserKey = ?;',
                ('test-user-1',),
            )
            dashboard_sections = fetch_all_result_sets(cursor)

        return jsonify(
            {
                'success': True,
                'user_key': 'test-user-1',
                'section_count': len(dashboard_sections),
                'dashboard_sections': dashboard_sections,
            }
        )

    except Exception as error:
        app.logger.exception('PeerSlate dashboard database test failed.')
        return jsonify(
            {
                'success': False,
                'message': 'The PeerSlate dashboard could not be loaded.',
            }
        ), 500


# --- START THE SERVER ---
if __name__ == '__main__':
    # Use the PORT environment variable when a tool (like the Claude
    # preview) or a hosting platform assigns one, and fall back to the
    # usual 5000 for normal local development. Hosting services like
    # Render/Railway set PORT the same way, so this also prepares the
    # app for public deployment later.
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=port)
