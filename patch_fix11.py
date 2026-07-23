with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

old_states_line = """        SELECT_COURSE_FOR_REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course_for_report)],
        REPORT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_menu_handler)],"""

new_states_line = old_states_line + """
        JOIN_COURSE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, join_course_input_received)],
        STUDENT_REPORT_ROLL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, student_report_roll_received)],
        REPORT_DATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_received)],"""

if old_states_line in content and "JOIN_COURSE_INPUT: [MessageHandler" not in content:
    content = content.replace(old_states_line, new_states_line, 1)
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: new states registered.")
elif "JOIN_COURSE_INPUT: [MessageHandler" in content:
    print("INFO: already registered, no change needed.")
else:
    print("ERROR: could not find the states block to patch. Pasting nearby content for debugging:")
    idx = content.find("REPORT_MENU: [MessageHandler")
    print(content[max(0,idx-200):idx+300])
