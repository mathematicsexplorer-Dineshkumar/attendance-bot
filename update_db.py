import sqlite3
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN teacher_lat REAL")
except Exception as e:
    print("teacher_lat:", e)
try:
    cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN teacher_lon REAL")
except Exception as e:
    print("teacher_lon:", e)
conn.commit()
conn.close()
print("Database updated.")
