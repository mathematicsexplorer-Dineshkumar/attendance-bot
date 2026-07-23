import sqlite3
import random
import string

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE courses ADD COLUMN join_code TEXT")
    print("join_code column added.")
except Exception as e:
    print("join_code column:", e)

def generate_code():
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(6))

cursor.execute("SELECT course_id FROM courses WHERE join_code IS NULL OR join_code = ''")
courses_needing_code = cursor.fetchall()

existing_codes = set()
cursor.execute("SELECT join_code FROM courses WHERE join_code IS NOT NULL")
for row in cursor.fetchall():
    if row[0]:
        existing_codes.add(row[0])

for (cid,) in courses_needing_code:
    code = generate_code()
    while code in existing_codes:
        code = generate_code()
    existing_codes.add(code)
    cursor.execute("UPDATE courses SET join_code = ? WHERE course_id = ?", (code, cid))

conn.commit()
conn.close()
print(f"Backfilled join codes for {len(courses_needing_code)} course(s).")
