# app.py — The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what to show when someone visits each page.

from flask import Flask, render_template

# Create the Flask app
# __name__ tells Flask where to find files like templates and static assets
app = Flask(__name__)


# --- ROUTES ---
# A "route" tells Flask: "when someone goes to THIS URL, run THIS function"

# PeerSlate home page
@app.route('/')
def site_home():
    return render_template('site_home.html')


# Pete Carter portfolio home page
@app.route('/petec')
def home():
    return render_template('index.html')


# My Story page
@app.route('/about')
@app.route('/my-story')
@app.route('/petec/my-story')
def about():
    return render_template('my_story.html')


# Projects page
@app.route('/work')
@app.route('/petec/work')
def work():
    return render_template('work.html')


# Interactive resume page — http://127.0.0.1:5000/resume
@app.route('/resume')
@app.route('/petec/resume')
def resume():
    return render_template('resume.html')


# Legacy local route: the live site now keeps skills inside the resume.
@app.route('/skills')
def skills():
    return render_template('resume.html')


# Legacy local route: the live site now uses My Story for personal context.
@app.route('/hobbies')
def hobbies():
    return render_template('my_story.html')


# Contact page — http://127.0.0.1:5000/contact
@app.route('/contact')
@app.route('/petec/contact')
def contact():
    return render_template('contact.html')


# --- START THE SERVER ---
# This runs the website locally when you type: python app.py
# debug=True means it auto-reloads when you save changes
if __name__ == '__main__':
    app.run(debug=True, port=5000)
