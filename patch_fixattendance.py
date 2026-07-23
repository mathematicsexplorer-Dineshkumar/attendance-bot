with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add "Fix Attendance" to teacher menu keyboard
old_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Join Course", "Set Institute Name"]]'
new_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Fix Attendance"], ["Join Course", "Set Institute Name"]]'
if old_kb in content:
    content = content.replace(old_kb, new_kb, 1)
    changes.append("teacher keyboard updated with Fix Attendance")
else:
    print("WARNING: teacher menu keyboard line not found")

# 2. Add new state constants
old_state = "JOIN_COURSE_INPUT = 19\nSTUDENT_REPORT_ROLL_INPUT = 20\nREPORT_DATE_INPUT = 21"
new_state = old_state + "\nFIX_SELECT_COURSE = 22\nFIX_SELECT_DATE = 23\nFIX_SELECT_STUDENT = 24\nFIX_SET_STATUS = 25"
if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes.append("new state constants added")
else:
    print("WARNING: state constants block not found")

# 3. Add "fix attendance" elif branch inside teacher_menu_handler (before "join course")
marker_start = "async def teacher_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: teacher_menu_handler not found!")
else:
    next_func_idx = content.find("\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)
    func_block = content[idx:next_func_idx]

    old_marker = '    elif choice == "join course":'
    new_block = '''    elif choice == "fix attendance":
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

        await update.message.reply_text(
            "Select the course to fix attendance for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return FIX_SELECT_COURSE

    elif choice == "join course":'''
    if old_marker in func_block:
        func_block = func_block.replace(old_marker, new_block, 1)
        changes.append("fix attendance option added to teacher menu")
        content = content[:idx] + func_block + content[next_func_idx:]
    else:
        print("WARNING: 'join course' branch not found inside teacher_menu_handler")

# 4. Add all the new handler functions before "async def cancel"
fix_handlers_code = '''async def fix_select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    label = update.message.text.strip()
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
    student_map = context.user_data.get("fix_student_map", {})

    if label not in student_map:
        await update.message.reply_text("Please select a valid student from the list.")
        return FIX_SELECT_STUDENT

    context.user_data["fix_student_id"] = student_map[label]
    context.user_data["fix_student_label"] = label

    status_keyboard = ReplyKeyboardMarkup([["Present", "Absent"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"Set attendance status for:\\n{label}",
        reply_markup=status_keyboard
    )
    return FIX_SET_STATUS

async def fix_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    choice = update.message.text.strip().lower()
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

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def fix_select_course" not in content:
    content = content.replace(marker_cancel, fix_handlers_code + marker_cancel, 1)
    changes.append("fix attendance handlers added")
elif "async def fix_select_course" in content:
    print("INFO: fix attendance handlers already exist")
else:
    print("WARNING: cancel() marker not found for fix handlers")

# 5. Register new states in ConversationHandler
old_states_line = "        REPORT_DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_received)],"
new_states_line = old_states_line + """
        FIX_SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_course)],
        FIX_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_date)],
        FIX_SELECT_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_select_student)],
        FIX_SET_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_set_status)],"""
if old_states_line in content and "FIX_SELECT_COURSE: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes.append("fix attendance states registered")
elif "FIX_SELECT_COURSE: [MessageHandler" in content:
    print("INFO: already registered")
else:
    print("WARNING: REPORT_DATE_INPUT registration line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
