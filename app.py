from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from flask import make_response
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rootuser1',  # CHANGE THIS to your MySQL password
    'database': 'fit'
}

# Helper function to get database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Decorator to check login
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Health status calculation
def calculate_health_status(heart_rate, steps, sleep):
    issues = []
    
    if heart_rate < 60:
        issues.append('Low heart rate detected')
    elif heart_rate > 100:
        issues.append('Elevated heart rate detected')
    
    if sleep < 7:
        issues.append('Insufficient sleep')
    elif sleep > 9:
        issues.append('Excessive sleep')
    
    if steps < 5000:
        issues.append('Low activity level')
    
    if len(issues) == 0:
        return 'Healthy'
    elif len(issues) == 1:
        return 'Warning'
    else:
        return 'Critical'

# --- ROUTES ---

@app.route('/')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('welcome.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        age = request.form['age']
        gender = request.form['gender']
        password = request.form['password']
        
        # Server-side Validation
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if username OR email already exists
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            conn.close()
            if existing_user['username'] == username:
                flash('Username already taken. Please choose another.', 'error')
            else:
                flash('Email address already registered.', 'error')
            return render_template('register.html')
        
        # Hash password and Insert new user
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            'INSERT INTO users (username, email, age, gender, password) VALUES (%s, %s, %s, %s, %s)',
            (username, email, age, gender, hashed_password)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('welcome'))

@app.route('/home')
@login_required
def home():
    username = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get today's data
    today = datetime.now().date()
    cursor.execute(
        'SELECT * FROM health_data WHERE username = %s AND DATE(entry_time) = %s',
        (username, today)
    )
    today_data = cursor.fetchone()
    
    # Get recent entries
    cursor.execute(
        'SELECT * FROM health_data WHERE username = %s ORDER BY entry_time DESC LIMIT 5',
        (username,)
    )
    recent_entries = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Calculate status
    today_status = 'healthy'
    if today_data:
        today_status = today_data['status'].lower()
    
    return render_template('home.html', 
                         user={'username': username},
                         today_data=today_data or {},
                         today_status=today_status,
                         recent_entries=recent_entries)

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    days = request.args.get('days', 7, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get the data
    cursor.execute(
        '''SELECT * FROM health_data 
           WHERE username = %s 
           AND entry_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
           ORDER BY entry_time ASC''',
        (username, days)
    )
    all_data = cursor.fetchall()
    
    # 2. Calculate Averages
    avg_heart_rate = 0
    avg_steps = 0
    avg_sleep = 0
    overall_status = "Healthy"

    if all_data:
        avg_heart_rate = round(sum(d['heart_rate'] for d in all_data) / len(all_data))
        avg_steps = round(sum(d['steps'] for d in all_data) / len(all_data))
        avg_sleep = round(sum(float(d['sleep']) for d in all_data) / len(all_data), 1)
        
        # Simple logic for overall status
        if avg_heart_rate > 100 or avg_sleep < 6:
            overall_status = "Warning"

    # Prepare chart data
    chart_data = {
        'heart_rate': [d['heart_rate'] for d in all_data],
        'steps': [d['steps'] for d in all_data],
        'sleep': [float(d['sleep']) for d in all_data],
        'dates': [d['entry_time'].strftime('%Y-%m-%d') for d in all_data]
    }

    cursor.close()
    conn.close()

    # Pass everything to template
    return render_template('dashboard.html',
                         health_data=all_data[-20:],
                         chart_data=chart_data,
                         avg_heart_rate=avg_heart_rate,
                         avg_steps=avg_steps,
                         avg_sleep=avg_sleep,
                         overall_status=overall_status,
                         days=days)

@app.route('/data_entry', methods=['GET', 'POST'])
@login_required
def data_entry():
    if request.method == 'POST':
        username = session['username']
        heart_rate = int(request.form['heartRate'])
        steps = int(request.form['steps'])
        sleep = float(request.form['sleep'])
        entry_time = datetime.strptime(request.form['time'], '%Y-%m-%dT%H:%M')
        
        status = calculate_health_status(heart_rate, steps, sleep)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            '''INSERT INTO health_data (username, heart_rate, steps, sleep, status, entry_time)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (username, heart_rate, steps, sleep, status, entry_time)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f'Health data saved! Status: {status}', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('data_entry.html')

from flask import make_response
import csv
from io import StringIO

@app.route('/export_data')
@login_required
def export_data():
    username = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all data for this user (not just last 7 days)
    cursor.execute(
        'SELECT entry_time, heart_rate, steps, sleep, status FROM health_data WHERE username = %s ORDER BY entry_time DESC',
        (username,)
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    # Create a file-like buffer to receive CSV data
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(['Date & Time', 'Heart Rate (bpm)', 'Steps', 'Sleep (hours)', 'Status'])

    # Write the data rows
    for row in data:
        writer.writerow([
            row['entry_time'], 
            row['heart_rate'], 
            row['steps'], 
            row['sleep'], 
            row['status']
        ])

    # Prepare the response
    output.seek(0)
    response = make_response(output.getvalue())
    
    # Set headers so browser downloads the file
    response.headers['Content-Disposition'] = 'attachment; filename=fitpulse_health_data.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user info
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    
    # Get stats
    cursor.execute(
        '''SELECT 
               AVG(heart_rate) as avg_heart_rate,
               COUNT(*) as total_entries,
               COUNT(DISTINCT DATE(entry_time)) as days_active
           FROM health_data WHERE username = %s''',
        (username,)
    )
    stats = cursor.fetchone()
    
    if request.method == 'POST':
        # Update profile
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
        user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('profile.html', user=user, stats=stats)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    username = session['username']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    
    if user and check_password_hash(user['password'], current_password):
        cursor.execute(
            'UPDATE users SET password = %s WHERE username = %s',
            (generate_password_hash(new_password), username)
        )
        conn.commit()
        flash('Password changed successfully!', 'success')
    else:
        flash('Current password is incorrect', 'error')
    
    cursor.close()
    conn.close()
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)