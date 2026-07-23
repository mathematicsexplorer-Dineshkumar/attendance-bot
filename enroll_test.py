import sqlite3
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
cursor.execute("SELECT student_id FROM students WHERE roll_number = ?", ("TEST001",))
student_id = cursor.fetchone()[0]
cursor.execute("SELECT course_id FROM courses WHERE course_name = ?", ("MTH305",))
course_id = cursor.fetchone()[0]
cursor.execute("SELECT * FROM enrollments WHERE student_id = ? AND course_id = ?", (student_id, course_id))
if not cursor.fetchone():
    cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", (student_id, course_id))
    conn.commit()
    print("Test student enrolled in MTH305.")
else:
    print("Already enrolled.")
conn.close()
