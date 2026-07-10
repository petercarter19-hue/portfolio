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
import anthropic                                # The Claude AI client library
from dotenv import load_dotenv                  # Reads our secret API key from the .env file

# Load the .env file so ANTHROPIC_API_KEY is available to this app.
# This must happen before we create the Anthropic client below.
load_dotenv()

# Keep oversized prompts from consuming API budget or making the chat feel broken.
MAX_CHAT_MESSAGE_LENGTH = 1000

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        'ANTHROPIC_API_KEY is not set. Add it to your .env file locally or your hosting environment variables in deployment.'
    )

# Create the Flask app
app = Flask(__name__)

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


# -------------------------------------------------------
# SHARED NAVIGATION LINKS
# @app.context_processor means Flask runs this function before
# rendering ANY template, and every key in the dict it returns
# (like portfolio_work_url) becomes a variable every template can
# use directly - that's how base.html can write things like
# {{ portfolio_work_url }} without each route passing it in by hand.
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

    # Builds a full portfolio link by joining the base URL above with a
    # page name, e.g. portfolio_url('work') -> "/petec/work".
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
        'peerslate_home_url': url_for('home'),
        'portfolio_home_url': portfolio_url(),
        'portfolio_work_url': portfolio_url('work'),
        'portfolio_skills_url': portfolio_url('skills'),
        'portfolio_story_url': portfolio_url('my-story'),
        'portfolio_resume_url': portfolio_url('resume'),
        'portfolio_contact_url': portfolio_url('contact'),
        'portfolio_hobbies_url': portfolio_url('hobbies'),
        'is_portfolio_path': request.path == '/petec' or request.path.startswith('/petec/'),
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
        target_path = request.path
        if target_path == '/':
            target_path = '/petec'
        elif not target_path.startswith('/petec'):
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
    old_portfolio_paths = {'/pete', '/portfolio'}
    # /skills is a real page again (the Skills profile tab), so it now
    # canonicalizes to /petec/skills like every other portfolio section.
    section_paths = {'/about', '/contact', '/hobbies', '/interview-me', '/my-story', '/resume', '/skills', '/slate-board', '/work'}

    if request.path in old_portfolio_paths:
        return redirect('/petec', code=302)

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

# The root URL ("/") is the separate PeerSlate marketing homepage,
# not Pete's personal portfolio - see templates/peerslate.html.
@app.route('/')
def home():
    return render_template('peerslate.html')

# Three URLs, one page: /petec is the current address, while /portfolio
# and /pete are kept working as older addresses so no existing link breaks.
@app.route('/petec')
@app.route('/portfolio')
@app.route('/pete')
def portfolio_home():
    return render_template('index.html')

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
    # The My Story page replaced "About" in the navigation.
    # The URL uses a hyphen (/my-story) because URLs can't have spaces,
    # while the Python function name uses an underscore (my_story).
    return render_template('my_story.html')

@app.route('/work')
@app.route('/petec/work')
def work():
    return render_template('work.html')

@app.route('/slate-board')
@app.route('/petec/slate-board')
def slate_board():
    # "My Slate Board" - Pete's goals, progress, badges, and shareable
    # wins/thoughts. MVP is a fully designed static preview: the entries,
    # goal percentages, and badges live in the template as sample content.
    # A future pass adds real storage plus the draft/private/public flow.
    return render_template('slate_board.html')


@app.route('/interview-me')
@app.route('/petec/interview-me')
def interview_me():
    # "Interview Me" - interview prep powered by the candidate's slate.
    # The mock-interview coach calls the SAME /api/chat endpoint as every
    # other Ask Pete AI feature for now, so answers are grounded in Pete's
    # knowledge files. The 30 STAR + 30 behavioral questions live in the
    # template; static/js/interview.js runs the console.
    return render_template('interview_me.html')


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
    # Tab 1 — Slate Feed, with the People layer active (the layer that
    # best shows the PeerSlate idea: people connected by public goals).
    return render_template('the_slate_feed.html')


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
    return render_template('the_slate_daily.html')


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
    return render_template('slate_break.html')


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

def _render_living_resume(is_internal_preview=False):
    """Build the public résumé and gated preview from one shared data model."""
    resume_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'resume_data.json')
    with open(resume_path, 'r', encoding='utf-8') as resume_file:
        resume_data = json.load(resume_file)

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
    resume_degrees = [
        item for item in resume_data['education'] if item['id'] in degree_ids
    ]
    resume_development = [
        item for item in resume_data['education'] if item['id'] not in degree_ids
    ]
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

    return render_template(
        'living_resume_v2.html',
        resume=resume_data,
        living_resume=living_resume,
        ledger_events=ledger_events,
        constellation_events=constellation_events,
        career_highlight_metrics=career_highlight_metrics,
        career_highlight_skills=career_highlight_skills,
        constellation_skills=constellation_skills,
        constellation_evidence_metrics=constellation_evidence_metrics,
        constellation_outcome_metrics=constellation_outcome_metrics,
        resume_experience=resume_experience,
        resume_degrees=resume_degrees,
        resume_development=resume_development,
        featured_resume_skills=featured_resume_skills,
        skill_lookup=skill_by_id,
        is_internal_preview=is_internal_preview,
    )


@app.route('/resume')
@app.route('/petec/resume')
def resume():
    return _render_living_resume()


@app.route('/_internal/living-resume-v2')
def living_resume_v2():
    """Local-first review route for the same public Living Résumé render."""
    preview_enabled = os.environ.get('ENABLE_DESIGN_SYSTEM_PREVIEW') == '1'
    clean_host = request.host.split(':', 1)[0].lower().strip('[]')
    if clean_host not in {'127.0.0.1', 'localhost', '::1'} and not preview_enabled:
        abort(404)

    return _render_living_resume(is_internal_preview=True)


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
        '/', '/petec', '/experience',
        '/petec/my-story', '/petec/work', '/petec/skills', '/petec/resume',
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
