import sqlite3

def get_connection():
    conn = sqlite3.connect("attendance.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        roll_number TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        father_name TEXT,
        enrollment_number TEXT,
        dob TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        section TEXT,
        teacher_id INTEGER,
        FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course_id INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(student_id),
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        session_date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'open',
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        student_id INTEGER,
        status TEXT,
        marked_time TEXT,
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(session_id),
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
