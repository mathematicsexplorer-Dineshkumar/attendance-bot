with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Change "student-wise report" branch to show a selectable list instead of asking to type roll number
old_branch = '''    elif choice == "student-wise report":
        await update.message.reply_text(
            "Enter the student's Roll Number:",
            reply_markup=ReplyKeyboardRemove()
        )
        return STUDENT_REPORT_ROLL_INPUT'''
new_branch = '''    elif choice == "student-wise report":
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
        return STUDENT_REPORT_ROLL_INPUT'''
if old_branch in content:
    content = content.replace(old_branch, new_branch, 1)
    changes.append("student-wise report branch now shows selectable list")
else:
    print("WARNING: student-wise report branch not found")

# 2. Replace student_report_roll_received to resolve selection from the map instead of DB roll lookup
old_handler = '''async def student_report_roll_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    student_theme = get_student_theme(student_id)'''
new_handler = '''async def student_report_roll_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    student_map = context.user_data.get("student_report_map", {})

    if label not in student_map:
        await update.message.reply_text(
            "Please select a student from the list provided, or /cancel."
        )
        return STUDENT_REPORT_ROLL_INPUT

    student_id = student_map[label]
    student_name = label.split(" - ", 1)[1] if " - " in label else label
    student_theme = get_student_theme(student_id)'''
if old_handler in content:
    content = content.replace(old_handler, new_handler, 1)
    changes.append("student_report_roll_received updated to use selection map")
else:
    print("WARNING: student_report_roll_received function block not found")

# 3. The subsequent success message currently references roll_number - fix that reference
old_success_msg = 'await show_report_menu(update, f"Report for {student_name} ({roll_number}) sent above.")'
new_success_msg = 'await show_report_menu(update, f"Report for {student_name} sent above.")'
if old_success_msg in content:
    content = content.replace(old_success_msg, new_success_msg, 1)
    changes.append("success message updated")
else:
    print("WARNING: success message line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
