with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Update import to include get_setting, set_setting
old_import = "from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme"
new_import = "from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme, get_setting, set_setting"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("import updated")
else:
    print("WARNING: import line not found")

# 2. Add "Set Institute Name" to teacher menu keyboard
old_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"]]'
new_kb = 'TEACHER_MENU_KEYBOARD = [["Create Course", "My Courses"], ["Add Students"], ["Take Attendance"], ["Set Institute Name"]]'
if old_kb in content:
    content = content.replace(old_kb, new_kb)
    changes.append("teacher keyboard updated")
else:
    print("WARNING: teacher menu keyboard line not found")

# 3. Add INSTITUTE_NAME_INPUT state constant
old_state = "THEME_SELECT = 15"
new_state = "THEME_SELECT = 15\nINSTITUTE_NAME_INPUT = 16"
if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes.append("state constant added")
else:
    print("WARNING: THEME_SELECT = 15 not found")

# 4. Add elif branch inside teacher_menu_handler (before its final else)
marker_start = "async def teacher_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: teacher_menu_handler not found!")
else:
    next_func_idx = content.find("\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)
    func_block = content[idx:next_func_idx]

    old_else = '''    else:
        await show_teacher_menu(update, "Please choose an option from the menu below:")
        return TEACHER_MENU
'''
    new_block = '''    elif choice == "set institute name":
        await update.message.reply_text(
            "Enter your institute/college name (this will appear on student reports):",
            reply_markup=ReplyKeyboardRemove()
        )
        return INSTITUTE_NAME_INPUT

    else:
        await show_teacher_menu(update, "Please choose an option from the menu below:")
        return TEACHER_MENU
'''
    if old_else in func_block:
        func_block = func_block.replace(old_else, new_block)
        changes.append("institute name option added to teacher menu")
        content = content[:idx] + func_block + content[next_func_idx:]
    else:
        print("WARNING: else block not found inside teacher_menu_handler")

# 5. Add institute_name_received handler before "async def cancel"
handler_code = '''async def institute_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    set_setting("institute_name", name)
    await show_teacher_menu(update, f"Institute name set to '{name}'. It will now appear on student reports.")
    return TEACHER_MENU

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def institute_name_received" not in content:
    content = content.replace(marker_cancel, handler_code + marker_cancel, 1)
    changes.append("institute_name_received handler added")
elif "async def institute_name_received" in content:
    print("INFO: institute_name_received already exists")
else:
    print("WARNING: cancel() marker not found")

# 6. Register INSTITUTE_NAME_INPUT state in ConversationHandler
old_states_line = "        THEME_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_selected)],"
new_states_line = old_states_line + "\n        INSTITUTE_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, institute_name_received)],"
if old_states_line in content and "INSTITUTE_NAME_INPUT: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes.append("INSTITUTE_NAME_INPUT registered")
elif "INSTITUTE_NAME_INPUT: [MessageHandler" in content:
    print("INFO: already registered")
else:
    print("WARNING: THEME_SELECT registration line not found")

# 7. Capture teacher location accuracy and store it in session
old_teacher_loc = """    teacher_lat = update.message.location.latitude
    teacher_lon = update.message.location.longitude"""
new_teacher_loc = """    teacher_lat = update.message.location.latitude
    teacher_lon = update.message.location.longitude
    teacher_accuracy = update.message.location.horizontal_accuracy or 50"""
if old_teacher_loc in content:
    content = content.replace(old_teacher_loc, new_teacher_loc, 1)
    changes.append("teacher accuracy captured")
else:
    print("WARNING: teacher_lat/teacher_lon lines not found")

old_insert = '''    cursor.execute(
        """INSERT INTO attendance_sessions 
           (course_id, session_date, start_time, status, teacher_lat, teacher_lon) 
           VALUES (?, ?, ?, 'open', ?, ?)""",
        (course_id, today, now_time, teacher_lat, teacher_lon)
    )'''
new_insert = '''    cursor.execute(
        """INSERT INTO attendance_sessions 
           (course_id, session_date, start_time, status, teacher_lat, teacher_lon, teacher_accuracy) 
           VALUES (?, ?, ?, 'open', ?, ?, ?)""",
        (course_id, today, now_time, teacher_lat, teacher_lon, teacher_accuracy)
    )'''
if old_insert in content:
    content = content.replace(old_insert, new_insert, 1)
    changes.append("session insert includes accuracy")
else:
    print("WARNING: session insert query not found")

# 8. Update session select query in student_location_received to fetch teacher_accuracy
old_select = '''    cursor.execute(
        "SELECT status, teacher_lat, teacher_lon FROM attendance_sessions WHERE session_id = ?",
        (session_id,)
    )
    session = cursor.fetchone()'''
new_select = '''    cursor.execute(
        "SELECT status, teacher_lat, teacher_lon, teacher_accuracy FROM attendance_sessions WHERE session_id = ?",
        (session_id,)
    )
    session = cursor.fetchone()'''
if old_select in content:
    content = content.replace(old_select, new_select, 1)
    changes.append("session select updated")
else:
    print("WARNING: session select query not found")

old_unpack = "    status, teacher_lat, teacher_lon = session"
new_unpack = "    status, teacher_lat, teacher_lon, teacher_accuracy = session\n    teacher_accuracy = teacher_accuracy or 50"
if old_unpack in content:
    content = content.replace(old_unpack, new_unpack, 1)
    changes.append("session unpack updated")
else:
    print("WARNING: session unpack line not found")

# 9. Replace static distance check with dynamic accuracy-based threshold
old_distance = '''    distance = haversine(teacher_lat, teacher_lon, student_lat, student_lon)

    if distance > MAX_DISTANCE_METERS:
        conn.close()
        await update.message.reply_text(
            f"You appear to be too far from the classroom ({int(distance)}m away). "
            "Attendance not marked. Please try again from inside the classroom.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END'''
new_distance = '''    student_accuracy = update.message.location.horizontal_accuracy or 50
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
        return ConversationHandler.END'''
if old_distance in content:
    content = content.replace(old_distance, new_distance, 1)
    changes.append("dynamic distance check applied")
else:
    print("WARNING: distance check block not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
