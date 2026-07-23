with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add random/string imports near top
old_imports = "import os\nimport sqlite3"
new_imports = "import os\nimport sqlite3\nimport random\nimport string"
if old_imports in content and "import random" not in content.split("async def start")[0]:
    content = content.replace(old_imports, new_imports, 1)
    changes.append("random/string imports added")
else:
    print("WARNING: top import block not found or already patched")

# 2. Add a helper function for generating unique join codes, right after get_connection()
old_conn_func = '''def get_connection():
    conn = sqlite3.connect("attendance.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn'''
new_conn_func = '''def get_connection():
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
            return code'''
if old_conn_func in content:
    content = content.replace(old_conn_func, new_conn_func, 1)
    changes.append("generate_unique_join_code helper added")
else:
    print("WARNING: get_connection function block not found")

# 3. Update course_section() to store join_code and show it
old_course_section = '''    cursor.execute(
        "INSERT INTO courses (course_name, section, teacher_id) VALUES (?, ?, ?)",
        (course_name_val, section, teacher[0])
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
        f"Course '{course_name_val} ({section})' created successfully!\\n"
        f"Course ID: {new_course_id}\\n"
        f"Share this ID with co-teachers so they can join via 'Join Course'."
    )
    return TEACHER_MENU'''
new_course_section = '''    join_code = generate_unique_join_code()
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
        f"Course '{course_name_val} ({section})' created successfully!\\n"
        f"Join Code: {join_code}\\n"
        f"Share this code with co-teachers so they can join via 'Join Course'."
    )
    return TEACHER_MENU'''
if old_course_section in content:
    content = content.replace(old_course_section, new_course_section, 1)
    changes.append("course_section updated with join_code")
else:
    print("WARNING: course_section tail block not found")

# 4. Update "my courses" listing to show join_code instead of ID
old_my_courses = '''        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have not created any courses yet.")
        else:
            text = "Your Courses:\\n\\n"
            for c in courses:
                text += f"- {c[1]} ({c[2]})  [ID: {c[0]}]\\n"
            await update.message.reply_text(text)'''
new_my_courses = '''        cursor.execute(
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
            text = "Your Courses:\\n\\n"
            for c in courses:
                text += f"- {c[1]} ({c[2]})  [Join Code: {c[3]}]\\n"
            await update.message.reply_text(text)'''
if old_my_courses in content:
    content = content.replace(old_my_courses, new_my_courses, 1)
    changes.append("my courses listing updated with join_code")
else:
    print("WARNING: my courses block not found")

# 5. Update join_course_input_received to accept alphanumeric code and look up by join_code
old_join_handler = '''async def join_course_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    telegram_id = update.effective_user.id

    if not text.isdigit():
        await update.message.reply_text("Please enter a valid numeric Course ID.")
        return JOIN_COURSE_INPUT

    course_id = int(text)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
    teacher = cursor.fetchone()

    cursor.execute("SELECT course_name, section FROM courses WHERE course_id = ?", (course_id,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        await update.message.reply_text("No course found with that ID. Please check and try again, or /cancel.")
        return JOIN_COURSE_INPUT

    cursor.execute(
        "INSERT OR IGNORE INTO course_teachers (course_id, teacher_id) VALUES (?, ?)",
        (course_id, teacher[0])
    )
    conn.commit()
    conn.close()

    await show_teacher_menu(update, f"You have joined '{course[0]} ({course[1]})' as a co-teacher.")
    return TEACHER_MENU'''
new_join_handler = '''async def join_course_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    return TEACHER_MENU'''
if old_join_handler in content:
    content = content.replace(old_join_handler, new_join_handler, 1)
    changes.append("join_course_input_received updated to use join_code")
else:
    print("WARNING: join_course_input_received block not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
