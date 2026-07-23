with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add "Join Course" to teacher menu keyboard
old_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Set Institute Name"]]'
new_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Join Course", "Set Institute Name"]]'
if old_kb in content:
    content = content.replace(old_kb, new_kb, 1)
    changes.append("teacher keyboard updated with Join Course")
else:
    print("WARNING: teacher menu keyboard line not found")

# 2. Add new state constants
old_state = "SELECT_COURSE_FOR_REPORT = 17\nREPORT_MENU = 18"
new_state = "SELECT_COURSE_FOR_REPORT = 17\nREPORT_MENU = 18\nJOIN_COURSE_INPUT = 19\nSTUDENT_REPORT_ROLL_INPUT = 20\nREPORT_DATE_INPUT = 21"
if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes.append("new state constants added")
else:
    print("WARNING: SELECT_COURSE_FOR_REPORT/REPORT_MENU block not found")

# 3. Update course_section() to also insert into course_teachers and show course ID
old_course_section = '''    cursor.execute(
        "INSERT INTO courses (course_name, section, teacher_id) VALUES (?, ?, ?)",
        (course_name_val, section, teacher[0])
    )
    conn.commit()
    conn.close()

    await show_teacher_menu(
        update,
        f"Course '{course_name_val} ({section})' created successfully!"
    )
    return TEACHER_MENU'''
