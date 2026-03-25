# LeaveMate 🎯
### Make every class count

A full-stack web app for students to track attendance and plan their leaves strategically — always staying above the 75% minimum.

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | Python (Flask) |
| Database | SQLite |

---

## Setup & Run

### 1. Install dependencies
```bash
pip install flask flask-cors
```

### 2. Start the backend
```bash
python app.py
```
Backend starts at **http://localhost:5000**

### 3. Open the frontend
Open `index.html` in your browser, OR visit **http://localhost:5000** (Flask serves it too).

---

## Features


- **Authentication** — Secure login and registration with hashed passwords (SHA-256)
- **Subjects Management** — Add and manage subjects with color tags and priority levels
- **Attendance Tracking** — Mark attendance daily with automatic percentage calculation
- **Leave Planner** — Calculate how many classes can be missed while staying above 75%
- **Dashboard** — Visual bar chart of all subjects vs the 75% threshold line
- **Timetable** — Weekly grid to plan schedule
- **Profile Management** — Edit personal and academic details

---

## Attendance Calculation (75% Rule)

The system uses a 75% attendance threshold to determine eligibility:

**Maximum classes you can miss (if above 75%):**

N = floor((attended - 0.75 × total) / 0.75)


**Minimum classes you must attend (if below 75%):**

M = ceil((0.75 × total - attended) / 0.25)


These formulas dynamically calculate safe leave limits and required attendan

---

## Database Schema

```
users         — id, name, email, password, roll_no, semester
subjects      — id, user_id, name, code, total_classes, attended_classes, priority, color
attendance_log — id, user_id, subject_id, date, status, notes
timetable     — id, user_id, subject_id, day, start_time, end_time
```

All CRUD operations are exposed via REST API at `/api/*`.
