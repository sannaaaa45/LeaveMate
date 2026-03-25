from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='.')
CORS(app)

DB_PATH = 'leavemate.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        roll_no TEXT,
        semester TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        code TEXT,
        total_classes INTEGER DEFAULT 0,
        attended_classes INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 2,
        color TEXT DEFAULT '#00ff88',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
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
    try:
        conn.execute(
            'INSERT INTO users (name, email, password, roll_no, semester) VALUES (?,?,?,?,?)',
            (data['name'], data['email'], hash_password(data['password']),
             data.get('roll_no',''), data.get('semester',''))
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE email=?', (data['email'],)).fetchone()
        return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE email=? AND password=?',
        (data['email'], hash_password(data['password']))
    ).fetchone()
    conn.close()
    if user:
        return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'roll_no': user['roll_no'], 'semester': user['semester']}})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

# ─── SUBJECT ROUTES ─────────────────────────────────────────────────────────

@app.route('/api/subjects/<int:user_id>', methods=['GET'])
def get_subjects(user_id):
    conn = get_db()
    subjects = conn.execute('SELECT * FROM subjects WHERE user_id=?', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(s) for s in subjects])

@app.route('/api/subjects', methods=['POST'])
def add_subject():
    data = request.json
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO subjects (user_id, name, code, total_classes, attended_classes, priority, color) VALUES (?,?,?,?,?,?,?)',
        (data['user_id'], data['name'], data.get('code',''), data.get('total_classes',0),
         data.get('attended_classes',0), data.get('priority',2), data.get('color','#00ff88'))
    )
    conn.commit()
    subject = conn.execute('SELECT * FROM subjects WHERE id=?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(subject))

@app.route('/api/subjects/<int:subject_id>', methods=['PUT'])
def update_subject(subject_id):
    data = request.json
    conn = get_db()
    conn.execute(
        'UPDATE subjects SET name=?, code=?, total_classes=?, attended_classes=?, priority=?, color=? WHERE id=?',
        (data['name'], data.get('code',''), data['total_classes'], data['attended_classes'],
         data.get('priority',2), data.get('color','#00ff88'), subject_id)
    )
    conn.commit()
    subject = conn.execute('SELECT * FROM subjects WHERE id=?', (subject_id,)).fetchone()
    conn.close()
    return jsonify(dict(subject))

@app.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    conn = get_db()
    conn.execute('DELETE FROM attendance_log WHERE subject_id=?', (subject_id,))
    conn.execute('DELETE FROM timetable WHERE subject_id=?', (subject_id,))
    conn.execute('DELETE FROM subjects WHERE id=?', (subject_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── ATTENDANCE ROUTES ───────────────────────────────────────────────────────

@app.route('/api/attendance/<int:user_id>', methods=['GET'])
def get_attendance(user_id):
    conn = get_db()
    logs = conn.execute('''
        SELECT al.*, s.name as subject_name, s.color
        FROM attendance_log al
        JOIN subjects s ON al.subject_id = s.id
        WHERE al.user_id=?
        ORDER BY al.date DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO attendance_log (user_id, subject_id, date, status, notes) VALUES (?,?,?,?,?)',
        (data['user_id'], data['subject_id'], data['date'], data['status'], data.get('notes',''))
    )
    # Update subject counts
    if data['status'] == 'present':
        conn.execute('UPDATE subjects SET total_classes=total_classes+1, attended_classes=attended_classes+1 WHERE id=?', (data['subject_id'],))
    else:
        conn.execute('UPDATE subjects SET total_classes=total_classes+1 WHERE id=?', (data['subject_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': cursor.lastrowid})

@app.route('/api/attendance/<int:log_id>', methods=['DELETE'])
def delete_attendance(log_id):
    conn = get_db()
    log = conn.execute('SELECT * FROM attendance_log WHERE id=?', (log_id,)).fetchone()
    if log:
        if log['status'] == 'present':
            conn.execute('UPDATE subjects SET total_classes=total_classes-1, attended_classes=attended_classes-1 WHERE id=?', (log['subject_id'],))
        else:
            conn.execute('UPDATE subjects SET total_classes=total_classes-1 WHERE id=?', (log['subject_id'],))
        conn.execute('DELETE FROM attendance_log WHERE id=?', (log_id,))
        conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── TIMETABLE ROUTES ────────────────────────────────────────────────────────

@app.route('/api/timetable/<int:user_id>', methods=['GET'])
def get_timetable(user_id):
    conn = get_db()
    slots = conn.execute('''
        SELECT t.*, s.name as subject_name, s.color, s.priority
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id=?
        ORDER BY t.day, t.start_time
    ''', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(s) for s in slots])

@app.route('/api/timetable', methods=['POST'])
def add_timetable():
    data = request.json
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO timetable (user_id, subject_id, day, start_time, end_time) VALUES (?,?,?,?,?)',
        (data['user_id'], data['subject_id'], data['day'], data['start_time'], data['end_time'])
    )
    conn.commit()
    slot = conn.execute('''
        SELECT t.*, s.name as subject_name, s.color, s.priority
        FROM timetable t JOIN subjects s ON t.subject_id = s.id
        WHERE t.id=?
    ''', (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(slot))

@app.route('/api/timetable/<int:slot_id>', methods=['DELETE'])
def delete_timetable(slot_id):
    conn = get_db()
    conn.execute('DELETE FROM timetable WHERE id=?', (slot_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── ANALYTICS ROUTES ────────────────────────────────────────────────────────

@app.route('/api/analytics/<int:user_id>', methods=['GET'])
def get_analytics(user_id):
    conn = get_db()
    subjects = conn.execute('SELECT * FROM subjects WHERE user_id=?', (user_id,)).fetchall()
    
    result = []
    for s in subjects:
        total = s['total_classes']
        attended = s['attended_classes']
        pct = (attended / total * 100) if total > 0 else 0
        
        # How many more can bunk while maintaining 75%
        # attended / (total + x) = 0.75 => attended - 0.75*total = 0.75*x
        # x = (attended - 0.75*total) / 0.75
        if total > 0:
            can_bunk = max(0, int((attended - 0.75 * total) / 0.75))
        else:
            can_bunk = 0
        
        # How many need to attend to reach 75%
        # (attended + x) / (total + x) = 0.75
        # attended + x = 0.75*total + 0.75*x
        # 0.25*x = 0.75*total - attended
        if pct < 75:
            need_attend = max(0, int((0.75 * total - attended) / 0.25) + 1)
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
    conn.execute(
        'UPDATE users SET name=?, roll_no=?, semester=? WHERE id=?',
        (data['name'], data.get('roll_no',''), data.get('semester',''), user_id)
    )
    conn.commit()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    return jsonify({'id': user['id'], 'name': user['name'], 'email': user['email'], 'roll_no': user['roll_no'], 'semester': user['semester']})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    init_db()
    print("🚀 LeaveMate backend running on http://localhost:5000")
    app.run(debug=True, port=5000)
