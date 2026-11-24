# CampusDesk — Student Data Collection & Attendance System

## Features
- Teacher login; all student and attendance pages require sign-in.
- Add, view, edit and delete student records.
- Search and filter students; export student and attendance records to CSV.
- Select an attendance date and mark every student Present or Absent.
- Re-save a date to update attendance; records are unique per student per date.
- Dashboard pie chart shows Present, Absent and Unmarked students for today.

## Run on Windows
1. Extract the ZIP and open the folder in VS Code.
2. Run `python -m venv venv` then `venv\Scripts\activate` (optional).
3. Run `pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000`.

## Demo teacher login
Username: `teacher`  
Password: `teacher123`

On first run, `students.db` is created with the demo teacher and three sample students. Existing student records are retained when upgrading this project; attendance and teacher tables are added automatically.

## Technology
Python, Flask, SQLite, HTML, CSS, Jinja templates and Chart.js. Chart.js loads from a CDN, so the pie chart requires an internet connection.

## Security note
This is a local academic demo, not production-ready. Change the demo password and set a strong random `SECRET_KEY` environment variable. Before public deployment add CSRF protection, HTTPS, rate limiting, backups, audit logging and privacy controls; disable Flask debug mode.
