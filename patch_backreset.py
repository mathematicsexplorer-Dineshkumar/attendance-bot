with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []
warnings = []

def try_replace(old, new, label, count=1):
    global content
    if old in content:
        content = content.replace(old, new, count) if count else content.replace(old, new)
        changes.append(label)
        return True
    else:
        warnings.append(label + " -> OLD STRING NOT FOUND")
        return False

# 1. Add BACK_BUTTON constant near keyboards
try_replace(
    'STUDENT_MENU_KEYBOARD = [["My Attendance"], ["Download Attendance Report"], ["Settings"]]',
    'STUDENT_MENU_KEYBOARD = [["My Attendance"], ["Download Attendance Report"], ["Settings"]]\nBACK_BUTTON = "\u2b05 Back to Menu"',
    "BACK_BUTTON constant added"
)

# 2. Add "Reset Attendance" to teacher menu keyboard
try_replace(
    'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Fix Attendance"], ["Join Course", "Set Institute Name"]]',
    'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Fix Attendance", "Reset Attendance"], ["Join Course", "Set Institute Name"]]',
    "Reset Attendance added to teacher keyboard"
)

# 3. Add new state constants
try_replace(
    "FIX_SELECT_COURSE = 22\nFIX_SELECT_DATE = 23\nFIX_SELECT_STUDENT = 24\nFIX_SET_STATUS = 25",
    "FIX_SELECT_COURSE = 22\nFIX_SELECT_DATE = 23\nFIX_SELECT_STUDENT = 24\nFIX_SET_STATUS = 25\nRESET_SELECT_COURSE = 26\nRESET_SELECT_SCOPE = 27\nRESET_SELECT_DATE = 28\nRESET_MONTH_INPUT = 29\nRESET_CONFIRM = 30",
    "reset state constants added"
)

# 4. Append back button to "Add Students" course keyboard
try_replace(
    '''        context.user_data["course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["course_map"][label] = c[0]
            keyboard.append([label])

        await update.message.reply_text(
            "Select the course to add students to:",''',
    '''        context.user_data["course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to add students to:",''',
    "back button added to Add Students course list"
)

# 5. Append back button to "Take Attendance" course keyboard
try_replace(
    '''        context.user_data["attendance_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["attendance_course_map"][label] = c[0]
            keyboard.append([label])

        await update.message.reply_text(
            "Select the course to take attendance for:",''',
    '''        context.user_data["attendance_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["attendance_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to take attendance for:",''',
    "back button added to Take Attendance course list"
)

# 6. Append back button to "View Reports" course keyboard
try_replace(
    '''        context.user_data["report_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["report_course_map"][label] = c[0]
            keyboard.append([label])

        await update.message.reply_text(
            "Select the course to view reports for:",''',
    '''        context.user_data["report_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["report_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to view reports for:",''',
    "back button added to View Reports course list"
)

# 7. Append back button to "Fix Attendance" course keyboard
try_replace(
    '''        context.user_data["fix_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["fix_course_map"][label] = c[0]
            keyboard.append([label])

        await update.message.reply_text(
            "Select the course to fix attendance for:",''',
    '''        context.user_data["fix_course_map"] = {}
        keyboard = []
        for c in courses:
            label = f"{c[1]} ({c[2]})"
            context.user_data["fix_course_map"][label] = c[0]
            keyboard.append([label])
        keyboard.append([BACK_BUTTON])

        await update.message.reply_text(
            "Select the course to fix attendance for:",''',
    "back button added to Fix Attendance course list"
)

# 8. Add back-check + back button to select_course_for_students
try_replace(
    '''    label = update.message.text.strip()
    course_map = context.user_data.get("course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_STUDENTS''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_STUDENTS''',
    "back check added to select_course_for_students"
)

# 9. Add back-check to select_course_for_attendance
try_replace(
    '''    label = update.message.text.strip()
    course_map = context.user_data.get("attendance_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_ATTENDANCE''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("attendance_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_ATTENDANCE''',
    "back check added to select_course_for_attendance"
)

# 10. Add back-check to select_course_for_report
try_replace(
    '''    label = update.message.text.strip()
    course_map = context.user_data.get("report_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_REPORT''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("report_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_REPORT''',
    "back check added to select_course_for_report"
)

# 11. Add back button + back-check to fix_select_course
try_replace(
    '''    label = update.message.text.strip()
    course_map = context.user_data.get("fix_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return FIX_SELECT_COURSE''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    course_map = context.user_data.get("fix_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return FIX_SELECT_COURSE''',
    "back check added to fix_select_course"
)

try_replace(
    '''        context.user_data["fix_date_map"][display] = d
        keyboard.append([display])

    await update.message.reply_text(
        "Select the session date:",''',
    '''        context.user_data["fix_date_map"][display] = d
        keyboard.append([display])
    keyboard.append([BACK_BUTTON])

    await update.message.reply_text(
        "Select the session date:",''',
    "back button added to fix_select_date keyboard"
)

