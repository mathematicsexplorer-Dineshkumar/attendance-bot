import os
import sqlite3
import random
import string
import math
import pandas as pd
from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme, get_setting, set_setting, generate_course_report_pdf, generate_course_report_excel
from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme, get_setting, set_setting, generate_course_report_pdf, generate_course_report_excel
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, BotCommand
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, CallbackQueryHandler, filters, PicklePersistence
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

MAX_DISTANCE_METERS = 100  # allowed radius from teacher's location

def get_connection():
    conn = sqlite3.connect("attendance.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def generate_unique_join_code():
    conn = get_connection()
    cursor = conn.cursor()
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(chars) for _ in range(6))
        cursor.execute("SELECT 1 FROM courses WHERE join_code = ?", (code,))
        if not cursor.fetchone():
            conn.close()
            return code

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def initialize_database():
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
        dob TEXT NOT NULL,
        theme TEXT DEFAULT \'light\'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        section TEXT,
        teacher_id INTEGER,
        join_code TEXT,
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
        status TEXT DEFAULT \'open\',
        teacher_lat REAL,
        teacher_lon REAL,
        teacher_accuracy REAL,
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS course_teachers (
        course_id INTEGER,
        teacher_id INTEGER,
        PRIMARY KEY (course_id, teacher_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Backfill course_teachers for any pre-existing courses that predate this table
    cursor.execute("SELECT course_id, teacher_id FROM courses")
    for cid, tid in cursor.fetchall():
        cursor.execute(
            "INSERT OR IGNORE INTO course_teachers (course_id, teacher_id) VALUES (?, ?)",
            (cid, tid)
        )

    # Backfill join_code for any courses missing one
    import random as _random
    import string as _string
    cursor.execute("SELECT course_id FROM courses WHERE join_code IS NULL OR join_code = \'\'")
    for (cid,) in cursor.fetchall():
        while True:
            code = "".join(_random.choice(_string.ascii_uppercase + _string.digits) for _ in range(6))
            cursor.execute("SELECT 1 FROM courses WHERE join_code = ?", (code,))
            if not cursor.fetchone():
                break
        cursor.execute("UPDATE courses SET join_code = ? WHERE course_id = ?", (code, cid))

    conn.commit()
    conn.close()
    print("Database initialized/verified successfully.")


# States
CHOOSING_ROLE, STUDENT_ROLL, STUDENT_DOB, TEACHER_NAME, TEACHER_PASSWORD = range(5)
TEACHER_MENU, COURSE_NAME, COURSE_SECTION = range(5, 8)
SELECT_COURSE_FOR_STUDENTS, UPLOAD_STUDENTS_FILE = range(8, 10)
SELECT_COURSE_FOR_ATTENDANCE, WAIT_TEACHER_LOCATION, ATTENDANCE_RUNNING = range(10, 13)
WAIT_STUDENT_LOCATION = 13
STUDENT_MENU = 14
THEME_SELECT = 15
INSTITUTE_NAME_INPUT = 16
SELECT_COURSE_FOR_REPORT = 17
REPORT_MENU = 18
JOIN_COURSE_INPUT = 19
STUDENT_REPORT_ROLL_INPUT = 20
REPORT_DATE_INPUT = 21
FIX_SELECT_COURSE = 22
FIX_SELECT_DATE = 23
FIX_SELECT_STUDENT = 24
FIX_SET_STATUS = 25
RESET_SELECT_COURSE = 26
RESET_SELECT_SCOPE = 27
RESET_SELECT_DATE = 28
RESET_MONTH_INPUT = 29
RESET_CONFIRM = 30

TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Fix Attendance", "Reset Attendance"], ["Join Course", "Set Institute Name"]]
STUDENT_MENU_KEYBOARD = [["My Attendance"], ["Download Attendance Report"], ["Settings"]]
BACK_BUTTON = "⬅ Back to Menu"

async def show_teacher_menu(update: Update, text: str):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(TEACHER_MENU_KEYBOARD, resize_keyboard=True)
    )

async def show_student_menu(update: Update, text: str):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(STUDENT_MENU_KEYBOARD, resize_keyboard=True)
    )