new_course_section = '''    cursor.execute(
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
if old_course_section in content:
    content = content.replace(old_course_section, new_course_section, 1)
    changes.append("course_section updated with course_teachers insert")
else:
    print("WARNING: course_section tail block not found")

# 4. Update "my courses" query to join course_teachers, and show course id
old_my_courses = '''        cursor.execute(
            "SELECT course_name, section FROM courses WHERE teacher_id = ?",
            (teacher[0],)
        )
        courses = cursor.fetchall()
        conn.close()

        if not courses:
            await update.message.reply_text("You have not created any courses yet.")
        else:
            text = "Your Courses:\\n\\n"
            for c in courses:
                text += f"- {c[0]} ({c[1]})\\n"
            await update.message.reply_text(text)'''
new_my_courses = '''        cursor.execute(
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
if old_my_courses in content:
    content = content.replace(old_my_courses, new_my_courses, 1)
    changes.append("my courses query updated")
else:
    print("WARNING: my courses block not found")

# 5. Replace the shared course_id-listing query pattern (used in Add Students / Take Attendance / View Reports) - all occurrences
old_shared_query = '''        cursor.execute(
            "SELECT course_id, course_name, section FROM courses WHERE teacher_id = ?",
            (teacher[0],)
        )'''
new_shared_query = '''        cursor.execute(
            """SELECT c.course_id, c.course_name, c.section FROM courses c
               JOIN course_teachers ct ON c.course_id = ct.course_id
               WHERE ct.teacher_id = ?""",
            (teacher[0],)
        )'''
count_before = content.count(old_shared_query)
if count_before > 0:
    content = content.replace(old_shared_query, new_shared_query)
    changes.append(f"shared course query updated ({count_before} occurrences)")
else:
    print("WARNING: shared course_id listing query not found")

# 6. Add "join course" elif branch inside teacher_menu_handler (before "set institute name")
marker_start = "async def teacher_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: teacher_menu_handler not found!")
else:
    next_func_idx = content.find("\\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)
    func_block = content[idx:next_func_idx]

    old_marker = '    elif choice == "set institute name":'
    new_block = '''    elif choice == "join course":
        await update.message.reply_text(
            "Enter the Course ID shared by the other teacher:",
            reply_markup=ReplyKeyboardRemove()
        )
        return JOIN_COURSE_INPUT

    elif choice == "set institute name":'''
    if old_marker in func_block:
        func_block = func_block.replace(old_marker, new_block, 1)
        changes.append("join course option added to teacher menu")
        content = content[:idx] + func_block + content[next_func_idx:]
    else:
        print("WARNING: 'set institute name' branch not found inside teacher_menu_handler")

# 7. Add join_course_input_received handler before "async def cancel"
join_handler_code = '''async def join_course_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    return TEACHER_MENU

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def join_course_input_received" not in content:
    content = content.replace(marker_cancel, join_handler_code + marker_cancel, 1)
    changes.append("join_course_input_received handler added")
elif "async def join_course_input_received" in content:
    print("INFO: join_course_input_received already exists")
else:
    print("WARNING: cancel() marker not found for join handler")

# 8. Update REPORT_MENU_KEYBOARD to add Student-wise Report and Search by Date
old_report_kb = 'REPORT_MENU_KEYBOARD = [["Course Summary"], ["Download PDF", "Download Excel"], ["Back to Menu"]]'
new_report_kb = 'REPORT_MENU_KEYBOARD = [["Course Summary"], ["Download PDF", "Download Excel"], ["Student-wise Report", "Search by Date"], ["Back to Menu"]]'
if old_report_kb in content:
    content = content.replace(old_report_kb, new_report_kb, 1)
    changes.append("report menu keyboard updated")
else:
    print("WARNING: REPORT_MENU_KEYBOARD line not found")

# 9. Add elif branches in report_menu_handler for the two new options
old_back_branch = '''    elif choice == "back to menu":
        await show_teacher_menu(update, "Back to main menu.")
        return TEACHER_MENU'''
new_back_branch = '''    elif choice == "student-wise report":
        await update.message.reply_text(
            "Enter the student's Roll Number:",
            reply_markup=ReplyKeyboardRemove()
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
        return TEACHER_MENU'''
if old_back_branch in content:
    content = content.replace(old_back_branch, new_back_branch, 1)
    changes.append("student-wise report and date search options added")
else:
    print("WARNING: back to menu branch not found in report_menu_handler")

# 10. Add student_report_roll_received and report_date_received handlers before "async def cancel"
new_handlers_code = '''async def student_report_roll_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roll_number = update.message.text.strip()
    course_id = context.user_data.get("report_course_id")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.student_id, s.name FROM students s
           JOIN enrollments e ON s.student_id = e.student_id
           WHERE s.roll_number = ? AND e.course_id = ?""",
        (roll_number, course_id)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(
            "No student with that Roll Number found in this course. Try again or /cancel."
        )
        return STUDENT_REPORT_ROLL_INPUT

    student_id, student_name = row
    student_theme = get_student_theme(student_id)
    img_path = f"teacher_view_{student_id}.png"
    pdf_path = f"teacher_view_{student_id}.pdf"

    generate_report_image(student_id, img_path, theme=student_theme)
    generate_report_pdf(student_id, pdf_path)

    await update.message.reply_photo(photo=open(img_path, "rb"))
    await update.message.reply_document(document=open(pdf_path, "rb"))

    await show_report_menu(update, f"Report for {student_name} ({roll_number}) sent above.")
    return REPORT_MENU

async def report_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    text = f"Attendance on {date_text}:\\n\\n"
    text += f"Present ({len(present_list)}):\\n"
    text += "\\n".join(f"- {r[0]} {r[1]}" for r in present_list) or "  (none)"
    text += f"\\n\\nAbsent ({len(absent_list)}):\\n"
    text += "\\n".join(f"- {r[0]} {r[1]}" for r in absent_list) or "  (none)"

    if no_class_list:
        text += f"\\n\\nNo session recorded that day for {len(no_class_list)} student(s)."

    if len(text) > 3800:
        text = text[:3800] + "\\n... (truncated)"

    await show_report_menu(update, text)
    return REPORT_MENU

'''
marker_cancel2 = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel2 in content and "async def student_report_roll_received" not in content:
    content = content.replace(marker_cancel2, new_handlers_code + marker_cancel2, 1)
    changes.append("student_report_roll_received and report_date_received handlers added")
elif "async def student_report_roll_received" in content:
    print("INFO: handlers already exist")
else:
    print("WARNING: cancel() marker not found for new report handlers")

# 11. Register new states in ConversationHandler
old_states_line = "        SELECT_COURSE_FOR_REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_report)],\\n        REPORT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_menu_handler)],"
new_states_line = old_states_line + "\\n        JOIN_COURSE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, join_course_input_received)],\\n        STUDENT_REPORT_ROLL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_report_roll_received)],\\n        REPORT_DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_received)],"
if old_states_line in content and "JOIN_COURSE_INPUT: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes.append("new states registered in ConversationHandler")
elif "JOIN_COURSE_INPUT: [MessageHandler" in content:
    print("INFO: already registered")
else:
    print("WARNING: REPORT_MENU registration line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
