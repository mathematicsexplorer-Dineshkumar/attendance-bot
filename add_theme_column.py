import sqlite3
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE students ADD COLUMN theme TEXT DEFAULT 'light'")
    print("theme column added.")
except Exception as e:
    print("theme column:", e)
conn.commit()
conn.close()
