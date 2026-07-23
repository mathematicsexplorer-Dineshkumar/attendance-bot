with open("reports.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []
warnings = []

def try_replace(old, new, label):
    global content
    if old in content:
        content = content.replace(old, new, 1)
        changes.append(label)
    else:
        warnings.append(label + " -> NOT FOUND")

# Fix 1: get_date_grid_data (used for student's own date-grid PDF)
try_replace(
    '''        cursor.execute(
            """SELECT s.session_date, ar.status FROM attendance_records ar
               JOIN attendance_sessions s ON ar.session_id = s.session_id
               WHERE ar.student_id = ? AND s.course_id = ?
               ORDER BY s.session_date""",
            (student_id, cid)
        )
        recs = cursor.fetchall()
        day_status = {}
        for d, st in recs:
            if d not in day_status:
                day_status[d] = st
            elif day_status[d] == "present" and st != "present":
                day_status[d] = st''',
    '''        cursor.execute(
            """SELECT s.session_date, ar.status FROM attendance_records ar
               JOIN attendance_sessions s ON ar.session_id = s.session_id
               WHERE ar.student_id = ? AND s.course_id = ?
               ORDER BY s.session_date, s.session_id""",
            (student_id, cid)
        )
        recs = cursor.fetchall()
        day_status = {}
        for d, st in recs:
            day_status[d] = st  # latest session for that date wins''',
    "get_date_grid_data aggregation fixed"
)

# Fix 2: get_course_grid_data (used for course-wide teacher PDF/Excel)
try_replace(
    '''        cursor.execute(
            """SELECT s.session_date, ar.status FROM attendance_records ar
               JOIN attendance_sessions s ON ar.session_id = s.session_id
               WHERE ar.student_id = ? AND s.course_id = ?
               ORDER BY s.session_date""",
            (sid, course_id)
        )
        recs = cursor.fetchall()
        day_status = {}
        for d, st in recs:
            if d not in day_status:
                day_status[d] = st
            elif day_status[d] == "present" and st != "present":
                day_status[d] = st''',
    '''        cursor.execute(
            """SELECT s.session_date, ar.status FROM attendance_records ar
               JOIN attendance_sessions s ON ar.session_id = s.session_id
               WHERE ar.student_id = ? AND s.course_id = ?
               ORDER BY s.session_date, s.session_id""",
            (sid, course_id)
        )
        recs = cursor.fetchall()
        day_status = {}
        for d, st in recs:
            day_status[d] = st  # latest session for that date wins''',
    "get_course_grid_data aggregation fixed"
)

with open("reports.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("Warnings:", warnings)
print("PATCH COMPLETE")
