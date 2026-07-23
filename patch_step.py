with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

marker_start = "async def student_menu_handler"
idx = content.find(marker_start)
if idx == -1:
    print("ERROR: student_menu_handler not found!")
else:
    # Find the end of this function (next "async def " after marker_start, skipping marker itself)
    next_func_idx = content.find("\nasync def ", idx + len(marker_start))
    if next_func_idx == -1:
        next_func_idx = len(content)

    func_block = content[idx:next_func_idx]

    old_else = '''    else:
        await show_student_menu(update, "Please choose an option from the menu below:")
        return STUDENT_MENU
'''

    if old_else not in func_block:
        print("ERROR: else block not found inside student_menu_handler. No changes made.")
    else:
        new_block = '''    elif choice == "download attendance report":
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

        generate_report_image(student_id, img_path)
        generate_report_pdf(student_id, pdf_path)

        await update.message.reply_photo(photo=open(img_path, "rb"))
        await update.message.reply_document(document=open(pdf_path, "rb"))

        await show_student_menu(update, "Here is your attendance report!")
        return STUDENT_MENU

    else:
        await show_student_menu(update, "Please choose an option from the menu below:")
        return STUDENT_MENU
'''
        new_func_block = func_block.replace(old_else, new_block)
        new_content = content[:idx] + new_func_block + content[next_func_idx:]

        with open("bot.py", "w", encoding="utf-8") as f:
            f.write(new_content)

        print("SUCCESS: student_menu_handler updated.")
