with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Capture teacher's location-prompt message id in select_course_for_attendance
old_teacher_prompt = '''    await update.message.reply_text(
        "Please share your current location (classroom location) to start attendance.\\n"
        "Tap the button below.",
        reply_markup=location_keyboard
    )
    return WAIT_TEACHER_LOCATION'''
new_teacher_prompt = '''    sent_msg = await update.message.reply_text(
        "Please share your current location (classroom location) to start attendance.\\n"
        "Tap the button below.",
        reply_markup=location_keyboard
    )
    context.user_data["teacher_loc_prompt_id"] = sent_msg.message_id
    return WAIT_TEACHER_LOCATION'''
if old_teacher_prompt in content:
    content = content.replace(old_teacher_prompt, new_teacher_prompt, 1)
    changes.append("teacher prompt id captured")
else:
    print("WARNING: teacher prompt block not found")

# 2. Clean up teacher's prompt + location message once location is received
old_teacher_recv = '''    teacher_lat = update.message.location.latitude
    teacher_lon = update.message.location.longitude
    teacher_accuracy = update.message.location.horizontal_accuracy or 50'''
new_teacher_recv = '''    teacher_lat = update.message.location.latitude
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
        pass'''
if old_teacher_recv in content:
    content = content.replace(old_teacher_recv, new_teacher_recv, 1)
    changes.append("teacher location cleanup added")
else:
    print("WARNING: teacher_location_received block not found")

# 3. Capture student's location-prompt + waiting message ids in mark_present_callback
old_mark = '''    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Please share your current location to confirm your attendance.",
        reply_markup=location_keyboard
    )
    await query.edit_message_text("Waiting for your location...")
    return WAIT_STUDENT_LOCATION'''
new_mark = '''    sent_msg = await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Please share your current location to confirm your attendance.",
        reply_markup=location_keyboard
    )
    context.user_data["student_loc_prompt_id"] = sent_msg.message_id
    await query.edit_message_text("Waiting for your location...")
    context.user_data["student_waiting_msg_id"] = query.message.message_id
    return WAIT_STUDENT_LOCATION'''
if old_mark in content:
    content = content.replace(old_mark, new_mark, 1)
    changes.append("student prompt/waiting ids captured")
else:
    print("WARNING: mark_present_callback tail not found")

# 4. Clean up student's prompt + waiting + location message once location is received
old_student_recv = '''async def student_location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.location:
        await update.message.reply_text(
            "Please share your location using the button provided, or send /cancel."
        )
        return WAIT_STUDENT_LOCATION

    session_id = context.user_data.get("pending_mark_session_id")'''
new_student_recv = '''async def student_location_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    session_id = context.user_data.get("pending_mark_session_id")'''
if old_student_recv in content:
    content = content.replace(old_student_recv, new_student_recv, 1)
    changes.append("student location cleanup added")
else:
    print("WARNING: student_location_received block not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
