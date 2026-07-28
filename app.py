# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page,
# and handles the AI chatbot API in MVP 1.

import os                                       # Lets us read file paths and environment variables
import glob                                     # Lets us find all files matching a pattern (e.g. all .md files)
import json                                     # Lets us read structured resume content from JSON
import re                                       # Lets us clean Markdown symbols out of chatbot replies
import hashlib                                  # Creates opaque, per-member browser storage scopes
from datetime import datetime, timedelta        # Lets the Slate Feed compute live "2h ago" labels and week ranges
from flask import Flask, render_template, request, jsonify, url_for, redirect, abort  # Added: request (reads incoming data), jsonify (sends JSON back)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import BadData, URLSafeTimedSerializer
from werkzeug.middleware.proxy_fix import ProxyFix
import anthropic                                # The Claude AI client library
from dotenv import load_dotenv                  # Reads our secret API key from the .env file
from db import get_connection, fetch_all_result_sets
from identity import AuthenticationRequired, get_current_identity
from auth_routes import auth
from owner_routes import owner
from control_room_routes import control_room
from peerslate_api import peerslate_api
from people_interests_api import people_interests_api
from overview_projection_service import (
    STYLE_MANIFESTS,
    OverviewProjectionError,
    build_overview_projection,
    build_public_overview_projection,
    list_fixture_options,
    load_fixture_catalog,
)
from scripts.release_identity import load_release_id

# Load the .env file so ANTHROPIC_API_KEY is available to this app.
# This must happen before we create the Anthropic client below.
load_dotenv()


def _configured_trusted_hosts():
    hosts = {
        "localhost",
        "127.0.0.1",
        "[::1]",
        "peerslate.com",
        ".peerslate.com",
    }
    azure_hostname = os.environ.get("WEBSITE_HOSTNAME")
    if azure_hostname:
        hosts.add(azure_hostname.strip().lower())
    configured_hosts = os.environ.get("PEERSLATE_TRUSTED_HOSTS", "")
    hosts.update(
        host.strip().lower()
        for host in configured_hosts.split(",")
        if host.strip()
    )
    return sorted(hosts)

# Keep oversized prompts from consuming API budget or making the chat feel broken.
MAX_CHAT_MESSAGE_LENGTH = 1000

# Interview Studio: request-size guards for the structured coaching
# endpoints. Answers are longer than chat messages by design.
MAX_INTERVIEW_ANSWER_LENGTH = 5000
MAX_INTERVIEW_QUESTION_LENGTH = 300

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        'ANTHROPIC_API_KEY is not set. Add it to your .env file locally or your hosting environment variables in deployment.'
    )

INTERVIEW_CONTEXT_MAX_AGE_SECONDS = 30 * 60
INTERVIEW_CONTEXT_SIGNING_KEY = os.environ.get('INTERVIEW_CONTEXT_SIGNING_KEY') or hashlib.sha256(
    ('peerslate-interview-context-v1:' + ANTHROPIC_API_KEY).encode('utf-8')
).hexdigest()
interview_context_serializer = URLSafeTimedSerializer(
    INTERVIEW_CONTEXT_SIGNING_KEY,
    salt='peerslate-interview-model-answer-v1',
)

# Create the Flask app
app = Flask(__name__)
# Azure terminates HTTPS before forwarding the request to Gunicorn. Trust the
# single platform proxy hop for the original scheme so external URLs, canonical
# tags, and Open Graph metadata stay HTTPS in production while localhost keeps
# its native HTTP scheme.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.config.update(
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    MAX_FORM_MEMORY_SIZE=500 * 1024,
    MAX_FORM_PARTS=100,
    TRUSTED_HOSTS=_configured_trusted_hosts(),
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
    PEERSLATE_OWNER_HOME_ENABLED=(
        os.environ.get('PEERSLATE_OWNER_HOME_ENABLED', 'false').lower() == 'true'
    ),
    # PS-SLATE-STUDIO-SLICE-1-001: keep the protected Studio shell dark until
    # its separate owner enablement decision.  This flag is intentionally
    # independent of Owner Home; it must not change /app or any public route.
    PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED=(
        os.environ.get('PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED', 'false').lower() == 'true'
    ),
    # Backend-only Slice J1: derived private Journal read + one-step Save
    # Moment. Keep off until the visual gate and the proposed migration pass.
    PEERSLATE_JOURNAL_ENABLED=(
        os.environ.get('PEERSLATE_JOURNAL_ENABLED', 'false').lower() == 'true'
    ),
    PEERSLATE_TRUST_EASYAUTH_HEADERS=(
        os.environ.get('PEERSLATE_TRUST_EASYAUTH_HEADERS', 'false').lower() == 'true'
    ),
    PEERSLATE_AUTH_ISSUER=os.environ.get('PEERSLATE_AUTH_ISSUER'),
    PEERSLATE_AUTH_PROVIDER_NAME=os.environ.get(
        'PEERSLATE_AUTH_PROVIDER_NAME', 'aad'
    ),
    PEERSLATE_AUTH_HEADER_MAX_LENGTH=65536,
    # Site-owner allowlist for the owner-only Control Room (owner_authorization
    # .py). Comma/space separated. Values are configured per environment and are
    # never hardcoded here. Empty => the Control Room is inaccessible to everyone
    # (fail-closed). Emails match the server-resolved identity email
    # case-insensitively; user keys match the opaque identity.user_key exactly.
    PEERSLATE_OWNER_EMAILS=os.environ.get('PEERSLATE_OWNER_EMAILS', ''),
    PEERSLATE_OWNER_USER_KEYS=os.environ.get('PEERSLATE_OWNER_USER_KEYS', ''),
    # Control Room Tier 1 (services/azure_devops_read.py): optional, read-only
    # live Azure DevOps sync. All four must be set to activate it; any one
    # missing => the dashboard truthfully reports "not configured". The PAT
    # needs only Code (Read) + Build (Read) scopes and is set by Pete directly
    # in the environment — never requested, read, or handled by an agent.
    PEERSLATE_ADO_ORG_URL=os.environ.get('PEERSLATE_ADO_ORG_URL', ''),
    PEERSLATE_ADO_PROJECT=os.environ.get('PEERSLATE_ADO_PROJECT', ''),
    PEERSLATE_ADO_REPO=os.environ.get('PEERSLATE_ADO_REPO', ''),
    PEERSLATE_ADO_READ_PAT=os.environ.get('PEERSLATE_ADO_READ_PAT', ''),
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
app.register_blueprint(auth)
app.register_blueprint(owner)
app.register_blueprint(control_room)
app.register_blueprint(peerslate_api)
app.register_blueprint(people_interests_api)


