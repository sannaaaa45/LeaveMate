from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import os
import math
from datetime import datetime

app = Flask(__name__, static_folder='.')
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:Sanna@2006$& @db.hjsdhqzbumkbhfyhzlfi.supabase.co:5432/postgres")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        roll_no TEXT,
        semester TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        code TEXT,
        total_classes INTEGER DEFAULT 0,
        attended_classes INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 2,
        color TEXT DEFAULT '#00ff88'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_log (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AUTH ROUTES ────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    try:
        c.execute(
            'INSERT INTO users (name, email, password, roll_no, semester) VALUES (%s,%s,%s,%s,%s) RETURNING id',
            (data['name'], data['email'], hash_password(data['password']),
             data.get('roll_no',''), data.get('semester',''))
        )
        new_id = c.fetchone()['id']
        conn.commit()
        c.execute('SELECT * FROM users WHERE id=%s', (new_id,))
        user = c.fetchone()
        return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}})
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'SELECT * FROM users WHERE email=%s AND password=%s',
        (data['email'], hash_password(data['password']))
    )
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'roll_no': user['roll_no'], 'semester': user['semester']}})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

# ─── SUBJECT ROUTES ─────────────────────────────────────────────────────────

@app.route('/api/subjects/<int:user_id>', methods=['GET'])
def get_subjects(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('SELECT * FROM subjects WHERE user_id=%s', (user_id,))
    subjects = c.fetchall()
    conn.close()
    return jsonify([dict(s) for s in subjects])

@app.route('/api/subjects', methods=['POST'])
def add_subject():
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'INSERT INTO subjects (user_id, name, code, total_classes, attended_classes, priority, color) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',
        (data['user_id'], data['name'], data.get('code',''), data.get('total_classes',0),
         data.get('attended_classes',0), data.get('priority',2), data.get('color','#00ff88'))
    )
    new_id = c.fetchone()['id']
    conn.commit()
    c.execute('SELECT * FROM subjects WHERE id=%s', (new_id,))
    subject = c.fetchone()
    conn.close()
    return jsonify(dict(subject))

@app.route('/api/subjects/<int:subject_id>', methods=['PUT'])
def update_subject(subject_id):
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'UPDATE subjects SET name=%s, code=%s, total_classes=%s, attended_classes=%s, priority=%s, color=%s WHERE id=%s',
        (data['name'], data.get('code',''), data['total_classes'], data['attended_classes'],
         data.get('priority',2), data.get('color','#00ff88'), subject_id)
    )
    conn.commit()
    c.execute('SELECT * FROM subjects WHERE id=%s', (subject_id,))
    subject = c.fetchone()
    conn.close()
    return jsonify(dict(subject))

@app.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM subjects WHERE id=%s', (subject_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── ATTENDANCE ROUTES ───────────────────────────────────────────────────────

@app.route('/api/attendance/<int:user_id>', methods=['GET'])
def get_attendance(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('''
        SELECT al.*, s.name as subject_name, s.color
        FROM attendance_log al
        JOIN subjects s ON al.subject_id = s.id
        WHERE al.user_id=%s
        ORDER BY al.date DESC
    ''', (user_id,))
    logs = c.fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'INSERT INTO attendance_log (user_id, subject_id, date, status, notes) VALUES (%s,%s,%s,%s,%s) RETURNING id',
        (data['user_id'], data['subject_id'], data['date'], data['status'], data.get('notes',''))
    )
    log_id = c.fetchone()['id']
    if data['status'] == 'present':
        c.execute('UPDATE subjects SET total_classes=total_classes+1, attended_classes=attended_classes+1 WHERE id=%s', (data['subject_id'],))
    else:
        c.execute('UPDATE subjects SET total_classes=total_classes+1 WHERE id=%s', (data['subject_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': log_id})

@app.route('/api/attendance/<int:log_id>', methods=['DELETE'])
def delete_attendance(log_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('SELECT * FROM attendance_log WHERE id=%s', (log_id,))
    log = c.fetchone()
    if log:
        if log['status'] == 'present':
            c.execute('UPDATE subjects SET total_classes=total_classes-1, attended_classes=attended_classes-1 WHERE id=%s', (log['subject_id'],))
        else:
            c.execute('UPDATE subjects SET total_classes=total_classes-1 WHERE id=%s', (log['subject_id'],))
        c.execute('DELETE FROM attendance_log WHERE id=%s', (log_id,))
        conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── TIMETABLE ROUTES ────────────────────────────────────────────────────────

@app.route('/api/timetable/<int:user_id>', methods=['GET'])
def get_timetable(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('''
        SELECT t.*, s.name as subject_name, s.color, s.priority
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id=%s
        ORDER BY t.day, t.start_time
    ''', (user_id,))
    slots = c.fetchall()
    conn.close()
    return jsonify([dict(s) for s in slots])

@app.route('/api/timetable', methods=['POST'])
def add_timetable():
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'INSERT INTO timetable (user_id, subject_id, day, start_time, end_time) VALUES (%s,%s,%s,%s,%s) RETURNING id',
        (data['user_id'], data['subject_id'], data['day'], data['start_time'], data['end_time'])
    )
    slot_id = c.fetchone()['id']
    conn.commit()
    c.execute('''
        SELECT t.*, s.name as subject_name, s.color, s.priority
        FROM timetable t JOIN subjects s ON t.subject_id = s.id
        WHERE t.id=%s
    ''', (slot_id,))
    slot = c.fetchone()
    conn.close()
    return jsonify(dict(slot))

@app.route('/api/timetable/<int:slot_id>', methods=['DELETE'])
def delete_timetable(slot_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM timetable WHERE id=%s', (slot_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── ANALYTICS ROUTES ────────────────────────────────────────────────────────

@app.route('/api/analytics/<int:user_id>', methods=['GET'])
def get_analytics(user_id):
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute('SELECT * FROM subjects WHERE user_id=%s', (user_id,))
    subjects = c.fetchall()
    
    result = []
    for s in subjects:
        total = s['total_classes']
        attended = s['attended_classes']
        pct = (attended / total * 100) if total > 0 else 0
        
        if total > 0:
            can_bunk = max(0, int((attended - 0.75 * total) / 0.75))
        else:
            can_bunk = 0
            
        if pct < 75:
            need_attend = max(0, math.ceil((0.75 * total - attended) / 0.25))
        else:
            need_attend = 0
        
        result.append({
            'id': s['id'],
            'name': s['name'],
            'code': s['code'],
            'total': total,
            'attended': attended,
            'percentage': round(pct, 1),
            'can_bunk': can_bunk,
            'need_attend': need_attend,
            'priority': s['priority'],
            'color': s['color'],
            'status': 'safe' if pct >= 75 else ('warning' if pct >= 65 else 'danger')
        })
    
    conn.close()
    return jsonify(result)

# ─── USER ROUTES ─────────────────────────────────────────────────────────────

@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    conn = get_db()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(
        'UPDATE users SET name=%s, roll_no=%s, semester=%s WHERE id=%s',
        (data['name'], data.get('roll_no',''), data.get('semester',''), user_id)
    )
    conn.commit()
    c.execute('SELECT * FROM users WHERE id=%s', (user_id,))
    user = c.fetchone()
    conn.close()
    return jsonify({'id': user['id'], 'name': user['name'], 'email': user['email'], 'roll_no': user['roll_no'], 'semester': user['semester']})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ != '__main__':
    try:
        init_db()
    except Exception as e:
        print("Database initialization failed (perhaps wrong password):", e)

if __name__ == '__main__':
    init_db()
    print("🚀 LeaveMate backend running on http://127.0.0.1:5000")
    import os
    port=int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
