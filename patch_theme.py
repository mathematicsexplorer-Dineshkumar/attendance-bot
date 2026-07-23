with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes_made = []

# 1. Add Settings button to student menu keyboard
old_kb = 'STUDENT_MENU_KEYBOARD = [["My Attendance"], ["Download Attendance Report"]]'
new_kb = 'STUDENT_MENU_KEYBOARD = [["My Attendance"], ["Download Attendance Report"], ["Settings"]]'
if old_kb in content:
    content = content.replace(old_kb, new_kb)
    changes_made.append("keyboard updated")
else:
    print("WARNING: student menu keyboard line not found, skipping that change.")

# 2. Add THEME_SELECT state constant after STUDENT_MENU = 14
old_state = "STUDENT_MENU = 14"
new_state = "STUDENT_MENU = 14\nTHEME_SELECT = 15"
if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes_made.append("state added")
else:
    print("WARNING: STUDENT_MENU = 14 line not found, skipping that change.")

# 3. Import theme helpers
old_import = "from reports import generate_report_image, generate_report_pdf"
new_import = "from reports import generate_report_image, generate_report_pdf, get_student_theme, set_student_theme"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes_made.append("import updated")
else:
    print("WARNING: reports import line not found, skipping that change.")

# 4. Update the download block to use theme, and add Settings option + theme_selected handler
marker_start = "async def student_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: student_menu_handler not found!")
else:
    next_func_idx = content.find("\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)
    func_block = content[idx:next_func_idx]

    old_download_call = """        generate_report_image(student_id, img_path)
        generate_report_pdf(student_id, pdf_path)"""
    new_download_call = """        student_theme = get_student_theme(student_id)
        generate_report_image(student_id, img_path, theme=student_theme)
        generate_report_pdf(student_id, pdf_path)"""

    if old_download_call in func_block:
        func_block = func_block.replace(old_download_call, new_download_call)
        changes_made.append("download call updated with theme")
    else:
        print("WARNING: download call block not found, skipping that change.")

    old_else = '''    else:
        await show_student_menu(update, "Please choose an option from the menu below:")
        return STUDENT_MENU
'''
    new_settings_block = '''    elif choice == "settings":
        theme_keyboard = ReplyKeyboardMarkup([["Light", "Dark"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Choose your report theme:",
            reply_markup=theme_keyboard
        )
        return THEME_SELECT

    else:
        await show_student_menu(update, "Please choose an option from the menu below:")
        return STUDENT_MENU
'''
    if old_else in func_block:
        func_block = func_block.replace(old_else, new_settings_block)
        changes_made.append("settings option added")
    else:
        print("WARNING: else block not found in student_menu_handler, skipping settings addition.")

    content = content[:idx] + func_block + content[next_func_idx:]

# 5. Add theme_selected handler function right before "async def cancel"
theme_handler_code = '''async def theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

'''
marker_cancel = "async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):"
if marker_cancel in content and "async def theme_selected" not in content:
    content = content.replace(marker_cancel, theme_handler_code + marker_cancel, 1)
    changes_made.append("theme_selected handler added")
elif "async def theme_selected" in content:
    print("INFO: theme_selected already exists, skipping.")
else:
    print("WARNING: cancel() marker not found, could not add theme_selected handler.")

# 6. Register THEME_SELECT state in ConversationHandler
old_states_line = "        STUDENT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_menu_handler)],"
new_states_line = old_states_line + "\n        THEME_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_selected)],"
if old_states_line in content and "THEME_SELECT: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    changes_made.append("THEME_SELECT registered in ConversationHandler")
elif "THEME_SELECT: [MessageHandler" in content:
    print("INFO: THEME_SELECT already registered, skipping.")
else:
    print("WARNING: STUDENT_MENU state registration line not found.")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes_made)
print("PATCH COMPLETE")
