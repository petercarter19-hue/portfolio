# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page,
# and handles the AI chatbot API in MVP 1.

import os                                       # Lets us read file paths and environment variables
import glob                                     # Lets us find all files matching a pattern (e.g. all .md files)
import re                                       # Lets us clean Markdown symbols out of chatbot replies
from flask import Flask, render_template, request, jsonify  # Added: request (reads incoming data), jsonify (sends JSON back)
import anthropic                                # The Claude AI client library
from dotenv import load_dotenv                  # Reads our secret API key from the .env file

# Load the .env file so ANTHROPIC_API_KEY is available to this app.
# This must happen before we create the Anthropic client below.
load_dotenv()

# Create the Flask app
app = Flask(__name__)

# Create the Anthropic client.
# It automatically reads ANTHROPIC_API_KEY from the environment (loaded above).
client = anthropic.Anthropic()


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

RESPONSE STYLE:
- Write in complete, polished sentences suitable for a professional portfolio website.
- Answer the visitor's question directly in the first sentence.
- Prioritize the most impressive or decision-useful information instead of listing every detail.
- Use a second short paragraph when the answer needs more than one idea.
- Do not copy raw resume bullets or fragments from the knowledge base.
- Do not end with salesy follow-up questions like "Would you like to know more?"
- If the question asks for a count, give the count first, then briefly explain it.

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


# -------------------------------------------------------
# MVP 1 — AI CHAT ROUTE
# This is the new endpoint the chatbot calls.
# The browser sends a POST request with a JSON body
# like: { "message": "What is Pete's MBSE experience?" }
# Flask calls the Claude API and sends back:
# { "response": "Pete is proficient in..." }
# -------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
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
            max_tokens=220,
            system=system_prompt,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        f"Visitor question: {user_message}\n\n"
                        "Answer in polished plain English using only the most impactful details. "
                        "Use 1 to 3 short complete sentences. If the answer has two ideas, split them into two short paragraphs. "
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
    app.run(debug=True, port=5000)