@app.get('/healthz')
def healthz():
    """Minimal process-liveness signal for Azure and release smoke checks.

    This endpoint intentionally does not query member data, Azure SQL, Blob
    Storage, identity providers, or AI providers. A dependency readiness check
    belongs in a separately authorized operational package because it can wake
    services, consume quota, or expose infrastructure state.
    """
    response = jsonify(
        service='peerslate',
        status='ok',
        release=load_release_id(),
    )
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.after_request
def prevent_stale_html(response):
    """Always revalidate HTML pages so a design change (like the homepage
    move from peerslate.html to the Experience page) can't stick in a
    visitor's browser cache. Versioned static assets (?v=...) are left
    cacheable — only text/html is marked no-cache."""
    if response.mimetype == 'text/html':
        # Routes may set a stricter policy for private owner-specific HTML.
        # Preserve it; ordinary pages retain the historic default exactly.
        response.headers.setdefault('Cache-Control', 'no-cache, must-revalidate')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Permissions-Policy',
        'camera=(self), microphone=(self), geolocation=()',
    )
    if request.is_secure:
        response.headers.setdefault(
            'Strict-Transport-Security', 'max-age=31536000'
        )
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
        # Interview Studio is a platform product, not a Pete-only profile
        # section. Keeping one route here prevents the global header and
        # search index from rebuilding a profile-scoped /interview-me link.
        'interview_studio_url': url_for('interview_studio'),
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
    '/interview-me': '/interview-studio',
    '/petec/interview-me': '/interview-studio',
    '/petec/interview-studio': '/interview-studio',
    '/atrium': '/',
    '/petec/atrium': '/',
}
LEGACY_INTERVIEW_PATHS = {
    '/interview-me',
    '/petec/interview-me',
    '/petec/interview-studio',
}


def _legacy_interview_redirect_target():
    mode = request.args.get('mode')
    entitlements = get_interview_entitlements()
    mode_enabled = {
        'me': entitlements['written_practice'],
        'ai': entitlements['model_answers'],
        'video': entitlements['video_studio'] != 'disabled',
    }
    if mode in mode_enabled and mode_enabled[mode]:
        return url_for('interview_studio', mode=mode)
    return url_for('interview_studio')


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
        elif request.path in LEGACY_INTERVIEW_PATHS:
            target_path = _legacy_interview_redirect_target()
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
        target = (
            _legacy_interview_redirect_target()
            if request.path in LEGACY_INTERVIEW_PATHS
            else RETIRED_PORTFOLIO_PATHS[request.path]
        )
        return redirect(target, code=302)

    # /skills is a real page again (the Skills profile tab), so it now
    # canonicalizes to /petec/skills like every other portfolio section.
    section_paths = {'/about', '/contact', '/hobbies', '/my-story', '/skills', '/slate-board'}

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

