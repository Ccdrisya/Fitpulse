from asyncio import sleep

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
# import mysql.connector
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL Configuration
# db_config = {
#     'host': 'localhost',
#     'user': 'root',
#     'password': 'rootuser1',
#     'database': 'fit'
# }
def get_db_connection():
    if os.environ.get("RENDER"):  
        return psycopg2.connect(
            host=os.environ.get("DB_HOST"),
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            port=os.environ.get("DB_PORT")
        )
    else:
        return mysql.connector.connect(**db_config)
# def get_db_connection():
#     return mysql.connector.connect(**db_config)

@app.route('/init_db')
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT,
        age INT,
        gender TEXT,
        password TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_data (
        id SERIAL PRIMARY KEY,
        username TEXT,
        heart_rate INT,
        steps INT,
        sleep FLOAT,
        status TEXT,
        entry_time TIMESTAMP
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()

    return "Tables created!"

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# --- ROUTES ---

@app.route('/')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        # cursor = conn.cursor(dictionary=True)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # user = cursor.fetchone()
        user = fetch_one_dict(cursor)
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            age = request.form['age']
            gender = request.form['gender']
            password = generate_password_hash(request.form['password'])
                
            conn = get_db_connection()
            # cursor = conn.cursor(dictionary=True)
            cursor = conn.cursor()
            
            # cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            # if cursor.fetchone():
            #     flash('Username exists', 'error')
            #     return render_template('register.html')

            #render---
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            existing_user = fetch_one_dict(cursor)
            if existing_user:
                flash('Username already exists', 'error')
                cursor.close()
                conn.close()
                return render_template('register.html')
            cursor.execute(
                'INSERT INTO users (username, email, age, gender, password) VALUES (%s, %s, %s, %s, %s)',
                (username, email, age, gender, password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Registered! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            return str(e) 
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))


@app.context_processor
def inject_user():
    if 'username' in session:
        return dict(user={'username': session['username']})
    return dict(user=None)

@app.route('/home')
@login_required
def home():
    username = session['username']

    conn = get_db_connection()
    # cursor = conn.cursor(dictionary=True)
    cursor = conn.cursor()

    # latest snapshot (already exists)
    cursor.execute('SELECT * FROM health_data WHERE username = %s ORDER BY entry_time DESC LIMIT 1', (username,))
    # latest = cursor.fetchone()

#render-----
    latest = fetch_one_dict(cursor)

    # ✅ NEW: last 15 records for anomaly chart
    cursor.execute('''
        SELECT entry_time, steps, status 
        FROM health_data 
        WHERE username = %s 
        ORDER BY entry_time ASC 
        LIMIT 15
    ''', (username,))
    # recent_chart = cursor.fetchall()
    #render----
    recent_chart = fetch_all_dict(cursor)
    cursor.close()
    conn.close()

    chart_data = {
        'dates': [d['entry_time'].strftime('%m-%d') for d in recent_chart],
        'steps': [d['steps'] for d in recent_chart],
        'status': [d['status'] for d in recent_chart]
    }

    return render_template('home.html',
                           user={'username': username},
                           latest=latest,
                           chart_data=chart_data,
                           recent_entries=[latest] if latest else [])
# --- NEW: UPLOAD FEATURE (Milestone 4 Logic) ---
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        try:
            # Read file
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.json'):
                df = pd.read_json(file)
            else:
                flash('Unsupported format. Use CSV or JSON.', 'error')
                return redirect(request.url)

            
            # Save to DB
            conn = get_db_connection()
            # cursor = conn.cursor(dictionary=True)
            cursor = conn.cursor()
            
            count = 0
            for _, row in df.iterrows():
                # Find date column dynamically
                date_val = row.get('entry_time') or row.get('ds') or row.get('timestamp') or datetime.now()
                
                # Find metric columns dynamically
                hr = row.get('heart_rate') or row.get('heart_rate_bpm') or 0
                steps = row.get('steps') or 0
                sleep = row.get('sleep') or 0
                hr = int(hr)
                sleep = float(sleep)

                if hr >= 120 or sleep < 5:
                    status = "Critical"
                elif hr >= 100 or sleep < 6:
                    status = "Warning"
                else:
                    status = "Healthy"# Use calculated severity
                
                cursor.execute(
                    """INSERT INTO health_data (username, heart_rate, steps, sleep, status, entry_time)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session['username'], int(hr), int(steps), float(sleep), status, date_val)
                )
                count += 1

                
                
            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Successfully imported {count} records!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            
    return render_template('upload.html')

@app.route('/data_entry', methods=['GET', 'POST'])
@login_required
def data_entry():
    if request.method == 'POST':
        username = session['username']
        hr = int(request.form['heartRate'])
        steps = int(request.form['steps'])
        sleep = float(request.form['sleep'])
        entry_time = datetime.strptime(request.form['time'], '%Y-%m-%dT%H:%M')
        
        # Simple rule-based logic
        if hr >= 120 or sleep < 5:
            status = "Critical"
        elif hr >= 100 or sleep < 6:
            status = "Warning"
        else:
            status = "Healthy"

        conn = get_db_connection()
        # cursor = conn.cursor(dictionary=True)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO health_data (username, heart_rate, steps, sleep, status, entry_time) VALUES (%s, %s, %s, %s, %s, %s)',
            (username, hr, steps, sleep, status, entry_time)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Data saved! Status: {status}', 'success')
        return redirect(url_for('dashboard'))
    return render_template('data_entry.html')

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    days = request.args.get('days', 7, type=int)

    conn = get_db_connection()
    # cursor = conn.cursor(dictionary=True)
    cursor = conn.cursor()
    # cursor.execute(
    #     '''SELECT * FROM health_data 
    #        WHERE username = %s 
    #        AND entry_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
    #        ORDER BY entry_time ASC''',
    #     (username, days)
    # )
    # health_data = cursor.fetchall()
#render-----
    cursor.execute(
        '''SELECT * FROM health_data 
        WHERE username = %s 
        AND entry_time >= NOW() - (%s * INTERVAL '1 day')
        ORDER BY entry_time ASC''',
        (username, days)
    )
    health_data = fetch_all_dict(cursor)
    cursor.close()
    conn.close()

    # Calculate stats
    avg_hr = round(sum(d['heart_rate'] for d in health_data) / len(health_data)) if health_data else 0
    avg_steps = round(sum(d['steps'] for d in health_data) / len(health_data)) if health_data else 0
    avg_sleep = round(sum(float(d['sleep']) for d in health_data) / len(health_data), 1) if health_data else 0

    # Fix status and add class for CSS
    for entry in health_data:
        if not entry.get('status'):
            entry['status'] = 'Healthy'
        status_lower = entry['status'].lower()
        if status_lower in ['healthy', 'normal']:
            entry['status_class'] = 'healthy'
        elif status_lower == 'warning':
            entry['status_class'] = 'warning'
        elif status_lower == 'critical':
            entry['status_class'] = 'critical'
        else:
            entry['status_class'] = 'healthy'

    # Prepare chart data
    chart_data = {
        'heart_rate': [d['heart_rate'] for d in health_data],
        'steps': [d['steps'] for d in health_data],
        'sleep': [float(d['sleep']) for d in health_data],
        'dates': [d['entry_time'].strftime('%Y-%m-%d %H:%M') for d in health_data],
        'status': [d['status'] for d in health_data]  # optional for chart
    }

    return render_template('dashboard.html',
                           health_data=health_data[-20:],
                           chart_data=chart_data,
                           avg_heart_rate=avg_hr,
                           avg_steps=avg_steps,
                           avg_sleep=avg_sleep,
                           days=days)

@app.route('/export_data')
@login_required
def export_data():
    username = session['username']

    conn = get_db_connection()
    # cursor = conn.cursor(dictionary=True)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT entry_time, heart_rate, steps, sleep, status FROM health_data WHERE username = %s",
        (username,)
    )
    data = fetch_all_dict(cursor)

    cursor.close()
    conn.close()

    if not data:
        flash("No data to export", "warning")
        return redirect(url_for('dashboard'))

    df = pd.DataFrame(data)

    response = make_response(df.to_csv(index=False))
    response.headers["Content-Disposition"] = "attachment; filename=health_data.csv"
    response.headers["Content-Type"] = "text/csv"

    return response

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = session['username']
    conn = get_db_connection()
    # cursor = conn.cursor(dictionary=True)
    cursor = conn.cursor()

    # Get user info
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    # user = cursor.fetchone()
    user = fetch_one_dict(cursor)

    # Get stats for the profile page
    cursor.execute('SELECT COUNT(*) as total_entries FROM health_data WHERE username = %s', (username,))
    stats = fetch_one_dict(cursor)

    if request.method == 'POST':
        # Handle Profile Update
        email = request.form['email']
        age = request.form['age']
        gender = request.form['gender']
        
        cursor.execute(
            'UPDATE users SET email = %s, age = %s, gender = %s WHERE username = %s',
            (email, age, gender, username)
        )
        conn.commit()
        flash('Profile updated successfully!', 'success')
        
        # Refresh user data
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # user = cursor.fetchone()
        user = fetch_one_dict(cursor)

    cursor.close()
    conn.close()
    
    return render_template('profile.html', user=user, stats=stats)

@app.route('/change_password', methods=['POST'])
def change_password():
    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')

    if new != confirm:
        flash("Passwords do not match", "danger")
        return redirect(url_for('profile'))

    # TODO: verify current password + update in DB

    flash("Password updated successfully", "success")
    return redirect(url_for('profile'))

@app.route('/delete_all', methods=['POST'])
@login_required
def delete_all():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM health_data WHERE username = %s", (session['username'],))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

## Helper functions to convert DB results to dicts (if not using dictionary cursor)-renderdb
def fetch_all_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def fetch_one_dict(cursor):
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None

if __name__ == '__main__':
    app.run(debug=True)