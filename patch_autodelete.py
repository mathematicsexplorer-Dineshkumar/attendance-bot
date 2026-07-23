with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

delete_snippet = """    try:
        await update.message.delete()
    except Exception:
        pass
"""

target_functions = [
    "start",
    "choose_role",
    "student_roll",
    "student_dob",
    "teacher_name",
    "teacher_password",
    "teacher_menu_handler",
    "course_name",
    "course_section",
    "select_course_for_students",
    "select_course_for_attendance",
    "attendance_running_handler",
    "student_menu_handler",
    "theme_selected",
    "institute_name_received",
    "select_course_for_report",
    "report_menu_handler",
    "join_course_input_received",
    "student_report_roll_received",
    "report_date_received",
    "cancel",
    "logout",
]

patched = []
skipped = []

for name in target_functions:
    signature = f"async def {name}(update: Update, context: ContextTypes.DEFAULT_TYPE):\n"
    idx = content.find(signature)
    if idx == -1:
        skipped.append(name + " (signature not found)")
        continue

    insert_pos = idx + len(signature)
    # Check if delete snippet already present right after (avoid double insert on re-run)
    already_there = content[insert_pos:insert_pos + len(delete_snippet)] == delete_snippet
    if already_there:
        skipped.append(name + " (already patched)")
        continue

    content = content[:insert_pos] + delete_snippet + content[insert_pos:]
    patched.append(name)

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched functions:", patched)
print("Skipped:", skipped)
print("PATCH COMPLETE")
