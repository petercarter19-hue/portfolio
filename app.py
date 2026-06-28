# app.py - The main Flask application for Pete Carter's Portfolio
# This file is the "brain" of the website.
# It tells Flask what page to show when someone visits each URL.

from flask import Flask, render_template
app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)