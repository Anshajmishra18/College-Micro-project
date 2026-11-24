from flask import Flask, render_template, request, redirect, url_for, flash, make_response, abort, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
import sqlite3, csv, io, os
from pathlib import Path
app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY','change-this-demo-secret-before-deployment')
DB_PATH=Path(__file__).with_name('students.db')
def get_db():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init_db():
 with get_db() as c:
  c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,display_name TEXT NOT NULL)''')
  c.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,full_name TEXT NOT NULL,roll_number TEXT NOT NULL UNIQUE,email TEXT NOT NULL,phone TEXT,department TEXT NOT NULL,course TEXT,year_of_study INTEGER NOT NULL,gender TEXT,date_of_birth TEXT,address TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
  c.execute('''CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,attendance_date TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('Present','Absent')),marked_by INTEGER,marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,UNIQUE(student_id,attendance_date))''')
  if not c.execute("SELECT id FROM users WHERE username='teacher'").fetchone(): c.execute('INSERT INTO users(username,password_hash,display_name) VALUES(?,?,?)',('teacher',generate_password_hash('teacher123'),'College Teacher'))
  if c.execute('SELECT COUNT(*) FROM students').fetchone()[0]==0:
   c.executemany('INSERT INTO students(full_name,roll_number,email,phone,department,course,year_of_study,gender,date_of_birth,address) VALUES(?,?,?,?,?,?,?,?,?,?)',[
   ('Aarav Sharma','CS2024001','aarav@example.com','9876543210','Computer Science','B.Tech',2,'Male','2005-02-14','Bhopal, Madhya Pradesh'),('Diya Verma','IT2024002','diya@example.com','9876501234','Information Technology','B.Tech',2,'Female','2004-11-08','Indore, Madhya Pradesh'),('Kabir Khan','EC2023007','kabir@example.com','9123456780','Electronics','B.Tech',3,'Male','2004-04-21','Sehore, Madhya Pradesh')])
def login_required(fn):
 @wraps(fn)
 def wrapped(*a,**kw):
  if 'user_id' not in session: return redirect(url_for('login',next=request.path))
  return fn(*a,**kw)
 return wrapped
def validate_student(d):
 for f in ['full_name','roll_number','email','department','year_of_study']:
  if not d.get(f,'').strip(): return f"Please fill in the {f.replace('_',' ')} field."
 try:
  if int(d['year_of_study']) not in range(1,7): return 'Year must be between 1 and 6.'
 except ValueError: return 'Please select a valid year.'
 if '@' not in d['email'] or '.' not in d['email'].split('@')[-1]: return 'Please enter a valid email address.'
 return None
@app.route('/login',methods=['GET','POST'])
def login():
 if 'user_id' in session: return redirect(url_for('index'))
 if request.method=='POST':
  with get_db() as c: u=c.execute('SELECT * FROM users WHERE username=?',(request.form.get('username','').strip(),)).fetchone()
  if u and check_password_hash(u['password_hash'],request.form.get('password','')):
   session.clear(); session['user_id']=u['id']; session['display_name']=u['display_name']; return redirect(request.args.get('next') or url_for('index'))
  flash('Incorrect username or password.','error')
 return render_template('login.html')
@app.post('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
@login_required
def index():
 q=request.args.get('q','').strip(); dept=request.args.get('department','').strip(); today=date.today().isoformat()
 with get_db() as c:
  where=[]; p=[]
  if q: where.append('(s.full_name LIKE ? OR s.roll_number LIKE ? OR s.email LIKE ?)'); p += [f'%{q}%']*3
  if dept: where.append('s.department=?'); p.append(dept)
  clause=' WHERE '+' AND '.join(where) if where else ''
  students=c.execute(f'''SELECT s.*,a.status AS today_status FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date=? {clause} ORDER BY s.created_at DESC''',[today]+p).fetchall()
  total=c.execute('SELECT COUNT(*) FROM students').fetchone()[0]; departments=c.execute('SELECT COUNT(DISTINCT department) FROM students').fetchone()[0]
  stats={r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM attendance WHERE attendance_date=? GROUP BY status',(today,)).fetchall()}
  depts=c.execute('SELECT DISTINCT department FROM students ORDER BY department').fetchall()
 present=stats.get('Present',0); absent=stats.get('Absent',0); unmarked=max(total-present-absent,0)
 return render_template('index.html',students=students,total=total,departments=departments,present=present,absent=absent,unmarked=unmarked,today=today,dept_list=depts,q=q,selected_department=dept)
@app.route('/student/new',methods=['GET','POST'])
@login_required
def add_student():
 if request.method=='POST':
  d=request.form; err=validate_student(d)
  if err: flash(err,'error'); return render_template('form.html',student=d,title='Add Student')
  try:
   with get_db() as c: c.execute('INSERT INTO students(full_name,roll_number,email,phone,department,course,year_of_study,gender,date_of_birth,address) VALUES(?,?,?,?,?,?,?,?,?,?)',(d['full_name'].strip(),d['roll_number'].strip(),d['email'].strip(),d.get('phone','').strip(),d['department'],d.get('course','').strip(),int(d['year_of_study']),d.get('gender',''),d.get('date_of_birth',''),d.get('address','').strip()))
   flash('Student record added successfully.','success'); return redirect(url_for('index'))
  except sqlite3.IntegrityError: flash('That roll number already exists.','error')
 return render_template('form.html',student=request.form if request.method=='POST' else {},title='Add Student')
@app.route('/student/<int:student_id>/edit',methods=['GET','POST'])
@login_required
def edit_student(student_id):
 with get_db() as c: s=c.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
 if not s: abort(404)
 if request.method=='POST':
  d=request.form; err=validate_student(d)
  if err: flash(err,'error'); return render_template('form.html',student=d,title='Edit Student',student_id=student_id)
  try:
   with get_db() as c: c.execute('UPDATE students SET full_name=?,roll_number=?,email=?,phone=?,department=?,course=?,year_of_study=?,gender=?,date_of_birth=?,address=? WHERE id=?',(d['full_name'].strip(),d['roll_number'].strip(),d['email'].strip(),d.get('phone','').strip(),d['department'],d.get('course','').strip(),int(d['year_of_study']),d.get('gender',''),d.get('date_of_birth',''),d.get('address','').strip(),student_id))
   flash('Student record updated.','success'); return redirect(url_for('index'))
  except sqlite3.IntegrityError: flash('That roll number is already in use.','error'); return render_template('form.html',student=d,title='Edit Student',student_id=student_id)
 # Convert sqlite3.Row to dict because the template uses student.get(...).
 return render_template('form.html',student=dict(s),title='Edit Student',student_id=student_id)
@app.post('/student/<int:student_id>/delete')
@login_required
def delete_student(student_id):
 with get_db() as c: c.execute('DELETE FROM students WHERE id=?',(student_id,))
 flash('Student record deleted.','success'); return redirect(url_for('index'))
@app.route('/student/<int:student_id>')
@login_required
def student_detail(student_id):
 with get_db() as c: s=c.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
 if not s: abort(404)
 return render_template('detail.html',student=s)
@app.route('/attendance',methods=['GET','POST'])
@login_required
def attendance():
 selected=request.values.get('attendance_date',date.today().isoformat())
 try: date.fromisoformat(selected)
 except ValueError: selected=date.today().isoformat()
 if request.method=='POST':
  with get_db() as c:
   for s in c.execute('SELECT id FROM students').fetchall():
    status=request.form.get(f"status_{s['id']}")
    if status in ('Present','Absent'):
     c.execute('''INSERT INTO attendance(student_id,attendance_date,status,marked_by) VALUES(?,?,?,?) ON CONFLICT(student_id,attendance_date) DO UPDATE SET status=excluded.status,marked_by=excluded.marked_by,marked_at=CURRENT_TIMESTAMP''',(s['id'],selected,status,session['user_id']))
  flash(f'Attendance saved for {selected}.','success'); return redirect(url_for('attendance',attendance_date=selected))
 with get_db() as c:
  students=c.execute('''SELECT s.*,a.status FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date=? ORDER BY s.full_name''',(selected,)).fetchall()
  counts={r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM attendance WHERE attendance_date=? GROUP BY status',(selected,)).fetchall()}
 stats={'Present':counts.get('Present',0),'Absent':counts.get('Absent',0)}; stats['Unmarked']=max(len(students)-stats['Present']-stats['Absent'],0)
 return render_template('attendance.html',students=students,selected_date=selected,stats=stats,total=len(students))
@app.route('/export')
@login_required
def export_csv():
 with get_db() as c: rows=c.execute('''SELECT s.id,s.full_name,s.roll_number,s.email,s.phone,s.department,s.course,s.year_of_study,s.gender,s.date_of_birth,s.address,a.attendance_date,a.status FROM students s LEFT JOIN attendance a ON a.student_id=s.id ORDER BY s.full_name,a.attendance_date''').fetchall()
 out=io.StringIO(); w=csv.writer(out); w.writerow(['ID','Full Name','Roll Number','Email','Phone','Department','Course','Year','Gender','Date of Birth','Address','Attendance Date','Attendance Status']); w.writerows([tuple(r) for r in rows])
 resp=make_response('\ufeff'+out.getvalue()); resp.headers['Content-Disposition']='attachment; filename=student_records_and_attendance.csv'; resp.headers['Content-Type']='text/csv; charset=utf-8'; return resp
@app.errorhandler(404)
def not_found(_): return render_template('404.html'),404
if __name__=='__main__': init_db(); app.run(debug=True)
