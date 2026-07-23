with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Update import
old_import = "from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme, get_setting, set_setting"
new_import = "from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme, get_setting, set_setting, generate_course_report_pdf, generate_course_report_excel"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("import updated")
else:
    print("WARNING: import line not found")

# 2. Add "View Reports" to teacher menu keyboard
old_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["Set Institute Name"]]'
new_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["View Reports"], ["Set Institute Name"]]'
if old_kb in content:
    content = content.replace(old_kb, new_kb)
    changes.append("teacher keyboard updated")
else:
    print("WARNING: teacher menu keyboard line not found")

# 3. Add new state constants
old_state = "INSTITUTE_NAME_INPUT = 16"
new_state = "INSTITUTE_NAME_INPUT = 16\nSELECT_COURSE_FOR_REPORT = 17\nREPORT_MENU = 18"
if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes.append("state constants added")
else:
    print("WARNING: INSTITUTE_NAME_INPUT = 16 not found")

# 4. Add elif branch inside teacher_menu_handler
marker_start = "async def teacher_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: teacher_menu_handler not found!")
else:
    next_func_idx = content.find("\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)
    func_block = content[idx:next_func_idx]

    old_else = '''    elif choice == "set institute name":'''
    new_block = '''    elif choice == "view reports":
        telegram_id = update.effective_user.id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_id FROM teachers WHERE telegram_id = ?", (telegram_id,))
        teacher = cursor.fetchone()

        cursor.execute(
            "SELECT course_id, course_name, section FROM courses WHERE teacher_id = ?",
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

        await update.message.reply_text(
            "Select the course to view reports for:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_COURSE_FOR_REPORT

    elif choice == "set institute name":'''
    if old_else in func_block:
        func_block = func_block.replace(old_else, new_block, 1)
        changes.append("view reports option added to teacher menu")
        content = content[:idx] + func_block + content[next_func_idx:]
    else:
        print("WARNING: 'set institute name' branch not found inside teacher_menu_handler")

# 5. Add select_course_for_report, report_menu_handler, report state helpers before "async def cancel"
report_handlers_code = '''REPORT_MENU_KEYBOARD = [["Course Summary"], ["Download PDF", "Download Excel"], ["Back to Menu"]]

async def show_report_menu(update: Update, text: str):
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(REPORT_MENU_KEYBOARD, resize_keyboard=True)
    )

async def select_course_for_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    course_map = context.user_data.get("report_course_map", {})

    if label not in course_map:
        await update.message.reply_text("Please select a valid course from the list.")
        return SELECT_COURSE_FOR_REPORT

    context.user_data["report_course_id"] = course_map[label]
    context.user_data["report_course_label"] = label

    await show_report_menu(update, f"Reports for {label}:")
    return REPORT_MENU

async def report_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()
    course_id = context.user_data.get("report_course_id")
    label = context.user_data.get("report_course_label", "")

    if choice == "course summary":
        from reports import get_course_grid_data
        cdata = get_course_grid_data(course_id)
        if not cdata or not cdata["students"]:
            await update.message.reply_text("No students enrolled or no attendance data yet.")
            return REPORT_MENU

        text = f"Summary for {label}:\\n\\n"
        text += f"Total sessions held: {len(cdata['dates'])}\\n"
        text += f"Total students: {len(cdata['students'])}\\n\\n"
        for sid, roll, name in cdata["students"]:
            ct = cdata["totals"][sid]
            text += f"{roll} - {name}: {ct['present']}/{ct['total']} ({ct['pct']:.1f}%)\\n"

        if len(text) > 3800:
            text = text[:3800] + "\\n... (truncated, use PDF/Excel for full report)"

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

    elif choice == "back to menu":
        await show_teacher_menu(update, "Back to main menu.")
        return TEACHER_MENU

    else:
        await show_report_menu(update, "Please choose an option from the menu below:")
        return REPORT_MENU

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def report_menu_handler" not in content:
    content = content.replace(marker_cancel, report_handlers_code + marker_cancel, 1)
    changes.append("report handlers added")
elif "async def report_menu_handler" in content:
    print("INFO: report_menu_handler already exists")
else:
    print("WARNING: cancel() marker not found")

# 6. Register new states in ConversationHandler
old_states_line = "        INSTITUTE_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, institute_name_received)],"
new_states_line = old_states_line + "\n        SELECT_COURSE_FOR_REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_report)],\n        REPORT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_menu_handler)],"
if old_states_line in content and "SELECT_COURSE_FOR_REPORT: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes.append("report states registered")
elif "SELECT_COURSE_FOR_REPORT: [MessageHandler" in content:
    print("INFO: already registered")
else:
    print("WARNING: INSTITUTE_NAME_INPUT registration line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
