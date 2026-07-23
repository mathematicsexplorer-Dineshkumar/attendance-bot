import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

cursor.execute("""
INSERT INTO students (roll_number, name, father_name, enrollment_number, dob)
VALUES (?, ?, ?, ?, ?)
""", ("TEST001", "Test Student", "Test Father", "ENR001", "01012000"))

conn.commit()
conn.close()
print("Test student added successfully.")
