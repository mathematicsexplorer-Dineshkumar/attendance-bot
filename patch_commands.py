with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Import BotCommand
old_import = "from telegram import (\n    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,\n    InlineKeyboardButton, InlineKeyboardMarkup,\n    KeyboardButton\n)"
new_import = "from telegram import (\n    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,\n    InlineKeyboardButton, InlineKeyboardMarkup,\n    KeyboardButton, BotCommand\n)"
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    changes.append("BotCommand imported")
else:
    print("WARNING: telegram import block not found (exact match)")

# 2. Add post_init function before "app = ApplicationBuilder"
post_init_code = '''async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Start or open your main menu"),
        BotCommand("logout", "Log out of your account"),
    ])

'''
old_app_line = "persistence = PicklePersistence(filepath=\"bot_persistence.pickle\")"
if old_app_line in content and "async def post_init" not in content:
    content = content.replace(old_app_line, post_init_code + old_app_line, 1)
    changes.append("post_init function added")
elif "async def post_init" in content:
    print("INFO: post_init already exists")
else:
    print("WARNING: persistence line not found")

# 3. Register post_init in ApplicationBuilder
old_builder = 'app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()'
new_builder = 'app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).post_init(post_init).build()'
if old_builder in content:
    content = content.replace(old_builder, new_builder, 1)
    changes.append("post_init registered in builder")
else:
    print("WARNING: ApplicationBuilder line not found")

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Changes made:", changes)
print("PATCH COMPLETE")
