# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page,
# and handles the AI chatbot API in MVP 1.

import os                                       # Lets us read file paths and environment variables
import glob                                     # Lets us find all files matching a pattern (e.g. all .md files)
import json                                     # Lets us read structured resume content from JSON
import re                                       # Lets us clean Markdown symbols out of chatbot replies
from flask import Flask, render_template, request, jsonify, url_for, redirect  # Added: request (reads incoming data), jsonify (sends JSON back)
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
    is_local = clean_host in {'127.0.0.1', 'localhost'}
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
        'is_platform_site': is_platform,
        'portfolio_url': portfolio_url,
        'peerslate_home_url': url_for('home') if is_local or is_platform else 'https://peerslate.com/',
        'portfolio_home_url': portfolio_url(),
        'portfolio_work_url': portfolio_url('work'),
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
    section_paths = {'/about', '/contact', '/hobbies', '/my-story', '/resume', '/work'}

    if request.path in old_portfolio_paths:
        return redirect('/petec', code=302)

    if request.path == '/skills':
        return redirect('/petec/resume', code=302)

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
- For recruiter or resume questions, make the answer evidence-grounded. Give the answer first, then include a short source sentence such as "This is based on Pete's approved resume and career-history sources." Add a short limitation when the approved sources do not fully answer the question.

RESPONSE STYLE:
- Write in complete, polished sentences suitable for a professional portfolio website.
- Answer the visitor's question directly in the first sentence.
- Prioritize the most impressive or decision-useful information instead of listing every detail.
- Use a second short paragraph when the answer needs more than one idea.
- Do not copy raw resume bullets or fragments from the knowledge base.
- Do not end with salesy follow-up questions like "Would you like to know more?"
- If the question asks for a count, give the count first, then briefly explain it.
- Do not mention specific program names, customer names, contract numbers, internal system names, or employer-sensitive details, even if they appear in the knowledge base. Generalize them as "a major defense program," "a navigation-system redesign," or "approved career-history sources."

APPROVED TOPICS:
- Pete's job titles and general responsibilities
- Tools and technologies (Cameo, DOORS, Jira, Python, Flask, Claude API, etc.)
- Education, certifications (PMP, Ph.D. program), and accomplishments
- Career goals and target roles
- This portfolio website and the projects it showcases
- General location (Athens, Alabama)
- The fact that Pete holds an active U.S. Secret security clearance
- Pete's public hobbies (smart home, technology)

TOPICS TO NEVER DISCUSS:
- Classified information of any kind
- Specific program names, contract numbers, or customer names
- Internal system names, network details, or security architecture
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

@app.route('/skills')
@app.route('/petec/skills')
def skills():
    return redirect('/petec/resume', code=302)

@app.route('/hobbies')
@app.route('/petec/hobbies')
def hobbies():
    return render_template('hobbies.html')

@app.route('/contact')
@app.route('/petec/contact')
def contact():
    return render_template('contact.html')

@app.route('/resume')
@app.route('/petec/resume')
def resume():
    # Resume content lives in JSON so Pete can update words and metrics
    # later without digging through a large HTML template.
    resume_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'resume_data.json')

    with open(resume_path, 'r', encoding='utf-8') as f:
        resume_data = json.load(f)

    return render_template('resume.html', resume=resume_data)


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
                        "Do not name specific programs, customers, contract numbers, or internal systems; generalize those details. "
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