# PS-HOME-STORY-001 (2026-07-16): the homepage is now the three-scene
# overhaul approved by Pete — voice-first hero, Living Résumé scene, and
# the My Story + Future scene — rendered from the SAME data sources as the
# live My Story page and résumé (no second copy of Pete's content). The
# previous cinematic page stays reachable at /experience for comparison
# and one-line rollback; the old marketing page remains at /peerslate.
def _load_home_json(filename):
    path = os.path.join(os.path.dirname(__file__), 'static', 'data', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_home_context():
    """Small, intentional preview view models for the homepage scenes.

    Pulls specific approved cards by id from story_data.json and
    resume_data.json so the homepage can never drift from the live
    My Story and résumé content.
    """
    story = _load_home_json('story_data.json')
    resume = _load_home_json('resume_data.json')

    acts = {act['id']: act for act in story['acts']}

    def story_card(act_id, card_id):
        return next(c for c in acts[act_id]['cards'] if c['id'] == card_id)

    story_preview = {
        'act_index': [
            {'number': act['number'], 'eyebrow': act['eyebrow'],
             'label': act['nav_label']}
            for act in story['acts']
        ],
        'act_one': {
            'image': story_card('act-now', 'now-maui')['image'],
            'purpose': story_card('act-now', 'now-purpose'),
            'currently': story_card('act-now', 'now-currently')['list'],
            'turning': story_card('act-now', 'now-turning'),
        },
        'act_two': {
            'title': acts['act-becoming']['title'],
            'chapters': [
                story_card('act-becoming', cid)
                for cid in ('ch-pizza', 'ch-36', 'ch-airforce', 'ch-industry')
            ],
        },
        'act_three': {
            'polaroids': [
                story_card('act-life', cid)
                for cid in ('life-race', 'life-bali', 'life-hawaii')
            ],
        },
        'act_four': {
            'closing': story_card('act-next', 'next-closing'),
            'focus': story_card('act-next', 'next-focus')['list'],
            'toward': story_card('act-next', 'next-toward'),
        },
    }

    metrics = {m['id']: m for m in resume['metrics']}
    skills = {s['id']: s for s in resume['skills']}
    roles = {r['id']: r for r in resume['career_roles']}
    education = {e['id']: e for e in resume['education']}
    cameo_proof = skills['cameo']['evidence_items'][0]

    resume_preview = {
        'profile': resume['profile'],
        'metrics': [
            metrics[mid] for mid in
            ('engineers-led', 'redesigns', 'contract', 'repair-test',
             'issue-time')
        ],
        'skills': [
            {
                'name': skills[sid]['display_name'],
                'proof_count': len(skills[sid]['evidence_items']),
                'role_count': len({e['role_id'] for e in
                                   skills[sid]['evidence_items']}),
            }
            for sid in ('systems-engineering', 'requirements-management',
                        'mbse')
        ],
        'roles': [roles[rid] for rid in ('northrop', 'l3harris', 'dod')],
        'proof': cameo_proof,
        'credentials': [education['education-pmp'], education['education-ms']],
    }

    return {'story_preview': story_preview, 'resume_preview': resume_preview}


@app.route('/')
def home():
    return render_template('homepage.html', **_build_home_context())

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


# PS-FEED-001 (2026-07-16): the Living Stream Feed prototype from the
# approved Feed Vision Handoff v1. Publicly reachable and linked from real
# navigation (2026-07-16, Pete) — the "Feed Preview" tab on the Community
# board and the header search index both point here. It is still a
# fixture/demo-data design preview, not a production data path: no
# database, no publication, no real auth, no changes to the existing
# Feed/Community board behavior. The page carries a visible preview
# banner so visitors never mistake sample data for real functionality.
@app.route('/feed-living-stream')
def feed_living_stream():
    """The connected Living Stream Feed design preview (mockups 01–16)."""
    return render_template('feed_living_stream.html')


@app.route('/feed-living-stream/states')
def feed_living_stream_states():
    """The page/state map: every mockup state with a deep link into the
    prototype, for review against mockups/production/01–18."""
    return render_template('feed_living_stream_states.html')


@app.route('/_internal/feed-living-stream')
def feed_living_stream_legacy_redirect():
    """The prototype's brief internal-preview address; kept as a redirect
    so any bookmark from its first hour still lands correctly."""
    return redirect(url_for('feed_living_stream'), code=302)


@app.route('/_internal/feed-living-stream/states')
def feed_living_stream_states_legacy_redirect():
    return redirect(url_for('feed_living_stream_states'), code=302)


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
    # Browser-first note storage is always available. When the authenticated
    # database UI is enabled, its local cache receives an opaque per-member
    # scope before the page can read or render any private board state.
    database_feature_enabled = app.config['PEERSLATE_DATABASE_UI_ENABLED']
    database_ui_enabled = False
    storage_scope = 'petec-preview'
    if database_feature_enabled:
        try:
            identity = get_current_identity()
        except AuthenticationRequired:
            storage_scope = 'signed-out'
        else:
            database_ui_enabled = True
            storage_scope = 'member-' + hashlib.sha256(
                str(identity.user_key).encode('utf-8')
            ).hexdigest()[:20]

    return render_template(
        'slate_board.html',
        database_ui_enabled=database_ui_enabled,
        board_storage_scope=storage_scope,
    )


def get_interview_entitlements():
    """Resolve Interview Studio capability labels on the server.

    The public portfolio currently offers written practice and grounded model
    answers. Video remains a local browser rehearsal until authenticated
    storage, retention, and processing services exist.
    """
    video_setting = os.environ.get('INTERVIEW_VIDEO_STUDIO', 'preview').strip().lower()
    history_setting = os.environ.get('INTERVIEW_PROGRESS_HISTORY', 'preview').strip().lower()
    # Preserve the legacy preview/enabled/locked deployment contract while
    # reporting the narrower capabilities this implementation actually has.
    video_studio = 'preview' if video_setting in {'preview', 'enabled'} else 'disabled'
    progress_history = 'browser' if history_setting in {'preview', 'enabled', 'browser'} else 'disabled'

    return {
        'written_practice': True,
        'model_answers': True,
        'mock_interviews': True,
        'video_studio': video_studio,
        'progress_history': progress_history,
    }


def _interview_metric_tag(metric):
    related_skills = set(metric.get('related_skill_ids') or [])
    if related_skills & {
        'project-management', 'contracting', 'control-account-management',
        'leadership', 'people-leadership',
    }:
        return 'Leadership'
    if related_skills & {
        'mbse', 'cameo', 'systems-engineering', 'requirements-management',
        'sysml-modeling', 'software-development', 'ai',
    }:
        return 'Technical'
    return 'Impact'


def _interview_evidence_from_profile(resume_data):
    """Return a small, approved evidence set from one public profile fixture.

    The selected IDs already drive the public Living Resume, so Interview
    Studio never sends the complete profile record or hidden source notes to
    the browser or model.
    """
    living_resume = resume_data.get('living_resume') or {}
    selected_ids = []
    for key in (
        'career_highlight_metric_ids',
        'constellation_evidence_metric_ids',
        'constellation_outcome_metric_ids',
    ):
        for metric_id in living_resume.get(key) or []:
            if metric_id not in selected_ids:
                selected_ids.append(metric_id)

    metrics = {
        item.get('id'): item
        for item in resume_data.get('metrics') or []
        if item.get('id') and item.get('value') and item.get('label')
    }
    evidence = []
    for metric_id in selected_ids:
        metric = metrics.get(metric_id)
        if not metric:
            continue
        evidence.append({
            'id': metric_id,
            'metric': str(metric['value']),
            'label': str(metric['label']),
            'summary': str(metric.get('context') or metric['label']),
            'tag': _interview_metric_tag(metric),
        })
        if len(evidence) == 10:
            break
    return evidence


def _interview_page_context(profile_slug='petec'):
    resume_data = _load_resume_profile(profile_slug)
    profile = dict(resume_data.get('profile') or {})
    profile['role'] = (profile.get('positioning') or 'PeerSlate member').split('|', 1)[0].strip()
    profile['first_name'] = (profile.get('name') or 'Candidate').split()[0]
    return profile, _interview_evidence_from_profile(resume_data)


def _render_interview_studio(initial_view='me'):
    profile, evidence = _interview_page_context('petec')
    entitlements = get_interview_entitlements()
    if initial_view == 'history' and entitlements['progress_history'] == 'disabled':
        return redirect(url_for('interview_studio'), code=302)

    enabled_modes = []
    if entitlements['written_practice']:
        enabled_modes.append('me')
    if entitlements['model_answers']:
        enabled_modes.append('ai')
    if entitlements['video_studio'] != 'disabled':
        enabled_modes.append('video')

    if initial_view != 'history' and not enabled_modes:
        abort(404)

    requested_mode = request.args.get('mode', initial_view)
    if initial_view != 'history' and requested_mode in {'me', 'ai', 'video'} and requested_mode not in enabled_modes:
        fallback_mode = enabled_modes[0]
        target = url_for('interview_studio', mode=fallback_mode) if fallback_mode != 'me' else url_for('interview_studio')
        return redirect(target, code=302)
    if requested_mode not in enabled_modes:
        requested_mode = enabled_modes[0] if enabled_modes else 'me'
    return render_template(
        'interview_studio.html',
        interview_profile=profile,
        interview_evidence=evidence,
        interview_entitlements=entitlements,
        interview_initial_view=initial_view,
        interview_initial_mode=requested_mode,
    )


@app.route('/interview-studio')
def interview_studio():
    return _render_interview_studio('me')


@app.route('/interview-studio/history')
def interview_studio_history():
    return _render_interview_studio('history')


@app.route('/interview-me')
@app.route('/petec/interview-me')
@app.route('/petec/interview-studio')
def interview_me():
    """Keep old bookmarks working without retaining the retired workspace."""
    return redirect(_legacy_interview_redirect_target(), code=302)


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
# inside it. The feed's deeper layers (Progress / Pulse) kept
# their own pages and simply moved under /the-slate/*.
#
# The feed is built to aggregate events from EVERY member's
# slate — each item in static/data/slate_feed.json names its
# author, so when other profiles exist their events join the
# same feed automatically. Today the only profile is Pete's, so
# every card is pulled from his real Slate Board content and
# links back to it.
# -------------------------------------------------------


def _render_community_tabs(initial_tab):
    # PS-COMMUNITY-TABS-001 (2026-07-21, owner supersession): Feed and The
    # Break are the only first-class Community views. Both panels render
    # server-side and JavaScript swaps visibility without a normal-click
    # reload; `initial_tab` selects the bookmarkable Feed or Break route.
    return render_template(
        'the_slate.html',
        initial_tab=initial_tab,
    )


@app.route('/the-slate')
def the_slate():
    # THE SLATE LANDING = Feed (owner decision, 2026-07-21): the People &
    # Interests corkboard that lived here since 2026-07-14 is retired — it
    # overlapped Feed almost completely. Its own template
    # (the_slate_people_interests.html) stays on disk for rollback, matching
    # the site's existing convention for a retired landing view.
    return _render_community_tabs('feed')


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
    # The Break is the second first-class view in the same seamless,
    # two-view Community shell as Feed.
    return _render_community_tabs('break')


@app.route('/the-slate/saved')
def the_slate_saved():
    # Compatibility-only legacy address. Saved is not a Community view and
    # must never render a third panel or destination.
    return redirect(url_for('the_slate'), code=302)


@app.route('/the-slate/people-interests')
def the_slate_people_interests():
    # The board launched at this address (2026-07-13), became The Slate
    # landing the next day, and was retired as the landing on 2026-07-21 in
    # favor of the Feed / The Break Community shell — forward so any
    # shared link keeps working.
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

    public_overview_projection = None
    try:
        public_overview_projection = build_public_overview_projection(resume_data)
    except OverviewProjectionError as exc:
        # A malformed public selection must fail closed to the existing
        # truthful Summary opening. Never partially render a public Overview.
        app.logger.error(
            'Public Overview projection failed for %s: %s',
            profile_slug,
            exc.code,
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
        public_overview_projection=public_overview_projection,
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


@app.route('/_internal/member-overview')
def member_overview_preview():
    """Render the generic Overview foundation for bounded visual review only."""
    preview_enabled = os.environ.get('ENABLE_DESIGN_SYSTEM_PREVIEW') == '1'
    request_host = request.host.lower()
    if request_host.startswith('['):
        clean_host = request_host.split(']', 1)[0].lstrip('[')
    else:
        clean_host = request_host.split(':', 1)[0]
    if clean_host not in {'127.0.0.1', 'localhost', '::1'} and not preview_enabled:
        abort(404)

    submitted_identity_keys = {
        'member',
        'member_id',
        'owner',
        'owner_id',
        'profile',
        'profile_slug',
    }.intersection(request.args)
    if submitted_identity_keys:
        abort(400)

    fixture_id = request.args.get('fixture', 'experienced-leader')
    style_id = request.args.get('style', 'story-career')
    try:
        fixture_catalog = load_fixture_catalog()
        projection = build_overview_projection(
            fixture_catalog,
            fixture_id,
            style_id,
        )
        fixture_options = list_fixture_options(fixture_catalog)
    except OverviewProjectionError as exc:
        if exc.code in {'unknown_fixture', 'unsupported_style'}:
            abort(404)
        abort(400)

    style_options = [
        {'id': manifest['id'], 'label': manifest['label']}
        for manifest in STYLE_MANIFESTS.values()
    ]
    response = app.make_response(
        render_template(
            'overview_preview.html',
            projection=projection,
            fixture_options=fixture_options,
            style_options=style_options,
            capture=request.args.get('capture') == '1',
            large_text=request.args.get('largeText') == '1',
        )
    )
    response.headers['Cache-Control'] = 'no-store'
    return response


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
# INTERVIEW STUDIO — structured coaching endpoints. Every model response is
# validated before the browser sees it. Public profile evidence is selected
# server-side and only minimal approved summaries enter a prompt or response.
# -------------------------------------------------------

INTERVIEW_REVIEW_DIMENSIONS = ('relevance', 'structure', 'specificity', 'evidence', 'impact')
INTERVIEW_STAR_PARTS = ('situation', 'task', 'action', 'result')
INTERVIEW_STAR_STATUSES = ('strong', 'present', 'partial', 'missing')


def _dimension_score(value):
    score = int(value)
    if score < 0 or score > 20:
        raise ValueError('dimension score out of range')
    return score


def _strip_md(text):
    """Remove markdown emphasis the model sometimes sneaks into plain text."""
    return re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', str(text)).strip()


def _string_list(value, max_items):
    """Validate a list of non-empty strings, trimmed and capped."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError('expected a list')
    items = [_strip_md(item) for item in value if _strip_md(item)]
    return items[:max_items]


def validate_interview_review(raw, answer_length=None, allowed_evidence_ids=None):
    """Validate and normalize one transparent, internally consistent review."""
    if not isinstance(raw, dict):
        raise ValueError('review is not an object')

    review = {
        'verdict': _strip_md(raw.get('verdict', ''))[:80],
        'encouragement': _strip_md(raw.get('encouragement', ''))[:300],
        'strengths': _string_list(raw.get('strengths', []), 4),
        'improvements': _string_list(raw.get('improvements', []), 4),
    }
    # Owner decision (2026-07-20): strengths may be empty; improvements may not.
    # "There should never be a blank, but there can be something to encourage to
    # do better."
    #
    # The system prompt sets a MAXIMUM ("max 4 short bullets") and never a
    # minimum, so for a genuinely weak answer zero strengths is the honest
    # result: PeerSlate preserves what the coach actually found rather than
    # pressuring it to manufacture praise, and an empty strengths list renders as
    # a truthful absence instead of being thrown away as a 502.
    #
    # An empty improvements list is different. It is not plausible coaching -- if
    # the coach found no way to improve a weak answer, that indicates a degraded
    # response we should not render. The page's own header promises "what is
    # missing, and the clearest next improvement", so that column is the actual
    # deliverable. Verdict, encouragement, dimensions, STAR, and scores below
    # also remain required.
    if not review['verdict'] or not review['encouragement'] or not review['improvements']:
        raise ValueError('review summary is incomplete')

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
        rationale = _strip_md(dim.get('rationale', ''))[:400]
        next_action = _strip_md(dim.get('nextAction', ''))[:300]
        if not rationale or not next_action:
            raise ValueError('dimension explanation is incomplete')
        clean_dimensions.append({
            'key': key,
            'score': _dimension_score(dim.get('score')),
            'rationale': rationale,
            'nextAction': next_action,
        })
        seen_keys.add(key)
    if len(clean_dimensions) != len(INTERVIEW_REVIEW_DIMENSIONS):
        raise ValueError('incomplete dimensions')
    order = {key: i for i, key in enumerate(INTERVIEW_REVIEW_DIMENSIONS)}
    review['dimensions'] = sorted(clean_dimensions, key=lambda d: order[d['key']])
    # The five dimension scores are the transparent, itemized breakdown the
    # reader actually sees -- each shown with its own rationale and next action --
    # and the coaching prompt already requires overallScore to equal their exact
    # sum. A capable model still slips that arithmetic on a meaningful fraction of
    # otherwise-complete replies: dimensions that are individually valid, but an
    # overall that is off by a point or two. Rejecting the entire review as a 502
    # in that case throws away real, itemized coaching over a display-number
    # mismatch, and it strikes non-deterministically -- the same "passes the clean
    # fixture, fails on real output" failure class recorded twice already in
    # docs/governance/CURRENT_STATE.md. Derive the overall from the parts so the
    # number in the ring always equals the breakdown beneath it, rather than
    # discarding the review. The individual scores remain clamped to 0-20 and all
    # five dimensions are still required, so the healed total stays within 0-100.
    review['overallScore'] = sum(item['score'] for item in review['dimensions'])

    star = raw.get('star')
    if not isinstance(star, dict):
        raise ValueError('STAR assessment missing')
    clean_star = {}
    for part in INTERVIEW_STAR_PARTS:
        item = star.get(part)
        if not isinstance(item, dict) or item.get('status') not in INTERVIEW_STAR_STATUSES:
            raise ValueError('invalid STAR assessment')
        reason = _strip_md(item.get('reason', ''))[:240]
        if not reason:
            raise ValueError('STAR reason missing')
        clean_star[part] = {'status': item['status'], 'reason': reason}
    review['star'] = clean_star

    allowed_ids = set(allowed_evidence_ids or [])
    suggestions = []
    for item in (raw.get('evidenceSuggestions') or [])[:2]:
        if not isinstance(item, dict):
            continue
        opportunity = _strip_md(item.get('opportunity', ''))
        suggested_use = _strip_md(item.get('suggestedUse', ''))
        if not opportunity or not suggested_use:
            continue
        evidence_id = str(item.get('evidenceId', '')).strip()[:80]
        if not evidence_id:
            continue
        if evidence_id not in allowed_ids:
            raise ValueError('review referenced unauthorized evidence')
        suggestions.append({
            'opportunity': opportunity[:400],
            'suggestedUse': suggested_use[:400],
            'evidenceId': evidence_id,
        })
    review['evidenceSuggestions'] = suggestions

    return review


def validate_interview_model_answer(raw, evidence_by_id, require_evidence=True):
    """Validate one model answer.

    Two legitimately different kinds of answer arrive here.

    A *grounded* answer (member_history) speaks as the profile owner and must
    cite at least one approved evidence id, so `require_evidence` stays True.

    An *illustrative* answer (best_practice) is a deliberately generic example
    that is not anyone's real history. Its own system prompt instructs the model
    to return `"evidenceIds": []`, so zero citations is the correct result, not
    a validation failure. Callers pass `require_evidence=False` together with an
    empty evidence map: the unauthorized-evidence check below therefore still
    rejects an illustrative answer that tries to cite anything at all.
    """
    if not isinstance(raw, dict):
        raise ValueError('model answer is not an object')
    status = str(raw.get('status') or '').strip().lower()
    if status == 'insufficient':
        return {
            'status': 'insufficient',
            'answer': 'PeerSlate does not have enough approved profile evidence to answer this question without guessing.',
            'whyItWorks': ['Avoids unsupported claims and makes the evidence gap explicit.'],
            'evidenceUsed': [],
        }
    if status != 'answered':
        raise ValueError('model answer status is invalid')
    answer = str(raw.get('answer') or '').strip()[:MAX_INTERVIEW_ANSWER_LENGTH]
    why = _string_list(raw.get('whyItWorks', []), 4)
    raw_evidence_ids = raw.get('evidenceIds') or []
    if not isinstance(raw_evidence_ids, list):
        raise ValueError('model answer evidence is not a list')
    evidence_ids = [str(item) for item in raw_evidence_ids]
    if not answer or not why:
        raise ValueError('model answer is incomplete')
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError('duplicate evidence references')
    if require_evidence and not evidence_ids:
        raise ValueError('model answer has no approved evidence references')
    if any(item not in evidence_by_id for item in evidence_ids):
        raise ValueError('model answer referenced unauthorized evidence')
    return {
        'status': 'answered',
        'answer': answer,
        'whyItWorks': why,
        'evidenceUsed': [evidence_by_id[item] for item in evidence_ids],
    }


def _sign_interview_model_context(profile_slug, question, level, family, model_answer):
    return interview_context_serializer.dumps({
        'profile_slug': profile_slug,
        'question': question,
        'level': level,
        'family': family,
        'answer': model_answer['answer'],
        'evidence_ids': [item['id'] for item in model_answer['evidenceUsed']],
    })


def _load_interview_model_context(token):
    if not isinstance(token, str) or not token or len(token) > 12000:
        raise ValueError('model-answer context token is invalid')
    try:
        context = interview_context_serializer.loads(
            token,
            max_age=INTERVIEW_CONTEXT_MAX_AGE_SECONDS,
        )
    except BadData as error:
        raise ValueError('model-answer context token is invalid or expired') from error
    if not isinstance(context, dict):
        raise ValueError('model-answer context is invalid')
    required_text = ('profile_slug', 'question', 'level', 'family', 'answer')
    if any(not isinstance(context.get(key), str) or not context[key] for key in required_text):
        raise ValueError('model-answer context is incomplete')
    evidence_ids = context.get('evidence_ids')
    if not isinstance(evidence_ids, list) or any(not isinstance(item, str) for item in evidence_ids):
        raise ValueError('model-answer context evidence is invalid')
    if len(context['question']) > MAX_INTERVIEW_QUESTION_LENGTH or len(context['answer']) > MAX_INTERVIEW_ANSWER_LENGTH:
        raise ValueError('model-answer context is too long')
    return context


def validate_interview_improvement(raw, evidence_by_id):
    if not isinstance(raw, dict):
        raise ValueError('improvement is not an object')
    draft = str(raw.get('draft') or '').strip()[:MAX_INTERVIEW_ANSWER_LENGTH]
    changes = _string_list(raw.get('changes', []), 4)
    raw_evidence_ids = raw.get('evidenceIds') or []
    if not isinstance(raw_evidence_ids, list) or any(not isinstance(item, str) for item in raw_evidence_ids):
        raise ValueError('improvement evidence is not a list')
    evidence_ids = raw_evidence_ids
    if not draft or not changes:
        raise ValueError('improvement is incomplete')
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError('duplicate evidence references')
    if any(item not in evidence_by_id for item in evidence_ids):
        raise ValueError('improvement referenced unauthorized evidence')
    return {
        'draft': draft,
        'changes': changes,
        'evidenceUsed': [evidence_by_id[item] for item in evidence_ids],
    }


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


# -------------------------------------------------------
# Coaching failure diagnostics.
#
# The interview AI routes reject any model reply they cannot fully validate and
# return 502 rather than render partial or invented coaching. That behavior is
# correct and is deliberately unchanged here. The problem is that roughly a
# dozen genuinely different provider outcomes -- a reply truncated mid-JSON, a
# reply missing its verdict, dimension scores that do not add
# up to the stated overall score -- all collapse into one log line and one
# status code, so the observed failure rate cannot be attributed to a cause.
#
# These labels are low-cardinality and stable so logs can be grouped by cause.
# They never carry candidate answer text or model output text.
# -------------------------------------------------------

INTERVIEW_FAILURE_REASONS = {
    'no JSON object in reply': 'no_json_object',
    'review is not an object': 'not_an_object',
    'model answer is not an object': 'not_an_object',
    'improvement is not an object': 'not_an_object',
    'expected a list': 'wrong_field_type',
    'model answer evidence is not a list': 'wrong_field_type',
    'improvement evidence is not a list': 'wrong_field_type',
    'review summary is incomplete': 'empty_required_field',
    'model answer is incomplete': 'empty_required_field',
    'improvement is incomplete': 'empty_required_field',
    'dimensions missing': 'incomplete_dimensions',
    'incomplete dimensions': 'incomplete_dimensions',
    'dimension explanation is incomplete': 'incomplete_dimensions',
    'dimension score out of range': 'score_out_of_range',
    'STAR assessment missing': 'invalid_star',
    'invalid STAR assessment': 'invalid_star',
    'STAR reason missing': 'invalid_star',
    'review referenced unauthorized evidence': 'unauthorized_evidence',
    'model answer referenced unauthorized evidence': 'unauthorized_evidence',
    'improvement referenced unauthorized evidence': 'unauthorized_evidence',
    'model answer has no approved evidence references': 'no_evidence_reference',
    'duplicate evidence references': 'duplicate_evidence',
    'model answer status is invalid': 'invalid_status',
}

INTERVIEW_UNCLASSIFIED_REASON = 'unclassified'


def _interview_failure_reason(error):
    """Map one rejected model reply to a stable, low-cardinality cause label."""
    if isinstance(error, json.JSONDecodeError):
        return 'unparseable_json'
    if isinstance(error, (KeyError, TypeError)):
        return 'unexpected_shape'
    return INTERVIEW_FAILURE_REASONS.get(str(error), INTERVIEW_UNCLASSIFIED_REASON)


def _log_interview_failure(label, error, stop_reason, reply_length):
    """Record why a model reply was rejected, without logging its content.

    `reply_length` is a character count only. Candidate answers and model text
    never enter the log line.
    """
    app.logger.warning(
        '%s: reason=%s error_class=%s provider_stop_reason=%s reply_chars=%d detail=%s',
        label,
        _interview_failure_reason(error),
        type(error).__name__,
        stop_reason or 'unknown',
        reply_length,
        error,
    )


@app.route('/api/interview/review', methods=['POST'])
@limiter.limit('6 per minute')
def interview_review():
    if not get_interview_entitlements().get('written_practice'):
        return jsonify({'error': 'Interview coaching is not available for this profile.'}), 403
    if not request.is_json:
        return jsonify({'error': 'Send interview requests as JSON.'}), 415
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403
    origin = request.headers.get('Origin')
    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Send one JSON object for the interview request.'}), 400
    question = str(data.get('question') or '').strip()
    answer = str(data.get('answer') or '').strip()
    level = str(data.get('level') or 'experienced').strip()
    family = str(data.get('family') or 'behavioral').strip()
    competency = str(data.get('competency') or 'Communication').strip()[:80]
    profile_slug = str(data.get('profile_slug') or 'petec').strip()

    if not question or not answer:
        return jsonify({'error': 'Both the question and your answer are required.'}), 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH:
        return jsonify({'error': 'That question is too long.'}), 400
    if len(answer) > MAX_INTERVIEW_ANSWER_LENGTH:
        return jsonify({'error': 'Please keep answers under 5,000 characters.'}), 400
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'experienced'
    if family not in ('situational', 'behavioral', 'mixed'):
        family = 'behavioral'
    if profile_slug not in RESUME_PROFILE_FILES:
        return jsonify({'error': 'That interview profile is unavailable.'}), 404

    profile, evidence = _interview_page_context(profile_slug)
    evidence_by_id = {item['id']: item for item in evidence}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in evidence
    ) or '- No approved public evidence is available.'
    grounding = (
        'APPROVED PUBLIC PROFILE EVIDENCE: the ONLY evidence you may suggest is listed below. '
        'Never invent metrics, employers, titles, projects, dates, duties, or outcomes. '
        'If nothing fits, return no evidence suggestions.\n' + evidence_lines
    )

    system_prompt = (
        'You are the PeerSlate interview coach: direct, specific, encouraging. '
        'Praise must cite the actual behavior that earned it; criticism must include a fix; never shame a weak answer. '
        'You score a candidate\'s interview answer against a transparent rubric and respond with JSON ONLY — '
        'no prose before or after, no markdown fences.\n\n'
        'The candidate is practicing at the "%s" experience level. The question family is "%s" and the explicit '
        'competency is "%s". Calibrate the review to that context.\n\n'
        '%s\n\n'
        'Respond with exactly this JSON shape:\n'
        '{"overallScore": <int 0-100>, "verdict": "<short phrase, max 6 words>", '
        '"encouragement": "<1-2 encouraging but honest sentences>", '
        '"dimensions": [{"key": "relevance|structure|specificity|evidence|impact", "score": <int 0-20>, '
        '"rationale": "<plain-language reason for the score>", "nextAction": "<one concrete improvement step>"}] '
        '(exactly these five keys, each once), '
        '"star": {"situation": {"status": "strong|present|partial|missing", "reason": "<why>"}, '
        '"task": {"status": "strong|present|partial|missing", "reason": "<why>"}, '
        '"action": {"status": "strong|present|partial|missing", "reason": "<why>"}, '
        '"result": {"status": "strong|present|partial|missing", "reason": "<why>"}}, '
        '"strengths": ["<max 4 short bullets>"], "improvements": ["<max 4 short bullets>"], '
        '"evidenceSuggestions": [{"opportunity": "<why this approved evidence could strengthen a future draft>", '
        '"suggestedUse": "<a truthful way to connect it, without claiming it is already in the answer>", '
        '"evidenceId": "<exact id from the list>"}] (max 2)}.\n\n'
        'Each dimension is worth 20 points and overallScore MUST equal the exact sum of the five dimension scores. '
        'Keep rationales under 25 words and bullets under 15 words. Output complete, valid JSON.'
    ) % (level, family, competency, grounding)

    raw_reply = ''
    stop_reason = ''
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
                        'The candidate\'s submitted answer (score this exact text):\n%s'
                    ) % (question, answer),
                }
            ],
        )
        stop_reason = getattr(response, 'stop_reason', '') or ''
        raw_reply = response.content[0].text
        review = validate_interview_review(
            _extract_json_object(raw_reply),
            len(answer),
            allowed_evidence_ids=evidence_by_id,
        )
        return jsonify({'review': review})
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        # Never render a partial or malformed score as real feedback.
        _log_interview_failure(
            'Interview review validation error', e, stop_reason, len(raw_reply),
        )
        return jsonify({'error': 'The coach returned an unreadable review. Please try again.'}), 502
    except Exception as e:
        app.logger.error('Interview review API error: %s', e)
        return jsonify({'error': 'The coach is unavailable right now. Please try again.'}), 500


@app.route('/api/interview/improve', methods=['POST'])
@limiter.limit('6 per minute')
def interview_improve():
    if not get_interview_entitlements().get('written_practice'):
        return jsonify({'error': 'Interview coaching is not available for this profile.'}), 403
    if not request.is_json:
        return jsonify({'error': 'Send interview requests as JSON.'}), 415
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403
    origin = request.headers.get('Origin')
    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Send one JSON object for the interview request.'}), 400
    raw_improvements = data.get('improvements') or []
    raw_evidence_ids = data.get('evidence_ids') or []
    if (
        not isinstance(raw_improvements, list)
        or any(not isinstance(item, str) for item in raw_improvements)
        or not isinstance(raw_evidence_ids, list)
        or any(not isinstance(item, str) for item in raw_evidence_ids)
    ):
        return jsonify({'error': 'Improvements and evidence IDs must be JSON lists of text values.'}), 400
    question = str(data.get('question') or '').strip()
    answer = str(data.get('answer') or '').strip()
    profile_slug = str(data.get('profile_slug') or 'petec').strip()
    improvements = _string_list(raw_improvements, 4)
    selected_ids = raw_evidence_ids[:2]

    if not question or not answer:
        return jsonify({'error': 'The question and submitted answer are required.'}), 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH or len(answer) > MAX_INTERVIEW_ANSWER_LENGTH:
        return jsonify({'error': 'That interview content is too long.'}), 400
    if profile_slug not in RESUME_PROFILE_FILES:
        return jsonify({'error': 'That interview profile is unavailable.'}), 404

    _profile, evidence = _interview_page_context(profile_slug)
    all_evidence = {item['id']: item for item in evidence}
    if len(selected_ids) != len(set(selected_ids)) or any(item not in all_evidence for item in selected_ids):
        return jsonify({'error': 'One of those evidence suggestions is unavailable.'}), 403
    selected_evidence = {item: all_evidence[item] for item in selected_ids}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in selected_evidence.values()
    ) or '- No additional evidence was selected. Use only facts already present in the answer.'

    system_prompt = (
        'You are the PeerSlate Interview Coach. Rewrite a submitted answer as an editable draft while preserving '
        'the candidate\'s first-person voice. You may use ONLY facts already in the answer and the explicitly selected '
        'approved evidence below. Never invent metrics, roles, employers, actions, dates, technologies, conversations, '
        'or outcomes. If a needed fact is absent, omit it or add a short bracketed prompt for the candidate to confirm. '
        'Respond with JSON only: {"draft":"<60-120 second spoken answer>", '
        '"changes":["<max 4 concrete changes>"], "evidenceIds":["<only selected ids actually used>"]}.\n\n'
        'Selected evidence:\n%s'
    ) % evidence_lines
    improvement_notes = '\n'.join('- ' + item for item in improvements) or '- Make the answer clearer and more specific.'

    raw_reply = ''
    stop_reason = ''
    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1300,
            system=system_prompt,
            messages=[{
                'role': 'user',
                'content': (
                    'Question: %s\n\nSubmitted answer:\n%s\n\nCoach priorities:\n%s'
                ) % (question, answer, improvement_notes),
            }],
        )
        stop_reason = getattr(response, 'stop_reason', '') or ''
        raw_reply = response.content[0].text
        improvement = validate_interview_improvement(
            _extract_json_object(raw_reply),
            selected_evidence,
        )
        return jsonify({'improvement': improvement})
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        _log_interview_failure(
            'Interview improvement validation error', error, stop_reason, len(raw_reply),
        )
        return jsonify({'error': 'The coach returned an unreadable draft. Please try again.'}), 502
    except Exception as error:
        app.logger.error('Interview improvement API error: %s', error)
        return jsonify({'error': 'The coach is unavailable right now. Please try again.'}), 500


@app.route('/api/interview/model-answer', methods=['POST'])
@limiter.limit('6 per minute')
def interview_model_answer():
    if not get_interview_entitlements().get('model_answers'):
        return jsonify({'error': 'Interview AI is not available for this profile.'}), 403
    if not request.is_json:
        return jsonify({'error': 'Send interview requests as JSON.'}), 415
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403
    origin = request.headers.get('Origin')
    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
        return jsonify({'error': 'Cross-site interview requests are not allowed.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Send one JSON object for the interview request.'}), 400
    question = str(data.get('question') or '').strip()
    profile_slug = str(data.get('profile_slug') or 'petec').strip()
    level = str(data.get('level') or 'experienced').strip()
    family = str(data.get('family') or 'behavioral').strip()
    follow_up = str(data.get('follow_up') or '').strip()
    prior_answer = ''

    if follow_up:
        try:
            context = _load_interview_model_context(data.get('context_token'))
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
        profile_slug = context['profile_slug']
        question = context['question']
        level = context['level']
        family = context['family']
        prior_answer = context['answer']

    if not question:
        return jsonify({'error': 'Ask an interview question first.'}), 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH or len(follow_up) > MAX_INTERVIEW_QUESTION_LENGTH:
        return jsonify({'error': 'That interview question is too long.'}), 400
    if profile_slug not in RESUME_PROFILE_FILES:
        return jsonify({'error': 'That interview profile is unavailable.'}), 404
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'experienced'
    if family not in ('situational', 'behavioral', 'mixed'):
        family = 'behavioral'
    # PS-INTERVIEW-002 (v1.2): explicit grounding modes. member_history is
    # the original behavior; best_practice is a clearly generic example;
    # compare returns both so the member can study the structural lessons.
    mode = str(data.get('mode') or 'member_history').strip()
    if mode not in ('member_history', 'best_practice', 'compare'):
        mode = 'member_history'

    profile, evidence = _interview_page_context(profile_slug)
    evidence_by_id = {item['id']: item for item in evidence}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in evidence
    ) or '- No approved public evidence is available.'
    system_prompt = (
        'You are generating an evidence-grounded interview model answer for the selected PeerSlate profile. '
        'Write naturally in first person at the %s experience level for a %s question. Use ONLY approved evidence '
        'below. Never invent accomplishments, metrics, duties, employers, dates, technologies, or outcomes. '
        'If evidence is insufficient, do not attempt an answer. Do not award a score. '
        'Respond with JSON only. For an answer use '
        '{"status":"answered", "answer":"<natural 60-120 second answer>", '
        '"whyItWorks":["<2-4 concise factors>"], "evidenceIds":["<ids actually used>"]}. '
        'When the approved evidence cannot support the question, use '
        '{"status":"insufficient", "answer":"", "whyItWorks":[], "evidenceIds":[]}.\n\n'
        'Approved evidence:\n%s'
    ) % (level, family, evidence_lines)
    best_practice_system = (
        'You are writing a GENERIC best-practice interview example answer for a %s-level %s question. '
        'This is an illustrative example only — it is NOT the history of any real person and must never '
        'read as a specific verifiable career claim. Use a clearly generic scenario (for example "a '
        'cross-functional project at a previous employer") with no real company names, no invented '
        'precise metrics presented as fact, and no references to the PeerSlate profile. '
        'Show strong structure (situation, task, action, result, reflection). Do not award a score. '
        'Respond with JSON only: {"status":"answered", "answer":"<natural 60-120 second example>", '
        '"whyItWorks":["<2-4 structural lessons this example demonstrates>"], "evidenceIds":[]}.'
    ) % (level, family)

    # Holds the most recent provider reply so a rejection can be attributed to a
    # cause. Only the stop reason and a character count are ever logged.
    last_reply = {'text': '', 'stop_reason': ''}

    def _generate(system_text, illustrative=False):
        # An illustrative best-practice example is not grounded in this member's
        # approved evidence, so it is validated against an empty evidence map
        # and is not required to cite anything. It is still rejected if it cites
        # an id, because nothing is authorized for a generic example.
        api_response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1300,
            system=system_text,
            messages=[{'role': 'user', 'content': user_content}],
        )
        last_reply['stop_reason'] = getattr(api_response, 'stop_reason', '') or ''
        last_reply['text'] = api_response.content[0].text
        return validate_interview_model_answer(
            _extract_json_object(last_reply['text']),
            {} if illustrative else evidence_by_id,
            require_evidence=not illustrative,
        )

    user_content = 'Interview question: %s' % question
    if follow_up:
        user_content += '\n\nPrior server-validated model answer:\n%s\n\nInterviewer follow-up: %s' % (
            prior_answer,
            follow_up,
        )

    try:
        best_practice_answer = None
        if mode == 'best_practice':
            model_answer = _generate(best_practice_system, illustrative=True)
            model_answer['generic'] = True
        elif mode == 'compare':
            model_answer = _generate(system_prompt)
            best_practice_answer = _generate(best_practice_system, illustrative=True)
            best_practice_answer['generic'] = True
        else:
            model_answer = _generate(system_prompt)
        context_token = _sign_interview_model_context(
            profile_slug,
            question,
            level,
            family,
            model_answer,
        )
        payload = {
            'mode': mode,
            'modelAnswer': model_answer,
            'contextToken': context_token,
            'profile': {
                'displayName': profile.get('name') or 'Candidate',
                'firstName': profile.get('first_name') or 'Candidate',
            },
        }
        if best_practice_answer is not None:
            payload['bestPractice'] = best_practice_answer
        return jsonify(payload)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        _log_interview_failure(
            'Interview model-answer validation error',
            error,
            last_reply['stop_reason'],
            len(last_reply['text']),
        )
        return jsonify({'error': 'The answer could not be validated against the profile evidence. Please try again.'}), 502
    except Exception as error:
        app.logger.error('Interview model-answer API error: %s', error)
        return jsonify({'error': 'Interview AI is unavailable right now. Please try again.'}), 500


@app.route('/api/interview/coach', methods=['POST'])
@limiter.limit('10 per minute')
def interview_coach():
    return jsonify({
        'error': 'This legacy coach endpoint has retired. Use the Interview Studio review and improve actions.'
    }), 410


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
        '/petec/slate-board', '/interview-studio', '/peerslate', '/petec/about',
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
