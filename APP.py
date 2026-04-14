from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string, session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # change this in production

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB = 'users.db'

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )''')
init_db()

HTML = '''
<!doctype html>
<title>the Free cloud</title>
{% if session.get('user') %}
  <p>Logged in as {{ session['user'] }} | <a href="/logout">Logout</a></p>
  <h1>Upload a File</h1>
  <form method=post enctype=multipart/form-data>
    <input type=file name=file>
    <input type=submit value=Upload>
  </form>

  <h2>Your Files:</h2>
  <ul>
  {% for file in files %}
    <li><a href="/download/{{ file }}">{{ file }}</a></li>
  {% endfor %}
  </ul>
{% else %}
  <h2>Login</h2>
  <form method="post" action="/login">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">Login</button>
  </form>

  <h2>Register</h2>
  <form method="post" action="/register">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">Register</button>
  </form>
{% endif %}
'''

# Helper to get a user's personal folder
def get_user_folder(username):
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return render_template_string(HTML)

    username = session['user']
    user_folder = get_user_folder(username)

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)
            return redirect(url_for('home'))

    files = os.listdir(user_folder)
    return render_template_string(HTML, files=files)

@app.route('/download/<filename>')
def download_file(filename):
    if 'user' not in session:
        return redirect(url_for('home'))

    username = session['user']
    user_folder = get_user_folder(username)

    return send_from_directory(user_folder, filename, as_attachment=True)

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = generate_password_hash(request.form['password'])

    try:
        with sqlite3.connect(DB) as conn:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    except sqlite3.IntegrityError:
        return '''
        <!doctype html>
        <title>Register unsuccessful</title>
        <h2>User already exists</h2>
        <p><a href="/">home</a></p>
        '''

    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    with sqlite3.connect(DB) as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if user and check_password_hash(user[2], password):
        session['user'] = username
    else:
        return 'Invalid credentials'

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
