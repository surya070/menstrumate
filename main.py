from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
db = "period_tracker.db"
user_id = None

def init_db():
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                cycle_duration INTEGER DEFAULT 28
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        con.commit()

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        try:
            cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            con.commit()
            return redirect(url_for("log"))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists")
    

@app.route('/log', methods=['GET', 'POST'])
def log():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    global user_id
    username = request.form['username']
    password = request.form['password']
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cur.fetchone()
        if user:
            user_id = username
            return redirect(url_for('view_entries'))
        else:
            return render_template('login.html', error="Invalid username or password")

@app.route('/logout')
def logout():
    global user_id
    user_id = None
    return redirect(url_for('log'))

@app.route('/')
def index():
    if user_id:
        return redirect(url_for('view_entries'))
    else:
        return render_template('login.html')

@app.route('/ad', methods=['GET'])
def ad():
    if user_id:
        return render_template('add_entry.html')
    else:
        return redirect(url_for('log'))

@app.route('/add', methods=['POST'])
def add_entry():
    global user_id
    if user_id:
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute('INSERT INTO periods (username, start_date, end_date) VALUES (?, ?, ?)', (user_id, start_date, end_date))
            con.commit()
            return redirect(url_for('view_entries'))
        
    else:
        return redirect(url_for('log'))

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    global user_id
    if user_id:
        if request.method == 'POST':
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            with sqlite3.connect(db) as con:
                cur = con.cursor()
                cur.execute('UPDATE periods SET start_date = ?, end_date = ? WHERE id = ? AND username = ?', (start_date, end_date, entry_id, user_id))
                con.commit()
                return redirect(url_for('view_entries'))
            
        else:
            with sqlite3.connect(db) as con:
                cur = con.cursor()
                cur.execute('SELECT * FROM periods WHERE id = ? AND username = ?', (entry_id, user_id))
                entry = cur.fetchone()
                if entry:
                    return render_template('edit_entry.html', entry=entry)
            return redirect(url_for('view_entries'))
    else:
        return redirect(url_for('log'))

@app.route('/delete/<int:entry_id>')
def delete_entry(entry_id):
    global user_id
    if user_id:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute('DELETE FROM periods WHERE id = ? AND username = ?', (entry_id, user_id))
            con.commit()
        return redirect(url_for('view_entries'))
    else:
        return redirect(url_for('log'))

@app.route('/view')
def view_entries():
    global user_id
    if user_id:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute('SELECT * FROM periods WHERE username = ? ORDER BY start_date DESC', (user_id,))
            entries = cur.fetchall()
            cur.execute('SELECT cycle_duration FROM users WHERE username = ?', (user_id,))
            cycle_duration = cur.fetchone()[0]

        next_period, ovulation, fertile_start, fertile_end, days_until_next_period, days_until_ovulation = calculate_next_period_and_ovulation(entries, cycle_duration)

        return render_template('view_entries.html', username=user_id,entries=entries, next_period=next_period, ovulation=ovulation, fertile_start=fertile_start, fertile_end=fertile_end, days_until_next_period=days_until_next_period, days_until_ovulation=days_until_ovulation)
    else:
        return redirect(url_for('log'))

def calculate_next_period_and_ovulation(entries, cycle_duration):
    if not entries:
        return None, None, None, None, None, None
    
    last_period = datetime.strptime(entries[0][2], '%Y-%m-%d')
    next_period = last_period + timedelta(days=cycle_duration)
    ovulation = last_period + timedelta(days=(cycle_duration // 2))
    fertile_start = ovulation - timedelta(days=3)
    fertile_end = ovulation + timedelta(days=2)
    today = datetime.today()
    days_until_next_period = (next_period - today).days
    days_until_ovulation = (ovulation - today).days

    return next_period.strftime('%Y-%m-%d'), ovulation.strftime('%Y-%m-%d'), fertile_start.strftime('%Y-%m-%d'), fertile_end.strftime('%Y-%m-%d'), days_until_next_period, days_until_ovulation

@app.route('/set', methods=['GET'])
def set():
    if user_id:
        return render_template('settings.html')
    else:
        return redirect(url_for('log'))

@app.route('/settings', methods=['POST'])
def settings():
    global user_id
    if user_id:
        cycle_duration = request.form['cycle_duration']
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute('UPDATE users SET cycle_duration = ? WHERE username = ?', (cycle_duration, user_id))
            con.commit()
            return redirect(url_for('view_entries'))
    else:
        return redirect(url_for('log'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
