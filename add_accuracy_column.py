import sqlite3
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN teacher_accuracy REAL")
    print("teacher_accuracy column added.")
except Exception as e:
    print("teacher_accuracy:", e)
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.commit()
conn.close()
print("Done.")
