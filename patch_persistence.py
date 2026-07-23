with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Import PicklePersistence
old_import = "from telegram.ext import (\n    ApplicationBuilder, CommandHandler, MessageHandler,\n    ConversationHandler, ContextTypes, CallbackQueryHandler, filters\n)"
new_import = "from telegram.ext import (\n    ApplicationBuilder, CommandHandler, MessageHandler,\n    ConversationHandler, ContextTypes, CallbackQueryHandler, filters, PicklePersistence\n)"
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    changes.append("PicklePersistence imported")
else:
    print("WARNING: telegram.ext import block not found (exact match)")

# 2. Build app with persistence
old_app = 'app = ApplicationBuilder().token(BOT_TOKEN).build()'
new_app = '''persistence = PicklePersistence(filepath="bot_persistence.pickle")
app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()'''
if old_app in content:
    content = content.replace(old_app, new_app, 1)
    changes.append("persistence added to app")
else:
    print("WARNING: app = ApplicationBuilder()... line not found")

# 3. Make conv_handler persistent
old_conv = '''conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],'''
new_conv = '''conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    name="main_conv",
    persistent=True,'''
if old_conv in content:
    content = content.replace(old_conv, new_conv, 1)
    changes.append("main conv_handler made persistent")
else:
    print("WARNING: conv_handler definition not found")

# 4. Make student_location_conv persistent
old_sconv = '''student_location_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(mark_present_callback, pattern="^mark_")],'''
new_sconv = '''student_location_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(mark_present_callback, pattern="^mark_")],
    name="student_location_conv",
    persistent=True,'''
if old_sconv in content:
    content = content.replace(old_sconv, new_sconv, 1)
    changes.append("student_location_conv made persistent")
else:
    print("WARNING: student_location_conv definition not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
