# LeaveMate 🎯
### Bunk Smart, Not Hard

A full-stack web app for students to track attendance and plan their leaves strategically — always staying above the 75% minimum.

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | Python (Flask) |
| Database | SQLite (auto-created) |

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

- **Auth** — Register / Login with hashed passwords (SHA-256)
- **Subjects** — Add subjects with color tags, subject codes, priority levels
- **Attendance Tracking** — Mark present/absent per subject per day, instant count update
- **Bunk Planner** — See exactly how many more classes you can skip per subject while staying ≥75%
- **Dashboard** — Visual bar chart of all subjects vs the 75% threshold line
- **Timetable** — Weekly grid to plan your schedule
- **Profile** — Editable name, roll number, semester

---

## The 75% Math

**Can bunk N more classes:**
```
N = floor((attended - 0.75 × total) / 0.75)
```

**Need to attend M more (if below 75%):**
```
M = ceil((0.75 × total - attended) / 0.25)
```

---

## Database Schema

```
users         — id, name, email, password, roll_no, semester
subjects      — id, user_id, name, code, total_classes, attended_classes, priority, color
attendance_log — id, user_id, subject_id, date, status, notes
timetable     — id, user_id, subject_id, day, start_time, end_time
```

All CRUD operations are exposed via REST API at `/api/*`.
