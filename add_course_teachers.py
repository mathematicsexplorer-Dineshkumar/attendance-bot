import sqlite3
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS course_teachers (
    course_id INTEGER,
    teacher_id INTEGER,
    PRIMARY KEY (course_id, teacher_id)
)
""")
cursor.execute("SELECT course_id, teacher_id FROM courses")
existing = cursor.fetchall()
for cid, tid in existing:
    cursor.execute("INSERT OR IGNORE INTO course_teachers (course_id, teacher_id) VALUES (?, ?)", (cid, tid))
conn.commit()
conn.close()
print("course_teachers table created and backfilled with", len(existing), "existing courses.")