try_replace(
    '''    label = update.message.text.strip()
    date_map = context.user_data.get("fix_date_map", {})

    if label not in date_map:
        await update.message.reply_text("Please select a valid date from the list.")
        return FIX_SELECT_DATE''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    date_map = context.user_data.get("fix_date_map", {})

    if label not in date_map:
        await update.message.reply_text("Please select a valid date from the list.")
        return FIX_SELECT_DATE''',
    "back check added to fix_select_date"
)

try_replace(
    '''        context.user_data["fix_student_map"][display] = sid
        keyboard.append([display])

    conn.close()

    if not keyboard:
        await show_teacher_menu(update, "No students enrolled in this course.")
        return TEACHER_MENU

    await update.message.reply_text(
        "Select the student to correct:",''',
    '''        context.user_data["fix_student_map"][display] = sid
        keyboard.append([display])

    conn.close()

    if not keyboard:
        await show_teacher_menu(update, "No students enrolled in this course.")
        return TEACHER_MENU

    keyboard.append([BACK_BUTTON])
    await update.message.reply_text(
        "Select the student to correct:",''',
    "back button added to fix_select_student keyboard"
)

try_replace(
    '''    label = update.message.text.strip()
    student_map = context.user_data.get("fix_student_map", {})

    if label not in student_map:
        await update.message.reply_text("Please select a valid student from the list.")
        return FIX_SELECT_STUDENT

    context.user_data["fix_student_id"] = student_map[label]
    context.user_data["fix_student_label"] = label

    status_keyboard = ReplyKeyboardMarkup([["Present", "Absent"]], resize_keyboard=True, one_time_keyboard=True)''',
    '''    label = update.message.text.strip()

    if label == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    student_map = context.user_data.get("fix_student_map", {})

    if label not in student_map:
        await update.message.reply_text("Please select a valid student from the list.")
        return FIX_SELECT_STUDENT

    context.user_data["fix_student_id"] = student_map[label]
    context.user_data["fix_student_label"] = label

    status_keyboard = ReplyKeyboardMarkup([["Present", "Absent"], [BACK_BUTTON]], resize_keyboard=True, one_time_keyboard=True)''',
    "back check + back button added to fix_select_student/fix_set_status"
)

try_replace(
    '''    choice = update.message.text.strip().lower()
    if choice not in ("present", "absent"):
        await update.message.reply_text("Please choose Present or Absent from the buttons.")
        return FIX_SET_STATUS''',
    '''    choice_raw = update.message.text.strip()
    if choice_raw == BACK_BUTTON:
        await show_teacher_menu(update, "Cancelled.")
        return TEACHER_MENU

    choice = choice_raw.lower()
    if choice not in ("present", "absent"):
        await update.message.reply_text("Please choose Present or Absent from the buttons.")
        return FIX_SET_STATUS''',
    "back check added to fix_set_status"
)

# 12. Add "Reset Attendance" elif branch in teacher_menu_handler (before "join course")
old_marker = '    elif choice == "join course":'
new_block = '''    elif choice == "reset attendance":
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

    elif choice == "join course":'''
if old_marker in content:
    content = content.replace(old_marker, new_block, 1)
    changes.append("reset attendance option added to teacher menu")
else:
    warnings.append("reset attendance branch -> 'join course' marker not found")

# 13. Add all Reset Attendance handler functions before "async def cancel"
reset_handlers_code = '''async def reset_select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"This will permanently delete ALL attendance data for {label}.\\n"
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
        f"This will permanently delete attendance data for {course_label} on {label}.\\n"
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
        f"This will permanently delete attendance data for {course_label} for {text}.\\n"
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

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def reset_select_course" not in content:
    content = content.replace(marker_cancel, reset_handlers_code + marker_cancel, 1)
    changes.append("reset attendance handlers added")
elif "async def reset_select_course" in content:
    print("INFO: reset handlers already exist")
else:
    warnings.append("reset handlers -> cancel() marker not found")

# 14. Register new states in ConversationHandler
old_states_line = "        FIX_SET_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fix_set_status)],"
new_states_line = old_states_line + """
        RESET_SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_course)],
        RESET_SELECT_SCOPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_scope)],
        RESET_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_select_date)],
        RESET_MONTH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_month_input)],
        RESET_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_confirm)],"""
if old_states_line in content and "RESET_SELECT_COURSE: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes.append("reset attendance states registered")
elif "RESET_SELECT_COURSE: [MessageHandler" in content:
    print("INFO: already registered")
else:
    warnings.append("reset states registration -> FIX_SET_STATUS line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("Warnings:", warnings)
print("PATCH COMPLETE")