def build_student_attendance_report(student_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT c.course_id, c.course_name, c.section
           FROM courses c
           JOIN enrollments e ON c.course_id = e.course_id
           WHERE e.student_id = ?""",
        (student_id,)
    )
    courses = cursor.fetchall()

    if not courses:
        conn.close()
        return "You are not enrolled in any courses yet."

    lines = ["Your Attendance Summary:\n"]
    total_classes_all = 0
    total_present_all = 0

    for course_id, course_name, section in courses:
        cursor.execute(
            """SELECT ar.status FROM attendance_records ar
               JOIN attendance_sessions s ON ar.session_id = s.session_id
               WHERE ar.student_id = ? AND s.course_id = ?""",
            (student_id, course_id)
        )
        records = cursor.fetchall()
        total = len(records)
        present = sum(1 for r in records if r[0] == "present")
        absent = total - present
        pct = (present / total * 100) if total > 0 else 0.0

        total_classes_all += total
        total_present_all += present

        lines.append(
            f"{course_name} ({section}): {present}/{total} present ({pct:.1f}%), {absent} absent"
        )

    conn.close()

    overall_pct = (total_present_all / total_classes_all * 100) if total_classes_all > 0 else 0.0
    lines.append(f"\nOverall: {total_present_all}/{total_classes_all} classes present ({overall_pct:.1f}%)")

    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE telegram_id = ?", (telegram_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM teachers WHERE telegram_id = ?", (telegram_id,))
    teacher = cursor.fetchone()
    conn.close()

    if student:
        await show_student_menu(
            update,
            f"Welcome back, {student[3]}!\nUse /logout to log out."
        )
        return STUDENT_MENU

    if teacher:
        await show_teacher_menu(update, f"Welcome back, {teacher[2]}!\nUse /logout to log out.")
        return TEACHER_MENU

    keyboard = [["Teacher", "Student"]]
    await update.message.reply_text(
        "Welcome to the Attendance Bot!\nAre you a Teacher or a Student?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING_ROLE

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    role = update.message.text.strip().lower()

    if role == "student":
        await update.message.reply_text(
            "Please enter your Roll Number:",
            reply_markup=ReplyKeyboardRemove()
        )
        return STUDENT_ROLL

    elif role == "teacher":
        await update.message.reply_text(
            "Please enter your full Name:",
            reply_markup=ReplyKeyboardRemove()
        )
        return TEACHER_NAME

    else:
        keyboard = [["Teacher", "Student"]]
        await update.message.reply_text(
            "Please choose from the options below:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return CHOOSING_ROLE

async def student_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    roll_number = update.message.text.strip()
    context.user_data["roll_number"] = roll_number

    await update.message.reply_text("Please enter your Date of Birth (DDMMYYYY format, e.g. 15082006):")
    return STUDENT_DOB

async def student_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    dob = update.message.text.strip()
    roll_number = context.user_data.get("roll_number")
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM students WHERE roll_number = ? AND dob = ?",
        (roll_number, dob)
    )
    student = cursor.fetchone()

    if not student:
        conn.close()
        await update.message.reply_text(
            "Roll Number or Date of Birth is incorrect, or you are not yet added by your teacher.\n"
            "Please try again with /start"
        )
        return ConversationHandler.END

    if student[1] is not None:
        conn.close()
        await update.message.reply_text(
            "This Roll Number is already linked to another Telegram account.\n"
            "Please contact your teacher if this is a mistake."
        )
        return ConversationHandler.END

    cursor.execute(
        "UPDATE students SET telegram_id = ? WHERE roll_number = ?",
        (telegram_id, roll_number)
    )
    conn.commit()
    conn.close()

    await show_student_menu(
        update,
        f"Login successful! Welcome, {student[3]}.\nUse /logout to log out."
    )
    return STUDENT_MENU

async def teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    context.user_data["teacher_name"] = update.message.text.strip()
    await update.message.reply_text("Please set a password for your account:")
    return TEACHER_PASSWORD

async def teacher_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    password = update.message.text.strip()
    name = context.user_data.get("teacher_name")
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO teachers (telegram_id, name, password) VALUES (?, ?, ?)",
        (telegram_id, name, password)
    )
    conn.commit()
    conn.close()

    await show_teacher_menu(update, f"Registration successful! Welcome, {name}.\nUse /logout to log out.")
    return TEACHER_MENU

async def teacher_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    choice = update.message.text.strip().lower()

    if choice == "create course":
        await update.message.reply_text(
            "Enter the Course Name (e.g. MTH305):",
            reply_markup=ReplyKeyboardRemove()
        )
        return COURSE_NAME

    elif choice == "my courses":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section, c.join_code FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have not created any courses yet.")
        else:
            text = "Your Courses:\n\n"
            for c in courses:
                text += f"- {c[1]} ({c[2]})  [Join Code: {c[3]}]\n"
            await update.message.reply_text(text)

        return TEACHER_MENU

    elif choice == "add students":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have no courses yet. Please create a course first.")
            return TEACHER_MENU

        context.user_data["course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to add students to:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_COURSE_FOR_STUDENTS

    elif choice == "take attendance":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have no courses yet. Please create a course first.")
            return TEACHER_MENU

        context.user_data["attendance_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["attendance_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to take attendance for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_COURSE_FOR_ATTENDANCE

    elif choice == "view reports":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have no courses yet. Please create a course first.")
            return TEACHER_MENU

        context.user_data["report_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["report_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to view reports for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_COURSE_FOR_REPORT

    elif choice == "fix attendance":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have no courses yet.")
            return TEACHER_MENU

        context.user_data["fix_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["fix_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to fix attendance for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return FIX_SELECT_COURSE

    elif choice == "reset attendance":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have no courses yet.")
            return TEACHER_MENU

        context.user_data["reset_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["reset_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to reset attendance for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return RESET_SELECT_COURSE

    elif choice == "join course":
        await update.message.reply_text(
            "Enter the Course ID shared by the other teacher:",
            reply_markup=ReplyKeyboardRemove()
        )
        return JOIN_COURSE_INPUT

    elif choice == "set institute name":
        await update.message.reply_text(
            "Enter your institute/college name (this will appear on student reports):",
            reply_markup=ReplyKeyboardRemove()
        )
        return INSTITUTE_NAME_INPUT

    else:
        await show_teacher_menu(update, "Please choose an option from the menu below:")
        return TEACHER_MENU

async def course_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    context.user_data["course_name"] = update.message.text.strip()
    await update.message.reply_text("Enter the Section (e.g. G-1):")
    return COURSE_SECTION

async def course_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    section = update.message.text.strip()
    course_name_val = context.user_data.get("course_name")
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
    teacher = cursor.fetchone()

    join_code = generate_unique_join_code()
    cursor.execute(
        "INSERT INTO courses (course_name, section, teacher_id, join_code) VALUES (?, ?, ?, ?)",
        (course_name_val, section, teacher[0], join_code)
    )
    new_course_id = cursor.lastrowid
    cursor.execute(
        "INSERT OR IGNORE INTO course_teachers (course_id, teacher_id) VALUES (?, ?)",
        (new_course_id, teacher[0])
    )
    conn.commit()
    conn.close()

    await show_teacher_menu(
        update,
        f"Course '{course_name_val} ({section})' created successfully!\n"
        f"Join Code: {join_code}\n"
        f"Share this code with co-teachers so they can join via 'Join Course'."
    )
    return TEACHER_MENU

async def select_course_for_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_STUDENTS

    context.user_data["selected_course_id"] = course_map[label]

    await update.message.reply_text(
        "Please upload the CSV or Excel file with these exact columns:\n"
        "name, father_name, roll_number, enrollment_number, dob\n\n"
        "(dob format: DDMMYYYY, e.g. 15082006)",
        reply_markup=ReplyKeyboardRemove()
    )
    return UPLOAD_STUDENTS_FILE

async def upload_students_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        await update.message.reply_text("Please upload a valid CSV or Excel file.")
        return UPLOAD_STUDENTS_FILE

    file_name = document.file_name
    file = await context.bot.get_file(document.file_id)

    local_path = f"temp_{file_name}"
    await file.download_to_drive(local_path)

    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(local_path, dtype=str)
        else:
            df = pd.read_excel(local_path, dtype=str)
    except Exception as e:
        os.remove(local_path)
        await update.message.reply_text(f"Could not read the file. Error: {e}")
        return UPLOAD_STUDENTS_FILE

    os.remove(local_path)

    required_cols = {"name", "father_name", "roll_number", "enrollment_number", "dob"}
    if not required_cols.issubset(set(df.columns.str.strip().str.lower())):
        await update.message.reply_text(
            "File is missing required columns. Needed columns:\n"
            "name, father_name, roll_number, enrollment_number, dob"
        )
        return UPLOAD_STUDENTS_FILE

    df.columns = df.columns.str.strip().str.lower()
    course_id = context.user_data.get("selected_course_id")

    conn = get_connection()
    cursor = conn.cursor()

    added = 0
    already_existed = 0
    enrolled = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            name = str(row["name"]).strip()
            father_name = str(row["father_name"]).strip()
            roll_number = str(row["roll_number"]).strip()
            enrollment_number = str(row["enrollment_number"]).strip()
            dob = str(row["dob"]).strip()

            if not roll_number or not dob:
                errors.append(f"Row {idx+2}: missing roll_number or dob")
                continue

            cursor.execute("SELECT student_id FROM students WHERE roll_number = ?", (roll_number,))
            existing = cursor.fetchone()

            if existing:
                student_id = existing[0]
                already_existed += 1
            else:
                cursor.execute(
                    "INSERT INTO students (roll_number, name, father_name, enrollment_number, dob) VALUES (?, ?, ?, ?, ?)",
                    (roll_number, name, father_name, enrollment_number, dob)
                )
                student_id = cursor.lastrowid
                added += 1

            cursor.execute(
                "SELECT enrollment_id FROM enrollments WHERE student_id = ? AND course_id = ?",
                (student_id, course_id)
            )
            already_enrolled = cursor.fetchone()

            if not already_enrolled:
                cursor.execute(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
                    (student_id, course_id)
                )
                enrolled += 1

        except Exception as e:
            errors.append(f"Row {idx+2}: {e}")

    conn.commit()
    conn.close()

    result_text = (
        f"Upload complete!\n\n"
        f"New students added: {added}\n"
        f"Already existing students: {already_existed}\n"
        f"Newly enrolled in this course: {enrolled}\n"
    )
    if errors:
        result_text += f"\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])

    await show_teacher_menu(update, result_text)
    return TEACHER_MENU

async def select_course_for_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("attendance_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_ATTENDANCE

    context.user_data["pending_attendance_course_id"] = course_map[label]
    context.user_data["pending_attendance_label"] = label

    location_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Share Classroom Location", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    sent_msg = await update.message.reply_text(
        "Please share your current location (classroom location) to start attendance.\n"
        "Tap the button below.",
        reply_markup=location_keyboard
    )
    context.user_data["teacher_loc_prompt_id"] = sent_msg.message_id
    return WAIT_TEACHER_LOCATION

async def teacher_location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text("Please share your location using the button provided.")
        return WAIT_TEACHER_LOCATION

    teacher_lat = update.message.location.latitude
    teacher_lon = update.message.location.longitude
    teacher_accuracy = update.message.location.horizontal_accuracy or 50

    try:
        prompt_id = context.user_data.get("teacher_loc_prompt_id")
        if prompt_id:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_id)
    except Exception:
        pass
    try:
        await update.message.delete()
    except Exception:
        pass

    course_id = context.user_data.get("pending_attendance_course_id")
    label = context.user_data.get("pending_attendance_label")

    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute(
        """INSERT INTO attendance_sessions 
           (course_id, session_date, start_time, status, teacher_lat, teacher_lon, teacher_accuracy) 
           VALUES (?, ?, ?, 'open', ?, ?, ?)""",
        (course_id, today, now_time, teacher_lat, teacher_lon, teacher_accuracy)
    )
    session_id = cursor.lastrowid

    cursor.execute(
        """SELECT s.student_id, s.telegram_id, s.name FROM students s
           JOIN enrollments e ON s.student_id = e.student_id
           WHERE e.course_id = ?""",
        (course_id,)
    )
    enrolled_students = cursor.fetchall()
    conn.commit()
    conn.close()

    context.user_data["active_session_id"] = session_id
    context.user_data["active_course_label"] = label

    sent_count = 0
    for student_id, telegram_id, name in enrolled_students:
        if telegram_id is None:
            continue
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Mark Present", callback_data=f"mark_{session_id}_{student_id}")]
            ])
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"Attendance is open for {label}.\nTap the button below to mark yourself present.",
                reply_markup=keyboard
            )
            sent_count += 1
        except Exception:
            pass

    stop_keyboard = ReplyKeyboardMarkup([["Stop Attendance"]], resize_keyboard=True)
    await update.message.reply_text(
        f"Attendance session started for {label}.\n"
        f"Notifications sent to {sent_count} students.\n\n"
        f"Press 'Stop Attendance' when done.",
        reply_markup=stop_keyboard
    )
    return ATTENDANCE_RUNNING

async def attendance_running_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    text = update.message.text.strip().lower()

    if text == "stop attendance":
        session_id = context.user_data.get("active_session_id")
        label = context.user_data.get("active_course_label")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT course_id FROM attendance_sessions WHERE session_id = ?", (session_id,))
        course_id = cursor.fetchone()[0]

        now_time = datetime.now().strftime("%H:%M:%S")
        cursor.execute(
            "UPDATE attendance_sessions SET status = 'closed', end_time = ? WHERE session_id = ?",
            (now_time, session_id)
        )

        cursor.execute(
            """SELECT s.student_id FROM students s
               JOIN enrollments e ON s.student_id = e.student_id
               WHERE e.course_id = ?""",
            (course_id,)
        )
        all_students = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT student_id FROM attendance_records WHERE session_id = ? AND status = 'present'",
            (session_id,)
        )
        present_students = set(row[0] for row in cursor.fetchall())

        absent_count = 0
        for sid in all_students:
            if sid not in present_students:
                cursor.execute(
                    "SELECT record_id FROM attendance_records WHERE session_id = ? AND student_id = ?",
                    (session_id, sid)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO attendance_records (session_id, student_id, status, marked_time) VALUES (?, ?, 'absent', NULL)",
                        (session_id, sid)
                    )
                    absent_count += 1

        conn.commit()
        conn.close()

        await show_teacher_menu(
            update,
            f"Attendance for {label} closed.\n"
            f"Present: {len(present_students)}\n"
            f"Absent: {absent_count}"
        )
        return TEACHER_MENU

    else:
        await update.message.reply_text("Attendance is currently running. Press 'Stop Attendance' when done.")
        return ATTENDANCE_RUNNING

async def mark_present_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    _, session_id, student_id = data.split("_")
    session_id = int(session_id)
    student_id = int(student_id)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM attendance_sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()

    if not session or session[0] != "open":
        conn.close()
        await query.edit_message_text("This attendance session is closed. You could not be marked.")
        return ConversationHandler.END

    cursor.execute("SELECT telegram_id FROM students WHERE student_id = ?", (student_id,))
    expected_telegram_id = cursor.fetchone()[0]
    conn.close()

    if expected_telegram_id != update.effective_user.id:
        await query.edit_message_text("This attendance link is not valid for your account.")
        return ConversationHandler.END

    context.user_data["pending_mark_session_id"] = session_id
    context.user_data["pending_mark_student_id"] = student_id

    location_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Share My Location", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    sent_msg = await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Please share your current location to confirm your attendance.",
        reply_markup=location_keyboard
    )
    context.user_data["student_loc_prompt_id"] = sent_msg.message_id
    await query.edit_message_text("Waiting for your location...")
    context.user_data["student_waiting_msg_id"] = query.message.message_id
    return WAIT_STUDENT_LOCATION

async def student_location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text(
            "Please share your location using the button provided, or send /cancel."
        )
        return WAIT_STUDENT_LOCATION

    try:
        prompt_id = context.user_data.get("student_loc_prompt_id")
        if prompt_id:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_id)
    except Exception:
        pass
    try:
        waiting_id = context.user_data.get("student_waiting_msg_id")
        if waiting_id:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_id)
    except Exception:
        pass
    try:
        await update.message.delete()
    except Exception:
        pass

    session_id = context.user_data.get("pending_mark_session_id")
    student_id = context.user_data.get("pending_mark_student_id")

    if session_id is None or student_id is None:
        await update.message.reply_text("No pending attendance action found.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    student_lat = update.message.location.latitude
    student_lon = update.message.location.longitude

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, teacher_lat, teacher_lon, teacher_accuracy FROM attendance_sessions WHERE session_id = ?",
        (session_id,)
    )
    session = cursor.fetchone()

    if not session or session[0] != "open":
        conn.close()
        await update.message.reply_text(
            "This attendance session is closed. You could not be marked.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    status, teacher_lat, teacher_lon, teacher_accuracy = session
    teacher_accuracy = teacher_accuracy or 50

    cursor.execute(
        "SELECT record_id FROM attendance_records WHERE session_id = ? AND student_id = ?",
        (session_id, student_id)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        await update.message.reply_text(
            "You have already been marked for this session.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    student_accuracy = update.message.location.horizontal_accuracy or 50
    distance = haversine(teacher_lat, teacher_lon, student_lat, student_lon)

    # Dynamic allowed radius: base buffer + both devices' reported GPS accuracy,
    # capped so it can't become unreasonably large.
    dynamic_limit = min(300, MAX_DISTANCE_METERS + teacher_accuracy + student_accuracy)

    if distance > dynamic_limit:
        conn.close()
        await update.message.reply_text(
            f"You appear to be too far from the classroom ({int(distance)}m away, "
            f"allowed up to {int(dynamic_limit)}m based on GPS accuracy). "
            "Attendance not marked. Please move closer, ensure GPS/location accuracy is high "
            "(open outdoors or near a window helps), and try again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    now_time = datetime.now().strftime("%H:%M:%S")
    cursor.execute(
        "INSERT INTO attendance_records (session_id, student_id, status, marked_time) VALUES (?, ?, 'present', ?)",
        (session_id, student_id, now_time)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "You have been marked PRESENT. \u2705",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def student_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    choice = update.message.text.strip().lower()

    if choice == "my attendance":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("Could not find your student record. Please /logout and log in again.")
            return STUDENT_MENU

        student_id = row[0]
        report_text = build_student_attendance_report(student_id)
        await show_student_menu(update, report_text)
        return STUDENT_MENU

    elif choice == "download attendance report":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text("Could not find your student record. Please /logout and log in again.")
            return STUDENT_MENU

        student_id = row[0]
        img_path = f"report_{student_id}.png"
        pdf_path = f"report_{student_id}.pdf"

        student_theme = get_student_theme(student_id)
        generate_report_image(student_id, img_path, theme=student_theme)
        generate_report_pdf(student_id, pdf_path)

        await update.message.reply_photo(photo=open(img_path, "rb"))
        await update.message.reply_document(document=open(pdf_path, "rb"))

        await show_student_menu(update, "Here is your attendance report!")
        return STUDENT_MENU

    elif choice == "settings":
        theme_keyboard = ReplyKeyboardMarkup([["Light", "Dark"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Choose your report theme:",
            reply_markup=theme_keyboard
        )
        return THEME_SELECT

    else:
        await show_student_menu(update, "Please choose an option from the menu below:")
        return STUDENT_MENU

async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    choice = update.message.text.strip().lower()
    if choice not in ("light", "dark"):
        await update.message.reply_text("Please choose Light or Dark from the buttons.")
        return THEME_SELECT

    telegram_id = update.effective_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id FROM students WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text("Could not find your student record.")
        return ConversationHandler.END

    set_student_theme(row[0], choice)
    await show_student_menu(update, f"Theme set to {choice.capitalize()}.")
    return STUDENT_MENU

async def institute_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    name = update.message.text.strip()
    set_setting("institute_name", name)
    await show_teacher_menu(update, f"Institute name set to '{name}'. It will now appear on student reports.")
    return TEACHER_MENU

REPORT_MENU_KEYBOARD = [["Course Summary"], ["Download PDF", "Download Excel"], ["Student-wise Report", "Search by Date"], ["Back to Menu"]]

async def show_report_menu(update: Update, text: str):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(REPORT_MENU_KEYBOARD, resize_keyboard=True)
    )

async def select_course_for_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("report_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_REPORT

    context.user_data["report_course_id"] = course_map[label]
    context.user_data["report_course_label"] = label

    await show_report_menu(update, f"Reports for {label}:")
    return REPORT_MENU

async def report_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    choice = update.message.text.strip().lower()
    course_id = context.user_data.get("report_course_id")
    label = context.user_data.get("report_course_label", "")

    if choice == "course summary":
        from reports import get_course_grid_data
        cdata = get_course_grid_data(course_id)
        if not cdata or not cdata["students"]:
            await update.message.reply_text("No students enrolled or no attendance data yet.")
            return REPORT_MENU

        text = f"Summary for {label}:\n\n"
        text += f"Total sessions held: {len(cdata['dates'])}\n"
        text += f"Total students: {len(cdata['students'])}\n\n"
        for sid, roll, name in cdata["students"]:
            ct = cdata["totals"][sid]
            text += f"{roll} - {name}: {ct['present']}/{ct['total']} ({ct['pct']:.1f}%)\n"

        if len(text) > 3800:
            text = text[:3800] + "\n... (truncated, use PDF/Excel for full report)"

        await show_report_menu(update, text)
        return REPORT_MENU

    elif choice == "download pdf":
        pdf_path = f"course_report_{course_id}.pdf"
        result = generate_course_report_pdf(course_id, pdf_path)
        if result:
            await update.message.reply_document(document=open(pdf_path, "rb"))
        else:
            await update.message.reply_text("No data available to generate report.")
        return REPORT_MENU

    elif choice == "download excel":
        xlsx_path = f"course_report_{course_id}.xlsx"
        result = generate_course_report_excel(course_id, xlsx_path)
        if result:
            await update.message.reply_document(document=open(xlsx_path, "rb"))
        else:
            await update.message.reply_text("No data available to generate report.")
        return REPORT_MENU

    elif choice == "student-wise report":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT s.student_id, s.roll_number, s.name FROM students s
               JOIN enrollments e ON s.student_id = e.student_id
               WHERE e.course_id = ?
               ORDER BY s.roll_number""",
            (course_id,)
        )
        students = cursor.fetchall()
        conn.close()

        if not students:
            await update.message.reply_text("No students enrolled in this course yet.")
            return REPORT_MENU

        context.user_data["student_report_map"] = {}
        keyboard = []
        for sid, roll, name in students:
            label = f"{roll} - {name}"
            context.user_data["student_report_map"][label] = sid
            keyboard.append([label])

        await update.message.reply_text(
            "Select a student:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return STUDENT_REPORT_ROLL_INPUT

    elif choice == "search by date":
        await update.message.reply_text(
            "Enter the date to search (format: DD-MM-YYYY):",
            reply_markup=ReplyKeyboardRemove()
        )
        return REPORT_DATE_INPUT

    elif choice == "back to menu":
        await show_teacher_menu(update, "Back to main menu.")
        return TEACHER_MENU

    else:
        await show_report_menu(update, "Please choose an option from the menu below:")
        return REPORT_MENU

async def join_course_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    code = update.message.text.strip().upper()
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
    teacher = cursor.fetchone()

    cursor.execute("SELECT course_id, course_name, section FROM courses WHERE join_code = ?", (code,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        await update.message.reply_text("No course found with that Join Code. Please check and try again, or /cancel.")
        return JOIN_COURSE_INPUT

    course_id, course_name, section = course

    cursor.execute(
        "SELECT 1 FROM course_teachers WHERE course_id = ? AND teacher_id = ?",
        (course_id, teacher[0])
    )
    already_joined = cursor.fetchone()

    cursor.execute(
        "INSERT OR IGNORE INTO course_teachers (course_id, teacher_id) VALUES (?, ?)",
        (course_id, teacher[0])
    )
    conn.commit()
    conn.close()

    if already_joined:
        await show_teacher_menu(update, f"You are already a co-teacher for '{course_name} ({section})'.")
    else:
        await show_teacher_menu(update, f"You have joined '{course_name} ({section})' as a co-teacher.")
    return TEACHER_MENU

async def student_report_roll_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    label = update.message.text.strip()
    student_map = context.user_data.get("student_report_map", {})

    if label not in student_map:
        await update.message.reply_text(
            "Please select a student from the list provided, or /cancel."
        )
        return STUDENT_REPORT_ROLL_INPUT

    student_id = student_map[label]
    student_name = label.split(" - ", 1)[1] if " - " in label else label
    student_theme = get_student_theme(student_id)
    img_path = f"teacher_view_{student_id}.png"
    pdf_path = f"teacher_view_{student_id}.pdf"

    generate_report_image(student_id, img_path, theme=student_theme)
    generate_report_pdf(student_id, pdf_path)

    await update.message.reply_photo(photo=open(img_path, "rb"))
    await update.message.reply_document(document=open(pdf_path, "rb"))

    await show_report_menu(update, f"Report for {student_name} sent above.")
    return REPORT_MENU

async def report_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    date_text = update.message.text.strip()
    course_id = context.user_data.get("report_course_id")

    try:
        parsed = datetime.strptime(date_text, "%d-%m-%Y")
        db_date = parsed.strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Invalid format. Please use DD-MM-YYYY, or /cancel.")
        return REPORT_DATE_INPUT

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.roll_number, s.name, ar.status FROM students s
           JOIN enrollments e ON s.student_id = e.student_id
           LEFT JOIN attendance_sessions sess ON sess.course_id = e.course_id AND sess.session_date = ?
           LEFT JOIN attendance_records ar ON ar.session_id = sess.session_id AND ar.student_id = s.student_id
           WHERE e.course_id = ?
           ORDER BY s.roll_number""",
        (db_date, course_id)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await show_report_menu(update, "No students found for this course.")
        return REPORT_MENU

    present_list = [r for r in rows if r[2] == "present"]
    absent_list = [r for r in rows if r[2] == "absent"]
    no_class_list = [r for r in rows if r[2] is None]

    text = f"Attendance on {date_text}:\n\n"
    text += f"Present ({len(present_list)}):\n"
    text += "\n".join(f"- {r[0]} {r[1]}" for r in present_list) or "  (none)"
    text += f"\n\nAbsent ({len(absent_list)}):\n"
    text += "\n".join(f"- {r[0]} {r[1]}" for r in absent_list) or "  (none)"

    if no_class_list:
        text += f"\n\nNo session recorded that day for {len(no_class_list)} student(s)."

    if len(text) > 3800:
        text = text[:3800] + "\n... (truncated)"

    await show_report_menu(update, text)
    return REPORT_MENU

async def fix_select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("fix_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return FIX_SELECT_COURSE

    course_id = course_map[label]
    context.user_data["fix_course_id"] = course_id

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT session_date FROM attendance_sessions WHERE course_id = ? ORDER BY session_date DESC LIMIT 15",
        (course_id,)
    )
    date_rows = cursor.fetchall()
    conn.close()

    if not date_rows:
        await show_teacher_menu(update, "No attendance sessions found for this course yet.")
        return TEACHER_MENU

    context.user_data["fix_date_map"] = {}
    keyboard = []
    for (d,) in date_rows:
        try:
            display = datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception:
            display = d
        context.user_data["fix_date_map"][display] = d
        keyboard.append([display])
    keyboard.append([BACK_BUTTON])

    await update.message.reply_text(
        "Select the session date:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return FIX_SELECT_DATE

async def fix_select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    date_map = context.user_data.get("fix_date_map", {})

    if label not in date_map:
        await update.message.reply_text("Please select a valid date from the list.")
        return FIX_SELECT_DATE

    db_date = date_map[label]
    course_id = context.user_data.get("fix_course_id")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id FROM attendance_sessions WHERE course_id = ? AND session_date = ? ORDER BY session_id DESC LIMIT 1",
        (course_id, db_date)
    )
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        await show_teacher_menu(update, "No session found for that date.")
        return TEACHER_MENU

    session_id = session_row[0]
    context.user_data["fix_session_id"] = session_id

    cursor.execute(
        """SELECT s.student_id, s.roll_number, s.name FROM students s
           JOIN enrollments e ON s.student_id = e.student_id
           WHERE e.course_id = ?
           ORDER BY s.roll_number""",
        (course_id,)
    )
    students = cursor.fetchall()

    context.user_data["fix_student_map"] = {}
    keyboard = []
    for sid, roll, name in students:
        cursor.execute(
            "SELECT status FROM attendance_records WHERE session_id = ? AND student_id = ?",
            (session_id, sid)
        )
        rec = cursor.fetchone()
        current = rec[0] if rec else "not marked"
        display = f"{roll} - {name} [{current}]"
        context.user_data["fix_student_map"][display] = sid
        keyboard.append([display])

    conn.close()

    if not keyboard:
        await show_teacher_menu(update, "No students enrolled in this course.")
        return TEACHER_MENU

    keyboard.append([BACK_BUTTON])
    await update.message.reply_text(
        "Select the student to correct:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return FIX_SELECT_STUDENT

async def fix_select_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    student_map = context.user_data.get("fix_student_map", {})

    if label not in student_map:
        await update.message.reply_text("Please select a valid student from the list.")
        return FIX_SELECT_STUDENT

    context.user_data["fix_student_id"] = student_map[label]
    context.user_data["fix_student_label"] = label

    status_keyboard = ReplyKeyboardMarkup([["Present", "Absent"], [BACK_BUTTON]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"Set attendance status for:\n{label}",
        reply_markup=status_keyboard
    )
    return FIX_SET_STATUS

async def fix_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    choice_raw = update.message.text.strip()
    if choice_raw == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    choice = choice_raw.lower()
    if choice not in ("present", "absent"):
        await update.message.reply_text("Please choose Present or Absent from the buttons.")
        return FIX_SET_STATUS

    session_id = context.user_data.get("fix_session_id")
    student_id = context.user_data.get("fix_student_id")
    label = context.user_data.get("fix_student_label", "")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT record_id FROM attendance_records WHERE session_id = ? AND student_id = ?",
        (session_id, student_id)
    )
    existing = cursor.fetchone()

    now_time = datetime.now().strftime("%H:%M:%S") if choice == "present" else None

    if existing:
        cursor.execute(
            "UPDATE attendance_records SET status = ?, marked_time = ? WHERE record_id = ?",
            (choice, now_time, existing[0])
        )
    else:
        cursor.execute(
            "INSERT INTO attendance_records (session_id, student_id, status, marked_time) VALUES (?, ?, ?, ?)",
            (session_id, student_id, choice, now_time)
        )

    conn.commit()
    conn.close()

    await show_teacher_menu(update, f"Updated: {label.split(' [')[0]} is now marked {choice.upper()} for this session.")
    return TEACHER_MENU

async def reset_select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("reset_course_map", {})
    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return RESET_SELECT_COURSE

    context.user_data["reset_course_id"] = course_map[label]
    context.user_data["reset_course_label"] = label

    scope_keyboard = ReplyKeyboardMarkup(
        [["Specific Date"], ["Whole Month"], ["Entire Course"], [BACK_BUTTON]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(
        f"What do you want to reset for {label}?",
        reply_markup=scope_keyboard
    )
    return RESET_SELECT_SCOPE

async def reset_select_scope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    choice = update.message.text.strip()

    if choice == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_id = context.user_data.get("reset_course_id")

    if choice == "Specific Date":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT session_date FROM attendance_sessions WHERE course_id = ? ORDER BY session_date DESC LIMIT 20",
            (course_id,)
        )
        date_rows = cursor.fetchall()
        conn.close()

        if not date_rows:
            await show_teacher_menu(update, "No attendance sessions found for this course.")
            return TEACHER_MENU

        context.user_data["reset_date_map"] = {}
        keyboard = []
        for (d,) in date_rows:
            try:
                display = datetime.strptime(d, "%Y-%m-%d").strftime("%d-%b-%Y")
            except Exception:
                display = d
            context.user_data["reset_date_map"][display] = d
            keyboard.append([display])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the date to reset:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return RESET_SELECT_DATE

    elif choice == "Whole Month":
        await update.message.reply_text(
            "Enter the month to reset (format: MM-YYYY, e.g. 01-2026):",
            reply_markup=ReplyKeyboardRemove()
        )
        return RESET_MONTH_INPUT

    elif choice == "Entire Course":
        context.user_data["reset_scope"] = "course"
        label = context.user_data.get("reset_course_label", "")
        confirm_keyboard = ReplyKeyboardMarkup([["Yes, Reset It", "No, Cancel"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            f"This will permanently delete ALL attendance data for {label}.\n"
            "This cannot be undone. Are you sure?",
            reply_markup=confirm_keyboard
        )
        return RESET_CONFIRM

    else:
        await update.message.reply_text("Please choose an option from the buttons.")
        return RESET_SELECT_SCOPE

async def reset_select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    date_map = context.user_data.get("reset_date_map", {})
    if label not in date_map:
        await update.message.reply_text("Please select a valid date from the list.")
        return RESET_SELECT_DATE

    context.user_data["reset_scope"] = "date"
    context.user_data["reset_target"] = date_map[label]
    course_label = context.user_data.get("reset_course_label", "")

    confirm_keyboard = ReplyKeyboardMarkup([["Yes, Reset It", "No, Cancel"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"This will permanently delete attendance data for {course_label} on {label}.\n"
        "This cannot be undone. Are you sure?",
        reply_markup=confirm_keyboard
    )
    return RESET_CONFIRM

async def reset_month_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    text = update.message.text.strip()

    if text == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    try:
        parsed = datetime.strptime(text, "%m-%Y")
        month_pattern = parsed.strftime("%Y-%m")
    except ValueError:
        await update.message.reply_text("Invalid format. Please use MM-YYYY (e.g. 01-2026), or /cancel.")
        return RESET_MONTH_INPUT

    context.user_data["reset_scope"] = "month"
    context.user_data["reset_target"] = month_pattern
    course_label = context.user_data.get("reset_course_label", "")

    confirm_keyboard = ReplyKeyboardMarkup([["Yes, Reset It", "No, Cancel"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"This will permanently delete attendance data for {course_label} for {text}.\n"
        "This cannot be undone. Are you sure?",
        reply_markup=confirm_keyboard
    )
    return RESET_CONFIRM

async def reset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    choice = update.message.text.strip().lower()

    if not choice.startswith("yes"):
        await show_teacher_menu(update, "Cancelled. No data was deleted.")
        return TEACHER_MENU

    course_id = context.user_data.get("reset_course_id")
    scope = context.user_data.get("reset_scope")
    target = context.user_data.get("reset_target")

    conn = get_connection()
    cursor = conn.cursor()

    if scope == "course":
        cursor.execute(
            "DELETE FROM attendance_records WHERE session_id IN (SELECT session_id FROM attendance_sessions WHERE course_id = ?)",
            (course_id,)
        )
        cursor.execute("DELETE FROM attendance_sessions WHERE course_id = ?", (course_id,))

    elif scope == "date":
        cursor.execute(
            "DELETE FROM attendance_records WHERE session_id IN (SELECT session_id FROM attendance_sessions WHERE course_id = ? AND session_date = ?)",
            (course_id, target)
        )
        cursor.execute("DELETE FROM attendance_sessions WHERE course_id = ? AND session_date = ?", (course_id, target))

    elif scope == "month":
        like_pattern = target + "-%"
        cursor.execute(
            "DELETE FROM attendance_records WHERE session_id IN (SELECT session_id FROM attendance_sessions WHERE course_id = ? AND session_date LIKE ?)",
            (course_id, like_pattern)
        )
        cursor.execute("DELETE FROM attendance_sessions WHERE course_id = ? AND session_date LIKE ?", (course_id, like_pattern))

    conn.commit()
    conn.close()

    await show_teacher_menu(update, "Attendance data has been reset successfully.")
    return TEACHER_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    await update.message.reply_text("Cancelled. Send /start to begin again.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass
    telegram_id = update.effective_user.id

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE telegram_id = ?", (telegram_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM teachers WHERE telegram_id = ?", (telegram_id,))
    teacher = cursor.fetchone()

    if student:
        cursor.execute("UPDATE students SET telegram_id = NULL WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            "You have been logged out successfully.\nSend /start to log in again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if teacher:
        cursor.execute("UPDATE teachers SET telegram_id = NULL WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            "You have been logged out successfully.\nSend /start to log in again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    conn.close()
    await update.message.reply_text("You are not currently logged in. Send /start to log in.")

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start or open your main menu"),
        BotCommand("logout", "Log out of your account"),
    ])

initialize_database()
persistence = PicklePersistence(filepath="bot_persistence.pickle")
app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).post_init(post_init).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    name="main_conv",
    persistent=True,
    states={
        CHOOSING_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
        STUDENT_ROLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_roll)],
        STUDENT_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_dob)],
        TEACHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_name)],
        TEACHER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_password)],
        TEACHER_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, teacher_menu_handler)],
        COURSE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, course_name)],
        COURSE_SECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, course_section)],
        SELECT_COURSE_FOR_STUDENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_students)],
        UPLOAD_STUDENTS_FILE: [MessageHandler(filters.Document.ALL, upload_students_file)],
        SELECT_COURSE_FOR_ATTENDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_attendance)],
        WAIT_TEACHER_LOCATION: [MessageHandler(filters.LOCATION, teacher_location_received)],
        ATTENDANCE_RUNNING: [MessageHandler(filters.TEXT & ~filters.COMMAND, attendance_running_handler)],
        STUDENT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_menu_handler)],
        THEME_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_selected)],
        INSTITUTE_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, institute_name_received)],
        SELECT_COURSE_FOR_REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_report)],
        REPORT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_menu_handler)],
        JOIN_COURSE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, join_course_input_received)],
        STUDENT_REPORT_ROLL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_report_roll_received)],
        REPORT_DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_received)],
        FIX_SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_course)],
        FIX_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_date)],
        FIX_SELECT_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_student)],
        FIX_SET_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_set_status)],
        RESET_SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_course)],
        RESET_SELECT_SCOPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_scope)],
        RESET_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_date)],
        RESET_MONTH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_month_input)],
        RESET_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_confirm)],
    },
    fallbacks=[CommandHandler("cancel", cancel), CommandHandler("logout", logout)],
)

student_location_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(mark_present_callback, pattern="^mark_")],
    name="student_location_conv",
    persistent=True,
    states={
        WAIT_STUDENT_LOCATION: [MessageHandler(filters.LOCATION, student_location_received)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False,
)

app.add_handler(conv_handler)
app.add_handler(student_location_conv)
app.add_handler(CommandHandler("logout", logout))

print("Bot is running...")
app.run_polling()

