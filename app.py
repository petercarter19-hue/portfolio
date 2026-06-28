# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page.

from flask import Flask, render_template

# Create the Flask app
# __name__ tells Flask where to find files like templates and static assets
app = Flask(__name__)


# --- ROUTES ---
# A "route" tells Flask: "when someone goes to THIS URL, run THIS function"

# Home page — when someone visits http://127.0.0.1:5000/
@app.route('/')
def home():
    return render_template('index.html')


# About page — http://127.0.0.1:5000/about
@app.route('/about')
def about():
    return render_template('about.html')


# Work Experience page — http://127.0.0.1:5000/work
@app.route('/work')
def work():
    return render_template('work.html')


# Skills & Certifications page — http://127.0.0.1:5000/skills
@app.route('/skills')
def skills():
    return render_template('skills.html')


# Hobbies page — http://127.0.0.1:5000/hobbies
@app.route('/hobbies')
def hobbies():
    return render_template('hobbies.html')


# Contact page — http://127.0.0.1:5000/contact
@app.route('/contact')
def contact():
    return render_template('contact.html')


# --- START THE SERVER ---
# This runs the website locally when you type: python app.py
# debug=True means it auto-reloads when you save changes
if __name__ == '__main__':
    app.run(debug=True, port=8080)   # Port 8080 used because Windows reserves port 5000
